# Quy trình tiếp nhận và nhận dạng camera FD5640 500W-V11 — nhận hàng 2026-09-22

**Trạng thái 22/09 tối: N1–N2 ĐÃ CHẠY và ĐẠT** — ảnh trong `docs/logs/`,
cả hai cáp in số `24`, bề rộng bằng nhau (người dùng xác nhận + đọc từ
ảnh). Được phép làm tiếp N3. N3–N6 CHƯA CHẠY.

**Cập nhật 09/10 (Điều phối):** người dùng muốn thử FD5640 có thay được
OV3660 không. Làm theo thứ tự N0 → N3 → N4 → N5 → N6 → N7. ĐÃ ĐỌC Ở ĐÂY:
firmware `CameraWebServerTest` trên `main` có nhánh riêng cho OV5640
(`app_httpd.cpp:680`, trang web `index_ov5640` ở dòng 969); thư viện
`esp32-camera` trong core 3.3.11 có bật OV5640 hay không thì CHƯA KIỂM
CHỨNG — N4 sẽ trả lời. Yêu cầu an toàn laser không liên quan bước này.

**Cập nhật 11–12/10 (Coder P03 Vòng 2, đồng bộ bằng chứng 11–12/10, D076, D077, D080 và PLAN Vòng 3):**
- **Thông tin bo theo hồ sơ (`ENVIRONMENT.md`, `docs/HARDWARE.md`):** module trên bo là `ESP32-S3-WROOM-1-N16R8`, Flash quan sát `16 MB`, PSRAM `8192 KB` (`OPI PSRAM`); nhà sản xuất bo chưa xác nhận (`Freenove ESP32-S3-WROOM CAM` chỉ là giả thuyết bố cục chân).
- **N0, N3, N4, N5 ĐÃ CHẠY:** ảnh N0 lưu tại `docs/logs/esp32s3-ov3660-dau-noi-n0-2026-10-11.jpg`; thông tin Serial ngày 11/10 do người dùng báo qua phiếu (`00_DIEU_PHOI.md`), và ngày 12/10 người dùng đã chép nguyên văn 18 dòng từ `Serial Monitor` ở bước P03.1 trước khi chụp `r2` lưu tại `docs/logs/serial_fd5640_p03_20261012.txt` (`Camera Init OK: fb_count=1, grab_mode=1, fb_location=0`, `Camera PID: 0x5640`, `Flash: 16 MB`, `PSRAM: 8192 KB`, `WiFi connected, IP 192.168.31.9` — đây là văn bản người dùng chép từ `Serial Monitor`, không phải tệp log tự động). Theo D076, FD5640 đang được giữ làm camera thử trên bo.
- **Đính chính bất biến (errata) và trạng thái 8 phiên chụp FD5640 hiện có (theo D080 và `01_PLAN.md` Vòng 3 mục 2, không sửa ảnh thô hay `session.json`):**
  1. `capture_fd5640_250mm` (11/10 16:31, 5/5 PASS): `session.json` ghi `"250 mm"` nhưng thực tế đặt ở **200 mm** (người dùng đính chính ngày 12/10). Theo D080, **200 mm và 250 mm** là hai khoảng cách đánh giá chính thức S1–S4: phiên này dùng chính thức cho S1, S2 và 1 phiên S3 tại **200 mm** (tuyệt đối không tính vào 250 mm; riêng S4 tại 200 mm cần 3 phiên mới `capture_p03_fd5640_200mm_r1`..`r3` cùng bố trí).
  2. `capture_p03_fd5640_250mm_r1` (11/10 19:28) và `r2`–`r6` (12/10 23:10–23:39): cả 6 phiên đều ở **250 mm thật** đo từ mặt trước ống kính tới mặt vật (**30/30 ảnh PASS**). Đã đủ 30/30 ảnh cho S3 tại 250 mm và đủ bộ 15 ảnh cùng bố trí `r4 + r5 + r6` cho S4 tại 250 mm (kèm ảnh bố trí `docs/logs/p03-bo-tri-250mm-2026-10-12.jpg`); **không cần chụp lại `r2/r3` ở 250 mm**.
  3. `capture_fd5640_350mm` (11/10 19:11, 5/5 PASS): khoảng cách thực **350 mm**. Theo D080, **bỏ 350 mm khỏi cổng** (chỉ giữ kết quả phân tích 350 mm làm thông tin tham khảo).
- **Phần bổ sung P03 (cuối tệp này):** ghi nhận trạng thái đã thu xong ở 250 mm (`r1–r6`), hướng dẫn thu bộ 3 phiên lặp ở **200 mm** (`capture_p03_fd5640_200mm_r1`..`r3`) nếu cần đóng tiêu chí S4 tại 200 mm, và hợp đồng phép so chỉ báo tăng nhiệt chip (S5) đồng bộ với `p15` Vòng 2.

Viết 2026-09-22 khi người dùng báo đã nhận 2 module. Mục đích: xác định
module có **cắm được vào bo ESP32-S3-WROOM-1-N16R8** và **cảm biến thật là
gì**, trước khi đụng tới bo đang chạy được. Không suy từ tên sản phẩm
(`AGENTS.md`, "Quyết định kỹ thuật").

Điều đang biết, NGƯỜI DÙNG CUNG CẤP 22/09: mã in trên dây `FD5640 500W
-V11`; người bán báo tự động lấy nét, tiêu cự 3 mm, điện áp làm việc
1,8–2,8 V, phạm vi chụp 0 → vô cùng. Tất cả là **lời người bán, CHƯA
KIỂM CHỨNG**.

Module đang chạy để so sánh: cáp in `TY-OV3660-21MM-V3.0`, đầu nối FPC
**24 chân bước 0,5 mm**, cáp dài 21 mm (`docs/HARDWARE.md`).

**Không tháo module cũ ở bước N1–N2.** Bo hiện là thiết bị duy nhất đã
chụp được 125 ảnh; giữ nó chạy được cho tới khi biết chắc module mới lắp
vừa.

## N1 — Chụp ảnh module mới

- **Ở đâu:** bàn làm việc, đủ sáng; điện thoại.
- **Làm gì:** chụp bốn ảnh cho **một** module (module còn lại giữ nguyên
  trong túi): (1) mặt trước có ống kính; (2) mặt sau đọc được chữ in trên
  bảng mạch; (3) toàn bộ dây cáp đọc được `FD5640 500W -V11`; (4) cận
  phần đầu cáp thấy rõ hàng tiếp điểm vàng. Đặt module **cạnh module
  OV3660 đang dùng** trong ảnh (3) để so chiều dài cáp và bề rộng.
- **Thấy gì là đúng:** ảnh rõ, chữ đọc được khi phóng to, không loá.
- **Nếu sai:** chữ nhoè → chụp lại ở chỗ sáng hơn, cách 15–20 cm, chạm
  vào chữ trên màn hình để máy lấy nét vào đó.

## N2 — Đếm chân và đo cáp, không cắm

- **Ở đâu:** bàn làm việc.
- **Làm gì:** đặt cáp module mới **chồng lên** cáp module cũ, hai đầu
  tiếp điểm trùng mép. Nhìn và trả lời ba câu: (a) bề rộng dải cáp có
  bằng nhau không; (b) đếm số tiếp điểm vàng của module mới; (c) chiều
  dài từ mép bảng mạch tới đầu cáp có bằng nhau không (cũ là 21 mm).
  Ghi ba câu trả lời ra giấy hoặc nhắn lại.
- **Thấy gì là đúng:** bề rộng bằng nhau, **24 tiếp điểm**, chiều dài
  xấp xỉ bằng.
- **Nếu sai:** khác số chân hoặc khác bề rộng → **dừng, không cắm**;
  module không dùng cho bo này. Gửi ảnh N1 và số đếm. Cáp ngắn hơn hoặc
  dài hơn vẫn có thể cắm được nhưng module sẽ không tựa đúng chỗ — báo
  lại trước khi làm tiếp.

## N0 — Chuẩn bị trước khi tháo (09/10)

- **Ở đâu:** bàn làm việc; điện thoại; bo ESP32-S3 đang cắm module OV3660.
- **Làm gì:** (1) chụp **một ảnh cận** đầu nối camera của bo khi module
  OV3660 còn cắm, thấy rõ mặt tiếp điểm cáp quay lên hay xuống — ảnh này
  dùng để lắp lại ở N7; (2) chuẩn bị một túi chống tĩnh điện hoặc hộp
  giấy nhỏ ghi "OV3660 — module gốc"; (3) không cần nạp lại firmware: bo
  đang chạy firmware của `main` (C5a) là được.
- **Thấy gì là đúng:** ảnh đọc được hướng tiếp điểm; có chỗ cất module cũ.
- **Nếu sai:** ảnh nhoè thì chụp lại gần hơn, chạm màn hình lấy nét vào
  đầu nối.

## N3 — Thay module (chỉ khi N2 đúng cả ba)

- **Ở đâu:** bo ESP32-S3, đầu nối FPC nắp gạt ở mặt trước.
- **Làm gì:** rút cáp USB khỏi bo (cả hai cổng), chờ đèn tắt hẳn. Gạt
  nhẹ nắp đen của đầu nối FPC lên bằng móng tay, hai bên đều nhau. Rút
  cáp module cũ ra, **cất vào túi chống tĩnh điện hoặc hộp giấy**. Đưa
  cáp module mới vào hết chiều sâu, **mặt tiếp điểm vàng quay đúng phía
  như module cũ vừa rút** (nhìn ảnh N1 để nhớ). Gạt nắp xuống. Kéo nhẹ
  cáp: không tuột.
- **Thấy gì là đúng:** cáp vào thẳng, nắp đóng kín, không thấy phần tiếp
  điểm vàng lộ ra ngoài.
- **Nếu sai:** nắp không đóng được, hoặc cáp vào lệch → mở nắp, rút ra,
  làm lại. Không ấn mạnh. Ba lần không được thì cắm lại module cũ và báo.

## N4 — Đọc PID để biết cảm biến thật

- **Ở đâu:** VS Code, Git Bash tại `/d/scanner3d`; bo cắm cổng USB-UART
  (COM9 theo `ENVIRONMENT.md`).
- **Làm gì:** nạp và chạy `firmware/esp32s3/CameraWebServerTest` đúng
  như mọi lần (Arduino IDE, nhớ nhìn menu `Tools > PSRAM` phải là `OPI
  PSRAM`). Mở Serial Monitor 115200 và đọc các dòng đầu khi bo khởi
  động. Rồi lấy trạng thái qua mạng:
  ```bash
  cd /d/scanner3d
  .venv/Scripts/python.exe -c "import requests,json;print(json.dumps(requests.get('http://<IP-cua-bo>/status',timeout=5).json(),indent=1)[:800])"
  ```
- **Thấy gì là đúng:** một trong hai kết quả, cả hai đều là thông tin:
  - Serial in PID `0x5640` hoặc dòng có chữ `OV5640` → cảm biến là
    OV5640, khác OV3660 hiện dùng.
  - Serial báo lỗi dò cảm biến (`Camera probe failed`, `camera init
    failed`) → **không phải hỏng module**; nhiều khả năng bản thư viện
    `esp32-camera` đang biên dịch chưa bật hỗ trợ OV5640. Đây là **đầu
    việc mã**, mở chặng Planner, không tự sửa.
- **Nếu sai:** không lên Wi-Fi, không có dòng nào → chép **toàn bộ** log
  Serial từ lúc cắm điện và gửi lại; cắm lại module cũ nếu cần bo chạy
  ngay. Module hoặc bo **nóng bất thường** khi chạm tay, hoặc bo khởi động
  lại liên tục → rút USB ngay, cắm lại module cũ theo N7 và báo; thứ tự chân
  của FD5640 chưa có tài liệu (chỉ biết cùng 24 chân).

## N5 — Chụp thử ở 250 mm để so với OV3660

- **Ở đâu:** bố trí y như `docs/procedures/quy-trinh-khao-sat-quang-hoc.md`
  phần A (khối gỗ + thước, đèn phòng), khoảng cách 250 mm.
- **Làm gì:** chạy đúng lệnh phiên chụp của quy trình đó nhưng đặt
  `--session-id capture_fd5640_250mm`, `--note "FD5640 500W-V11, 250 mm,
  bo tri nhu 17/09"`.
  Lệnh nguyên văn cho Git Bash (thay `192.168.31.9` nếu Serial N4 in IP
  khác; giữ VGA để so được với ba phiên 17/09):
  ```bash
  cd /d/scanner3d
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_fd5640_250mm --meta-copy docs/logs --note "FD5640 500W-V11, 250 mm, bo tri nhu 17/09; den phong"
  ```
  Không dùng `--profile`: mọi hồ sơ trong `data/calibration/camera_profiles/`
  gắn với OV3660.
- **Thấy gì là đúng:** 5 ảnh PASS trong `data/raw/capture_fd5640_250mm/`.
  Mở một ảnh, phóng to vào thước: thấy được vạch mm riêng rẽ là dấu hiệu
  tốt (OV3660 ngày 17/09 không thấy).
- **Ảnh mờ không có nghĩa module hỏng.** Firmware hiện không điều khiển
  lấy nét tự động; module AF khi cuộn lấy nét (VCM) không được cấp dòng
  thường đứng ở vị trí nét xa — GIẢ THUYẾT, chưa kiểm. Nếu mờ, việc tiếp
  theo là một đầu việc mã: nạp firmware lấy nét cho OV5640 hoặc đặt vị trí
  VCM cố định (cũng là cách khoá tiêu điểm khi quét). Chụp thêm một phiên
  ở 350 mm cùng lệnh, đổi `250` thành `350` trong `--session-id` và
  `--note`, để biết điểm nét nằm gần hay xa.
- **Nếu sai:** lỗi giống các lần trước thì theo phần F của quy trình
  khảo sát quang học. Trùng `--session-id` thì thêm `_lan2`, không xoá thư
  mục cũ.

## N6 — Gửi lại

Ảnh N1, ba câu trả lời N2, log Serial N4, tên phiên chụp N5. Phiên viết
sẽ đo lại độ nét bằng `pc/sharpness.py` và `pc/ruler_ticks.py`, so với
bảng 17/09, rồi ghi `docs/HARDWARE.md` và `docs/tests/`.

## N7 — Lắp lại OV3660 (khi cần bo cho việc khác)

- **Ở đâu:** bo ESP32-S3; ảnh N0.
- **Làm gì:** rút USB, chờ đèn tắt; mở nắp FPC; rút FD5640, cất túi ghi
  "FD5640 — đã thử"; cắm lại OV3660 đúng hướng như ảnh N0; đóng nắp; cắm
  USB, xem Serial in `Camera PID: 0x3660`.
- **Thấy gì là đúng:** PID `0x3660`, trang web lên như trước.
- **Nếu sai:** PID khác hoặc lỗi dò cảm biến → mở nắp, cắm lại cho thẳng;
  vẫn lỗi thì gửi log Serial.

Giữ FD5640 trên bo hay lắp lại OV3660 là quyết định sau N6, ghi
`DECISIONS.md`. Các việc C5/C7 và A1 dùng camera nào phải theo quyết định
đó; không dùng lẫn hồ sơ hiệu chuẩn giữa hai cảm biến.

## Điều phải quyết trước khi dùng FD5640 cho việc quét

Ghi ở đây để không quên, **không phải việc của người dùng lúc nhận
hàng**:

- Nếu module **tự động lấy nét thật**: chu trình quét đòi tham số ảnh cố
  định trong suốt một phiên (`docs/SPEC.md` mục 13–15; C2 đang khoá hồ sơ
  camera). Tiêu điểm tự đổi giữa các góc quay sẽ làm hỏng hiệu chuẩn.
  Phải khoá được tiêu điểm (lấy nét một lần rồi tắt AF) thì mới dùng
  được; chưa biết firmware hiện tại làm được không → việc của chặng
  Planner.
- Đổi cảm biến là **đổi hồ sơ hiệu chuẩn**: mọi ảnh và số đo cũ gắn với
  OV3660, không dùng lẫn (`docs/PROCESS.md` R9, R10).
- Quyết định "đổi hẳn sang FD5640 hay giữ OV3660" là của người dùng, ghi
  `DECISIONS.md` khi có số đo N5 so với bảng 17/09.

## Phần P03 — Thu bổ sung ổn định/tiêu điểm cố định (S3, S4) và quy ước phần nhiệt (S5)

Thực hiện theo `handoff/2026-10-09_p03_fd5640-danh-gia/01_PLAN.md` Vòng 3 và
`docs/SPEC.md` §10.3 (D076, D077, D080).

- **Trạng thái tại 250 mm (ĐÃ THU XONG — không chụp lại `r2/r3`):** Đã có đủ 6 phiên × 5 ảnh = **30/30 ảnh PASS** (`capture_p03_fd5640_250mm_r1` ngày 11/10 và `r2`–`r6` ngày 12/10), kèm văn bản chép từ `Serial Monitor` (`docs/logs/serial_fd5640_p03_20261012.txt`) và ảnh bố trí (`docs/logs/p03-bo-tri-250mm-2026-10-12.jpg`). Bộ 15 ảnh `r4 + r5 + r6` cùng bố trí đã được dùng để chấm S4 tại 250 mm.
- **Trạng thái tại 200 mm:** Đã có phiên `capture_fd5640_250mm` (5/5 ảnh thực tế ở 200 mm) đủ để chấm S1, S2 và 1 phiên S3 tại 200 mm. Riêng tiêu chí **S4 tại 200 mm** hiện là `CHƯA ĐỦ DỮ LIỆU` vì cần **3 phiên mới × 5 ảnh = 15 ảnh cùng bố trí ở 200 mm** (`capture_p03_fd5640_200mm_r1`, `capture_p03_fd5640_200mm_r2`, `capture_p03_fd5640_200mm_r3`; không ghép 5 ảnh cũ vào bộ S4 mới vì bố trí đã chuyển sang 250 mm sau đó). Theo `01_PLAN.md` Vòng 3 mục 2, do S2 ở 200 mm và S1/S2/S4 ở 250 mm đã có kết quả `CHƯA ĐẠT`, việc thu thêm 3 phiên ở 200 mm bên dưới **không bắt buộc trước khi bàn giao mốc `B_A`**, chỉ thực hiện khi bạn cần đóng trạng thái `CHƯA ĐỦ DỮ LIỆU` của S4 tại 200 mm.
- **Lưu ý bảo vệ phần cứng:** Chỉ cắm nguồn USB khi đã chuẩn bị xong lệnh chụp; rút USB ngay sau khi chụp xong; không chạm tay vào module camera hay bo khi vừa chạy.

### P03.1 — Kiểm tra bố trí cố định 200 mm và đọc IP hiện tại trên Serial

- **Ở đâu:** Bàn làm việc (khối gỗ 30×32×49 mm đặt trên bệ 20 mm, thước nhựa
  dựng đứng thẳng hàng sát mặt trước khối, vạch 0 ở dưới như ngày 17/09); phần
  mềm Arduino IDE 2.3.10, cửa sổ `Serial Monitor` (`115200 baud`, cổng `COM9`
  theo `ENVIRONMENT.md`).
- **Làm gì:**
  1. Dùng thước đo trên mặt bàn từ hình chiếu **mặt trước ống kính** (mốc 0)
     tới mặt trước khối gỗ đúng **200 mm**. Giữ mặt trước khối gỗ và mặt thước
     vuông góc với trục quang học của camera; cố định gá kẹp bo và vị trí ống
     kính của module FD5640; không vặn ống kính và không chạy bất kỳ thao tác
     lấy nét nào trong suốt cả 3 phiên `r1`, `r2`, `r3`.
  2. Đóng toàn bộ tab trình duyệt web đang mở địa chỉ của bo ESP32-S3 để đảm bảo
     tắt hẳn luồng stream MJPEG.
  3. Cắm cáp USB vào cổng UART của bo ESP32-S3, bấm nút `RST` trên bo nếu cần
     và đọc dòng địa chỉ IP in ra trên `Serial Monitor` (DHCP có thể cấp IP
     khác `192.168.31.9` giữa các lần bật). Ghi nhận mọi lần khởi động/reset
     của bo, đóng `Serial Monitor` hoặc giữ yên và chuyển ngay sang bước P03.2.
- **Thấy gì là đúng:** `Serial Monitor` in các dòng khởi tạo thành công (tương tự
  bản chép ngày 12/10 trong `docs/logs/serial_fd5640_p03_20261012.txt`):
  ```text
  Camera Init OK: fb_count=1, grab_mode=1, fb_location=0
  Camera PID: 0x5640
  WiFi connected, IP <IP-cua-bo>
  Camera Ready! Use 'http://<IP-cua-bo>' to connect
  ```
- **Nếu sai:** Báo `Camera init failed` hoặc `WiFi connect FAILED` → rút cáp
  USB ngay, chờ 10 giây, kiểm tra lại cáp FPC theo bước N3 rồi cắm lại; nếu
  thấy mùi khét, biến dạng hoặc nóng bất thường thì rút cáp USB ngay lập tức,
  không chạm tay vào module và gửi lại toàn bộ chữ trên `Serial Monitor`.

### P03.2 — Chụp phiên lặp thứ nhất và thứ hai ở 200 mm (`capture_p03_fd5640_200mm_r1`, `r2`)

- **Ở đâu:** Cửa sổ terminal `Git Bash` trong VS Code (hoặc `PowerShell` ở khối
  riêng bên dưới), chạy tại thư mục cây làm việc riêng
  `D:\scanner3d\.worktrees\p03-fd5640`.
- **Làm gì:** Chạy lần lượt 2 lệnh thu 5 ảnh VGA cách nhau 3 giây ở **200 mm**
  bằng đường dẫn Python tuyệt đối của cây chung và thư mục ảnh thô tuyệt đối
  `D:/datascanner3d/raw` (thay `<IP-cua-bo>` bằng địa chỉ IP vừa đọc ở P03.1;
  **không** dùng cờ `--profile`; **không** sửa hay xoá thư mục
  `capture_fd5640_250mm` hoặc các thư mục `r1`–`r6` đã có).

  Lệnh cho **Git Bash**:
  ```bash
  cd /d/scanner3d/.worktrees/p03-fd5640
  D:/scanner3d/.venv/Scripts/python.exe -B pc/capture_session.py --host <IP-cua-bo> --framesize VGA --count 5 --interval 3 --warmup 5 --out D:/datascanner3d/raw --meta-copy docs/logs --session-id capture_p03_fd5640_200mm_r1 --note "FD5640 500W-V11, 200 mm that (do tu mat truoc ong kinh), r1 bo S4 200 mm; den phong"
  D:/scanner3d/.venv/Scripts/python.exe -B pc/capture_session.py --host <IP-cua-bo> --framesize VGA --count 5 --interval 3 --warmup 5 --out D:/datascanner3d/raw --meta-copy docs/logs --session-id capture_p03_fd5640_200mm_r2 --note "FD5640 500W-V11, 200 mm that (do tu mat truoc ong kinh), r2 cung bo tri/tieu diem voi r1; den phong"
  ```

  Lệnh cho **PowerShell** (chỉ dùng nếu bạn mở terminal PowerShell):
  ```powershell
  Set-Location D:\scanner3d\.worktrees\p03-fd5640
  & "D:/scanner3d/.venv/Scripts/python.exe" -B pc/capture_session.py --host <IP-cua-bo> --framesize VGA --count 5 --interval 3 --warmup 5 --out D:/datascanner3d/raw --meta-copy docs/logs --session-id capture_p03_fd5640_200mm_r1 --note "FD5640 500W-V11, 200 mm that (do tu mat truoc ong kinh), r1 bo S4 200 mm; den phong"
  & "D:/scanner3d/.venv/Scripts/python.exe" -B pc/capture_session.py --host <IP-cua-bo> --framesize VGA --count 5 --interval 3 --warmup 5 --out D:/datascanner3d/raw --meta-copy docs/logs --session-id capture_p03_fd5640_200mm_r2 --note "FD5640 500W-V11, 200 mm that (do tu mat truoc ong kinh), r2 cung bo tri/tieu diem voi r1; den phong"
  ```
- **Thấy gì là đúng:** Với cả hai phiên `r1` và `r2`, terminal in báo cáo kết thúc:
  ```text
  Framesize: VGA, kich thuoc mong doi (640, 480)
  Ket qua: PASS
    anh dat/yeu cau       : 5/5
    tong so lan chup lai  : 0
    loi ket noi           : 0
    nghi reset (ts lui)   : 0
    bang chung kiem reset : 4/4 phep so timestamp
    anh trung anh truoc   : 0
    X-Timestamp trung     : 0
  ```
  Trong `D:/datascanner3d/raw/capture_p03_fd5640_200mm_r1/` và `r2/` có đủ 5 ảnh
  `img_0001.jpg`..`img_0005.jpg` cùng 7 tệp metadata, và bản sao 7 tệp metadata
  nằm trong `D:/scanner3d/.worktrees/p03-fd5640/docs/logs/`.
- **Nếu sai:** Nếu báo `Ket qua: FAIL`, lỗi kết nối HTTP hoặc trùng tên thư mục →
  **không xoá** thư mục vừa chạy (để bảo toàn `attempts.jsonl` và ảnh lỗi theo
  mục 6 kế hoạch); kiểm tra lại IP/Wi-Fi, rồi chạy lại với `--session-id` mới
  (thêm hậu tố `_lan2`) và gửi lại cả hai tên phiên cùng toàn bộ chữ in trên terminal.

### P03.3 — Chụp phiên lặp thứ ba ở 200 mm (`capture_p03_fd5640_200mm_r3`) và ngắt nguồn

- **Ở đâu:** Cùng cửa sổ terminal `Git Bash` (hoặc `PowerShell`) tại
  `D:\scanner3d\.worktrees\p03-fd5640`; giữ nguyên hoàn toàn vị trí khối gỗ,
  thước, ánh sáng, gá kẹp và ống kính như ở P03.2.
- **Làm gì:** Chạy tiếp lệnh thu phiên lặp thứ ba ở 200 mm (`r3`), sau đó **rút
  cáp USB khỏi bo ESP32-S3 ngay khi lệnh báo xong** để bo và camera nghỉ.

  Lệnh cho **Git Bash**:
  ```bash
  cd /d/scanner3d/.worktrees/p03-fd5640
  D:/scanner3d/.venv/Scripts/python.exe -B pc/capture_session.py --host <IP-cua-bo> --framesize VGA --count 5 --interval 3 --warmup 5 --out D:/datascanner3d/raw --meta-copy docs/logs --session-id capture_p03_fd5640_200mm_r3 --note "FD5640 500W-V11, 200 mm that (do tu mat truoc ong kinh), r3 cung bo tri/tieu diem voi r1-r2; den phong"
  ```

  Lệnh cho **PowerShell** (chỉ dùng nếu bạn mở terminal PowerShell):
  ```powershell
  Set-Location D:\scanner3d\.worktrees\p03-fd5640
  & "D:/scanner3d/.venv/Scripts/python.exe" -B pc/capture_session.py --host <IP-cua-bo> --framesize VGA --count 5 --interval 3 --warmup 5 --out D:/datascanner3d/raw --meta-copy docs/logs --session-id capture_p03_fd5640_200mm_r3 --note "FD5640 500W-V11, 200 mm that (do tu mat truoc ong kinh), r3 cung bo tri/tieu diem voi r1-r2; den phong"
  ```
- **Thấy gì là đúng:** Terminal in `Ket qua: PASS`, `anh dat/yeu cau : 5/5`,
  `tong so lan chup lai : 0`, `loi ket noi : 0`, `nghi reset (ts lui) : 0`,
  `bang chung kiem reset : 4/4 phep so timestamp`, `anh trung anh truoc : 0`,
  `X-Timestamp trung : 0`. Có đủ 5 ảnh JPEG trong
  `D:/datascanner3d/raw/capture_p03_fd5640_200mm_r3/` và 7 tệp metadata trong
  `D:/scanner3d/.worktrees/p03-fd5640/docs/logs/capture_p03_fd5640_200mm_r3/`.
  Sau khi rút cáp USB, đèn nguồn trên bo tắt hẳn.
- **Nếu sai:** Giữ nguyên thư mục lỗi, không xoá; nếu chụp lại thì đặt
  `--session-id capture_p03_fd5640_200mm_r3_lan2` và báo lại thông báo lỗi.

### P03.4 — Ghi nhận bằng chứng cố định tiêu điểm ở 200 mm (S4) và gửi kết quả

- **Ở đâu:** Bàn làm việc (điện thoại chụp ảnh) và cửa sổ chat.
- **Làm gì:**
  1. Chụp **1 ảnh bố trí ở 200 mm** nhìn ngang thấy rõ mặt trước ống kính FD5640,
     vạch 200 mm trên bàn, thước và khối gỗ (tương tự ảnh 250 mm đã lưu ở
     `docs/logs/p03-bo-tri-250mm-2026-10-12.jpg`).
  2. Nhắn lại cho trợ lý 4 thông tin xác nhận cho tiêu chí S4 tại 200 mm
     (`docs/SPEC.md` §10.3): (a) tên 3 phiên vừa chụp
     (`capture_p03_fd5640_200mm_r1`..`r3`); (b) giữa `r1`, `r2`, `r3` vị trí gá,
     khoảng cách 200 mm và ống kính có giữ nguyên (không chỉnh tay, không chạy
     lấy nét) hay không; (c) có rút/cắm lại nguồn USB hay tháo/lắp cáp FPC giữa
     các phiên đó không (ghi rõ mọi lần khởi động); (d) bản firmware trên bo có
     giữ nguyên không.
- **Thấy gì là đúng:** Có ảnh bố trí 200 mm rõ nét và tin nhắn trả lời đủ 4 ý
  (a)–(d); 3 thư mục metadata mới nằm trong
  `D:/scanner3d/.worktrees/p03-fd5640/docs/logs/`.
- **Nếu sai:** Nếu gá kẹp, khối gỗ hoặc ống kính bị xê dịch giữa các phiên thì
  ghi rõ trong tin nhắn và chụp bổ sung phiên mới cùng bố trí để đủ bộ 3 phiên
  (15 ảnh) đồng nhất cho S4 tại 200 mm, không ghép chung phiên khác bố trí.

### P03.5 — Phép so chỉ báo tăng nhiệt chip ESP32-S3 (S5 — CHỜ ĐẦU VIỆC P15 QUA CỔNG)

- **Trạng thái hiện tại:** **CHƯA THỰC HIỆN Ở PHẦN A.** Theo quyết định D077, D080 và
  `01_PLAN.md` Vòng 3 mục 5, tiêu chí S5 dùng cảm biến nhiệt bên trong chip
  ESP32-S3 làm chỉ báo tương đối giữa OV3660 và FD5640, phụ thuộc vào đầu việc
  `handoff/2026-10-11_p15_nhiet-esp32s3-chi-bao` (hiện `p15` mới ở trạng thái
  `SẴN SÀNG CHO TESTER`, chưa qua cổng Reviewer/bo).
- **Hợp đồng dữ liệu S5 đồng bộ với `p15` Vòng 2 (`01_PLAN.md` Vòng 3 mục 5):**
  - Chỉ nhận phản hồi HTTP `200`, `valid=true`, `temperature_c` hữu hạn trong
    `[−10, 80] °C`, `configured_min_c=-10`, `configured_max_c=80`, có boot ID và
    uptime phù hợp (đây là dải cấu hình/kiểm ứng dụng, không phải dải phần cứng
    đã đọc từng mẫu; **bỏ** yêu cầu `range_reg`/`range_min`/`max`/`error_max`
    từng mẫu, giao dải động, cửa sổ `−5…75 °C` và biên tham khảo `4 °C` của
    Vòng 2).
  - Giữ 3 cặp lượt `OV/FD` đổi thứ tự (`OV→FD`, `FD→OV`, `OV→FD`) trên cùng
    chip/bo/firmware/tải chụp (40 ảnh VGA q10 cách 3 s, tắt stream)/điều kiện;
    hai baseline `t0` trong một cặp chênh `≤ 2 °C`; 6 mốc thời gian
    `0, 5, 15, 30, 60, 120 s` (sai lệch thời điểm thực `≤ 2 s`).
  - Với `d(k,t) = [T_FD(k,t) − T_FD(k,0)] − [T_OV(k,t) − T_OV(k,0)]` và
    `D_k = max_{t ∈ {5,15,30,60,120}} d(k,t)`: đủ mẫu hợp lệ cả 3 cặp và mọi
    `D_k ≤ 5 °C` → `ĐẠT theo chỉ báo`; có cặp đầy đủ `D_k > 5 °C` →
    `CHƯA ĐẠT theo chỉ báo`; thiếu/lỗi/reset trong lượt/sai thời điểm →
    `CHƯA ĐỦ DỮ LIỆU` (không gán 0, không nội suy, không làm tròn để đạt).
    Nhiệt bề mặt module camera/ổn áp luôn giữ nhãn `CHƯA ĐO`.
- **Quy định bắt buộc trước khi `p15` qua cổng:**
  - Không tự ý gọi các đường dẫn HTTP hay lệnh Serial đọc nhiệt chưa được `p15`
    qua cổng Reviewer và kiểm chứng trên bo.
  - Không dùng tay chạm vào module camera hay bo để ước lượng nhiệt độ.
  - Chỉ sau khi `p15` qua cổng Reviewer và nạp lên bo, Coder P03 mới cập nhật
    mục P03.5 này bằng lệnh thu thực tế của `p15` để thực hiện mốc `B_B`.
