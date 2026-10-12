# Mẫu báo kết quả thử

Mỗi lần thử lưu một tệp riêng trong `docs/tests/`, ví dụ `2026-09-16_s3_psram.md`. Ngày trong ví dụ chỉ minh họa cách đặt tên.

- Mục tiêu phép thử:
- Bo / camera / revision:
- Nguồn cấp và kết nối:
- Hệ điều hành, IDE, board package:
- Mã nguồn / commit / thay đổi chưa commit:
- Toàn bộ cài đặt build liên quan:
- Cổng và tốc độ Serial:
- Bước tái hiện:
- Kết quả mong đợi:
- Kết quả quan sát thực tế:
- Log nguyên văn đã bỏ thông tin bí mật:
- Ảnh gốc / ảnh dây / ảnh cấu hình đi kèm:
- Thời gian chạy và số lần thử thực tế:
- Số lần lặp mỗi đại lượng đo (từ 20/09 theo `docs/PROCESS.md` R7: ≥ 3, ghi rõ nếu ít hơn và vì sao):
- Bảng giá trị: từng lần đo, trung bình, độ lệch (độ lệch chuẩn hoặc min–max), đơn vị:
- Ngưỡng đối chiếu (mục nào của `docs/SPEC.md`) và kết luận ĐẠT / CHƯA ĐẠT từng đại lượng:
- Kết luận có thể rút ra:
- Điều chưa thể kết luận:
- Bước thử tiếp theo:

Bài kiểm tra là bước Q9 của `docs/PROCESS.md`: chỉ khi có bảng số đo so với ngưỡng mới là Q9; "nạp được, lên hình" là Q8, ghi ở mục kết quả quan sát nhưng không kết luận ĐẠT.

Một lần chỉ thay đổi số ít yếu tố để đối chiếu nguyên nhân. Không thay log lỗi bằng câu “không chạy”; giữ thông báo từ đầu đến cuối nếu có thể. Ảnh camera để phân tích nên là tệp gốc, không chỉ ảnh chụp màn hình stream.
