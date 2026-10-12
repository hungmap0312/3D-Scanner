# Test `/capture_fresh` và khóa camera trên PC (harness C++ của Tester C5a Q6)

Chạy **nguyên văn** các handler của `../app_httpd.cpp` trên máy tính với
API ESP-IDF giả (`fake_esp.h`). Mục đích là kiểm các nhánh khó tạo trên bo:

- khung tươi về đúng/sau hạn 1,5 s;
- `fb_get` trả NULL sau khi driver chặn ~4 s;
- đặt header hoặc gửi body lỗi;
- biên `UINT64_MAX`;
- tranh chấp stream với `/capture_fresh`, `/capture`, `/bmp`, `/xclk`,
  `/` ở hai thứ tự, bằng hai luồng thật;
- (Vòng 6) `/status`: hai trường heap, kiểm biên JSON, lỗi bộ định dạng ở
  từng phép ghi, tranh chấp với stream.

Kỳ vọng lấy từ `handoff/2026-09-21_c5a-s3-fresh-capture/01_PLAN.md`
Vòng 5 mục 4–5 và Vòng 6 mục 2, 5 (V6-T1…V6-T3), không lấy từ mã.

Đây **không phải** thử trên phần cứng: không có DMA, Wi-Fi, lập lịch FreeRTOS
thật; đồng hồ do test điều khiển. PASS ở đây chỉ nói logic handler đúng với
chuỗi sự kiện đưa vào. Q6-T9/T10 vẫn phải chạy trên bo theo
`docs/procedures/quy-trinh-c5a-fresh-capture.md`.

Arduino chỉ biên dịch tệp ở gốc thư mục sketch và trong `src/`, nên thư mục
`test/` không vào firmware. Tester đã kiểm điều này ngày 2026-10-03: build
sketch có `test/` cho cùng kích thước 1 004 306 byte, log build không nhắc
tới tệp test.

## Chạy (Git Bash, từ gốc repo)

Cần MinGW g++ (`ENVIRONMENT.md`: `D:\MinGW\bin`, 9.2.0) và Git.

```
.venv/Scripts/python.exe pc/test_c5a_runtime.py
```

Lệnh này lần lượt:

1. trích các đoạn của `app_httpd.cpp` tại commit `C5A_Q6_B` (mặc định là
   B đang kiểm, ghi ở đầu `pc/test_c5a_runtime.py`) thành
   `app_httpd_extract.inc` trong thư mục tạm; từ Vòng 6 trích thêm
   `status_json_append`, `print_reg_safe` (hoặc `print_reg` ở bản cũ) và
   `status_handler`;
2. biên dịch `test_fresh_host.cpp` hai lần: không LED (đúng
   `CAMERA_MODEL_ESP32S3_EYE` của bo) và `-DLED_GPIO_NUM=4`;
3. chạy cả hai bản, in từng dòng `[PASS]/[FAIL] Hxx` và các dòng
   `@JSON <mã> <body>`; phía Python parse các JSON này (nhóm J).

Muốn kiểm commit khác:

```
C5A_Q6_B=<hash đầy đủ> .venv/Scripts/python.exe pc/test_c5a_runtime.py
```

**Thấy gì là đúng:** dòng cuối `TONG: N PASS, 0 FAIL, ...`; mỗi bản harness
in `== N PASS, 0 FAIL ==`.

**Nếu sai:** dòng `[FAIL] Hxx` ghi kỳ vọng ở tiêu đề và thực tế sau dấu `|`:

- `HTTP …`, thân phản hồi;
- `get`/`return`: số lần lấy/trả buffer;
- `con_giu`: số buffer chưa trả;
- `khoa take/give`: số lần lấy/nhả khóa;
- `n_send`: số lần gửi response.

Nếu lỗi là biên dịch, chép toàn bộ output.

## Các trường hợp (Hxx)

- **H01–H02 (Q6-T1):**
  - Boot ID đủ 32 hex thường, gọi lại không đổi.
  - 20 lượt liên tiếp: 200, 5 header đúng một lần, ID 1..20,
    `t_frame > t_req` = mốc lấy khóa, mỗi lượt 1 lấy / 1 trả buffer, khóa
    cân bằng.
- **H03–H11 (Q6-T2):**
  - 1 và 4 khung cũ thì thành công; khung cũ thứ 5 thì 503, không lấy khung
    thứ 6, ID không bị tiêu thụ.
  - Khung có timestamp bằng mốc request bị coi là cũ.
  - Khung tươi về trước hạn 1 µs thì 200.
  - Khung tươi về **đúng hoặc sau** hạn phải trả 503 TIMEOUT.
  - Khung cũ về đúng hạn thì 503.
- **H12–H19 (Q6-T4):**
  - NULL trước hạn → `NO_BUFFER`; NULL **sau** hạn phải trả TIMEOUT.
  - Khung không-JPEG → 500.
  - Đặt header lỗi phải trả 500 `CAMERA_INTERNAL`.
  - Gửi body lỗi: ID vẫn bị tiêu thụ, không gửi response thứ hai.
  - Thiếu mutex → 500.
- **H20 (Q6-T3):** `UINT64_MAX` được cấp đúng một lần, lượt kế tiếp 500
  `FRAME_ID_OVERFLOW`.
- **H21–H29 (Q6-T5):**
  - Khóa đang bị giữ: các endpoint trả 503 đúng chủ sở hữu, chờ khoảng
    100 ms.
  - Trang `/` khi bận không được gửi `Content-Encoding: gzip` kèm thân văn
    bản.
  - Stream ở luồng khác giữ trọn kết nối; client ngắt thì nhả hết.
  - Fresh đang giữ buffer thì `/stream` báo `BUSY_CAPTURE`.
- **H30–H34 (Q6-T8):** `/capture`, `/bmp`, `/xclk`, `/` khi không tranh
  chấp vẫn đúng hợp đồng cũ, trả buffer và nhả khóa.
- **H36 (V6-T1):** `/status` bình thường (OV3660): 200 JSON, heap nội 123456
  đọc bằng `MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT`, PSRAM 654321 bằng
  `MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT`, mỗi mask một lần; khóa cân bằng.
  Nhóm J1 parse JSON: trường = trường sensor của base main + đúng 2 trường
  heap, 48 thanh ghi, giá trị sensor giữ nguyên.
- **H37–H39 (V6-T2):** heap 0 / `UINT32_MAX`; mọi trường dài nhất theo kiểu
  thật (thanh ghi `INT_MIN`, int8 −128, uint8 255…) vẫn vừa bộ đệm; nhánh
  OV2640.
- **H40–H41 (V6-T2):** `vsnprintf` của đoạn trích được thay bằng hàm giả
  (`fake_vsnprintf`, macro trong `fake_esp.h`, `#undef` ngay sau khi include
  đoạn trích). Lần lượt cho **từng** phép ghi trả −1 (lỗi định dạng) hoặc
  báo hết chỗ: phải 500 `ERROR CAMERA_INTERNAL`, nhả khóa đúng một lần,
  `/status` sau đó 200.
- **H42 (V6-T2):** `status_json_append` thật với bộ đệm nhỏ có byte canh
  (vừa đủ, thiếu 1 byte, con trỏ ở biên/NULL).
- **H43–H44 (V6-T3):** `/status` khi khóa bị giữ có/không stream và khi
  stream ở luồng khác đang gửi → 503 đúng chủ, không đọc sensor/heap; sau
  khi nhả, 3 mẫu heap khác nhau thì phần sensor giống hệt. Nhóm J5 chạy
  `diff_controls`/`compare_registers` trên ba mẫu.
- **H35:** trên toàn bộ phiên chạy:
  - không lấy buffer hay chạm sensor ngoài khóa;
  - không có hai vùng camera chồng nhau;
  - không trả sai, không trả NULL, không còn buffer bị giữ.

Mutex FreeRTOS được giả bằng semaphore Win32 nhị phân, không đệ quy. Chỉ
luồng đang giữ mới nhả được; nhả sai bị đếm.
