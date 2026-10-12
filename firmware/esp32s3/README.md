# Firmware ESP32-S3

Đã có sketch người dùng cung cấp tại [CameraWebServerTest/CameraWebServerTest.ino](CameraWebServerTest/CameraWebServerTest.ino), cùng 6 tệp phụ; nguồn đang có trong Git ở commit `e65ec13`. Chưa đối chiếu với binary trên bo và cấu hình của lần chạy thành công.

Rà soát ngày 2026-09-15 giữ nguyên toàn bộ 7 tệp sketch. Xem [biên bản review](../../docs/CAMERA_REVIEW_2026-09-15.md) về cấu hình quan sát, các điểm cần sửa và phép kiểm tra đã chạy.

Ngày 2026-09-16 đã sửa bốn phát hiện R01–R04 của biên bản đó, nhánh
`fix/camera-r01-r04`, đã gộp vào `main`. Người dùng đã nạp và thử trên
bo cùng ngày: trang web lên được, chụp được; timeout Wi-Fi và vòng thử
lại chạy đúng qua nhiều chu kỳ. Log tại
`docs/logs/s3-boot-2026-09-16-r01-r04.log` và
`docs/logs/s3-wifi-retry-2026-09-16-after-fix.log`. Giới hạn còn lại:
chưa đọc giá trị `X-Timestamp` thực tế của stream, và chưa dựng lại được
tình huống HTTP server không khởi động để thử nhánh lỗi của R04.

Ngày 2026-10-03 (D043, đầu việc C5a chặng Q6): Triển khai endpoint
`/capture_fresh` trên ESP32-S3 theo Phương án B (D041). Endpoint trả về ảnh
JPEG tươi chụp sau thời điểm nhận yêu cầu, cung cấp 5 headers chẩn đoán bắt
buộc (`X-Frame-Id`, `X-Boot-Id`, `X-Timestamp`, `X-Request-Timestamp`,
`X-Discarded-Frames`). Cấu hình camera chốt `fb_count = 1` kết hợp
`CAMERA_GRAB_LATEST` cho JPEG PSRAM theo `docs/SPEC.md` mục 10. Toàn bộ các
handler truy cập camera và thanh ghi cảm biến được bảo vệ bởi Mutex FreeRTOS
`s_cam_mutex` (chờ 100 ms); từ chối 503 `ERROR CAMERA_BUSY_STREAM` nếu
`/stream` đang mở. Hướng dẫn nạp và kiểm tra chi tiết tại
`docs/procedures/quy-trinh-c5a-fresh-capture.md`.

## Trước khi build

Thư mục sketch cần `secrets.h` chứa thông tin Wi-Fi. Tệp này nằm trong
`.gitignore` nên không có trong repository. Chép `secrets.h.example`
thành `secrets.h` rồi điền SSID và mật khẩu. Xem D009 trong
`DECISIONS.md`, gồm cả lưu ý rằng giá trị cũ vẫn nằm trong lịch sử Git.

## Cấu hình build đã chạy được

FQBN `esp32:esp32:esp32s3:PSRAM=opi` với core esp32 3.3.11. Mọi mục khác
giữ mặc định của bo, trùng với menu Tools người dùng đang dùng; ảnh menu
tại `docs/logs/arduino-tools-menu-2026-09-16.png`.

Từ 2026-09-16, mỗi thư mục sketch có `sketch.yaml` ghi `default_fqbn`
đúng giá trị trên, theo D011. arduino-cli tự lấy FQBN từ đó nên lệnh
build không cần `--fqbn` nữa:

```
arduino-cli compile --warnings all firmware/esp32s3/CameraWebServerTest
```

Đã kiểm chứng ở môi trường trợ lý: build không truyền `--fqbn` cho ra
đúng `PSRAM=opi`, dùng core 3.3.11 sẵn có, có cờ `BOARD_HAS_PSRAM`; log
tại `docs/logs/build-2026-09-16-sketch-yaml.log`.

**Arduino IDE 2.3.10 KHÔNG đọc `sketch.yaml`.** Người dùng xác nhận
2026-09-16: mở sketch có `sketch.yaml`, `Tools > PSRAM` vẫn hiện
`Disabled`. Hệ quả cho ai nạp bằng IDE, việc bắt buộc trước mỗi lần nạp:

1. Vào `Tools`, kiểm `Board` là `ESP32S3 Dev Module`.
2. Kiểm `PSRAM` là `OPI PSRAM`. Menu này theo từng sketch đang mở; mở
   sketch mới là nó trở về `Disabled`.
3. Rồi mới nạp.

Muốn bỏ hẳn bước nhìn menu thì nạp bằng arduino-cli, vốn đọc `sketch.yaml`.
Lệnh dưới đây CHƯA THỬ vì trợ lý không có bo; cổng COM lấy từ
`ENVIRONMENT.md`:

```
arduino-cli compile --upload -p COM9 firmware/esp32s3/PsramTest
```

`sketch.yaml` cố ý KHÔNG có mục `profiles`. Chế độ profile của arduino-cli
tải core vào thư mục riêng, lần đầu mất vài trăm MB, nên chỉ dùng khi cần
ghim phiên bản core độc lập với bản cài toàn cục. Profile mẫu do công cụ
sinh ra nằm cuối log trên.

Kết quả và bảng phân vùng do build sinh ra nằm ở
`docs/logs/build-2026-09-16-r01-r04.log`. Hai điều cần nhớ: `partitions.csv`
trong thư mục sketch ghi đè lựa chọn Partition Scheme trên menu, nhưng
hạn mức mà công cụ dùng để kiểm tra kích thước vẫn lấy theo menu, tức
1,25 MiB chứ không phải 3,75 MiB của phân vùng thật.

## Sketch thử PSRAM

`PsramTest/PsramTest.ino` là sketch độc lập, không dùng camera, phục vụ chỉ
tiêu B "Nhận dạng và bộ nhớ" của tuần 1: kiểm tra ghi đọc vùng 1 MiB
trên PSRAM không sai dữ liệu. Viết ngày 2026-09-16, build đạt trên PC,
CHƯA NẠP lên bo.

Build cùng menu Tools với sketch camera, tức `PSRAM = OPI PSRAM`. Thư
mục này cũng có `sketch.yaml` nên không cần `--fqbn`:

```
arduino-cli compile --warnings all firmware/esp32s3/PsramTest
```

Sketch chạy hai phép thử rồi in hai dòng kết luận trên Serial 115200:

- `RESULT_1MIB : PASS/FAIL`. Cấp phát 1 MiB trong PSRAM, xác nhận con
  trỏ nằm ở RAM ngoài, rồi ghi và đọc lại sáu mẫu: 0x00, 0xFF, 0xAA,
  0x55, tăng dần, giả ngẫu nhiên. Đây là dòng dùng cho chỉ tiêu B.
- `RESULT_LARGEST : PASS/FAIL (N KB)`. Cấp phát khối lớn nhất còn trống,
  ghi mỗi word 32 bit bằng chính chỉ số word rồi đọc lại. Mẫu này phát
  hiện được trường hợp vùng địa chỉ lớn bị ánh xạ trùng vào bộ nhớ nhỏ
  hơn, điều mà mẫu byte lặp không làm được. Không gate chỉ tiêu.

Nếu firmware được build với PSRAM tắt, sketch in `psramFound: no` kèm gợi
ý kiểm tra `Tools > PSRAM`. Trong Arduino IDE thiết lập này theo từng
sketch đang mở, nên mở sketch mới có thể trở về `Disabled`.

Dùng con trỏ `volatile` để trình biên dịch không bỏ qua các lần ghi đọc
thật. Log build: `docs/logs/build-2026-09-16-psram-test.log`.

Ghi cấu hình IDE, phiên bản Arduino-ESP32, pinout, Flash/PSRAM và log trong `ENVIRONMENT.md` trước khi thử thay đổi. Tên macro `CAMERA_MODEL_ESP32S3_EYE` là lựa chọn bộ chân trong mã, chưa xác nhận model bo thật hoặc cấu hình PSRAM. Giữ nguyên tên thư mục sketch và tệp `.ino` chính tương ứng khi lưu bản gốc.
