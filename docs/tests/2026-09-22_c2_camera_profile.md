# Phép thử C2/C2b — khoá hồ sơ camera OV3660, ma trận bốn cấu hình trên bo thật

Tên tệp giữ đúng chỉ định của `handoff/2026-09-21_c2-camera-profile/01_PLAN.md`
Vòng 4 mục 2. Tệp ghi **ba lần thử**: lần hiện hành (Vòng 8, đợt
`20260928_1117`, 28/09, có ảnh bố trí) ở phần chính; Vòng 7 (25/09 và
27/09 — số đo tham khảo, thiếu ảnh bố trí, R05) ở Phụ lục A; Vòng 4
(23/09, CHƯA ĐẠT) ở Phụ lục B. Không xoá lần nào.
Người thao tác bo: người dùng. Người lập hồ sơ: Tester (Claude Code).

**Kết quả tóm tắt (Vòng 8, đợt `20260928_1117`): ĐẠT.** Bố trí mới có ảnh
chụp ngoài **trước khi đo** (commit `d2c2933` trước bước B), lúc đổi rèm
và cuối đợt; camera và vật không xê dịch suốt đợt. Khoảng cách ≈ 246–250
mm (không có ê-ke — xem giới hạn). Preset 1 và 2 đạt O5–O7, chọn preset 2
(Cloudy). T5 `d < 2 %` trên bốn cấu hình ma trận; bề rộng mép đo được 5/5
ảnh mọi phiên. Đề xuất cấu hình **chính SVGA q20, phụ VGA q10**. Bốn hồ
sơ mới đã `verified`; ảnh thô, hồ sơ, log và ảnh bố trí có bản sao OneDrive
`backup_scanner3d_20260928_1117`, hash khớp. Giới hạn còn mở: O3/L07
(D016), vạch laser ở quality 20, khung ảnh hỏng không bị script bắt — xem
"Điều chưa thể kết luận".

## Mục tiêu phép thử

Theo `01_PLAN.md` "Vòng 8 (điều chỉnh)" (V8-T5R…T10R) và `docs/SPEC.md`
mục 10.2, làm lại toàn bộ khảo sát trong một bố trí mới có ảnh bố trí:

1. Cổng ảnh bố trí trước khi đo: 250 mm, gá, vật, giấy, đèn, rèm.
2. Chọn preset cân bằng trắng (`wb_mode` 1–4) đạt O5 (lệch độ sáng so tham
   chiếu tự động ≤ 15 %), O6 (`channel_spread_pct` ≤ 15 %), O7 (tối/bão
   hoà bất kỳ kênh ≤ 1 % mỗi phía).
3. T5: `d = 100 × max|mᵢ − m̄| / m̄ < 2 %`, controls và bảy thanh ghi ổn định.
4. C2b: VGA/SVGA × quality 10/20 — bề rộng mép, kích thước tệp, thời gian
   `/capture`; chọn cấu hình chính/phụ theo số đợt này.
5. Chẩn đoán haze: rèm mở/đóng có ảnh bố trí hai trạng thái, chỉ so sánh.
6. `verified` cho bốn hồ sơ ma trận; bản sao thứ hai.

## Bo / camera / revision

- ESP32-S3 N16R8 có camera; **OV3660, PID `0x3660`** — NGƯỜI DÙNG XÁC NHẬN
  trên Serial Monitor 115200. Firmware `CameraWebServerTest` (D013), phiên
  bản nạp CHƯA ĐỐI CHIẾU commit. Không nạp lại firmware. IP `192.168.31.9`.
- Bo **tắt nguồn** khoảng 12:50–14:59 (người dùng tắt thiết bị, ghi trong
  sổ); khởi động lại ~14:59:25 theo X-Timestamp. Từ đó tới hết G không
  khởi động lại (X-Timestamp liên tục).

## Nguồn cấp và kết nối

Cáp USB tới máy tính, Wi-Fi LAN. Laser **tắt và chưa đấu**; không Nucleo,
không bàn xoay, không `pair_capture`.

## Hệ điều hành, IDE, board package

Windows 11 Home, Git Bash trong VS Code, Python 3.11.9 trong `.venv`.
Board package theo `ENVIRONMENT.md` mục ESP32-S3.

## Mã nguồn / commit / thay đổi chưa commit

- Mã PC được kiểm: B7 `7cb659e`; quy trình B8 `85c1044` (`03_TEST.md`
  Vòng 8: V8-T1…T4 đạt, bộ 50 kịch bản chạy lại 50/50).
- Commit lúc chụp: `50d6348` (A5, cây sạch) và `d2c2933` (B–G). Các phiên
  B–G ghi `dirty: true` vì sổ ghi nhận và log Tester chưa commit; `pc/`
  không đổi (`git diff d2c2933..HEAD -- pc/` rỗng).

## Toàn bộ cài đặt build liên quan

Không build lại firmware. Cấu hình camera do các hồ sơ ở "Bảng giá trị".

## Cổng và tốc độ Serial

Serial Monitor 115200 chỉ để đọc PID và IP. Mọi số đo qua HTTP.

## Bước tái hiện

Theo `docs/procedures/quy-trinh-c2-camera-profile.md` bản Vòng 8 (B8).

**A — bố trí và cổng ảnh (11:15–12:50).**
1. Bố trí: tờ A4 bọc trên hộp (bên trái), khối gỗ mặt có chữ, thước 20 cm
   dán trên giấy cách mép khối ≈ 1,5 cm; camera trên gá, tâm cao 62 mm;
   mốc băng dính trên bàn, vạch bút chì dưới mặt ống kính, mốc chữ L ở chân
   đế camera. Thư mục đợt `docs/logs/c2-bo-tri-v8/20260928_1117/`.
2. A5 bốn lần: `…_112715` (quên khối gỗ), `…_113005` và `…_120001` chưa
   đạt (thước che/sát mép khối; thước 30 cm trong khung), `…_122446` đạt.
   Raw `…_112715` bị xoá vào Thùng rác rồi khôi phục (hash khớp).
3. A6/A7: 16 ảnh điện thoại gốc; A8 Tester kiểm; commit `d2c2933` trước B.

**B–C (15:01–15:16).**
4. Lần đầu không dùng: bo vừa khởi động lại nên probe
   `probe_20260928_150138` chạy ở QVGA; B2 `…_150226` có ảnh 2 hỏng.
5. A5 lại `…_151109`; B1 `probe_20260928_151120`: `aec_value = 783`
   (**kẹp** từ 784), `agc_gain = 8` (`0x350a = 128`).
6. B2 tham chiếu tự động `capture_20260928_151158`; đầu và cuối đều
   `{'aec': 1, 'agc': 1, 'awb': 1, 'awb_gain': 1, 'wb_mode': 0, '0x3406': 0}`.
7. B3 ROI giấy `40,60,200,300`; `m_ref = 169,6`.
8. C1 bốn hồ sơ `cam_VGA_q10_20260928`, `_r01`, `_r02`, `_r03` (`wb_mode`
   1–4); C2 bảng thanh ghi WB khớp 4/4.

**D–G (15:20–15:45).**
9. D1/D2 `…_152048`, `…_152150`, `…_152228`, `…_152301`; D3 chọn preset 2.
10. F: `cam_VGA_q20_20260928` → `…_153631`; `cam_SVGA_q10_20260928` →
    `…_153742`; `cam_SVGA_q20_20260928` → `…_153824`. Cùng 783 / 8 /
    `wb_mode=2`.
11. G1 ảnh `20260928_154007` (rèm cuốn cửa sổ gần mở) → G-a `…_154022`;
    G3 ảnh `20260928_154123` (rèm kéo xuống) → G-b `…_154135`; G5 ảnh
    `…_154425`–`…_154511`, đo lại 250 mm lúc 15:45.

**H — Tester chạy trên dữ liệu (không chạm bo).** `pc/sharpness.py` sáu
phiên với ROI VGA `40,60,200,300`, SVGA `50,75,250,375` →
`docs/logs/sharpness_c2b_v8_20260928/`; `pc/ruler_ticks.py <phiên> --edge
380,255,370` (VGA) / `--edge 475,320,462` (SVGA) →
`docs/logs/c2b-mep-v8-2026-09-28.log`; bytes (JPEG thật tới dấu `FFD9`
đầu tiên) và `elapsed_ms` từ `frames.csv`.

## Kết quả mong đợi

- Ảnh bố trí trước đo, lúc đổi rèm, cuối đợt; mốc không xê dịch.
- Ít nhất một preset đạt O5–O7; T5 `d < 2 %`; thanh ghi ổn định.
- Bốn cấu hình C2b `PASS`, mép đo được 5/5 ảnh mỗi phiên.

## Kết quả quan sát thực tế

- 16 phiên ngày 28/09 đều `PASS` theo script; phiên dùng trong kết luận:
  tham chiếu, bốn preset, ba F, G-a, G-b.
- Ảnh đúng chiều. Thanh ghi WB đúng bảng preset; sau áp = cuối phiên cho
  bảy khoá ở mọi phiên khoá; `0x3500 = 12528` (783×16), `0x350a = 127`.
- **Không xê dịch:** mép trái khối gỗ x 381–382, mép trên khối y 239–241,
  mép phải thước x 327 trên ảnh camera từ A5 (12:24) tới G-b (15:41);
  mốc chữ L vẫn ôm chân đế ở ảnh G5; đo lại cuối đợt 250 mm (người dùng).
- **Khung hỏng không bị bắt:** `…_150226` ảnh 2 nửa dưới sọc tím/xanh,
  `decode_ok=True`, phiên `PASS` (bytes 15 443 so với ~10 900). Phiên này
  không dùng.
- **Dữ liệu thừa sau JPEG:** `…_153631` ảnh 3 = JPEG 8 753 byte + 1 678
  byte sau dấu `FFD9` đầu tiên; ảnh nguyên vẹn, điểm ảnh khớp các ảnh khác.
  Một trên 60 ảnh ngày 28/09.

## Log nguyên văn đã bỏ thông tin bí mật

- Kiểm của Tester: `docs/logs/c2-v8-a5-kiem-bo-tri-2026-09-28.log`,
  `docs/logs/c2b-mep-v8-2026-09-28.log`, `docs/logs/sharpness_c2b_v8_20260928/`.
- `docs/logs/probe_20260928_150138.json`, `probe_20260928_151120.json`.
- `docs/logs/capture_20260928_*` (16 phiên, bản `--meta-copy`, không ảnh);
  `docs/logs/sharpness_20260928_*` (sáu thư mục D2/B3).
- Ảnh thô `data/raw/capture_20260928_*` (junction tới
  `D:\datascanner3d\raw`, ngoài Git).

## Ảnh gốc / ảnh bố trí / ảnh cấu hình đi kèm

Thư mục `docs/logs/c2-bo-tri-v8/20260928_1117/`: 21 ảnh gốc Samsung
SM-N975U1 4032×3024 (EXIF khớp tên tệp) và 1 bản nén 75 KB giữ nguyên (bản
gốc của nó ở `anh-goc-bo-sung/`), sổ `ghi-nhan-nguoi-dung.md`. SHA-256 trong log
kiểm của Tester.

| Nhóm | Tệp dùng làm bằng chứng | Ghi chú |
| --- | --- | --- |
| (a) bố trí trước đo | `20260928_122050`, `anh-goc-bo-sung/20260928_123449` | ảnh 11:32–11:58 là bố trí trước khi dời thước — lịch sử |
| (b) 250 mm trước đo | `20260928_115733`, `115742`, `121954` | `113407`, `113411`, `113425` không dùng (vạch 0 ở hộp giấy) |
| (c) ánh sáng chuẩn | `20260928_122101` (rèm gần mở), `115852` (rèm xa mở) | không đèn nào bật, màn hình tắt — NGƯỜI DÙNG XÁC NHẬN |
| G1 / G3 | `20260928_154007` / `154123` | chụp 15 s / 12 s trước G-a / G-b |
| G5 cuối đợt | `20260928_154425`, `154437`, `154455`, `154511` | ống kính ≈ 24,8 cm (ảnh từ trên, ống kính giữa ảnh); mốc chữ L còn |

**Khoảng cách 250 mm — giới hạn.** Không có ê-ke; thước 30 cm nằm trên bàn,
vạch 0 ở mặt khối gỗ, đầu kia đọc tại vạch bút chì dưới mặt ống kính (tâm
ống kính cao 62 mm). Ảnh chụp từ trên với ống kính ở giữa ảnh đọc ≈ 25,0
cm (11:57) và ≈ 24,8 cm (15:44); ảnh cả thước 12:19 đọc vạch bút chì
≈ 24,6 cm. Tester kết luận **≈ 246–250 mm**; người dùng ghi 250. D015 là
khoảng cách tạm, không ghi dung sai; C2 chỉ so tương đối trong đợt.

Hồ sơ camera (ngoài Git) — SHA-256 trước/sau `verified` ở mục "Kết quả
bước I/J".

## Thời gian chạy và số lần thử thực tế

A: 11:15–12:50 (bốn lần A5). Bo tắt 12:50–14:59. B–G: 15:01–15:45 (một
lần B hỏng do bo khởi động lại, chạy lại). I/J sau 15:50. Mọi lần thử và
lần không dùng giữ nguyên, ghi trong sổ ghi nhận.

## Số lần lặp mỗi đại lượng đo

5 ảnh mỗi phiên cho mọi đại lượng. Số trong bảng là trung vị 5 ảnh (T5
dùng trung bình theo định nghĩa), kèm min–max hoặc độ lệch chuẩn.

## Bảng giá trị

### A. Chọn preset cân bằng trắng

Hồ sơ chung VGA q10, `aec=0`, `agc=0`, `awb=1`, `awb_gain=1`,
`aec_value=783`, `agc_gain=8`. `m_ref = 169,6` (tham chiếu tự động,
spread 1,8–2,8 %). ROI `40,60,200,300`.

| Preset | Phiên | `mean` | R / G / B | d (O5 ≤ 15 %) | spread (O6 ≤ 15 %) | O7 bão hoà / tối | T5 | Kết quả |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 Sunny | `…_152048` | 161,6 | 150,4 / 167,3 / 161,8 | 4,70 % | 10,62 % | 0 / 0 % | 0,080 % | **ĐẠT** |
| 2 Cloudy | `…_152150` | 162,4 | 155,7 / 166,6 / 158,7 | 4,26 % | **6,76 %** | 0 / 0 % | 0,187 % | **ĐẠT — chọn** |
| 3 Office | `…_152228` | 160,7 | 139,9 / 167,9 / 178,0 | 5,25 % | 23,50 % | 0 / 0 % | 0,098 % | loại (O6) |
| 4 Home | `…_152301` | 156,9 | 125,7 / 167,0 / 187,9 | 7,47 % | 39,03 % | 0 / 0 % | 0,298 % | loại (O6) |

### B. Ma trận C2b

Cùng `aec_value=783`, `agc_gain=8`, `wb_mode=2`. Mép trái khối gỗ (giấy →
gỗ) ở x≈381 (VGA) và x≈477 (SVGA), tỷ lệ 1,252 ≈ 800/640 → cùng trường
nhìn, quy px SVGA về px-VGA bằng chia 1,25. Cửa sổ ±20 px không chứa mép
thước.

| Cấu hình | Phiên | `mean` ROI | T5 d (< 2 %) | Mép từng ảnh (px) | Mép trung vị | **Mép px-VGA** | bytes TB ± sd | `elapsed_ms` trung vị (min–max) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VGA q10 | `…_152150` | 162,4 | **0,187 %** | 1,58 / 1,53 / 1,53 / 1,57 / 1,59 | 1,57 | **1,57** | 10 556 ± 22 | 460 (335–730) |
| VGA q20 | `…_153631` | 170,6 | **0,286 %** | 2,12 / 1,94 / 1,94 / 1,94 / 2,04 | 1,94 | **1,94** | 8 736 ± 11 | 508 (266–846) |
| SVGA q10 | `…_153742` | 160,5 | **0,150 %** | 1,97 / 1,97 / 2,01 / 2,03 / 1,96 | 1,97 | **1,57** | 14 784 ± 30 | 704 (534–1 551) |
| SVGA q20 | `…_153824` | 159,2 | **0,092 %** | 2,00 / 2,12 / 2,00 / 2,07 / 2,10 | 2,07 | **1,65** | 12 438 ± 5 | 755 (326–3 017) |

Spread màu 5,9–6,8 %; O7 0 % mọi phiên. Bytes VGA q20 tính theo JPEG thật
(ảnh 3 có 1 678 byte thừa). Độ lặp lại của phép đo mép: cùng hồ sơ VGA q10,
D1 và G-a cách 20 phút cho 1,57 và 1,69 px.

### C. Chẩn đoán haze — rèm cuốn cửa sổ gần mở / đóng (cùng hồ sơ VGA q10)

| | Phiên | Ảnh bố trí | `mean` ROI | R / G / B | spread | Mép trung vị (px) | bytes TB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Rèm mở (G-a) | `…_154022` | `20260928_154007` | 167,1 | 161,3 / 171,3 / 160,5 | 6,67 % | 1,69 | 10 530 |
| Rèm đóng (G-b) | `…_154135` | `20260928_154123` | 140,4 | 139,6 / 142,8 / 129,3 | 9,78 % | 3,21 | 9 269 |
| Chênh | | | **−16,0 %** | B giảm mạnh nhất | +3,1 điểm | +90 % | −12,0 % |

Rèm xa (cửa kính, ~3 m) mở suốt đợt; không đèn nào bật.

## Ngưỡng đối chiếu và kết luận từng đại lượng

| Đại lượng | Ngưỡng (nguồn) | Đo được | Kết luận |
| --- | --- | --- | --- |
| Ảnh bố trí trước đo, đổi rèm, cuối đợt | `01_PLAN.md` Vòng 8 V8-T5R | đủ, commit trước B | **ĐẠT** |
| Preset đạt O5–O7 | `SPEC` 10.2, D032 | preset 1 và 2 | **ĐẠT** (V8-T6R) |
| T5 | `d < 2 %` | 0,187 / 0,286 / 0,150 / 0,092 % | **ĐẠT** bốn cấu hình |
| Controls và thanh ghi ổn định | `SCAN_SESSION.md` mục 5 | bảy khoá khớp sau áp = cuối | **ĐẠT** |
| Bề rộng mép đo được | V8-T7R | 5/5 ảnh mọi phiên | **ĐẠT** |
| Bề rộng mép — giá trị | không có ngưỡng trong C2b | 1,57–1,94 px-VGA | chỉ so tương đối |
| Haze | không có ngưỡng | bảng C | chỉ so sánh |
| Khoảng cách 250 mm | D015 (tạm, không dung sai) | ≈ 246–250 mm | ghi giới hạn |
| O3 (L07) | `SPEC` O3, D016 | chưa đo theo định nghĩa O3 | **CHƯA KẾT LUẬN** |

## Kết luận có thể rút ra

1. **Chuỗi bằng chứng bố trí đầy đủ**: ảnh trước đo đã commit trước khi đo,
   ảnh hai trạng thái rèm chụp ngay trước từng phiên, ảnh cuối đợt; vị trí
   mép trên ảnh camera không đổi suốt 3 giờ 17 phút.
2. **Cơ chế khoá hồ sơ lặp lại được** trong bố trí mới: preset 2 (Cloudy)
   lại cho spread nhỏ nhất (6,76 %), preset 3/4 lại trượt O6. Probe lại
   chạm trần phơi sáng (783), `agc_gain` 8.
3. **Quality 20 ở VGA làm mép rộng hơn 24 %** (1,94 so với 1,57 px), vượt
   nhiễu phép đo (~7 %) — khác Vòng 7 (khi đó không phát hiện khác biệt).
   Ở SVGA, q20 rộng hơn q10 khoảng 5 %, trong nhiễu.
4. **SVGA q10 và VGA q10 ngang nhau theo đơn vị vật** (1,57 px-VGA). Mép
   đợt này hẹp hơn Vòng 7 (≈ 1,6 so với ≈ 2,4–3,0 px) do vật và mép khác
   nhau — không so chéo hai bố trí.
5. **Đề xuất cấu hình chính: SVGA q20** — mép ngang nhóm tốt nhất trong
   nhiễu, mật độ lấy mẫu gấp 1,25 lần VGA, tệp nhỏ hơn SVGA q10 15,9 %.
   **Cấu hình phụ: VGA q10** — mép ngang nhóm tốt nhất, tệp 10,6 KB. VGA q20
   không chọn vì mép kém rõ rệt. Chọn theo số đợt này.
6. **Rèm gần có tác dụng rõ**: đóng rèm làm ảnh tối 16,0 %, kênh lam giảm
   mạnh nhất, spread 6,67 → 9,78 % (vẫn ≤ 15 %), mép đo rộng gần gấp đôi.

## Điều chưa thể kết luận

- **Khung ảnh hỏng và dữ liệu thừa sau JPEG không bị `capture_session.py`
  bắt** (chỉ kiểm giải mã, kích thước, trùng ảnh, timestamp). Nguyên nhân
  phía bo (bộ đệm khung) chưa rõ. Liên quan nghiệm thu "ảnh lỗi" của
  `SPEC` 9.8 ở các chặng sau; đề xuất Planner thêm kiểm khung trước C5.
- **`elapsed_ms`** dao động trong phiên (175–3 017 ms) lớn hơn chênh giữa
  cấu hình — nhiễu Wi-Fi, không dùng làm căn cứ.
- **VGA q20 sáng hơn** các cấu hình khác (`mean` 170,6 so với 159–167),
  giống xu hướng Vòng 7; chưa rõ do nén hay do ánh sáng tăng dần trong
  đợt (G-a 15:40 sáng hơn D1 15:21 khoảng 2,9 %).
- **Mép rộng gần gấp đôi khi đóng rèm**: có thể do hướng sáng đổi (viền
  sáng ở góc hộp giấy mất, tương phản giảm), không nhất thiết do haze.
- **Chất lượng vạch laser** ở q10/q20 — laser chưa đấu (C5/C6).
- **mm/px tuyệt đối**: thước 20 cm có trong khung nhưng chưa hiệu chuẩn;
  chỉ so px.
- **Khoảng cách chính xác** — xem giới hạn 246–250 mm ở trên.
- **O3/L07**, thanh ghi `0x5585` (đổi nhẹ ở vài phiên), firmware chưa đối
  chiếu commit.
- **Bản sao OneDrive đã đồng bộ lên máy chủ hay chưa** — Tester chỉ kiểm
  được thư mục trên máy.

## Bước thử tiếp theo

1. Reviewer soi đầu việc C2 (Vòng 8).
2. Khi sang C5: cấu hình chính `cam_SVGA_q20_20260928`; thử bề rộng vạch
   laser ở q10 và q20 trước khi chốt.
3. Planner cân nhắc kiểm khung hỏng / dữ liệu thừa sau EOI trong
   `capture_session.py` trước C5.
4. Sau khi chỉnh/đổi ống kính (D016), đo O3 theo định nghĩa để khép L07.

### Kết quả bước I/J

Người dùng chạy sau khi Tester xác nhận T5 (`03_TEST.md` "Vòng 8 (tiếp
2)"); Tester chạy thử vòng lệnh trên bản sao trước, rồi kiểm lại độc lập.

**I — `verified`.** Thay đúng chuỗi `"verified": null`; bản gốc lưu
`docs/logs/<hồ sơ>.json.bak` (không commit).

| Hồ sơ | `session_id` | `mean_drift_pct` | SHA-256 trước | SHA-256 sau |
| --- | --- | --- | --- | --- |
| `cam_VGA_q10_20260928_r01` | `capture_20260928_152150` | 0,187 | `99e5d156…` | `ed6f8083…` |
| `cam_VGA_q20_20260928` | `capture_20260928_153631` | 0,286 | `22fe2b76…` | `1976884b…` |
| `cam_SVGA_q10_20260928` | `capture_20260928_153742` | 0,150 | `be793b0e…` | `c596a157…` |
| `cam_SVGA_q20_20260928` | `capture_20260928_153824` | 0,092 | `60c8b93c…` | `5c32b27b…` |

Hash "sau" trùng đúng hash Tester dự kiến từ lần chạy thử (chỉ trường
`verified` đổi, CRLF giữ). Người dùng báo `--verify` đạt. Preset 1, 3, 4
giữ `verified: null`. Hồ sơ Vòng 7 và bốn `.bak` 27/09 không đổi.

**J — bản sao thứ hai.** `C:\Users\bestp\OneDrive\backup_scanner3d_20260928_1117`.
Ảnh thô 172 tệp (16 phiên, 60 JPEG), hồ sơ 11 tệp (7 hồ sơ + 4 `.bak`),
log/ảnh bố trí 155 tệp. Tester tính lại hash từ nguồn và `sha256sum -c`
trên bản sao: ảnh thô và hồ sơ khớp toàn bộ; log khớp trừ sổ ghi nhận (sửa
sau J, thêm sáu dòng ảnh G theo uỷ quyền người dùng) — bản sổ mới được chép
thêm vào bản sao với tên `ghi-nhan-nguoi-dung_sau-J.md`, hash khớp.

---

## Phụ lục A — Vòng 7 (25/09 và 27/09): số đo tham khảo, thiếu ảnh bố trí

Giữ nguyên nội dung hồ sơ Vòng 7 (chỉ hạ một cấp tiêu đề). Kết luận ĐẠT của phần này **không phải nghiệm thu** — xem khối đính chính ngay dưới (R05). Lời dẫn cũ của tệp:

> Tên tệp giữ đúng chỉ định của `handoff/2026-09-21_c2-camera-profile/01_PLAN.md`
> Vòng 4 mục 2. Tệp ghi **hai lần thử**: lần hiện hành (Vòng 7, 25/09 và
> 27/09) ở phần chính; lần thử Vòng 4 (23/09, CHƯA ĐẠT — ảnh lật ngược, ám
> lục) giữ nguyên ở phụ lục cuối tệp làm lịch sử, không xoá.
> Người thao tác bo: người dùng. Người lập hồ sơ: Tester (Claude Code).

**Kết quả tóm tắt (Vòng 7): ĐẠT.** Hai preset cân bằng trắng đạt cả ba
ngưỡng O5–O7, chọn preset 2 (Cloudy). T5 `d < 2 %` trên cả bốn cấu hình
ma trận. Bề rộng mép đo được 5/5 ảnh ở mọi phiên. Đề xuất cấu hình
**chính SVGA q20, phụ VGA q20**. Bốn hồ sơ ma trận đã đánh dấu
`verified`; ảnh thô và hồ sơ có bản sao thứ hai trên OneDrive, đối chiếu
hash khớp toàn bộ. Giới hạn còn mở: độ nét quang học O3/L07 (D016) và
chất lượng vạch laser ở quality 20 — xem "Điều chưa thể kết luận".

> **Đính chính 2026-09-27 (Tester Vòng 8).** Kết luận "ĐẠT" ở trên được
> ban hành khi **chưa có ảnh bố trí** chụp ngoài bằng điện thoại cho buổi
> 25/09 và 27/09 (mục "Ảnh gốc / ảnh dây / ảnh cấu hình đi kèm"), trong
> khi `01_PLAN.md` Vòng 4 bắt buộc ảnh đó. Reviewer Vòng 3 chặn vì điều
> này (R05). Vì vậy:
>
> - Số đo Vòng 7 (preset, T5, C2b, rèm) **giữ làm tham khảo**: đúng với
>   dữ liệu đã có, nhưng không chứng minh được khoảng cách 250 mm, gá,
>   đèn và rèm lúc đo.
> - Kết luận ĐẠT của Vòng 7 **không phải nghiệm thu** C2/C2b. Preset 2 và
>   đề xuất "chính SVGA q20, phụ VGA q20" chưa phải lựa chọn chốt.
> - Bốn hồ sơ đã `verified` (25/09–27/09), bốn `.bak` và bản sao OneDrive
>   27/09 giữ nguyên, không sửa. Đợt đo mới không dùng lại hồ sơ, số
>   `aec_value`/`agc_gain` hay toạ độ ROI/mép cũ.
> - Người dùng chọn làm lại toàn bộ khảo sát trong một bố trí mới có ảnh
>   bố trí (`01_PLAN.md` "Vòng 8 (điều chỉnh)"). Kết quả đợt mới sẽ thành
>   phần chính của tệp này; Vòng 7 chuyển thành lần thử tham khảo, không
>   xoá.

### Mục tiêu phép thử

Theo `01_PLAN.md` Vòng 7 hợp đồng V7-T8/V7-T9 và `docs/SPEC.md` mục 10.2:

1. Chọn một preset cân bằng trắng cố định (`wb_mode` 1–4) đạt O5 (lệch độ
   sáng so tham chiếu tự động ≤ 15 %), O6 (`channel_spread_pct` ≤ 15 %),
   O7 (tối/bão hoà bất kỳ kênh ≤ 1 % mỗi phía).
2. T5: năm ảnh cùng hồ sơ có `d = 100 × max|mᵢ − m̄| / m̄ < 2 %`, controls
   và thanh ghi ổn định đầu–cuối.
3. C2b: bốn cấu hình VGA/SVGA × quality 10/20, so bề rộng mép, kích thước
   tệp, thời gian `/capture`; chọn cấu hình chính/phụ có căn cứ.
4. Chẩn đoán haze: so rèm mở/rèm đóng, chỉ so sánh, không ngưỡng.

### Bo / camera / revision

- ESP32-S3 N16R8 có camera; sensor **OV3660, PID `0x3660`** — NGƯỜI DÙNG
  XÁC NHẬN trên Serial Monitor 115200 (`Camera PID: 0x3660`) ở cả buổi
  25/09 và 27/09.
- Firmware `firmware/esp32s3/CameraWebServerTest` (D013), board config
  `CAMERA_MODEL_ESP32S3_EYE`; phiên bản nạp CHƯA ĐỐI CHIẾU với commit
  (firmware không in phiên bản). Không nạp lại firmware trong phép thử.
- IP `192.168.31.9`.

### Nguồn cấp và kết nối

Cáp USB tới máy tính, Wi-Fi LAN. Laser **tắt và chưa đấu**; không Nucleo,
không bàn xoay, không `pair_capture` (`01_PLAN.md` Vòng 7 mục 6).

### Hệ điều hành, IDE, board package

Windows 11 Home, Git Bash trong VS Code, Python 3.11.9 trong `.venv`.
Board package theo `ENVIRONMENT.md` mục ESP32-S3.

### Mã nguồn / commit / thay đổi chưa commit

- Mã được kiểm: commit B7 `7cb659e75b3d43303bb255036fa7a86ce4a5aafb`
  (`03_TEST.md` Vòng 7: phần mềm 50/50 PASS).
- Commit PC lúc chụp: `af4c071` (25/09) và `1f0c265` (27/09), cây làm
  việc sạch; mã `pc/` không đổi giữa hai commit (chỉ hồ sơ/log Tester).

### Toàn bộ cài đặt build liên quan

Không build lại firmware. Cấu hình camera do các hồ sơ ở mục "Bảng giá
trị" quyết định.

### Cổng và tốc độ Serial

Serial Monitor 115200 chỉ để đọc PID và IP. Mọi số đo qua HTTP.

### Bước tái hiện

Theo `docs/procedures/quy-trinh-c2-camera-profile.md` bản Vòng 7:

**Buổi 1 — 25/09, 14:28–14:57 (chọn preset):**
1. A1/A2 — PID `0x3660`, IP.
2. B1 `--probe` → `aec_value = 783` (**đã kẹp** từ 784, L08),
   `agc_gain = 7` (từ `0x350a = 104`). Log
   `docs/logs/probe_20260925_142836.json`.
3. B2 tham chiếu tự động `capture_20260925_143009`; `status_start` và
   `status_end` đều `{'aec': 1, 'agc': 1, 'awb': 1, 'awb_gain': 1,
   'wb_mode': 0, '0x3406': 0}`.
4. B3 ROI tờ giấy trắng `40,40,200,200`; `m_ref = 177,1`.
5. C1 bốn hồ sơ `cam_VGA_q10_20260925.json`, `_r01`, `_r02`, `_r03`
   (`wb_mode` 1–4, `awb=1`, `awb_gain=1`, `aec=agc=0`). C2 bảng thanh ghi
   WB khớp.
6. D1/D2 bốn phiên `capture_20260925_144534` / `_144648` / `_144743` /
   `_144843`, đo O5–O7. D3 chọn preset 2.

**Buổi 2 — 27/09, 15:02–15:16 (ma trận C2b và rèm):**
7. F — ba hồ sơ mới và ba phiên: VGA q20 (`cam_VGA_q20_20260927`,
   `capture_20260927_150208`), SVGA q10 (`cam_SVGA_q10_20260927`,
   `capture_20260927_150505`), SVGA q20 (`cam_SVGA_q20_20260927`,
   `capture_20260927_150719`). Cùng `aec_value=783`, `agc_gain=7`,
   `wb_mode=2`.
8. G-a — **chụp lại VGA q10** bằng hồ sơ preset 2 (`cam_VGA_q10_20260925_r01`),
   rèm mở, phiên `capture_20260927_151514` (xem mục "Vì sao chụp lại VGA
   q10").
9. G-b — cùng hồ sơ, **chỉ đóng rèm gần** (cách vật 0,5 m; rèm thứ hai
   cách 3 m vẫn mở), phiên `capture_20260927_151646`.

Số đo do Tester chạy trên các phiên đã có (không chạm bo):
`pc/sharpness.py ... --roi 40,40,200,200 --out docs/logs --report-id
sharpness_c2b_vong7_20260927`; `pc/ruler_ticks.py <session> --edge X,Y0,Y1
--json docs/logs/c2b_mep_vong7_20260927/<cấu hình>.json`; bytes/`elapsed_ms`
từ `frames.csv`.

#### Vì sao chụp lại VGA q10 ở buổi 2

Giữa 25/09 và 27/09 **bố trí đã xê dịch** (khối gỗ dịch lên ~50 px, sang
phải ~20 px trên ảnh VGA) và **ánh sáng khác**: cùng hồ sơ, cùng ROI, ảnh
27/09 tối hơn 25/09 khoảng 11 % (mean 153,6 so với 173,2). Ma trận C2b
chỉ so được khi chỉ đổi framesize/quality, nên phiên VGA q10 của 25/09
**không** dùng trong ma trận; G-a thay nó. G-a chụp cách phiên F đầu tiên
13 phút, độ sáng ROI giấy khớp F trong 1,4 % (151,5 so với 153,6).

Việc chọn preset ở buổi 1 **không** phải làm lại: đó là phép so nội bộ
cùng ngày với tham chiếu tự động cùng ngày. Ngày 27/09 preset 2 vẫn giữ
màu: spread 8,2–8,9 % (≤ 15 %).

### Kết quả mong đợi

- Ít nhất một preset đạt O5–O7.
- T5 `d < 2 %`; bảy thanh ghi và 14 control ổn định đầu–cuối.
- Bốn cấu hình C2b `completed`, bề rộng mép đo được 5/5 ảnh mỗi phiên.
- Ảnh đúng chiều, màu trung thực.

### Kết quả quan sát thực tế

- **Cả 10 phiên `PASS`** (buổi 1: tham chiếu + bốn preset; buổi 2: ba F +
  G-a + G-b). Chín phiên dùng hồ sơ đều `status: completed`; phiên tham
  chiếu tự động không dùng hồ sơ nên không có trường `status`. 0 lần chụp
  lại, 0 lỗi kết nối, 0 nghi reset.
- Ảnh **đúng chiều** (khối gỗ ở đáy, thước chĩa lên) — lỗi L05 của lần
  thử 23/09 đã khắc phục.
- Bảng thanh ghi WB khớp preset ở cả `status_after_set` và `status_end`
  mọi phiên khoá; bảy thanh ghi hồ sơ khớp ở ba điểm (hồ sơ = sau áp =
  cuối phiên) trên bốn hồ sơ ma trận.
- Hai preset đạt O5–O7; bốn cấu hình ma trận đều đạt T5.

### Log nguyên văn đã bỏ thông tin bí mật

- `docs/logs/probe_20260925_142836.json`
- `docs/logs/capture_20260925_*` (năm phiên buổi 1),
  `docs/logs/capture_20260927_*` (năm phiên buổi 2) — bản sao
  `--meta-copy`, không gồm ảnh.
- `docs/logs/sharpness_20260925_*` (năm thư mục, buổi 1);
  `docs/logs/sharpness_c2b_vong7_20260927/` (năm phiên buổi 2).
- `docs/logs/c2b_mep_vong7_20260927/` — JSON bề rộng mép từng cấu hình.
- Ảnh thô `data/raw/capture_2026092{5,7}_*` (junction tới
  `D:\datascanner3d\raw`, ngoài Git).

### Ảnh gốc / ảnh dây / ảnh cấu hình đi kèm

Hồ sơ camera (`data/calibration/camera_profiles/`, ngoài Git), SHA-256
**trước khi** đánh dấu `verified`:

| Hồ sơ | SHA-256 |
| --- | --- |
| `cam_VGA_q10_20260925_r01.json` | `0f57d9657ac9f8ed4c285baff7c1411ecee5bbe9abc2868658bf9d97618d9a5d` |
| `cam_VGA_q20_20260927.json` | `5ddb571ed5a4de169ecfc5a560e3a09cfc90e17949caaee5d5799b3647a3616f` |
| `cam_SVGA_q10_20260927.json` | `494f89aae0d3f6b512e6e18a0a78e63bdb075f2b2783c42cd6cd38525d384121` |
| `cam_SVGA_q20_20260927.json` | `4b4fc1dbae0b1abfed1bd4208f18661ae0405dd076297afdb40c68a3883265c0` |

`session.json` của năm phiên buổi 2:

| Phiên | SHA-256 |
| --- | --- |
| `capture_20260927_151514` (VGA q10) | `063c5a5acd79c513b66d16e2cdc46ca422ee8f7269572b11db6cfaa9a2e94a79` |
| `capture_20260927_150208` (VGA q20) | `f8e0f00d60dbd3bbdb8a1d1b85b07938df8ae0ef50480b1bc0112f17107357df` |
| `capture_20260927_150505` (SVGA q10) | `ceeccc7b5db6a0ba666c1dfa02df9b3ca7564fc5093b5ab8ca25cf028c319183` |
| `capture_20260927_150719` (SVGA q20) | `512251afb99ba966683874525c82e8bc6527271edcd71f7f79ac4abcd03af089` |
| `capture_20260927_151646` (rèm đóng) | `935b6473d8eff5fd3635ee6f4a476f41bfb7a3f30a06fe34a50961d006437164` |

Chưa có ảnh bố trí chụp ngoài bằng điện thoại cho buổi 25/09 và 27/09.

### Thời gian chạy và số lần thử thực tế

Buổi 1 khoảng 30 phút, buổi 2 khoảng 15 phút. Các lần thử bị loại trước
đó (đêm 22/09 thiếu sáng; sáng 23/09 lắp nhầm OV5640; chiều 23/09 dừng ở
C3 vì ánh sáng đổi) đã xoá theo yêu cầu người dùng; lần thử 24/09 (hợp
đồng `awb=0`, L11) giữ nguyên làm bằng chứng trong `docs/logs/capture_20260924_*`.

### Số lần lặp mỗi đại lượng đo

5 ảnh mỗi phiên cho mọi đại lượng (R7 yêu cầu ≥ 3 — đạt). Số trong bảng
dưới là trung vị hoặc trung bình của 5 ảnh, kèm độ lệch chuẩn hoặc
min–max.

### Bảng giá trị

#### A. Chọn preset cân bằng trắng (buổi 1, 25/09)

Hồ sơ chung: VGA q10, `aec=0`, `agc=0`, `awb=1`, `awb_gain=1`,
`aec_value=783`, `agc_gain=7`. `m_ref = 177,1` (tham chiếu tự động,
spread 2,4 %). ROI `40,40,200,200`.

| Preset | `wb_mode` | `mean` | R / G / B | d (O5 ≤ 15 %) | spread (O6 ≤ 15 %) | O7 bão hoà / tối | Kết quả |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 Sunny | 1 | 171,6 | 157,7 / 178,6 / 171,6 | 3,11 % | 12,3 % | 0 / 0 % | **ĐẠT** |
| 2 Cloudy | 2 | 173,2 | 164,0 / 178,7 / 168,6 | 2,20 % | **8,7 %** | 0 / 0 % | **ĐẠT — chọn** |
| 3 Office | 3 | 171,5 | 147,7 / 180,1 / 190,6 | 3,16 % | 24,9 % | 0 / 0 % | loại (O6) |
| 4 Home | 4 | 164,6 | 129,0 / 176,1 / 199,1 | 7,06 % | 41,8 % | 0 / 0 % | loại (O6) |

Tương quan thanh ghi–ảnh (bằng chứng gain lên ảnh, đóng L11): R/B trong
thanh ghi 1,119 / 1,278 / 0,804 / 0,584; R/B trên ảnh 0,919 / 0,973 /
0,775 / 0,648 — cùng thứ tự `[2, 1, 3, 4]`. Biến thiên R/B ảnh giữa bốn
preset **50,1 %** (lần thử 24/09 với `awb=0`: 0,6 %).

#### B. Ma trận C2b (buổi 2, 27/09)

Cùng `aec_value=783`, `agc_gain=7`, `wb_mode=2`, `awb=1`, `awb_gain=1`.
ROI màu `40,40,200,200`. Mép trái khối gỗ đo bằng `--edge 385,260,340`
(VGA) và `--edge 485,325,425` (SVGA) — toạ độ SVGA xác định lại trên ảnh
SVGA thật, không nhân tỷ lệ; vị trí mép trên hai độ phân giải (VGA
`x≈391`, SVGA `x≈490`) cho tỷ lệ 1,253, khớp 800/640 = 1,250, nên hai độ
phân giải **cùng trường nhìn** và đổi được px SVGA sang đơn vị VGA bằng
cách chia 1,25.

| Cấu hình | Phiên | `mean` ROI | T5 d (< 2 %) | Mép từng ảnh (px) | Mép trung vị (px) | **Mép quy về px-VGA** | bytes TB ± sd | `elapsed_ms` trung vị (min–max) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VGA q10 | `…_151514` | 151,5 | **0,105 %** | 2,91 / 2,94 / 2,46 / 2,92 / 2,94 | 2,92 | **2,92** | 10 560 ± 707 | 562 (392–1 272) |
| VGA q20 | `…_150208` | 153,7 | **0,282 %** | 2,57 / 3,19 / 2,92 / 3,48 / 2,97 | 2,97 | **2,97** | 8 581 ± 68 | 866 (266–1 473) |
| SVGA q10 | `…_150505` | 150,8 | **0,122 %** | 3,03 / 3,20 / 2,89 / 2,88 / 3,11 | 3,03 | **2,42** | 14 687 ± 25 | 1 100 (365–1 601) |
| SVGA q20 | `…_150719` | 150,0 | **0,266 %** | 3,07 / 2,84 / 3,34 / 2,81 / 3,04 | 3,04 | **2,43** | 12 414 ± 24 | 1 362 (532–2 872) |

Spread màu trên cả bốn cấu hình 8,2–8,9 %; O7 0 % mọi phiên.

#### C. Chẩn đoán haze — rèm mở / rèm đóng (cùng hồ sơ VGA q10)

| | Phiên | `mean` ROI | R / G / B | spread | Mép trung vị (px) | bytes TB |
| --- | --- | --- | --- | --- | --- | --- |
| Rèm mở (G-a) | `…_151514` | 151,5 | 146,2 / 156,0 / 142,8 | 8,9 % | 2,92 | 10 560 |
| Rèm gần đóng (G-b) | `…_151646` | 127,6 | 126,4 / 130,5 / 115,9 | 11,8 % | 3,20 | 8 702 |
| Chênh | | **−15,8 %** | B giảm mạnh nhất | +2,9 điểm | +9,6 % | −17,6 % |

### Ngưỡng đối chiếu và kết luận từng đại lượng

| Đại lượng | Ngưỡng (nguồn) | Đo được | Kết luận |
| --- | --- | --- | --- |
| Preset đạt O5–O7 | `SPEC` 10.2, D032 | preset 1 và 2 đạt | **ĐẠT** (V7-T8) |
| T5 — độ lệch sáng nội bộ 5 ảnh | `01_PLAN.md` Vòng 4 mục 4.3: `d < 2 %` | 0,105 / 0,282 / 0,122 / 0,266 % | **ĐẠT** cả bốn cấu hình |
| Controls và thanh ghi ổn định | `SCAN_SESSION.md` mục 5 | bảy khoá khớp ở ba điểm, bốn hồ sơ | **ĐẠT** |
| Bề rộng mép đo được | `01_PLAN.md` Vòng 7 V7-T9 | 5/5 ảnh mọi phiên | **ĐẠT** |
| Bề rộng mép — giá trị | không có ngưỡng tuyệt đối trong C2b | 2,42–2,97 px-VGA | chỉ so tương đối, **không** kết luận ĐẠT/CHƯA ĐẠT |
| Haze | không có ngưỡng trong `SPEC` | xem bảng C | chỉ so sánh |
| Chất lượng quang học O3 (L07) | `SPEC` O3, D016 | chưa đo theo định nghĩa O3 | **CHƯA KẾT LUẬN** |

### Kết luận có thể rút ra

1. **Cơ chế khoá hồ sơ C2 hoạt động đúng trên bo thật**, cả màu: hợp đồng
   `awb=1` + preset thủ công (`0x3406=1`) cho gain lên ảnh, bốn preset cho
   bốn màu khác nhau đúng thứ tự thanh ghi. L05 và L11 đã khắc phục.
2. **Preset 2 (Cloudy)** cho màu gần trung tính nhất trong ánh sáng phòng
   thử (spread 8,7 %), và giữ được qua hai ngày ánh sáng khác nhau
   (8,2–8,9 % ngày 27/09).
3. **Quality 20 không làm mép kém đi so với quality 10** ở cả hai độ phân
   giải trong phạm vi phép đo: chênh 0,05 px (VGA) và 0,01 px (SVGA),
   nhỏ hơn nhiều so với dao động giữa các ảnh trong cùng phiên (khoảng
   0,3–0,9 px min–max). Tệp q20 nhỏ hơn q10 **19 %** (VGA) và **15 %**
   (SVGA). Đây là "không phát hiện được khác biệt", không phải "chứng
   minh bằng nhau".
4. **SVGA cho mép sắc hơn VGA khoảng 17 %** theo đơn vị vật (2,42 so với
   2,92 px-VGA). Nếu mờ chỉ do quang học (một độ rộng cố định trên mặt
   vật) thì px SVGA phải gấp 1,25 lần px VGA; đo được chỉ 1,04 lần, nên ở
   VGA độ rộng mép bị giới hạn một phần bởi mật độ lấy mẫu, và SVGA lấy
   thêm được chi tiết.
5. **Đề xuất cấu hình chính: SVGA q20** — mép sắc nhất (ngang SVGA q10),
   tệp nhỏ hơn SVGA q10 15 %. **Cấu hình phụ: VGA q20** — tệp nhỏ nhất
   (8,6 KB), dùng khi cần nhẹ/nhanh, chấp nhận mép kém hơn khoảng 22 %.
   Trong mỗi độ phân giải, q20 trội hơn q10 (cùng độ sắc, tệp nhỏ hơn),
   nên hai ứng viên thực sự chỉ còn SVGA q20 và VGA q20.
6. **Rèm gần có tác dụng rõ**: đóng rèm làm ảnh tối 15,8 %, kênh lam giảm
   mạnh nhất (ánh sáng ngày giảm, tỷ lệ đèn phòng tăng) nên spread tăng
   8,9 → 11,8 % (vẫn dưới 15 %), mép đo rộng hơn 9,6 %. Chỉ so sánh.

### Điều chưa thể kết luận

- **`elapsed_ms` không phân biệt được cấu hình.** Dao động trong một phiên
  lớn hơn chênh lệch giữa các phiên (ví dụ SVGA q20: 532–2 872 ms), và
  SVGA q20 có tệp nhỏ hơn SVGA q10 nhưng lại chậm hơn — ngược với thời
  gian truyền, tức nhiễu Wi-Fi lấn át. Không dùng làm căn cứ chọn; cần
  nhiều ảnh hơn hoặc mạng ổn định hơn nếu muốn so thời gian.
- **Bytes của VGA q10 (G-a) chia hai nhóm** (~10 050 và ~11 330, sd 707)
  trong khi độ sáng ROI giấy gần như không đổi (151,36–151,65). Nội dung
  ngoài ROI có thể đã đổi nhẹ giữa các ảnh; chưa rõ nguyên nhân, không suy
  đoán.
- **Nguyên nhân mép rộng hơn khi đóng rèm**: có thể do tương phản thấp hơn
  làm phép đo kém chính xác, không nhất thiết do haze; phép thử một biến
  này không tách được hai khả năng. Chỉ rèm gần được đóng.
- **Chất lượng vạch laser**: mọi phép đo dùng mép khối gỗ. Quality 20 nén
  nhiều hơn có thể ảnh hưởng vạch laser mảnh và sáng khác với mép vật —
  chưa thử vì laser chưa đấu (C5/C6).
- **mm/px tuyệt đối hôm nay**: không có thước trong vùng đo được, nên chỉ
  so tương đối; không quy mép ra mm.
- **O3 và L07 (độ nét quang học)** vẫn mở: D016 (ống kính gốc, tiêu điểm
  xa); phép đo mép khối gỗ ở đây không phải định nghĩa O3.
- **Thanh ghi `0x5585`** đổi nhẹ trong phiên preset 3 (25/09) và SVGA q20
  (27/09), nằm ngoài bảy khoá hồ sơ theo dõi; chưa rõ chức năng.
- Firmware trên bo CHƯA ĐỐI CHIẾU commit; phần mềm PC không tự kiểm được
  PID (chỉ qua Serial).

### Bước thử tiếp theo

1. Reviewer soi đầu việc C2 (`handoff/2026-09-21_c2-camera-profile/`).
2. Khi sang C5: dùng cấu hình chính SVGA q20 (`cam_SVGA_q20_20260927`);
   thử lại bề rộng vạch laser ở q10 và q20 trước khi chốt, vì kết luận
   "q20 không kém" mới chỉ đúng với mép vật.
3. Sau khi chỉnh/đổi ống kính (D016), đo O3 theo đúng định nghĩa để khép
   L07.

#### Kết quả bước I/J

Người dùng chạy 27/09 sau khi Tester xác nhận T5; Tester kiểm lại độc
lập, log `docs/logs/c2-verified-saoluu-2026-09-27.log`.

**I — `verified`.** Sửa bằng lệnh thay đúng chuỗi `"verified": null`
(giữ nguyên xuống dòng CRLF và mọi byte khác; Tester chạy thử trước trên
bản giả). Bản gốc lưu ở `docs/logs/<hồ sơ>.json.bak` (**không** commit —
hồ sơ ngoài Git theo kế hoạch mục 2).

| Hồ sơ | `session_id` | `mean_drift_pct` | SHA-256 trước | SHA-256 sau |
| --- | --- | --- | --- | --- |
| `cam_VGA_q10_20260925_r01` | `capture_20260927_151514` | 0,105 | `0f57d965…` | `ed430617…` |
| `cam_VGA_q20_20260927` | `capture_20260927_150208` | 0,282 | `5ddb571e…` | `cbb1384d…` |
| `cam_SVGA_q10_20260927` | `capture_20260927_150505` | 0,122 | `494f89aa…` | `2cc6fb35…` |
| `cam_SVGA_q20_20260927` | `capture_20260927_150719` | 0,266 | `4b4fc1db…` | `828f4def…` |

Hash đầy đủ trong log. Cả bốn: `validate_profile` hợp lệ, **chỉ trường
`verified` đổi** so với `.bak`, `registers_stable: true`; `--verify` trên
bo in `Ho so khop bo` cả bốn. Tám hồ sơ còn lại giữ `verified: null`.

**J — bản sao thứ hai.** `C:\Users\bestp\OneDrive\backup_scanner3d_20260927`
(OneDrive, đồng bộ lên máy chủ). Không dùng ổ C: vì C: và D: cùng một ổ
vật lý (`Get-Partition`: `DiskNumber 0`). Sao lưu **toàn bộ** ảnh thô (cả
phiên đạt lẫn phiên lỗi): 347/347 tệp, 205 JPEG; và 12/12 hồ sơ camera
(đã có `verified`). `sha256sum -c` khớp toàn bộ — Tester chạy lại độc lập.
`data/raw` (junction) không tính là bản sao.

---

## Phụ lục B — lần thử 23/09 (Vòng 4), CHƯA ĐẠT, giữ làm lịch sử

Phép thử này dùng hợp đồng hồ sơ trước Vòng 5 (`vflip=0`, `awb=0`, giá
trị phơi sáng chưa đo). Kết quả: cơ chế khoá ổn định nhưng ảnh lật ngược,
ám lục và tối — dẫn tới L05–L07 (`03_TEST.md` Vòng 4). Nội dung gốc giữ
nguyên dưới đây, chỉ hạ cấp tiêu đề.

Tên tệp giữ đúng chỉ định của `handoff/2026-09-21_c2-camera-profile/01_PLAN.md`
Vòng 4 mục 2; **phép thử thực tế chạy ngày 2026-09-23**, không phải 22/09.
Người thao tác bo: người dùng. Người lập hồ sơ: Tester (Claude Code).

Kết quả tóm tắt: **CHƯA ĐẠT**. Cơ chế khoá cấu hình chạy đúng và rất ổn
định, nhưng bộ giá trị mặc định đang khoá **mâu thuẫn với cấu hình mà
firmware đặt cho OV3660**: ảnh bị lật ngược 180°, ám lục và tối hơn phiên
đối chứng 2,85 lần. Chi tiết mục "Ngưỡng đối chiếu" và "Kết luận".

### Mục tiêu phép thử

T5 của `01_PLAN.md`: chụp 5 ảnh VGA quality 10 ở 250 mm với hồ sơ camera
cố định; xác nhận (a) `/status` và thanh ghi bắt buộc giữ nguyên suốt
phiên, (b) `d = 100 × max|mᵢ − m̄| / m̄ < 2 %` (kế hoạch Vòng 4 mục 4.3),
(c) ảnh dùng được cho ma trận C2b (B5) và đo bề rộng mép (B6).

### Bo / camera / revision

- ESP32-S3 N16R8 có camera.
- **Sensor: OV3660, PID `0x3660`** — NGƯỜI DÙNG XÁC NHẬN 2026-09-23 bằng
  dòng `Camera PID: 0x3660` in ra Serial Monitor 115200 khi khởi động
  (`CameraWebServerTest.ino:145`). Đây là lần đầu PID được xác nhận trực
  tiếp; các phiên trước chỉ suy từ hồ sơ. Xem "Điều chưa thể kết luận"
  về việc phần mềm PC không tự kiểm được PID.
- Firmware: sketch `firmware/esp32s3/CameraWebServerTest` (D013), board
  config `CAMERA_MODEL_ESP32S3_EYE`. Phiên bản nạp CHƯA ĐỐI CHIẾU với
  commit (firmware không in phiên bản) — hạn chế đã biết.
- IP trong phiên: `192.168.31.9`.

### Nguồn cấp và kết nối

Cáp USB từ máy tính tới bo; Wi-Fi LAN nội bộ. Laser **tắt và chưa đấu**
(`01_PLAN.md` mục 6). Không dùng Nucleo, không bàn xoay.

### Hệ điều hành, IDE, board package

Windows 11 Home, Git Bash trong VS Code; Python 3.11.9 trong `.venv`.
Board package theo `ENVIRONMENT.md` mục ESP32-S3 (Arduino-ESP32 3.3.11,
`PSRAM=opi`). Phép thử **không nạp lại firmware**.

### Mã nguồn / commit / thay đổi chưa commit

- Commit PC khi chạy: `8dcf22728001a20ad1c083b4797ed3dc46b51b5e`
  (nhánh `feat/c2-camera-profile`).
- **`dirty: true`** — cây làm việc có một thay đổi chưa commit lúc chụp:
  người dùng sửa `STATUS.md` bước B4, thêm `--out docs/logs` vào lệnh
  `sharpness.py` (một dòng tài liệu, không phải mã). Không ảnh hưởng số
  đo; ghi lại vì `session.json` đánh dấu phiên là "working tree BAN".
- Lệnh dùng: `pc/camera_profile.py --create`, `pc/capture_session.py
  --profile`, `pc/sharpness.py`.

### Toàn bộ cài đặt build liên quan

Không build lại firmware. Cấu hình camera do hồ sơ
`cam_VGA_q10_20260923.json` quyết định, ghi đủ ở mục "Bảng giá trị".

### Cổng và tốc độ Serial

Serial Monitor 115200: dùng ở B1 lấy IP và để đọc `Camera PID: 0x3660`.
Mọi số đo đi qua HTTP.

### Bước tái hiện

Theo `STATUS.md` mục "Quy trình khoá hồ sơ camera và khảo sát C2b":

1. **B1** — IP từ Serial Monitor: `192.168.31.9`.
2. **B2** — `.venv/Scripts/python.exe pc/camera_profile.py --create --host 192.168.31.9 --framesize VGA --quality 10`
   → 16 dòng `/control … OK`, ghi `data/calibration/camera_profiles/cam_VGA_q10_20260923.json`.
3. **B3** — `.venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --profile data/calibration/camera_profiles/cam_VGA_q10_20260923.json --count 5 --interval 2 --meta-copy docs/logs --note "C2 khoa ho so, VGA q10"`
   → phiên `capture_20260923_112304`, `Ket qua: PASS`.
4. **B4** — `.venv/Scripts/python.exe pc/sharpness.py capture_20260923_112304 --roi center --out docs/logs`
   → `docs/logs/sharpness_20260923_112443/`.
5. **B5 trở đi không chạy**: người dùng dừng sau khi thấy B4 bất thường.

Bố trí: giữ từ khảo sát quang học 17/09 (250 mm theo D015), khối gỗ
30×32×49 mm trên bệ, thước dựng trước mặt khối, đèn phòng. **Bố trí đã
được xác nhận đúng**: lật ảnh `img_0004.jpg` theo chiều dọc cho ra đúng
bố cục 17/09 — khối gỗ giữa khung trên bệ, thước dựng phía sau, chữ viết
tay đọc được.

### Kết quả mong đợi

- rc 0, `status: completed`, 5 JPEG 640×480, thanh ghi đầu–cuối trùng hồ sơ.
- `d < 2 %`.
- Ảnh **đúng chiều**, màu trung thực, đủ tương phản để B6 đo bề rộng mép
  và để so bốn cấu hình C2b.

### Kết quả quan sát thực tế

- Phiên `capture_20260923_112304`: rc 0, `verdict: PASS`,
  `status: completed`, 5/5 ảnh 640×480, 0 lần chụp lại, 0 lỗi kết nối,
  0 nghi reset, `/status doi start->end: khong doi (da doi chieu 76 truong)`,
  thời gian 8,2 s.
- Thanh ghi hồ sơ giữ nguyên tuyệt đối cả ba snapshot:
  `0x3500=7840`, `0x350a=31`, `0x3400=1643`, `0x3404=1459`.
- `d = 0,568 %` — dưới ngưỡng 2 %.
- Độ sáng **đủ**: `mean` ROI 56,16/255; `dark_frac` = 0; `sat_frac` = 0.
  Khác hẳn lần thử nhầm camera trước đó trong ngày.
- **Ảnh bị lật ngược 180°**: khối gỗ nằm ở đỉnh khung, thước chĩa xuống.
- **Ảnh ám lục nặng**: toàn khung phủ màu xanh lá, nền tường trắng hiện
  thành xanh.
- **Độ nét thấp**: `lap_var` trung vị 1,9 (min 1,8 / max 1,9),
  `grad_energy` 59 — so với 11,2 và 485 của phiên đối chứng 17/09 cùng
  bố trí, cùng khoảng cách.

### Log nguyên văn đã bỏ thông tin bí mật

- `docs/logs/capture_20260923_112304/` — bản sao hồ sơ phiên
  (`session.json`, `frames.csv`, `attempts.jsonl`, ba snapshot `/status`,
  `summary.txt`) do `--meta-copy` tạo; không gồm ảnh.
- `docs/logs/sharpness_20260923_112443/` — `per_image.csv`,
  `summary.json`, `summary.txt` của B4.
- Ảnh thô: `data/raw/capture_20260923_112304/` (junction tới
  `D:\datascanner3d\raw`, ngoài Git). **Chưa có bản sao thứ hai** — B8
  chưa chạy vì T5 chưa đạt.

### Ảnh gốc / ảnh dây / ảnh cấu hình đi kèm

| Tệp | SHA-256 |
| --- | --- |
| `img_0001.jpg` | `0d4529beb7fdde07cdc16f0fe3645ce449367e273831bb85ea1040a8febad2bf` |
| `img_0002.jpg` | `b824c354beeef405f3bbc3737ccd2190cb10e003648fbcb25b5465d6f5ba95d8` |
| `img_0003.jpg` | `b540b99a0406b51c8ff53c8074e7fa10e7e56826cbf66d24965e9773b2d3f6f3` |
| `img_0004.jpg` | `308896001c2180668aa3035fceaaf93749da4dc9ffe884bba5f95d94a2ca015d` |
| `img_0005.jpg` | `6930bacc0dc0e1a96b906236a183aaa4c64fc403c56d14f16bdd15cdeee4cc63` |
| `session.json` | `282846a8ea22d5603715f13851ae2ce5d93bf08bc1fc313b9c007cf2a81ef687` |
| `cam_VGA_q10_20260923.json` | `7935d67ffbb633cfdda8cf25f0ba04e52e54ba7f8a11a90825b182fd8ba92524` |

Chưa có ảnh bố trí chụp bằng điện thoại cho phiên 23/09; đối chiếu bố trí
dựa trên khung hình của chính ảnh chụp (xem "Bước tái hiện").

### Thời gian chạy và số lần thử thực tế

Phiên B3 chạy 8,2 s cho 5 ảnh (interval 2 s), 2 khung làm nóng bỏ đi.
Một lần thử hợp lệ trong ngày. Hai lần thử trước bị loại và đã xoá: đêm
22/09 (ánh sáng ban đêm) và sáng 23/09 (lắp nhầm camera OV5640 mới nhận);
không dùng làm bằng chứng.

### Số lần lặp mỗi đại lượng đo

5 ảnh cho `mean`/`lap_var` (R7 yêu cầu ≥ 3 — đạt). Chưa lặp ở mức cấu
hình: mới một phiên VGA q10 trong bốn phiên ma trận C2b.

### Bảng giá trị

**Cấu hình đang khoá** (`cam_VGA_q10_20260923.json`, `verified: null`)
so với cấu hình firmware tự đặt cho OV3660
(`CameraWebServerTest.ino:147-150` và khối `CAMERA_MODEL_ESP32S3_EYE`
dòng 162-164), và với `/status` phiên đối chứng 17/09:

| Biến | Firmware đặt cho OV3660 | `/status` 17/09 | Hồ sơ khoá 23/09 | Khớp? |
| --- | --- | --- | --- | --- |
| `vflip` | **1** (`// flip it back`) | 1 | **0** | **KHÔNG** |
| `brightness` | **1** | 1 | **0** | **KHÔNG** |
| `saturation` | **−2** | −2 | **0** | **KHÔNG** |
| `hmirror` | (không đặt) | 0 | 0 | có |
| `awb` | (không đặt) | 1 | 0 | khoá có chủ đích |
| `awb_gain` | (không đặt) | 0 | 0 | có |
| `wb_mode` | (không đặt) | 0 | 0 | có |
| `aec` / `agc` | (không đặt) | 1 / 1 | 0 / 0 | khoá có chủ đích |
| `aec_value` | (không đặt) | 490 | 490 | xem ghi chú |
| `agc_gain` | (không đặt) | 2 | 2 | xem ghi chú |
| `lenc`, `dcw` | (không đặt) | 1, 1 | 1, 1 | có |

*Ghi chú `aec_value`/`agc_gain`:* `/status` 17/09 báo 490 và 2 **trong khi
AEC/AGC đang bật** — đó là giá trị lưu trong `sensor_t.status`, không phải
giá trị camera đang dùng. Giá trị thật đọc ở thanh ghi: 17/09
`0x3500=12544` (→ 784 dòng) và `0x350a=248` (→ 15,50×); 23/09 khoá cho
`0x3500=7840` (→ 490 dòng) và `0x350a=31` (→ 1,94×).

**Số đo từng ảnh** (ROI trung tâm 320×240 tại `160,120`):

| # | Tệp | `mean` | `lap_var` | `dark_frac` | `sat_frac` | byte |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `img_0001.jpg` | 56,0303 | 1,824 | 0 | 0 | 8 621 |
| 2 | `img_0002.jpg` | 56,2554 | 1,816 | 0 | 0 | 8 571 |
| 3 | `img_0003.jpg` | 56,2262 | 1,885 | 0 | 0 | 8 542 |
| 4 | `img_0004.jpg` | 55,8387 | 1,855 | 0 | 0 | 8 594 |
| 5 | `img_0005.jpg` | 56,4382 | 1,871 | 0 | 0 | 8 526 |

- `m̄` = **56,1578**; độ lệch chuẩn giữa 5 ảnh = **0,2296**;
  `d` = **0,568 %**.
- `lap_var` trung vị 1,9; `grad_energy` trung vị 59.

**So với phiên đối chứng 17/09** (`capture_qh_250mm`, cùng bố trí, cùng
250 mm, AEC/AGC/AWB bật, cùng ROI trung tâm):

| Đại lượng | 17/09 (tự động) | 23/09 (khoá) | Tỷ lệ |
| --- | --- | --- | --- |
| `mean` | 160,4 | 56,2 | 2,85× tối hơn |
| `lap_var` trung vị | 11,2 | 1,9 | 5,9× thấp hơn |
| `grad_energy` trung vị | 485 | 59 | 8,2× thấp hơn |

### Ngưỡng đối chiếu và kết luận từng đại lượng

| Đại lượng | Ngưỡng (nguồn) | Đo được | Kết luận |
| --- | --- | --- | --- |
| Thanh ghi hồ sơ giữ nguyên trong phiên | `01_PLAN.md` T5; `SCAN_SESSION.md` mục 5 | ba snapshot trùng khít, 76 trường không đổi | **ĐẠT** |
| `status`/rc của phiên | `01_PLAN.md` Vòng 4 mục 4.2 | rc 0, `completed`, 5/5 ảnh, 0 retry, 0 reset | **ĐẠT** |
| Độ sáng ảnh dùng được | `01_PLAN.md` Vòng 4 mục 4.3 (`m̄ > 0`) | `mean` 56,16; `dark_frac` 0; `sat_frac` 0 | **ĐẠT** |
| `d < 2 %` | `01_PLAN.md` Vòng 4 mục 4.3 | 0,568 % | **ĐẠT** |
| Ảnh đúng chiều | firmware đặt `vflip=1` cho OV3660 | ảnh lật ngược 180° | **CHƯA ĐẠT** |
| Màu trung thực | `/status` 17/09 `saturation=-2`, `awb=1` | ám lục toàn khung | **CHƯA ĐẠT** |
| Độ nét dùng được cho B6 | `01_PLAN.md` Vòng 4 mục 4.6 | `lap_var` 1,9 so với 11,2 đối chứng | **CHƯA ĐẠT** |
| Bề rộng mép (B6) | `01_PLAN.md` Vòng 4 mục 4.6 | chưa đo | **CHƯA CHẠY** |
| Ma trận C2b bốn cấu hình | `01_PLAN.md` Vòng 4 mục 5 | mới 1/4 phiên, đã dừng | **CHƯA CHẠY** |

### Kết luận có thể rút ra

1. **Cơ chế khoá cấu hình của C2 hoạt động đúng trên bo thật.** 16 lệnh
   `/control` được áp, đọc lại `/status`, đối chiếu hồ sơ đã lưu, theo
   dõi thanh ghi đầu–cuối: không sai sót; 76/76 trường `/status` không
   đổi suốt phiên; `d = 0,568 %` cho thấy ảnh rất ổn định giữa các lần
   chụp. Phần này là bằng chứng tốt cho C2.
2. **`DEFAULT_CONTROLS` mâu thuẫn với cấu hình firmware cho OV3660.**
   Firmware đặt `vflip=1` (chú thích nguyên văn `// flip it back` — cảm
   biến gắn ngược trên bo), `brightness=1`, `saturation=-2`. Hồ sơ khoá
   cả ba về 0, phá đúng phần firmware đã chỉnh. Hậu quả trực tiếp và
   quan sát được: ảnh lật ngược 180°.
3. **Tắt cân bằng trắng mà không có cấu hình thay thế gây ám lục.**
   `awb=0` cùng `awb_gain=0` và `wb_mode=0` để camera chạy với hệ số kênh
   mặc định; nền tường trắng hiện thành xanh lá.
4. **Độ nét chưa kết luận được nguyên nhân.** `lap_var` thấp 5,9 lần so
   với đối chứng, nhưng ảnh tối hơn 2,85 lần và ám màu nặng — cả hai đều
   kéo tương phản xuống, mà `lap_var`/`grad_energy` phụ thuộc tương phản.
   Vạch thước và chữ viết tay vẫn đọc được trong ảnh, nên chưa có dấu
   hiệu mất nét cơ học. Phải sửa xong chiều ảnh, màu và độ sáng rồi đo
   lại mới tách được phần nào do quang học (D016 đã ghi ống kính tiêu
   điểm xa, mờ ≈ 1,2–1,4 mm ở mặt vật).
5. **Bố trí của người dùng đúng**, không phải nguyên nhân: lật ảnh theo
   chiều dọc cho ra đúng bố cục 17/09.

### Điều chưa thể kết luận

- Giá trị `aec_value`/`agc_gain` nào cho độ sáng tương đương 17/09: suy
  `aec_value ≈ 784` từ `0x3500` là phép suy luận **chưa kiểm chứng**;
  `agc_gain` chưa biết map từ thang `/control` 0–30 sang thanh ghi
  `0x350a` (`sensor.h` chỉ ghi dải, không ghi công thức; driver
  `ov3660.c` đã biên dịch sẵn, không có nguồn trên máy).
- Ánh sáng phòng 23/09 so với 17/09: chưa đo. Ảnh 23/09 chỉ tối hơn
  2,85× trong khi phơi sáng khoá thấp hơn 12,8× so với lúc tự động —
  chênh lệch này gợi ý phòng sáng hơn hôm 17/09, nhưng không có số đo.
- Phần độ nét do quang học so với phần do tương phản thấp: chưa tách.
- `wb_mode`/`awb_gain` nào cho màu đúng khi `awb=0`: chưa thử.
- **Phần mềm PC không tự kiểm được PID sensor.** `camera_profile.py`
  ghi cứng `sensor: "OV3660 PID 0x3660"` trong `build_profile_dict()`;
  `/status` của firmware dùng chung một nhánh thanh ghi cho OV5640 và
  OV3660 (`app_httpd.cpp:439`) và không in PID. PID chỉ đọc được qua
  Serial Monitor. Vì vậy một hồ sơ tạo bằng camera khác vẫn "hợp lệ" —
  đây chính là điều đã xảy ra ở lần thử bị loại sáng 23/09.
- Toàn bộ C2b (ma trận bốn cấu hình), B5a, B6, B7, B8: chưa chạy.

### Bước thử tiếp theo

Thuộc quyết định của Planner (xem `03_TEST.md` Vòng 4 mục 3, lỗi L05–L07).
Đề xuất của Tester, chưa được duyệt:

1. `DEFAULT_CONTROLS` lấy `vflip=1`, `brightness=1`, `saturation=-2` cho
   khớp firmware OV3660, thay vì đặt về 0.
2. Chọn cấu hình cân bằng trắng cố định thay cho `awb_gain=0`/`wb_mode=0`,
   rồi kiểm bằng ảnh nền trắng.
3. Đo trên bo để chốt `aec_value`/`agc_gain`: bật `aec=1`/`agc=1` cho
   camera tự chỉnh trong đúng ánh sáng sẽ dùng, đọc `0x3500`/`0x350a`;
   quét `agc_gain` 0–30 với `agc=0` và đọc `0x350a` để lập bảng map.
4. Sau khi ba việc trên xong, chụp lại B3 và **so `lap_var` với mốc 11,2
   của `capture_qh_250mm`** trước khi chạy B5 — nếu vẫn thấp rõ rệt thì
   đó là vấn đề quang học thuộc D016, không phải cấu hình.
