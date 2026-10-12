// Tester C5a Q6: API ESP-IDF/FreeRTOS/esp32-camera gia, du de bien dich NGUYEN VAN cac
// handler trich tu app_httpd.cpp tren may tinh (MinGW g++). Khong phai firmware that:
// khong co Wi-Fi, khong co DMA, dong ho do test dieu khien. Xem test/README.md.
#ifndef FAKE_ESP_H
#define FAKE_ESP_H

// MinGW: PRIu32 trong C++ can macro nay; %llu can stdio C99 (bien dich them -D_ISOC99_SOURCE)
#ifndef __STDC_FORMAT_MACROS
#define __STDC_FORMAT_MACROS 1
#endif
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <sys/types.h>
#include <sys/time.h>
#include <string>
#include <vector>
#include <utility>

typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_HTTPD_RESP_HDR 0xb005
#define ESP_ERR_HTTPD_RESP_SEND 0xb006
#define ESP_ERR_NOT_FOUND 0x105

// log: muc thap de cac khoi `#if ARDUHAL_LOG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO` bi bo qua
#define ARDUHAL_LOG_LEVEL_INFO 3
#define ARDUHAL_LOG_LEVEL 0
#define log_e(...) ((void)0)
#define log_i(...) ((void)0)
#define log_w(...) ((void)0)

// FreeRTOS
typedef uint32_t TickType_t;
typedef int BaseType_t;
#define pdTRUE 1
#define pdFALSE 0
#define portTICK_PERIOD_MS 1
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
struct FakeSem;
typedef FakeSem *SemaphoreHandle_t;
SemaphoreHandle_t xSemaphoreCreateMutex(void);
BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t ticks);
BaseType_t xSemaphoreGive(SemaphoreHandle_t s);
void vTaskDelay(TickType_t ticks);

// esp_timer / esp_random
int64_t esp_timer_get_time(void);
void esp_fill_random(void *buf, size_t len);

// esp32-camera
typedef enum { PIXFORMAT_RGB565, PIXFORMAT_YUV422, PIXFORMAT_YUV420, PIXFORMAT_GRAYSCALE, PIXFORMAT_JPEG } pixformat_t;
typedef struct {
  uint8_t *buf;
  size_t len;
  size_t width;
  size_t height;
  pixformat_t format;
  struct timeval timestamp;
} camera_fb_t;
camera_fb_t *esp_camera_fb_get(void);
void esp_camera_fb_return(camera_fb_t *fb);

typedef enum { LEDC_TIMER_0 = 0 } ledc_timer_t;
// camera_status_t: dung kieu truong cua esp32-camera (sensor.h trong esp32s3-libs 3.3.11) de do dai so
// in ra /status khop bo that (vd. int8_t am, uint16_t aec_value)
typedef enum { FRAMESIZE_96X96 = 0, FRAMESIZE_INVALID = 30 } framesize_t;
typedef struct {
  framesize_t framesize;
  bool scale;
  bool binning;
  uint8_t quality;
  int8_t brightness;
  int8_t contrast;
  int8_t saturation;
  int8_t sharpness;
  uint8_t denoise;
  uint8_t special_effect;
  uint8_t wb_mode;
  uint8_t awb;
  uint8_t awb_gain;
  uint8_t aec;
  uint8_t aec2;
  int8_t ae_level;
  uint16_t aec_value;
  uint8_t agc;
  uint8_t agc_gain;
  uint8_t gainceiling;
  uint8_t bpc;
  uint8_t wpc;
  uint8_t raw_gma;
  uint8_t lenc;
  uint8_t hmirror;
  uint8_t vflip;
  uint8_t dcw;
  uint8_t colorbar;
} camera_status_t;
typedef struct _sensor sensor_t;
struct _sensor {
  struct { uint16_t PID; } id;
  pixformat_t pixformat;
  camera_status_t status;
  int xclk_freq_hz;
  int (*set_xclk)(sensor_t *s, int timer, int xclk);
  int (*get_reg)(sensor_t *s, int reg, int mask);
};
sensor_t *esp_camera_sensor_get(void);
#define OV2640_PID 0x26
#define OV3660_PID 0x3660
#define OV5640_PID 0x5640

// esp_heap_caps (gia tri mask nhu esp_heap_caps.h cua esp32s3-libs 3.3.11)
#define MALLOC_CAP_8BIT (1 << 2)
#define MALLOC_CAP_SPIRAM (1 << 10)
#define MALLOC_CAP_INTERNAL (1 << 11)
size_t heap_caps_get_free_size(uint32_t caps);
extern const unsigned char index_ov2640_html_gz[];
extern const unsigned char index_ov3660_html_gz[];
extern const unsigned char index_ov5640_html_gz[];
extern const size_t index_ov2640_html_gz_len;
extern const size_t index_ov3660_html_gz_len;
extern const size_t index_ov5640_html_gz_len;

// LED (chi dung khi bien dich bien the -DLED_GPIO_NUM=...)
void ledcWrite(int pin, uint32_t duty);

// img_converters
typedef size_t (*jpg_out_cb)(void *arg, size_t index, const void *data, size_t len);
bool frame2bmp(camera_fb_t *fb, uint8_t **out, size_t *out_len);
bool frame2jpg(camera_fb_t *fb, uint8_t quality, uint8_t **out, size_t *out_len);
bool frame2jpg_cb(camera_fb_t *fb, uint8_t quality, jpg_out_cb cb, void *arg);

// esp_http_server: moi request ghi lai status/header/body de test doi chieu
typedef void *httpd_handle_t;
#define HTTPD_RESP_USE_STRLEN -1
struct httpd_req {
  std::string status;                                     // "" = mac dinh 200 OK
  std::string type;
  std::vector<std::pair<std::string, std::string> > hdrs;
  std::string body;
  int n_send;           // so lan gui tron mot response (httpd_resp_send / send_500 / send_404)
  int n_chunks;         // so chunk khac rong
  int hdr_calls;
  const char *fail_hdr_name;  // set_hdr voi ten nay tra ESP_ERR_HTTPD_RESP_HDR (vd. vuot max_resp_headers)
  bool fail_send;       // httpd_resp_send tra loi (vd. client dong ket noi)
  int chunk_fail_after; // >=0: chunk khac rong thu (n+1) tra loi -> stream ket thuc
  void *chunk_block;    // HANDLE: chunk dau tien cho su kien nay truoc khi tra (stream dang giu)
  void *chunk_entered;  // HANDLE: bao hieu da vao chunk dau tien
  const char *query;
  httpd_req()
      : n_send(0), n_chunks(0), hdr_calls(0), fail_hdr_name(0), fail_send(false),
        chunk_fail_after(-1), chunk_block(0), chunk_entered(0), query(0) {}
};
typedef struct httpd_req httpd_req_t;
esp_err_t httpd_resp_set_status(httpd_req_t *r, const char *status);
esp_err_t httpd_resp_set_type(httpd_req_t *r, const char *type);
esp_err_t httpd_resp_set_hdr(httpd_req_t *r, const char *field, const char *value);
esp_err_t httpd_resp_send(httpd_req_t *r, const char *buf, ssize_t len);
esp_err_t httpd_resp_send_chunk(httpd_req_t *r, const char *buf, ssize_t len);
esp_err_t httpd_resp_send_500(httpd_req_t *r);
esp_err_t httpd_resp_send_404(httpd_req_t *r);
size_t httpd_req_get_url_query_len(httpd_req_t *r);
esp_err_t httpd_req_get_url_query_str(httpd_req_t *r, char *buf, size_t len);
esp_err_t httpd_query_key_value(const char *qry, const char *key, char *val, size_t val_size);

// Tiem loi bo dinh dang: chi doan ma trich (app_httpd_extract.inc) thay vsnprintf bang ham gia; harness
// #undef ngay sau khi include doan trich. Mac dinh ham gia goi vsnprintf that (khong doi hanh vi).
int fake_vsnprintf(char *buf, size_t n, const char *fmt, va_list ap);
#define vsnprintf fake_vsnprintf

#endif  // FAKE_ESP_H
