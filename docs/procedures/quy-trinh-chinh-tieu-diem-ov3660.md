# Quy trình chỉnh tiêu điểm ống kính OV3660 — bước 3.7, ĐÃ THỬ 17/09: barrel cứng, không hề di chuyển (người dùng báo 18/09), dừng theo F4

Mục đích: đưa tiêu điểm ống kính từ xa (ước 1,4 m) về 250 mm để vạch mm
trên thước phân biệt được; sau đó chụp lại phiên 250 mm và đánh giá lại
chỉ tiêu MT "Quang học". Cơ sở: `docs/tests/2026-09-17_s3_quang_hoc.md`;
ảnh cận module 17/09 (người dùng gửi) cho thấy barrel ống kính có vành
khía, kiểu barrel ren xoay được, thường có một chấm keo giữ.

Thời gian: 15–20 phút. Cần: bố trí y như phiên 250 mm (bệ 20 mm, khối,
thước dựng, vạch 250), trình duyệt mở `http://IP/capture`, nhíp đầu nhỏ
hoặc ngón tay sạch, bút dạ hoặc bút xoá để đánh dấu, kính lúp nếu có.

**Nguyên tắc:** chỉ đổi một thứ là góc xoay ống kính. Xoay từng góc RẤT
nhỏ. Lượng cần xoay dự đoán chỉ cỡ **1/10 vòng**: dời tiêu điểm từ 1,4 m
về 250 mm với ống kính f ≈ 3–4 mm cần dịch ống kính khoảng 0,04 mm, mà ren
barrel loại này cỡ 0,35–0,5 mm mỗi vòng. Xoay quá 1/2 vòng mà không thấy
khác gì thì dừng và quay về vị trí gốc.

**F1. Đánh dấu vị trí gốc.**
- Ở đâu: module camera trên bo, bo vẫn trên gá, đã cắm USB.
- Làm gì: chấm một điểm bút dạ trên vành khía barrel và một điểm đối diện
  trên khung kim loại module, để biết đã xoay bao nhiêu và quay về được.
  Chụp một ảnh cận trước khi xoay, lưu `docs/logs/s3-lens-before-2026-09-17.jpg`.
- Thấy gì là đúng: hai chấm thẳng hàng trong ảnh.

**F2. Bố trí như phiên 250.**
- Ở đâu: bàn.
- Làm gì: khối trên bệ, mặt trước trùng vạch 250, thước dựng như A2. Mở
  trình duyệt `http://192.168.31.9/capture` (IP theo B1), bấm `F5`.
- Thấy gì là đúng: ảnh giống `docs/logs/quang-hoc-2026-09-17-250mm-img0003.jpg`.
- Nếu sai: khối lệch khung thì chỉnh khối, không chỉnh bo.

**F3. Cách cầm.**
- Ở đâu: module camera.
- Làm gì: một tay giữ chặt **khung kim loại vuông** của module bằng ngón
  cái và ngón trỏ. Tay kia kẹp vành khía barrel bằng nhíp hoặc đầu hai
  ngón tay. KHÔNG kéo, không đè lên cáp dẹt màu cam.
- Nếu sai: cáp dẹt tuột khỏi đầu nối trắng thì ảnh `/capture` đen hoặc bo
  báo lỗi camera; rút USB, cắm lại cáp dẹt vào đầu nối, gạt chốt, cắm USB.

**F4. Phá keo và xoay bước đầu.**
- Làm gì: xoay barrel **ngược chiều kim đồng hồ** (nhìn thẳng vào mặt ống
  kính) một góc **1/16 vòng** (≈ 20°, vài răng khía). Lần đầu có thể thấy
  hơi cứng rồi "tách" nhẹ khi chấm keo vỡ — bình thường. Ngược chiều kim
  đồng hồ là nới ống kính ra xa cảm biến, là chiều đưa tiêu điểm về gần.
- Thấy gì là đúng: barrel xoay được, hai chấm lệch nhau một góc nhỏ.
- Nếu sai: cứng hoàn toàn dù đã tăng lực vừa (không dùng lực mạnh) → DỪNG,
  không cố. Chụp ảnh, báo tôi: barrel dán chết thì chuyển sang phương án
  ở mục "Nếu không chỉnh được" dưới đây.

**F5. Kiểm sau mỗi bước.**
- Ở đâu: trình duyệt.
- Làm gì: bấm `F5`, nhìn đoạn thước phía trên khối: các vạch mm có tách
  thành từng đường riêng không; chữ trên khối có đọc được không.
- Thấy gì là đúng: rõ hơn bước trước → xoay tiếp 1/16 vòng cùng chiều, lại
  `F5`. Mờ hơn → đổi chiều: xoay về gốc rồi quá gốc 1/16 vòng theo chiều
  kim đồng hồ, lại `F5`.
- Nếu sai: không thấy khác gì sau 3–4 bước → có thể đang ở vùng bão hoà;
  xoay tiếp tới tổng 1/2 vòng, nếu vẫn không đổi thì quay về gốc và báo tôi.

**F6. Dừng đúng chỗ.**
- Làm gì: dừng khi vạch mm là các đường rời nhau và chữ viết tay đọc được
  ở `/capture`. Nếu xoay thêm mà bắt đầu mờ lại thì lùi nửa bước. Ghi lại
  chiều và tổng góc đã xoay (ví dụ "ngược chiều kim đồng hồ khoảng 1/8
  vòng").
- Sau đó KHÔNG dán keo, không chạm ống kính nữa. Chụp ảnh cận, lưu
  `docs/logs/s3-lens-after-2026-09-17.jpg`.

**F7. Chụp lại phiên 250 và, nếu tốt, 200 và 350.**
- Ở đâu: terminal Git Bash ở thư mục gốc (C1–C2 của quy trình quang học).
- Làm gì: đóng tab trình duyệt, gõ rồi `Enter` (sửa IP, số vòng, chiều):
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_250mm_lan2 --meta-copy docs/logs --note "sau chinh tieu diem: xoay nguoc chieu kim dong ho ~1/8 vong; 250 mm; khoi go 30x32x49; be 20 mm; H 65; thuoc dung vach 0 duoi; den phong + cua so qua rem"
  ```
  Rồi, nếu ảnh 250 đã rõ, dời khối tới vạch 200 và 350, dựng lại thước,
  chạy hai lệnh giống trên với `capture_qh_200mm_lan2` và
  `capture_qh_350mm_lan2`, đổi số mm trong `--note`.
- Thấy gì là đúng: `Ket qua: PASS`, `anh dat/yeu cau : 5/5` mỗi phiên.
- GIỮ `--framesize VGA`, không đổi độ phân giải ở bước này: để so trực
  tiếp với 4,32 px của phiên 250 cũ, một lần chỉ đổi một yếu tố. Ba phiên
  17/09 đều là 640×480 (kiểm `frames.csv`); ảnh 320×240 người dùng thấy
  là `/capture` trong trình duyệt ở B2 trước khi script đặt VGA. Vết mờ
  1,3 mm ở mặt vật là quang học, tăng độ phân giải chỉ trải nó lên nhiều
  pixel hơn (UXGA ≈ 8,6 px), không làm nó nhỏ đi. So độ phân giải làm sau
  khi tiêu điểm đạt, theo roadmap tuần 2 việc 3.
- Sau đó báo tôi; tôi chạy `ruler_ticks.py` và `sharpness.py` như 3.4 và
  so bề rộng mép với 4,32 px của phiên 250 cũ.

**Nếu không chỉnh được** (ĐÃ XẢY RA 17/09: barrel không xoay): trước hết
thử kính cận cảnh theo mục "Quy trình thử kính cận cảnh" (bước 3.8) — rẻ,
không đụng module. Song song xét đổi module, ĐỀ XUẤT hai hướng, chưa chọn: (1) module cùng chuẩn cáp dẹt 24 chân nhưng có ngàm lens
M12 chỉnh tay (OV2640 hoặc OV3660 bản "M12"), giữ được driver và mã hiện
có, lens thay được; (2) module OV5640 có lấy nét tự động — driver
esp32-camera hỗ trợ cảm biến, nhưng AF cần nạp firmware AF riêng và phải
khoá tiêu điểm khi hiệu chuẩn, phức tạp hơn. Điều kiện bắt buộc trước khi
mua: đầu nối và pinout cáp dẹt phải khớp đầu nối trên bo `ESP32-S3 WROOM`
hiện tại — CHƯA XÁC NHẬN, phải đối chiếu tài liệu bo. Camera Raspberry Pi
Global Shutter đang có là hướng nâng cấp riêng theo `PROJECT.md`, không
cắm được vào ESP32-S3.
