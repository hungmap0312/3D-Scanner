# Hồ sơ cơ sở — máy quét 3D

Mốc cơ sở 15/09/2026; phạm vi và kế hoạch cập nhật theo người dùng chốt
08/10/2026 (D048). Nguồn và hiệu lực: `docs/SOURCES.md`.

Đây là bản tóm tắt cấu hình. **Đặc tả đầy đủ** — mục tiêu, phạm vi, sản phẩm bàn giao, kiến trúc, giao thức, chu trình quét, an toàn, hiệu chuẩn, xử lý ảnh, chỉ tiêu nghiệm thu, quy cách đo, kế hoạch theo nhánh phụ thuộc, dự toán — nằm ở `docs/SPEC.md` (tổng hợp 2026-09-19 từ ba tệp trong `docs/reference/`, kèm số mục bản gốc). Khi cần đối chiếu yêu cầu hoặc chỉ tiêu, đọc `docs/SPEC.md` trước; D048 thay phạm vi tương ứng của bản 15/09; SPEC, ROADMAP và DOCX hiện hành
được đồng bộ, không để bản lịch sử ghi đè quyết định mới.

## Mục tiêu

Thiết kế và chế tạo máy quét 3D để bàn dùng một laser vạch và bàn xoay tự động. Thu cặp ảnh laser tắt/bật tại 200 góc (400 ảnh hợp lệ), hiệu chuẩn camera–laser–trục, ghép điểm và xuất PLY có đơn vị mm.

## Cấu hình theo bản mô tả hiện tại

| Khối | Vai trò |
| --- | --- |
| STM32 Nucleo-F446RE | Điều khiển bàn xoay, laser, HOME và các điều kiện dừng/liên động |
| ESP32-S3 N16R8 + camera OV3660 | Chụp ảnh và truyền về PC. PSRAM 0 KB của log 14/09 đã xử lý 16/09 (menu `OPI PSRAM`, D008): nhận 8192 KB, ghi đọc 1 MiB đạt, log trong `docs/logs/` |
| PC | Điều phối, lưu ảnh, hiệu chuẩn, xử lý/ghép điểm, GUI tối thiểu, xuất PLY; xem 3D độc lập |
| PC ↔ Nucleo | USB qua cổng COM ảo của ST-LINK |
| PC ↔ ESP32-S3 | Wi-Fi nội bộ |
| PCB tự thiết kế | Bo mở rộng cho Nucleo, gồm nguồn/đầu nối, driver và điều khiển laser/liên động |

Bản đầu chưa cần UART trực tiếp giữa Nucleo và ESP32-S3. Đây là cấu hình tài liệu cơ sở, không phải xác nhận rằng mọi khối đã được lắp hoặc chạy.

## Phạm vi

- Khởi đầu với vật đục, nhám, kích thước điển hình 50–100 mm.
- Một camera, một laser vạch, một trục quay.
- Một cấu hình camera chính kế thừa tuần 2; đầu ra bắt buộc PLY, ảnh gốc, hồ sơ hiệu chuẩn và nhật ký.
- Dựng lưới/OBJ/STL, in 3D, xem/chỉnh sửa 3D tích hợp, so sánh thuật toán và nhiều chế độ ảnh/góc sau tuần 2 chuyển sang tốt nghiệp. Tuần 2 và các phép khảo sát đang thực hiện giữ nguyên.
- Camera Raspberry Pi Global Shutter đang có được giữ cho hướng nâng cấp riêng.
- Kế hoạch sau tuần 2: G → các nhánh A/B/C/D/E → H1–H4 → V/F; hồ sơ R xuyên suốt. Sơ đồ, đầu vào, cổng, nhánh Git dự kiến: `docs/ROADMAP.md`.
- Mục tiêu H4 01–03/12/2026; nghiệm thu trước 24/12; bàn giao trước 31/12; hạn nộp đầu 01/2027 (chưa ngày cụ thể).
- Người dùng xác nhận 4 giờ/ngày, mọi ngày (28 giờ/7 ngày); đây là quỹ dự kiến, không phải giờ đã làm. D010 giữ làm lịch sử tuần 1, không tiếp tục chia tuần 3–14.
- Giữ PCB hoạt động, ba bước hiệu chuẩn, ba mẫu đối chứng, một mẫu năm phiên lặp và ba lượt 200 góc liên tiếp; yêu cầu an toàn/liên động đã bỏ (D050). Mục tiêu ≤2 mm và ≤15 phút/lượt 200 góc; chi tiết B/MT ở SPEC.

## Giới hạn của hồ sơ này

Không dùng hồ sơ này thay sơ đồ đấu dây. Pinout, driver, cơ khí, thông số chụp và ngưỡng kiểm tra phải đối chiếu tài liệu gốc và thiết bị thực. BOM cũ sử dụng OV2640 và kiến trúc khác; xem `DECISIONS.md` trước khi mua hoặc đấu nối theo BOM.
