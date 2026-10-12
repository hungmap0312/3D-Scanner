// Copyright 2015-2016 Espressif Systems (Shanghai) PTE LTD
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "Arduino.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_camera.h"
#include "img_converters.h"
#include "fb_gfx.h"
#include "esp32-hal-ledc.h"
#include "sdkconfig.h"
#include "camera_index.h"
#include "board_config.h"
#include <inttypes.h>
#include <stdarg.h>
#include <atomic>
#include "esp_heap_caps.h"
#include "fresh_capture_core.h"

#if defined(ARDUINO_ARCH_ESP32) && defined(CONFIG_ARDUHAL_ESP_LOG)
#include "esp32-hal-log.h"
#endif

// D043: Mutex chung bảo vệ cảm biến/DMA và cờ stream đồng bộ atomic
static SemaphoreHandle_t s_cam_mutex = NULL;
static std::atomic<bool> s_stream_active(false);
static char s_boot_id[FRESH_CAPTURE_BOOT_ID_LEN + 1] = {0};
static uint64_t s_frame_id_counter = 0;
static bool s_frame_id_max_served = false;

void fresh_capture_init_boot_id() {
  if (s_boot_id[0] == '\0') {
    uint8_t rnd[16];
    esp_fill_random(rnd, sizeof(rnd));
    fresh_capture_bytes_to_hex(rnd, 16, s_boot_id);
  }
}

const char* fresh_capture_get_boot_id() {
  if (s_boot_id[0] == '\0') {
    fresh_capture_init_boot_id();
  }
  return s_boot_id;
}

static bool cam_mutex_take(httpd_req_t *req) {
  if (!s_cam_mutex) {
    httpd_resp_send_500(req);
    return false;
  }
  if (xSemaphoreTake(s_cam_mutex, pdMS_TO_TICKS(FRESH_CAPTURE_MUTEX_WAIT_MS)) != pdTRUE) {
    httpd_resp_set_status(req, "503 Service Unavailable");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    if (s_stream_active.load()) {
      httpd_resp_send(req, "ERROR CAMERA_BUSY_STREAM", HTTPD_RESP_USE_STRLEN);
    } else {
      httpd_resp_send(req, "ERROR CAMERA_BUSY_CAPTURE", HTTPD_RESP_USE_STRLEN);
    }
    return false;
  }
  if (s_stream_active.load()) {
    xSemaphoreGive(s_cam_mutex);
    httpd_resp_set_status(req, "503 Service Unavailable");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, "ERROR CAMERA_BUSY_STREAM", HTTPD_RESP_USE_STRLEN);
    return false;
  }
  return true;
}

static void cam_mutex_give() {
  if (s_cam_mutex) {
    xSemaphoreGive(s_cam_mutex);
  }
}

// LED FLASH setup
#if defined(LED_GPIO_NUM)
#define CONFIG_LED_MAX_INTENSITY 255

int led_duty = 0;
bool isStreaming = false;

#endif

typedef struct {
  httpd_req_t *req;
  size_t len;
} jpg_chunking_t;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char *_STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *_STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
// R02: %d cannot carry time_t (64-bit) or suseconds_t on this toolchain.
// Use the same PRIu32 style the /capture and /bmp handlers already use.
static const char *_STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %" PRIu32 "\r\nX-Timestamp: %" PRIu32 ".%06" PRIu32 "\r\n\r\n";

httpd_handle_t stream_httpd = NULL;
httpd_handle_t camera_httpd = NULL;

typedef struct {
  size_t size;   //number of values used for filtering
  size_t index;  //current value index
  size_t count;  //value count
  int sum;
  int *values;  //array to be filled with values
} ra_filter_t;

static ra_filter_t ra_filter;

static ra_filter_t *ra_filter_init(ra_filter_t *filter, size_t sample_size) {
  // startCameraServer() can now be called again from loop() while the HTTP
  // server keeps failing to start (R04 retry path). Release the previous
  // buffer first so each retry does not leak the old allocation.
  if (filter->values) {
    free(filter->values);
    filter->values = NULL;
  }
  memset(filter, 0, sizeof(ra_filter_t));

  filter->values = (int *)malloc(sample_size * sizeof(int));
  if (!filter->values) {
    return NULL;
  }
  memset(filter->values, 0, sample_size * sizeof(int));

  filter->size = sample_size;
  return filter;
}

#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
static int ra_filter_run(ra_filter_t *filter, int value) {
  if (!filter->values) {
    return value;
  }
  filter->sum -= filter->values[filter->index];
  filter->values[filter->index] = value;
  filter->sum += filter->values[filter->index];
  filter->index++;
  filter->index = filter->index % filter->size;
  if (filter->count < filter->size) {
    filter->count++;
  }
  return filter->sum / filter->count;
}
#endif

#if defined(LED_GPIO_NUM)
void enable_led(bool en) {  // Turn LED On or Off
  int duty = en ? led_duty : 0;
  if (en && isStreaming && (led_duty > CONFIG_LED_MAX_INTENSITY)) {
    duty = CONFIG_LED_MAX_INTENSITY;
  }
  ledcWrite(LED_GPIO_NUM, duty);
  //ledc_set_duty(CONFIG_LED_LEDC_SPEED_MODE, CONFIG_LED_LEDC_CHANNEL, duty);
  //ledc_update_duty(CONFIG_LED_LEDC_SPEED_MODE, CONFIG_LED_LEDC_CHANNEL);
  log_i("Set LED intensity to %d", duty);
}
#endif

static esp_err_t bmp_handler(httpd_req_t *req) {
  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
  int64_t fr_start = esp_timer_get_time();
#endif
  fb = esp_camera_fb_get();
  if (!fb) {
    log_e("Camera capture failed");
    cam_mutex_give();
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/x-windows-bmp");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.bmp");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  char ts[32];
  // Cast to uint32_t is safe until year 2106.
  snprintf(ts, 32, "%" PRIu32 ".%06" PRIu32, (uint32_t)fb->timestamp.tv_sec, (uint32_t)fb->timestamp.tv_usec);
  httpd_resp_set_hdr(req, "X-Timestamp", (const char *)ts);

  uint8_t *buf = NULL;
  size_t buf_len = 0;
  bool converted = frame2bmp(fb, &buf, &buf_len);
  esp_camera_fb_return(fb);
  if (!converted) {
    log_e("BMP Conversion failed");
    cam_mutex_give();
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  res = httpd_resp_send(req, (const char *)buf, buf_len);
  free(buf);
  cam_mutex_give();
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
  int64_t fr_end = esp_timer_get_time();
#endif
  log_i("BMP: %" PRId32 "ms, %" PRIu32 "B", (int32_t)((fr_end - fr_start) / 1000), (uint32_t)buf_len);
  return res;
}

static size_t jpg_encode_stream(void *arg, size_t index, const void *data, size_t len) {
  jpg_chunking_t *j = (jpg_chunking_t *)arg;
  if (!index) {
    j->len = 0;
  }
  if (httpd_resp_send_chunk(j->req, (const char *)data, len) != ESP_OK) {
    return 0;
  }
  j->len += len;
  return len;
}

static esp_err_t capture_handler(httpd_req_t *req) {
  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
  int64_t fr_start = esp_timer_get_time();
#endif

#if defined(LED_GPIO_NUM)
  enable_led(true);
  vTaskDelay(150 / portTICK_PERIOD_MS);  // The LED needs to be turned on ~150ms before the call to esp_camera_fb_get()
  fb = esp_camera_fb_get();              // or it won't be visible in the frame. A better way to do this is needed.
  enable_led(false);
#else
  fb = esp_camera_fb_get();
#endif

  if (!fb) {
    log_e("Camera capture failed");
    cam_mutex_give();
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  char ts[32];
  // Cast to uint32_t is safe until year 2106.
  snprintf(ts, 32, "%" PRIu32 ".%06" PRIu32, (uint32_t)fb->timestamp.tv_sec, (uint32_t)fb->timestamp.tv_usec);
  httpd_resp_set_hdr(req, "X-Timestamp", (const char *)ts);

#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
  size_t fb_len = 0;
#endif
  if (fb->format == PIXFORMAT_JPEG) {
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
    fb_len = fb->len;
#endif
    res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  } else {
    jpg_chunking_t jchunk = {req, 0};
    res = frame2jpg_cb(fb, 80, jpg_encode_stream, &jchunk) ? ESP_OK : ESP_FAIL;
    httpd_resp_send_chunk(req, NULL, 0);
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
    fb_len = jchunk.len;
#endif
  }
  esp_camera_fb_return(fb);
  cam_mutex_give();
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
  int64_t fr_end = esp_timer_get_time();
#endif
  log_i("JPG: %" PRIu32 "B %" PRId32 " ms", (uint32_t)fb_len, (int32_t)((fr_end - fr_start) / 1000));
  return res;
}

static esp_err_t capture_fresh_handler(httpd_req_t *req) {
  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  int64_t t_req = esp_timer_get_time();
  int64_t t_deadline = t_req + FRESH_CAPTURE_TIMEOUT_US;
  uint32_t discarded_count = 0;
  camera_fb_t *fb = NULL;

  while (true) {
    int64_t now = esp_timer_get_time();
    if (now >= t_deadline) {
      cam_mutex_give();
      httpd_resp_set_status(req, "503 Service Unavailable");
      httpd_resp_set_type(req, "text/plain");
      httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
      httpd_resp_send(req, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME", HTTPD_RESP_USE_STRLEN);
      return ESP_FAIL;
    }

    fb = esp_camera_fb_get();
    now = esp_timer_get_time();
    if (now >= t_deadline) {
      if (fb) {
        esp_camera_fb_return(fb);
        fb = NULL;
      }
      cam_mutex_give();
      httpd_resp_set_status(req, "503 Service Unavailable");
      httpd_resp_set_type(req, "text/plain");
      httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
      httpd_resp_send(req, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME", HTTPD_RESP_USE_STRLEN);
      return ESP_FAIL;
    }

    if (!fb) {
      cam_mutex_give();
      httpd_resp_set_status(req, "503 Service Unavailable");
      httpd_resp_set_type(req, "text/plain");
      httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
      httpd_resp_send(req, "ERROR CAMERA_NO_BUFFER", HTTPD_RESP_USE_STRLEN);
      return ESP_FAIL;
    }

    int64_t t_frame = fresh_capture_make_timestamp_us((uint32_t)fb->timestamp.tv_sec, (uint32_t)fb->timestamp.tv_usec);
    if (fresh_capture_is_fresh(t_frame, t_req)) {
      break;
    }

    // Stale frame
    discarded_count++;
    esp_camera_fb_return(fb);
    fb = NULL;

    if (discarded_count >= FRESH_CAPTURE_MAX_DISCARD) {
      cam_mutex_give();
      httpd_resp_set_status(req, "503 Service Unavailable");
      httpd_resp_set_type(req, "text/plain");
      httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
      httpd_resp_send(req, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME", HTTPD_RESP_USE_STRLEN);
      return ESP_FAIL;
    }
  }

  if (fb->format != PIXFORMAT_JPEG) {
    esp_camera_fb_return(fb);
    cam_mutex_give();
    httpd_resp_set_status(req, "500 Internal Server Error");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, "ERROR CAMERA_UNSUPPORTED_FORMAT", HTTPD_RESP_USE_STRLEN);
    return ESP_FAIL;
  }

  uint64_t allocated_id = 0;
  if (!fresh_capture_allocate_id(&s_frame_id_counter, &s_frame_id_max_served, &allocated_id)) {
    esp_camera_fb_return(fb);
    cam_mutex_give();
    httpd_resp_set_status(req, "500 Internal Server Error");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, "ERROR FRAME_ID_OVERFLOW", HTTPD_RESP_USE_STRLEN);
    return ESP_FAIL;
  }

  char str_id[32];
  snprintf(str_id, sizeof(str_id), "%llu", (unsigned long long)allocated_id);

  char str_ts[32];
  fresh_capture_format_timestamp(str_ts, sizeof(str_ts), (uint32_t)fb->timestamp.tv_sec, (uint32_t)fb->timestamp.tv_usec);

  char str_req_ts[32];
  uint32_t req_sec = 0;
  uint32_t req_usec = 0;
  fresh_capture_split_timestamp_us(t_req, &req_sec, &req_usec);
  fresh_capture_format_timestamp(str_req_ts, sizeof(str_req_ts), req_sec, req_usec);

  char str_discarded[16];
  snprintf(str_discarded, sizeof(str_discarded), "%u", (unsigned)discarded_count);

  if (httpd_resp_set_type(req, "image/jpeg") != ESP_OK ||
      httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture_fresh.jpg") != ESP_OK ||
      httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*") != ESP_OK ||
      httpd_resp_set_hdr(req, "X-Frame-Id", str_id) != ESP_OK ||
      httpd_resp_set_hdr(req, "X-Boot-Id", fresh_capture_get_boot_id()) != ESP_OK ||
      httpd_resp_set_hdr(req, "X-Timestamp", str_ts) != ESP_OK ||
      httpd_resp_set_hdr(req, "X-Request-Timestamp", str_req_ts) != ESP_OK ||
      httpd_resp_set_hdr(req, "X-Discarded-Frames", str_discarded) != ESP_OK) {
    esp_camera_fb_return(fb);
    fb = NULL;
    cam_mutex_give();
    httpd_resp_set_status(req, "500 Internal Server Error");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, "ERROR CAMERA_INTERNAL", HTTPD_RESP_USE_STRLEN);
    return ESP_FAIL;
  }

  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  cam_mutex_give();
  return res;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  if (!s_cam_mutex || xSemaphoreTake(s_cam_mutex, pdMS_TO_TICKS(FRESH_CAPTURE_MUTEX_WAIT_MS)) != pdTRUE) {
    httpd_resp_set_status(req, "503 Service Unavailable");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    if (s_stream_active.load()) {
      httpd_resp_send(req, "ERROR CAMERA_BUSY_STREAM", HTTPD_RESP_USE_STRLEN);
    } else {
      httpd_resp_send(req, "ERROR CAMERA_BUSY_CAPTURE", HTTPD_RESP_USE_STRLEN);
    }
    return ESP_FAIL;
  }
  s_stream_active.store(true);

  camera_fb_t *fb = NULL;
  struct timeval _timestamp;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t *_jpg_buf = NULL;
  char *part_buf[128];

  static int64_t last_frame = 0;
  if (!last_frame) {
    last_frame = esp_timer_get_time();
  }

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) {
    s_stream_active = false;
    cam_mutex_give();
    return res;
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "X-Framerate", "60");

#if defined(LED_GPIO_NUM)
  isStreaming = true;
  enable_led(true);
#endif

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      log_e("Camera capture failed");
      res = ESP_FAIL;
    } else {
      _timestamp.tv_sec = fb->timestamp.tv_sec;
      _timestamp.tv_usec = fb->timestamp.tv_usec;
      if (fb->format != PIXFORMAT_JPEG) {
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if (!jpeg_converted) {
          log_e("JPEG compression failed");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    if (res == ESP_OK) {
      size_t hlen = snprintf((char *)part_buf, 128, _STREAM_PART, (uint32_t)_jpg_buf_len, (uint32_t)_timestamp.tv_sec, (uint32_t)_timestamp.tv_usec);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if (res != ESP_OK) {
      log_e("Send frame failed");
      break;
    }
    int64_t fr_end = esp_timer_get_time();

    int64_t frame_time = fr_end - last_frame;
    last_frame = fr_end;

    frame_time /= 1000;
#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO
    uint32_t avg_frame_time = ra_filter_run(&ra_filter, frame_time);
#endif
    log_i(
      "MJPG: %" PRIu32 "B %" PRId32 "ms (%.1ffps), AVG: %" PRIu32 "ms (%.1ffps)", (uint32_t)_jpg_buf_len, (int32_t)frame_time, 1000.0 / frame_time,
      avg_frame_time, 1000.0 / avg_frame_time
    );
  }

#if defined(LED_GPIO_NUM)
  isStreaming = false;
  enable_led(false);
#endif

  s_stream_active.store(false);
  cam_mutex_give();
  return res;
}

static esp_err_t parse_get(httpd_req_t *req, char **obuf) {
  char *buf = NULL;
  size_t buf_len = 0;

  buf_len = httpd_req_get_url_query_len(req) + 1;
  if (buf_len > 1) {
    buf = (char *)malloc(buf_len);
    if (!buf) {
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
    if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK) {
      *obuf = buf;
      return ESP_OK;
    }
    free(buf);
  }
  httpd_resp_send_404(req);
  return ESP_FAIL;
}

static esp_err_t cmd_handler(httpd_req_t *req) {
  char *buf = NULL;
  char variable[32];
  char value[32];

  if (parse_get(req, &buf) != ESP_OK) {
    return ESP_FAIL;
  }
  if (httpd_query_key_value(buf, "var", variable, sizeof(variable)) != ESP_OK || httpd_query_key_value(buf, "val", value, sizeof(value)) != ESP_OK) {
    free(buf);
    httpd_resp_send_404(req);
    return ESP_FAIL;
  }
  free(buf);

  int val = atoi(value);
  log_i("%s = %d", variable, val);

  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  sensor_t *s = esp_camera_sensor_get();
  int res = 0;

  if (!strcmp(variable, "framesize")) {
    if (s->pixformat == PIXFORMAT_JPEG) {
      res = s->set_framesize(s, (framesize_t)val);
    }
  } else if (!strcmp(variable, "quality")) {
    res = s->set_quality(s, val);
  } else if (!strcmp(variable, "contrast")) {
    res = s->set_contrast(s, val);
  } else if (!strcmp(variable, "brightness")) {
    res = s->set_brightness(s, val);
  } else if (!strcmp(variable, "saturation")) {
    res = s->set_saturation(s, val);
  } else if (!strcmp(variable, "gainceiling")) {
    res = s->set_gainceiling(s, (gainceiling_t)val);
  } else if (!strcmp(variable, "colorbar")) {
    res = s->set_colorbar(s, val);
  } else if (!strcmp(variable, "awb")) {
    res = s->set_whitebal(s, val);
  } else if (!strcmp(variable, "agc")) {
    res = s->set_gain_ctrl(s, val);
  } else if (!strcmp(variable, "aec")) {
    res = s->set_exposure_ctrl(s, val);
  } else if (!strcmp(variable, "hmirror")) {
    res = s->set_hmirror(s, val);
  } else if (!strcmp(variable, "vflip")) {
    res = s->set_vflip(s, val);
  } else if (!strcmp(variable, "awb_gain")) {
    res = s->set_awb_gain(s, val);
  } else if (!strcmp(variable, "agc_gain")) {
    res = s->set_agc_gain(s, val);
  } else if (!strcmp(variable, "aec_value")) {
    res = s->set_aec_value(s, val);
  } else if (!strcmp(variable, "aec2")) {
    res = s->set_aec2(s, val);
  } else if (!strcmp(variable, "dcw")) {
    res = s->set_dcw(s, val);
  } else if (!strcmp(variable, "bpc")) {
    res = s->set_bpc(s, val);
  } else if (!strcmp(variable, "wpc")) {
    res = s->set_wpc(s, val);
  } else if (!strcmp(variable, "raw_gma")) {
    res = s->set_raw_gma(s, val);
  } else if (!strcmp(variable, "lenc")) {
    res = s->set_lenc(s, val);
  } else if (!strcmp(variable, "special_effect")) {
    res = s->set_special_effect(s, val);
  } else if (!strcmp(variable, "wb_mode")) {
    res = s->set_wb_mode(s, val);
  } else if (!strcmp(variable, "ae_level")) {
    res = s->set_ae_level(s, val);
  }
#if defined(LED_GPIO_NUM)
  else if (!strcmp(variable, "led_intensity")) {
    led_duty = val;
    if (isStreaming) {
      enable_led(true);
    }
  }
#endif
  else {
    log_i("Unknown command: %s", variable);
    res = -1;
  }

  cam_mutex_give();

  if (res < 0) {
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}

static bool status_json_append(char **p, char *end, const char *fmt, ...) {
  if (!p || !*p || *p >= end) {
    return false;
  }
  va_list args;
  va_start(args, fmt);
  int n = vsnprintf(*p, end - *p, fmt, args);
  va_end(args);
  if (n < 0 || n >= (end - *p)) {
    return false;
  }
  *p += n;
  return true;
}

static bool print_reg_safe(char **p, char *end, sensor_t *s, uint16_t reg, uint32_t mask) {
  return status_json_append(p, end, "\"0x%04x\":%d,", reg, s->get_reg(s, reg, mask));
}

static esp_err_t status_handler(httpd_req_t *req) {
  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  static char json_response[2048];

  sensor_t *s = esp_camera_sensor_get();
  char *p = json_response;
  // Reserve 2 bytes at the end for '}' and '\0'
  char *end = json_response + sizeof(json_response) - 2;

  bool ok = true;
  *p++ = '{';

  if (s->id.PID == OV5640_PID || s->id.PID == OV3660_PID) {
    for (int reg = 0x3400; ok && reg < 0x3406; reg += 2) {
      ok = print_reg_safe(&p, end, s, reg, 0xFFF);  //12 bit
    }
    if (ok) ok = print_reg_safe(&p, end, s, 0x3406, 0xFF);

    if (ok) ok = print_reg_safe(&p, end, s, 0x3500, 0xFFFF0);  //16 bit
    if (ok) ok = print_reg_safe(&p, end, s, 0x3503, 0xFF);
    if (ok) ok = print_reg_safe(&p, end, s, 0x350a, 0x3FF);   //10 bit
    if (ok) ok = print_reg_safe(&p, end, s, 0x350c, 0xFFFF);  //16 bit

    for (int reg = 0x5480; ok && reg <= 0x5490; reg++) {
      ok = print_reg_safe(&p, end, s, reg, 0xFF);
    }

    for (int reg = 0x5380; ok && reg <= 0x538b; reg++) {
      ok = print_reg_safe(&p, end, s, reg, 0xFF);
    }

    for (int reg = 0x5580; ok && reg < 0x558a; reg++) {
      ok = print_reg_safe(&p, end, s, reg, 0xFF);
    }
    if (ok) ok = print_reg_safe(&p, end, s, 0x558a, 0x1FF);  //9 bit
  } else if (s->id.PID == OV2640_PID) {
    if (ok) ok = print_reg_safe(&p, end, s, 0xd3, 0xFF);
    if (ok) ok = print_reg_safe(&p, end, s, 0x111, 0xFF);
    if (ok) ok = print_reg_safe(&p, end, s, 0x132, 0xFF);
  }

  if (ok) ok = status_json_append(&p, end, "\"xclk\":%u,", s->xclk_freq_hz / 1000000);
  if (ok) ok = status_json_append(&p, end, "\"pixformat\":%u,", s->pixformat);
  if (ok) ok = status_json_append(&p, end, "\"framesize\":%u,", s->status.framesize);
  if (ok) ok = status_json_append(&p, end, "\"quality\":%u,", s->status.quality);
  if (ok) ok = status_json_append(&p, end, "\"brightness\":%d,", s->status.brightness);
  if (ok) ok = status_json_append(&p, end, "\"contrast\":%d,", s->status.contrast);
  if (ok) ok = status_json_append(&p, end, "\"saturation\":%d,", s->status.saturation);
  if (ok) ok = status_json_append(&p, end, "\"sharpness\":%d,", s->status.sharpness);
  if (ok) ok = status_json_append(&p, end, "\"special_effect\":%u,", s->status.special_effect);
  if (ok) ok = status_json_append(&p, end, "\"wb_mode\":%u,", s->status.wb_mode);
  if (ok) ok = status_json_append(&p, end, "\"awb\":%u,", s->status.awb);
  if (ok) ok = status_json_append(&p, end, "\"awb_gain\":%u,", s->status.awb_gain);
  if (ok) ok = status_json_append(&p, end, "\"aec\":%u,", s->status.aec);
  if (ok) ok = status_json_append(&p, end, "\"aec2\":%u,", s->status.aec2);
  if (ok) ok = status_json_append(&p, end, "\"ae_level\":%d,", s->status.ae_level);
  if (ok) ok = status_json_append(&p, end, "\"aec_value\":%u,", s->status.aec_value);
  if (ok) ok = status_json_append(&p, end, "\"agc\":%u,", s->status.agc);
  if (ok) ok = status_json_append(&p, end, "\"agc_gain\":%u,", s->status.agc_gain);
  if (ok) ok = status_json_append(&p, end, "\"gainceiling\":%u,", s->status.gainceiling);
  if (ok) ok = status_json_append(&p, end, "\"bpc\":%u,", s->status.bpc);
  if (ok) ok = status_json_append(&p, end, "\"wpc\":%u,", s->status.wpc);
  if (ok) ok = status_json_append(&p, end, "\"raw_gma\":%u,", s->status.raw_gma);
  if (ok) ok = status_json_append(&p, end, "\"lenc\":%u,", s->status.lenc);
  if (ok) ok = status_json_append(&p, end, "\"hmirror\":%u,", s->status.hmirror);
  if (ok) ok = status_json_append(&p, end, "\"vflip\":%u,", s->status.vflip);
  if (ok) ok = status_json_append(&p, end, "\"dcw\":%u,", s->status.dcw);
  if (ok) ok = status_json_append(&p, end, "\"colorbar\":%u", s->status.colorbar);
#if defined(LED_GPIO_NUM)
  if (ok) ok = status_json_append(&p, end, ",\"led_intensity\":%u", led_duty);
#else
  if (ok) ok = status_json_append(&p, end, ",\"led_intensity\":%d", -1);
#endif
  uint32_t internal_free = (uint32_t)heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  uint32_t psram_free = (uint32_t)heap_caps_get_free_size(MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (ok) ok = status_json_append(&p, end, ",\"heap_internal_free_bytes\":%u", internal_free);
  if (ok) ok = status_json_append(&p, end, ",\"heap_psram_free_bytes\":%u", psram_free);

  if (!ok) {
    cam_mutex_give();
    httpd_resp_set_status(req, "500 Internal Server Error");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, "ERROR CAMERA_INTERNAL", HTTPD_RESP_USE_STRLEN);
    return ESP_FAIL;
  }

  *p++ = '}';
  *p++ = 0;
  cam_mutex_give();
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, json_response, strlen(json_response));
}

static esp_err_t xclk_handler(httpd_req_t *req) {
  char *buf = NULL;
  char _xclk[32];

  if (parse_get(req, &buf) != ESP_OK) {
    return ESP_FAIL;
  }
  if (httpd_query_key_value(buf, "xclk", _xclk, sizeof(_xclk)) != ESP_OK) {
    free(buf);
    httpd_resp_send_404(req);
    return ESP_FAIL;
  }
  free(buf);

  int xclk = atoi(_xclk);
  log_i("Set XCLK: %d MHz", xclk);

  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  sensor_t *s = esp_camera_sensor_get();
  int res = s->set_xclk(s, LEDC_TIMER_0, xclk);
  cam_mutex_give();
  if (res) {
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}

static esp_err_t reg_handler(httpd_req_t *req) {
  char *buf = NULL;
  char _reg[32];
  char _mask[32];
  char _val[32];

  if (parse_get(req, &buf) != ESP_OK) {
    return ESP_FAIL;
  }
  if (httpd_query_key_value(buf, "reg", _reg, sizeof(_reg)) != ESP_OK || httpd_query_key_value(buf, "mask", _mask, sizeof(_mask)) != ESP_OK
      || httpd_query_key_value(buf, "val", _val, sizeof(_val)) != ESP_OK) {
    free(buf);
    httpd_resp_send_404(req);
    return ESP_FAIL;
  }
  free(buf);

  int reg = atoi(_reg);
  int mask = atoi(_mask);
  int val = atoi(_val);
  log_i("Set Register: reg: 0x%02x, mask: 0x%02x, value: 0x%02x", reg, mask, val);

  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  sensor_t *s = esp_camera_sensor_get();
  int res = s->set_reg(s, reg, mask, val);
  cam_mutex_give();
  if (res) {
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}

static esp_err_t greg_handler(httpd_req_t *req) {
  char *buf = NULL;
  char _reg[32];
  char _mask[32];

  if (parse_get(req, &buf) != ESP_OK) {
    return ESP_FAIL;
  }
  if (httpd_query_key_value(buf, "reg", _reg, sizeof(_reg)) != ESP_OK || httpd_query_key_value(buf, "mask", _mask, sizeof(_mask)) != ESP_OK) {
    free(buf);
    httpd_resp_send_404(req);
    return ESP_FAIL;
  }
  free(buf);

  int reg = atoi(_reg);
  int mask = atoi(_mask);

  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  sensor_t *s = esp_camera_sensor_get();
  int res = s->get_reg(s, reg, mask);
  cam_mutex_give();
  if (res < 0) {
    return httpd_resp_send_500(req);
  }
  log_i("Get Register: reg: 0x%02x, mask: 0x%02x, value: 0x%02x", reg, mask, res);

  char buffer[20];
  const char *val = itoa(res, buffer, 10);
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, val, strlen(val));
}

static int parse_get_var(char *buf, const char *key, int def) {
  char _int[16];
  if (httpd_query_key_value(buf, key, _int, sizeof(_int)) != ESP_OK) {
    return def;
  }
  return atoi(_int);
}

static esp_err_t pll_handler(httpd_req_t *req) {
  char *buf = NULL;

  if (parse_get(req, &buf) != ESP_OK) {
    return ESP_FAIL;
  }

  int bypass = parse_get_var(buf, "bypass", 0);
  int mul = parse_get_var(buf, "mul", 0);
  int sys = parse_get_var(buf, "sys", 0);
  int root = parse_get_var(buf, "root", 0);
  int pre = parse_get_var(buf, "pre", 0);
  int seld5 = parse_get_var(buf, "seld5", 0);
  int pclken = parse_get_var(buf, "pclken", 0);
  int pclk = parse_get_var(buf, "pclk", 0);
  free(buf);

  log_i("Set Pll: bypass: %d, mul: %d, sys: %d, root: %d, pre: %d, seld5: %d, pclken: %d, pclk: %d", bypass, mul, sys, root, pre, seld5, pclken, pclk);

  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  sensor_t *s = esp_camera_sensor_get();
  int res = s->set_pll(s, bypass, mul, sys, root, pre, seld5, pclken, pclk);
  cam_mutex_give();
  if (res) {
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}

static esp_err_t win_handler(httpd_req_t *req) {
  char *buf = NULL;

  if (parse_get(req, &buf) != ESP_OK) {
    return ESP_FAIL;
  }

  int startX = parse_get_var(buf, "sx", 0);
  int startY = parse_get_var(buf, "sy", 0);
  int endX = parse_get_var(buf, "ex", 0);
  int endY = parse_get_var(buf, "ey", 0);
  int offsetX = parse_get_var(buf, "offx", 0);
  int offsetY = parse_get_var(buf, "offy", 0);
  int totalX = parse_get_var(buf, "tx", 0);
  int totalY = parse_get_var(buf, "ty", 0);  // codespell:ignore totaly
  int outputX = parse_get_var(buf, "ox", 0);
  int outputY = parse_get_var(buf, "oy", 0);
  bool scale = parse_get_var(buf, "scale", 0) == 1;
  bool binning = parse_get_var(buf, "binning", 0) == 1;
  free(buf);

  log_i(
    "Set Window: Start: %d %d, End: %d %d, Offset: %d %d, Total: %d %d, Output: %d %d, Scale: %u, Binning: %u", startX, startY, endX, endY, offsetX, offsetY,
    totalX, totalY, outputX, outputY, scale, binning  // codespell:ignore totaly
  );

  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  sensor_t *s = esp_camera_sensor_get();
  int res = s->set_res_raw(s, startX, startY, endX, endY, offsetX, offsetY, totalX, totalY, outputX, outputY, scale, binning);  // codespell:ignore totaly
  cam_mutex_give();
  if (res) {
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}

static esp_err_t index_handler(httpd_req_t *req) {
  if (!cam_mutex_take(req)) {
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Content-Encoding", "gzip");

  sensor_t *s = esp_camera_sensor_get();
  int pid = -1;
  if (s != NULL) {
    pid = s->id.PID;
  }
  cam_mutex_give();

  if (s != NULL) {
    if (pid == OV3660_PID) {
      return httpd_resp_send(req, (const char *)index_ov3660_html_gz, index_ov3660_html_gz_len);
    } else if (pid == OV5640_PID) {
      return httpd_resp_send(req, (const char *)index_ov5640_html_gz, index_ov5640_html_gz_len);
    } else {
      return httpd_resp_send(req, (const char *)index_ov2640_html_gz, index_ov2640_html_gz_len);
    }
  } else {
    log_e("Camera sensor not found");
    return httpd_resp_send_500(req);
  }
}

esp_err_t startCameraServer() {
  if (!s_cam_mutex) {
    s_cam_mutex = xSemaphoreCreateMutex();
    if (!s_cam_mutex) {
      log_e("Failed to create camera mutex");
      return ESP_FAIL;
    }
  }

  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.max_uri_handlers = 16;

  httpd_uri_t index_uri = {
    .uri = "/",
    .method = HTTP_GET,
    .handler = index_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t status_uri = {
    .uri = "/status",
    .method = HTTP_GET,
    .handler = status_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t cmd_uri = {
    .uri = "/control",
    .method = HTTP_GET,
    .handler = cmd_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t capture_uri = {
    .uri = "/capture",
    .method = HTTP_GET,
    .handler = capture_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t capture_fresh_uri = {
    .uri = "/capture_fresh",
    .method = HTTP_GET,
    .handler = capture_fresh_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t stream_uri = {
    .uri = "/stream",
    .method = HTTP_GET,
    .handler = stream_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t bmp_uri = {
    .uri = "/bmp",
    .method = HTTP_GET,
    .handler = bmp_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t xclk_uri = {
    .uri = "/xclk",
    .method = HTTP_GET,
    .handler = xclk_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t reg_uri = {
    .uri = "/reg",
    .method = HTTP_GET,
    .handler = reg_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t greg_uri = {
    .uri = "/greg",
    .method = HTTP_GET,
    .handler = greg_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t pll_uri = {
    .uri = "/pll",
    .method = HTTP_GET,
    .handler = pll_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  httpd_uri_t win_uri = {
    .uri = "/resolution",
    .method = HTTP_GET,
    .handler = win_handler,
    .user_ctx = NULL
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    .handle_ws_control_frames = false,
    .supported_subprotocol = NULL
#endif
  };

  ra_filter_init(&ra_filter, 20);

  // R04: a failed httpd_start or handler registration used to be swallowed
  // here, so setup() printed "Camera Ready" for a server that never listened.
  // Report the first failure and leave no half-open handle behind.
  const httpd_uri_t *camera_uris[] = {&index_uri, &cmd_uri, &status_uri, &capture_uri, &capture_fresh_uri, &bmp_uri,
                                      &xclk_uri,  &reg_uri, &greg_uri,   &pll_uri,     &win_uri};

  log_i("Starting web server on port: '%u'", config.server_port);
  esp_err_t err = httpd_start(&camera_httpd, &config);
  if (err != ESP_OK) {
    log_e("httpd_start failed for web server: 0x%x", err);
    camera_httpd = NULL;
    return err;
  }

  for (size_t i = 0; i < sizeof(camera_uris) / sizeof(camera_uris[0]); i++) {
    err = httpd_register_uri_handler(camera_httpd, camera_uris[i]);
    if (err != ESP_OK) {
      log_e("Failed to register '%s': 0x%x", camera_uris[i]->uri, err);
      httpd_stop(camera_httpd);
      camera_httpd = NULL;
      return err;
    }
  }

  config.server_port += 1;
  config.ctrl_port += 1;
  log_i("Starting stream server on port: '%u'", config.server_port);
  err = httpd_start(&stream_httpd, &config);
  if (err != ESP_OK) {
    log_e("httpd_start failed for stream server: 0x%x", err);
    stream_httpd = NULL;
    httpd_stop(camera_httpd);
    camera_httpd = NULL;
    return err;
  }

  err = httpd_register_uri_handler(stream_httpd, &stream_uri);
  if (err != ESP_OK) {
    log_e("Failed to register '%s': 0x%x", stream_uri.uri, err);
    httpd_stop(stream_httpd);
    stream_httpd = NULL;
    httpd_stop(camera_httpd);
    camera_httpd = NULL;
    return err;
  }

  return ESP_OK;
}

void setupLedFlash() {
#if defined(LED_GPIO_NUM)
  ledcAttach(LED_GPIO_NUM, 5000, 8);
#else
  log_i("LED flash is disabled -> LED_GPIO_NUM undefined");
#endif
}
