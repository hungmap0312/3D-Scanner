# Quy trình lưu ảnh từ điện thoại vào repo — dùng cho 3.6 và mọi ảnh sau

Mục đích: đưa ảnh bằng chứng vào `docs/logs/` đúng tên để trợ lý kiểm và
đưa vào Git. Ảnh trong chat không phải hồ sơ; chỉ tệp trong repo mới tính.

Tên hai ảnh bo S3 chụp 18/09:

| Ảnh nào | Tên tệp đúng | Nằm ở thư mục |
| --- | --- | --- |
| Mặt trước: thấy module camera, đầu nối dẹt trắng, chữ `ESP32-S3 WROOM`, hai cổng USB-C | `s3-board-front-2026-09-18.jpg` | `D:\scanner3d\docs\logs` |
| Mặt sau: thấy khe thẻ nhớ microSD, chú giải `Camera / SD Card / PSRAM`, chữ `USB-UART` và `USB-OTG` | `s3-board-back-2026-09-18.jpg` | `D:\scanner3d\docs\logs` |

**L1. Đưa ảnh từ điện thoại sang máy tính.**
- Ở đâu: cách bạn đã dùng cho ba ảnh bố trí hôm 17/09 (cáp USB, Zalo/
  Telegram gửi cho chính mình, Google Photos, hoặc email). Dùng lại cách đó.
- Làm gì: lấy hai ảnh về máy, thường vào thư mục `Downloads`.
- Thấy gì là đúng: trong `Downloads` có hai tệp ảnh mới, mở lên xem đúng
  là mặt trước và mặt sau bo.
- Nếu sai: ảnh gửi qua ứng dụng chat có thể bị nén nhỏ hơn bản gốc; vẫn
  dùng được cho hồ sơ, không cần bản gốc.

**L2. Hiện đuôi tệp để đổi tên không bị sai.**
- Ở đâu: Windows Explorer, bất kỳ thư mục nào.
- Làm gì: menu `View` (Xem) ở thanh trên > `Show` (Hiện) > tích
  `File name extensions` (Phần mở rộng tên tệp).
- Thấy gì là đúng: tên tệp ảnh hiện thêm đuôi, ví dụ `IMG_1234.jpg` thay
  cho `IMG_1234`.
- Nếu sai: đuôi là `.jpeg` thì vẫn là ảnh JPEG, đổi tên sang `.jpg` được.
  Đuôi là `.heic` hoặc `.heif` thì trợ lý không đọc được: mở ảnh bằng
  ứng dụng `Photos`, chọn `...` > `Save as` > định dạng JPEG, rồi dùng tệp
  mới đó. Đuôi `.png` thì báo tôi, giữ nguyên `.png` trong tên.

**L3. Chép vào đúng thư mục.**
- Ở đâu: Explorer.
- Làm gì: mở `Downloads`, chọn hai ảnh, `Ctrl` + `C`. Trên thanh địa chỉ
  gõ `D:\scanner3d\docs\logs` rồi `Enter`. Bấm `Ctrl` + `V`.
- Thấy gì là đúng: hai ảnh xuất hiện trong `docs\logs` cạnh các tệp
  `quang-hoc-bo-tri-2026-09-17-*.jpg`.

**L4. Đổi tên.**
- Ở đâu: thư mục `D:\scanner3d\docs\logs`.
- Làm gì: bấm chuột phải vào ảnh mặt trước > `Rename` (Đổi tên), xoá tên cũ,
  gõ đúng `s3-board-front-2026-09-18.jpg`, `Enter`. Làm tương tự với ảnh
  mặt sau: `s3-board-back-2026-09-18.jpg`. Chữ thường, dấu gạch ngang, không
  dấu cách, không dấu tiếng Việt.
- Thấy gì là đúng: hai tệp tên đúng như bảng trên, mở lên đúng ảnh.
- Nếu sai: Windows hỏi "đổi phần mở rộng có thể làm tệp không dùng được"
  chỉ khi bạn gõ sai đuôi; bấm `No` và gõ lại có `.jpg`. Báo "tệp đã tồn
  tại" nghĩa là đã có tệp tên đó, không ghi đè, báo tôi.

**L5. Báo tôi.** Chỉ cần nhắn "đã lưu hai ảnh". Tôi kiểm bằng Pillow, đưa
vào Git, và ghi vào `docs/HARDWARE.md`.
