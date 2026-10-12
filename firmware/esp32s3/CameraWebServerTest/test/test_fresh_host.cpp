// Tester C5a Q6 - harness may tinh cho /capture_fresh va khoa camera (01_PLAN Vong 5 muc 5, Q6-T1..T5).
//
// `app_httpd_extract.inc` do pc/test_c5a_runtime.py sinh ra: chep NGUYEN VAN cac doan cua
// firmware/esp32s3/CameraWebServerTest/app_httpd.cpp tai commit dang kiem (bien/khoa/boot ID,
// bmp/capture/capture_fresh/stream, parse_get, xclk, index). Harness khong viet lai thuat toan;
// chi gia lap API ESP-IDF (test/fake_esp.h) va doi chieu ket qua voi ke hoach.
//
// Ky vong lay tu 01_PLAN.md Vong 5 muc 4-5 (khong lay tu ma). Mot dong FAIL la mot sai lech.
// Vong 6 (V6-T1..T3): them status_handler that (truong heap, kiem bien JSON, tranh chap); dong
// "  @JSON <ma> <body>" de pc/test_c5a_runtime.py doi chieu JSON bang parser that.
// Khong phai thu tren bo: khong co DMA, Wi-Fi, lap lich FreeRTOS that.
#include "fake_esp.h"
#include "app_httpd_extract.inc"
#undef vsnprintf

#include <windows.h>
#include <stdarg.h>
#include <limits.h>
#include <deque>
#include <map>
#include <set>

// ---------------------------------------------------------------- gia lap he thong
static CRITICAL_SECTION g_cs;
static int64_t g_now = 10000000;  // us, chi tang khi esp_camera_fb_get() "chan"

int64_t esp_timer_get_time(void) {
  EnterCriticalSection(&g_cs);
  int64_t v = g_now;
  LeaveCriticalSection(&g_cs);
  return v;
}
static void clock_set(int64_t v) {
  EnterCriticalSection(&g_cs);
  g_now = v;
  LeaveCriticalSection(&g_cs);
}

static uint32_t g_rng = 0x9e3779b9u;
void esp_fill_random(void *buf, size_t len) {
  uint8_t *p = (uint8_t *)buf;
  for (size_t i = 0; i < len; i++) {
    g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5;
    p[i] = (uint8_t)(g_rng >> 11);
  }
}

struct FakeSem {
  HANDLE h;
  volatile LONG owner;
  volatile LONG takes, gives, bad_gives;
};
SemaphoreHandle_t xSemaphoreCreateMutex(void) {
  FakeSem *s = new FakeSem();
  s->h = CreateSemaphore(NULL, 1, 1, NULL);  // nhi phan, KHONG de quy nhu mutex FreeRTOS lay lai
  s->owner = 0; s->takes = s->gives = s->bad_gives = 0;
  return s;
}
BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t ticks) {
  if (WaitForSingleObject(s->h, ticks) == WAIT_OBJECT_0) {
    InterlockedExchange(&s->owner, (LONG)GetCurrentThreadId());
    InterlockedIncrement(&s->takes);
    return pdTRUE;
  }
  return pdFALSE;
}
BaseType_t xSemaphoreGive(SemaphoreHandle_t s) {
  if ((DWORD)s->owner != GetCurrentThreadId()) {  // FreeRTOS: chi task dang giu moi nha duoc mutex
    InterlockedIncrement(&s->bad_gives);
    return pdFALSE;
  }
  InterlockedExchange(&s->owner, 0);
  InterlockedIncrement(&s->gives);
  ReleaseSemaphore(s->h, 1, NULL);
  return pdTRUE;
}
void vTaskDelay(TickType_t ticks) { Sleep(ticks); }
void ledcWrite(int, uint32_t) {}

// ---------------------------------------------------------------- driver camera gia
struct FrameSpec {
  int64_t delay_us;  // thoi gian esp_camera_fb_get() "chan" (dong ho tang chung ay)
  bool is_null;
  bool ts_now;       // timestamp = dong ho luc tra khung (khung moi)
  int64_t ts_us;     // dung khi ts_now = false
  pixformat_t fmt;
  HANDLE block, entered;
  FrameSpec() : delay_us(33000), is_null(false), ts_now(true), ts_us(0), fmt(PIXFORMAT_JPEG), block(0), entered(0) {}
};
static std::deque<FrameSpec> g_script;
static std::map<camera_fb_t *, DWORD> g_out;  // buffer dang bi giu -> thread
static std::set<camera_fb_t *> g_returned;
static int g_gets = 0, g_returns = 0, g_bad_returns = 0, g_null_returns = 0;
static int g_unlocked_get = 0, g_overlap = 0, g_unlocked_sensor = 0, g_sensor_calls = 0;
static const uint8_t JPEG_BYTES[] = {0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 'J', 'F', 'I', 'F', 0x00, 0x01, 0x01, 0x00,
                                     0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9};
static DWORD sem_owner() { return s_cam_mutex ? (DWORD)s_cam_mutex->owner : 0; }

static FrameSpec F_stale(int64_t ts, int64_t delay = 33000) { FrameSpec f; f.ts_now = false; f.ts_us = ts; f.delay_us = delay; return f; }
static FrameSpec F_fresh(int64_t delay = 33000) { FrameSpec f; f.delay_us = delay; return f; }
static FrameSpec F_null(int64_t delay) { FrameSpec f; f.is_null = true; f.delay_us = delay; return f; }

camera_fb_t *esp_camera_fb_get(void) {
  EnterCriticalSection(&g_cs);
  FrameSpec sp;
  if (!g_script.empty()) { sp = g_script.front(); g_script.pop_front(); }
  DWORD me = GetCurrentThreadId();
  g_gets++;
  if (s_cam_mutex && sem_owner() != me) g_unlocked_get++;
  for (std::map<camera_fb_t *, DWORD>::iterator it = g_out.begin(); it != g_out.end(); ++it)
    if (it->second != me) g_overlap++;
  LeaveCriticalSection(&g_cs);
  if (sp.entered) SetEvent(sp.entered);
  if (sp.block) WaitForSingleObject(sp.block, 10000);
  EnterCriticalSection(&g_cs);
  g_now += sp.delay_us;
  int64_t now = g_now;
  camera_fb_t *fb = NULL;
  if (!sp.is_null) {
    fb = new camera_fb_t();
    fb->len = sizeof(JPEG_BYTES);
    fb->buf = new uint8_t[fb->len];
    memcpy(fb->buf, JPEG_BYTES, fb->len);
    fb->format = sp.fmt;
    int64_t ts = sp.ts_now ? now : sp.ts_us;
    fb->timestamp.tv_sec = (long)(ts / 1000000);
    fb->timestamp.tv_usec = (long)(ts % 1000000);
    g_out[fb] = me;
  }
  LeaveCriticalSection(&g_cs);
  return fb;
}
void esp_camera_fb_return(camera_fb_t *fb) {
  EnterCriticalSection(&g_cs);
  if (!fb) g_null_returns++;
  else if (!g_out.count(fb)) g_bad_returns++;  // tra 2 lan hoac tra buffer la
  else { g_out.erase(fb); g_returned.insert(fb); g_returns++; }  // khong free: bat duoc dung sau khi tra
  LeaveCriticalSection(&g_cs);
}

static int fake_set_xclk(sensor_t *, int, int) {
  EnterCriticalSection(&g_cs);
  g_sensor_calls++;
  if (s_cam_mutex && sem_owner() != GetCurrentThreadId()) g_unlocked_sensor++;
  LeaveCriticalSection(&g_cs);
  return 0;
}
// get_reg: gia tri tat dinh theo reg/mask; che do cuc tri tra INT_MIN (chuoi %d dai nhat)
static bool g_reg_extreme = false;
static int g_get_reg_calls = 0;
static int fake_get_reg(sensor_t *, int reg, int mask) {
  EnterCriticalSection(&g_cs);
  g_get_reg_calls++;
  if (s_cam_mutex && sem_owner() != GetCurrentThreadId()) g_unlocked_sensor++;
  LeaveCriticalSection(&g_cs);
  return g_reg_extreme ? INT_MIN : (((reg * 7) ^ mask) & 0xFFFF);
}
static sensor_t g_sensor;
// gia tri sensor binh thuong: trung profile cam_SVGA_q20_20260928 o cac control co trong /status
static void sensor_defaults(uint16_t pid) {
  memset(&g_sensor, 0, sizeof(g_sensor));
  g_sensor.id.PID = pid;
  g_sensor.pixformat = PIXFORMAT_JPEG;
  g_sensor.xclk_freq_hz = 20000000;
  camera_status_t &st = g_sensor.status;
  st.framesize = (framesize_t)11; st.quality = 20; st.brightness = 1; st.contrast = 0; st.saturation = -2;
  st.sharpness = 0; st.special_effect = 0; st.wb_mode = 2; st.awb = 1; st.awb_gain = 1; st.aec = 0; st.aec2 = 0;
  st.ae_level = 0; st.aec_value = 783; st.agc = 0; st.agc_gain = 8; st.gainceiling = 0; st.bpc = 0; st.wpc = 1;
  st.raw_gma = 1; st.lenc = 1; st.hmirror = 0; st.vflip = 1; st.dcw = 1; st.colorbar = 0;
  g_sensor.set_xclk = fake_set_xclk;
  g_sensor.get_reg = fake_get_reg;
  g_reg_extreme = false;
}
// moi truong so in ra dai nhat theo kieu that (int8 -128, uint8 255, uint16 65535, reg INT_MIN)
static void sensor_extreme(uint16_t pid) {
  sensor_defaults(pid);
  g_sensor.xclk_freq_hz = INT_MAX;
  g_sensor.pixformat = (pixformat_t)4;
  camera_status_t &st = g_sensor.status;
  st.framesize = FRAMESIZE_INVALID; st.quality = 255; st.brightness = -128; st.contrast = -128; st.saturation = -128;
  st.sharpness = -128; st.special_effect = 255; st.wb_mode = 255; st.awb = 255; st.awb_gain = 255; st.aec = 255;
  st.aec2 = 255; st.ae_level = -128; st.aec_value = 65535; st.agc = 255; st.agc_gain = 255; st.gainceiling = 255;
  st.bpc = 255; st.wpc = 255; st.raw_gma = 255; st.lenc = 255; st.hmirror = 255; st.vflip = 255; st.dcw = 255;
  st.colorbar = 255;
  g_reg_extreme = true;
}
sensor_t *esp_camera_sensor_get(void) {
  EnterCriticalSection(&g_cs);
  g_sensor_calls++;
  if (s_cam_mutex && sem_owner() != GetCurrentThreadId()) g_unlocked_sensor++;
  LeaveCriticalSection(&g_cs);
  return &g_sensor;
}
const unsigned char index_ov2640_html_gz[] = {0x1f, 0x8b, 0x08, 0x00};
const unsigned char index_ov3660_html_gz[] = {0x1f, 0x8b, 0x08, 0x01};
const unsigned char index_ov5640_html_gz[] = {0x1f, 0x8b, 0x08, 0x02};
const size_t index_ov2640_html_gz_len = 4, index_ov3660_html_gz_len = 4, index_ov5640_html_gz_len = 4;

static bool g_bmp_fail = false;
bool frame2bmp(camera_fb_t *fb, uint8_t **out, size_t *out_len) {
  if (g_bmp_fail) return false;
  *out = (uint8_t *)malloc(fb->len + 2);
  (*out)[0] = 'B'; (*out)[1] = 'M';
  memcpy(*out + 2, fb->buf, fb->len);
  *out_len = fb->len + 2;
  return true;
}
bool frame2jpg(camera_fb_t *fb, uint8_t, uint8_t **out, size_t *out_len) {
  *out = (uint8_t *)malloc(fb->len); memcpy(*out, fb->buf, fb->len); *out_len = fb->len; return true;
}
bool frame2jpg_cb(camera_fb_t *fb, uint8_t, jpg_out_cb cb, void *arg) { return cb(arg, 0, fb->buf, fb->len) == fb->len; }

// ---------------------------------------------------------------- heap / bo dinh dang gia (Vong 6)
static uint32_t g_heap_int = 123456, g_heap_ps = 654321;
static int g_heap_int_calls = 0, g_heap_ps_calls = 0, g_heap_bad_mask = 0;
size_t heap_caps_get_free_size(uint32_t caps) {
  if (caps == (MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)) { g_heap_int_calls++; return g_heap_int; }
  if (caps == (MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)) { g_heap_ps_calls++; return g_heap_ps; }
  g_heap_bad_mask++;  // mask khac ke hoach (vd. chi 8BIT) -> so khac han de lo ra
  return 7777777;
}
// fake_vsnprintf: chi doan ma trich goi (macro trong fake_esp.h). Lan goi thu g_vsn_fail_at tra -1 (loi
// bo dinh dang); lan thu g_vsn_trunc_at ghi cat cut va tra >= n (het cho). 0 = khong tiem.
static int g_vsn_calls = 0, g_vsn_fail_at = 0, g_vsn_trunc_at = 0;
int fake_vsnprintf(char *buf, size_t n, const char *f, va_list ap) {
  g_vsn_calls++;
  if (g_vsn_fail_at && g_vsn_calls == g_vsn_fail_at) return -1;
  int r = vsnprintf(buf, n, f, ap);
  if (g_vsn_trunc_at && g_vsn_calls == g_vsn_trunc_at) return r > (int)n ? r : (int)n;
  return r;
}

// ---------------------------------------------------------------- esp_http_server gia
esp_err_t httpd_resp_set_status(httpd_req_t *r, const char *s) { r->status = s; return ESP_OK; }
esp_err_t httpd_resp_set_type(httpd_req_t *r, const char *t) { r->type = t; return ESP_OK; }
esp_err_t httpd_resp_set_hdr(httpd_req_t *r, const char *f, const char *v) {
  r->hdr_calls++;
  if (r->fail_hdr_name && !strcmp(f, r->fail_hdr_name)) return ESP_ERR_HTTPD_RESP_HDR;
  r->hdrs.push_back(std::make_pair(std::string(f), std::string(v)));
  return ESP_OK;
}
esp_err_t httpd_resp_send(httpd_req_t *r, const char *buf, ssize_t len) {
  if (len == HTTPD_RESP_USE_STRLEN) len = buf ? (ssize_t)strlen(buf) : 0;
  r->n_send++;
  if (r->fail_send) return ESP_ERR_HTTPD_RESP_SEND;
  r->body.assign(buf ? buf : "", buf ? (size_t)len : 0);
  return ESP_OK;
}
esp_err_t httpd_resp_send_chunk(httpd_req_t *r, const char *buf, ssize_t len) {
  if (len == HTTPD_RESP_USE_STRLEN) len = buf ? (ssize_t)strlen(buf) : 0;
  if (!buf || len == 0) { r->n_send++; return ESP_OK; }
  r->n_chunks++;
  if (r->n_chunks == 1 && r->chunk_entered) SetEvent((HANDLE)r->chunk_entered);
  if (r->n_chunks == 1 && r->chunk_block) WaitForSingleObject((HANDLE)r->chunk_block, 10000);
  if (r->chunk_fail_after >= 0 && r->n_chunks > r->chunk_fail_after) return ESP_FAIL;  // client dong
  r->body.append(buf, (size_t)len);
  return ESP_OK;
}
esp_err_t httpd_resp_send_500(httpd_req_t *r) { r->status = "500 Internal Server Error"; return httpd_resp_send(r, "500 Internal Server Error", -1); }
esp_err_t httpd_resp_send_404(httpd_req_t *r) { r->status = "404 Not Found"; return httpd_resp_send(r, "404 Not Found", -1); }
size_t httpd_req_get_url_query_len(httpd_req_t *r) { return r->query ? strlen(r->query) : 0; }
esp_err_t httpd_req_get_url_query_str(httpd_req_t *r, char *buf, size_t len) {
  if (!r->query || strlen(r->query) + 1 > len) return ESP_FAIL;
  strcpy(buf, r->query); return ESP_OK;
}
esp_err_t httpd_query_key_value(const char *q, const char *key, char *val, size_t n) {
  size_t kl = strlen(key);
  for (const char *p = q; p && *p;) {
    const char *amp = strchr(p, '&');
    size_t seg = amp ? (size_t)(amp - p) : strlen(p);
    if (seg > kl && !strncmp(p, key, kl) && p[kl] == '=') {
      size_t vl = seg - kl - 1;
      if (vl + 1 > n) return ESP_FAIL;
      memcpy(val, p + kl + 1, vl); val[vl] = 0; return ESP_OK;
    }
    p = amp ? amp + 1 : NULL;
  }
  return ESP_ERR_NOT_FOUND;
}

// ---------------------------------------------------------------- tien ich kiem
static int g_pass = 0, g_fail = 0;
static void check(const char *id, bool ok, const char *title, const std::string &detail) {
  printf("  [%s] %s %s | %s\n", ok ? "PASS" : "FAIL", id, title, detail.c_str());
  fflush(stdout);
  if (ok) g_pass++; else g_fail++;
}
static std::string fmt(const char *f, ...) {
  char b[1024]; va_list ap; va_start(ap, f); vsnprintf(b, sizeof b, f, ap); va_end(ap); return b;
}
static int code_of(const httpd_req_t &r) { return r.status.empty() ? 200 : atoi(r.status.c_str()); }
static int hdr_count(const httpd_req_t &r, const char *n) {
  int c = 0;
  for (size_t i = 0; i < r.hdrs.size(); i++) if (!_stricmp(r.hdrs[i].first.c_str(), n)) c++;
  return c;
}
static std::string hdr(const httpd_req_t &r, const char *n) {
  for (size_t i = 0; i < r.hdrs.size(); i++) if (!_stricmp(r.hdrs[i].first.c_str(), n)) return r.hdrs[i].second;
  return "";
}
static bool parse_ts(const std::string &s, int64_t *us) {  // <sec>.<6 chu so>, so nguyen
  size_t d = s.find('.');
  if (d == std::string::npos || d == 0 || s.size() - d - 1 != 6) return false;
  for (size_t i = 0; i < s.size(); i++) if (i != d && (s[i] < '0' || s[i] > '9')) return false;
  *us = (int64_t)strtoull(s.substr(0, d).c_str(), 0, 10) * 1000000 + atoi(s.substr(d + 1).c_str());
  return true;
}
static const char *HDR5[] = {"X-Frame-Id", "X-Boot-Id", "X-Timestamp", "X-Request-Timestamp", "X-Discarded-Frames"};

struct Snap { int gets, returns, bad, nullret, takes, gives, badg; size_t out; };
static Snap snap() {
  EnterCriticalSection(&g_cs);
  Snap s = {g_gets, g_returns, g_bad_returns, g_null_returns, (int)s_cam_mutex->takes, (int)s_cam_mutex->gives,
            (int)s_cam_mutex->bad_gives, g_out.size()};
  LeaveCriticalSection(&g_cs);
  return s;
}
// so lieu mot request: ket qua, so lan lay/tra buffer, can bang khoa
struct Run {
  httpd_req_t r; esp_err_t ret; int gets, returns; bool balanced; std::string why;
};
static Run run_handler(esp_err_t (*h)(httpd_req_t *), httpd_req_t req = httpd_req_t()) {
  Run x; x.r = req;
  Snap a = snap();
  x.ret = h(&x.r);
  Snap b = snap();
  x.gets = b.gets - a.gets; x.returns = b.returns - a.returns;
  bool every_fb_back = b.out == a.out && b.bad == a.bad && b.nullret == a.nullret;
  bool lock_ok = (b.takes - a.takes) == (b.gives - a.gives) && b.badg == a.badg && sem_owner() == 0;
  x.balanced = every_fb_back && lock_ok;
  x.why = fmt("get=%d return=%d con_giu=%u tra_sai=%d tra_NULL=%d khoa take/give=%d/%d nha_sai=%d n_send=%d",
              x.gets, x.returns, (unsigned)b.out, b.bad - a.bad, b.nullret - a.nullret, b.takes - a.takes,
              b.gives - a.gives, b.badg - a.badg, x.r.n_send);
  return x;
}
static Run fresh_at(int64_t t0, const std::vector<FrameSpec> &frames, httpd_req_t req = httpd_req_t()) {
  clock_set(t0);
  g_script.clear();
  for (size_t i = 0; i < frames.size(); i++) g_script.push_back(frames[i]);
  return run_handler(capture_fresh_handler, req);
}
static std::string brief(const Run &x) {
  return fmt("HTTP %d '%s' type=%s id=%s disc=%s; %s", code_of(x.r), x.r.type == "image/jpeg" ? "<jpeg>" : x.r.body.c_str(),
             x.r.type.c_str(), hdr(x.r, "X-Frame-Id").c_str(), hdr(x.r, "X-Discarded-Frames").c_str(), x.why.c_str());
}
static bool is_err(const Run &x, int code, const char *body) {
  return code_of(x.r) == code && x.r.body == body && x.r.type != "image/jpeg" && x.r.n_send == 1;
}
static uint64_t last_id = 0;
static bool ok_jpeg(const Run &x) {
  bool five = true;
  for (int i = 0; i < 5; i++) five = five && hdr_count(x.r, HDR5[i]) == 1;
  return code_of(x.r) == 200 && x.r.type == "image/jpeg" && five && x.r.n_send == 1 &&
         x.r.body == std::string((const char *)JPEG_BYTES, sizeof(JPEG_BYTES));
}
static uint64_t id_of(const Run &x) { return strtoull(hdr(x.r, "X-Frame-Id").c_str(), 0, 10); }

// ---------------------------------------------------------------- luong cho test tranh chap
struct ThreadArg { esp_err_t (*h)(httpd_req_t *); httpd_req_t *req; esp_err_t ret; };
static DWORD WINAPI thread_main(LPVOID p) { ThreadArg *a = (ThreadArg *)p; a->ret = a->h(a->req); return 0; }

int main() {
  InitializeCriticalSection(&g_cs);
#if defined(LED_GPIO_NUM)
  printf("== Bien the CO LED (LED_GPIO_NUM=%d)\n", (int)LED_GPIO_NUM);
#else
  printf("== Bien the KHONG LED (dung cau hinh CAMERA_MODEL_ESP32S3_EYE cua bo)\n");
#endif
  s_cam_mutex = xSemaphoreCreateMutex();  // startCameraServer() tao truoc khi nhan request
  sensor_defaults(OV3660_PID);
  int64_t T = 10000000;

  // ---- Q6-T1: 20 luot binh thuong
  fresh_capture_init_boot_id();
  std::string boot = fresh_capture_get_boot_id();
  bool hexok = boot.size() == 32;
  for (size_t i = 0; i < boot.size(); i++) hexok = hexok && ((boot[i] >= '0' && boot[i] <= '9') || (boot[i] >= 'a' && boot[i] <= 'f'));
  fresh_capture_init_boot_id();
  check("H01", hexok && boot == fresh_capture_get_boot_id(), "Boot ID 32 hex thuong, goi init lan 2 khong doi",
        fmt("boot=%s", boot.c_str()));
  bool all = true; std::string first_bad;
  for (int i = 1; i <= 20; i++) {
    T += 1000000;
    Run x = fresh_at(T, std::vector<FrameSpec>());
    int64_t tf = 0, tr = 0;
    bool ok = ok_jpeg(x) && parse_ts(hdr(x.r, "X-Timestamp"), &tf) && parse_ts(hdr(x.r, "X-Request-Timestamp"), &tr) &&
              tf > tr && tr == T && hdr(x.r, "X-Discarded-Frames") == "0" && id_of(x) == (uint64_t)i &&
              hdr(x.r, "X-Boot-Id") == boot && x.gets == 1 && x.returns == 1 && x.balanced;
    if (!ok && first_bad.empty()) first_bad = fmt("luot %d: %s", i, brief(x).c_str());
    all = all && ok;
    last_id = id_of(x);
  }
  check("H02", all, "Q6-T1: 20 luot lien tiep -> 200, du 5 header 1 lan, ID 1..20, cung boot, t_frame > t_req = moc khoa, discarded 0, 1 lay/1 tra, khoa can bang",
        first_bad.empty() ? fmt("ID cuoi %llu", (unsigned long long)last_id) : first_bad);

  // ---- Q6-T2: stale va han
  int ks[] = {1, 4};
  for (int j = 0; j < 2; j++) {
    int k = ks[j]; T += 2000000;
    std::vector<FrameSpec> fr;
    for (int i = 0; i < k; i++) fr.push_back(F_stale(T - 33000 * (k - i)));
    fr.push_back(F_fresh());
    Run x = fresh_at(T, fr);
    bool ok = ok_jpeg(x) && hdr(x.r, "X-Discarded-Frames") == fmt("%d", k) && x.gets == k + 1 && x.returns == k + 1 &&
              x.balanced && id_of(x) == last_id + 1;
    if (ok) last_id = id_of(x);
    check(k == 1 ? "H03" : "H04", ok, fmt("Q6-T2: %d khung cu roi khung moi -> 200, discarded %d, lay %d tra %d", k, k, k + 1, k + 1).c_str(), brief(x));
  }
  {
    T += 2000000;
    std::vector<FrameSpec> fr;
    for (int i = 0; i < 6; i++) fr.push_back(i < 5 ? F_stale(T - 1000 * (5 - i)) : F_fresh());
    Run x = fresh_at(T, fr);
    bool ok = is_err(x, 503, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME") && x.gets == 5 && x.returns == 5 && g_script.size() == 1 && x.balanced;
    check("H05", ok, "Q6-T2: khung cu thu 5 -> 503 TIMEOUT, khong goi lay khung thu 6", brief(x) + fmt(" con_trong_kich_ban=%u", (unsigned)g_script.size()));
    T += 2000000;
    Run y = fresh_at(T, std::vector<FrameSpec>());
    check("H06", ok_jpeg(y) && id_of(y) == last_id + 1, "Q6-T2: sau 503 TIMEOUT, luot hop le tiep theo chay va ID khong bi tieu thu", brief(y));
    last_id = id_of(y);
  }
  {
    T += 2000000;
    std::vector<FrameSpec> fr; fr.push_back(F_stale(T, 0)); fr.push_back(F_fresh());
    Run x = fresh_at(T, fr);
    bool ok = ok_jpeg(x) && hdr(x.r, "X-Discarded-Frames") == "1" && x.balanced;
    if (ok) last_id = id_of(x);
    check("H07", ok, "Q6-T2: timestamp khung BANG moc request la cu (t_frame <= t_req)", brief(x));
  }
  {
    T += 3000000;
    std::vector<FrameSpec> fr; fr.push_back(F_fresh(1499999));
    Run x = fresh_at(T, fr);
    bool ok = ok_jpeg(x) && x.balanced;
    if (ok) last_id = id_of(x);
    check("H08", ok, "Q6-T2: khung moi ve truoc han 1 us (now = deadline - 1) -> 200", brief(x));
  }
  {
    T += 3000000;
    std::vector<FrameSpec> fr; fr.push_back(F_fresh(1500000));
    Run x = fresh_at(T, fr);
    bool ok = is_err(x, 503, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME") && x.returns == 1 && x.balanced && hdr_count(x.r, "X-Frame-Id") == 0;
    if (code_of(x.r) == 200) last_id = id_of(x);
    check("H09", ok, "Q6-T2: khung moi ve DUNG han (now >= deadline) -> 503 TIMEOUT, tra buffer, khong cap ID/gui JPEG", brief(x));
  }
  {
    T += 3000000;
    std::vector<FrameSpec> fr; fr.push_back(F_fresh(1600000));
    Run x = fresh_at(T, fr);
    bool ok = is_err(x, 503, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME") && x.returns == 1 && x.balanced && hdr_count(x.r, "X-Frame-Id") == 0;
    if (code_of(x.r) == 200) last_id = id_of(x);
    check("H10", ok, "Q6-T2: driver tra khung moi TRE (sau han 100 ms) -> 503 TIMEOUT, khong gui JPEG tre", brief(x));
  }
  {
    T += 3000000;
    std::vector<FrameSpec> fr; fr.push_back(F_stale(T - 1, 1500000)); fr.push_back(F_fresh());
    Run x = fresh_at(T, fr);
    bool ok = is_err(x, 503, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME") && x.gets == 1 && x.returns == 1 && x.balanced;
    check("H11", ok, "Q6-T2: khung cu ve dung han -> 503 TIMEOUT, khong lay them", brief(x));
  }

  // ---- Q6-T4: NULL, sai dinh dang
  {
    T += 3000000;
    std::vector<FrameSpec> fr; fr.push_back(F_null(100000));
    Run x = fresh_at(T, fr);
    bool ok = is_err(x, 503, "ERROR CAMERA_NO_BUFFER") && x.gets == 1 && x.returns == 0 && x.balanced;
    check("H12", ok, "Q6-T4: fb_get NULL truoc han -> 503 CAMERA_NO_BUFFER, khong tra NULL", brief(x));
  }
  {
    T += 6000000;
    std::vector<FrameSpec> fr; fr.push_back(F_null(4000000));
    Run x = fresh_at(T, fr);
    bool ok = is_err(x, 503, "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME") && x.returns == 0 && x.balanced;
    check("H13", ok, "Q6-T4: fb_get NULL SAU han (driver chan ~4 s) -> uu tien 503 TIMEOUT (ke hoach 4.3)", brief(x));
  }
  {
    T += 3000000;
    FrameSpec f = F_fresh(); f.fmt = PIXFORMAT_RGB565;
    std::vector<FrameSpec> fr; fr.push_back(f);
    Run x = fresh_at(T, fr);
    bool ok = is_err(x, 500, "ERROR CAMERA_UNSUPPORTED_FORMAT") && x.returns == 1 && x.balanced;
    check("H14", ok, "Q6-T4: khung khong-JPEG truoc han -> 500 UNSUPPORTED_FORMAT, tra buffer 1 lan", brief(x));
    T += 3000000;
    Run y = fresh_at(T, std::vector<FrameSpec>());
    check("H15", ok_jpeg(y) && id_of(y) == last_id + 1, "Q6-T4: sau loi NULL/dinh dang, luot hop le van chay, ID khong bi tieu thu boi luot loi", brief(y));
    last_id = id_of(y);
  }
  {
    httpd_req_t rq; rq.fail_hdr_name = "X-Boot-Id";
    T += 3000000;
    Run x = fresh_at(T, std::vector<FrameSpec>(), rq);
    bool ok = is_err(x, 500, "ERROR CAMERA_INTERNAL") && x.returns == 1 && x.balanced;
    if (hdr_count(x.r, "X-Frame-Id")) last_id = id_of(x);
    std::string names;
    for (size_t i = 0; i < x.r.hdrs.size(); i++) names += x.r.hdrs[i].first + (i + 1 < x.r.hdrs.size() ? "," : "");
    check("H16", ok, "Q6-T4: dat header that bai truoc khi gui -> 500 CAMERA_INTERNAL, khong gui JPEG thieu header",
          brief(x) + " header_trong_phan_hoi=[" + names + "]");
  }
  {
    httpd_req_t rq; rq.fail_send = true;
    T += 3000000;
    Run x = fresh_at(T, std::vector<FrameSpec>(), rq);
    uint64_t consumed = id_of(x);
    bool ok = x.ret != ESP_OK && x.r.n_send == 1 && x.returns == 1 && x.balanced && consumed == last_id + 1;
    check("H17", ok, "Q6-T4: gui body loi (client dong) -> tra loi, 1 lan gui, tra buffer 1 lan, nha khoa, ID da cap", brief(x));
    last_id = consumed;
    T += 3000000;
    Run y = fresh_at(T, std::vector<FrameSpec>());
    check("H18", ok_jpeg(y) && id_of(y) == last_id + 1, "Q6-T4: luot sau loi gui chay binh thuong, ID = ID bi tieu thu + 1", brief(y));
    last_id = id_of(y);
  }
  {
    SemaphoreHandle_t keep = s_cam_mutex;
    s_cam_mutex = NULL;
    clock_set(T += 3000000); g_script.clear();
    int g0 = g_gets;
    httpd_req_t rq;
    esp_err_t r = capture_fresh_handler(&rq);
    s_cam_mutex = keep;
    check("H19", r != ESP_OK && code_of(rq) == 500 && g_gets == g0 && rq.n_send == 1,
          "Q6-T4: khong co mutex -> 500, khong cham camera", fmt("HTTP %d get=%d", code_of(rq), g_gets - g0));
  }

  // ---- Q6-T3: bien ID
  {
    uint64_t keep_c = s_frame_id_counter; bool keep_m = s_frame_id_max_served;
    s_frame_id_counter = UINT64_MAX - 1; s_frame_id_max_served = false;
    Run a = fresh_at(T += 3000000, std::vector<FrameSpec>());
    Run b = fresh_at(T += 3000000, std::vector<FrameSpec>());
    Run c = fresh_at(T += 3000000, std::vector<FrameSpec>());
    int served_max = (code_of(a.r) == 200 && id_of(a) == UINT64_MAX) + (code_of(b.r) == 200 && id_of(b) == UINT64_MAX) +
                     (code_of(c.r) == 200 && id_of(c) == UINT64_MAX);
    bool ok = ok_jpeg(a) && hdr(a.r, "X-Frame-Id") == "18446744073709551615" && is_err(b, 500, "ERROR FRAME_ID_OVERFLOW") &&
              is_err(c, 500, "ERROR FRAME_ID_OVERFLOW") && b.returns == 1 && c.returns == 1 && b.balanced && c.balanced;
    check("H20", ok, "Q6-T3: counter MAX-1 -> cap UINT64_MAX MOT lan, luot ke tiep 500 FRAME_ID_OVERFLOW (khong quay vong, khong trung ID)",
          fmt("luot1: %s || luot2: %s || luot3: HTTP %d; so lan cap UINT64_MAX = %d", brief(a).c_str(), brief(b).c_str(), code_of(c.r), served_max));
    s_frame_id_counter = keep_c; s_frame_id_max_served = keep_m;
  }

  // ---- Q6-T5: tranh chap 1 luong (snapshot chu so huu)
  {
    xSemaphoreTake(s_cam_mutex, 0);  // nguoi khac dang giu khoa
    s_stream_active = true;
    int g0 = g_gets, s0 = g_sensor_calls;
    DWORD t0 = GetTickCount();
    Run f; f.r = httpd_req_t(); f.ret = capture_fresh_handler(&f.r);
    DWORD waited = GetTickCount() - t0;
    httpd_req_t rc, rb, rx, ri; rx.query = "xclk=20";
    capture_handler(&rc); bmp_handler(&rb); xclk_handler(&rx); index_handler(&ri);
    bool ok = is_err(f, 503, "ERROR CAMERA_BUSY_STREAM") && code_of(rc) == 503 && rc.body == "ERROR CAMERA_BUSY_STREAM" &&
              code_of(rb) == 503 && code_of(rx) == 503 && code_of(ri) == 503 && g_gets == g0 && g_sensor_calls == s0;
    check("H21", ok, "Q6-T5: khoa dang bi giu + co stream -> fresh/capture/bmp/xclk/index 503 BUSY_STREAM, khong cham camera/sensor",
          fmt("fresh=%d '%s' cho=%lums capture=%d bmp=%d xclk=%d index=%d get=%d sensor=%d", code_of(f.r), f.r.body.c_str(),
              (unsigned long)waited, code_of(rc), code_of(rb), code_of(rx), code_of(ri), g_gets - g0, g_sensor_calls - s0));
    check("H22", waited >= 90 && waited < 1000, "Q6-T5: cho khoa danh nghia 100 ms roi bao ban (khong busy-wait vo han)", fmt("%lu ms", (unsigned long)waited));
    bool gz = hdr_count(ri, "Content-Encoding") > 0;
    check("H23", !(gz && ri.type == "text/plain"), "Q6-T5: index '/' khi ban tra 503 text/plain KHONG kem 'Content-Encoding: gzip' (body khong nen)",
          fmt("type=%s Content-Encoding=%s body='%s'", ri.type.c_str(), hdr(ri, "Content-Encoding").c_str(), ri.body.c_str()));
    s_stream_active = false;
    Run g; g.r = httpd_req_t(); g.ret = capture_fresh_handler(&g.r);
    check("H24", is_err(g, 503, "ERROR CAMERA_BUSY_CAPTURE"), "Q6-T5: khoa bi giu, khong co stream -> 503 BUSY_CAPTURE", g.r.body);
    xSemaphoreGive(s_cam_mutex);
  }

  // ---- Q6-T5: stream giu ca ket noi, hai thu tu (2 luong that)
  {
    HANDLE blk = CreateEvent(NULL, TRUE, FALSE, NULL), ent = CreateEvent(NULL, TRUE, FALSE, NULL);
    httpd_req_t rs; rs.chunk_block = blk; rs.chunk_entered = ent; rs.chunk_fail_after = 1;  // client ngat sau chunk dau
    g_script.clear();
    ThreadArg ta = {stream_handler, &rs, ESP_OK};
    HANDLE th = CreateThread(NULL, 0, thread_main, &ta, 0, NULL);
    bool entered = WaitForSingleObject(ent, 5000) == WAIT_OBJECT_0;
    int gm0 = g_gets;
    httpd_req_t rf, rc, rb, rx; rx.query = "xclk=20";
    capture_fresh_handler(&rf); capture_handler(&rc); bmp_handler(&rb); xclk_handler(&rx);
    int main_gets = g_gets - gm0;
    bool active_during = s_stream_active;
    SetEvent(blk);
    bool joined = WaitForSingleObject(th, 5000) == WAIT_OBJECT_0;
    bool ok = entered && joined && active_during && code_of(rf) == 503 && rf.body == "ERROR CAMERA_BUSY_STREAM" &&
              rc.body == "ERROR CAMERA_BUSY_STREAM" && rb.body == "ERROR CAMERA_BUSY_STREAM" && rx.body == "ERROR CAMERA_BUSY_STREAM" &&
              main_gets == 0;
    check("H25", ok, "Q6-T5: stream (luong khac) dang gui -> fresh/capture/bmp/xclk 503 BUSY_STREAM, luong chinh khong lay buffer",
          fmt("vao_stream=%d fresh=%d '%s' capture='%s' bmp='%s' xclk='%s' get_luong_chinh=%d", entered, code_of(rf), rf.body.c_str(),
              rc.body.c_str(), rb.body.c_str(), rx.body.c_str(), main_gets));
    Snap s = snap();
    bool ok2 = joined && ta.ret != ESP_OK && !s_stream_active && sem_owner() == 0 && s.out == 0 && s.takes == s.gives;
    check("H26", ok2, "Q6-T5: client ngat stream -> stream thoat, nha khoa, tra het buffer, co stream ve false",
          fmt("ret=%d active=%d owner=%lu con_giu=%u take/give=%d/%d", ta.ret, (int)s_stream_active, (unsigned long)sem_owner(),
              (unsigned)s.out, s.takes, s.gives));
    Run y = fresh_at(T += 3000000, std::vector<FrameSpec>());
    check("H27", ok_jpeg(y), "Q6-T5: sau khi stream nha, /capture_fresh 200", brief(y));
    CloseHandle(blk); CloseHandle(ent); CloseHandle(th);
  }
  {
    HANDLE blk = CreateEvent(NULL, TRUE, FALSE, NULL), ent = CreateEvent(NULL, TRUE, FALSE, NULL);
    clock_set(T += 3000000);
    g_script.clear();
    FrameSpec f = F_fresh(); f.block = blk; f.entered = ent; g_script.push_back(f);
    httpd_req_t rf;
    ThreadArg ta = {capture_fresh_handler, &rf, ESP_OK};
    HANDLE th = CreateThread(NULL, 0, thread_main, &ta, 0, NULL);
    bool entered = WaitForSingleObject(ent, 5000) == WAIT_OBJECT_0;
    httpd_req_t rs;
    esp_err_t sr = stream_handler(&rs);
    bool stream_busy = sr != ESP_OK && code_of(rs) == 503 && rs.body == "ERROR CAMERA_BUSY_CAPTURE" && rs.n_chunks == 0 && !s_stream_active;
    SetEvent(blk);
    bool joined = WaitForSingleObject(th, 5000) == WAIT_OBJECT_0;
    check("H28", entered && joined && stream_busy && code_of(rf) == 200,
          "Q6-T5: fresh (luong khac) dang giu buffer -> /stream 503 BUSY_CAPTURE, khong bat dau stream; fresh xong 200",
          fmt("stream=%d '%s' chunk=%d fresh=%d", code_of(rs), rs.body.c_str(), rs.n_chunks, code_of(rf)));
    httpd_req_t rs2; rs2.chunk_fail_after = 3;  // khung 1 gui du 3 chunk, khung 2 hong
    g_script.clear();
    Snap a = snap();
    esp_err_t r2 = stream_handler(&rs2);
    Snap b = snap();
    check("H29", r2 != ESP_OK && b.gets - a.gets == 2 && b.out == 0 && sem_owner() == 0 && !s_stream_active && (b.takes - a.takes) == (b.gives - a.gives),
          "Q6-T5: stream binh thuong 2 khung roi client ngat -> tra du 2 buffer, nha khoa",
          fmt("get=%d con_giu=%u chunk=%d", b.gets - a.gets, (unsigned)b.out, rs2.n_chunks));
    CloseHandle(blk); CloseHandle(ent); CloseHandle(th);
  }

  // ---- Q6-T8: legacy khong tranh chap giu hop dong
  {
    g_script.clear();
    Run c = run_handler(capture_handler);
    bool ok = code_of(c.r) == 200 && c.r.type == "image/jpeg" && hdr_count(c.r, "X-Timestamp") == 1 && c.returns == 1 && c.balanced &&
              c.r.body == std::string((const char *)JPEG_BYTES, sizeof(JPEG_BYTES));
    check("H30", ok, "Q6-T8: /capture khong tranh chap: 200 image/jpeg + X-Timestamp, tra buffer, nha khoa", c.why);
    g_script.push_back(F_null(1000));
    Run n = run_handler(capture_handler);
    check("H31", code_of(n.r) == 500 && n.balanced && n.returns == 0, "/capture fb NULL -> 500, nha khoa", n.why);
    Run b = run_handler(bmp_handler);
    check("H32", code_of(b.r) == 200 && b.r.type == "image/x-windows-bmp" && b.returns == 1 && b.balanced, "/bmp khong tranh chap: 200 bmp, tra buffer, nha khoa", b.why);
    g_bmp_fail = true;
    Run bf = run_handler(bmp_handler);
    g_bmp_fail = false;
    check("H33", code_of(bf.r) == 500 && bf.returns == 1 && bf.balanced, "/bmp doi dinh dang loi -> 500, tra buffer, nha khoa", bf.why);
    httpd_req_t rx; rx.query = "xclk=20";
    Run x = run_handler(xclk_handler, rx);
    httpd_req_t ri;
    Run i = run_handler(index_handler, ri);
    check("H34", code_of(x.r) == 200 && x.balanced && code_of(i.r) == 200 && i.balanced && hdr(i.r, "Content-Encoding") == "gzip",
          "/xclk va '/' khong tranh chap: 200, nha khoa", fmt("xclk=%d index=%d", code_of(x.r), code_of(i.r)));
  }

  // ---- Vong 6 V6-T1: /status binh thuong, heap gia 123456 / 654321
  int n_fmt = 0;
  {
    sensor_defaults(OV3660_PID);
    g_heap_int = 123456; g_heap_ps = 654321;
    int hi0 = g_heap_int_calls, hp0 = g_heap_ps_calls, bm0 = g_heap_bad_mask, v0 = g_vsn_calls, r0 = g_get_reg_calls, s0 = g_sensor_calls;
    Run x = run_handler(status_handler);
    n_fmt = g_vsn_calls - v0;
    const std::string &b = x.r.body;
    bool ok = code_of(x.r) == 200 && x.r.type == "application/json" && x.r.n_send == 1 && x.ret == ESP_OK && x.balanced &&
              x.gets == 0 && !b.empty() && b[0] == '{' && b[b.size() - 1] == '}' && strlen(b.c_str()) == b.size() &&
              b.find("\"heap_internal_free_bytes\":123456") != std::string::npos &&
              b.find("\"heap_psram_free_bytes\":654321") != std::string::npos &&
              g_heap_int_calls - hi0 == 1 && g_heap_ps_calls - hp0 == 1 && g_heap_bad_mask == bm0;
    printf("  @JSON H36 %s\n", b.c_str());
    check("H36", ok, "V6-T1: /status binh thuong (OV3660) -> 200 application/json, heap noi 123456 (INTERNAL|8BIT) va PSRAM 654321 (SPIRAM|8BIT) moi mask 1 lan, khoa can bang, khong lay buffer",
          fmt("HTTP %d type=%s len=%u lan_dinh_dang=%d get_reg=%d sensor_get=%d heap noi/psram/mask_sai=%d/%d/%d; %s", code_of(x.r), x.r.type.c_str(),
              (unsigned)b.size(), n_fmt, g_get_reg_calls - r0, g_sensor_calls - s0, g_heap_int_calls - hi0, g_heap_ps_calls - hp0,
              g_heap_bad_mask - bm0, x.why.c_str()));
  }
  // ---- V6-T2: bien gia tri heap 0 / UINT32_MAX
  {
    sensor_defaults(OV3660_PID);
    g_heap_int = 0; g_heap_ps = UINT32_MAX;
    Run a = run_handler(status_handler);
    g_heap_int = UINT32_MAX; g_heap_ps = 0;
    Run b = run_handler(status_handler);
    std::string ea = ",\"heap_internal_free_bytes\":0,\"heap_psram_free_bytes\":4294967295}";
    std::string eb = ",\"heap_internal_free_bytes\":4294967295,\"heap_psram_free_bytes\":0}";
    bool ok = code_of(a.r) == 200 && code_of(b.r) == 200 && a.balanced && b.balanced &&
              a.r.body.size() > ea.size() && a.r.body.compare(a.r.body.size() - ea.size(), ea.size(), ea) == 0 &&
              b.r.body.size() > eb.size() && b.r.body.compare(b.r.body.size() - eb.size(), eb.size(), eb) == 0;
    printf("  @JSON H37a %s\n", a.r.body.c_str());
    printf("  @JSON H37b %s\n", b.r.body.c_str());
    check("H37", ok, "V6-T2: heap 0 va UINT32_MAX in dung 0 / 4294967295 (khong am, khong quay vong), JSON dong dung",
          fmt("a: HTTP %d ...%s | b: HTTP %d ...%s", code_of(a.r), a.r.body.substr(a.r.body.size() > 70 ? a.r.body.size() - 70 : 0).c_str(),
              code_of(b.r), b.r.body.substr(b.r.body.size() > 70 ? b.r.body.size() - 70 : 0).c_str()));
  }
  // ---- V6-T2: moi truong dai nhat theo kieu that (OV5640/OV3660 48 thanh ghi INT_MIN) va nhanh OV2640
  {
    g_heap_int = UINT32_MAX; g_heap_ps = UINT32_MAX;
    sensor_extreme(OV5640_PID);
    Run a = run_handler(status_handler);
    sensor_extreme(OV3660_PID);
    Run c = run_handler(status_handler);
    printf("  @JSON H38a %s\n", a.r.body.c_str());
    printf("  @JSON H38b %s\n", c.r.body.c_str());
    check("H38", code_of(a.r) == 200 && code_of(c.r) == 200 && a.balanced && c.balanced && a.r.body.size() < 2046 && c.r.body.size() < 2046,
          "V6-T2: /status gia tri cuc tri (reg INT_MIN, int8 -128, uint8 255, aec_value 65535, heap UINT32_MAX) -> 200 du JSON, vua bo dem 2048",
          fmt("OV5640: HTTP %d len=%u | OV3660: HTTP %d len=%u (cho toi da 2045 ky tu + '}' + NUL)", code_of(a.r), (unsigned)a.r.body.size(),
              code_of(c.r), (unsigned)c.r.body.size()));
    sensor_defaults(0x26);
    g_heap_int = 1000; g_heap_ps = 2000;
    Run o = run_handler(status_handler);
    printf("  @JSON H39 %s\n", o.r.body.c_str());
    check("H39", code_of(o.r) == 200 && o.balanced && o.r.body.find("\"heap_psram_free_bytes\":2000}") != std::string::npos,
          "V6-T2: nhanh OV2640 (3 thanh ghi) cung co hai truong heap, 200", fmt("HTTP %d len=%u", code_of(o.r), (unsigned)o.r.body.size()));
    sensor_defaults(OV3660_PID);
  }
  // ---- V6-T2: cuong buc loi bo dinh dang / het cho o TUNG phep append
  {
    g_heap_int = 123456; g_heap_ps = 654321;
    for (int mode = 0; mode < 2; mode++) {
      int bad = 0, n = 0; std::string first;
      for (int k = 1; k <= n_fmt; k++) {
        g_vsn_calls = 0;
        if (mode == 0) g_vsn_fail_at = k; else g_vsn_trunc_at = k;
        Run x = run_handler(status_handler);
        g_vsn_fail_at = g_vsn_trunc_at = 0;
        n++;
        bool ok = x.ret != ESP_OK && is_err(x, 500, "ERROR CAMERA_INTERNAL") && x.r.type == "text/plain" && x.balanced && x.gets == 0;
        if (!ok) { bad++; if (first.empty()) first = fmt("phep %d: %s", k, brief(x).c_str()); }
      }
      Run y = run_handler(status_handler);
      bool after = code_of(y.r) == 200 && y.balanced;
      check(mode == 0 ? "H40" : "H41", n_fmt > 0 && bad == 0 && after,
            mode == 0 ? "V6-T2: loi bo dinh dang (tra -1) o tung phep append -> 500 ERROR CAMERA_INTERNAL, khong 200 JSON cut, nha khoa 1 lan; /status sau do 200"
                      : "V6-T2: het cho (vsnprintf tra >= con lai) o tung phep append -> 500 ERROR CAMERA_INTERNAL, nha khoa 1 lan; /status sau do 200",
            fmt("%d phep append, %d sai%s; luot sau: HTTP %d", n, bad, first.empty() ? "" : (" | " + first).c_str(), code_of(y.r)));
    }
  }
  // ---- V6-T2: ham append that voi bo dem nho (khong tiem loi): bien vua du / thieu 1 byte / con tro o bien
  {
#ifdef HAVE_STATUS_JSON_APPEND
    char buf[16];
    memset(buf, 'Z', sizeof buf);
    char *p = buf, *end = buf + 8;
    bool a = status_json_append(&p, end, "%s", "abcdefg");
    bool a_ok = a && p == buf + 7 && buf[7] == 0 && !memcmp(buf, "abcdefg", 7) && buf[8] == 'Z';
    memset(buf, 'Z', sizeof buf); p = buf;
    bool b = status_json_append(&p, end, "%s", "abcdefgh");
    bool tail = true;
    for (int i = 8; i < 16; i++) tail = tail && buf[i] == 'Z';
    bool b_ok = !b && p == buf && tail;
    p = end;
    bool c = status_json_append(&p, end, "%s", "");
    char *np = NULL;
    bool d = status_json_append(&np, end, "%s", "x");
    bool e = status_json_append(NULL, end, "%s", "x");
    check("H42", a_ok && b_ok && !c && p == end && !d && !e,
          "V6-T2: status_json_append that: vua du (7 ky tu + NUL trong 8) -> tien 7; thieu 1 byte -> false, khong tien, khong ghi qua bien; con tro o bien/NULL -> false",
          fmt("vua_du=%d thieu=%d(p_giu=%d duoi_nguyen=%d) o_bien=%d null=%d/%d", a_ok, b, p == end, tail, c, d, e));
#else
    check("H42", false, "V6-T2: status_json_append khong co trong app_httpd.cpp", "khong kiem duoc bien helper");
#endif
  }
  // ---- V6-T3: /status khi khoa bi giu (co/khong stream) va khi stream (luong khac) dang gui
  {
    sensor_defaults(OV3660_PID);
    int hi0 = g_heap_int_calls + g_heap_ps_calls, r0 = g_get_reg_calls, s0 = g_sensor_calls;
    xSemaphoreTake(s_cam_mutex, 0);
    s_stream_active = true;
    httpd_req_t ra; esp_err_t ea = status_handler(&ra);
    s_stream_active = false;
    httpd_req_t rb; esp_err_t eb = status_handler(&rb);
    xSemaphoreGive(s_cam_mutex);
    HANDLE blk = CreateEvent(NULL, TRUE, FALSE, NULL), ent = CreateEvent(NULL, TRUE, FALSE, NULL);
    httpd_req_t rs; rs.chunk_block = blk; rs.chunk_entered = ent; rs.chunk_fail_after = 1;
    g_script.clear();
    ThreadArg ta = {stream_handler, &rs, ESP_OK};
    HANDLE th = CreateThread(NULL, 0, thread_main, &ta, 0, NULL);
    bool entered = WaitForSingleObject(ent, 5000) == WAIT_OBJECT_0;
    int rs0 = g_get_reg_calls, hs0 = g_heap_int_calls + g_heap_ps_calls;
    httpd_req_t rc; esp_err_t ec = status_handler(&rc);
    int during_reg = g_get_reg_calls - rs0, during_heap = g_heap_int_calls + g_heap_ps_calls - hs0;
    SetEvent(blk);
    bool joined = WaitForSingleObject(th, 5000) == WAIT_OBJECT_0;
    CloseHandle(blk); CloseHandle(ent); CloseHandle(th);
    bool ok = ea != ESP_OK && code_of(ra) == 503 && ra.body == "ERROR CAMERA_BUSY_STREAM" && ra.n_send == 1 &&
              eb != ESP_OK && code_of(rb) == 503 && rb.body == "ERROR CAMERA_BUSY_CAPTURE" && rb.n_send == 1 &&
              entered && joined && ec != ESP_OK && code_of(rc) == 503 && rc.body == "ERROR CAMERA_BUSY_STREAM" && rc.n_send == 1 &&
              during_reg == 0 && during_heap == 0;
    check("H43", ok, "V6-T3: /status khi khoa bi giu + stream -> 503 BUSY_STREAM; khoa giu khong stream -> 503 BUSY_CAPTURE; stream (luong khac) dang gui -> 503 BUSY_STREAM, khong doc sensor/heap",
          fmt("giu+stream=%d '%s' giu=%d '%s' stream_that=%d '%s' (vao=%d xong=%d) doc_reg/heap luc ban=%d/%d; tu dau khoi: reg=%d heap=%d sensor_get=%d",
              code_of(ra), ra.body.c_str(), code_of(rb), rb.body.c_str(), code_of(rc), rc.body.c_str(), entered, joined, during_reg,
              during_heap, g_get_reg_calls - r0, g_heap_int_calls + g_heap_ps_calls - hi0, g_sensor_calls - s0));
  }
  // ---- V6-T3: sau khi stream nha, lay mau /status 3 lan voi heap thay doi
  {
    uint32_t vi[3] = {100000, 99000, 101000}, vp[3] = {2000000, 1990000, 2010000};
    bool ok = true; std::string why, base_no_heap;
    for (int i = 0; i < 3; i++) {
      g_heap_int = vi[i]; g_heap_ps = vp[i];
      int s0 = g_sensor_calls, r0 = g_get_reg_calls;
      Run x = run_handler(status_handler);
      std::string tail = fmt(",\"heap_internal_free_bytes\":%u,\"heap_psram_free_bytes\":%u}", (unsigned)vi[i], (unsigned)vp[i]);
      bool good = code_of(x.r) == 200 && x.balanced && x.gets == 0 && g_sensor_calls - s0 == 1 && x.r.body.size() > tail.size() &&
                  x.r.body.compare(x.r.body.size() - tail.size(), tail.size(), tail) == 0;
      std::string no_heap = good ? x.r.body.substr(0, x.r.body.size() - tail.size()) : "";
      if (i == 0) base_no_heap = no_heap; else good = good && no_heap == base_no_heap;
      printf("  @JSON H44%c %s\n", 'a' + i, x.r.body.c_str());
      if (!good && why.empty()) why = fmt("mau %d: HTTP %d get=%d sensor_get=%d reg=%d; %s", i + 1, code_of(x.r), x.gets, g_sensor_calls - s0, g_get_reg_calls - r0, x.why.c_str());
      ok = ok && good;
    }
    check("H44", ok, "V6-T3: sau khi stream nha, 3 mau /status voi heap doi -> moi mau 200 dung so heap; phan sensor (bo heap) giong het; khong lay buffer, chi 1 lan sensor_get",
          why.empty() ? "3/3 mau dung" : why);
  }

  Snap e = snap();
  check("H35", g_unlocked_get == 0 && g_overlap == 0 && g_unlocked_sensor == 0 && e.bad == 0 && e.nullret == 0 && e.out == 0 && e.badg == 0,
        "Toan bo: khong lay buffer/sensor ngoai khoa, khong hai vung camera chong nhau, khong tra sai/tra NULL, khong con buffer bi giu",
        fmt("ngoai_khoa get=%d sensor=%d chong=%d tra_sai=%d tra_NULL=%d con_giu=%u nha_sai=%d", g_unlocked_get, g_unlocked_sensor,
            g_overlap, e.bad, e.nullret, (unsigned)e.out, e.badg));

  printf("\n== %d PASS, %d FAIL ==\n", g_pass, g_fail);
  return g_fail ? 1 : 0;
}
