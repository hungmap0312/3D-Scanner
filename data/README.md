# Lưu dữ liệu quét

| Thư mục | Dùng cho | Cách giữ |
| --- | --- | --- |
| `raw/` | Ảnh nguyên gốc của từng phiên | Giữ bất biến; sao lưu riêng vì đã loại khỏi Git. **Vị trí thật từ 18/09:** `D:\datascanner3d\raw\` (người dùng chuyển toàn bộ 5 phiên 16–17/09 sang đó). `data\raw` trong repo là **junction** trỏ tới thư mục ấy (tạo 18/09 bằng `New-Item -ItemType Junction`), nên mọi lệnh ghi `data/raw` vẫn chạy; gỡ junction bằng `rmdir data\raw` trong cmd, không mất dữ liệu. LƯU Ý: chuyển chỗ không phải sao lưu — hiện chỉ có MỘT bản; bản sao thứ hai (USB, đám mây) chưa có |
| `processed/` | PLY, điểm trung gian và kết quả xử lý; lưới dành giai đoạn tốt nghiệp | Ghi cấu hình tạo kết quả; có thể tái tạo nếu ảnh và hiệu chuẩn còn đủ |
| `samples/` | Tập ảnh nhỏ tái hiện lỗi hoặc kiểm tra thuật toán | Chọn ít ảnh đại diện để đưa vào Git và gửi trợ lý |
| `calibration/` | Hồ sơ hiệu chuẩn và metadata | Version theo camera/chế độ ảnh/gá, giữ cùng mã nguồn hoặc trong bản sao lưu xác định |

Mỗi phiên cần ID và metadata: phiên bản mã nguồn, cấu hình camera, firmware, calibration_id, số thứ tự góc, số xung/góc lệnh, laser OFF/ON, thời gian và lỗi. Tên như `scan_20260916_001` chỉ là ví dụ, không phải phiên đã chạy.

Ảnh hiệu chuẩn dung lượng lớn có thể ở `raw/`; hồ sơ hiệu chuẩn ghi vị trí tập ảnh và cách tái tạo. Sau khi đổi độ phân giải, focus hoặc gá, kiểm tra hồ sơ hiệu chuẩn còn áp dụng được trước khi dùng lại.

Git không sao lưu những gì bị loại khỏi theo dõi. Cuối ngày, sao lưu ảnh gốc sang ổ khác hoặc nơi lưu trữ người dùng lựa chọn, và ghi vị trí bản sao.

## Phạm vi hiện hành — D048 (08/10/2026)

200 góc → 400 ảnh OFF/ON được chọn hợp lệ; giữ riêng ảnh/payload thử lại.
Một cấu hình camera chính kế thừa tuần 2; PLY có đơn vị mm là đầu ra bắt
buộc. Không sửa/xoá các phiên dữ liệu cũ khi đổi kế hoạch. Ảnh gốc, hồ sơ
và kết quả đã lưu tiếp tục giữ nguyên; roadmap không chứng nhận đã quét.
