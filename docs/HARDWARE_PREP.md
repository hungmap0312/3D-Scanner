# Danh mục chuẩn bị phần cứng theo tuần

> **Đính chính 2026-10-09 — D050:** người dùng xoá toàn bộ yêu cầu an toàn/liên động của `docs/SPEC.md` mục 9 (công tắc cửa SW1, nút dừng SW2, hộp kín, watchdog, giới hạn thời gian bật laser, kính bảo hộ như điều kiện cổng, MVS của D049). Các cổng/điểm dừng an toàn trong tệp này không còn chặn việc cấp nguồn laser hay chặng nào. Phần mạch MOSFET đóng ngắt laser vẫn là thiết kế chức năng. Nội dung dưới giữ nguyên làm lịch sử.

Lập ngày 2026-09-16 tối, kết phiên 2 của tuần 1. Toàn bộ là **ĐỀ XUẤT** của
phiên viết, rút từ ba nguồn: bản mô tả ngày 15/09 (mục 3 camera, 4 bố trí
quang học, 5 mạch điện và nguồn, phần an toàn), roadmap 14 tuần (điều
kiện đầu vào tuần 1–6) và BOM ngày 13/09 (mã A/B/C/D; BOM đó cũ về kiến
trúc theo D005 nhưng phần linh kiện laser, nguồn và cơ khí vẫn dùng được).
Không mục nào là quyết định; linh kiện thật khi mua về sẽ ghi vào
`docs/HARDWARE.md` với mã, ảnh và số đo, và chốt trong `DECISIONS.md`.

Cột **Có / Mua / ?**: `Có` đã sở hữu, `Mua` cần mua, `?` chưa biết.
NGƯỜI DÙNG TRẢ LỜI 16/09 tối cho bảy câu hỏi cuối tệp; các ô đã điền theo
đó, ô `?` là mục chưa hỏi tới. Nhóm D, E chỉ điền ba mục đã hỏi. Cột **Kiểm khi nhận** là việc phải làm trước khi tin vào
linh kiện; kết quả ghi vào `docs/HARDWARE.md`.

Mốc thời gian theo D010: tuần 2 bắt đầu **23/09**, tuần 3 **30/09**,
tuần 4 **07/10**, tuần 5 **14/10**, tuần 6 **21/10**. Mỗi nhóm dưới đây
ghi "cần có trước" là ngày bắt đầu tuần tương ứng.

## Nguyên tắc rút từ bản mô tả, áp cho mọi mục

- Không cấp laser hoặc động cơ trực tiếp từ chân GPIO (mô tả mục 5).
- Laser đóng ngắt qua MOSFET logic-level hoạt động ở 3,3 V, có điện trở
  cổng và điện trở kéo xuống để laser TẮT khi MCU reset (mục 5).
- Module laser vạch đỏ khoảng 650 nm, có mạch giới hạn dòng; chọn module
  có thông số và phân loại laser rõ từ nhà cung cấp, không suy độ an toàn
  từ công suất quảng cáo (mục 5 và phần an toàn).
- Laser chỉ hoạt động trong hộp kín có đường chặn tia, không có khe chiếu
  ra vị trí người dùng; cửa ngắt nguồn laser bằng phần cứng (phần an toàn).
- Nguồn hoàn thiện: adapter 12 V 3 A, nhánh motor riêng, buck 5 V cho
  camera, cầu chì, công tắc. Giai đoạn thử: Nucleo cấp qua USB, camera cấp
  bằng nhánh 5 V riêng; không nối song song 5 V từ USB và từ buck (mục 5).
- Thử quang học trước khi mua cơ khí; khoá lens và gá sau khi căn chỉnh
  (bảng rủi ro của mô tả). Đây là lý do nhóm A và B đi trước nhóm D.

## Nhóm A — ngay bây giờ, cho chỉ tiêu MT "Quang học" tuần 1 (không cần mua)

Cần có trước: càng sớm càng tốt, hạn tuần 1 là 22/09.

| # | Hạng mục | Yêu cầu cụ thể | Dùng cho | Kiểm khi nhận | Có / Mua / ? |
| --- | --- | --- | --- | --- | --- |
| A1 | Vật mẫu 1: khối hộp | Đục, nhám, không bóng, cạnh 50–100 mm; ví dụ hộp giấy cứng, khối gỗ. Bản mô tả (mục đánh giá) chọn "khối hộp và vật trụ nhám có kích thước ổn định" | Tuần 1 quang học; tuần 2 chiếu vạch; tuần 11 đo sai số | Đo ba cạnh bằng thước, ghi vào phiên chụp `--note` | Có: khối gỗ 30×32×49 mm, NGƯỜI DÙNG CUNG CẤP 17/09 kèm ảnh, mặt 32×49 có chữ và vạch bút chì. NHỎ HƠN dải 50–100 mm; đủ cho khảo sát quang học tuần 1 vì thước làm thang mm. Từ tuần 2 nên thêm hộp giấy cứng cạnh 60–100 mm, chưa mua |
| A2 | Vật mẫu 2: trụ nhám | Đường kính 50–100 mm, cao 50–120 mm; ví dụ cốc sứ mờ, lon bọc giấy nhám | như A1 | Đo đường kính và chiều cao | Có |
| A3 | Thước kẻ mm | Thước nhựa hoặc kim loại 300 mm, vạch mm rõ, đặt cạnh vật trong khung ảnh để ước lượng mm/pixel | Tuần 1 trường nhìn | Không | Có |
| A4 | Gá tạm cho bo S3 | Giữ bo không rung, ống kính ngang tầm vật: kẹp giấy lớn, băng dính hai mặt lên hộp, hoặc chân đế điện thoại mini | Tuần 1; tuần 2 thay bằng gá thử B8 | Bo không xê dịch khi rút cắm cáp | ? — chưa hỏi; tự làm từ đồ có sẵn |
| A5 | Nền và ánh sáng | Nền sau vật là tường hoặc bìa màu đồng nhất; đèn phòng ổn định, không nắng chiếu trực tiếp lên vật | Tuần 1 | Không | ? — tự bố trí |
| A6 | Cáp USB cho S3 | Đã có (đang dùng nạp và cấp nguồn) | — | — | Có |

## Nhóm B — trước tuần 2 (23/09): laser, mạch đóng ngắt, hộp che, gá thử

Điều kiện đầu vào tuần 2 theo roadmap: "Camera qua tuần 1; laser vạch,
MOSFET, nguồn phù hợp và hộp che tạm có đường chặn tia". Camera đã qua.

| # | Hạng mục | Yêu cầu cụ thể | Dùng cho | Kiểm khi nhận | Có / Mua / ? |
| --- | --- | --- | --- | --- | --- |
| B1 | Module laser **vạch** đỏ | 650 nm; loại **vạch** (line), không phải chấm (dot) hay chữ thập; điện áp 3–5 V DC; có mạch driver hạn dòng trên module; công suất ≤ 5 mW, nhà bán ghi rõ cấp (thường 3R); góc quạt (fan angle) 60–90° để phủ chiều cao vật 100–120 mm ở 250 mm (tối thiểu cần khoảng 31°); ưu tiên loại vặn được tiêu cự để lấy vạch mảnh tại 250 mm; thân Ø12 mm phổ biến, dễ kẹp. BOM A04 gợi ý Hshop HS0956. Mua **2** cái: một dùng, một dự phòng, vì hàng giá rẻ lệch thông số | Tuần 2 trở đi | Đo dòng tiêu thụ ở 5 V bằng đồng hồ (kỳ vọng dưới 50 mA); chiếu lên tấm B3 ở 250 mm, chụp ảnh vạch, đo bề rộng vạch theo pixel; ghi mã sản phẩm, điện áp ghi trên thân | **ĐÃ NHẬN 22/09 ×2**, mã `SYD1230`, nhãn ghi `650nm` và `Class IIIa`. Đã có 22/09: thân Ø12 mm × 40 mm (khớp yêu cầu Ø12), dây 130 mm, 2 dây đỏ/đen, điện áp 3–5 V DC và dòng < 40 mA (người bán) — **khớp** yêu cầu 3–5 V và kỳ vọng < 50 mA của B7; đầu phát có vành khía, có thể chỉnh tiêu cự (chưa thử). Chưa cấp nguồn, chưa đo thật. nhãn ghi công suất **5 mW** (NGƯỜI DÙNG XÁC NHẬN 22/09, khớp yêu cầu cột "Yêu cầu"). CHƯA KIỂM CHỨNG: vạch hay chấm, góc quạt, có mạch hạn dòng (người bán không xác định được). Theo `docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md` |
| B2 | MOSFET kênh N logic-level | Mở hoàn toàn ở Vgs = 3,3 V: chọn loại có Vgs(th) tối đa ≤ 2 V và nhà sản xuất cho Rds(on) tại 2,5 V hoặc 3,3 V. BOM A06 lịch sử ghi AO3400A; lựa chọn hiện hành theo D046 (07/10, đính chính D047) là **AO3400** (SOT-23, Rds(on) ≤ 52 mΩ tại Vgs = 2,5 V, Id danh định 5,8 A tại TA=25°C, VGS=10V theo datasheet AOS AO3400 Rev 8) thay thế cho linh kiện IRFZ44N nhận ngày 29/09 lệch yêu cầu IRLZ44N. Người dùng đã tự làm bo chuyển chân phíp đồng cắt rãnh hàn 3 dây Dupont đực (ảnh `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`, `docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png`). Cần đo kiểm nhận không cấp nguồn ở Bước 2a trước khi cắm breadboard | Tuần 2 mạch laser; tuần 6 lên PCB | Đọc mã in trên thân (A09T do người dùng cung cấp); kiểm nhận bo chuyển ở Bước 2a không cấp nguồn | **ĐÃ CHỌN AO3400 theo D046 (07/10)**: NGƯỜI DÙNG XÁC NHẬN 07/10: chọn AO3400, mã in trên thân `A09T` trên chiếc đã làm bo chuyển; NGƯỜI DÙNG XÁC NHẬN 08/10: **ĐÃ MUA 18 cái AO3400 SOT-23 rời** (không tính chiếc trên bo chuyển thành 19, không coi là mua thêm 18; chưa kiểm đếm/đo từng chiếc); đã có bo chuyển chân tự làm nối 3 dây Dupont đực. Lưu `IRFZ44N 258X 77 WS` đã nhận 29/09 lệch yêu cầu IRLZ44N làm lịch sử linh kiện |
| B2b | Bo chuyển chân AO3400 tự làm ra chân cắm breadboard | Bo chuyển chân chuyển đổi SOT-23 ra 3 chân cắm để cắm breadboard; người dùng đã tự làm từ phíp đồng cắt rãnh, hàn 3 dây Dupont đực (ảnh `docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png`, `docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png`). Chưa kiểm cách ly và ánh xạ chân; phân biệt rõ với adapter nguồn 12 V 3 A mua sẵn (D9) | Tuần 2 / C6 | Đo kiểm nhận bo chuyển chân ở Bước 2a không cấp nguồn (ngoại quan, cách ly, kiểm diode thân D–S và xả gate) | ĐÃ CÓ bo chuyển chân tự làm (NGƯỜI DÙNG XÁC NHẬN 07/10); CHƯA KIỂM CHỨNG / CẦN ĐO KIỂM NHẬN KHÔNG CẤP NGUỒN |
| B3 | Điện trở | 100 Ω ×3 (nối tiếp gate), 10 kΩ ×3 (kéo gate xuống GND), 1/4 W | Tuần 2 | Đọc vạch màu hoặc đo | 100 Ω **ĐÃ NHẬN 29/09** (1/4 W, khớp yêu cầu); 10 kΩ **Có**; NGƯỜI DÙNG XÁC NHẬN 07/10: có thêm 10 kΩ, 15 kΩ và tụ 100 nF (chỉ xác nhận sở hữu, công suất/dung sai chưa đối chiếu); 11/10: 15 kΩ 1/4 W có 50 cái; 2 W 120 Ω có 10 cái (xem `docs/HARDWARE.md`) |
| B4 | Tấm trắng nhám | Giấy A4 in mờ hoặc giấy vẽ, dán phẳng lên bìa cứng hoặc tấm foam; không dùng giấy bóng | Tuần 2 chiếu vạch, chỉ tiêu MT trích vạch | Không | Tự làm |
| B5 | Hộp che tạm | Thùng carton cỡ khoảng 40×40×40 cm, mặt trong dán giấy đen mờ hoặc sơn đen nhám; khoét một cửa sổ cho ống kính camera; laser gắn bên trong hướng vào tấm B4; không có khe nào cho tia đi ra phía người ngồi. ~~Chưa cần công tắc cửa ở tuần 2~~ [BỊ THAY THẾ: `docs/SPEC.md` mục 9.3 đòi công tắc cửa NC ngắt nguồn laser bằng phần cứng trước khi cấp nguồn laser; xem `docs/design/LASER_CIRCUIT.md` mục 1 SW1 và `docs/procedures/quy-trinh-c6-chuan-bi-mach-laser.md`] | Tuần 2 | Bật laser, đứng ngoài hộp nhìn quanh: không thấy tia trực tiếp | Tự làm (NGƯỜI DÙNG XÁC NHẬN 07/10: có hộp che; độ kín CHƯA KIỂM) |
| B6 | Breadboard và dây | Breadboard 400 hoặc 830 lỗ; dây jumper **cái–đực** (header Nucleo là chân đực) khoảng 20 sợi, dây đực–đực 20 sợi; kẹp cá sấu nhỏ 4 cái để nối laser tạm | Tuần 2, 5 | Không | Breadboard, jumper **Có**; kẹp cá sấu ? |
| B7 | Nguồn cho laser ở tuần 2 | Lấy 5 V từ chân `5V` Nucleo (cấu hình hiện có: JP5 = U5V, nguồn từ USB ST-LINK theo xác nhận 07/10). GIỚI HẠN THEO ST UM1724: tối đa 300 mA khi JP1 = OFF (sau enumeration), 100 mA khi JP1 = ON; MCU Nucleo tiêu thụ dòng nền nên phần dòng dư cho chân 5V không phải 300 mA trọn vẹn riêng cho laser. Cần kiểm tra vị trí JP1/JP5. Tuyệt đối không nối song song nguồn 5 V ngoài với chân 5V USB (tránh backfeed). Nguồn thử độc lập CHƯA CÓ | Tuần 2 | Đo điện áp tại laser khi bật | Có (chân 5V Nucleo; JP1/JP5 chưa kiểm) |
| B8 | Gá thử camera và laser | Một tấm gỗ ván hoặc MDF cỡ 300×400 mm làm đế; camera S3 và laser gắn lên hai khối gỗ nhỏ hoặc ke góc bằng băng dính hai mặt hoặc kẹp, chỉnh góc được rồi cố định. Bố trí ban đầu theo mô tả mục 4: góc giữa trục camera và mặt phẳng laser 25–35° tại vùng quét; với khoảng cách quét 250 mm thì laser đặt cách camera khoảng 115–175 mm theo phương ngang, cùng hướng vào vật; con số này chỉ để bắt đầu, chỉnh bằng thực nghiệm | Tuần 2, 3, 4 (tuần 4 đòi camera và laser giữ cố định) | Sau khi chỉnh, chụp ảnh gá và đo khoảng cách camera–laser, ghi `docs/HARDWARE.md` | Tự làm; đế gỗ ? |
| B9 | Đồng hồ vạn năng | Đo V DC, mA DC, thông mạch. Cần để đo dòng laser (B1), điện áp 5 V (B7), sau này dòng motor | Tuần 2 trở đi | Đo pin 1,5 V thử | **Mượn** cuối tuần (khoảng 20–21/09); NGƯỜI DÙNG XÁC NHẬN 07/10: đã có đồng hồ vạn năng (lịch sử); NGƯỜI DÙNG XÁC NHẬN 08/10: máy chốt dùng cho C6 là máy mượn của người thân (nhận 10/10), model/thang đo chưa biết, dừng đo ở Bước 2a tới khi nhận máy |
| B10 | Kính bảo hộ laser đỏ | Loại chặn 600–700 nm. ~~Không bắt buộc với 5 mW nếu không nhìn thẳng~~ [BỊ THAY THẾ: `docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md` điều kiện 5 và kế hoạch C6 Vòng 1 mục 6 yêu cầu kính đúng dải bước sóng khi thao tác laser; NGƯỜI DÙNG XÁC NHẬN 07/10 đã có kính bảo hộ] | Tuần 2 trở đi | Ghi dải bước sóng ghi trên kính | Có (NGƯỜI DÙNG XÁC NHẬN 07/10) |
| B13 | Công tắc cửa NC (SW1) | Microswitch tiếp điểm NC ngắt nguồn laser phần cứng khi mở cửa. Ứng viên chính thức: Omron SS-01GL (tuần sau mới có). Đề xuất tạm: KW11 cơ khí (SPDT COM/NO/NC) chỉ dùng để thử gá cơ khí không cấp điện | Tuần 2 liên động C6 | Đo thông mạch: cửa đóng kín COM–NC, cửa hé ngắt mạch | **Lịch sử 07/10: CHƯA CÓ** (chưa có cả 2: SW1 và SW2); NGƯỜI DÙNG XÁC NHẬN 08/10: **ĐÃ MUA 5 cái KW11** (dùng chung thông tin lô 5 cái với D17 HOME, chưa phân bổ số lượng riêng; ảnh chat có cần gạt con lăn, 3 chân); chưa kiểm mã biến thể/chân/tiếp điểm/gá; chỉ là ứng viên thử gá cơ khí tạm, **CHƯA ĐẠT liên động an toàn SW1** theo `docs/SPEC.md` mục 9.3; ứng viên chính thức Omron SS-01GL vẫn chưa có |
| B14 | Nút dừng khẩn cấp (SW2) | Nút nhấn NC có hai cặp tiếp điểm NC: một cặp cắt đường nguồn V_LASER_PWR bằng phần cứng, một cặp báo `SENSE_ESTOP` về Nucleo | Tuần 2 an toàn C6 | Đo thông mạch hai cặp NC độc lập | **ĐÃ CÓ 1 nút (NGƯỜI DÙNG XÁC NHẬN 12/10, quan sát: 2 tiếp điểm NC; nhãn `CNAOM LA38`, đọc từ ảnh; chưa đo thông mạch)**; yêu cầu liên động đã bỏ theo D050, dùng tuỳ chọn. Trước đó: CHƯA CÓ (NGƯỜI DÙNG XÁC NHẬN 07/10: chưa có cả 2) |
| B15 | Tải giả C6 (Rtest) | Điện trở 120 Ω ±5%, công suất danh định ≥ 1 W (Planner tính: tại 5,25 V / 114 Ω cho I ≈ 46,05 mA, P ≈ 0,242 W) để thử nghiệm không phát tia | Tuần 2 thử tải giả C6 | Đo điện trở bằng VOM, kiểm tra công suất danh định | **ĐỀ XUẤT thiết kế Vòng 4, CHƯA CÓ / CHƯA XÁC NHẬN** |

### Sơ đồ mạch laser đề xuất cho tuần 2 (đấu tạm trên breadboard)

```
Nucleo 5V (chân 5V trên CN7, đối chiếu nhãn bo/UM1724; xem B7)
   ───[SW1 cửa NC]───[SW2 estop NC]───┬─── cực (+) tải (laser J1.1 hoặc tải giả Rtest)
                                      │
                                  [C1 100 nF]
                                      │
                                     GND
Nucleo GPIO (PA8, nhãn D7 trên CN9)
   ───[R1 100 Ω]───┬─── Gate (Pin 1) MOSFET AO3400 (SOT-23 qua adapter tự làm)
                   │
               [R2 10 kΩ]
                   │
                  GND
Source (Pin 2) MOSFET ─── GND chung (Nucleo GND)
Drain (Pin 3) MOSFET ─── cực (−) tải (laser J1.2 hoặc tải giả Rtest)
```

- Chọn chân: `PA8` được đề xuất vì không trùng PA2/PA3 (USART2) và PA5
  (LD2); ánh xạ PA8 ↔ nhãn `D7` lấy từ tài liệu UM1724 của ST, **phải
  đối chiếu với nhãn in trên bo trước khi cắm** (ảnh bo ngày 16/09 thấy rõ
  cột nhãn D2–D13 trên CN9/CN10). Chốt chân khi làm lệnh `LASER`.
- Q1 đã chốt chọn **AO3400** (D046, đính chính D047); sơ đồ chân SOT-23: Pin 1 = Gate, Pin 2 = Source, Pin 3 = Drain qua adapter tự làm ra 3 đầu dây Dupont; tuyệt đối không dùng thứ tự TO-220 1:G, 2:D, 3:S của IRFZ44N.
- Điện trở 10 kΩ kéo gate xuống làm laser tắt khi Nucleo reset, khi chân
  còn ở trạng thái trở kháng cao lúc khởi động, hoặc khi rút dây tín hiệu.
  Đây là yêu cầu "tắt khi MCU reset" của mô tả mục 5.
- Liên động phần cứng: SW1 (cửa NC) và SW2 (nút dừng NC) cắt trực tiếp đường cấp nguồn phần cứng. Không mặc định cửa đóng đè cần thì COM–NC kín (với công tắc vi động SPDT, đè cần thì COM–NC ngắt và COM–NO kín; trạng thái tiếp điểm thực tế của cơ cấu gá CHƯA XÁC NHẬN, bắt buộc đo thông mạch ở hai trạng thái cửa trước khi nối dây).
- Firmware sẽ thêm liên động phần mềm: chân mặc định mức thấp; tắt laser
  khi mất liên lạc > 3000 ms (`T_hb`) hoặc hết hạn laser max 5000 ms (`T_laser_max`) theo D038.
- Không bật laser trước khi: mạch có điện trở kéo xuống R2 10 kΩ; công tắc cửa SW1 (NC) và nút dừng khẩn cấp SW2 (NC) đấu nối phần cứng ngắt nguồn; module laser có driver hạn dòng (Cổng 3 / I13); hộp che B5 đã che kín; người ngồi phía sau camera; có kính bảo hộ B10 đúng dải bước sóng 600–700 nm; các cổng tiền kiểm an toàn và thử tải giả đã đạt. Thử nghiệm trước bằng tải giả B15 (120 Ω ≥ 1 W).

### Bổ sung nhóm B ngày 17/09 sau khảo sát quang học

| # | Hạng mục | Yêu cầu cụ thể | Dùng cho | Kiểm khi nhận | Có / Mua / ? |
| --- | --- | --- | --- | --- | --- |
| B11 | Mắt kính lão +3.00 D, thêm +3.50 D nếu tiện | Kính hội tụ (dấu +), loại rẻ ở hiệu thuốc/chợ hoặc mượn; chỉ dùng mảnh ≈ 2 mm giữa mắt kính nên chất lượng không quan trọng. Cơ sở: ống kính OV3660 lấy nét ≈ 1,4 m, barrel không xoay được (17/09); +3.00 D đưa tiêu điểm về ≈ 270 mm, +3.50 D về ≈ 240 mm | Bước 3.8 tuần 1; nếu đạt thì gá cố định cùng gá thử B8 cho tuần 2–3 | Theo `docs/procedures/quy-trinh-thu-kinh-can-canh.md` (chuyển khỏi `STATUS.md` 22/09, D031): vạch mm tách được ở `/capture`, rồi đo bề rộng mép | Người dùng 18/09: KHÔNG THỰC HIỆN ĐƯỢC hiện tại; giữ mục để dùng sau |
| B12 | Module camera dự phòng cho bo `ESP32-S3 WROOM` | Cùng đầu nối cáp dẹt 24 chân bước 0,5 mm, cáp 21 mm, **pinout khớp bo** — CHƯA XÁC NHẬN; cách kiểm: trang người bán bo liệt kê module camera nào cho đúng bo này thì mua trong số đó. 18/09 người dùng tra: trang bán ghi "KIT ESP32-S3 N16R8 Camera board OV3660, OV5640", hỗ trợ OV3660 hoặc OV5640 tuỳ phiên bản → module OV5640 của cùng người bán là ứng viên; trước khi mua hỏi người bán xác nhận dùng cho bản N16R8 này, cáp 21 mm, và hỏi ống kính có vặn tiêu cự được không (module OV3660 hiện tại không vặn được). Ưu tiên bản ghi "chỉnh được tiêu cự" hoặc ngàm M12. OV5640 có AF là hướng phụ, phức tạp hơn (firmware AF, khoá tiêu điểm khi hiệu chuẩn) | Bảo hiểm nếu B11 không đạt; tuần 2 trở đi | Cắm thay module hiện tại, chạy `CameraWebServerTest`, PID phải đọc được; kiểm tiêu cự xoay được trước khi dán | **ĐÃ NHẬN 22/09 ×2**: `FD5640 500W -V11`, người bán báo tự động lấy nét, tiêu cự 3 mm. CHƯA cắm, CHƯA đọc PID, CHƯA đếm chân cáp — ba điều kiện của cột này đều chưa kiểm. Theo `docs/procedures/quy-trinh-tiep-nhan-camera-fd5640.md`. Nếu AF thật thì phải khoá được tiêu điểm mới dùng cho quét (SPEC 13–15) |

## Nhóm C — trước tuần 3 (30/09): hiệu chuẩn camera và mặt phẳng laser

| # | Hạng mục | Yêu cầu cụ thể | Dùng cho | Kiểm khi nhận | Có / Mua / ? |
| --- | --- | --- | --- | --- | --- |
| C1 | Bảng bàn cờ | In laser trên giấy mờ, lưới ô vuông ví dụ 9×6 góc trong với ô 20 mm (vừa khổ A4), dán phẳng không bọt lên tấm cứng phẳng (mica 3 mm, kính, hoặc MDF); mặt bảng không bóng. BOM D04 | Tuần 3 nội tham số; tuần 4 tư thế bảng cho mặt phẳng laser | **Đo kích thước ô thực sau in** bằng thước cặp hoặc thước kẻ trên 5 ô liên tiếp rồi chia, ghi vào hồ sơ hiệu chuẩn; mô tả nhấn mạnh không dùng kích thước trong tệp | Tự in |
| C2 | Thước cặp | Độ chia 0,05 hoặc 0,02 mm; mượn được thì không mua (mô tả gợi ý mượn) | Đo ô bàn cờ C1; đo vật mẫu tuần 11 | Đo một khối chuẩn có sẵn, ví dụ cạnh bo Nucleo | **Mượn** được |
| C3 | Giá đỡ bảng | Kẹp hoặc giá để đặt bảng C1 ở nhiều tư thế nghiêng trong vùng quét mà không rung | Tuần 3, 4 | Không | ? |

## Nhóm D — trước tuần 5 (14/10): bàn xoay, driver, nguồn 12 V

Điều kiện đầu vào tuần 5: "Kết quả quang học tuần 2 và 4; NEMA17, A4988,
nguồn, đai GT2, ổ đỡ, trục, mâm và HOME". Mua sau khi tuần 2 và 4 cho kết
quả, đúng nguyên tắc "thử quang học trước mua cơ khí". Thông số theo mô
tả mục 4 và BOM C01–C13, B01–B05.

| # | Hạng mục | Yêu cầu cụ thể | BOM | Có / Mua / ? |
| --- | --- | --- | --- | --- |
| D1 | Động cơ bước NEMA17 | 1,8°/bước, 4 dây, trục 5 mm; dòng định mức ghi rõ trên nhãn để chỉnh A4988 (BOM gợi ý đặt 0,6–0,9 A/pha ban đầu) | C01 | **ĐÃ CÓ 1 cái (NGƯỜI DÙNG XÁC NHẬN 11/10)**: nhãn `42HD3401S-23B`, đọc từ ảnh; chưa đo, nhãn không ghi dòng định mức (xem `docs/HARDWARE.md`, mục 11/10). Trước đây: Mua (chưa có) |
| D2 | Driver A4988 kèm tản nhiệt | Chế độ 1/16 vi bước; VDD 3,3 V; VMOT 12 V; điện trở sense ghi trên module để tính dòng | A05 | **ĐÃ MUA 1 bộ (08/10)** (ảnh chat bo đỏ có chữ A4988, tản nhiệt rời; chưa kiểm điện trở sense/IC/hàn tản nhiệt, chưa chỉnh Vref, chặng motor chưa mở; lịch sử: chưa có) |
| D3 | Pulley GT2 20 răng | Đai 6 mm, lỗ 5 mm, có vít chặn | C02 | **ĐÃ MUA 1 cái (08/10)** (thông số 20T lỗ 5 mm theo người dùng báo, chưa đếm răng/đo lỗ thực tế; chặng motor chưa mở; lịch sử: chưa có) |
| D4 | Pulley GT2 60 răng | Đai 6 mm, lỗ 8 mm, có vít chặn (tỷ số 3:1 → 9 600 xung/vòng ở 1/16) | C03 | **ĐÃ MUA 1 cái (08/10)** (thông số 60T lỗ 8 mm theo người dùng báo, chưa đếm răng/đo lỗ thực tế; chặng motor chưa mở; lịch sử: chưa có) |
| D5 | Đai GT2 vòng kín 6 mm | Chiều dài chọn sau khi vẽ lắp khoảng cách hai trục; mua sau D3–D4 | C04 | |
| D6 | Trục thép trơn Ø8 mm | Dài 100–150 mm, chốt theo bản vẽ | C05 | |
| D7 | Gối bi KFL08 ×2 | Lỗ 8 mm, đặt cách nhau để chống lắc | C06 | |
| D8 | Vòng bi chặn dọc trục F8-16M | Chịu khối lượng mâm và vật (mục tiêu tải 300 g, thử lệch tâm) | C09 | |
| D9 | Adapter 12 V 3 A | Vỏ kín, jack DC 5,5×2,1 mm; nhánh motor riêng | B01 | **ĐÃ NHẬN 1 bộ (NGƯỜI DÙNG XÁC NHẬN 11/10)**: nhãn `MODEL:1230`, `12V DC 3A`, tâm dương, đọc từ ảnh; chưa đo bằng VOM (xem `docs/HARDWARE.md`, mục 11/10 chiều). Trước đó: **ĐÃ ĐẶT — CHỜ NHẬN 1 bộ (08/10)** (chưa nhận hàng; chưa xác nhận cực tính jack 5,5×2,1, điện áp thực tế hay nhãn nhà sản xuất; phân biệt với bo chuyển chân AO3400 tự làm; nguồn hiện dùng cho Nucleo/laser vẫn là USB ST-LINK; lịch sử: chưa có; 10/10: người dùng dự kiến nhận sau 1–2 ngày) |
| D10 | Buck 5 V | Từ 12 V ra 5 V ≥ 2 A cho camera S3 (S3 + Wi-Fi có đỉnh dòng lớn); có tụ đầu ra | mô tả mục 5 |  **ỨNG VIÊN ĐÃ NHẬN 10/10:** mạch XL4005 (ảnh `docs/logs/buck-xl4005-*.jpg`, chi tiết ở `docs/HARDWARE.md`); chưa chỉnh, chưa đo, cần nguồn vào lớn hơn 5 V (adapter 12 V đang chờ) |
| D11 | Jack DC, công tắc nguồn, cầu chì DC và đế | Đúng dòng dây và tải; tụ khối sát VMOT (ví dụ 100 µF/25 V) | B04 | |
| D12 | Dây 22–24 AWG, ống co nhiệt, dây rút | Không dẫn dòng motor qua breadboard | B05 | |
| D13 | Bích kẹp trục lỗ 8 mm, vòng chặn Ø8 ×2, long đen | Gắn mâm lên trục và định vị dọc trục | C07, C08 | |
| D14 | Mâm xoay Ø160 mm | Gỗ hoặc mica 6–8 mm, phủ đen nhám, có cơ cấu giữ vật tháo lắp được | C10 | |
| D15 | Gá motor chữ L có rãnh căng đai | Khớp NEMA17 | C11 | |
| D16 | Đế máy MDF khoảng 400×400 mm, dày 12–15 mm | Đặt camera, laser, bàn xoay chung đế; thay cho đế thử B8 | C13 | |
| D17 | Công tắc HOME | Microswitch có cần gạt, dùng để xác lập gốc | A07 | **ĐÃ MUA ứng viên KW11 (08/10)** (lô 5 cái KW11 dùng chung thông tin với B13 SW1, chưa phân bổ số lượng riêng; ảnh chat có cần gạt con lăn, 3 chân; chưa kiểm mã biến thể/tiếp điểm/cơ cấu gá mâm; chặng motor/HOME chưa mở; lịch sử: chưa có) |
| D18 | Bu lông M3/M4, đai ốc, long đen, trụ đỡ, bản lề, chốt cửa, chân cao su | | C15 | |
| D19 | Mỏ hàn, thiếc, kìm tuốt dây, tua vít | Dụng cụ, chưa có trong BOM | — | |

## Nhóm E — trước tuần 6 (21/10): liên động và PCB

| # | Hạng mục | Yêu cầu cụ thể | BOM | Có / Mua / ? |
| --- | --- | --- | --- | --- |
| E1 | Công tắc cửa buồng | Tiếp điểm đóng khi cửa đóng; mở cửa **ngắt nguồn laser bằng phần cứng** và có đường báo trạng thái riêng về Nucleo | A08 | |
| E2 | Nút dừng tự giữ | Tiếp điểm NC chịu tải DC, ngắt nhánh laser và động lực; trạng thái lỗi chỉ xoá bằng thao tác có chủ ý | A09 | |
| E3 | PCB lỗ để hàn mạch mẫu | Hàn thử nguồn, MOSFET, đầu nối trước khi đặt PCB | D01 | |
| E4 | Socket, đầu nối | Socket A4988; đầu nối motor 4P; laser, HOME, cửa 2P; terminal nguồn | D03 | |
| E5 | Đặt PCB hai lớp | Sau ERC/DRC tuần 6; giữ mạch thử để tuần 7 không phụ thuộc ngày nhận bo | D02 | |

## An toàn laser, áp dụng từ nhóm B

- Laser 650 nm ≤ 5 mW thường là cấp 3R: không nhìn thẳng vào tia hoặc vào
  phản xạ gương, không chiếu vào mắt người khác, không đặt thấu kính hội tụ
  trước tia. Vạch quét trên bề mặt nhám thì nhìn được bình thường.
- Chỉ bật laser khi: mạch có điện trở kéo xuống; có công tắc cửa NC (SW1)
  ngắt nguồn bằng phần cứng và nút dừng NC (SW2/estop) ngắt nguồn (SPEC
  9.3, 9.4; `docs/design/LASER_CIRCUIT.md` mục 1); firmware có liên động tắt
  khi reset và khi mất liên lạc; hộp che đã đóng hướng tia; đeo kính bảo hộ
  B10 (`docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md` điều kiện 5,
  kế hoạch C6 Vòng 1 mục 6); người ngồi phía sau camera.
- Ghi lại mã module, thông số nhà bán và dòng đo được; nếu nhà bán không
  ghi phân loại, coi module là chưa rõ và không dùng ngoài hộp.

## Trả lời của người dùng 16/09 tối và danh sách mua trước tuần 2

Trả lời nguyên văn, NGƯỜI DÙNG CUNG CẤP: (1) đã có hộp/trụ nhám và thước
mm; (2) chưa có laser; (3) chưa có MOSFET và 100 Ω, có trở 10 kΩ; (4) có
breadboard và jumper, chưa có đồng hồ vạn năng, cuối tuần có thể mượn;
(5) chưa có kính bảo hộ; (6) chưa sở hữu NEMA17, A4988, adapter 12 V;
(7) có thể mượn thước cặp.

Hệ quả: **nhóm A đủ ngay**, khảo sát quang học tuần 1 làm được không cần
mua gì. **Nhóm B cần mua bốn thứ** trước 23/09:

| # | Mua | Số lượng | Ghi chú khi mua | Giá dự toán theo BOM 13/09 |
| --- | --- | --- | --- | --- |
| B1 | Module laser vạch đỏ 650 nm, 3–5 V, có driver hạn dòng, ≤ 5 mW, vạch (line) | 2 | Hỏi rõ: "vạch" không phải "chấm"; góc quạt; có vặn tiêu cự không; nhà bán ghi công suất và cấp. BOM gợi ý Hshop HS0956 | 35 000 đ/cái, chưa tra lại giá |
| B2 | MOSFET AO3400 (SOT-23) + bo chuyển chân | 3 (dự kiến lịch sử) | **ĐÃ CHỌN AO3400 theo D046 (07/10)**: NGƯỜI DÙNG XÁC NHẬN 08/10: **ĐÃ MUA 18 cái AO3400 SOT-23 rời** (không tính chiếc trên bo chuyển thành 19, không coi là mua thêm 18; chưa kiểm đếm/đo từng chiếc); người dùng đã tự làm bo chuyển chân phíp đồng cắt rãnh ra 3 đầu dây Dupont đực; cần kiểm nhận ở Bước 2a không cấp nguồn. Lưu IRFZ44N nhận 29/09 lệch yêu cầu IRLZ44N làm lịch sử linh kiện | BOM A06 gộp 20 000 đ cho MOSFET + trở |
| B3 | Điện trở 100 Ω 1/4 W | 3–10 | Mua theo gói 10 rẻ hơn; hoặc một bộ trở tổng hợp dùng cho các tuần sau — **ĐÃ NHẬN 29/09** (1/4 W); NGƯỜI DÙNG XÁC NHẬN 07/10: có thêm 10 kΩ, 15 kΩ và tụ 100 nF (chỉ xác nhận sở hữu); 11/10: 15 kΩ 1/4 W có 50 cái; 2 W 120 Ω có 10 cái | trong A06 |
| B10 | Kính bảo hộ laser đỏ, chặn 600–700 nm | 1 | ~~Khuyến nghị, không bắt buộc với 5 mW~~ [BỊ THAY THẾ: `docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md` điều kiện 5 và kế hoạch C6 Vòng 1 mục 6 yêu cầu kính đúng dải bước sóng; NGƯỜI DÙNG XÁC NHẬN 07/10: đã có kính bảo hộ] | chưa tra giá |
| B13 | Công tắc cửa NC (SW1) | 1 (dự kiến lịch sử) | Microswitch tiếp điểm NC ngắt nguồn laser phần cứng khi mở cửa. Lịch sử 07/10: chưa có cả 2 (SW1 và SW2); NGƯỜI DÙNG XÁC NHẬN 08/10: **ĐÃ MUA 5 cái KW11** (dùng chung thông tin lô 5 cái với D17 HOME, chưa phân bổ số lượng riêng; ảnh chat có cần gạt con lăn, 3 chân); chưa kiểm mã biến thể/tiếp điểm/gá; chỉ là ứng viên thử gá cơ khí tạm, **CHƯA ĐẠT liên động an toàn SW1** theo SPEC 9.3; ứng viên chính thức Omron SS-01GL tuần sau mới có | chưa tra giá |
| B14 | Nút dừng khẩn cấp NC (SW2) | 1 | Nút nhấn estop 2 cặp tiếp điểm NC: một cặp ngắt nguồn phần cứng, một cặp báo Nucleo. **ĐÃ CÓ 1 nút (NGƯỜI DÙNG XÁC NHẬN 12/10, 2 tiếp điểm NC, chưa đo)**; trước đó: CHƯA CÓ (NGƯỜI DÙNG XÁC NHẬN 07/10: chưa có cả 2) | chưa tra giá |
| B15 | Tải giả C6 (Rtest) | 1 | Điện trở 120 Ω ±5%, công suất danh định ≥ 1 W (Planner tính: tại 5,25 V / 114 Ω cho I ≈ 46,05 mA, P ≈ 0,242 W) để thử nghiệm không phát tia. **ĐỀ XUẤT thiết kế Vòng 4, CHƯA CÓ / CHƯA XÁC NHẬN** | chưa tra giá |

Tuỳ chọn: kẹp cá sấu nhỏ 4 cái để nối laser tạm; đế gỗ/MDF nhỏ 300×400
mm cho gá thử B8 nếu nhà không có sẵn tấm nào.

Mượn cuối tuần (20–21/09): ~~đồng hồ vạn năng (B9)~~ [NGƯỜI DÙNG XÁC NHẬN 07/10: đã có đồng hồ vạn năng], thước cặp (C2). Đồng
hồ cần có trước khi bật laser lần đầu để đo dòng.

Nhóm D chưa mua, đúng nguyên tắc "thử quang học trước mua cơ khí"; quyết
định mua sau khi tuần 2 và 4 có kết quả.
[ĐÍNH CHÍNH 08/10/2026: Người dùng đã mua trước một phần vật tư cơ khí/driver (D2 A4988 ×1 bộ, D3 puly 20T ×1, D4 puly 60T ×1, D17 KW11 trong lô 5 cái) và đặt nguồn D9 (12 V 3 A ×1 bộ — chờ nhận). Giữ nguyên tắc cổng kỹ thuật: việc mua trước không mở chặng động cơ tuần 5, không cấp nguồn motor, không thay đổi thứ tự ưu tiên thử nghiệm quang học/laser tuần 2].
