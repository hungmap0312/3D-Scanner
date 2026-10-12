# Đặc tả thiết kế Q3 — ESP32-S3 Fresh Capture (`/capture_fresh`)

- **Ngày lập:** 2026-10-02
- **Bước quy trình:** `[Q3]` — Đặc tả giao thức và cơ chế phần mềm trước chặng lập trình `[Q6]`.
- **Căn cứ:**
  - `docs/SPEC.md` mục 5.2, 6.2–6.4, 9.2, 10, 18.2.
  - `docs/design/SCAN_SESSION.md` mục 4, 6, 7.
  - `DECISIONS.md`: D041 (Phương án B: endpoint `/capture_fresh` và `X-Frame-Id`), D042 (cổng B/H riêng cho C5a).
  - Driver `esp32-camera` precompiled trong Arduino-ESP32 3.3.11 (`libespressif__esp32-camera.a`).

---

## 1. Mục tiêu và nguyên tắc thiết kế

### 1.1 Mục tiêu
Cung cấp endpoint HTTP GET `/capture_fresh` trên ESP32-S3 bảo đảm:
1. **Khung hình tươi (Freshness):** Khung hình trả về bắt đầu nhận DMA sau thời điểm client gửi yêu cầu HTTP, loại bỏ triệt để hiện tượng nhận phải khung hình cũ còn tồn đọng trong bộ đệm hàng đợi (stale frames) khi chuyển trạng thái laser.
2. **Định danh đơn điệu (`X-Frame-Id`):** Mỗi khung hình hợp lệ được gán một mã định danh nguyên dương tăng dần (bắt đầu từ 1 sau khi boot). Client phát hiện được ngay lập tức nếu camera bị lặp khung hoặc mất khung giữa phiên quét.
3. **Định danh chu kỳ khởi động (`X-Boot-Id`):** Mỗi chu kỳ boot tạo token 128-bit ngẫu nhiên (32 ký tự hex thường) theo D043. Client phát hiện ngay lập tức nếu bo bị reboot giữa chừng dù Frame ID và timestamp của bo mới đều tăng.
4. **Truy xuất chẩn đoán đầy đủ:** Trả về 5 header HTTP (`X-Frame-Id`, `X-Boot-Id`, `X-Timestamp`, `X-Request-Timestamp`, `X-Discarded-Frames`) cung cấp đầy đủ thông tin đồng bộ.
5. **Loại trừ tranh chấp (Mutual Exclusion):** Dùng một mutex chung FreeRTOS (`s_cam_mutex`, timeout danh nghĩa 100 ms) bảo vệ toàn bộ các handler chạm camera và cảm biến (`/capture_fresh`, `/capture`, `/bmp`, `/stream`, `/control`, `/resolution`, `/xclk`, `/reg`, `/greg`, `/pll`, `/status`, web root sensor info).
6. **Cấu hình 1 buffer:** Chốt cấu hình khởi tạo 1 buffer (`fb_count = 1`), `CAMERA_GRAB_LATEST` cho nhánh JPEG PSRAM theo SPEC §10 và D043.
7. **Tương thích ngược:** Giữ nguyên endpoint `/capture` cũ cho các ứng dụng xem thử không yêu cầu đồng bộ laser.

### 1.2 Điều KHÔNG làm
- Không điều khiển chân GPIO laser từ ESP32-S3 (laser do Nucleo điều khiển độc lập theo SPEC 9.1).
- Không coi `X-Frame-Id`, `X-Boot-Id` hay timestamp DMA là bằng chứng duy nhất chứng minh ảnh đúng trạng thái laser (C5/C7 vẫn bắt buộc kiểm chứng bằng chuỗi bật/tắt laser không tuần hoàn ≥ 100 chu kỳ theo SPEC 6.4).
- Không thay đổi pinout hay loại cảm biến (giữ nguyên OV3660 theo cấu hình hiện tại).
- Không kết nối laser hay cấp điện laser trong chặng triển khai và thử nghiệm camera Q6.

---

## 2. Căn cứ kỹ thuật Driver và Timebase

### 2.1 Chuỗi Provenance nguồn gốc và Bằng chứng Artifact

Để đáp ứng đầy đủ tiêu chí D2 (nguồn khớp gói build, có bằng chứng provenance bất biến), toàn bộ chuỗi phát hành và nguồn gốc của thư viện `esp32-camera` trong môi trường Arduino-ESP32 3.3.11 được truy xuất và xác minh độc lập:

1. **Package Index chính thức của Espressif:**
   - URL: `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   - Tệp cục bộ: `C:\Users\bestp\AppData\Local\Arduino15\package_esp32_index.json`
   - Platform: `esp32:esp32` phiên bản `3.3.11` (archive `esp32-core-3.3.11.zip`, SHA-256 `a18203f2429f5551ec929b80e8129e439df7a3a009b536b305f00b4a1f1bbb62`).
   - Công cụ phụ thuộc: `esp32s3-libs` phiên bản `3.3.11`.
2. **Artifact phát hành chính thức (`esp32s3-libs`):**
   - URL tải chính thức: `https://github.com/espressif/arduino-esp32/releases/download/3.3.11/esp32s3-libs-3.3.11.zip`
   - Tệp lưu trong staging cache: `C:\Users\bestp\AppData\Local\Arduino15\staging\packages\esp32s3-libs-3.3.11.zip`
   - Checksum SHA-256 (công bố trong JSON và thực tế trên máy):
     `FEC76794708694120C6EC803CDBFC7DCD36286EA22B7D38097B7909BBD19F7B5`
   - Thư viện tĩnh giải nén: `lib/libespressif__esp32-camera.a`
     - SHA-256: `7A96DAB88367CC3CB3EC113AAB5F181DC59DAA7B656B9E4F1E0F0C66D77FFE02`
   - Header driver giải nén: `include/espressif__esp32-camera/driver/include/esp_camera.h`
     - SHA-256: `8E295497B505B1A717919EE4773283D2ACF1A283EFA27AC1EA72823045152C0F`
3. **Build Record của Espressif (`versions.txt` trong archive):**
   - Tệp `versions.txt` lưu kèm gói build ghi rõ mốc công cụ:
     - `lib-builder: master ee57070`
     - `esp-idf: v5.5.5 b774170ff46`
     - `arduino: master 0d7a8614b`
   - Commit của `esp32-arduino-lib-builder`: Full SHA `ee57070cc8571c488a64b8ef028684acdc6ff5e2` (ngày 2026-07-14T13:33:45Z, tác giả me-no-dev).
4. **Manifest quản lý Component (`main/idf_component.yml` tại `ee57070`):**
   - Tệp manifest của `esp32-arduino-lib-builder` tại commit `ee57070` ghim dependency `esp32-camera` như sau:
     ```yaml
     espressif/esp32-camera:
       version: "master"
       git: https://github.com/espressif/esp32-camera.git
       require: public
       rules:
         - if: "target in [esp32, esp32s2, esp32s3]"
     ```
5. **Commit Revision nguồn bất biến của `espressif/esp32-camera`:**
   - Tại thời điểm commit `ee57070` (14/07/2026) và đóng gói bản phát hành core 3.3.11 (22–23/07/2026), commit HEAD mới nhất trên nhánh `master` của repo `espressif/esp32-camera` là:
     **`202df95d7b1dc72e9303ad78f47b8dc9f339e6a1`** (ngày 2026-06-05T17:48:33Z: *"Preserve repeated-start SCCB reads with fallback (#847)"*; commit kế tiếp của repo là ngày 14/09/2026).
    - **Xác nhận khớp mã nguồn 100% & Dấu vân tay mã máy:**
      - Header `driver/include/esp_camera.h` tại revision `202df95d7b` (được đưa vào từ commit `1484db7` và giữ nguyên qua tag `v2.1.6` / `2ac69a6`): SHA-256 = `8E295497B505B1A717919EE4773283D2ACF1A283EFA27AC1EA72823045152C0F` (khớp hoàn toàn đến từng byte với header đang cài đặt).
      - Dấu vân tay chuỗi trong thư viện nhị phân `libespressif__esp32-camera.a`: chuỗi `SCCB_Read data phase failed` (chỉ có từ `202df95`) có mặt trong `.a`, và chuỗi cũ `SCCB_Read Failed addr` (bị xóa ở `202df95`) không còn trong `.a`. Revision `202df95d7b1dc72e9303ad78f47b8dc9f339e6a1` đồng thời chính là tag phát hành `v2.1.7` của `espressif/esp32-camera`.
      - Toàn bộ các phân tích luồng điều khiển, hàm gán timestamp, hàng đợi và timeout dưới đây được trích xuất trực tiếp từ mã nguồn tại revision bất biến `202df95d7b1dc72e9303ad78f47b8dc9f339e6a1` và đối chiếu với mã máy dịch ngược của `libespressif__esp32-camera.a`.

### 2.2 Bảng Đối chiếu Nguồn ↔ Mã máy và Các Kết luận Kỹ thuật

| Chủ đề | Vị trí mã nguồn (`esp32-camera@202df95`) | Mã máy `libespressif__esp32-camera.a` | Kết luận & Giới hạn kỹ thuật |
| --- | --- | --- | --- |
| **Timebase & Clock** | `driver/cam_hal.c:235-248` (`cam_start_frame`):<br>`uint64_t us = (uint64_t)esp_timer_get_time();`<br>`cam_obj->frames[*frame_pos].fb.timestamp.tv_sec = us / 1000000UL;`<br>`cam_obj->frames[*frame_pos].fb.timestamp.tv_usec = us % 1000000UL;` | `cam_hal.c.obj` relocation `.text.cam_start_frame` gọi tuần tự:<br>1. `ll_cam_start`<br>2. kích hoạt VSYNC tầng thấp (`ll_cam`)<br>3. `esp_timer_get_time`<br>4. `__udivdi3`<br>5. `__umoddi3`<br>Ký hiệu `gettimeofday`: **0 lần**. | **Nguồn đồng hồ đồng nhất:** Khung hình lấy timestamp từ `esp_timer_get_time()` (nguồn monotonic microsecond, cùng nguồn với HTTP server).<br>**Giới hạn:** Mốc này là lúc bắt đầu nhận DMA trong task FreeRTOS `cam_task`, có độ trễ lập lịch task so với VSYNC phần cứng; phơi sáng rolling shutter của cảm biến diễn ra trước mốc nhận DMA. |
| **Hàng đợi `GRAB_LATEST`** | `driver/cam_hal.c:608-612` (`cam_config`):<br>`if (config->grab_mode == CAMERA_GRAB_LATEST && cam_obj->frame_cnt > 1)`<br>`  frame_buffer_queue_len = cam_obj->frame_cnt - 1;`<br>`cam_obj->frame_buffer_queue = xQueueCreate(frame_buffer_queue_len, ...);`<br>`driver/cam_hal.c:404-420`: khi queue đầy, pop khung cũ (`cam_give`), push khung mới. | `cam_hal.c.obj` section `.text.cam_config`: tính độ dài queue = `frame_cnt - 1` khi `grab_mode == 1` và `frame_cnt > 1`. Section `.text.cam_task` gọi `xQueueReceive(..., 0)` và `cam_give`. | Với cấu hình baseline `fb_count = 2`, hàng đợi nhận khung có độ dài đúng bằng **1** (`2 - 1 = 1`). Khi hàng đợi đầy, `cam_task` pop khung cũ ra giải phóng và đẩy khung mới nhất vào. Khung trong hàng đợi luôn là khung mới nhất đã nhận xong. |
| **Cận chặn driver** | `driver/esp_camera.c:387-394` (`esp_camera_fb_get`):<br>`#define FB_GET_TIMEOUT (4000 / portTICK_PERIOD_MS)`<br>`cam_take(FB_GET_TIMEOUT);`<br>`driver/cam_hal.c:686-772` (`cam_take`):<br>Vòng lặp `for(;;)` với `xTaskGetTickCount`, `xQueueReceive(..., remaining)`, `ll_cam_dma_reset`, `vTaskDelay(1)`, `cam_verify_jpeg_eoi`, `cam_give`. | `esp_camera.c.obj` section `.text.esp_camera_fb_get`: nạp hằng số `4000` (`movi a10, 160; addmi a10, a10, 0xf00`) truyền vào `cam_take`. | **Mức chứng cứ thực:** `4000 ticks` (~4000 ms ở 1000 Hz) là **đối số timeout quan sát được** truyền vào `cam_take`.<br>**CHƯA CHỨNG MINH ĐÂY LÀ CẬN CỨNG 4.000 s CHO MỌI ĐƯỜNG:** Vòng lặp `for(;;)` bên trong có thể kéo dài hơn do độ trễ trả quyền CPU của FreeRTOS, chi phí quét EOI cache, hoặc reset DMA khi Wi-Fi bận; ngược lại nếu khung có sẵn thì trả về gần như tức thì. Không biến cận driver chưa biết thành budget an toàn C5. |
| **Quyền sở hữu Buffer** | `driver/esp_camera.c:404-410` (`esp_camera_fb_return`): gọi `cam_give(fb);`.<br>`driver/cam_hal.c:771`: tự động `cam_give` khung JPEG hỏng (thiếu EOI). | `esp_camera.c.obj` gọi trực tiếp `cam_give`. | Khung do `esp_camera_fb_get()` trả về thuộc sở hữu của caller cho đến khi gọi `esp_camera_fb_return()`. Mọi nhánh thoát của `/capture_fresh` (lỗi, timeout, stale) **bắt buộc phải gọi `esp_camera_fb_return(fb)`** để tránh rò rỉ bộ đệm làm cạn kiệt DMA/PSRAM. |

### 2.3 Phân tích Timebase, Giới hạn Đồng hồ và Timeout Hệ thống

1. **Chứng minh tính hợp lệ của phép so sánh $t_{\text{frame}} > t_{\text{req}}$:**
   - Trong `driver/include/esp_camera.h`:
     ```c
     typedef struct {
         uint8_t * buf;              /*!< Pointer to the pixel data */
         size_t len;                 /*!< Length of the buffer in bytes */
         size_t width;               /*!< Width of the buffer in pixels */
         size_t height;              /*!< Height of the buffer in pixels */
         pixformat_t format;         /*!< Format of the pixel data */
         struct timeval timestamp;   /*!< Timestamp since boot of the first DMA buffer of the frame */
     } camera_fb_t;
     ```
   - Cả `t_req` (lấy lúc handler nhận HTTP request) và `t_frame` (lấy trong `cam_start_frame`) đều gọi trực tiếp hàm `esp_timer_get_time()`.
   - Hàm `esp_timer_get_time()` trên ESP-IDF sử dụng đồng hồ phần cứng monotonic microsecond (bắt đầu từ 0 lúc boot, không bị ảnh hưởng bởi NTP/RTC hay múi giờ).
   - Quy đổi mốc thời gian khung hình:
     $$\text{t\_frame} = (\text{int64\_t})\text{fb}\to\text{timestamp.tv\_sec} \times 1000000\text{LL} + (\text{int64\_t})\text{fb}\to\text{timestamp.tv\_usec}$$
   - Vì cùng nguồn và cùng đơn vị, phép so sánh $\text{t\_frame} > \text{t\_req}$ là hoàn toàn hợp lệ về mặt toán học và vật lý để khẳng định khung hình được bắt đầu nhận sau mốc request.

2. **Giới hạn kỹ thuật cần ghi nhận:**
   - Timestamp phản ánh thời điểm task `cam_task` bắt đầu nhận DMA khung hình, có độ trễ lập lịch FreeRTOS so với tín hiệu VSYNC phần cứng.
   - Cảm biến OV3660 sử dụng kiến trúc màn trập lăn (rolling shutter), quá trình phơi sáng của các dòng quét đầu tiên diễn ra trước mốc nhận DMA. Do đó mốc DMA không đồng nhất với thời điểm bắt đầu phơi sáng.
   - Phép so sánh $t_{\text{frame}} > t_{\text{req}}$ là điều kiện cần để đảm bảo không lấy khung cũ trong bộ đệm; bằng chứng ảnh đúng trạng thái laser bắt buộc phải qua chuỗi kiểm chứng không tuần hoàn C5/C7 ≥ 100 chu kỳ theo SPEC 6.4.

3. **Phân biệt 4 tầng Timeout trong hệ thống và Cảnh báo Ngân sách Laser:**
   - **Tầng 1 — Cận chặn driver (`FB_GET_TIMEOUT`):** `cam_take(4000 ticks)`. Vòng lặp kiểm tra đồng hồ của ứng dụng (`timeout_us`) **không tạo thành cận cứng** ngắt được lời gọi driver đang chặn. Nếu driver đang chặn đợi DMA, handler phải đợi đến khi `fb_get()` trả về hoặc hết hạn bên trong `cam_take`.
   - **Tầng 2 — Timeout vòng lặp loại stale của handler (Tham số đề xuất):** Đề xuất `timeout_us = 1500000LL` (1.5 s). Kiểm tra giữa các lần gọi `fb_get()`. Nếu tổng thời gian vượt quá ngưỡng này hoặc đã loại quá 4 khung cũ (dừng ở lần thứ 5), handler dừng lặp và trả lỗi 503.
   - **Tầng 3 — Timeout socket HTTP (`httpd_resp_send`):** Do cấu hình socket của HTTP server quản trị.
   - **Tầng 4 — Timeout phía client (PC):** Client đặt timeout HTTP (ví dụ 5000 ms).
   - *Cảnh báo an toàn laser:* Liên động an toàn của Nucleo giới hạn laser tối đa 5000 ms (`SPEC` mục 9). Vì đối số timeout danh nghĩa của driver là `4000 ticks` (~4000 ms ở 1000 Hz) và cận thời gian thực chưa biết (do FreeRTOS scheduling, DMA reset, EOI verify cache), handler và client phải phối hợp để đảm bảo client kịp gửi lệnh `LASER OFF` trước khi liên động phần cứng trip. Tham số đề xuất 1.5 s, đối số timeout danh nghĩa của driver và cận thời gian thực chưa biết (chưa chứng minh cận cứng 4.000 s) là các điểm kỹ thuật cần Planner/người dùng quyết định trước Q6.

---

## 3. Giao thức HTTP `/capture_fresh`

### 3.1 Cú pháp yêu cầu (Request)
- **Phương thức:** `GET`
- **URI:** `/capture_fresh`
- **Header gửi kèm (tùy chọn):** `Accept: image/jpeg`

### 3.2 Cú pháp phản hồi thành công (Response 200 OK)
- **HTTP Status:** `200 OK`
- **Content-Type:** `image/jpeg`
- **Content-Disposition:** `inline; filename=capture_fresh.jpg`
- **Access-Control-Allow-Origin:** `*`
- **Các Header chẩn đoán bắt buộc (5 headers):**
  1. `X-Frame-Id`: Số nguyên không dấu dạng chuỗi `%llu` (ví dụ `1`, `2`, `3`...).
  2. `X-Boot-Id`: Chuỗi 32 ký tự hex thường biểu diễn token 128-bit ngẫu nhiên của chu kỳ khởi động hiện tại (ví dụ `4a8f9c1b2e3d4f5a6b7c8d9e0f1a2b3c`).
  3. `X-Timestamp`: Chuỗi thời gian DMA của khung hình: `<sec>.<usec>` với phần micro giây bắt buộc đệm đủ 6 chữ số dạng `%06u` (ví dụ `45.123456`, `45.000005`).
  4. `X-Request-Timestamp`: Chuỗi thời gian nhận request: `<sec>.<usec>` với phần micro giây bắt buộc đệm đủ 6 chữ số dạng `%06u` (ví dụ `45.098765`, `45.000000`).
  5. `X-Discarded-Frames`: Số khung hình cũ bị loại bỏ trước khi lấy được khung này, dạng số nguyên `%u` (ví dụ `0`, `1`, `2`).
- **Body:** Dữ liệu nhị phân ảnh JPEG nguyên vẹn (bắt đầu bằng byte `0xFF 0xD8`, kết thúc bằng `0xFF 0xD9`).

### 3.3 Miền giá trị, Kiểu dữ liệu và Chính sách Tràn
1. **Kiểu dữ liệu và miền giá trị từng Header:**
   - `X-Frame-Id`: Kiểu số nguyên không dấu 64-bit (`uint64_t` / `unsigned long long`). Miền giá trị: $[1, 2^{64}-1]$ (`UINT64_MAX`).
   - `X-Boot-Id`: Chuỗi đúng 32 ký tự hex chữ thường (`[0-9a-f]{32}`), đại diện cho 128-bit ngẫu nhiên sinh bằng `esp_fill_random()` sau khi Wi-Fi sẵn sàng.
   - `X-Timestamp`: `<sec>.<usec>` với `sec` $\in [0, 2^{32}-1]$, `usec` $\in [000000, 999999]$ (bắt buộc đủ 6 chữ số đệm 0).
   - `X-Request-Timestamp`: `<sec>.<usec>` với `sec` $\in [0, 2^{32}-1]$, `usec` $\in [000000, 999999]$ (bắt buộc đủ 6 chữ số đệm 0).
   - `X-Discarded-Frames`: Số nguyên không âm $\in [0, 4]$ cho phản hồi thành công 200 OK (tối đa 4 khung cũ bị loại trước khi nhận khung tươi; nếu đến lần thứ 5 vẫn cũ thì trả lỗi 503).
2. **Quy tắc phân tích phía Client (PC):**
   - **Không phân biệt hoa/thường:** Theo RFC 7230, header HTTP là case-insensitive. Client phải tìm kiếm header không phân biệt hoa thường (`x-frame-id`, `X-Frame-Id`, `X-FRAME-ID`).
   - **Phân tích số nguyên microsecond:** Phân tích `X-Timestamp` thành $t_f = \text{sec} \times 10^6 + \text{usec}$ và `X-Request-Timestamp` thành $t_r = \text{sec} \times 10^6 + \text{usec}$.
   - **Kiểm tra bất biến:** Bắt buộc $t_f > t_r$ (nghiêm ngặt). Nếu $t_f \le t_r$, client coi là ảnh không tươi (stale) và xử lý lỗi.
3. **Quy tắc Frame ID và Chính sách Tràn (Overflow Policy):**
   - **Kiểu dữ liệu và miền giá trị:** Bộ đếm Frame ID sử dụng kiểu số nguyên không dấu 64-bit `uint64_t` (`unsigned long long`, in ra dạng `%llu`), với miền giá trị $[1, 2^{64}-1]$ (`UINT64_MAX`).
   - **Giá trị ban đầu:** Sau khi bo khởi động lại, `s_frame_id_counter` bắt đầu từ 0. Khung hình tươi hợp lệ đầu tiên được cấp `X-Frame-Id = 1`.
   - **Thời điểm cấp phát tại Server:** Server tăng `s_frame_id_counter++` khi đã có buffer khung hình tươi hợp lệ và chuẩn bị gửi header HTTP vào socket. Nếu quá trình gửi body vào socket bị đứt kết nối (TCP broken pipe / reset), Frame ID này được coi là **đã tiêu thụ** tại server và không cấp lại, tránh cấp trùng ID cho ảnh khác. Client sẽ phát hiện ID bị nhảy cóc ở lần request tiếp theo (mất khung).
   - **Chính sách tràn:** Miền giá trị $2^{64}-1$ là thực tế vô hạn đối với vòng đời hệ thống. Tuy nhiên, quy định hợp đồng chặt chẽ: **CẤM QUAY VÒNG IM LẶNG (NO SILENT WRAP/OVERFLOW)**. Nếu bộ đếm chạm `UINT64_MAX`, server được phép cấp `UINT64_MAX` một lần; lượt tiếp theo phải từ chối yêu cầu, trả HTTP 500 `ERROR FRAME_ID_OVERFLOW` để buộc khởi động lại bo.
4. **Quy tắc Boot ID và Phát hiện Khởi động lại (Reboot detection theo D043):**
   - Token 128-bit `X-Boot-Id` được sinh một lần duy nhất khi firmware khởi động, giữ nguyên suốt thời gian sống của chu kỳ boot (kể cả khi Wi-Fi reconnect hoặc server init lại).
   - Client lưu `X-Boot-Id` của request đầu tiên trong phiên. Trong các request tiếp theo:
     + Nếu `X-Boot-Id` thay đổi: Bo **chắc chắn đã bị reboot** (`CAMERA_REBOOT`), kể cả khi `X-Frame-Id` hay `X-Timestamp` mới có giá trị lớn hơn mốc trước đó. Toàn bộ phiên quét bị vô hiệu hóa lập tức.
     + Nếu `X-Boot-Id` không đổi: `X-Frame-Id` bắt buộc phải là `last_frame_id + 1` (trong phiên 1 client duy nhất). Nếu ID lùi hoặc trùng $\implies$ lỗi tính toàn vẹn dữ liệu; nếu ID nhảy cóc $\implies$ mất khung mạng.

### 3.4 Chuỗi ví dụ minh họa Response
Dưới đây là ví dụ chuỗi phản hồi tuần tự trong cùng một chu kỳ boot (giả sử Boot ID `4a8f9c1b2e3d4f5a6b7c8d9e0f1a2b3c`):

- **Lần 1 (Khung đầu sau boot, hàng đợi rỗng):**
  ```http
  HTTP/1.1 200 OK
  Content-Type: image/jpeg
  X-Frame-Id: 1
  X-Boot-Id: 4a8f9c1b2e3d4f5a6b7c8d9e0f1a2b3c
  X-Timestamp: 12.045000
  X-Request-Timestamp: 12.010000
  X-Discarded-Frames: 0
  ```
  *(Kiểm tra: $12045000 > 12010000 \implies$ Đạt fresh).*

- **Lần 2 (Có 1 khung cũ trong hàng đợi):**
  ```http
  HTTP/1.1 200 OK
  Content-Type: image/jpeg
  X-Frame-Id: 2
  X-Boot-Id: 4a8f9c1b2e3d4f5a6b7c8d9e0f1a2b3c
  X-Timestamp: 12.580000
  X-Request-Timestamp: 12.520000
  X-Discarded-Frames: 1
  ```
  *(Khung cũ tại $12.510000 \le 12.520000$ đã bị loại, khung trả về đạt fresh).*

- **Lần 3 (Khung cũ trùng mốc request $t_f = t_r$):**
  - Khung tại $13.100000 = 13.100000$ bị loại vì không thỏa $t_f > t_r$. Khung tiếp theo đạt $13.133000$:
  ```http
  HTTP/1.1 200 OK
  Content-Type: image/jpeg
  X-Frame-Id: 3
  X-Boot-Id: 4a8f9c1b2e3d4f5a6b7c8d9e0f1a2b3c
  X-Timestamp: 13.133000
  X-Request-Timestamp: 13.100000
  X-Discarded-Frames: 1
  ```

---

## 4. Quản lý trạng thái và Xử lý tranh chấp (Concurrency & Mutex theo D043)

### 4.1 Phân tích các luồng và Mô hình Server
Hệ thống firmware có hai server HTTP chạy trên FreeRTOS:
1. `camera_httpd` (Port 80): Xử lý `/control`, `/status`, `/capture`, `/capture_fresh`, `/bmp`, `/resolution`, `/xclk`, `/reg`, `/greg`, `/pll` và trang chủ web root.
2. `stream_httpd` (Port 81): Xử lý `/stream` (vòng lặp liên tục đẩy MJPEG).

**Đặc điểm mô hình Server Port 80 và Cổng 81:**
- Hàm `httpd_start` của `esp_http_server` tạo đúng 1 task FreeRTOS cho mỗi server instance.
- Tuy nhiên, để đảm bảo an toàn tuyệt đối cho phần cứng cảm biến và DMA khi có luồng stream Port 81 chạy song song, hoặc khi có các tác vụ quản trị, firmware áp dụng một Mutex chung FreeRTOS `s_cam_mutex` bảo vệ mọi handler chạm camera/sensor.

### 4.2 Cơ chế khóa liên động toàn diện với Mutex chung (`s_cam_mutex`)
Theo quyết định D043:
1. **Mutex duy nhất:** Khởi tạo `static SemaphoreHandle_t s_cam_mutex = NULL;` tại `startCameraServer()` (sử dụng `xSemaphoreCreateMutex()`).
2. **Cờ trạng thái Stream:** `static std::atomic<bool> s_stream_active(false);` để phân biệt nguồn gốc tranh chấp một cách an toàn đồng bộ (không coi `volatile` là mutex).
3. **Phạm vi bảo vệ:** Mọi handler có truy cập vào `esp_camera_fb_get()` hoặc thao tác thanh ghi cảm biến `sensor_t` đều phải chiếm `s_cam_mutex` trước khi thao tác:
   - `/capture_fresh`
   - `/capture`
   - `/bmp`
   - `/stream`
   - `/control`
   - `/resolution`
   - `/xclk`
   - `/reg`, `/greg`
   - `/pll`
   - `/status`
   - Web root sensor info (`index_handler` đọc thông tin sensor).
4. **Thời gian chờ Mutex danh nghĩa:** Chờ danh nghĩa 100 ms (`pdMS_TO_TICKS(100)`).
5. **Quy tắc phản hồi khi tranh chấp (không lấy được Mutex trong 100 ms):**
   - Nếu `s_stream_active == true`: Trả về `HTTP 503` với body `ERROR CAMERA_BUSY_STREAM`.
   - Nếu `s_stream_active == false`: Trả về `HTTP 503` với body `ERROR CAMERA_BUSY_CAPTURE`.
6. **Quy tắc giải phóng Mutex:**
   - Trong mọi nhánh thoát (thành công, lỗi mạng, lỗi driver, timeout), bắt buộc gọi `xSemaphoreGive(s_cam_mutex)` trước khi return.
   - Đối với `/stream`: Task stream chiếm `s_cam_mutex`, đặt `s_stream_active = true`, giữ mutex trong suốt vòng lặp stream. Khi vòng lặp stream kết thúc (client disconnect hoặc lỗi), đặt `s_stream_active = false` và gọi `xSemaphoreGive(s_cam_mutex)`.

### 4.3 Hợp đồng Endpoint `/status` và Telemetry Heap (theo Quyết định D044)
Endpoint `GET /status` trên Port 80 trả về trạng thái cảm biến cùng hai trường chẩn đoán bộ nhớ:
1. **Bảo vệ Mutex:** Bắt buộc chiếm `s_cam_mutex` với thời gian chờ 100 ms (`pdMS_TO_TICKS(100)`). Nếu thất bại, trả HTTP 503 `ERROR CAMERA_BUSY_STREAM` hoặc `ERROR CAMERA_BUSY_CAPTURE`.
2. **Hai trường Telemetry Bộ nhớ (D044):**
   - `heap_internal_free_bytes`: Số nguyên JSON không âm, đơn vị byte, đo từ `heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)`. Phản ánh tổng vùng nhớ RAM nội rảnh cho truy cập 8-bit tại thời điểm lấy mẫu.
   - `heap_psram_free_bytes`: Số nguyên JSON không âm, đơn vị byte, đo từ `heap_caps_get_free_size(MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)`. Phản ánh tổng vùng nhớ PSRAM rảnh cho truy cập 8-bit tại thời điểm lấy mẫu.
   - *Ý nghĩa và phạm vi:* Hai trường này là số liệu telemetry động phục vụ khảo sát bộ đệm/bộ nhớ hệ thống; **không thuộc controls** hay thanh ghi cấu hình cảm biến (`expected_registers`) của camera profile. Dù `capture_session.compare_status()` có thể liệt kê hai trường heap là thay đổi giữa các snapshot, sự thay đổi này là biến động RAM runtime được dự liệu trước và không ảnh hưởng đến đánh giá trôi cấu hình hay verdict phiên quét (vốn chỉ xét framesize, quality, controls và các thanh ghi camera). Giá trị 0 được xuất thật nếu không có/hết RAM; sự tồn tại của trường không cấu thành chứng minh PSRAM hoạt động hay firmware không rò rỉ bộ nhớ.
3. **Chính sách An toàn Bộ đệm JSON:**
   - Bộ đệm JSON danh nghĩa 2048 byte (`char json_response[2048]`).
   - Mọi thao tác ghi (`status_json_append`, `print_reg_safe`) bắt buộc kiểm tra biên `n < 0 || n >= (end - *p)`, dành sẵn chỗ cho dấu đóng `}` và ký tự kết thúc `\0`.
   - Nếu xảy ra lỗi định dạng hoặc vượt quá dung lượng đệm: lập tức dừng, giải phóng Mutex `xSemaphoreGive(s_cam_mutex)`, và trả HTTP 500 với body `ERROR CAMERA_INTERNAL`. Tuyệt đối **không gửi HTTP 200 kèm chuỗi JSON bị cắt cụt**.

---

## 5. Trình tự thực thi FSM của Handler `/capture_fresh`

### 5.1 Các bước thực thi chi tiết
```
[Client GET /capture_fresh]
          │
          ▼
1. Kiểm tra tranh chấp và Chiếm Mutex:
   - Thử xSemaphoreTake(s_cam_mutex, pdMS_TO_TICKS(100)):
       -> Thất bại:
            Nếu s_stream_active == true: Trả HTTP 503 "ERROR CAMERA_BUSY_STREAM"
            Ngược lại: Trả HTTP 503 "ERROR CAMERA_BUSY_CAPTURE"
   - Sau khi chiếm được Mutex:
       Nếu s_stream_active == true:
            Nhả Mutex, trả HTTP 503 "ERROR CAMERA_BUSY_STREAM"
          │ (Đã chiếm được khóa Mutex độc quyền)
          ▼
2. Ghi mốc thời gian nhận yêu cầu & Thiết lập hạn chót (Deadline):
   int64_t t_req = esp_timer_get_time();
   int64_t t_deadline = t_req + 1500000LL; // Hạn chót 1.5 s
   uint32_t discarded_count = 0;
   camera_fb_t *fb = NULL;
          │
          ▼
3. Vòng lặp lấy khung hình tươi (Fresh Frame Loop):
   ┌──▶ Kiểm tra hạn chót:
   │    Nếu esp_timer_get_time() >= t_deadline:
   │        -> Nhả Mutex, trả HTTP 503 "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME"
   │
   │    Gọi fb = esp_camera_fb_get();
   │    int64_t t_now = esp_timer_get_time();
   │
   │    Kiểm tra hạn chót ngay sau khi nhận kết quả driver (kể cả khi nhận khung fresh hoặc NULL):
   │    Nếu t_now >= t_deadline:
   │        -> Quá hạn chót! Giải phóng buffer nếu có: if (fb) { esp_camera_fb_return(fb); fb = NULL; }
   │        -> Nhả Mutex: xSemaphoreGive(s_cam_mutex);
   │        -> Trả HTTP 503 "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME"
   │
   │    Nếu fb == NULL (và t_now < t_deadline):
   │        -> Driver hết hạn timeout hoặc hết buffer DMA/PSRAM trước hạn!
   │        -> Nhả Mutex, trả HTTP 503 "ERROR CAMERA_NO_BUFFER"
   │
   │    Tính t_frame = fb->timestamp.tv_sec * 1000000LL + fb->timestamp.tv_usec;
   │
   │    Nếu t_frame > t_req:
   │        -> ĐẠT: Khung hình tươi hợp lệ trong hạn! Thoát vòng lặp.
   │
   │    Nếu t_frame <= t_req:
   │        -> Khung cũ (stale frame)!
   │        discarded_count++;
   │        Gọi esp_camera_fb_return(fb); fb = NULL;
   │
   │        Kiểm tra giới hạn stale tối đa:
   │        Nếu discarded_count >= 5 HOẶC esp_timer_get_time() >= t_deadline:
   │            -> Đã gặp stale thứ 5 hoặc quá hạn: DỪNG NGAY, không gọi fb_get lần 6!
   │            -> Nhả Mutex, trả HTTP 503 "ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME"
   └─── Tiếp tục vòng lặp (lấy khung tiếp theo).
          │
          ▼
4. Kiểm tra Định dạng & Cấp Frame ID an toàn:
   - Kiểm tra định dạng: Nếu fb->format != PIXFORMAT_JPEG:
       -> Gọi esp_camera_fb_return(fb); fb = NULL;
       -> Nhả Mutex, trả HTTP 500 "ERROR CAMERA_UNSUPPORTED_FORMAT"
   - Cấp Frame ID an toàn:
       Gọi fresh_capture_allocate_id(&s_frame_id_counter, &s_max_served, &assigned_id).
       Nếu thất bại (tràn UINT64_MAX vượt 1 lần):
           -> Gọi esp_camera_fb_return(fb); fb = NULL;
           -> Nhả Mutex, trả HTTP 500 "ERROR FRAME_ID_OVERFLOW"
          │
          ▼
5. Gửi Header HTTP (5 Header bắt buộc theo chuẩn RFC 7230):
   - Đặt kiểu nội dung: httpd_resp_set_type(req, "image/jpeg")
   - Đặt 5 headers:
       X-Frame-Id: <assigned_id>
       X-Boot-Id: <32 ký tự hex thường>
       X-Timestamp: <sec>.<usec_6_digits>
       X-Request-Timestamp: <sec>.<usec_6_digits>
       X-Discarded-Frames: <discarded_count>
       Content-Disposition: inline; filename=capture_fresh.jpg
   - Kiểm tra kết quả các hàm set header / set type:
       Nếu bất kỳ lệnh nào trả lỗi khác ESP_OK:
           -> Gọi esp_camera_fb_return(fb); fb = NULL;
           -> Nhả Mutex: xSemaphoreGive(s_cam_mutex);
           -> Trả HTTP 500 "ERROR CAMERA_INTERNAL"
          │
          ▼
6. Gửi Body JPEG & Dọn dẹp tài nguyên:
   - Gửi dữ liệu fb->buf (độ dài fb->len) qua httpd_resp_send().
   - Luôn giải phóng buffer: esp_camera_fb_return(fb); fb = NULL;
   - Luôn nhả Mutex: xSemaphoreGive(s_cam_mutex);
          │
          ▼
[Hoàn tất Response 200 OK]
```

### 5.2 Xử lý ngoại lệ và ngắt kết nối giữa chừng
- Nếu trong quá trình gửi JPEG client đóng kết nối (TCP Reset/Broken pipe):
  - `httpd_resp_send()` trả về mã lỗi (`ESP_FAIL`).
  - Handler vẫn bảo đảm giải phóng tài nguyên: gọi `esp_camera_fb_return(fb)` và `xSemaphoreGive(s_cam_mutex)`.
  - Frame ID đã được tiêu thụ (không rollback để tránh nguy cơ client nhận 2 ảnh khác nhau có cùng ID).

### 5.3 Ma trận quy tắc xử lý phía Client (PC)
Khi nhận phản hồi từ `/capture_fresh`, client phải áp dụng ma trận kiểm tra sau:

| Tình huống Client gặp phải | Dấu hiệu nhận biết | Xử lý của Client |
| :--- | :--- | :--- |
| **Thiếu header bắt buộc** | Phản hồi 200 nhưng thiếu một trong 5 header: `X-Frame-Id`, `X-Boot-Id`, `X-Timestamp`, `X-Request-Timestamp`, `X-Discarded-Frames`. | Coi là lỗi giao thức, hủy khung hình, trả FAIL. |
| **Header sai cú pháp / giá trị** | Header chứa ký tự không phải số/hex, NaN, Inf, số âm, boot ID không đúng 32 hex, hoặc usec không đủ 6 chữ số. | Hủy khung hình, trả FAIL với mã lỗi parse header. |
| **Khởi động lại bo (Reboot)** | `X-Boot-Id` khác với `boot_id` ban đầu ghi nhận ở đầu phiên quét. | Bo đã bị reset/reboot giữa chừng: Vô hiệu hóa toàn bộ phiên quét, dừng và báo lỗi reboot. |
| **Khung hình không tươi** | Phân tích số nguyên cho thấy $t_f \le t_r$. | Hủy khung hình, ghi nhận lỗi stale frame từ firmware. |
| **Frame ID lùi hoặc trùng** | Trong cùng một Boot ID, `X-Frame-Id <= last_frame_id` hoặc timestamp lùi. | Lỗi tính toàn vẹn dữ liệu: Dừng phiên quét và báo lỗi. |
| **Frame ID nhảy cóc** | Trong cùng một Boot ID, `X-Frame-Id > last_frame_id + 1`. | Đã có khung bị mất mạng giữa chừng: Ghi nhận cảnh báo mất khung trong `captures.jsonl`. |
| **Ảnh JPEG bị cắt cụt / hỏng** | Kích thước ảnh nhỏ bất thường, thiếu byte kết thúc EOI `0xFF 0xD9`, hoặc lỗi giải mã JPEG. | Hủy khung hình, lưu payload lỗi phục vụ điều tra, thực hiện chụp lại (retry). |
| **Mất kết nối TCP / Lỗi mạng** | Connection reset, Broken pipe hoặc lỗi socket cấp thấp trước hoặc trong khi đọc body. | Gán nhãn `Socket/Network error`, vô hiệu hóa phiên quét hiện tại (INVALID); lưu phần body/raw đã nhận phục vụ điều tra. |
| **Mất kết nối TCP / Timeout** | Socket inactivity timeout (quá 5 s) trước hạn chót tổng HOẶC request vượt quá deadline tổng từng request 10 s. | Vô hiệu hóa phiên quét hiện tại; phân biệt rõ `TIMEOUT_SOCKET` (khi inactivity quá 5 s trước hạn tổng) và `TIMEOUT_TOTAL_DEADLINE` (khi watchdog Timer hoặc thời gian request vượt quá 10 s); probe thu hồi Timer và đóng socket an toàn trong cùng tiến trình, không rò rỉ luồng chạy ngầm. |

### 5.4 Kiến trúc Timeout và Quản lý Tài nguyên của Probe Client (R11 & R12)
1. **Cơ chế Timeout 2 lớp (R11):**
   - Probe HTTP client (`FreshCaptureClient`) chạy trong cùng tiến trình, quản lý kết nối socket HTTP tuần tự qua `TrackedHTTPConnection`.
   - **Deadline tổng từng request (Single-request Total Deadline):** Mặc định 10.0 s (áp dụng cho từng request riêng biệt, không phải giới hạn toàn phiên/buổi). Được bảo vệ bởi `threading.Timer` watchdog kích hoạt `s.shutdown()` và `s.close()` nếu request vượt quá thời gian cho phép.
   - **Socket Inactivity Timeout:** Mặc định 5.0 s. Được cập nhật động trước mỗi thao tác mạng (`update_sock_timeout`) theo công thức $\min(\text{timeout}, \text{remaining\_sec})$. Nếu còn dưới 5 s trước deadline, socket timeout sẽ co lại đúng bằng thời gian còn lại.
2. **Thu hồi tài nguyên và dọn dẹp luồng (Cleanup - R11):**
   - Sau khi kết thúc mỗi lượt request (thành công hoặc có ngoại lệ), khối `finally` luôn gọi `timer.cancel()` và đóng kết nối socket.
   - Không tạo hay để sót luồng watchdog/worker chạy ngầm sau khi lượt kết thúc; không spawn/reap tiến trình con (subprocess).
3. **Chẩn đoán lỗi Timeout chính xác (R12):**
   - **`TIMEOUT_TOTAL_DEADLINE`:** Kích hoạt khi watchdog Timer đã báo (`timed_out[0] == True`) HOẶC thời gian trôi qua $t_{\text{now}} - t_{\text{start}} \ge \text{deadline}$. Ưu tiên nhãn này khi xảy ra đua đúng biên.
   - **`TIMEOUT_SOCKET`:** Kích hoạt khi socket bị inactivity timeout (`socket.timeout` / `TimeoutError`) xảy ra trước hạn tổng ($t_{\text{now}} - t_{\text{start}} < \text{deadline}$) và watchdog Timer chưa báo.
   - **`Socket/Network error`:** Các lỗi mạng khác xảy ra trước hạn (ConnectionReset, HostUnreachable, v.v.).

---

## 6. Bảng mã lỗi HTTP và Chi tiết Phản hồi

| HTTP Status | Body phản hồi | Điều kiện kích hoạt | Hành động của Client (PC) |
| :--- | :--- | :--- | :--- |
| **200 OK** | `[Binary JPEG data]` | Thu được khung tươi thành công ($t_{\text{frame}} > t_{\text{req}}$), đủ 5 header. | Đọc ảnh, kiểm tra header, lưu trữ kết quả. |
| **503 Service Unavailable** | `ERROR CAMERA_BUSY_STREAM` | Kênh stream `/stream` đang mở và giữ khóa `s_cam_mutex`. | Dừng phiên quét, báo người dùng tắt stream. |
| **503 Service Unavailable** | `ERROR CAMERA_BUSY_CAPTURE` | Đang có một tác vụ khác giữ `s_cam_mutex` quá 100 ms. | Thử lại (retry) theo chính sách chụp lại của C5. |
| **503 Service Unavailable** | `ERROR CAMERA_NO_BUFFER` | `esp_camera_fb_get()` trả về `NULL`: do driver hết hạn timeout (~4000 ms trong `cam_take`) không nhận được khung từ cảm biến HOẶC không còn buffer DMA/PSRAM rảnh rỗi. | Ghi nhận lỗi camera: kiểm tra cáp/cảm biến không phát khung hoặc thiếu buffer PSRAM. |
| **503 Service Unavailable** | `ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME` | Đã loại 4 khung cũ liên tiếp và khung thứ 5 vẫn cũ, HOẶC thời gian chờ vượt quá hạn chót `t_req + 1500000 us`. | Báo lỗi cảm biến camera không sinh khung mới đúng hạn. Dừng chụp. |
| **500 Internal Error** | `ERROR CAMERA_UNSUPPORTED_FORMAT` | Khung hình nhận được không phải định dạng JPEG (`PIXFORMAT_JPEG`). | Báo lỗi cấu hình định dạng camera. Nhả buffer và mutex. |
| **500 Internal Error** | `ERROR FRAME_ID_OVERFLOW` | Bộ đếm Frame ID đã đạt trần `UINT64_MAX` và nhận thêm request tiếp theo. | Báo lỗi tràn bộ đếm, yêu cầu khởi động lại bo. |
| **500 Internal Error** | `ERROR CAMERA_INTERNAL` | Lỗi nội bộ framework HTTP. | Ghi nhận lỗi hệ thống. Nhả buffer và mutex. |

---

## 7. Cấu hình Bộ đệm: Quyết định D043 Chốt fb_count = 1 và Phân tích Kỹ thuật

### 7.1 Quyết định kỹ thuật D043 và Cơ sở thực nghiệm
Theo quyết định D043 và `docs/SPEC.md` mục 10:
- Cấu hình camera trong `CameraWebServerTest.ino` được thiết lập chính thức:
  - `config.fb_count = 1` cho nhánh PSRAM (`CAMERA_MODEL_ESP32S3_EYE` với JPEG); nhánh không-JPEG giữ `fb_count = 2`.
  - `config.grab_mode = CAMERA_GRAB_LATEST` cho định dạng JPEG.
- **Mức độ chứng cứ kỹ thuật:**
  - `fb_count = 1` tuân thủ đúng khuyến nghị SPEC §10 ("Bắt đầu với 1 buffer").
  - Nhận định về hiệu năng độ trễ và độ ổn định của cấu hình 1 buffer được coi là **giả thuyết kỹ thuật cần kiểm chứng thực nghiệm** thông qua đo đạc trên bo thật ESP32-S3 tại chặng Q6 (bài test Q6-T9/Q6-T10 với probe độc lập), không khẳng định tiên nghiệm khi chưa có số đo thực tế.

### 7.2 Phân tích kỹ thuật chuyên sâu dựa trên luồng mã nguồn driver (revision 202df95)
1. **Đối với cấu hình `fb_count = 1`:**
   - **Về hàng đợi:** Theo mã nguồn `cam_hal.c:cam_config`, điều kiện giảm độ dài hàng đợi (`queue_len = fb_count - 1`) chỉ áp dụng khi `fb_count > 1` kết hợp `CAMERA_GRAB_LATEST`. Với `fb_count = 1`, độ dài hàng đợi được khởi tạo là `queue_len = fb_count = 1`. Do đó hàng đợi vẫn chứa 1 phần tử; một khung cũ hoàn tất trước thời điểm request vẫn có thể nằm chờ sẵn trong hàng đợi khi ứng dụng gọi `esp_camera_fb_get()`. Vì vậy, cấu hình 1 buffer vẫn bắt buộc phải có cơ chế lọc timestamp $t_{\text{frame}} > t_{\text{req}}$.
   - **Về tuổi khung và độ trễ:** Khi mỗi lượt chụp cách nhau (ví dụ interval 200 ms), khung hình cuối cùng nằm trong hàng đợi sẽ đọng lại cho đến lượt request tiếp theo (tuổi khung chờ ước tính 87–207 ms). Do đó, cấu hình 1 buffer không tự động loại bỏ độ trễ đọng buffer nếu không có cơ chế lọc timestamp.
   - **Về quyền sở hữu và luồng nhận khung:** Theo nguồn `cam_hal.c`, cờ trạng thái ô nhớ (`en = 0`) chỉ được đặt khi khung đã hoàn tất (nhánh VSYNC sau `ll_cam_stop`), và chỉ được mở lại (`en = 1`) khi ứng dụng gọi `esp_camera_fb_return(fb)` dẫn tới `cam_give(fb)`. Với 1 buffer duy nhất, trong suốt khoảng thời gian HTTP server giữ buffer để gửi dữ liệu mạng (ước tính 30–80 ms), ô nhớ duy nhất này có `en = 0`. Khi đó, tại các mốc VSYNC tiếp theo, `cam_start_frame` không tìm được ô nhớ rảnh nên task chuyển sang IDLE và dừng nhận; các khung hình phát ra từ cảm biến trong thời gian này sẽ bị bỏ qua (dropped frames) cho đến VSYNC đầu tiên sau khi buffer được trả qua `cam_give`. Mức độ ảnh hưởng thực tế tới độ trễ lấy khung và tỷ lệ lỗi JPEG cần được đo đạc thực nghiệm trên bo ở Q6.
2. **Đối với cấu hình `fb_count = 2` kết hợp `CAMERA_GRAB_LATEST` và lọc Fresh Timestamp:**
   - **Về hàng đợi và độ tươi:** `queue_len = 2 - 1 = 1`. Hàng đợi chỉ lưu tối đa 1 khung mới nhất. Khung cũ trong hàng đợi (nếu có) được loại bỏ bằng vòng lặp so sánh timestamp $t_{\text{frame}} > t_{\text{req}}$ kết hợp trả buffer qua `esp_camera_fb_return`. Tuổi khung chờ trong hàng đợi ước tính nhỏ hơn (~47 ms).
   - **Về quyền sở hữu và khả năng rảnh buffer:** Khi có 2 buffer (A và B), nếu HTTP server đang giữ buffer A và hàng đợi đang giữ buffer B (hoặc B chưa được trả), `cam_get_next_frame` vẫn có thể không tìm thấy buffer rảnh trong pool. Do đó, cấu hình 2 buffer không thể loại trừ hoàn toàn nguy cơ thiếu buffer rảnh trong các tình huống tranh chấp runtime, dù được dự đoán giảm thiểu nguy cơ nghẽn buffer so với 1 buffer (đây là giả thuyết kỹ thuật cần đo đạc thực nghiệm).
   - **Tài nguyên bộ nhớ:** Tốn thêm 1 khung trong PSRAM (với bo N16R8 có 8MB PSRAM, dung lượng này hoàn toàn khả thi).
3. **Kết luận kỹ thuật và nghiệm thu trên bo:**
   - Việc chốt `fb_count = 1` theo D043 là cấu hình chính thức cho Q6. Các chỉ số về độ trễ thu nhận khung tươi, tỷ lệ khung bị loại (`X-Discarded-Frames`), và tính toàn vẹn JPEG sẽ được đo đạc, kiểm chứng và ghi nhận chính xác trong báo cáo Q6-T9/Q6-T10 trên phần cứng thực tế.

---

## 8. Kế hoạch triển khai Q6 và Ma trận kiểm chứng Tester

### 8.1 Các tệp trong danh sách trắng Q6
1. `firmware/esp32s3/CameraWebServerTest/app_httpd.cpp`: Thêm handler `capture_fresh_handler()`, đăng ký URI `/capture_fresh`, quản lý Mutex `s_cam_mutex`, Boot ID, và Frame ID. Bọc `s_cam_mutex` quanh tất cả các handler camera/sensor.
2. `firmware/esp32s3/CameraWebServerTest/CameraWebServerTest.ino`: Đặt `config.fb_count = 1` ở nhánh PSRAM, sinh Boot ID bằng `esp_fill_random()` sau khi Wi-Fi active.
3. `firmware/esp32s3/CameraWebServerTest/fresh_capture_core.h`: Module logic dùng chung (Boot ID helper, parse timestamp, kiểm tra điều kiện fresh, kiểm tra định dạng và tràn ID).
4. `pc/mock_camera.py`: Bổ sung mô phỏng endpoint `/capture_fresh`, giả lập stale queue, 5 header, Boot ID, tăng Frame ID và tiêm các mã lỗi.
5. `pc/fresh_capture_probe.py`: Công cụ kiểm tra độc lập tự động trên PC kiểm tra 5 header, Boot ID, tính đơn điệu, JPEG hợp lệ, deadline tổng 10 s, socket timeout 5 s, và `--selftest`.
6. `docs/procedures/quy-trinh-c5a-fresh-capture.md`: Quy trình thao tác nạp firmware và chạy probe chi tiết cho người dùng.
7. `firmware/esp32s3/README.md` và `pc/README.md`: Hướng dẫn vận hành.

### 8.2 Ma trận kiểm chứng Host và Bo thực tế cho chặng Q6

| Tầng kiểm thử | Kịch bản kiểm tra | Công cụ thực hiện | Kết quả mong đợi |
| :--- | :--- | :--- | :--- |
| **Host Mock** | 20 fresh capture liên tiếp trên `mock_camera.py` | `fresh_capture_probe.py --selftest` | 20/20 JPEG hợp lệ; ID tăng từ 1 đến 20; Boot ID giữ nguyên; $t_f > t_r$; `discarded >= 0`. |
| **Host Mock** | Tiêm hàng đợi 1, 2 khung stale | `fresh_capture_probe.py` | Bỏ qua đúng 1, 2 khung cũ; trả về khung tươi hợp lệ. |
| **Host Mock** | Tiêm lỗi thiếu header, sai định dạng `%06u`, NaN, Inf | `fresh_capture_probe.py` | Probe phát hiện lỗi cú pháp, trả mã lỗi thoát khác 0 xác định. |
| **Host Mock** | Giả lập stream đang chạy đồng thời | `fresh_capture_probe.py` | Nhận HTTP 503 `CAMERA_BUSY_STREAM`; không gây deadlock. |
| **Host Mock** | Giả lập reset bo giữa chừng (đổi Boot ID) | `fresh_capture_probe.py` | Probe phát hiện Boot ID thay đổi, dừng phiên và báo lỗi `CAMERA_REBOOT`. |
| **Bo thật S3 (Q6-T9)** | Nạp firmware và chạy 3 lượt × 20 fresh capture không laser với profile chính `cam_SVGA_q20_20260928` | Người dùng chạy lệnh theo quy trình thao tác | 3×20 JPEG hợp lệ phân giải 800×600; 5 header hợp lệ; ID tăng đơn điệu; Boot ID không đổi qua các lượt; $t_f > t_r$; không crash hay reset bo; đối chiếu snapshot profile trước/sau không trôi cấu hình. Telemetry heap trước và sau mỗi lượt được ghi nhận làm số liệu khảo sát (chưa cấu thành chứng minh không rò rỉ bộ nhớ). |
| **Bo thật S3 (Q6-T10)** | Mở trình duyệt xem `/stream` rồi gọi probe; thử nghiệm các ca tranh chấp/bận | Người dùng mở stream và chạy probe | Trả về HTTP 503 `CAMERA_BUSY_STREAM`, in và lưu đầy đủ status code và response body; camera không bị treo hay deadlock sau khi nhả stream. |
| **Bo thật S3 (Q6-T10)** | Nhấn nút RST trên bo khi đang chạy probe | Người dùng nhấn RST | Probe phát hiện Boot ID đổi hoặc mất kết nối, dừng an toàn, vô hiệu hóa phiên. |

---

## 9. Các thông số vận hành chốt cho Q6 (D043 & D044)

Theo quyết định D043 và D044:
1. **Số lượng bộ đệm cảm biến:** Chốt `fb_count = 1`, `CAMERA_GRAB_LATEST` cho JPEG PSRAM.
2. **Hạn mức thời gian loại stale:** `timeout_us = 1500000LL` (1.5 s).
3. **Số khung stale tối đa:** Dừng ở stale thứ 5 (loại tối đa 4 khung stale; nếu khung thứ 5 vẫn stale thì trả 503 `ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME` và không gọi `esp_camera_fb_get()` lần thứ 6).
4. **Timeout Mutex `s_cam_mutex`:** 100 ms danh nghĩa cho mọi handler camera/sensor Port 80 & 81.
5. **Cận chặn Probe PC (R11 & R12):** Deadline tổng từng request 10.0 s (quản lý bằng Timer watchdog và clock monotonic), socket inactivity timeout 5.0 s (cập nhật động theo thời gian còn lại). Phân biệt chẩn đoán 2 lớp lỗi: `TIMEOUT_SOCKET` (khi inactivity quá 5 s trước hạn tổng) và `TIMEOUT_TOTAL_DEADLINE` (khi chạm hạn 10 s); cleanup Timer và socket an toàn trong cùng tiến trình, không rò rỉ worker/watchdog.
6. **Profile nghiệm thu chính Q6-T9 (D044):** `cam_SVGA_q20_20260928` (800×600, quality 20, SHA-256 `5c32b27b4e52a2518cba01caee03d19d95db1c31a0e8dde4fa315635ad85dbe6`).
7. **Khảo sát Telemetry Bộ nhớ (D044):** Ghi nhận `heap_internal_free_bytes` và `heap_psram_free_bytes` từ `/status` trước và sau mỗi lượt chụp (tổng 6 snapshot/3 cặp) phục vụ khảo sát; không đặt ngưỡng nghiệm thu "không leak" khi chưa có kiểm chứng độc lập dài hạn.
8. **An toàn phần cứng:** Thử nghiệm camera hoàn toàn **không bật laser** trong chặng Q6.
9. **Quản lý Artifact và Truy xuất Nguồn gốc Nạp Bất biến (R13):** Các bộ nhị phân nạp nghiệm thu (bootloader, partitions, boot_app0, app binary) và manifest được lưu trữ vào thư mục độc quyền theo phiên (`build/c5a-artifacts/<archive-id>/`); tuyệt đối không ghi đè artifact đã niêm phong của phiên trước; manifest ghi đầy đủ source commit, hash SHA-256 của từng tệp, offset flash nạp thực tế (`0x00000000`, `0x00008000`, `0x0000e000`, `0x00010000`), FQBN và phiên bản toolchain phục vụ tái nạp và đối chiếu độc lập.
