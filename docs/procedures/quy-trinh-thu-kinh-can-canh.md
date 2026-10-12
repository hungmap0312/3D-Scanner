# Quy trình thử kính cận cảnh trước ống kính — bước 3.8, CHƯA CHẠY, chờ người dùng

Mục đích: đưa tiêu điểm về ≈ 250 mm mà không đụng module, bằng một thấu
kính hội tụ đặt trước ống kính. Cơ sở tính (ĐỀ XUẤT từ số đo 17/09,
`docs/tests/2026-09-17_s3_quang_hoc.md`): ống kính đang lấy nét ≈ 1,4 m
(≈ 0,7 đi-ốp); muốn nét ở 250 mm cần 4 đi-ốp; thiếu ≈ 3,3 đi-ốp → mắt kính
lão **+3.00 D** cho tiêu điểm mới ≈ 1/(0,7 + 3,0) ≈ 270 mm; **+3.50 D** cho
≈ 240 mm. Khẩu độ camera ≈ 1,6 mm nên chỉ dùng mảnh ≈ 2 mm giữa mắt kính,
quang sai kính rẻ không đáng kể; trường nhìn đổi < 1 %. Ước lượng 1,4 m có
sai số, nên thử hai công suất nếu tiện.

Cần: mắt kính lão +3.00 (và +3.50 nếu có) — hiệu thuốc, chợ, hoặc mượn;
bố trí y như phiên 250; băng dính; trình duyệt `/capture`.

**G1. Kiểm nhanh bằng tay.**
- Ở đâu: bàn, bố trí như phiên 250 (khối trên bệ tại vạch 250, thước dựng).
- Làm gì: mở `http://192.168.31.9/capture`. Cầm mắt kính +3.00 che sát
  trước ống kính, cách mặt ống kính 5–10 mm, mặt kính vuông góc với hướng
  nhìn, tâm mắt kính trùng ống kính (kính lão tâm ở giữa mắt kính). Bấm
  `F5`. Không cần tháo kính ra khỏi gọng cho bước này.
- Thấy gì là đúng: các vạch mm trên thước tách thành đường riêng, chữ trên
  khối đọc được. Nếu nét hơn hẳn nhưng chưa tách vạch mm, dời khối tới lui
  20–30 mm quanh vạch 250 và `F5` từng lần để tìm chỗ nét nhất; ghi lại
  khoảng cách đó — nó cho biết tiêu điểm thật của hệ và kiểm lại ước lượng
  1,4 m.
- Nếu sai: không khác gì khi có và không có kính → kính không phải kính
  hội tụ (kính cận là phân kỳ, dấu âm) hoặc tâm kính lệch; thử lại. Ảnh
  tối hơn hẳn → kính che một phần ống kính, đưa tâm kính vào đúng.

**G2. Cố định tạm để chụp.**
- Làm gì: khi đã thấy nét, gá mắt kính (hoặc cả gọng) trước ống kính bằng
  băng dính lên chân đế hoặc kẹp giấy, giữ khoảng cách và góc như lúc cầm
  tay. Kiểm `F5` lần nữa.
- Thấy gì là đúng: ảnh vẫn nét như G1, không rung khi buông tay.

**G3. Chụp phiên 250 có kính.**
- Ở đâu: terminal Git Bash ở thư mục gốc.
- Làm gì: đóng tab trình duyệt, gõ rồi `Enter` (sửa IP, công suất kính,
  khoảng cách thật nếu đã dời khối):
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_250mm_kinh300 --meta-copy docs/logs --note "kinh lao +3.00 truoc ong kinh, cach ~8 mm; 250 mm; khoi go 30x32x49; be 20 mm; H 65; thuoc dung vach 0 duoi; den phong + cua so qua rem"
  ```
  Nếu có +3.50, chụp thêm `capture_qh_250mm_kinh350` cùng cách. Nếu chỗ
  nét nhất không phải 250, chụp tại chỗ đó và ghi số mm vào `--note` và
  vào `--session-id` (ví dụ `capture_qh_270mm_kinh300`).
- Thấy gì là đúng: `Ket qua: PASS`, `anh dat/yeu cau : 5/5`.
- Sau đó báo tôi công suất kính, khoảng cách kính–ống kính, khoảng cách
  nét nhất; tôi đo lại bằng `ruler_ticks.py` và `sharpness.py`, so với
  4,32 px.

Nếu G1 cho kết quả tốt: bước sau là gá kính cố định cứng vào gá camera
(tuần 2, cùng gá thử B8), vì hiệu chuẩn tuần 3 sẽ tính cho cả hệ ống kính
+ kính; kính lệch sau hiệu chuẩn là phải hiệu chuẩn lại.
