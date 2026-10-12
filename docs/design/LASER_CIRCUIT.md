# Mạch laser, liên động cửa và nút dừng — sơ đồ nguyên lý, bước Q5

> **Đính chính 2026-10-09 — D050:** người dùng xoá toàn bộ yêu cầu an toàn/liên động của `docs/SPEC.md` mục 9 (công tắc cửa SW1, nút dừng SW2, hộp kín, watchdog, giới hạn thời gian bật laser, kính bảo hộ như điều kiện cổng, MVS của D049). Các cổng/điểm dừng an toàn trong tệp này không còn chặn việc cấp nguồn laser hay chặng nào. Phần mạch MOSFET đóng ngắt laser vẫn là thiết kế chức năng. Nội dung dưới giữ nguyên làm lịch sử.

Ngày: 2026-09-20. Trạng thái: **ĐỀ XUẤT của phiên viết; chưa có linh
kiện, chưa đấu, chưa đo.** Đây là sản phẩm bước Q5 (`docs/PROCESS.md` R5)
cho mạch thử tuần 2 trên breadboard (C6) và là gốc cho sơ đồ PCB tuần 6.
Cơ sở: `docs/SPEC.md` mục 9 (an toàn, không nới) và 12 (mạch); vật tư
`docs/HARDWARE_PREP.md` nhóm B; chân theo `docs/HARDWARE.md`.

**Khác với bản phác trong `docs/HARDWARE_PREP.md` (16/09):** bản này có
công tắc cửa và nút dừng ngắt nguồn laser bằng phần cứng ngay ở mạch thử,
vì `SPEC` 9.3 và 9.7 đòi bảo vệ trước khi chạy tự động và C5 đã là chu
trình tự động; B5 "chưa cần công tắc cửa ở tuần 2" mâu thuẫn với `SPEC`
9.3 (review `REVIEW_2026-09-20_main_full.md` R01 cũng nêu). Mâu thuẫn này
ghi ở đây và `STATUS.md`; `HARDWARE_PREP.md` sửa khi xử lý review đó.

## 0b. Linh kiện thật đã nhận — 2026-09-22

Bổ sung khi người dùng nhận hàng; sơ đồ dưới đây **không đổi**, đây chỉ là
đối chiếu giả định với module thật.

| Giả định của sơ đồ | Module thật SYD1230 | Kết luận |
| --- | --- | --- |
| Laser cấp 5 V từ chân `5V` Nucleo (mục 4) | Nhãn/người bán: 3–5 V DC | **Khớp**, 5 V nằm trong dải |
| Dòng đủ nhỏ cho polyfuse 100 mA và chân `5V` | Người bán: < 40 mA (CHƯA ĐO) | **Khớp trên giấy**; đo lại khi đấu |
| Đóng ngắt phía âm bằng MOSFET (J1.1 `+`, J1.2 `−`) | 2 dây: đỏ và đen, không có dây điều khiển riêng | **Khớp**: bắt buộc cắt mạch ở đường nguồn, đúng như sơ đồ |
| Module có mạch hạn dòng bên trong | Người bán không xác định được; GIẢ THUYẾT: có, vì nhận dải 3–5 V | **Chưa xác nhận** — nếu hoá ra không có thì phải thêm điện trở hạn dòng trước khi cấp nguồn |

Nhãn thân ghi `Class IIIa` (ảnh `docs/logs/laser-syd1230-nhan-2026-09-22.jpg`),
tương đương Class 3R của IEC — vẫn là loại **tránh chiếu thẳng vào mắt**;
không dùng nhãn này để nới yêu cầu của `docs/SPEC.md` mục 9.

Chưa biết và cần trước khi tính góc đặt laser (mục 4, gá B8): **góc quạt**
của vạch, và **vành khía ở đầu phát có chỉnh được tiêu cự** hay không.

## 0c. MOSFET và điện trở thật đã nhận — 2026-09-29

NGƯỜI DÙNG CUNG CẤP: điện trở 100 Ω 1/4 W (khớp R1 mục 1, không có vấn đề)
và MOSFET mã in trên thân `IRFZ44N 258X 77 WS`.

**Đây không phải linh kiện B2 yêu cầu.** `IRFZ44N` khác `IRLZ44N`/`IRLZ34N`
đúng một chữ ("L" = logic-level) nhưng khác hẳn về đặc tính lái gate:

| | IRLZ44N/IRLZ34N (B2 yêu cầu) | IRFZ44N (đã nhận) |
| --- | --- | --- |
| Vgs(th) điển hình | ≤ 2 V (logic-level) | 2–4 V (chuẩn) |
| Rds(on) hãng công bố tại | 4 V, 5 V (và đôi khi thấp hơn) | thường chỉ 10 V |
| Dẫn bão hoà ở Vgs = 3,3 V (GPIO Nucleo) | nhiều khả năng, cần đo (R10) | KHÔNG BẢO ĐẢM — có thể còn ở vùng tuyến tính, Rds(on) cao hơn nhiều lần |

Dòng "nhiều khả năng dùng được" ở bảng Q1 mục 3 được viết cho IRLZ44N; **không
áp dụng thẳng cho IRFZ44N đã nhận**. `docs/HARDWARE_PREP.md` B2 đã cảnh báo
đúng điều này trước khi mua ("không phải IRFZ44N — cần 10 V mới mở hết");
việc mua lệch không đổi yêu cầu kỹ thuật.

**Không dùng để suy luận, chỉ đo mới biết:** phép đo L3 (mục 5, Vds ≤ 0,2 V
khi dẫn với tải laser thật) là bước quyết định duy nhất. Kết quả có thể là
(a) Vds đủ nhỏ dù ngoài datasheet — dùng tạm được cho dòng < 50 mA; hoặc
(b) Vds quá cao — đổi sang IRLZ44N/IRLZ34N thật, AO3400A, hoặc thêm tầng đệm
NPN lái gate bằng 5 V (đã liệt kê ở mục 3). Chưa đo thì chưa cấp nguồn qua
mạch này — vẫn nằm trong 6 điều kiện an toàn của
`docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md`.

## 0d. Lựa chọn AO3400 thay thế IRFZ44N — 2026-10-07 (D046, đính chính D047)

NGƯỜI DÙNG XÁC NHẬN 07/10: chọn **AO3400**, mã in trên thân `A09T`, dạng SOT-23 rời thay cho IRFZ44N; nguồn hiện dùng là USB Nucleo. Người dùng đã tự làm adapter chân cắm từ mảnh phíp đồng cắt rãnh, hàn 3 dây Dupont đực (ảnh `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`, `docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png`).

Căn cứ kỹ thuật đã đối chiếu ([AOS AO3400 datasheet Rev 8, trang 1–2](https://www.aosmd.com/pdfs/datasheet/AO3400.pdf)):
- MOSFET kênh N, đóng gói SOT-23, dòng xả cực đại danh định Id = 5,8 A (tại TA = 25 °C, VGS = 10 V theo datasheet AOS AO3400 Rev 8; không gán định mức 5,8 A này cho adapter tự làm ở điện áp điều khiển 3,3 V), điện áp Vds tối đa 30 V.
- **Rds(on) tối đa 52 mΩ tại Vgs = 2,5 V** (và 33 mΩ tại Vgs = 4,5 V). Theo datasheet AOS AO3400 chính hãng, Vgs = 2,5 V đã bảo đảm Rds(on) ≤ 52 mΩ, giải quyết xung đột logic-level với `docs/SPEC.md` mục 9/12 về mặt lý thuyết; hiện vật A09T trên adapter tự làm cần đo thực tế Vds dưới tải để nghiệm thu chỉ tiêu L3.
- Không nhầm lẫn thông số 52 mΩ của AO3400 với thông số 48 mΩ của **AO3400A** (linh kiện khác trong BOM A06 lịch sử).
- Chuỗi ký tự `A09T` trên thân là thông tin do người dùng cung cấp; chưa phải chứng nhận chính hãng từ nhà sản xuất, chưa đo đạc linh kiện thực tế.

Đóng gói SOT-23 và kết nối breadboard:
- AO3400 là linh kiện dán bề mặt (SMD) SOT-23 rời: người dùng đã tự làm adapter phíp đồng cắt rãnh ra 3 đầu dây Dupont đực để cắm breadboard.
- Sơ đồ chân SOT-23 theo datasheet AOS AO3400 Rev 8: **Pin 1 = Gate (G), Pin 2 = Source (S), Pin 3 = Drain (D)** (khi nhìn từ mặt trên có chữ A09T đọc xuôi chiều, cạnh có 2 chân ở dưới: chân trái là 1 (G), chân phải là 2 (S), cạnh đối diện có 1 chân là 3 (D)).
- Ánh xạ chân MOSFET ↔ đảo đồng ↔ màu dây jumper ↔ đầu cắm Dupont là GIẢ THUYẾT cần đo kiểm nhận không cấp nguồn ở Bước 2a trước khi cắm breadboard.
- **CẢNH BÁO SƠ ĐỒ CHÂN:** Tuyệt đối không sao chép thứ tự chân TO-220 của IRFZ44N (nhìn từ trước: Pin 1 = G, Pin 2 = D, Pin 3 = S) cho SOT-23 của AO3400. Phải hoàn thành đo kiểm nhận Bước 2a không cấp nguồn trước khi cắm breadboard; chưa kiểm nhận thì giữ CHƯA XÁC NHẬN và chặn đấu mạch.

## 1. Sơ đồ nguyên lý (văn bản)

```
                 5V_NUCLEO (chân 5V, CN7; nguồn từ USB ST-LINK, xem mục 4)
                     │
                    F1  polyfuse 100 mA (tuỳ chọn ở breadboard, bắt buộc trên PCB)
                     │
                 SW1 ─┤  công tắc cửa, tiếp điểm NC, cửa ĐÓNG = kín
                     │
                 SW2 ─┤  nút dừng, tiếp điểm NC, KHÔNG nhấn = kín
                     │
                     ├──────────────┐
                     │              R3 10 kΩ
                 V_LASER_PWR        ├──────── SENSE_PWR → Nucleo GPIO_IN (mục 2)
                     │              R4 15 kΩ
                    C1 100 nF       │
                     │             GND
                 J1.1 laser (+) / tải giả Rtest
                 J1.2 laser (−) / tải giả Rtest
                     │
                 Q1.D (Pin 3) ┐
   LASER_CTRL ──R1 100 Ω────── Q1.G (Pin 1)  Q1 AO3400 MOSFET N logic-level SOT-23 (mục 0d, 2, 3)
   (Nucleo GPIO_OUT)  │        │             (bo chuyển chân AO3400 tự làm, chờ kiểm Bước 2a)
                     R2 10 kΩ  │
                      │       Q1.S (Pin 2)
                     GND ──── GND chung với Nucleo

   SW2.2 (tiếp điểm NC thứ hai của nút dừng) ── SENSE_ESTOP → Nucleo GPIO_IN, pull-up nội
   SW2.2 đầu kia ── GND
```

Nguyên lý: laser chỉ nhận điện khi **cửa đóng VÀ nút dừng không nhấn VÀ**
Q1 dẫn. Hai điều kiện đầu là phần cứng, không qua firmware (`SPEC` 9.3,
9.4). R2 kéo gate xuống nên Q1 tắt khi Nucleo reset, chân ở trở kháng cao
lúc khởi động, hoặc rút dây tín hiệu (`SPEC` 9.1). `SENSE_PWR` cho firmware
biết laser đang có nguồn hay không; `SENSE_ESTOP` tách riêng nút dừng để
phân biệt "cửa mở" với "nút dừng" (`SPEC` 12: "công tắc cửa ngắt nguồn
laser và báo trạng thái riêng").

## 2. Danh sách linh kiện và chân

| Ký hiệu | Linh kiện | Giá trị / mã | Ghi chú |
| --- | --- | --- | --- |
| Q1 | MOSFET kênh N logic-level, SOT-23 | **AO3400 (mã thân A09T theo người dùng) đã chọn theo D046 (07/10, đính chính D047)** | Datasheet AOS AO3400 Rev 8 cho Rds(on) ≤ 52 mΩ tại Vgs = 2,5 V; dòng Id danh định 5,8 A (TA = 25 °C, VGS = 10 V); mở ở mức 3,3 V GPIO Nucleo, giải quyết xung đột logic-level với `docs/SPEC.md` mục 9/12 (không lẫn với AO3400A 48 mΩ). Sơ đồ chân SOT-23: Pin 1 = Gate, Pin 2 = Source, Pin 3 = Drain (tuyệt đối không dùng thứ tự TO-220 1:G, 2:D, 3:S). Người dùng đã tự làm bo chuyển chân phíp đồng cắt rãnh ra 3 dây Dupont đực, cần kiểm nhận Bước 2a không cấp nguồn trước khi cắm breadboard. NGƯỜI DÙNG XÁC NHẬN 08/10: **ĐÃ MUA 18 cái AO3400 SOT-23 rời** (không tính chiếc trên bo chuyển thành 19, không coi là mua thêm 18; chưa kiểm đếm/đo từng chiếc); mã in A09T ghi nhận trên chiếc đã hàn bo chuyển tự làm. Lưu IRFZ44N 258X 77 WS đã nhận ngày 29/09 lệch với yêu cầu IRLZ44N làm lịch sử linh kiện |
| R1 | Điện trở gate | 100 Ω, 1/4 W | Hạn dòng nạp gate từ GPIO; ĐÃ NHẬN 29/09 |
| R2 | Kéo gate xuống | 10 kΩ, 1/4 W | Bắt buộc, `SPEC` 9.1; NGƯỜI DÙNG XÁC NHẬN 07/10: có |
| R3, R4 | Chia áp SENSE_PWR | 10 kΩ, 15 kΩ | 5 V × 15/25 = 3,0 V vào GPIO; PA9/PC7 là chân FT (chịu 5 V) nhưng vẫn chia để không phụ thuộc; NGƯỜI DÙNG XÁC NHẬN 07/10: có |
| C1 | Tụ gốm sát laser | 100 nF | Lọc; `SPEC` 12; NGƯỜI DÙNG XÁC NHẬN 07/10: có |
| F1 | Polyfuse | 100 mA (tuỳ chọn breadboard) | Bảo vệ chân 5V Nucleo nếu laser chập; bắt buộc trên PCB tuần 6 |
| SW1 | Công tắc cửa | Microswitch có tiếp điểm NC | **Lịch sử 07/10: CHƯA CÓ** (chưa có cả 2); **NGƯỜI DÙNG XÁC NHẬN 08/10: ĐÃ MUA 5 cái KW11** (dùng chung thông tin lô 5 cái với D17 HOME, chưa phân bổ riêng; ảnh chat có cần gạt con lăn, 3 chân; chưa kiểm mã biến thể/chân/tiếp điểm/gá), chỉ là ứng viên thử gá cơ khí tạm, **CHƯA ĐẠT liên động an toàn SW1** theo `docs/SPEC.md` mục 9.3. Ứng viên chính thức: Omron SS-01GL (tuần sau mới có). Đề xuất tạm: KW11 cơ khí (SPDT COM/NO/NC, lkcg.vn) chỉ dùng để thử gá cơ khí không cấp điện và đưa vào thiết kế thử tải giả, laser tháo khỏi mạch. Yêu cầu chức năng: cửa đóng kín mạch, cửa hé ngắt mạch laser; không mặc định cửa đóng đè cần thì COM–NC kín (với công tắc vi động SPDT, đè cần thì COM–NC ngắt và COM–NO kín; trạng thái tiếp điểm thực tế của cơ cấu gá CHƯA XÁC NHẬN, bắt buộc đo thông mạch ở hai trạng thái cửa trước khi nối dây); không coi KW11 là SW1 chính thức. Khi thay sang Omron SS-01GL phải kiểm lại chân, gá, hành trình và phép thử liên động |
| SW2 | Nút dừng khẩn cấp | Nút nhấn NC **có hai cặp tiếp điểm NC** (hoặc hai nút ghép cơ khí); BOM A09 | **CHƯA CÓ (NGƯỜI DÙNG XÁC NHẬN 07/10: chưa có cả 2)**. Một cặp cắt đường nguồn V_LASER_PWR bằng phần cứng, một cặp báo `SENSE_ESTOP` về Nucleo PC7. Bắt buộc có trước mạch có điện |
| J1 | Đầu nối tải | 2 chân, kẹp cá sấu ở breadboard | Laser SYD1230 thật (khi nghiệm thu), hoặc điện trở tải giả Rtest 120 Ω ±5% ≥ 1 W (khi thử nghiệm không phát tia) |

Chân Nucleo — **ĐỀ XUẤT theo UM1724, phải đối chiếu nhãn in trên bo trước
khi cắm** (`docs/HARDWARE.md`); tránh PA2/PA3 (USART2), PA5 (LD2), PC13
(B1), PB3/PA13/PA14 (debug):

| Tín hiệu | Chân | Nhãn Arduino | Cấu hình |
| --- | --- | --- | --- |
| `LASER_CTRL` | PA8 | D7 (CN9) | Output push-pull, mặc định thấp; **đặt mức thấp trước khi bật clock các ngoại vi khác** |
| `SENSE_PWR` | PA9 | D8 (CN9) | Input, không pull; cao = laser có nguồn |
| `SENSE_ESTOP` | PC7 | D9 (CN9) | Input, pull-up nội; thấp = không nhấn (NC kín), cao = nhấn |
| GND | GND (CN7/CN6) | GND | Chung |
| 5V_NUCLEO | 5V (CN7) | 5V | Xem mục 4 |

Firmware suy ra `door`: `SENSE_PWR = 0` và `SENSE_ESTOP = thấp` → cửa mở;
`SENSE_ESTOP = cao` → estop (cửa không biết). Đủ cho FSM
`docs/design/NUCLEO_PROTOCOL.md` mục 4.

## 3. Điều kiện chọn Q1 — chỉ tiêu đo, không suy từ tên linh kiện

- Với Vgs = 3,3 V (đo tại gate khi `LASER_CTRL` cao) và tải laser thật (hoặc tải giả thử nghiệm):
  **Vds ≤ 0,2 V**; nếu không đạt thì đổi linh kiện, không chỉnh ngưỡng.
- Với Vgs = 0 V (GPIO thả nổi, R2 kéo): I_laser = 0, đo bằng đồng hồ mA.

**Xử lý xung đột SPEC/Q5 (chốt theo D046 ngày 07/10):**
`docs/SPEC.md` mục 9/12 yêu cầu MOSFET logic-level 3,3 V. Xung đột giữa việc IRFZ44N không đảm bảo logic-level và yêu cầu SPEC đã được giải quyết ở khâu thiết kế bằng Quyết định D046: chọn **AO3400** (Rds(on) ≤ 52 mΩ tại Vgs = 2,5 V theo datasheet AOS AO3400 Rev 8) làm linh kiện chính thức, lưu IRFZ44N làm lịch sử. Tiêu chí nghiệm thu Vds ≤ 0,2 V (L3) vẫn giữ nguyên không nới lỏng khi nghiệm thu có tải thật.

## 4. Nguồn 5 V cho laser ở tuần 2

Cấu hình hiện có: lấy từ chân `5V` của Nucleo (JP5 = U5V, nguồn từ cổng USB ST-LINK) theo xác nhận người dùng ngày 07/10.

**Phân tích giới hạn nguồn USB theo ST UM1724 Rev 17 (mục 7.5.1 và 7.5.4):**
- Giới hạn dòng nguồn USB: Tổng dòng tiêu thụ của bo Nucleo cộng với toàn bộ tải phụ gắn ngoài phụ thuộc cấu hình jumper JP1 và kết quả enumeration với host PC:
  + Cấu hình **JP1 = OFF**: Sau khi enumeration thành công với host PC, tổng dòng cấp cho bo và tải ngoài tối đa **300 mA khi JP1 = OFF**. Trường hợp host PC từ chối yêu cầu 300 mA hoặc khi chưa/không enumeration thành công: theo ST UM1724 Rev 17 mục 7.5.1, phần MCU cùng bo mở rộng hoàn toàn không được cấp nguồn và LED đỏ LD3 tắt (nguồn chân 5V không được mở cấp ra ngoài); khi đó **chưa có nguồn cho MCU/tải, dừng phép thử**, tuyệt đối không suy đoán có chế độ cấp 100 mA khả dụng tại chân 5V cho MCU và tải.
  + Cấu hình **JP1 = ON**: Giới hạn ngân sách dòng điện cố định tối đa **100 mA khi JP1 = ON** cho toàn bo Nucleo (bao gồm MCU) và tải phụ gắn ngoài.
- Ngân sách dòng: MCU STM32F446RE, ST-LINK và các linh kiện trên bo Nucleo tiêu thụ một phần dòng nền; do đó phần dòng còn dư trên chân 5V không phải là 300 mA trọn vẹn dành riêng cho laser. Cần đối chiếu vị trí thực tế của jumper JP1 và JP5 trên bo.
- Module laser SYD1230 dự kiến tiêu thụ < 40 mA (nhà bán khai, chưa đo) hoặc < 50 mA (ngưỡng an toàn B7). Nếu đo thấy 5V_NUCLEO < 4,75 V khi tải bật → chuyển sang nguồn sạc 5 V riêng, nối chung GND với Nucleo.
- **CẢNH BÁO AN TOÀN NGUỒN:** Tuyệt đối không nối song song nguồn 5 V ngoài với chân 5V USB Nucleo để tránh dòng nạp ngược (backfeed) gây hỏng ST-LINK hoặc cổng USB của PC. Nguồn thử liên động độc lập (nếu dùng) phải cách ly hoàn toàn cả đường nguồn lẫn tín hiệu khỏi Nucleo khi bo không cấp điện. Trên PCB tuần 6: dùng buck 5 V riêng theo `SPEC` 12.

## 5. Phép đo nghiệm thu mạch thử (Q9 của C6), khai báo trước

Ghi theo `docs/TEST_TEMPLATE.md`, mỗi đại lượng ≥ 3 lần, có ảnh mạch.

| # | Phép đo | Ngưỡng | Ghi chú |
| --- | --- | --- | --- |
| L1 | V tại J1 khi bật | 4,75–5,25 V | `SPEC` 12 |
| L2 | I laser khi bật | < 50 mA (cổng B7); nguồn chỉ cho cận trên < 40 mA (người bán), CHƯA CÓ trị danh định → chưa áp dụng ±20%; cần Q2 chốt dòng danh định trước nghiệm thu L2 đầy đủ | Đồng hồ mA nối tiếp |
| L3 | Vds của Q1 khi bật | ≤ 0,2 V | mục 3 |
| L4 | Mở cửa khi laser đang bật | 10/10 lần laser tắt, kể cả **Nucleo không cấp nguồn** (cấp laser từ nguồn riêng cho ca này) | `SPEC` 9.3 |
| L5 | Nhấn nút dừng khi laser đang bật | 10/10 lần laser tắt; `SENSE_ESTOP` đổi mức | `SPEC` 9.4 |
| L6 | Reset Nucleo (nút B2/RESET, ĐÃ KIỂM quy trình C4; B1 là USER/PC13 không phải RESET) 10 lần khi cửa đóng | Laser không loé quan sát bằng đồng hồ hoặc LED thử; GHI CHÚ: VOM/LED không loại trừ xung ngắn dưới thời gian lấy mẫu, R08 C4 còn mở; khảo sát xung reset cần máy hiện sóng oscilloscope | `SPEC` 9.3 |
| L7 | Rút dây `LASER_CTRL` khi laser đang bật | Laser tắt ngay | R2 |
| L8 | Mất liên lạc: im lặng > 3000 ms (`T_hb`, không HEARTBEAT) khi đang CAPTURING → ERROR LINK_LOST, laser tắt; riêng: HEARTBEAT đều nhưng không có LASER ON mới → hết `T_laser_max = 5000 ms` → IDLE, `last_err = LASER_TIMEOUT`, laser tắt. Hai kích thích khác nhau theo D038 | 10/10 lần laser tắt mỗi ca | `NUCLEO_PROTOCOL` mục 4–5; D038 |

**Trình tự 4 giai đoạn loại bỏ phụ thuộc vòng (giải quyết TX11):**
1. **Giai đoạn 1 — Tiền kiểm trước cấp điện (không cấp điện):** Kiểm tra ngoại quan, cực tính nguồn, ngân sách dòng nguồn USB, không nối tắt; kiểm tra chân SOT-23 qua adapter (Pin 1=G, 2=S, 3=D); cách ly nguồn ngoài; kiểm tra tình trạng máy đo và que đo.
2. **Giai đoạn 2 — Thử tải giả không phát tia (laser tháo khỏi mạch):**
   - Lắp điện trở tải giả Rtest = 120 Ω ±5%, công suất danh định ≥ 1 W thay tại đầu J1, laser tháo rời vật lý khỏi mạch.
   - Tính toán thiết kế độc lập (tại Vmax = 5,25 V, Rmin = 114 Ω):
     + Dòng tải cực đại: `I_max = 5,25 V / 114 Ω ≈ 46,05 mA` (< 50 mA cổng B7).
     + Công suất tiêu tán cực đại trên trở: `P_max = (5,25 V)² / 114 Ω ≈ 0,242 W`.
     + Với Rtest công suất danh định ≥ 1 W, hệ số an toàn công suất > 4 lần (1 W / 0,242 W ≈ 4,13), không lo cháy trở.
     + Tuyệt đối không dùng điện trở R1 100 Ω 1/4 W đơn lẻ làm tải cho nguồn 5 V (vì P ≈ 0,276 W vượt quá định mức 0,25 W).
   - Đo kiểm dưới tải giả: kiểm tra sụt áp chân 5V không sụt < 4,75 V; đo Vds trên Q1; thử cắt mạch SW1/SW2; kiểm tra reset không loé; rút dây LASER_CTRL; kiểm tra hai timeout mất liên lạc > 3000 ms và laser max 5000 ms theo D038.
   - Thử liên động độc lập: thử SW1/SW2 với tải giả và nguồn riêng độc lập để chứng minh cắt nguồn phần cứng ngay cả khi Nucleo không cấp điện (cách ly hoàn toàn tín hiệu khỏi Nucleo).
3. **Giai đoạn 3 — Thử laser thật trong môi trường kiểm soát (sau khi đạt cổng driver hạn dòng):** Sau khi chặng tải giả đạt 100%, có xác nhận driver hạn dòng trên module laser (Cổng 3 / I13), lắp laser thật SYD1230 trong hộp che kín B5, đeo kính B10 đúng dải 600–700 nm, cửa đóng và estop nối mạch; đo L1 (4,75–5,25 V) và L3 (Vds ≤ 0,2 V) trên tải laser thật; đo L2 khi có dòng danh định.
4. **Giai đoạn 4 — Nghiệm thu toàn diện L1–L8:** Nghiệm thu toàn bộ 8 chỉ tiêu theo số lần quy định, có lưu log, ảnh và dạng sóng.

**Phân biệt vị trí que đo:**
- Đo điện áp nguồn tại J1 / điện áp tải: đo giữa cực dương J1.1 và cực âm J1.2.
- Đo Vgs của Q1: đo giữa Pin 1 (Gate) và Pin 2 (Source).
- Đo Vds của Q1: đo giữa Pin 3 (Drain) và Pin 2 (Source).
- Đo dòng tiêu thụ: đo nối tiếp bằng đồng hồ vạn năng ở thang mA DC theo quy trình được duyệt.
- Khảo sát xung reset: VOM hiển thị 0 V không đủ chứng minh không có xung ngắn lọt qua thời gian lấy mẫu; cần dùng máy hiện sóng oscilloscope (như GDS-1102B) với đầu dò thích hợp, trigger cạnh và timebase khảo sát; khi chưa có đầu dò/thiết bị thì ghi **CHƯA CHỐT** cách đo khảo sát xung reset.

## 6. Chưa quyết, cần người dùng

1. **SW2 nút dừng:** CHƯA CÓ (người dùng xác nhận 07/10: chưa có cả 2). Cần nút dừng khẩn cấp có 2 cặp tiếp điểm NC trước khi mở mạch có điện.
2. **SW1 công tắc cửa:** Lịch sử 07/10: chưa có; NGƯỜI DÙNG XÁC NHẬN 08/10: ĐÃ MUA lô 5 cái KW11 (dùng chung thông tin với D17 HOME, chưa phân bổ riêng; ảnh chat có cần gạt con lăn, 3 chân; chưa kiểm mã biến thể/tiếp điểm/gá), chỉ là ứng viên thử gá cơ khí tạm, CHƯA ĐẠT liên động an toàn SW1; ứng viên chính thức Omron SS-01GL tuần sau mới có.
3. **Adapter SOT-23 ra chân cắm breadboard:** Người dùng đã có adapter tự làm từ phíp đồng cắt rãnh hàn 3 dây Dupont đực (ảnh `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`, `docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png`); cần hoàn thành đo kiểm nhận không cấp nguồn ở Bước 2a trước khi cắm breadboard.
4. **Tải giả:** Cần chuẩn bị điện trở 120 Ω ±5% ≥ 1 W cho chặng thử tải giả không phát tia.
5. **Chốt PA8/PA9/PC7:** đối chiếu nhãn in trên bo trước khi cắm (PA8=D7, PA9=D8, PC7=D9).
6. **Dòng danh định laser:** Cần xác nhận trị danh định của module laser SYD1230 trước khi nghiệm thu L2 theo ±20%.
