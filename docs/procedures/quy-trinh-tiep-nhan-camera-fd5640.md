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

Viết 2026-09-22 khi người dùng báo đã nhận 2 module. Mục đích: xác định
module có **cắm được vào bo ESP32-S3 WROOM CAM** và **cảm biến thật là
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
