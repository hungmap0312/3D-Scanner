#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>

// ===========================
// Select camera model in board_config.h
// ===========================
#include "board_config.h"

// ===========================
// WiFi credentials
// ===========================
// Gia tri that nam trong secrets.h, tep do duoc .gitignore bo qua.
// Chua co secrets.h thi chep secrets.h.example thanh secrets.h roi dien.
#include "secrets.h"

// R03: bound the Wi-Fi wait instead of blocking forever.
static const uint32_t WIFI_CONNECT_TIMEOUT_MS = 20000;
static const uint32_t WIFI_RETRY_INTERVAL_MS = 10000;

// R04: startCameraServer() now reports whether the HTTP servers came up.
esp_err_t startCameraServer();
void setupLedFlash();

// D043: Boot ID initialization for /capture_fresh
void fresh_capture_init_boot_id();
const char* fresh_capture_get_boot_id();

static bool cameraReady = false;
static bool serverStarted = false;

// R03: wait for Wi-Fi with a deadline. Returns true only when connected.
static bool connectWiFi(uint32_t timeoutMs) {
  // An earlier attempt can leave the station in "connecting" state, and
  // WiFi.begin() then fails with "wifi:sta is connecting, cannot set config"
  // so the retry never takes effect. Observed on the board on 2026-09-16
  // while testing the R03 timeout. Drop the pending attempt first.
  WiFi.disconnect(false, false);
  delay(100);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  Serial.print("WiFi connecting");
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - started) < timeoutMs) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");

  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("WiFi connect FAILED after %u ms, status=%d\n", (unsigned)timeoutMs, (int)WiFi.status());
    return false;
  }
  Serial.print("WiFi connected, IP ");
  Serial.println(WiFi.localIP());
  return true;
}

// R04: only announce readiness after the servers actually started.
static void startServerAndReport() {
  fresh_capture_init_boot_id();
  esp_err_t err = startCameraServer();
  if (err != ESP_OK) {
    serverStarted = false;
    Serial.printf("HTTP server FAILED to start: 0x%x. Camera is not reachable over the network.\n", (unsigned)err);
    return;
  }
  serverStarted = true;
  Serial.printf("Boot ID: %s\n", fresh_capture_get_boot_id());
  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.printf("Flash: %u MB\n",
              (unsigned)(ESP.getFlashChipSize() / 1048576));

  Serial.printf("PSRAM: %u KB\n",
              (unsigned)(ESP.getPsramSize() / 1024));
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG;  // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  // D043 / SPEC §10: chot fb_count = 1, grab_mode = CAMERA_GRAB_LATEST
  if (config.pixel_format == PIXFORMAT_JPEG) {
    if (psramFound()) {
      config.jpeg_quality = 10;
      config.fb_count = 1;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  Serial.printf("Camera Init OK: fb_count=%d, grab_mode=%d, fb_location=%d\n",
                config.fb_count, (int)config.grab_mode, (int)config.fb_location);

  sensor_t *s = esp_camera_sensor_get();
  Serial.printf("Camera PID: 0x%04X\n", (unsigned)s->id.PID);
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  }
  // drop down frame size for higher initial frame rate
  if (config.pixel_format == PIXFORMAT_JPEG) {
    s->set_framesize(s, FRAMESIZE_QVGA);
  }

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

#if defined(CAMERA_MODEL_ESP32S3_EYE)
  s->set_vflip(s, 1);
#endif

// Setup LED FLash if LED pin is defined in camera_pins.h
#if defined(LED_GPIO_NUM)
  setupLedFlash();
#endif

  cameraReady = true;

  if (connectWiFi(WIFI_CONNECT_TIMEOUT_MS)) {
    startServerAndReport();
  } else {
    Serial.println("No network yet. Camera is initialised; loop() keeps retrying Wi-Fi.");
  }
}

void loop() {
  if (!cameraReady) {
    // Camera init failed in setup(); there is nothing to serve.
    delay(10000);
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    // R04: if the servers never came up, try again now that we have a link.
    if (!serverStarted) {
      startServerAndReport();
    }
    delay(1000);
    return;
  }

  // R03: link is down. Keep the running servers as they are and retry the
  // connection; the httpd handles stay valid across a Wi-Fi drop.
  delay(WIFI_RETRY_INTERVAL_MS);
  Serial.println("WiFi not connected, retrying");
  connectWiFi(WIFI_CONNECT_TIMEOUT_MS);
}
