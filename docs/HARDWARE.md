# Hồ sơ phần cứng

Mốc: 2026-09-15. Phân biệt thiết bị người dùng có với linh kiện đang dự kiến trong bản thiết kế.

| Thiết bị | Trạng thái hiện biết | Tài liệu cần đặt cùng mã nguồn |
| --- | --- | --- |
| Nucleo-F446RE | ĐÃ CHẠY 2026-09-16: PCB `MB1136 rev C`, ST-LINK/V2-1 firmware `V2J45M31`, SN `066AFF485270535067114419`, COM ảo `COM3`; nạp bằng `STM32_Programmer_CLI`, trả lời PING 100/100 hai lần, LD2 nháy đều (người dùng quan sát). Nguồn: chỉ USB qua CN1, `JP5` ở `U5V`. `X3` HSE để trống, firmware dùng HSI. Ảnh người dùng gửi 16/09 tối, tệp `docs/logs/nucleo-board-2026-09-16.jpg` đã trong Git (ĐÃ KIỂM Ở ĐÂY bằng Pillow: JPEG 685×913, 149319 byte, sha256 đầu `2b36a33d71ca`, đưa vào Git tối 16/09) | Ảnh đã có; sơ đồ đấu dây ngoài bo chưa có vì chưa nối gì ngoài USB |
| ESP32-S3 N16R8 có camera | Đang có; PID 0x3660, Flash 16 MB; PSRAM 8192 KB từ 16/09 với `OPI PSRAM` (D008). Ảnh mặt trước `docs/logs/s3-board-mounted-2026-09-17.jpg` (NGƯỜI DÙNG CUNG CẤP 17/09, ĐÃ KIỂM Ở ĐÂY: JPEG 631×843, sha256 đầu `948408742177`): nhãn in trên module đọc được `ESP32-S3 WROOM`, module camera nối bằng cáp dẹt tới đầu nối FPC ở mặt trước, hai cổng USB-C cạnh nhau, hai nút bấm; bo gắn trên perfboard xanh, kẹp trong chân đế trắng. Nhà sản xuất bo, mặt sau và pinout CHƯA đọc được từ ảnh này. Ảnh cận module camera 17/09 (NGƯỜI DÙNG CUNG CẤP, trong chat): cáp dẹt in `TY-OV3660` và `21MM`, phần còn lại chưa đọc; barrel ống kính có vành khía kiểu ren xoay, tem tròn có năm 2027; người dùng xác nhận đã bóc màng bảo vệ, ống kính sạch; 17/09 vặn barrel với lực vừa: cứng, không hề di chuyển → không chỉnh tiêu cự bằng tay được. Khảo sát 17/09: ống kính lấy nét ở xa, xem `docs/tests/2026-09-17_s3_quang_hoc.md`. Ảnh cận hai mặt bo 18/09 ĐÃ VÀO GIT: `docs/logs/s3-board-front-2026-09-18.jpg` (JPEG 685×913, 181226 byte, sha256 đầu `d337137d838c`) và `s3-board-back-2026-09-18.jpg` (685×913, 168607 byte, `67430a0a0ead`), NGƯỜI DÙNG CUNG CẤP, ĐÃ KIỂM Ở ĐÂY bằng Pillow; ảnh cận hơn trong chat đọc được nhãn cáp camera `TY-OV3660-21MM-V3.0`. ĐỌC TỪ ẢNH: mặt trước có đầu nối FPC 24 chân nắp gạt cho camera, module camera cắm qua đầu nối đó và tựa lên một header đen ở mép trên; hai USB-C ghi ở mặt sau là `USB-UART` (trái) và `USB-OTG` (phải); nút `EN/RST` và `BOOT`; LED `ON`, `TX`, `RX`, `IO48`; hai hàng header 20 chân mỗi bên, nhãn chân in cạnh header khớp sơ đồ người bán — bảng đầy đủ ở mục "Pinout bo ESP32-S3 WROOM CAM" dưới đây. Mặt sau: khe microSD, chú giải `─: Camera`, `~: SD Card`, `●: PSRAM` đánh dấu chân đã dùng, IC USB-UART nhỏ, IC nguồn, tụ. GIẢ THUYẾT chưa xác nhận: bố cục và chú giải này giống bo Freenove ESP32-S3-WROOM CAM (FNK0085). TRANG NGƯỜI BÁN (NGƯỜI DÙNG CHÉP 18/09): tên hàng "KIT ESP32-S3 N16R8 Camera board OV3660, OV5640"; mô tả chung: ESP32-S3 hai nhân, Flash 16 MB, PSRAM 8 MB, "hỗ trợ gắn camera module OV3660 hoặc OV5640 (tùy phiên bản)", giao tiếp camera DVP song song (D0–D7, PCLK, VSYNC, HREF, SCCB, XCLK, PWDN/RESET), nguồn 5 V qua USB hạ áp 3,3 V, GPIO ra header "tùy phiên bản". KHÔNG có tên hãng. Cùng ngày người dùng gửi thêm SƠ ĐỒ CHÂN của người bán: khớp 14/14 chân camera với firmware đang chạy và khớp nhãn in trên bo → pinout ĐÃ ĐỐI CHIẾU, bảng ở mục riêng dưới; nhà sản xuất vẫn không rõ nhưng không còn cần. Điều dùng được: cùng người bán có module OV5640 cho bo này → ứng viên B12 | Ảnh mặt sau đủ đọc nhãn, ảnh cận đầu nối camera, tên bo và pinout đã dùng, firmware và cấu hình IDE |
| ESP32-CAM | Đã nạp và chạy camera theo báo cáo người dùng | Sketch đang chạy, cấu hình IDE, log và ảnh mẫu |
| Raspberry Pi Global Shutter Camera | Đang có; trước đó người dùng báo chưa có lens và Raspberry Pi | Chỉ cập nhật khi chuyển sang hướng nâng cấp; không đưa vào đường camera cơ sở |
| NEMA17 / A4988 / đai và mâm | Có trong thiết kế; sở hữu thực tế CHƯA XÁC NHẬN | Mã linh kiện thực, kích thước, ảnh lắp và thông số đã đo |
| Laser / nguồn / HOME / liên động / PCB | Có trong thiết kế; tình trạng thực tế CHƯA XÁC NHẬN | Sơ đồ, BOM đã cập nhật, hồ sơ kiểm tra |
| Vật mẫu hộp và trụ nhám, thước mm, breadboard, dây jumper, điện trở 10 kΩ | NGƯỜI DÙNG XÁC NHẬN 16/09 tối: đang có. 17/09: vật mẫu cho quang học là khối gỗ 30×32×49 mm (kích thước người dùng đo), thước nhựa trong ~15 cm; xem `docs/HARDWARE_PREP.md` A1 | Ảnh vật và thước khi dùng; hộp 60–100 mm cho tuần 2 |
| Laser vạch SYD1230 (×2) | **NGƯỜI DÙNG CUNG CẤP + ĐỌC TỪ ẢNH 2026-09-22.** Nhãn dán trên thân, đọc từ `docs/logs/laser-syd1230-nhan-2026-09-22.jpg` (ĐÃ KIỂM Ở ĐÂY bằng Pillow: JPEG 685×913, 66617 byte, sha256 đầu `7e6c66cadb48`; bản thu nhỏ từ ảnh người dùng gửi, ảnh gốc ở điện thoại): `DANGER — LASER RADIATION - A… DIRECT EYE EXPOSU…`, `Model: SYD1230`, `Wavelngth: 650nm` (in sai chính tả trên nhãn), `Class IIIa Laser Pro…`, và một hàng ô đánh dấu công suất `…W ☐10mW ☐20mW ☐30mW` — ô đầu bị ngón tay che khi chụp; NGƯỜI DÙNG XÁC NHẬN 22/09: ô được tick là **5mW** (khớp yêu cầu B1 "công suất ≤ 5 mW"). NGƯỜI DÙNG ĐO 22/09: thân Ø12 mm × dài 40 mm, dây dài 130 mm, **2 dây: đỏ và đen** (không có dây điều khiển riêng). NGƯỜI BÁN TRẢ LỜI 22/09: điện áp 3–5 V DC, dòng tiêu thụ < 40 mA; góc quạt và "có mạch hạn dòng không" **người bán không xác định được**. ĐỌC TỪ ẢNH: đầu phát có vành khía xoay được kiểu chỉnh tiêu cự (GIẢ THUYẾT, chưa thử xoay). GIẢ THUYẾT hợp lý nhưng CHƯA MỞ VỎ KIỂM: module nhận dải 3–5 V thì phải có mạch ổn dòng bên trong, vì diode laser trần không chịu được dải đó. CHƯA KIỂM CHỨNG: vạch hay chấm, góc quạt, vành khía có chỉnh được tiêu cự không. **CHƯA CẤP NGUỒN LẦN NÀO** và chưa được phép bật: `docs/SPEC.md` mục 9 đòi hộp kín, công tắc cửa ngắt nguồn bằng phần cứng, nút dừng và kính bảo hộ — cả bốn đều chưa có (R01 mức Chặn vẫn mở, hoãn theo D022). Quy trình và bảng 6 điều kiện: `docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md` | Còn thiếu: sau khi đấu — dòng đo thật ở 5 V, ảnh vạch trên tấm trắng ở 250 mm, bề rộng vạch theo pixel, góc quạt đo từ ảnh |
| Module camera FD5640 500W-V11 (×2) | **NGƯỜI DÙNG CUNG CẤP + ĐỌC TỪ ẢNH 2026-09-22.** Mã in trên cáp FPC: `FD5640 500W-V11`. Ảnh trong Git, ĐÃ KIỂM Ở ĐÂY bằng Pillow (JPEG 685×913, bản thu nhỏ từ chat): `docs/logs/camera-fd5640-mat-truoc-2026-09-22.jpg` (161841 byte, `947bd0d00ed3`), `camera-fd5640-mat-sau-2026-09-22.jpg` (129751 byte, `f07c8c69343f`), `camera-fd5640-vs-ov3660-truoc-2026-09-22.jpg` (135862 byte, `afc9101cad04`), `camera-fd5640-vs-ov3660-sau-2026-09-22.jpg` (166416 byte, `ddceda2fb080`). **ĐỐI CHIẾU CƠ HỌC VỚI MODULE ĐANG DÙNG — ĐẠT:** NGƯỜI DÙNG XÁC NHẬN bề rộng cáp và số chân bằng nhau; ĐỌC TỪ ẢNH mặt sau: **cả hai cáp đều in số `24`** cạnh dãy tiếp điểm, dãy tiếp điểm trông cùng bề rộng và cùng bước. ĐỌC TỪ ẢNH: thân module FD5640 to hơn OV3660 rõ rệt, vỏ kim loại vuông kiểu có cuộn lấy nét (VCM), mặt sau dán nhãn trắng trống chữ; OV3660 vỏ nhựa đen nhỏ. Người bán báo: tự động lấy nét, tiêu cự 3 mm, điện áp làm việc 1,8–2,8 V, phạm vi chụp 0 → vô cùng. **CHƯA KIỂM CHỨNG**: chưa cắm vào bo, chưa đọc PID cảm biến, **thứ tự chân chưa đối chiếu** (cùng 24 chân không có nghĩa cùng pinout). GIẢ THUYẾT (chỉ để biết phải kiểm gì): "5640" gợi cảm biến OV5640, "500W" gợi 5 triệu điểm ảnh — xác nhận bằng PID `0x5640` đọc từ firmware. Đây là mục B12 nay đã thành hàng thật. Quy trình: `docs/procedures/quy-trinh-tiep-nhan-camera-fd5640.md` | Còn thiếu: log Serial khi khởi động (PID), phiên chụp `capture_fd5640_250mm` để so bảng 17/09; nếu dùng thật: hồ sơ hiệu chuẩn mới, không dùng lẫn số đo với OV3660 |
| MOSFET IRFZ44N + điện trở 100 Ω 1/4 W | **NGƯỜI DÙNG CUNG CẤP 2026-09-29: đã nhận.** MOSFET mã in trên thân: `IRFZ44N 258X 77 WS` (số lượng CHƯA XÁC NHẬN). Điện trở: 100 Ω, 1/4 W, vạch màu (số lượng CHƯA XÁC NHẬN). **Điện trở khớp yêu cầu B3.** **MOSFET LỆCH yêu cầu B2**: `docs/HARDWARE_PREP.md` B2 và `docs/design/LASER_CIRCUIT.md` mục 3 (Q1) đòi loại **logic-level** — tên phải có chữ **IRLZ** (IRLZ44N/IRLZ34N), Vgs(th) ≤ 2 V, mở gần hết ở Vgs = 3,3 V. `IRFZ44N` là loại **thường** (không có "L"), Vgs(th) điển hình 2–4 V, datasheet hãng thường chỉ cho Rds(on) tại Vgs = 10 V (đôi khi 5 V), **không có số liệu ở 3,3 V** — rủi ro không dẫn bão hoà hoàn toàn khi lái bằng GPIO Nucleo (3,3 V), khác `docs/HARDWARE_PREP.md` dòng 173 đã cảnh báo trước khi mua ("Phải là chữ IRLZ… không phải IRFZ44N"). Đây là đúng phát hiện R10 đang mở (D022) nay có linh kiện thật để đo. **Chưa cấp nguồn, chưa đo Vds.** Quyết định giữ/đổi linh kiện chờ phép đo L3 (`LASER_CIRCUIT.md` mục 5, Vds ≤ 0,2 V khi dẫn với tải laser thật) — không suy từ tên linh kiện | Còn thiếu: đo Vds khi dẫn (L3) với tải laser SYD1230 thật, sau khi đủ điều kiện an toàn để cấp nguồn |
| MOSFET AO3400 (A09T) | **NGƯỜI DÙNG CUNG CẤP 2026-10-07: đã có linh kiện rời.** Đã chọn thay thế IRFZ44N theo Quyết định D046 (07/10, đính chính D047). Mã in trên thân theo người dùng: `A09T`, đóng gói SOT-23 rời; người dùng đã tự làm adapter phíp đồng cắt rãnh ra 3 đầu dây Dupont đực (ảnh `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`, `docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png`); nguồn hiện dùng là USB Nucleo. Theo datasheet AOS AO3400 Rev 8: MOSFET kênh N logic-level, Rds(on) ≤ 52 mΩ tại Vgs = 2,5 V, Id danh định 5,8 A (TA = 25 °C, VGS = 10 V); chân Pin 1 = Gate, Pin 2 = Source, Pin 3 = Drain. **CHƯA KIỂM CHỨNG**: chưa đo thông số thực tế, chưa kiểm nhận adapter không cấp nguồn ở Bước 2a | Kiểm nhận adapter Bước 2a không cấp nguồn, số đo Vds (L3) khi dẫn dưới tải |
| Máy hiện sóng GW Instek GDS-1102B | **NGƯỜI DÙNG XÁC NHẬN 2026-10-02 (ghi qua chặng Planner/Codex, `docs/SESSION_LOG.md` mục cùng ngày).** **Không phải tài sản dự án** — thiết bị của công ty nơi người dùng đang thực tập, mượn dùng, không mua. THEO HÃNG: 2 kênh, băng thông 100 MHz, tốc độ lấy mẫu tối đa 1 GSa/s (1 tỷ mẫu/giây — chuẩn hoá từ cách ghi ban đầu "1GB/s" của người dùng, đơn vị đúng là lấy mẫu chứ không phải truyền dữ liệu). Nguồn: [GW Instek — GDS-1000B, model GDS-1102B](https://www.gwinstek.com/en-US/products/detail/GDS-1000B), đối chiếu 02/10/2026. **CHƯA KIỂM CHỨNG**: đầu dò thực tế (mã, số lượng, hệ số suy hao — x1/x10), tình trạng hiệu chuẩn, lịch và quyền sử dụng tại công ty, kết quả đo trên bo. Chưa có ảnh màn hình hay dữ liệu dạng sóng nào. **Dùng được cho:** đo Vds của Q1 (L3, `docs/design/LASER_CIRCUIT.md` mục 5) chính xác hơn đồng hồ vạn năng (xem dạng sóng, không chỉ trị trung bình); kiểm tín hiệu UART/GPIO của Nucleo khi cần. Không coi việc có máy là đã đo xong — chưa phép đo nào chạy | Ảnh máy/đầu dò khi dùng; kết quả đo đầu tiên gắn với phép thử cụ thể (ví dụ L3) |
| Kính bảo hộ, đồng hồ vạn năng, thước cặp, NEMA17, A4988, adapter 12 V | NGƯỜI DÙNG XÁC NHẬN 16/09 tối: CHƯA CÓ; đồng hồ và thước cặp mượn được cuối tuần. Chưa có tin mới tới 29/09 | Danh sách mua và mã linh kiện khi mua, xem `docs/HARDWARE_PREP.md` |
| Vật tư tuần 2–6 còn lại: hộp che, bàn cờ, cơ khí bàn xoay, nguồn, liên động | Sở hữu thực tế CHƯA XÁC NHẬN, chưa hỏi tới. Danh mục chi tiết theo tuần, thông số, cách kiểm khi nhận và câu hỏi ở `docs/HARDWARE_PREP.md` | Mã linh kiện thật, ảnh, thông số đo (điện áp, dòng laser) khi có; chuyển từng mục sang bảng này khi xác nhận |

## Bảng đối chiếu vật tư C6 — ghi nhận C6 Q5, 2026-10-07

Tổng hợp bằng chứng hiện biết cho mạch laser trên breadboard. Nguồn: bàn
giao C4 (`handoff/2026-09-21_c4-nucleo-laser-control/`), xác nhận người
dùng, và kế hoạch C6 Vòng 2 (`01_PLAN.md` mục 2). Không có phép đo mới
trong gói hồ sơ này.
(Bổ sung Vòng 4/5, 2026-10-07: các hàng cập nhật ngày 07/10 được bổ sung thêm bên dưới các dòng cơ sở, bảo đảm hồ sơ chỉ thêm theo quy định).

| Thành phần | Bằng chứng hiện có | Nguồn/đường dẫn | Còn thiếu để mở Q8/Q9 |
| --- | --- | --- | --- |
| Nucleo PA8/D7 (LASER_CTRL) | C4 đã kiểm không tải: VOM 3,3 V khi ON, 0 V khi OFF; 12/12 output T5 trên bo; nhãn D7 đối chiếu UM1724 + ảnh bo | `handoff/2026-09-21_c4-nucleo-laser-control/03_TEST.md`; `docs/logs/nucleo-board-2026-09-16.jpg` | Chưa nối tải thật; R08 C4 (xung ngắn khi reset) còn Góp ý |
| Nucleo PA9/D8 (SENSE_PWR) | C4 đã kiểm: cấu hình input NOPULL (không pull); để hở chân thả nổi đọc lẫn 0 và 1; mạch thật cần R4 15 kΩ kéo xuống để tránh đọc sai trạng thái cửa đóng khi hở mạch | bàn giao C4 (03_TEST.md) | Chưa nối mạch chia áp R3/R4 thực |
| Nucleo PC7/D9 (SENSE_ESTOP) | C4 đã kiểm pull-up nội, input OK | bàn giao C4 | Chưa nối estop thực |
| Laser SYD1230 ×2 | Nhãn 5 mW/650 nm, Class IIIa, 2 dây, 3–5 V, <40 mA (người bán) | `docs/logs/laser-syd1230-nhan-2026-09-22.jpg`; xác nhận 22/09 | Driver hạn dòng CHƯA XÁC NHẬN; dòng danh định CHƯA CÓ; chưa đo thực |
| MOSFET IRFZ44N | Mã `258X 77 WS`, LỆCH yêu cầu B2 (IRLZ44N logic-level) | Xác nhận 29/09; `docs/design/LASER_CIRCUIT.md` mục 0c | Vds CHƯA ĐO; quyết định giữ/đổi Q1 CHƯA CHỐT |
| MOSFET AO3400 (A09T) — thay thế theo D046 | Mã thân `A09T` (người dùng cung cấp 07/10), SOT-23 rời; đã chọn theo D046 thay IRFZ44N; Rds(on) ≤ 52 mΩ @ 2,5 V, Id danh định 5,8 A (TA=25°C, VGS=10V theo datasheet AOS Rev 8) | Xác nhận 07/10; D046; D047; datasheet AOS AO3400 Rev 8 | Cần đo kiểm nhận adapter Bước 2a không cấp nguồn; Vds (L3) chưa đo |
| Adapter AO3400 tự làm | NGƯỜI DÙNG XÁC NHẬN 07/10: đã tự làm adapter từ phíp đồng cắt rãnh, hàn 3 dây Dupont đực (ảnh `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`, `docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png`) | Xác nhận 07/10 | Cần hoàn thành đo kiểm nhận Bước 2a không cấp nguồn trước khi cắm breadboard |
| R1 100 Ω 1/4 W | ĐÃ NHẬN 29/09, khớp yêu cầu | Xác nhận 29/09 | Số lượng CHƯA XÁC NHẬN |
| R2/R3 10 kΩ | NGƯỜI DÙNG XÁC NHẬN 07/10: có | Xác nhận 07/10 | Số lượng/dung sai chưa đối chiếu cho hai vị trí |
| R4 15 kΩ | NGƯỜI DÙNG XÁC NHẬN 07/10: có | Xác nhận 07/10 | Giá trị/dung sai chưa đối chiếu |
| C1 100 nF | NGƯỜI DÙNG XÁC NHẬN 07/10: có | Xác nhận 07/10 | Chưa kiểm loại/điện áp |
| Hộp che | NGƯỜI DÙNG XÁC NHẬN 07/10: có hộp che | Xác nhận 07/10 | Độ kín/chặn tia CHƯA KIỂM; vật liệu/kích thước chưa ghi |
| Kính bảo hộ | NGƯỜI DÙNG XÁC NHẬN 07/10: có kính bảo hộ | Xác nhận 07/10 | Dải bước sóng/thông số bảo vệ CHƯA KIỂM |
| Đồng hồ vạn năng | NGƯỜI DÙNG XÁC NHẬN 07/10: có; C4 có xác nhận VOM và ảnh phép thử không tải | Xác nhận 07/10; bàn giao C4 | Mã máy/thang đo CHƯA GHI |
| Đồng hồ vạn năng — cập nhật 08/10 | NGƯỜI DÙNG XÁC NHẬN 08/10: máy chốt dùng cho C6 là máy mượn của người thân (nhận 10/10), model/thang đo chưa biết | Xác nhận 08/10 (Tester Vòng 5 lần 2) | Dừng phần đo ở Bước 2a cho tới khi nhận máy |
| Máy hiện sóng GDS-1102B | NGƯỜI DÙNG XÁC NHẬN 02/10: có thể mượn | `docs/HARDWARE.md` dòng GDS-1102B bảng thiết bị | Quyền mượn/đầu dò/hiệu chuẩn CHƯA XÁC NHẬN |
| SW1 (cửa NC) | CHƯA XÁC NHẬN | — | Cần có trước Q8/Q9 |
| SW1 (cửa NC) — cập nhật 07/10 | CHƯA CÓ (NGƯỜI DÙNG XÁC NHẬN 07/10: chưa có cả 2); đề xuất tạm KW11 cơ khí để thử gá không điện, chính thức Omron SS-01GL tuần sau | Xác nhận 07/10 | Cần có trước Q8/Q9 |
| SW2 (estop hai NC) | CHƯA XÁC NHẬN | — | Cần có trước Q8/Q9 |
| SW2 (estop hai NC) — cập nhật 07/10 | CHƯA CÓ (NGƯỜI DÙNG XÁC NHẬN 07/10: chưa có cả 2); nút dừng khẩn cấp 2 cặp tiếp điểm NC | Xác nhận 07/10 | Cần có trước Q8/Q9 |
| Tải giả C6 (Rtest) | Điện trở 120 Ω ±5% ≥ 1 W (ĐỀ XUẤT thiết kế Vòng 4, tính toán 5,25 V / 114 Ω cho I ≈ 46,05 mA, P ≈ 0,242 W) | Kế hoạch Vòng 4; `LASER_CIRCUIT.md` mục 5 | CHƯA CÓ / CHƯA XÁC NHẬN |
| Nguồn 5 V laser | Lấy từ chân 5V USB Nucleo (JP5=U5V); giới hạn dòng bo+tải theo UM1724 (300 mA JP1 OFF, 100 mA JP1 ON) | Xác nhận 07/10; ST UM1724 | Vị trí JP1/JP5 chưa kiểm; nguồn thử độc lập CHƯA CÓ |
| F1 polyfuse 100 mA | CHƯA XÁC NHẬN | — | Tuỳ chọn breadboard, bắt buộc PCB |
| Breadboard/jumper | NGƯỜI DÙNG XÁC NHẬN 16/09: có | Xác nhận 16/09 | — |

### Cập nhật vật tư 08/10/2026 — xác nhận người dùng

Nguồn: hai mục nhật ký Planner ngày 08/10/2026 trong `docs/SESSION_LOG.md` ("bổ sung danh sách linh kiện đã mua theo người dùng" và "phân biệt adapter chân AO3400 và adapter nguồn 12 V"). Cập nhật sở hữu theo lời người dùng báo; chưa kiểm đếm/đo trên hiện vật, chưa thử tải, chưa mở các chặng phần cứng Q8/Q9/motor.

| Linh kiện / Vật tư | Số lượng | Trạng thái người dùng xác nhận | Đối chiếu vị trí | Phần chưa kiểm chứng |
| --- | --- | --- | --- | --- |
| Công tắc hành trình KW11 | 5 cái | ĐÃ MUA (08/10); ảnh chat có cần gạt con lăn, 3 chân | Ứng viên HOME (D17) và SW1 C6 (B13); dùng chung lô 5 cái, chưa phân bổ | Mã biến thể, COM/NC/NO, hành vi tiếp điểm và cơ cấu gá chưa kiểm/đo; KW11 chỉ là thử gá cơ khí tạm, chưa đạt liên động an toàn SW1/SW2 |
| MOSFET AO3400 SOT-23 rời | 18 cái | ĐÃ MUA (08/10) | Q1 C6 (B2); kế thừa lựa chọn D046/D047 | Chưa kiểm đếm/đo từng chiếc; ghi đúng 18 chiếc rời (không cộng chiếc trên bo chuyển thành 19, không coi là mua thêm); chưa đo Vds (L3) |
| Puly răng GT2 20 răng, lỗ trục 5 mm | 1 cái | ĐÃ MUA (08/10) | D3 / BOM C02 (bàn xoay) | Số răng, chuẩn GT2, đường kính lỗ theo người dùng, chưa đếm/đo thực tế; bề rộng đai phù hợp chưa xác nhận |
| Puly răng GT2 60 răng, lỗ trục 8 mm | 1 cái | ĐÃ MUA (08/10) | D4 / BOM C03 (bàn xoay) | Số răng, chuẩn GT2, đường kính lỗ theo người dùng, chưa đếm/đo thực tế; bề rộng đai phù hợp chưa xác nhận |
| Module A4988 + tản nhiệt | 1 bộ | ĐÃ MUA (08/10); ảnh chat bo đỏ có chữ A4988, tản nhiệt rời | D2 / BOM A05 (driver động cơ) | Chưa xác minh IC/điện trở sense, chưa chỉnh giới hạn dòng Vref, chưa thử với động cơ; chặng motor chưa mở |
| Adapter nguồn 12 V–3 A, đầu cắm 5,5 × 2,1 mm | 1 bộ | ĐÃ ĐẶT — CHỜ NHẬN (08/10) | D9 / BOM B01 (nguồn chính hệ thống) | Chưa nhận hàng; chưa xác nhận cực tính đầu cắm, nhãn/nhà sản xuất, điện áp thực tế hoặc khả năng cấp tải; phân biệt với bo chuyển chân AO3400 tự làm |

### Cập nhật vật tư 10/10/2026 — xác nhận người dùng

Nguồn: lời báo và hai ảnh của người dùng ngày 10/10/2026, lưu tại
`docs/logs/buck-xl4005-mat-tren-2026-10-10.jpg` và
`docs/logs/buck-xl4005-mat-sau-2026-10-10.jpg` (bản thu nhỏ 1500×2000 từ ảnh gốc
3024×4032, đã áp hướng xoay EXIF). Ghi bởi phiên Điều phối theo ngoại lệ người dùng
cho phép (D063). Chưa kiểm đếm hay đo trên hiện vật.

| Linh kiện / Vật tư | Số lượng | Trạng thái người dùng xác nhận | Đối chiếu vị trí | Phần chưa kiểm chứng |
| --- | --- | --- | --- | --- |
| Mạch hạ áp DC–DC (buck) XL4005 | 1 cái | ĐÃ NHẬN (10/10); ảnh hai mặt | D10 / mô tả mục 5 (buck 5 V cho camera S3): **ứng viên**, chưa phân bổ. ĐỌC TỪ ẢNH: IC ghi `XLSEMI XL4005E1 82412` (5 chân); hai tụ điện phân `220 35V VT` (một ở phía vào, một ở phía ra); diode dán ghi `SS54`; cuộn cảm toroid lõi vàng; biến trở núm vặn ghi `W103`/`103`; lụa in bốn điểm hàn `IN+`, `IN−`, `OUT+`, `OUT−`; mặt sau in `4005 DC-DC` và mũi tên từ cạnh IN sang cạnh OUT; hai lỗ bắt vít | Dải điện áp vào/ra, dòng tối đa, tần số chỉ theo datasheet hoặc người bán, chưa đo. Điện áp ra khi chưa chỉnh biến trở chưa biết. Hiệu suất, nhiệt, gợn chưa đo. Nhãn tụ 35 V chỉ gợi ý điện áp vào thực tế phải thấp hơn 35 V, không phải thông số của mạch. Mã `103` theo quy ước thường là 10 kΩ, chưa đo. Đây là mạch **hạ áp**: điện áp ra luôn thấp hơn điện áp vào, không tạo được 5 V từ nguồn 5 V. **Phải chỉnh biến trở và đo bằng VOM trước khi nối bất kỳ tải nào** (camera S3 cần 4,75–5,25 V theo `SPEC` §12) |
| Nguồn DC 5 V – 2 A (loại đầu cắm chưa rõ) | 1 bộ | NGƯỜI DÙNG BÁO CÓ SẴN (10/10); thông số "5 V 2 A" theo lời người dùng | Dùng **tạm** cấp 5 V cho laser ở C6 Q8 thay cho chân `5V` Nucleo, theo phương án "nguồn 5 V riêng, nối chung GND" của `docs/design/LASER_CIRCUIT.md` §4 (D063) | Chưa có ảnh hoặc nhãn; chưa xác nhận đầu cắm, cực tính, điện áp thực không tải và có tải, gợn; chưa đo bằng VOM. **Không nối vào chân `5V` của Nucleo** (LASER_CIRCUIT §4: tránh dòng nạp ngược). Dòng sự cố của nguồn 2 A cao hơn nhiều ngân sách USB 300 mA; module laser có hạn dòng hay không chưa xác nhận |
| Adapter nguồn 12 V–3 A, đầu cắm 5,5 × 2,1 mm | 1 bộ | VẪN CHỜ NHẬN; người dùng dự kiến nhận sau 1–2 ngày kể từ 10/10 | D9 / BOM B01 (xem dòng 08/10 ở trên) | Như dòng 08/10. Không còn là điều kiện của p01: laser dùng tạm nguồn 5 V 2 A (D063). Vẫn cần cho motor/PCB (p11, p13) và đầu vào của mạch XL4005 |

### Cập nhật 10/10/2026 (tối) — mạch bên trong module laser SYD1230

Nguồn: hai ảnh cận cảnh người dùng gửi tối 10/10/2026, lưu nguyên bản (PNG 685×913, không xử lý) tại
`docs/logs/laser-syd1230-mach-trong-mat-a-2026-10-10.png` (mặt có điện trở `01Y`, `362` và tụ gốm) và
`docs/logs/laser-syd1230-mach-trong-mat-b-2026-10-10.png` (mặt có điện trở `39B`). Ảnh toàn cảnh
(4032×3024) chưa lưu vào repo. Ghi bởi phiên Điều phối theo ngoại lệ người dùng cho phép (D065). Mọi mục dưới là
**ĐỌC TỪ ẢNH hoặc theo lời người dùng**; chưa đo gì, chưa tra datasheet đúng hãng.

| Hạng mục | Quan sát | Phần chưa kiểm chứng |
| --- | --- | --- |
| Bo mạch | Bo nhỏ màu xanh, có linh kiện cả hai mặt; hai dây (đỏ, đen) hàn vào bo; hai chân mạ vàng nhô ra, đi qua mặt bích mạ vàng sang đầu kim loại có ren. Trong ảnh bo nằm **rời** đầu kim loại: người dùng đã tháo module | Ý nghĩa hai chân (anode/cathode của diode laser?), hướng chân đúng khi lắp lại, và tiêu cự/cơ khí đầu laser sau khi tháo chưa kiểm |
| Hai linh kiện SOT-23 ba chân | Một cái mỗi mặt bo. Người dùng đọc mã trên thân cả hai là `1AM`; ảnh cận chỉ đọc được phần mã trên mặt B | Theo datasheet nhiều hãng (MDD, ZRE, High Diode, JUXING…), `1AM` thường là **MMBT3904**: NPN, 40 V, 200 mA, chân 1=B, 2=E, 3=C. Bảng mã dán không phổ quát: chưa tra datasheet đúng hãng, chưa đo |
| Điện trở dán | Mã đọc từ ảnh: `01Y` (mặt A), `362` (mặt A), `39B` (mặt B, có thể là `398`) | Chưa giải mã, chưa đo; trị và vai trò trong mạch chưa biết |
| Tụ dán | Một tụ màu be (kiểu gốm) ở mặt A, không đọc được mã | Trị và điện áp chưa biết |
| Kết luận cho hồ sơ | Module có **mạch điều khiển trên bo** (transistor, điện trở, tụ), không phải diode laser trần | Điều này **không** chứng minh có hạn dòng, cũng không cho biết trị hạn. Giả thuyết "có mạch hạn dòng bên trong" ở `docs/design/LASER_CIRCUIT.md` §1 vẫn **CHƯA XÁC NHẬN**. Không đo thông mạch hay diode khi bo còn nối với diode laser (quy trình C6) |

### Cập nhật vật tư 11/10/2026 — xác nhận người dùng

Nguồn: lời người dùng ngày 11/10/2026 kèm năm ảnh (động cơ ba ảnh, hai bó điện trở), nay lưu thu nhỏ (1500×2000, đã áp EXIF; nguyên bản 3024×4032 không lưu) tại
`docs/logs/nema17-42hd3401s-{nhan,mat-bich,dau-noi}-2026-10-11.jpg`, `docs/logs/tro-2w-120r-2026-10-11.jpg`, `docs/logs/tro-quarterw-15k-2026-10-11.jpg`
(người dùng cho phép 11/10). Ghi bởi phiên Điều phối theo ngoại lệ người dùng cho phép (D069). Số lượng và kích thước
là **theo lời người dùng**; nhãn là **ĐỌC TỪ ẢNH**; chưa đo gì.

| Linh kiện / Vật tư | Số lượng | Trạng thái người dùng xác nhận | Đối chiếu vị trí | Phần chưa kiểm chứng |
| --- | --- | --- | --- | --- |
| Động cơ bước NEMA17, 42 × 42 × 34 mm, trục 5 mm, có kèm dây 4P | 1 cái | ĐÃ CÓ (11/10); ảnh ba góc. ĐỌC TỪ ẢNH: nhãn `MODEL:42HD3401S-23B`, `1.8°DEG 2-PHASE`, `AFDE`, `LOT NO.260919`; trục có mặt phẳng cắt (D-flat); mặt bích nhôm có 4 lỗ bắt vít và đế tròn đen quanh trục; đầu nối trắng **6 chân** (đếm từ ảnh `...dau-noi...`) gắn trên thân | D1 / BOM C01 (NEMA17 cho bàn xoay B2). Chặn p11 trước đây; p04 không cần | Nhãn **không ghi dòng định mức** nên chưa có căn cứ đặt Vref A4988 (BOM gợi ý 0,6–0,9 A/pha chỉ là đề xuất): cần datasheet đúng model hoặc đo điện trở cuộn. Chưa đo điện trở cuộn, chưa xác định cặp dây A/B, chân nào của đầu nối 6 chân dùng với dây 4P, chiều dài dây; kích thước và đường kính trục chưa đo bằng thước cặp |
| Điện trở 2 W 120 Ω (thân to, nhiều vạch màu) | 10 cái | ĐÃ CÓ (11/10); ảnh một bó | B15 (tải giả C6, đề xuất 120 Ω ≥ 1 W, LASER_CIRCUIT §5): **đủ số lượng để dùng phương án lịch sử** nếu p01 đổi; **Người dùng quyết 11/10 dùng 1 trở này làm tải giả p01 thay cho 6 × 100 Ω 1/4 W (D070)** | Chưa giải mã vạch màu, chưa đo trị và dung sai; công suất 2 W theo lời người dùng, không đọc được từ thân. Cả 10 chiếc phải đo ở bước kiểm nhận (p01 chọn một chiếc) |
| Điện trở 1/4 W 15 kΩ | 50 cái | ĐÃ CÓ (11/10); ảnh một bó băng | B3: dòng 07/10 chỉ ghi "có 15 kΩ" không số lượng, nay là 50 | Chưa giải mã vạch, chưa đo trị/dung sai. Chưa có mạch nào trong hồ sơ cần 15 kΩ |

### Cập nhật vật tư 11/10/2026 (chiều) — adapter 12 V 3 A đã nhận

Nguồn: lời người dùng và một ảnh nhãn adapter ngày 11/10/2026. Ảnh nhãn lưu thu nhỏ (1500x1705, đã áp EXIF; nguyên bản 3024x3438 không lưu) tại `docs/logs/adapter-12v-3a-nhan-2026-10-11.jpg` (người dùng cho phép 11/10). Ghi bởi phiên Điều phối theo ngoại lệ người dùng cho phép (D072). Số lượng theo lời người dùng; nhãn là **ĐỌC TỪ ẢNH**; chưa đo gì.

| Linh kiện / Vật tư | Số lượng | Trạng thái người dùng xác nhận | Đối chiếu vị trí | Phần chưa kiểm chứng |
| --- | --- | --- | --- | --- |
| Adapter nguồn 12 V 3 A, đầu cắm 5,5 × 2,1 mm | 1 bộ | **ĐÃ NHẬN (11/10)**; thay các dòng "chờ nhận" ngày 08/10 và 10/10 ở trên. ĐỌC TỪ ẢNH: nhãn `AC/DC ADAPTOR`, `MODEL:1230`, `INPUT:AC100-240V 50/60Hz`, `OUTPUT:12V DC 3A`; ký hiệu cực tính trên nhãn là tâm dương (+) ở đầu cắm; dấu CE, FCC, RoHS, UKCA; phích cắm hai chân dẹt kiểu Mỹ; cáp có một lõi ferrite | D9 / BOM B01 (nguồn chính hệ thống: motor A4988, đầu vào của mạch buck XL4005 cho camera S3, PCB). Hết chặn p11/p13 về nguồn 12 V (hai việc vẫn bị chặn bởi vật tư và việc khác) | Chưa đo điện áp thực không tải và có tải, gợn, cực tính trên jack bằng VOM (VOM chưa về); nhãn tự khai, chưa có chứng nhận hay datasheet. Phích dẹt kiểu Mỹ so với ổ cắm đang dùng chưa kiểm. `MODEL:1230` là mã nhãn của adapter này, **không** liên quan module laser SYD1230. Chưa kiểm đầu cắm có khớp jack của A4988/PCB và mạch XL4005 (chưa nối) |

## Bảng nối dây — chỉ điền sau khi có bằng chứng

| Bo | Chân | Đi tới | Mức logic / nguồn | Nguồn xác nhận | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| Nucleo-F446RE | PA2 | USART2_TX → ST-LINK VCP (RX của ST-LINK), ra PC là `COM3` | 3,3 V, 115200 8N1 | CubeMX `loadboard NUCLEO-F446RE` gán; kiểm chức năng 16/09: PONG về PC qua COM3 | ĐÃ CHẠY, chưa đo bằng máy đo |
| Nucleo-F446RE | PA3 | USART2_RX ← ST-LINK VCP (TX của ST-LINK) | 3,3 V | như trên; PING từ PC tới được bo | ĐÃ CHẠY, chưa đo |
| Nucleo-F446RE | PA5 | LD2, LED xanh trên bo (chung chân với Arduino D13/SCK) | đầu ra 3,3 V, tải chỉ là LED trên bo | CubeMX gán; người dùng thấy LD2 nháy đều 16/09 | ĐÃ QUAN SÁT |
| Nucleo-F446RE | PC13 | B1 nút USER, xanh dương | vào, kéo lên trên bo | CubeMX gán; firmware chưa dùng | CHƯA THỬ |
| Nucleo-F446RE | các chân còn lại | Chưa nối gì | — | — | Chưa dùng; roadmap tuần 1 cấm cấp tải vào GPIO |

Không chuyển pinout của ESP32-CAM sang S3 hoặc suy ra từ một ảnh bo tương tự. Mỗi lần thay dây, lưu ảnh đủ thấy nhãn chân và cập nhật bảng này.

## Pinout bo ESP32-S3 WROOM CAM (N16R8) — đối chiếu 18/09

Nguồn: (1) sơ đồ chân do người bán "Linh Kiện Cầu Giấy" đăng kèm mặt hàng
"KIT ESP32-S3 N16R8 Camera board OV3660, OV5640", NGƯỜI DÙNG CUNG CẤP
18/09, đã lưu `docs/reference/esp32-s3-wroom-cam-pinout-nguoi-ban-2026-09-18.webp`
(WebP 1058×1058, đuôi gốc `.png` sai định dạng nên đổi, byte giữ nguyên);
(2) cấu hình đang chạy `CAMERA_MODEL_ESP32S3_EYE` trong
`firmware/esp32s3/CameraWebServerTest/camera_pins.h`, đã chụp 125 ảnh
16–17/09; (3) nhãn in cạnh header trên ảnh
`docs/logs/s3-board-front-2026-09-18.jpg` và ảnh cận trong chat. Ba nguồn
khớp nhau ở 14/14 chân camera và ở thứ tự nhãn header. Nhà sản xuất bo vẫn
không rõ; bố cục giống Freenove FNK0085 nhưng không cần giả thuyết này nữa
vì pinout đã có nguồn trực tiếp.

Header trái, từ trên xuống (nhìn mặt trước, camera ở trên):

| Nhãn | GPIO | Chức năng theo sơ đồ người bán | Firmware dùng |
| --- | --- | --- | --- |
| 3V3 | — | 3,3 V ra | |
| EN | — | RST | |
| 4 | GPIO4 | CAM_SIOD, ADC1_CH3, T4 | `SIOD_GPIO_NUM 4` |
| 5 | GPIO5 | CAM_SIOC, ADC1_CH4, T5 | `SIOC_GPIO_NUM 5` |
| 6 | GPIO6 | CAM_VSYNC, ADC1_CH5, T6 | `VSYNC_GPIO_NUM 6` |
| 7 | GPIO7 | CAM_HREF, ADC1_CH6, T7 | `HREF_GPIO_NUM 7` |
| 15 | GPIO15 | CAM_XCLK, ADC2_CH4, U0RTS | `XCLK_GPIO_NUM 15` |
| 16 | GPIO16 | CAM_Y9, ADC2_CH5, U0CTS | `Y9_GPIO_NUM 16` |
| 17 | GPIO17 | CAM_Y8, ADC2_CH6, U1TXD | `Y8_GPIO_NUM 17` |
| 18 | GPIO18 | CAM_Y7, ADC2_CH7, U1RXD | `Y7_GPIO_NUM 18` |
| 8 | GPIO8 | CAM_Y4, ADC1_CH7, T8 | `Y4_GPIO_NUM 8` |
| 3 | GPIO3 | JTAG EN, ADC1_CH2, T3 | |
| 46 | GPIO46 | LOG | |
| 9 | GPIO9 | CAM_Y3, ADC1_CH8, T9 | `Y3_GPIO_NUM 9` |
| 10 | GPIO10 | CAM_Y5, ADC1_CH9, T10 | `Y5_GPIO_NUM 10` |
| 11 | GPIO11 | CAM_Y2, ADC2_CH0, T11 | `Y2_GPIO_NUM 11` |
| 12 | GPIO12 | CAM_Y6, ADC2_CH1, T12 | `Y6_GPIO_NUM 12` |
| 13 | GPIO13 | CAM_PCLK, ADC2_CH2, T13 | `PCLK_GPIO_NUM 13` |
| 14 | GPIO14 | ADC2_CH3, T14 | |
| 5V | — | 5 V vào/ra từ USB | |

Header phải, từ trên xuống:

| Nhãn | GPIO | Chức năng theo sơ đồ người bán |
| --- | --- | --- |
| TX | GPIO43 | U0TXD, LED TX |
| RX | GPIO44 | U0RXD, LED RX |
| 1 | GPIO1 | ADC1_CH0, T1 |
| 2 | GPIO2 | ADC1_CH1, LED ON, T2 |
| 42 | GPIO42 | MTMS |
| 41 | GPIO41 | MTDI |
| 40 | GPIO40 | SD_DATA, MTDO |
| 39 | GPIO39 | SD_CLK, MTCK |
| 38 | GPIO38 | SD_CMD |
| 37 | GPIO37 | PSRAM (octal) — KHÔNG dùng |
| 36 | GPIO36 | PSRAM (octal) — KHÔNG dùng |
| 35 | GPIO35 | PSRAM (octal) — KHÔNG dùng |
| 0 | GPIO0 | Boot |
| 45 | GPIO45 | VSPI (strapping) |
| 48 | GPIO48 | WS2812 (LED RGB trên bo) |
| 47 | GPIO47 | — |
| 21 | GPIO21 | — |
| 20 | GPIO20 | USB_D−, ADC2_CH9, U1CTS |
| 19 | GPIO19 | USB_D+, ADC2_CH8, U1RTS |
| GND | — | GND |

Camera: `PWDN` và `RESET` không nối (`-1` trong firmware), khớp việc sơ đồ
không có chân nào ghi CAM_PWDN/CAM_RESET. Chân còn trống cho việc sau trên
S3 (chưa dùng, chưa thử): GPIO1, 14, 21, 41, 42, 47; GPIO3/45/46/0 là
chân strapping hoặc JTAG, tránh dùng. Laser và bàn xoay đi qua Nucleo theo
D001, không dùng chân S3.
