# scanner3d — máy quét 3D laser và bàn xoay

Phạm vi được người dùng chốt 08/10/2026 (D048): một cấu hình camera,
200 góc/400 ảnh, ba bước hiệu chuẩn, PLY, GUI tối thiểu và PCB tự thiết kế.
Đây là mục tiêu triển khai, không phải xác nhận toàn hệ đã chạy.

- [Roadmap theo sơ đồ nhánh và hội tụ](docs/ROADMAP.md).
- [Đặc tả và nghiệm thu](docs/SPEC.md), [cấu hình cơ sở](PROJECT.md).

Giữ nguyên tuần 2 đang thực hiện; phần tiếp theo tổ chức theo phụ thuộc,
không theo tuần. Mục tiêu cơ bản xong đầu 12/2026, bàn giao trước 31/12,
nộp đầu 01/2027. Báo cáo phép đo và log thiết bị có ngày là bằng chứng lịch sử.

Tệp giới thiệu dự án: `PROJECT.md`, `docs/SPEC.md`, `docs/ROADMAP.md`.

| Nơi | Nội dung |
| --- | --- |
| `docs/` | Roadmap, phần cứng, thiết kế, nguồn và kết quả đo |
| `docs/reference/` | Mô tả/roadmap DOCX đã đồng bộ D048; BOM lịch sử giữ nguyên |
| `docs/tests/` | Báo cáo từng phép thử |
| `firmware/esp32s3/` | Firmware camera |
| `firmware/stm32/` | Firmware Nucleo |
| `pc/` | Chương trình PC |
| `hardware/kicad/` | Schematic và PCB khi bắt đầu phần mạch |
| `hardware/mechanical/` | Bản vẽ và mô hình cơ khí |
| `data/` | Dữ liệu gốc, mẫu nhỏ, hiệu chuẩn, kết quả |

## Phạm vi bản đưa lên GitHub — cập nhật 12/10/2026

Kho này bắt đầu bằng lịch sử mới, xuất từ nội dung đã commit trên `main`
của kho phát triển tại mốc `f98ade4d24ff794c09fb7d7a1b7a67e7c45278bb`.
Các thay đổi chưa commit và các nhánh chưa gộp không nằm trong bản xuất.
Trạng thái trong hồ sơ phản ánh mốc nguồn này, không phải tiến độ mới hơn
đang được thực hiện trong kho phát triển.

Theo lựa chọn của người dùng, bản xuất không gồm `handoff/`, tệp luật và
cấu hình trợ lý, dữ liệu thô/kết quả lớn, báo cáo đồ án, dự án tham khảo
tải về, báo cáo website nghe nhạc, mẫu PowerPoint HUST, script sinh hình,
`docs/figures/`, hay các log `capture_fd5640_*`, `capture_p03_*`, `ping_*`.
Nhật ký phiên, hồ sơ trạng thái/quyết định nội bộ, báo cáo review, quy trình
cộng tác và các bản chép bàn giao giữa người dùng với trợ lý hoặc giữa các
trợ lý cũng được giữ ngoài kho xuất bản. Các log Tester/Coder có kiểm cổng
bàn giao và các bản chép nội dung trao đổi không được đưa vào kho này.
Những tệp này vẫn được giữ tại máy phát triển. Ảnh thô cần được sao lưu riêng.

Các đường dẫn tới tệp bị loại và các hash commit cũ trong hồ sơ lịch sử
vẫn là tham chiếu của kho phát triển; chúng có thể không mở được trong
kho GitHub này. Không thay đổi bằng chứng cũ để che giấu phần bị loại.

Không chứa `secrets.h`; dùng bản mẫu
`firmware/esp32s3/CameraWebServerTest/secrets.h.example` khi cấu hình riêng.
Lịch sử Git cũ, bao gồm mật khẩu Wi-Fi từng nằm trong mã, không được nhập
vào kho này. Khi cập nhật các đợt sau, xuất nội dung đã hoàn thành theo cùng
danh sách loại trừ; không merge lịch sử kho phát triển vào kho xuất bản.
