# Quy trình chuẩn bị mạch laser C6 — kiểm kê và đối chiếu khi không cấp nguồn

> **Đính chính 2026-10-09 — D050:** người dùng xoá toàn bộ yêu cầu an toàn/liên động của `docs/SPEC.md` mục 9 (công tắc cửa SW1, nút dừng SW2, hộp kín, watchdog, giới hạn thời gian bật laser, kính bảo hộ như điều kiện cổng, MVS của D049). Các cổng/điểm dừng an toàn trong tệp này không còn chặn việc cấp nguồn laser hay chặng nào. Phần mạch MOSFET đóng ngắt laser vẫn là thiết kế chức năng. Nội dung dưới giữ nguyên làm lịch sử.

Ngày lập: 2026-10-07 (Coder Antigravity, gói hồ sơ C6 Q5, Vòng 5 khắc phục L08–L12).
Căn cứ: `docs/design/LASER_CIRCUIT.md` mục 1–5; `docs/SPEC.md` mục 9, 12;
`docs/HARDWARE_PREP.md` nhóm B; kế hoạch `handoff/2026-09-21_c6-laser-bringup/01_PLAN.md` Vòng 4 và Vòng 5;
Quyết định `D046` và đính chính `D047`.

**Phạm vi:** kiểm kê, đối chiếu linh kiện, xác nhận đầu vào và các điểm
dừng. **KHÔNG** cấp nguồn laser, **KHÔNG** đấu mạch có điện, **KHÔNG**
bật laser. Quy trình bật/đo thuộc vòng Q8/Q9 với đủ hộp/cửa/estop/kính.

## Bảng đầu vào — điều kiện trước khi bắt đầu

| # | Điều kiện | Trạng thái hiện biết | Nguồn | Điểm dừng nếu thiếu |
| --- | --- | --- | --- | --- |
| I1 | Nucleo PA8/D7, PA9/D8, PC7/D9 đã kiểm không tải (C4) | ĐÃ KIỂM | `handoff/2026-09-21_c4-nucleo-laser-control/03_TEST.md` | Không — đã đạt |
| I2 | Laser SYD1230 ×2 đã nhận | ĐÃ NHẬN 22/09 | `docs/HARDWARE.md` mục laser | Không tiến hành nếu chưa nhận |
| I3 | MOSFET AO3400 (SOT-23, mã thân A09T theo người dùng) đã chọn theo D046 (đính chính D047) thay thế IRFZ44N | NGƯỜI DÙNG XÁC NHẬN 07/10 (chọn AO3400), 08/10 (ĐÃ MUA 18 chiếc SOT-23 rời; không tính chiếc trên bo chuyển thành 19, không coi là mua thêm 18); D046, D047 | Kế hoạch Vòng 4, Vòng 5; D046, D047; SESSION_LOG 08/10 | **DỪNG** nếu chưa có AO3400; lưu IRFZ44N làm lịch sử linh kiện nhận được lệch yêu cầu |
| I4 | R1 100 Ω đã nhận | ĐÃ NHẬN 29/09 | `docs/HARDWARE.md` | Không tiến hành nếu chưa nhận |
| I5 | R2 10 kΩ, R3 10 kΩ, R4 15 kΩ, C1 100 nF có sẵn | NGƯỜI DÙNG XÁC NHẬN 07/10 | Kế hoạch Vòng 2 mục 2 | Không tiến hành nếu chưa xác nhận |
| I6 | Breadboard và jumper | NGƯỜI DÙNG XÁC NHẬN 16/09 | `docs/HARDWARE_PREP.md` B6 | Không tiến hành nếu chưa có |
| I7 | Đồng hồ vạn năng | NGƯỜI DÙNG XÁC NHẬN 07/10: có (lịch sử); NGƯỜI DÙNG XÁC NHẬN 08/10: chốt máy mượn của người thân (nhận 10/10), model/thang đo chưa biết | Kế hoạch Vòng 2 mục 2; TEST 08/10 | Dừng phần đo ở Bước 2a cho tới khi có máy đo cụ thể |
| I8 | Hộp che | NGƯỜI DÙNG XÁC NHẬN 07/10: có | Kế hoạch Vòng 2 mục 2 | Sở hữu ≠ đạt cổng; CHƯA KIỂM độ kín |
| I9 | Kính bảo hộ | NGƯỜI DÙNG XÁC NHẬN 07/10: có | Kế hoạch Vòng 2 mục 2 | Sở hữu ≠ đạt cổng; CHƯA KIỂM dải bước sóng |
| I10 | SW1 cửa NC | Lịch sử 07/10: chưa có; NGƯỜI DÙNG XÁC NHẬN 08/10: ĐÃ MUA lô 5 cái KW11 (dùng chung thông tin với D17, chưa phân bổ; ảnh chat có cần gạt con lăn, 3 chân; chưa kiểm mã biến thể/tiếp điểm/gá), chỉ là ứng viên thử gá cơ khí tạm; CHƯA ĐẠT liên động an toàn SW1 theo SPEC 9.3; Omron SS-01GL chính thức tuần sau mới có | Kế hoạch Vòng 4; SESSION_LOG 08/10 | **DỪNG** — cần có trước khi cấp điện, không bypass bằng jumper |
| I11 | SW2 estop hai NC | CHƯA CÓ (NGƯỜI DÙNG XÁC NHẬN 07/10: chưa có cả 2) | Kế hoạch Vòng 4 mục 2 | **DỪNG** — cần có trước khi cấp điện, không bypass bằng jumper |
| I12 | Quyết định Q1 (chọn AO3400 thay thế IRFZ44N) | ĐÃ CHỐT chọn AO3400 (D046, đính chính D047) | `DECISIONS.md` D046, D047; `LASER_CIRCUIT.md` mục 0d | Đã chốt thiết kế; cần bo chuyển chân AO3400 tự làm đạt kiểm nhận Bước 2a trước khi cắm breadboard (phân biệt với adapter nguồn 12 V D9) |
| I13 | Driver hạn dòng trên module laser | CHƯA XÁC NHẬN | `docs/HARDWARE.md` | **DỪNG** — cần xác nhận trước khi cấp nguồn laser (tránh cháy diode trần) |
| I14 | Nguồn 5 V laser (USB Nucleo JP5=U5V, giới hạn dòng UM1724 bo+tải; trình tự TX11 loại bỏ phụ thuộc vòng) | XÁC NHẬN 07/10 nguồn USB Nucleo; nguồn độc lập CHƯA CÓ | `docs/design/LASER_CIRCUIT.md` mục 4–5 | **DỪNG** — tiền kiểm trước thử có điện, không cấp nguồn trước kiểm tra |
| I15 | Dòng danh định laser cho phép đo L2 | CHƯA CÓ (chỉ có cận trên < 40 mA) | `docs/design/LASER_CIRCUIT.md` L2 | **DỪNG** — Planner/người dùng chốt trước nghiệm thu L2 theo ±20% |
| I16 | Bo chuyển chân AO3400 tự làm ra chân cắm breadboard (phíp đồng cắt rãnh hàn SOT-23 ra 3 dây Dupont đực) | NGƯỜI DÙNG XÁC NHẬN 07/10: đã tự làm bo chuyển chân; CHƯA KIỂM CHỨNG chất lượng/cách ly/ánh xạ chân; phân biệt với adapter nguồn 12 V D9 | Kế hoạch Vòng 5; ảnh `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`, `c6-v4-ao3400-adapter-day-2026-10-07.png` | **DỪNG** — bắt buộc kiểm nhận ngoại quan và thông mạch không cấp nguồn tại Bước 2a đạt trước khi cắm breadboard |
| I17 | Tải giả C6: điện trở 120 Ω ±5% ≥ 1 W | ĐỀ XUẤT thiết kế Vòng 4, CHƯA CÓ / CHƯA XÁC NHẬN | Kế hoạch Vòng 4; `LASER_CIRCUIT.md` mục 5 | **DỪNG** trước khi mở chặng thử tải giả |

## Các bước kiểm kê và đối chiếu

### Bước 1 — Đọc mã MOSFET AO3400 trên thân và kiểm tra đóng gói

- **Ở đâu:** bàn làm việc, ánh sáng đủ, kính lúp hoặc chụp ảnh phóng đại nếu cần, adapter tự làm chưa cắm breadboard.
- **Làm gì:** đọc mã chữ/số in hoặc khắc trên mặt thân MOSFET AO3400
  (người dùng cung cấp mã in `A09T`). Kiểm tra đóng gói SOT-23 đã hàn
  trên adapter tự làm (mảnh phíp đồng cắt rãnh hàn 3 dây Dupont đực).
  Ghi lại nguyên văn mã đọc được. Chụp ảnh rõ mặt có chữ của MOSFET và
  adapter tự làm (đối chiếu ảnh hiện có: `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`,
  `docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png`).
- **Thấy gì là đúng:** mã đọc được khớp với thông tin cung cấp `A09T`;
  đóng gói SOT-23; adapter tự làm ra 3 đầu dây Dupont đực cắm vừa breadboard.
  Ghi nhận linh kiện `IRFZ44N 258X 77 WS` đã nhận 29/09 làm lịch sử linh kiện
  nhận được lệch yêu cầu IRLZ44N.
- **Nếu sai:** mã không đọc được, linh kiện nứt vỡ, hoặc không có adapter ra
  chân cắm breadboard → **DỪNG**, không tiến hành cắm mạch. Báo Planner.

### Bước 2 — Đối chiếu chân MOSFET AO3400 (Gate / Source / Drain) và adapter

- **Ở đâu:** bàn làm việc, adapter tự làm chưa cắm, datasheet mở trên máy tính.
- **Làm gì:** tra datasheet AOS AO3400 Rev 8. Với đóng gói SOT-23, nhìn
  từ mặt trên có chữ (cạnh 2 chân ở dưới, cạnh 1 chân ở trên):
  - Pin 1 (chân trái dưới): Gate (G)
  - Pin 2 (chân phải dưới): Source (S)
  - Pin 3 (chân giữa trên): Drain (D)
  Đối chiếu đường dẫn từ 3 chân SOT-23 qua các đảo phíp đồng ra 3 dây Dupont
  đực của adapter tự làm. Phân biệt rõ với thứ tự chân TO-220 (1:G, 2:D, 3:S)
  của IRFZ44N. Ghi thứ tự chân và định danh đảo phíp vào bảng đối chiếu.
- **Thấy gì là đúng:** thứ tự chân SOT-23 khớp Pin 1=G, Pin 2=S, Pin 3=D
  theo datasheet AOS AO3400 Rev 8; định danh được ba đảo đồng tương ứng với
  chân G, S, D của SOT-23 trên adapter tự làm.
- **Nếu sai:** thứ tự chân không xác định hoặc không phân biệt được chân G/S/D
  trên adapter → **DỪNG**, không cắm vào breadboard.

### Bước 2a — Kiểm nhận adapter MOSFET AO3400 tự làm (tuyệt đối không cấp nguồn)

- **Ở đâu:** Bàn làm việc sạch, phẳng, khô ráo, ánh sáng tốt. Adapter MOSFET AO3400 tự làm đặt rời hoàn toàn trên mặt bàn cách điện; **tuyệt đối không cắm vào breadboard, không nối Nucleo, không nối USB, không nối tải giả, không nối nguồn hay module laser**.
- **Làm gì:**
  Tiến hành kiểm tra adapter rời theo 4 nội dung tuần tự, sử dụng đồng hồ vạn năng (VOM) và quan sát ngoại quan. Tuyệt đối không dùng nguồn ngoài hay máy đo điện áp cao (Megohmmeter).
  1. *Chuẩn bị máy đo và chống tĩnh điện:*
     - Xả tĩnh điện trên người (chạm tay vào vật kim loại tiếp đất lớn trước khi cầm adapter). Thao tác nhẹ nhàng, tránh tĩnh điện phóng vào chân Gate của MOSFET.
     - Kiểm tra đồng hồ vạn năng (VOM): dùng que đo nhọn, sạch. Nêu rõ model và tài liệu VOM thực; nếu chưa rõ model VOM hoặc chưa biết rõ khả năng máy đo thì ghi nhận thiếu đầu vào và dừng phần đo tương ứng (chỉ được ghi nhận ngoại quan). Tuyệt đối cẩn thận không để đầu que đo trượt làm ngắn mạch hai chân SOT-23 sát nhau trong lúc tì que.
  2. *Kiểm tra ngoại quan cơ học (Visual inspection):*
     - Dùng kính lúp hoặc chụp ảnh phóng đại soi kỹ các rãnh cắt giữa các đảo đồng: kiểm tra rãnh cắt có đứt hẳn lớp đồng không, có ba via (bavia đồng), vụn đồng hay cầu thiếc hàn bắc qua rãnh không. (Lưu ý: rãnh hẹp nhìn trên ảnh chưa kết luận chập; cần đối chiếu bằng đo điện trở ở bước sau).
     - Kiểm tra mối hàn 3 chân SOT-23 vào các đảo đồng: mối hàn ngấu thiếc hay mối hàn nguội/nứt; lõi dây đồng của 3 dây Dupont tại mối hàn có bị tòe, bung sợi hay chạm sang đảo lân cận không.
     - Kiểm tra độ bền cơ học: dây nối có bị lỏng lẻo dễ đứt khi uốn nhẹ không.
  3. *Định danh và đo thông mạch đường cùng nút (Pin ↔ Đảo ↔ Dây ↔ Đầu cắm):*
     - Đặt VOM ở thang đo thông mạch (Continuity / Beep) hoặc thang điện trở thấp (200 Ω).
     - Đo thông mạch từ từng chân SOT-23 / đảo đồng tới đầu cắm đực của dây Dupont tương ứng (đối chiếu màu dây vàng, xanh lá, cam trên hiện vật):
       + Chân 1 (Gate) → Đảo G → Mối hàn dây → Đầu cắm đực G: đo giữa chân 1 (hoặc đảo G) và đầu kim cắm đực tương ứng, điện trở phải xấp xỉ 0 Ω (thông mạch, beep).
       + Chân 2 (Source) → Đảo S → Mối hàn dây → Đầu cắm đực S: đo giữa chân 2 (hoặc đảo S) và đầu kim cắm đực tương ứng, điện trở phải xấp xỉ 0 Ω (thông mạch, beep).
       + Chân 3 (Drain) → Đảo D → Mối hàn dây → Đầu cắm đực D: đo giữa chân 3 (hoặc đảo D) và đầu kim cắm đực tương ứng, điện trở phải xấp xỉ 0 Ω (thông mạch, beep).
       *Lưu ý:* Phải đo trực tiếp trên từng nút riêng lẻ; không dùng đường dẫn qua thân MOSFET làm bằng chứng dây nối thông.
  4. *Kiểm tra cách ly và đặc tính bán dẫn MOSFET trên adapter (xét diode thân và điện tích Gate):*
     - *Thao tác xả điện tích Gate trước khi đo:* Dùng que đo hoặc nhíp kim loại chạm đồng thời chân Gate (G) và chân Source (S) trong 1–2 giây để xả hết điện tích ký sinh trên cực Gate ($V_{GS} = 0\text{ V}$), đảm bảo MOSFET ở trạng thái ngắt hoàn toàn. Tháo que xả trước khi tiến hành đo. Thao tác này chỉ là tiếp xúc que trên adapter rời, không thay đổi sơ đồ mạch.
     - *Đo cách ly cực Gate (G–S và G–D):*
       + Đặt VOM ở thang đo điện trở cao (2 MΩ hoặc tự động thang) hoặc thang đo thông mạch.
       + Đo cặp G và S: đo cả hai chiều que (đỏ tại G / đen tại S, và đảo que đỏ tại S / đen tại G).
       + Đo cặp G và D: đo cả hai chiều que (đỏ tại G / đen tại D, và đảo que đỏ tại D / đen tại G).
       + Kết quả mong đợi: Cực Gate cách ly hoàn toàn với Source và Drain; đồng hồ phải chỉ hở mạch (OL / quá thang) ở cả hai chiều trên cả hai cặp G–S và G–D.
     - *Đo cặp Drain – Source (D–S) có xét diode thân (Body Diode):*
       + Theo datasheet AOS AO3400 Rev 8, MOSFET kênh N có tích hợp diode thân ngược chiều giữa Source và Drain (Anode nối tại Source, Cathode nối tại Drain).
       + Đặt VOM ở thang đo Diode (Diode test):
         * Chiều thuận diode thân (Que ĐỎ tại Source / pin 2, Que ĐEN tại Drain / pin 3): Diode thân dẫn thuận. VOM hiển thị điện áp rơi thuận của tiếp giáp P-N (có chỉ số dẫn thuận một chiều, ghi nguyên số đọc trên màn hình VOM). *Lưu ý:* Thông số $V_{SD}$ điển hình 0,7 V trong datasheet AOS là đo tại dòng lớn $I_S = 1\text{ A}$; dòng thử của VOM nhỏ hơn nhiều nên chỉ dùng để sàng lọc xác nhận tính dẫn điện một chiều của diode thân, không chế ngưỡng điện áp mới và không ép buộc phải đúng 0,7 V tuyệt đối để nghiệm thu.
         * Chiều nghịch diode thân (Que ĐỎ tại Drain / pin 3, Que ĐEN tại Source / pin 2) — sau khi đã xả Gate (nối tắt tạm G–S): Diode thân phân cực ngược, kênh dẫn ngắt hoàn toàn. VOM phải hiển thị hở mạch (OL).
       + *Cảnh báo kỹ thuật:* Tuyệt đối KHÔNG yêu cầu cả hai chiều D–S đều là OL (vì diode thân dẫn thuận từ S sang D là bản chất cấu tạo linh kiện). Tuyệt đối KHÔNG nghe tiếng beep ở chiều que bất kỳ rồi vội kết luận chập cầu đồng khi chưa xác định rõ chiều que đo, thang đo và chưa xả điện tích Gate.
   - Điền kết quả vào bảng kiểm nhận (để trống phần chưa có số đo thực tế; lưu ý: nhãn đảo đồng trong bảng là **ánh xạ dự kiến theo ảnh** nhìn thẳng mặt chữ A09T với cạnh hai chân ở phía dưới — **cần đối chiếu với hiện vật thực tế** trước khi kết luận):

| Cặp đo / Đối tượng | Chân SOT-23 (Pin) | Đảo đồng (dự kiến — cần đối chiếu) | Màu dây | Đầu chân cắm | Thang đo VOM | Chiều que đo (Đỏ / Đen) | Kết quả lý thuyết kỳ vọng | Kết quả đo thực tế (người dùng điền khi đo) | Đánh giá |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Thông nút G | Pin 1 (Gate) | Đảo dưới-trái (dự kiến G) | (chưa đối chiếu màu) | Đầu cắm G | Thông mạch (Ω) | Bất kỳ | Thông mạch ($\approx 0\text{ }\Omega$, beep) | *(để trống)* | Chưa đo |
| Thông nút S | Pin 2 (Source) | Đảo dưới-phải (dự kiến S) | (chưa đối chiếu màu) | Đầu cắm S | Thông mạch (Ω) | Bất kỳ | Thông mạch ($\approx 0\text{ }\Omega$, beep) | *(để trống)* | Chưa đo |
| Thông nút D | Pin 3 (Drain) | Đảo trên (dự kiến D) | (chưa đối chiếu màu) | Đầu cắm D | Thông mạch (Ω) | Bất kỳ | Thông mạch ($\approx 0\text{ }\Omega$, beep) | *(để trống)* | Chưa đo |
| Cách ly G–S | Pin 1 ↔ Pin 2 | Đảo G ↔ Đảo S (dự kiến) | — | — | Trở cao / Diode | Đỏ G, Đen S | OL (hở mạch) | *(để trống)* | Chưa đo |
| Cách ly G–S | Pin 1 ↔ Pin 2 | Đảo G ↔ Đảo S (dự kiến) | — | — | Trở cao / Diode | Đỏ S, Đen G | OL (hở mạch) | *(để trống)* | Chưa đo |
| Cách ly G–D | Pin 1 ↔ Pin 3 | Đảo G ↔ Đảo D (dự kiến) | — | — | Trở cao / Diode | Đỏ G, Đen D | OL (hở mạch) | *(để trống)* | Chưa đo |
| Cách ly G–D | Pin 1 ↔ Pin 3 | Đảo G ↔ Đảo D (dự kiến) | — | — | Trở cao / Diode | Đỏ D, Đen G | OL (hở mạch) | *(để trống)* | Chưa đo |
| Diode thân S → D | Pin 2 → Pin 3 | Đảo S → Đảo D (dự kiến) | — | — | Diode | Đỏ S, Đen D | Có chỉ số dẫn thuận một chiều (ghi nguyên số đọc) | *(để trống)* | Chưa đo |
| Kênh khoá D → S | Pin 3 → Pin 2 | Đảo D → Đảo S (dự kiến) | — | — | Diode / Trở | Đỏ D, Đen S (sau xả G–S) | OL (hở mạch) | *(để trống)* | Chưa đo |

- **Thấy gì là đúng:**
  - Ngoại quan: các rãnh cắt cách ly hoàn toàn, không có bavia hay cầu thiếc nối tắt giữa các đảo đồng; mối hàn bóng ngấu, dây dẫn chắc chắn, không chạm chập.
  - Đường cùng nút: cả 3 đường (G, S, D) đều thông mạch tốt ($\approx 0\text{ }\Omega$) từ chân linh kiện ra đầu cắm đực Dupont tương ứng. Ánh xạ màu dây ra chân cắm được xác định không nhầm lẫn.
  - Cách ly: Cặp G–S và G–D đều hở mạch (OL) ở cả hai chiều đo. Cặp D–S hiển thị đúng tính chất diode thân (dẫn thuận từ S sang D, ngắt hở mạch OL từ D sang S sau khi xả Gate).
  - Không có hiện tượng chạm chập giữa các đảo đồng.
- **Nếu sai:**
  - Có cầu thiếc, bavia đồng, hoặc đo G–S / G–D thấy dẫn điện / điện trở thấp ($\ll \text{M}\Omega$) → **DỪNG**, nghi ngờ chập rãnh hoặc hỏng MOSFET. Dùng dao trổ/giũa cạo sạch rãnh đồng hoặc hút thiếc hàn lại. Nếu không khắc phục được thì bỏ adapter, làm lại cái khác.
  - Đo cùng nút bị hở mạch (dây đứt ngầm, mối hàn nguội không tiếp xúc) → **DỪNG**, hàn lại dây.
  - Đo D–S thấy thông mạch cả hai chiều (kể cả sau khi xả Gate) hoặc hở mạch cả hai chiều (hỏng diode thân) → **DỪNG**, nghi ngờ MOSFET bị đánh thủng hoặc chết đứt. Thay MOSFET khác.
  - Dây dẫn lỏng lẻo, rãnh phíp nứt vỡ, đầu cắm bị lỏng → **DỪNG**, sửa cơ khí trước khi sử dụng.
  - Thiếu đồng hồ vạn năng phù hợp hoặc chưa có kết quả đo → **DỪNG**, giữ nguyên trạng thái CHƯA KIỂM CHỨNG, tuyệt đối không cắm adapter vào breadboard và không cấp bất kỳ nguồn điện nào. Báo Planner.

### Bước 3 — Kiểm kê điện trở và tụ

- **Ở đâu:** bàn làm việc, đồng hồ vạn năng chế độ đo trở (Ω).
- **Làm gì:** đo từng điện trở bằng đồng hồ, đối chiếu giá trị:
  - R1: 100 Ω (4 vạch: nâu-đen-nâu-nhũ vàng là ±5%; 5 vạch: nâu-đen-đen-đen-nâu là ±1%)
  - R2, R3: 10 kΩ (4 vạch: nâu-đen-cam-nhũ vàng là ±5%; 5 vạch: nâu-đen-đen-đỏ-nâu là ±1%)
  - R4: 15 kΩ (4 vạch: nâu-xanh lá-cam-nhũ vàng là ±5%; 5 vạch: nâu-xanh lá-đen-đỏ-nâu là ±1%)
  - C1: 100 nF — đọc nhãn trên tụ (thường ghi `104`), không đo bằng VOM
    thông thường.
  Ghi giá trị đo vào bảng.
- **Thấy gì là đúng:** giá trị đo bằng đồng hồ nằm trong khoảng dung sai quy định của chính điện trở đó theo vạch màu:
  - Với điện trở dung sai ±1% (vạch dung sai nâu (brown)): giá trị đo nằm trong khoảng ±1% trị danh định (ví dụ 10 kΩ: 9900–10100 Ω, 10000 Ω trong miền, 9900 Ω và 10100 Ω ở biên miền; 100 Ω: 99–101 Ω; 15 kΩ: 14850–15150 Ω).
  - Với điện trở dung sai ±5% (vạch dung sai nhũ vàng (gold)): giá trị đo nằm trong khoảng ±5% trị danh định (ví dụ 10 kΩ: 9500–10500 Ω, 9500 Ω và 10500 Ω ở biên miền; 100 Ω: 95–105 Ω; 15 kΩ: 14250–15750 Ω).
  - Với điện trở 15 kΩ, vạch chữ số 5 dùng màu xanh lá (green) để phân biệt rõ với xanh dương.
  Tụ C1 có nhãn đọc rõ `104` hoặc `100nF`.
- **Nếu sai:**
  - Giá trị đo lệch ngoài khoảng dung sai quy định của chính điện trở đó (ví dụ với điện trở ±1%: giá trị đo < 99% hoặc > 101% trị danh định, như 10 kΩ đo 9899 Ω hay 10101 Ω ở ngoài miền, hoặc 10 kΩ đo 10,2 kΩ lệch 2% là ngoài dung sai quy định dù chưa vượt 5%; với điện trở ±5%: giá trị đo < 95% hoặc > 105% trị danh định, như 10 kΩ đo 9499 Ω hay 10501 Ω ở ngoài miền), hoặc không đọc được vạch màu/dung sai, hoặc chưa đủ khả năng đo / đầu vào thiếu → ghi **CHƯA XÁC NHẬN**, dừng kết luận đạt, đánh dấu linh kiện để đối chiếu thêm hoặc thay linh kiện khác; **DỪNG** nếu hết linh kiện đạt yêu cầu. Tuyệt đối không mặc định ±5% khi chưa đọc được dung sai, không dùng ngưỡng chung > ±5% để bỏ qua sai số.
  - Tụ C1 không đọc được nhãn `104`/`100nF` hoặc nứt vỡ → **DỪNG**, thay tụ khác.

### Bước 4 — Kiểm tra laser (KHÔNG CẤP NGUỒN)

- **Ở đâu:** bàn làm việc, laser chưa nối dây; tuyệt đối không cấp điện hay cắm que đo có dòng pin vào hai dây.
- **Làm gì:**
  - Đọc nhãn/mã trên thân laser: mã model, bước sóng, công suất, cấp
    (Class). Đối chiếu với `docs/HARDWARE.md` mục laser.
  - Kiểm tra ngoại quan cơ học hai dây: dây đỏ (+) và đen (−), kiểm tra mối
    nối cáp vào thân module chắc chắn, vỏ bọc cách điện nguyên vẹn, không dập
    nát, không chạm chập cơ học mắt thường thấy được. Tuyệt đối không đo điện
    hay đo thông mạch bằng đồng hồ lên module laser khi chưa có chỉ dẫn an toàn.
  - Ghi lại: chiều dài dây (~130 mm), đường kính thân (Ø12 mm × 40 mm), đầu
    phát có vành khía (khả năng chỉnh tiêu cự là GIẢ THUYẾT / CHƯA KIỂM CHỨNG,
    chưa thử xoay; không hướng dẫn xoay, đo điện hoặc bật laser để xác nhận
    trong gói Q5).
- **Thấy gì là đúng:** nhãn khớp SYD1230, 650 nm, ≤ 5 mW, Class IIIa; 2 dây
  đúng màu đỏ/đen, vỏ bọc nguyên vẹn, mối nối chắc chắn, không hư hại cơ học.
- **Nếu sai:** không có nhãn, dây đứt, vỏ dập hở lõi đồng, hoặc lỏng mối nối → **DỪNG**, cách ly module, dùng module dự phòng.

### Bước 5 — Đối chiếu hộp che và kính

- **Ở đâu:** phòng làm việc.
- **Làm gì:**
  - Hộp: kiểm tra có khe nào cho tia laser thoát ra phía người ngồi không.
    Đánh dấu vị trí sẽ khoét cửa sổ camera. Kiểm tra cửa có thể đóng kín
    được không.
  - Kính: đọc nhãn dải bước sóng. Đối chiếu với 600–700 nm (laser đỏ
    650 nm).
  Ghi kết quả vào `docs/HARDWARE.md`.
- **Thấy gì là đúng:** hộp kín không có khe rõ; kính ghi chặn dải bao
  gồm 650 nm.
- **Nếu sai:** hộp có khe lớn → bịt lại hoặc làm hộp mới. Kính không
  ghi dải hoặc dải không bao 650 nm → **DỪNG**, tìm kính khác.

### Bước 6 — Tổng kết và quyết định

- **Ở đâu:** máy tính, cập nhật hồ sơ.
- **Làm gì:** ghi kết quả bước 1–5 vào `docs/HARDWARE.md` bảng đối chiếu.
  Đối chiếu bảng đầu vào I1–I17 ở đầu quy trình này. Ghi rõ:
  - Những điều kiện nào ĐẠT
  - Những điều kiện nào CHƯA ĐẠT và lý do
  - **Tách rõ 3 cổng thực hiện:**
    + **Cổng 1 — Chuẩn bị / kiểm kê (Q5 hiện tại):** Hoàn thành gói hồ sơ thiết kế, kiểm kê vật tư ngoại quan không cấp điện, đối chiếu I1–I17. Tuyệt đối không cấp nguồn laser, không đấu mạch có điện.
    + **Cổng 2 — Thử tải giả không phát tia (Q8 tương lai, chờ kế hoạch có điện riêng):** Chỉ mở khi có kế hoạch Q8 được duyệt, đủ SW1/SW2 thật, bo chuyển chân AO3400 tự làm đạt kiểm nhận Bước 2a (không chập, đúng ánh xạ chân, cách ly và diode thân đạt yêu cầu), điện trở tải giả Rtest 120 Ω ±5% ≥ 1 W đã có; laser tháo rời vật lý khỏi mạch; tiến hành tiền kiểm nguồn và đo thử dưới tải giả.
    + **Cổng 3 — Thử laser thật và nghiệm thu (Q8/Q9 tương lai, chờ kế hoạch có điện riêng):** Chỉ mở khi chặng thử tải giả đạt 100%, có đủ hộp che kín B5, kính bảo hộ B10, driver module laser SYD1230 được xác nhận, và dòng danh định laser được Planner/người dùng chốt để đo L2.
- **Thấy gì là đúng:** bảng đầy đủ, mọi ô có trạng thái rõ ràng, phân biệt rõ các chặng.
- **Nếu sai:** bảng thiếu ô → bổ sung trước khi tiếp tục.

## Điểm dừng tổng hợp — KHÔNG được bỏ qua

1. **Chưa có SW1/SW2:** không được cấp nguồn mạch, dù có hộp che; tuyệt đối không bypass bằng jumper.
2. **Chưa có bo chuyển chân AO3400 tự làm hoặc bo chuyển chân chưa qua kiểm nhận Bước 2a:** DỪNG, không cắm trực tiếp chân SOT-23 rời hoặc bo chuyển chân chưa kiểm nhận vào breadboard (phân biệt với adapter nguồn 12 V D9).
3. **Chưa có tải giả 120 Ω ≥ 1 W:** DỪNG, không mở chặng thử tải giả có điện.
4. **Chưa có dòng danh định laser:** DỪNG, chưa nghiệm thu L2 theo ±20%.
5. **Thiếu driver hạn dòng hoặc nguồn laser chưa kiểm:** DỪNG, không cấp nguồn laser.
6. **Chưa đủ điều kiện an toàn (`docs/SPEC.md` mục 9):** không bật laser
   trong bất kỳ tình huống nào.

## Tham chiếu

- `docs/design/LASER_CIRCUIT.md` — sơ đồ nguyên lý, phép đo L1–L8, trình tự 4 giai đoạn
- `docs/SPEC.md` mục 9, 12 — yêu cầu an toàn và mạch
- `docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md` — quy trình tiếp nhận laser
- `docs/procedures/quy-trinh-c4-nucleo-khong-tai.md` — quy trình C4 không tải
- `handoff/2026-09-21_c6-laser-bringup/01_PLAN.md` — kế hoạch C6 Vòng 4 và Vòng 5
- `DECISIONS.md` D046, D047 — lựa chọn AO3400 thay thế IRFZ44N và đính chính thông số / adapter
