# Quy trình khoá hồ sơ camera và khảo sát C2b — Vòng 8, đợt đo mới có ảnh bố trí, CHƯA CHẠY, chờ người dùng

Quy trình này thay bản Vòng 7. Nó hướng dẫn **một đợt đo trọn vẹn, làm
lại từ đầu trong một bố trí mới**: dựng bố trí, chụp ảnh bố trí bằng điện
thoại và chờ Tester kiểm **trước khi đo**, rồi probe → ảnh tham chiếu →
bốn preset → T5 → ba cấu hình C2b → cặp rèm mở/đóng → so sánh → `verified`
→ sao lưu. Kế hoạch: `handoff/2026-09-21_c2-camera-profile/01_PLAN.md`
mục "Vòng 8 (điều chỉnh)".

### Vì sao làm lại

Các vòng trước đã sửa những lỗi sau; quy tắc của chúng vẫn áp dụng trong
các bước dưới:

- **L05–L07 (Vòng 5):** khoá đúng chiều ảnh (`vflip=1`), bốn giá trị hiệu
  chỉnh phải truyền rõ, có `--probe` đề xuất mức phơi sáng.
- **L08 (Vòng 6):** bo kẹp `aec_value` ở `783` trên VGA/SVGA — luôn dùng
  số probe in ra (đã kẹp nếu có chữ "DA KEP").
- **L09 (Vòng 6):** sáu chỗ hướng dẫn thiếu rõ (dấu `< >`, cách đọc ROI,
  cỡ giấy, bước chụp thử bố trí, chọn mép khối gỗ). Chỉ dẫn xoá phiên thử
  thêm ở vòng đó **bị bỏ ở Vòng 8** (R04 dưới đây).
- **L10/L11 (Vòng 6–7):** hồ sơ dùng `awb=1`, `awb_gain=1`, `wb_mode` 1–4
  (gain cố định theo preset, `0x3406=1`); probe đưa camera về tự động
  trước ảnh tham chiếu.

Vòng 8 xử lý hai phát hiện `Chặn` của Reviewer (`04_REVIEW.md` Vòng 3):

- **R04 — không xoá ảnh thô.** Bản cũ bảo xoá phiên chụp thử bố trí. Từ
  nay **không có lệnh xoá nào**: mỗi lần chụp lại dùng một session ID mới
  (script tự đặt theo giờ), lần không đạt vẫn giữ nguyên và ghi lý do.
- **R05 — thiếu ảnh bố trí.** Các buổi 25/09 và 27/09 không có ảnh chụp
  bố trí bằng điện thoại, nên không chứng minh được khoảng cách 250 mm,
  gá, đèn, rèm lúc đo. Người dùng đã chọn coi như không có ảnh hai buổi
  đó, nên **làm lại cả khảo sát preset lẫn ma trận C2b và cặp rèm** trong
  một bố trí mới, có ảnh bố trí chụp **trước** khi đo, lúc đổi rèm và
  cuối đợt.

**Dữ liệu cũ là lịch sử, giữ nguyên:** mọi ảnh thô, log, hồ sơ camera
23/09–27/09, bốn hồ sơ đã `verified` (25/09, 27/09), bốn tệp
`docs/logs/cam_*.json.bak` và bản sao OneDrive 27/09. Không xoá, không
sửa, không đổi tên, **không dùng lại hồ sơ cũ nào** cho đợt này (kể cả
hồ sơ đã `verified`), không dùng lại số `aec_value=783`/`agc_gain=7`,
toạ độ ROI hay toạ độ mép của lần trước. Preset và cấu hình chính/phụ
chọn lại theo số đo mới, không mặc định giữ Cloudy hay SVGA q20.

### Mã đợt đo `<run_id>` và thư mục của đợt

- `<run_id>` là ngày giờ bắt đầu đợt đo, dạng `YYYYMMDD_HHMM`, ví dụ
  `20260928_0915`. Tạo ở bước A3 và dùng cho mọi ghi chú của đợt.
- `<ngay>` là ngày chạy đợt đo, dạng `YYYYMMDD` (8 số đầu của
  `<run_id>`). Mọi session (`capture_<ngay>_HHMMSS`) và hồ sơ
  (`cam_..._<ngay>...json`) do script tự mang ngày này.
- Ảnh điện thoại và sổ ghi nhận của đợt nằm trong
  `docs/logs/c2-bo-tri-v8/<run_id>/`.
- Nếu đợt đo kéo qua nửa đêm, các session sau 00:00 mang ngày mới: ghi
  rõ trong sổ ghi nhận và báo Tester (bước J phải chép cả hai ngày).

### Quy tắc bảo toàn dữ liệu — áp dụng cho mọi bước

- **Không xoá, không đổi tên, không ghi đè** bất kỳ tệp/thư mục nào trong
  `data/raw/`, `data/calibration/`, `docs/logs/`, kể cả phiên FAIL, phiên
  thử, ảnh điện thoại chụp hỏng.
- Chụp lại = chạy lại đúng lệnh; script tự đặt ID mới theo giờ. Không
  dùng `--session-id` hay `--id` tự đặt trong đợt này.
- Script báo `da ton tai` / `khong ghi de` nghĩa là nó đã **từ chối** ghi
  đè — dữ liệu cũ vẫn nguyên. Chờ vài giây rồi chạy lại để có ID mới.
- Mỗi lần thử không đạt hoặc bị bỏ: ghi một dòng vào bảng "Các lần thử
  và lần không đạt" của sổ ghi nhận (giờ, bước, session ID, lý do).

### Điều kiện và thời gian

Bo S3 đã nạp `CameraWebServerTest` (D013), camera OV3660. **Laser không
đấu, không cấp nguồn**; C2 không chạy động cơ/HOME. Khoảng cách làm việc
250 mm (D015). Thời gian: khoảng 2–2,5 giờ cho A–H (kể cả chờ Tester
kiểm ảnh bố trí ở A8); I/J làm sau khi Tester xác nhận T5, thêm khoảng
20–30 phút. Chọn thời điểm ánh sáng phòng giữ ổn định được suốt A5–G
(tránh lúc chiều tối khi trời đang tối dần).

**Chuẩn bị trước:**
- Mảnh giấy trắng phẳng, không chữ/hoa văn, khoảng 8×10 cm (ở 250 mm
  trường nhìn chỉ khoảng 199×149 mm nên không cần cả tờ A4).
- Thước dây hoặc thước thẳng dài ≥ 30 cm để đo 250 mm.
- Băng dính giấy để đánh dấu mốc vị trí chân gá camera và khối gỗ.
- Điện thoại chụp ảnh bố trí, **tắt đèn flash**; cáp USB nối điện thoại
  với máy tính (để chép ảnh gốc).

### A. Thiết bị, bố trí mới và cổng ảnh bố trí — TRƯỚC khi đo

**A1. Xác nhận cảm biến qua Serial Monitor — BẮT BUỘC trước mọi bước khác.**
- Ở đâu: Arduino IDE, cửa sổ Serial Monitor (Tools → Serial Monitor),
  tốc độ **115200**.
- Làm gì: cắm cáp USB bo S3, mở Serial Monitor, nhấn nút RESET trên bo
  (nếu cần), đọc các dòng in ra lúc khởi động.
- Thấy gì là đúng: có dòng nguyên văn `Camera PID: 0x3660` (không phải
  `0x5640` hay giá trị khác). Ghi lại cả dòng địa chỉ IP in ra sau đó
  (dạng "Camera Ready! Use 'http://<ip>' to connect").
- Nếu sai: PID khác `0x3660` hoặc không thấy dòng PID — DỪNG, không làm
  tiếp, gửi Tester nguyên văn Serial Monitor. Module FD5640/OV5640 không
  được lẫn vào C2.

**A2. Ghi lại địa chỉ IP.**
- Ở đâu: dòng Serial Monitor ở A1.
- Làm gì: ghi địa chỉ, gọi là `<IP>` trong các lệnh dưới.
- Thấy gì là đúng: mở trình duyệt tới `http://<IP>/status` thấy một khối
  chữ JSON dài (có `"framesize"`, `"aec"`...).
- Nếu sai: trình duyệt không mở được — đổi Wi-Fi có thể đổi IP; đọc lại
  Serial Monitor, không đoán IP cũ.

**A3. Tạo mã đợt đo, thư mục đợt đo và sổ ghi nhận.**
- Ở đâu: Git Bash trong VS Code, thư mục gốc `/d/scanner3d` (prompt có
  `/d/scanner3d`).
- Làm gì:
  1. In mã đợt đo:
     ```
     date +%Y%m%d_%H%M
     ```
     Số in ra (ví dụ `20260928_0915`) là `<run_id>` — ghi lại.
  2. Tạo thư mục đợt đo, thay `<run_id>`:
     ```
     mkdir -p docs/logs/c2-bo-tri-v8
     mkdir docs/logs/c2-bo-tri-v8/<run_id>
     ```
  3. Tạo sổ ghi nhận: trong VS Code, khung Explorer bên trái, mở
     `docs/logs/c2-bo-tri-v8/<run_id>`, bấm chuột phải vào thư mục đó →
     `New File`, gõ tên `ghi-nhan-nguoi-dung.md`, Enter. Dán mẫu dưới đây
     vào tệp, thay `<run_id>`, điền dòng "Người thao tác", rồi `Ctrl+S`.
     Các mục còn lại điền dần theo từng bước.
     ```
     # Ghi nhận đợt đo C2 — <run_id>

     Mọi nội dung trong tệp này là THÔNG TIN NGƯỜI DÙNG XÁC NHẬN, không phải
     số đọc từ ảnh. Tester đánh dấu riêng điều nào thấy được trong ảnh.

     Người thao tác:
     Giờ bắt đầu dựng bố trí:

     ## Camera, gá, vật
     - Gá camera (loại, cao bao nhiêu):
     - Vật: khối gỗ (mặt nào hướng về camera):
     - Giấy trắng (kích thước, đặt ở đâu so với khối gỗ):
     - Thước dựng trong khung camera (có/không, đặt ở đâu):
     - Mốc băng dính đã dán (dán ở đâu):

     ## Khoảng cách 250 mm
     - Đo từ: mặt trước ống kính camera   tới: mặt trước khối gỗ
     - Dụng cụ đo:
     - Số đọc (mm, ghi đúng số đọc được):
     - Người đo:                 Giờ đo:
     - Tên tệp ảnh điện thoại chụp phép đo:
     - Đo lại cuối đợt (bước G5) — số đọc, giờ:

     ## Ánh sáng — trạng thái chuẩn của đợt đo
     - Đèn đang BẬT (tên/vị trí so với bàn đo):
     - Đèn đang TẮT:
     - Cửa sổ/rèm (mỗi cái: vị trí, khoảng cách ước tới camera, mở hay đóng):
     - Rèm sẽ ĐÓNG ở bước G:

     ## Các lần thử và lần không đạt
     | Giờ | Bước | Session ID hoặc tên tệp | Lý do loại / ghi chú |
     | --- | --- | --- | --- |

     ## Ảnh điện thoại
     | Tên tệp gốc | Bước | Nội dung / góc chụp | Giờ chụp |
     | --- | --- | --- | --- |
     ```
- Thấy gì là đúng: lệnh `mkdir` thứ hai không in gì; trong Explorer của
  VS Code có `docs/logs/c2-bo-tri-v8/<run_id>/ghi-nhan-nguoi-dung.md`.
- Nếu sai: `mkdir: cannot create directory ... File exists` — thư mục mã
  đó đã có từ trước. Không dùng lại, không xoá: chờ sang phút sau, chạy
  lại lệnh `date` để lấy `<run_id>` mới rồi làm lại bước 2.

**A4. Dựng bố trí mới và đo 250 mm.**
- Ở đâu: bàn đo.
- Làm gì:
  1. Đặt gá camera và khối gỗ; mặt trước khối gỗ hướng thẳng vào camera.
  2. Đặt thước đo từ **mặt trước ống kính** (vòng ngoài cùng của ống
     kính) tới **mặt trước khối gỗ**, chỉnh vị trí khối gỗ đến khi số đọc
     là 250 mm.
  3. Dán băng dính đánh dấu mép chân gá và hai góc đáy khối gỗ trên mặt
     bàn — đây là mốc để đối chiếu cuối đợt rằng không có gì xê dịch.
  4. Dựng mảnh giấy trắng **cùng mặt phẳng** với mặt trước khối gỗ (lệch
     không quá 1 cm), đặt **bên cạnh** khối gỗ, không che khối gỗ; thước
     dựng (nếu dùng) không che mép khối gỗ. Dán/kẹp cố định giấy.
  5. Chọn trạng thái ánh sáng chuẩn giữ được suốt đợt: đèn nào bật, rèm
     nào mở. Chọn trước một rèm sẽ đóng ở bước G.
  6. Ghi vào sổ ghi nhận mục "Camera, gá, vật", "Khoảng cách 250 mm" (số
     đọc thật, người đo, giờ) và "Ánh sáng". **Không** chép lại khoảng
     cách rèm của lần 27/09 — ước lại cho bố trí này.
  7. **Chưa cất thước đo**: để nguyên cho ảnh ở A6(b).
- Thấy gì là đúng: số đọc trên thước là 250 mm; giấy, khối gỗ, mốc băng
  dính cố định; sổ ghi nhận đã có ba mục trên.
- Nếu sai: không chỉnh được đúng 250 mm (gá/bàn không cho phép) — ghi
  đúng số đọc thật vào sổ và báo Tester trước khi làm tiếp; không ghi
  "250" khi thước đọc số khác.

**A5. Chụp thử bằng camera S3 để kiểm khung hình — mỗi lần thử một ID mới, KHÔNG xoá lần nào.**
- Ở đâu: Git Bash, thư mục gốc repo. Trước khi chạy: **cất thước đo**,
  điện thoại và tay ra khỏi khung camera (thước dựng cố định của bố trí
  thì giữ nguyên).
- Làm gì, thay `<IP>` và `<run_id>`:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host <IP> --framesize VGA --count 1 --meta-copy docs/logs --note "C2 Vong 8, anh thu bo tri, dot <run_id>"
  ```
  Đọc dòng `Phien: capture_YYYYMMDD_HHMMSS` ở đầu output — đó là
  `<session_id_thu>`. Mở `data/raw/<session_id_thu>/img_0001.jpg` bằng
  Paint.
- Thấy gì là đúng: output có `Ket qua: PASS` và dòng `Da chep ho so phien
  (khong gom anh) vao: ...`; ảnh đạt đủ năm điểm: (1) giấy trắng nằm trọn
  trong khung; (2) giấy không che khối gỗ, thước dựng không che mép khối
  gỗ; (3) không có bóng đổ hay chỗ loá trên giấy; (4) ảnh đúng chiều
  (khối gỗ ở phía dưới khung, không lật ngược); (5) không còn thước đo
  tạm, điện thoại hay tay trong khung. Ghi `<session_id_thu>` đạt vào
  bảng "Các lần thử" với ghi chú "đạt".
- Nếu sai:
  - Ảnh không đạt một điểm: ghi `<session_id_thu>` và điểm không đạt vào
    bảng "Các lần thử", chỉnh bố trí, chạy lại **đúng lệnh trên** — script
    tự đặt ID mới. Không xoá phiên cũ. Nếu đã xê dịch gá hoặc khối gỗ khi
    chỉnh, đo lại 250 mm như A4 và sửa mục khoảng cách trong sổ.
  - `Ket qua: FAIL - ...`, hoặc dòng bắt đầu bằng `FAIL:` (ví dụ `FAIL:
    khong doc duoc /status luc bat dau: loi ket noi ...`): ghi ID và lý do
    in ra vào bảng, mở `http://<IP>/status` trong trình duyệt kiểm bo còn
    phản hồi, rồi chạy lại lệnh. Log lần lỗi nằm ở
    `data/raw/<session_id_thu>/session.json` (lỗi ngay từ đầu thì không có
    bản chép trong `docs/logs/`) — giữ nguyên.
  - `Thu muc phien khong dung duoc, khong ghi de: da ton tai` hoặc `Thu
    muc --meta-copy cho phien nay da ton tai, khong ghi de`: hai lần chạy
    rơi vào cùng một giây. Script đã từ chối, dữ liệu cũ nguyên; chờ vài
    giây rồi chạy lại.

**A6. Chụp ảnh bố trí bằng điện thoại — nhóm ảnh "trước đo".**
- Ở đâu: điện thoại, đứng ngoài bàn đo; **tắt flash**; không dùng bộ lọc,
  không cắt/chỉnh ảnh trên điện thoại.
- Làm gì, chụp đủ ba nhóm (mỗi nhóm có thể nhiều ảnh, nhiều góc):
  - (a) **Toàn cảnh bố trí:** thấy trong cùng khung camera S3 và gá, khối
    gỗ, giấy trắng, thước dựng (nếu có) và các mốc băng dính. Chụp từ bên
    cạnh và từ phía sau camera.
  - (b) **Phép đo 250 mm:** đặt lại thước đo từ mặt trước ống kính tới
    mặt khối gỗ; chụp một ảnh thấy cả đoạn thước, một ảnh cận đầu thước ở
    ống kính (thấy vạch 0 chạm mặt ống kính), một ảnh cận đầu thước ở mặt
    khối gỗ (đọc được số). Chụp xong **cất thước đo** ra khỏi khung camera.
  - (c) **Ánh sáng:** thấy các đèn đang bật và cửa sổ/rèm ở trạng thái
    chuẩn, cùng vị trí của chúng so với bàn đo.
- Thấy gì là đúng: mở từng ảnh trên điện thoại, phóng to: đọc được số
  trên thước ở (b); thấy đủ các vật ở (a) và nguồn sáng/rèm ở (c).
- Nếu sai: thiếu góc hoặc ảnh mờ — chụp bổ sung **ngay**, khi bố trí còn
  nguyên. Ảnh hỏng không xoá trên điện thoại; vẫn chép sang máy ở A7 và
  ghi "hỏng" trong bảng ảnh.

**A7. Chép ảnh gốc từ điện thoại sang thư mục đợt đo — giữ nguyên tên, đuôi, EXIF.**
- Ở đâu: cáp USB điện thoại–máy tính; Windows Explorer (Win+E).
- Làm gì:
  1. Hiện đuôi tệp: Explorer → menu `View` (Xem) → `Show` (Hiện) → tích
     `File name extensions` (Phần mở rộng tên tệp).
  2. Mở thư mục ảnh trên điện thoại:
     - Android: cắm cáp, trên điện thoại chọn chế độ USB **Truyền tệp**
       (File transfer). Explorer → `This PC` → tên điện thoại → bộ nhớ
       trong → `DCIM` → `Camera`.
     - iPhone: cắm cáp, bấm **Tin cậy** (Trust) trên điện thoại. Explorer
       → `This PC` → `Apple iPhone` → `Internal Storage` → `DCIM` → thư
       mục mới nhất.
  3. Sắp xếp theo ngày (`Date modified`), chọn **tất cả** ảnh chụp ở A6
     (kể cả ảnh hỏng), `Ctrl+C`.
  4. Trên thanh địa chỉ Explorer gõ
     `D:\scanner3d\docs\logs\c2-bo-tri-v8\<run_id>` rồi Enter, `Ctrl+V`.
     **Không đổi tên tệp.** Ảnh `.heic` (iPhone) giữ nguyên `.heic` — đó
     là ảnh gốc.
  5. Ghi từng tệp vào bảng "Ảnh điện thoại" của sổ: tên tệp gốc, bước
     `A6`, nội dung (a)/(b)/(c) và góc chụp, giờ chụp. Lưu sổ (`Ctrl+S`).
  6. Kiểm trong Git Bash, thay `<run_id>`:
     ```
     ls -l docs/logs/c2-bo-tri-v8/<run_id>/
     ```
- Thấy gì là đúng: `ls` liệt kê `ghi-nhan-nguoi-dung.md` và các ảnh với
  tên gốc của điện thoại (dạng `IMG_...`, `PXL_...`), đuôi `.jpg`,
  `.jpeg` hoặc `.heic`, mỗi tệp vài trăm KB đến vài MB.
- Nếu sai:
  - Windows báo tệp trùng tên (`The destination already has a file
    named ...`): chọn **Skip** (Bỏ qua), không chọn Replace; báo Tester
    tên tệp đó.
  - Không có cáp, phải gửi qua Zalo/Messenger/Telegram: các ứng dụng này
    nén ảnh và xoá EXIF nếu gửi dạng "ảnh". Gửi dạng **tệp** (file), và
    ghi đường chuyển vào sổ ghi nhận.
  - Ảnh `.heic` không mở được trên Windows: vẫn giữ tệp `.heic`. Nếu cần
    bản xem, mở bằng ứng dụng Photos → `...` → `Save as` → JPEG, lưu bên
    cạnh với tên gốc thêm `_xem` (ví dụ `IMG_1234_xem.jpg`); bản này chỉ
    để xem, không thay tệp gốc.
  - Tệp có kích thước vài chục KB: có thể đã bị nén — báo Tester.

**A8. Báo Tester và CHỜ xác nhận cổng ảnh bố trí — chưa chạy bước B.**
- Ở đâu: phiên chat với Tester.
- Làm gì: gửi `<run_id>`, dòng `Camera PID: ...` và IP (A1–A2), session
  ID của lần chụp thử đạt ở A5 và các lần không đạt. Trong lúc chờ
  **không xê dịch** gá, vật, giấy, đèn, rèm.
- Thấy gì là đúng: Tester trả lời cổng ảnh bố trí **ĐẠT**, được chạy B.
- Nếu sai: Tester nêu mục thiếu (ví dụ không đọc được vạch 0 ở ống kính)
  — chụp bổ sung ngay khi bố trí còn nguyên, chép như A7, báo lại. Nếu
  bố trí đã bị xê dịch trong lúc chờ: đo lại 250 mm, chụp lại A5 (ID mới)
  và nhóm A6, ghi rõ trong sổ.

### B. Đưa camera về tự động, probe mức phơi sáng, rồi ảnh tham chiếu

Chỉ làm sau khi Tester xác nhận A8. **Probe chạy TRƯỚC ảnh tham chiếu**:
probe đặt rõ camera về tự động hoàn toàn (`aec=1`, `agc=1`, `awb=1`,
`awb_gain=1`, `wb_mode=0` — lệnh cuối xoá preset thủ công còn sót, `0x3406`
về `0`). Không nhấn RESET hay rút điện bo từ A5 tới hết bước B (A5 đã đặt
VGA); nếu lỡ, chạy lại lệnh A5 (script tự đặt ID mới, ghi lý do vào sổ)
rồi mới vào B1.

**B1. Probe — đưa camera về tự động và đọc mức phơi sáng.**
- Ở đâu: Git Bash.
- Làm gì, thay `<IP>`:
  ```
  .venv/Scripts/python.exe pc/camera_profile.py --probe --host <IP> --out docs/logs
  ```
- Thấy gì là đúng: 5 dòng `/control` đúng thứ tự `aec=1`, `agc=1`,
  `awb=1`, `awb_gain=1`, `wb_mode=0`, đều `OK`; 5 dòng "mau i/5"; cuối
  cùng khối "UNG VIEN (CHUA XAC MINH...)" in `aec_value = ...` và
  `agc_gain = ...`. Nếu dòng `aec_value` có chữ "DA KEP", script đã tự
  đổi về trần `783` — dùng đúng số in ra, không cộng/trừ gì thêm. Ghi lại
  `aec_value` (`<AEC>`), `agc_gain` (`<AGC>`) và tên tệp log
  `docs/logs/probe_<ngay>_<giờ>.json` (dòng `Log:`). Đây là số của đợt
  này — **không** dùng lại 783/7 của lần trước.
- Nếu sai:
  - `Probe THAT BAI: khong dat duoc <bien>=<gia tri> de ve tu dong ...` —
    `/control` lỗi HTTP/kết nối; mở `http://<IP>/status` xem bo còn phản
    hồi, thử lại một lần.
  - `Probe THAT BAI: mau i/5 chua o trang thai tu dong: ...` (ví dụ
    `0x3406: yeu cau 0, bo bao 1`) — bo trả `OK` nhưng không về tự động.
    **DỪNG, chưa chụp tham chiếu**; gửi Tester nguyên văn output và tệp
    log probe.
  - Lỗi khác (thiếu thanh ghi, mất kết nối) — thử lại tối đa một lần; vẫn
    lỗi thì gửi Tester nguyên văn. Tệp log probe lỗi giữ nguyên.

**B2. Chụp 5 ảnh tham chiếu tự động — NGAY sau B1, không chạy `--create` nào xen giữa.**
- Ở đâu: Git Bash.
- Làm gì, thay `<IP>` và `<run_id>`:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host <IP> --framesize VGA --count 5 --interval 2 --meta-copy docs/logs --note "C2 Vong 8 dot <run_id>, anh tham chieu tu dong sau probe"
  ```
  Ghi `<session_id>` ở dòng `Phien:` (gọi là `<session_id_B2>`), rồi kiểm
  trạng thái tự động ở ĐẦU và CUỐI phiên — thay `<session_id_B2>` ở hai chỗ:
  ```
  for f in docs/logs/<session_id_B2>/status_start.json docs/logs/<session_id_B2>/status_end.json; do .venv/Scripts/python.exe -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[1], {k: d.get(k) for k in ('aec','agc','awb','awb_gain','wb_mode','0x3406')})" "$f"; done
  ```
- Thấy gì là đúng: `Ket qua: PASS`; 5 ảnh trong `data/raw/<session_id_B2>/`;
  lệnh kiểm in đúng hai dòng, cả hai kết thúc bằng nguyên văn
  `{'aec': 1, 'agc': 1, 'awb': 1, 'awb_gain': 1, 'wb_mode': 0, '0x3406': 0}`.
  Chỉ khi đó phiên này mới là phiên THAM CHIẾU của đợt.
- Nếu sai:
  - `Ket qua: FAIL` — ghi ID và lý do vào sổ, xử lý theo mục K, không
    chuyển bước.
  - PASS nhưng một trong hai dòng khác chuỗi trên — phiên này KHÔNG phải
    tham chiếu tự động. Giữ nguyên dữ liệu, ghi "không đủ điều kiện" vào
    sổ, làm lại B1 rồi B2 (ID mới). Lần hai vẫn sai thì DỪNG, gửi Tester
    hai dòng in ra và cả hai session ID.

**B3. Đo độ sáng/màu của phiên tham chiếu — xác định ROI MỚI theo tờ giấy.**
- Ở đâu: Git Bash để chạy lệnh; Paint để đọc toạ độ trên ảnh.
- Làm gì, xác định ROI `X,Y,W,H` trên ảnh của đợt này (không chép ROI
  `40,40,200,200` của lần trước):
  1. Mở `data/raw/<session_id_B2>/img_0001.jpg` bằng Paint.
  2. Di chuột tới **góc trên-trái** của vùng giấy trắng muốn đo (lùi vào
     trong mép giấy 5–10 px để tránh bóng viền), đọc toạ độ ở thanh trạng
     thái phía dưới Paint — đây là `X,Y`. Gốc `(0,0)` ở góc trên-trái ảnh;
     Y tăng khi đi **xuống**.
  3. Di chuột tới **góc dưới-phải** của vùng muốn đo, đọc toạ độ `X2,Y2`.
  4. Tính `W = X2 − X`, `H = Y2 − Y` (bề rộng, chiều cao — **KHÔNG** chép
     nguyên `X2,Y2` vào chỗ `W,H`).
  5. Ràng buộc với ảnh VGA 640×480: `X + W ≤ 640`, `Y + H ≤ 480`; ROI nên
     ít nhất `150×120` px. Ví dụ: góc trên-trái `150,90`, góc dưới-phải
     `470,330` → `--roi 150,90,320,240`.
  6. Chạy, thay `<session_id_B2>` và `X,Y,W,H`:
     ```
     .venv/Scripts/python.exe pc/sharpness.py <session_id_B2> --roi X,Y,W,H --out docs/logs
     ```
- Thấy gì là đúng: dòng `do sang ROI  : mean ...` và dòng `mau RGB ROI :
  ... spread kenh mau ...%`. Ghi số sau chữ `mean` ở dòng `do sang ROI` —
  đây là **mốc `m_ref`** cho O5 ở bước D; ghi bốn số `X,Y,W,H` — bước D
  dùng LẠI đúng ROI này. Ghi cả tên thư mục ở dòng `Da ghi ho so:`.
- Nếu sai: `--roi ... vuot khung 640x480` — `X+W` hoặc `Y+H` vượt ảnh,
  thường do nhầm `W,H` với góc thứ hai; tính lại theo bước 4.

### C. Cổng thanh ghi — tạo bốn hồ sơ mới, xác nhận bảng WB (CHƯA chụp ảnh)

**C1. Tạo bốn hồ sơ mới `N` = 1, 2, 3, 4 (Sunny/Cloudy/Office/Home).**
- Ở đâu: Git Bash.
- Làm gì, lặp đúng bốn lần, mỗi lần thay `<IP>`, `<AEC>`, `<AGC>` (số của
  B1 đợt này), `<run_id>` và `N` (ở cả `--set wb_mode=N` và
  `--lens-note`). **Giữ nguyên `--set awb=1 --set awb_gain=1`**:
  ```
  .venv/Scripts/python.exe pc/camera_profile.py --create --host <IP> --framesize VGA --quality 10 --set aec_value=<AEC> --set agc_gain=<AGC> --set awb=1 --set awb_gain=1 --set wb_mode=N --lens-note "ong kinh goc, tieu diem xa; thu wb_mode=N Vong 8 dot <run_id>"
  ```
  Ví dụ đã điền số cho `N=1`, `<AEC>=650`, `<AGC>=5`, `<run_id>=20260928_0915`
  (số minh hoạ, không phải số cần dùng):
  ```
  .venv/Scripts/python.exe pc/camera_profile.py --create --host 192.168.31.9 --framesize VGA --quality 10 --set aec_value=650 --set agc_gain=5 --set awb=1 --set awb_gain=1 --set wb_mode=1 --lens-note "ong kinh goc, tieu diem xa; thu wb_mode=1 Vong 8 dot 20260928_0915"
  ```
- Thấy gì là đúng: 16 dòng `/control ... OK`; dòng `Da tao va xac minh ho
  so: ...`. Tên tệp do script tự đặt (không dùng `--id`): ngày đợt đo mới
  nên lần đầu là `cam_VGA_q10_<ngay>.json`, các lần sau tự thêm `_r01`,
  `_r02`, `_r03`. **Ghi tên tệp đầy đủ script in ra cho từng `N`** —
  không đoán theo hậu tố; dùng lại ở D.
- Nếu sai: có dòng `LOI` hoặc `KHONG tao ho so, lech: ...` — gửi Tester
  toàn bộ output. `Tham so khong hop le: aec_value ... vuot tran` — bạn
  nhập số chưa kẹp; dùng đúng số B1 in ra. Dòng lệch có đuôi `(L11)` —
  bo trả `OK` nhưng thanh ghi WB không theo bảng: **DỪNG ở C1**, không
  tạo tiếp preset khác. Không tự đổi `<AEC>`/`<AGC>` để "cho qua".

**C2. Đối chiếu bảng thanh ghi bốn hồ sơ — DỪNG nếu sai, chưa chụp ảnh.**
- Ở đâu: VS Code (mở tệp `.json`).
- Làm gì: mở lần lượt bốn tệp vừa tạo ở C1 trong
  `data/calibration/camera_profiles/`, xem `expected_registers` và
  `controls`, so với bảng (`--create` đã tự đối chiếu; C2 là đọc lại để
  chắc tệp lưu đúng):

  | `wb_mode` | `0x3400` | `0x3402` | `0x3404` | `0x3406` |
  | --- | ---: | ---: | ---: | ---: |
  | 1 Sunny | 1504 (`0x05e0`) | 1040 (`0x0410`) | 1344 (`0x0540`) | 1 |
  | 2 Cloudy | 1616 (`0x0650`) | 1040 (`0x0410`) | 1264 (`0x04f0`) | 1 |
  | 3 Office | 1312 (`0x0520`) | 1040 (`0x0410`) | 1632 (`0x0660`) | 1 |
  | 4 Home | 1056 (`0x0420`) | 1008 (`0x03f0`) | 1808 (`0x0710`) | 1 |

- Thấy gì là đúng: mỗi hồ sơ khớp đúng dòng của `wb_mode` của nó, bốn bộ
  ba gain khác nhau giữa các preset; trong `controls`: `"aec": 0`,
  `"agc": 0`, `"awb": 1`, `"awb_gain": 1`, `aec_value`/`agc_gain` đúng số
  C1, `"verified": null`.
- Nếu sai: **DỪNG, chưa sang D**. Gửi Tester đủ bốn bộ số đã đọc; không
  tự sửa bảng hay tệp; giữ bốn hồ sơ làm bằng chứng.

### D. Chụp ảnh và đo màu từng preset, chọn preset cho đợt này

Chỉ làm sau khi C2 đạt cả bốn hồ sơ. Không xê dịch bố trí, không đổi
đèn/rèm từ đây tới hết bước G trừ thao tác đóng rèm có chủ đích ở G3.
Trong lúc lệnh chụp đang chạy, đứng ở một chỗ cố định ngoài khung, không
che đèn hay cửa sổ (áp dụng cả B2, F, G).

**D1(N). Chụp 5 ảnh bằng hồ sơ N của C1 — lặp cho N = 1, 2, 3, 4.**
- Ở đâu: Git Bash.
- Làm gì, thay `<IP>`, `<ten_ho_so_N>` (tên tệp ghi ở C1, không có
  `.json`), `<run_id>`, `N`:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host <IP> --profile data/calibration/camera_profiles/<ten_ho_so_N>.json --count 5 --interval 2 --meta-copy docs/logs --note "C2 Vong 8 dot <run_id>, thu wb_mode=N"
  ```
- Thấy gì là đúng: `Ket qua: PASS`; KHÔNG có dòng `thanh ghi ho so camera
  lech` hay `control ho so camera lech`; ảnh đúng chiều. Ghi
  `<session_id_D1N>` (dòng `Phien:`) cho từng preset.
- Nếu sai:
  - `FAIL` kèm lệch thanh ghi/control, hoặc lỗi giao tiếp — **DỪNG, không
    chụp tiếp preset khác**; ghi vào sổ, gửi Tester `summary.txt` của
    phiên (`data/raw/<session_id_D1N>/summary.txt`).
  - `ho so camera khong hop le: controls['awb'] phai bang 1 ...` — đã chọn
    nhầm một hồ sơ cũ `awb=0`; thay đúng tên hồ sơ của C1 đợt này.
  - Ảnh lật ngược — dừng ngay, báo Tester (lỗi mã, không phải thao tác).
  - Đèn, rèm hoặc bố trí đổi giữa chừng — giữ dữ liệu, ghi phiên "không
    đủ điều kiện" vào sổ, báo Tester trước khi chạy lại.

**D2(N). Đo màu/sáng và so ngưỡng O5–O7 — lặp cho N = 1, 2, 3, 4.**
- Ở đâu: Git Bash.
- Làm gì, dùng ĐÚNG `X,Y,W,H` của B3:
  ```
  .venv/Scripts/python.exe pc/sharpness.py <session_id_D1N> --roi X,Y,W,H --out docs/logs
  ```
  Đọc số sau `mean` ở dòng `do sang ROI` (gọi là `<mean_N>`), rồi tính độ
  lệch so với `m_ref` của B3 — thay số thật vào hai chỗ `<mean_N>` và
  `<m_ref>` (đây là chỗ phải điền, không chạy nguyên văn):
  ```
  awk -v m=<mean_N> -v r=<m_ref> 'BEGIN{printf "d=%.2f%%\n", 100*(m>r?m-r:r-m)/r}'
  ```
  Ví dụ đã điền số (mean 171.3, mốc 158.7):
  ```
  awk -v m=171.3 -v r=158.7 'BEGIN{printf "d=%.2f%%\n", 100*(m>r?m-r:r-m)/r}'
  ```
- Thấy gì là đúng: `d ≤ 15%` (O5); dòng `mau RGB ROI` có `spread kenh mau
  ≤ 15%` (O6) và `bao hoa/toi bat ky kenh (max)` cả hai `≤ 1%` (O7). Ghi
  bảng tạm: preset N → d, spread, tối %, bão hoà %, tên thư mục
  `Da ghi ho so:`.
- Nếu sai: một ngưỡng không đạt — preset N bị loại, vẫn ghi số vào bảng
  (không xoá hồ sơ/ảnh), chuyển sang N tiếp theo.

**D3. Chọn preset của đợt này.**
- Ở đâu: bảng tạm ở D2.
- Làm gì: trong các preset đạt cả O5, O6, O7, chọn preset có spread
  **nhỏ nhất** — đó là cấu hình VGA q10 của ma trận, dùng cho E, F, G. Ghi
  `<WB>` (= `wb_mode` đã chọn), `<ho_so_VGA_q10>` (tên tệp hồ sơ của preset
  đó, không có `.json`) và `<session_id_D1_chon>`.
- Thấy gì là đúng: có ít nhất một preset đạt; lựa chọn theo số của đợt
  này (có thể khác Cloudy của lần trước).
- Nếu sai: KHÔNG preset nào đạt cả ba ngưỡng — DỪNG, không chọn "đỡ tệ
  nhất", gửi Tester bảng đủ bốn dòng (kế hoạch trả về Planner). Nếu cả bốn
  preset cho spread gần như bằng nhau (kiểu 26% của 24/09) dù `awb=1`, ghi
  rõ điều đó.

### E. T5 — độ ổn định 5 ảnh của phiên VGA q10 đã chọn

**E1. Tính độ lệch sáng nội bộ 5 ảnh (khác O5: không so với tham chiếu).**
- Ở đâu: Git Bash.
- Làm gì: dùng `per_image.csv` trong thư mục D2 của preset đã chọn (tên ở
  dòng `Da ghi ho so:`), thay `<thu_muc_sharpness>`:
  ```
  .venv/Scripts/python.exe -c "import csv,sys; m=[float(r['mean']) for r in csv.DictReader(open(sys.argv[1]))]; a=sum(m)/len(m); print('n=%d m_tb=%.3f d=%.3f%%' % (len(m), a, 100*max(abs(x-a) for x in m)/a))" docs/logs/<thu_muc_sharpness>/per_image.csv
  ```
- Thấy gì là đúng: `n=5` và `d` dưới 2% (`d = 100 × max|mᵢ − m̄| / m̄`).
- Nếu sai: `d ≥ 2%` — ánh sáng có thể đã đổi trong lúc chụp; ghi vào sổ,
  báo Tester trước khi chụp lại (chụp lại = D1 với cùng hồ sơ, ID mới).

### F. Ba cấu hình C2b còn lại (VGA q20, SVGA q10, SVGA q20)

**F1. Tạo hồ sơ và chụp 5 ảnh cho từng cấu hình, dùng ĐÚNG `<AEC>`/`<AGC>`/`<WB>` đã chọn.**
- Ở đâu: Git Bash.
- Làm gì, lặp cho `(VGA,20)`, `(SVGA,10)`, `(SVGA,20)` — đổi
  `--framesize`/`--quality` ở lệnh thứ nhất, `<ten_ho_so_vua_tao>` (tên
  in ở dòng `Da tao va xac minh ho so:`, bỏ đuôi `.json`) và phần ghi chú
  ở lệnh thứ hai:
  ```
  .venv/Scripts/python.exe pc/camera_profile.py --create --host <IP> --framesize VGA --quality 20 --set aec_value=<AEC> --set agc_gain=<AGC> --set awb=1 --set awb_gain=1 --set wb_mode=<WB> --lens-note "ong kinh goc, tieu diem xa; C2b Vong 8 dot <run_id>"
  .venv/Scripts/python.exe pc/capture_session.py --host <IP> --profile data/calibration/camera_profiles/<ten_ho_so_vua_tao>.json --count 5 --interval 2 --meta-copy docs/logs --note "C2b Vong 8 dot <run_id>, VGA q20"
  ```
- Thấy gì là đúng: mỗi cấu hình một dòng `Da tao va xac minh ho so:` và
  một `Ket qua: PASS`. Ghi tên ba hồ sơ và ba session ID. Cùng phiên D1
  đã chọn là đủ **bốn phiên ma trận**.
- Nếu sai: `aec_value`/`agc_gain` bị từ chối — kiểm đã dùng đúng số B1 của
  đợt này; lỗi khác xử lý như C1/D1 — ghi sổ, gửi output, không tự sửa mã.

### G. Cặp rèm mở/đóng — phép so chẩn đoán, KHÔNG bỏ qua

Không có ngưỡng ĐẠT/CHƯA ĐẠT cho haze; đây là phép so tương đối giữa hai
phiên cùng hồ sơ VGA q10, cùng bố trí, chỉ khác trạng thái một rèm. Hai
phiên G-a và G-b thêm 10 JPEG ngoài bộ tối thiểu 45.

**G1. Ảnh điện thoại trạng thái rèm MỞ (ngay trước khi đổi).**
- Ở đâu: điện thoại, đứng ngoài bàn đo, tắt flash.
- Làm gì: chụp lại nhóm (c) như A6 — thấy rèm sẽ đóng đang **mở**, các
  đèn đang bật.
- Thấy gì là đúng: ảnh thấy rõ rèm đó và các nguồn sáng.
- Nếu sai: chụp lại ngay; ảnh hỏng vẫn giữ.

**G2. Chụp 5 ảnh VGA q10 rèm mở (G-a).**
- Ở đâu: Git Bash.
- Làm gì, thay `<IP>`, `<ho_so_VGA_q10>` (hồ sơ đã chọn ở D3), `<run_id>`:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host <IP> --profile data/calibration/camera_profiles/<ho_so_VGA_q10>.json --count 5 --interval 2 --meta-copy docs/logs --note "C2 Vong 8 dot <run_id>, rem MO (G-a)"
  ```
- Thấy gì là đúng: `Ket qua: PASS`; ghi `<session_id_Ga>`.
- Nếu sai: như D1.

**G3. Đóng đúng rèm đã chọn và chụp ảnh điện thoại trạng thái ĐÓNG.**
- Ở đâu: rèm đã ghi trong sổ mục "Rèm sẽ ĐÓNG ở bước G"; điện thoại.
- Làm gì: chỉ đóng rèm đó; không đổi đèn, không chạm gá/vật/giấy. Chụp
  nhóm (c) ở trạng thái đóng, cùng góc với G1.
- Thấy gì là đúng: ảnh thấy rèm đó đã đóng; các nguồn sáng khác như G1.
- Nếu sai: không đóng được rèm nào, hoặc đóng rèm làm phải đổi đèn — báo
  Tester lý do. Khi đó **C2 chưa khép được** (cổng Q9 chưa hoàn tất);
  không bỏ qua bước này rồi báo xong.

**G4. Chụp 5 ảnh VGA q10 rèm đóng (G-b).**
- Ở đâu: Git Bash.
- Làm gì: như G2, đổi ghi chú:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host <IP> --profile data/calibration/camera_profiles/<ho_so_VGA_q10>.json --count 5 --interval 2 --meta-copy docs/logs --note "C2 Vong 8 dot <run_id>, rem DONG (G-b)"
  ```
- Thấy gì là đúng: `Ket qua: PASS`; ghi `<session_id_Gb>`.
- Nếu sai: như D1; giữ dữ liệu, ghi sổ.

**G5. Mở lại rèm và chụp ảnh bố trí CUỐI ĐỢT.**
- Ở đâu: bàn đo, điện thoại, rồi Explorer/Git Bash như A7.
- Làm gì:
  1. Mở lại rèm về trạng thái chuẩn.
  2. Đặt lại thước đo từ mặt trước ống kính tới mặt khối gỗ, đọc số; chụp
     lại nhóm (a) (thấy các mốc băng dính còn trùng mép gá/vật) và nhóm
     (b). Cất thước đo.
  3. Ghi số đọc và giờ vào dòng "Đo lại cuối đợt" của sổ.
  4. Chép **mọi** ảnh điện thoại của G1, G3, G5 vào
     `docs/logs/c2-bo-tri-v8/<run_id>/` theo đúng A7 (không đổi tên), điền
     bảng "Ảnh điện thoại" với bước `G1`/`G3`/`G5`, lưu sổ.
- Thấy gì là đúng: mốc băng dính còn trùng mép gá/vật; số đọc cuối đợt
  bằng số đọc A4.
- Nếu sai: mốc lệch hoặc số đọc khác — ghi đúng những gì thấy vào sổ,
  báo Tester; không chỉnh lại rồi ghi như chưa từng xê dịch.

### H. So sánh bốn cấu hình và cặp rèm (chỉ đọc dữ liệu, không chạm bo)

**H1. Đo bề rộng mép khối gỗ và trung bình bytes/elapsed_ms.**
- Ở đâu: Git Bash; Paint để đọc toạ độ.
- Làm gì:
  1. Mở `img_0001.jpg` của phiên D1 đã chọn (VGA) bằng Paint, chọn **một
     mép dọc của khối gỗ** (không phải mép tờ giấy hay mép thước). Đọc `X`
     của mép và hai hàng `Y0`, `Y1` trên/dưới đoạn mép thẳng. Cửa sổ đo
     lấy từ `X−20` tới `X+20`: trong khoảng đó chỉ được có **một** mép.
  2. Với phiên SVGA, **xác định lại toạ độ trên ảnh SVGA thật** (800×600),
     cùng mép đó; không nhân máy móc toạ độ VGA.
  3. Chạy cho từng phiên: bốn phiên ma trận, G-a, G-b (đối số
     `<session_id>` bắt buộc):
     ```
     .venv/Scripts/python.exe pc/ruler_ticks.py <session_id> --edge X,Y0,Y1
     ```
  4. Tính bytes và `/capture` ms trung bình của từng phiên từ `frames.csv`:
     ```
     awk -F',' 'NR>1{b+=$5; e+=$3; n++} END{printf "trung binh bytes=%.1f, trung binh elapsed_ms=%.1f (n=%d)\n", b/n, e/n, n}' data/raw/<session_id>/frames.csv
     ```
- Thấy gì là đúng: mỗi phiên đo được bề rộng mép hữu hạn cho 5/5 ảnh; đủ
  số cho bốn phiên ma trận và cặp G-a/G-b. Chỉ cần số px; Tester quy đổi
  px SVGA sang px VGA theo vị trí mép trên hai ảnh và ghi giới hạn (không
  có hiệu chuẩn mm mới nếu bạn không đo thước trong khung).
- Nếu sai: không tìm được mép rõ hoặc lỡ đo mép giấy — gửi Tester ảnh và
  toạ độ đã thử, không đoán; `can ten phien` là thiếu `<session_id>`.

**H2. Gửi Tester kết quả A–H.** Nội dung ở mục L, điểm 2–4. Chưa làm I/J
cho tới khi Tester xác nhận T5 và chọn cấu hình chính/phụ.

### I. Đánh dấu `verified` — CHỈ làm sau khi Tester xác nhận T5 đạt

Chỉ bốn hồ sơ **mới** của ma trận đợt này (VGA q10 đã chọn + ba hồ sơ F)
với đúng `session_id` và `mean_drift_pct` Tester đưa. Hồ sơ preset bị loại
giữ `verified: null`. **Không chạm hồ sơ 23/09–27/09.**

**I1. Sao lưu và băm từng hồ sơ trước khi sửa.**
- Ở đâu: Git Bash.
- Làm gì, cho từng hồ sơ, thay `<ten_ho_so>`:
  ```
  ls docs/logs/<ten_ho_so>.json.bak
  cp -n data/calibration/camera_profiles/<ten_ho_so>.json docs/logs/<ten_ho_so>.json.bak
  sha256sum data/calibration/camera_profiles/<ten_ho_so>.json docs/logs/<ten_ho_so>.json.bak
  ```
- Thấy gì là đúng: lệnh `ls` báo `No such file or directory` (chưa có
  `.bak` tên đó); `sha256sum` in hai dòng **cùng** một mã hash — đây là
  hash "trước", ghi lại.
- Nếu sai: `ls` liệt kê được tệp `.bak` — tên đó đã có; **dừng**, báo
  Tester, không chép đè. Hai hash khác nhau — báo Tester.

**I2. Sửa đúng trường `verified` bằng lệnh — không sửa tay.**
- Ở đâu: Git Bash. Lệnh thay đúng chuỗi `"verified": null` (phải xuất
  hiện đúng 1 lần) và giữ nguyên mọi byte khác của tệp, kể cả kiểu xuống
  dòng.
- Làm gì, thay `<ten_ho_so>`, `<session_id_tuong_ung>` và `<d>` (số Tester
  đưa, dấu **chấm** thập phân, ví dụ `0.105`):
  ```
  .venv/Scripts/python.exe -c "import sys,pathlib; p=pathlib.Path(sys.argv[1]); b=p.read_bytes(); old=b'\"verified\": null'; assert b.count(old)==1, 'DUNG: verified khong phai null hoac xuat hien khac 1 lan'; new=('\"verified\": {\"session_id\": \"%s\", \"mean_drift_pct\": %s, \"registers_stable\": true}' % (sys.argv[2], float(sys.argv[3]))).encode(); p.write_bytes(b.replace(old, new)); print('da sua', p)" data/calibration/camera_profiles/<ten_ho_so>.json <session_id_tuong_ung> <d>
  sha256sum data/calibration/camera_profiles/<ten_ho_so>.json
  .venv/Scripts/python.exe pc/camera_profile.py --verify --host <IP> --profile data/calibration/camera_profiles/<ten_ho_so>.json
  ```
- Thấy gì là đúng: `da sua ...`; hash mới khác hash "trước" của I1;
  `--verify` in `Ho so khop bo: <ten_ho_so>`. Ghi hash "sau".
- Nếu sai: `AssertionError: DUNG: ...` — tệp không còn `"verified": null`
  (đã sửa rồi, hoặc sai tệp): lệnh không ghi gì; báo Tester. `ValueError`
  — `<d>` gõ sai (dấu phẩy?), lệnh không ghi gì; gõ lại. `--verify` báo lỗi
  — DỪNG, không sửa tiếp, gửi Tester output; giữ nguyên cả tệp và `.bak`.

### J. Sao lưu toàn bộ dữ liệu đợt đo sang đích MỚI

Máy này có ổ C: và D: trên **cùng một ổ vật lý** (Tester kiểm 27/09), nên
bản sao thứ hai dùng thư mục OneDrive (đồng bộ lên máy chủ). Đích của đợt
này là thư mục MỚI `backup_scanner3d_<run_id>`; **không** chép vào
`backup_scanner3d_20260927` của lần trước. `data/raw` (junction tới
`D:\datascanner3d\raw`) không tính là bản sao.

**J1. Kiểm đích chưa tồn tại và tạo thư mục.**
- Ở đâu: Git Bash, thư mục gốc repo. Chạy J1–J3 liền trong **cùng một
  cửa sổ** (biến `DST` mất khi đóng cửa sổ; nếu lỡ đóng, chạy lại dòng
  `DST=...` trước).
- Làm gì, thay `<run_id>`:
  ```
  DST=/c/Users/bestp/OneDrive/backup_scanner3d_<run_id>
  ls -d "$DST"
  mkdir "$DST" "$DST/raw" "$DST/profiles" "$DST/logs" "$DST/logs/c2-bo-tri-v8"
  ```
- Thấy gì là đúng: `ls` báo `No such file or directory`; `mkdir` không in
  gì.
- Nếu sai: `ls` in ra đường dẫn — đích đã có; dừng, báo Tester, không
  chép vào đó. `mkdir: cannot create directory` — như trên.

**J2. Chép dữ liệu của đợt (không ghi đè).**
- Ở đâu: cùng cửa sổ Git Bash.
- Làm gì, thay `<ngay>` và `<run_id>`:
  ```
  cp -rn data/raw/capture_<ngay>_* "$DST/raw/"
  cp -n data/calibration/camera_profiles/cam_*_<ngay>*.json docs/logs/cam_*_<ngay>*.json.bak "$DST/profiles/"
  cp -rn docs/logs/c2-bo-tri-v8/<run_id> "$DST/logs/c2-bo-tri-v8/"
  cp -rn docs/logs/capture_<ngay>_* docs/logs/probe_<ngay>_* docs/logs/sharpness_<ngay>_* "$DST/logs/"
  ```
- Thấy gì là đúng: các lệnh không in gì.
- Nếu sai: `cannot stat ... No such file or directory` — một mẫu tên
  không khớp tệp nào (ví dụ gõ sai `<ngay>`); kiểm lại `<ngay>`, chạy lại
  riêng dòng đó. Đợt đo qua nửa đêm: chạy lại cả bốn dòng với ngày thứ
  hai.

**J3. Đối chiếu hash từng byte.**
- Ở đâu: cùng cửa sổ Git Bash.
- Làm gì, thay `<ngay>` và `<run_id>`:
  ```
  (cd data/raw && find capture_<ngay>_* -type f -exec sha256sum {} +) > "$DST/hash_raw.txt"
  (cd "$DST/raw" && sha256sum -c --quiet ../hash_raw.txt) && echo "RAW KHOP"
  (cd data/calibration/camera_profiles && sha256sum cam_*_<ngay>*.json) > "$DST/hash_profiles.txt"
  (cd docs/logs && sha256sum cam_*_<ngay>*.json.bak) >> "$DST/hash_profiles.txt"
  (cd "$DST/profiles" && sha256sum -c --quiet ../hash_profiles.txt) && echo "HO SO KHOP"
  (cd docs/logs && find c2-bo-tri-v8/<run_id> capture_<ngay>_* probe_<ngay>_* sharpness_<ngay>_* -type f -exec sha256sum {} +) > "$DST/hash_logs.txt"
  (cd "$DST/logs" && sha256sum -c --quiet ../hash_logs.txt) && echo "LOG KHOP"
  wc -l "$DST"/hash_*.txt
  ```
- Thấy gì là đúng: ba dòng `RAW KHOP`, `HO SO KHOP`, `LOG KHOP`, không có
  dòng `FAILED`; `wc -l` in số tệp của từng nhóm (gửi Tester). Biểu tượng
  OneDrive ở khay hệ thống báo đã đồng bộ xong (dấu tích xanh) — việc này
  bạn tự xác nhận, Tester không kiểm được.
- Nếu sai: dòng `... FAILED` — tệp đó chép lỗi; không xoá gì, báo Tester
  tên tệp. Không thấy dòng `... KHOP` nào mà cũng không có `FAILED` — gửi
  Tester toàn bộ output.

### K. Lỗi thường gặp, tra nhanh

| Thấy gì | Nghĩa là | Làm gì |
| --- | --- | --- |
| PID khác `0x3660` hoặc không thấy dòng PID (A1) | Sai camera hoặc firmware chưa in | Dừng; xác nhận đúng bo/module trước |
| `mkdir: cannot create directory ... File exists` (A3) | Mã đợt đo đã có | Không dùng lại, lấy `<run_id>` mới ở phút sau |
| `... khong ghi de: da ton tai` (A5, B2, D1, F1, G) | Hai lần chạy cùng một giây, script đã từ chối | Dữ liệu cũ nguyên; chờ vài giây, chạy lại |
| Ảnh thử A5 không đạt | Bố trí chưa đúng | Ghi ID + lý do vào sổ, chỉnh, chạy lại lệnh A5 (ID mới); không xoá |
| Windows hỏi thay tệp trùng tên khi chép ảnh (A7, G5) | Tên ảnh điện thoại trùng | Chọn Skip, báo Tester |
| Tester chưa xác nhận cổng ảnh bố trí (A8) | Thiếu ảnh/ghi nhận | Chụp bổ sung khi bố trí còn nguyên; chưa chạy B |
| `Probe THAT BAI: khong dat duoc <bien>=<gia tri> de ve tu dong` (B1) | `/control` lỗi HTTP/kết nối | Kiểm `http://<IP>/status`; thử lại một lần |
| `Probe THAT BAI: mau i/5 chua o trang thai tu dong` (B1) | Bo trả `OK` nhưng không về tự động | Dừng, chưa chụp tham chiếu; gửi output và log probe |
| Dòng kiểm B2 khác `{'aec': 1, 'agc': 1, 'awb': 1, 'awb_gain': 1, 'wb_mode': 0, '0x3406': 0}` | Tham chiếu không ở tự động | Giữ dữ liệu, làm lại B1 rồi B2; lần hai vẫn sai thì dừng |
| `--roi ... vuot khung 640x480` (B3) | Nhầm `W,H` với toạ độ góc thứ hai | Tính lại `W = X2−X`, `H = Y2−Y` |
| `Tham so khong hop le: aec_value ... vuot tran` (C1, F1) | Nhập `aec_value` chưa kẹp | Dùng đúng số B1 in ra |
| `Tham so khong hop le: controls['awb'] phai bang 1` (C1, F1) | Thiếu/sai `--set awb=1` | Chép lại đúng lệnh, có `--set awb=1 --set awb_gain=1` |
| `KHONG tao ho so, lech:` kèm dòng đuôi `(L11)` (C1) | Thanh ghi WB không theo bảng preset | Dừng ở C1, gửi output |
| `ho so camera khong hop le: controls['awb'] phai bang 1 ...` (D1, G) | Dùng nhầm hồ sơ cũ `awb=0` | Dùng hồ sơ C1 của đợt này; không sửa/xoá hồ sơ cũ |
| Ảnh lật ngược (A5, D1) | Lỗi mã, không phải thao tác | Dừng, báo Tester |
| Không preset nào đạt O5–O7 (D3) | Không có preset phù hợp ánh sáng này | Dừng, gửi bảng bốn dòng; không chọn "đỡ tệ nhất" |
| T5 `d ≥ 2%` (E1) | Ánh sáng đổi trong lúc chụp | Ghi sổ, báo Tester trước khi chụp lại |
| Không đóng được rèm (G3) | Không có phép so rèm | Báo Tester; C2 chưa khép, không bỏ qua |
| `ruler_ticks.py` báo `can ten phien` (H1) | Thiếu `<session_id>` | Thêm đối số trước `--edge` |
| `ls` thấy `.bak` đã có (I1) | Tên `.bak` đã dùng | Dừng, báo Tester, không chép đè |
| `AssertionError: DUNG: ...` (I2) | Tệp không còn `"verified": null` | Lệnh không ghi gì; báo Tester |
| `ls -d` in ra đường dẫn đích (J1) | Đích sao lưu đã có | Không chép vào đó; báo Tester |
| `FAILED` khi `sha256sum -c` (J3) | Bản sao sai | Không xoá gì; báo tên tệp |

### L. Gửi lại gì (tổng hợp)

1. Sau A (tại A8): `<run_id>`, dòng `Camera PID: ...`, IP, session ID lần
   chụp thử đạt và các lần không đạt; ảnh điện thoại đã nằm trong
   `docs/logs/c2-bo-tri-v8/<run_id>/` cùng sổ `ghi-nhan-nguoi-dung.md`.
2. Sau B–C: `<AEC>`, `<AGC>`, có "DA KEP" không, tên log probe (B1);
   `<session_id_B2>` và hai dòng kiểm tự động (B2); `m_ref`, `X,Y,W,H`,
   thư mục sharpness (B3); tên bốn hồ sơ và kết luận C2.
3. Sau D–E: bảng bốn dòng preset (d, spread, tối %, bão hoà %, session
   ID), preset đã chọn và lý do; dòng `n=5 ... d=...%` của E1.
4. Sau F–H: tên ba hồ sơ và ba session F; `<session_id_Ga>`,
   `<session_id_Gb>`; toạ độ mép đã dùng (VGA và SVGA) và output H1 của
   từng phiên; số đọc 250 mm cuối đợt; nhắc Tester sổ ghi nhận đã cập nhật
   ảnh G1/G3/G5.
5. Sau I (chỉ khi Tester yêu cầu): với mỗi hồ sơ — hash "trước" (I1), hash
   "sau" (I2), dòng `Ho so khop bo`.
6. Sau J (chỉ khi Tester yêu cầu): đường dẫn `$DST`, ba dòng `... KHOP`,
   output `wc -l`, và xác nhận OneDrive đã đồng bộ.
