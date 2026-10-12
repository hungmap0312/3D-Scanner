# Quy trình tiếp nhận laser vạch SYD1230 — nhận hàng 2026-09-22, CHƯA CẤP NGUỒN

> **Đính chính 2026-10-09 — D050:** người dùng xoá toàn bộ yêu cầu an toàn/liên động của `docs/SPEC.md` mục 9 (công tắc cửa SW1, nút dừng SW2, hộp kín, watchdog, giới hạn thời gian bật laser, kính bảo hộ như điều kiện cổng, MVS của D049). Các cổng/điểm dừng an toàn trong tệp này không còn chặn việc cấp nguồn laser hay chặng nào. Phần mạch MOSFET đóng ngắt laser vẫn là thiết kế chức năng. Nội dung dưới giữ nguyên làm lịch sử.

**Trạng thái 22/09 tối: L1–L3 ĐÃ CHẠY** (người dùng), kết quả trong
`docs/HARDWARE.md` và `docs/design/LASER_CIRCUIT.md` mục 0b. Công suất
nhãn ghi **5 mW** (xác nhận sau khi chụp lại chỗ ngón tay che). Còn
thiếu: góc quạt, có mạch hạn dòng hay không. L4 (cất, không cắm thử)
vẫn đang áp dụng.

Viết 2026-09-22 khi người dùng báo đã nhận 2 module laser. Mục đích: ghi
nhận đúng thông số **trước khi** cấp nguồn, và nói rõ điều kiện nào mới
được bật.

Điều đang biết, NGƯỜI DÙNG CUNG CẤP 22/09: mã in `SYD1230`; người bán ghi
650 nm, 5 mW. **CHƯA KIỂM CHỨNG** mọi thứ còn lại: điện áp làm việc, số
dây, có mạch hạn dòng trên module không, vạch hay chấm, góc quạt.

## Tại sao chưa bật — điều kiện bắt buộc

`docs/SPEC.md` mục 9 (an toàn, không nới) đòi: laser chỉ hoạt động trong
hộp kín, **cửa ngắt nguồn laser bằng phần cứng**, nút dừng, và các bảo vệ
này phải được thử trước khi chạy tự động. Phát hiện `R01` của
`docs/reviews/REVIEW_2026-09-20_main_full.md` (mức **Chặn**) về đúng điểm
này vẫn **đang mở**, hoãn theo D022. Khi chưa có linh kiện thì đó là lỗi
kế hoạch trên giấy; từ 22/09 laser đã nằm trên bàn nên nó thành rủi ro
thật.

Trước khi cấp nguồn cho laser lần đầu, phải có đủ:

| # | Thứ cần có | Trạng thái 22/09 |
| --- | --- | --- |
| 1 | MOSFET logic-level xuyên lỗ (B2) + R 100 Ω gate + R 10 kΩ kéo xuống | Chưa có; B2 còn vướng R10 (tiêu chí Rds(on)) |
| 2 | Hộp che B5, không khe chiếu ra phía người | Chưa làm |
| 3 | Công tắc cửa SW1 (NC) ngắt nguồn laser bằng phần cứng | Chưa có (E1) — đây là điểm R01 |
| 4 | Nút dừng SW2 (NC) | Chưa có |
| 5 | Kính bảo hộ chặn 600–700 nm (B10) | Chưa có |
| 6 | Sơ đồ đấu đúng `docs/design/LASER_CIRCUIT.md` | Sơ đồ đã có (ĐỀ XUẤT), chưa đấu |

Bật laser khi chưa đủ các mục trên là **ngoại lệ so với `SPEC` mục 9**;
nếu người dùng quyết làm vậy thì phải ghi một mục trong `DECISIONS.md`
nói rõ bỏ qua mục nào và vì sao (`docs/PROCESS.md` R2). Đây là quyết định
của người dùng, không phải của trợ lý.

## L1 — Ghi nhãn và chụp ảnh, không nối dây

- **Ở đâu:** bàn làm việc, đủ sáng; điện thoại. Laser vẫn trong túi tới
  lúc chụp.
- **Làm gì:** chụp ba ảnh cho **một** module: (1) toàn thân module thấy
  rõ đầu ra tia và thân trụ; (2) cận chỗ có chữ in, đọc được `SYD1230` và
  mọi chữ số khác; (3) toàn bộ dây ra, thấy rõ **số sợi dây và màu từng
  sợi**. Nếu trên thân hoặc trên nhãn có ghi điện áp (ví dụ `3-5V`,
  `DC5V`) thì chụp cận chỗ đó.
- **Thấy gì là đúng:** ảnh đọc được chữ khi phóng to.
- **Nếu sai:** chữ quá nhỏ hoặc mờ → chụp lại cách 10–15 cm, chạm vào
  chữ trên màn hình để lấy nét.

## L2 — Đo kích thước, không cấp điện

- **Ở đâu:** bàn làm việc; thước kẻ (thước cặp nếu đã mượn được).
- **Làm gì:** đo và ghi: đường kính thân (mm), chiều dài thân (mm), chiều
  dài dây (cm). Đếm lại số sợi dây và ghi màu theo thứ tự.
- **Thấy gì là đúng:** ba số và danh sách màu dây. Loại phổ biến cho gá
  B8 là thân Ø12 mm; khác cũng không sao, chỉ cần biết để làm gá.
- **Nếu sai:** không có thước → chụp module nằm cạnh một vật có kích
  thước biết trước (đồng xu, thước kẻ) và gửi ảnh.

## L3 — Hỏi người bán ba câu (nếu nhãn không ghi)

- **Ở đâu:** tin nhắn với người bán.
- **Làm gì:** hỏi đúng ba câu: (1) điện áp làm việc của module là bao
  nhiêu vôn DC; (2) module đã có mạch hạn dòng chưa, hay phải mắc thêm
  điện trở; (3) góc quạt của vạch là bao nhiêu độ.
- **Thấy gì là đúng:** ba câu trả lời bằng chữ, chụp màn hình giữ lại.
- **Nếu sai:** người bán không trả lời → ghi "người bán không trả lời"
  và **coi như chưa biết**; không suy từ tên `SYD1230` hay từ module
  tương tự trên mạng.

## L4 — Cất đúng cách

- **Ở đâu:** chỗ cất linh kiện.
- **Làm gì:** cho lại vào túi, cất nơi trẻ em và vật nuôi không với tới,
  **không cắm thử vào nguồn để xem có sáng không**. Lý do ở mục "Tại sao
  chưa bật" phía trên: tia 650 nm 5 mW chiếu thẳng vào mắt gây hại trước
  khi kịp chớp mắt, và hiện chưa có kính bảo hộ lẫn hộp che.
- **Thấy gì là đúng:** hai module nằm yên trong túi.
- **Nếu sai:** đã lỡ cắm rồi → không sao nếu không ai nhìn thẳng vào
  tia; báo lại để ghi vào hồ sơ (điện áp đã dùng, hiện tượng quan sát),
  và dừng tại đó.

## L5 — Gửi lại

Ảnh L1, số đo L2, câu trả lời L3. Phiên viết sẽ ghi `docs/HARDWARE.md`,
cập nhật `docs/HARDWARE_PREP.md` B1, và đối chiếu điện áp thật với
`docs/design/LASER_CIRCUIT.md` mục 4 (nguồn 5 V từ chân `5V` Nucleo) —
nếu laser là loại 3 V thì sơ đồ phải sửa trước khi đấu.
