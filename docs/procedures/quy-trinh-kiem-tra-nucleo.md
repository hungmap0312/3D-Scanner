# Quy trình kiểm tra Nucleo — ĐÃ LÀM XONG 16/09, giữ để dùng lại

Người dùng đã làm hết A–F tối 16/09, gồm cả dòng `ST-LINK FW`, ảnh bo (đã
vào Git) và xác nhận LED; kết quả trong bảng bằng chứng. Giữ lại vì sẽ dùng lại khi
đổi máy, đổi bo hoặc nạp firmware Nucleo mới ở các tuần sau.

### A. Cắm bo và nhận diện — ĐÃ LÀM 16/09: COM3, ST-LINK FW V2J45M31

**A1. Cắm bo.**
- Ở đâu: cổng USB mini-B trên bo Nucleo, nằm ở mép phía trên, cạnh nút
  reset màu đen và hai jumper; đó là phần ST-LINK của bo (in chữ
  `CN1` bên cạnh). Đầu kia cắm vào cổng USB máy tính.
- Làm gì: cắm vào. Không cắm thêm gì khác vào bo.
- Thấy gì là đúng: LED `LD1` gần cổng USB sáng đỏ hoặc nhấp nháy
  đỏ/xanh vài giây rồi ổn định; LED nguồn `LD3` đỏ sáng. Windows có thể
  hiện một ổ đĩa mới tên `NODE_F446RE` trong File Explorer. LED `LD2`
  xanh lá có thể đang nháy hoặc sáng theo firmware cũ trên bo, không quan
  trọng.
- Nếu sai: không có LED nào sáng → cáp chỉ có dây sạc hoặc cắm chưa
  chặt; đổi cáp khác. Gửi lại: LED nào sáng, có ổ `NODE_F446RE` không.

**A2. Mở terminal Git Bash ở thư mục gốc repo.**
- Ở đâu: VS Code, menu `Terminal > New Terminal`. Nhìn góc phải khung
  terminal: phải ghi `bash` hoặc `Git Bash`; dấu nhắc có dạng
  `bestp@... MINGW64 /d/scanner3d`. Nếu thấy `PS D:\scanner3d>` thì đó là
  PowerShell: bấm mũi tên cạnh dấu `+` ở góc phải khung terminal, chọn
  `Git Bash`.
- Làm gì: gõ `pwd` rồi Enter.
- Thấy gì là đúng: in `/d/scanner3d`.
- Nếu sai: in thư mục khác → gõ `cd /d/scanner3d` rồi Enter, gõ lại `pwd`.

**A3. Hỏi ST-LINK phiên bản firmware.**
- Ở đâu: cùng terminal Git Bash.
- Làm gì: chép nguyên dòng sau, dán, Enter:
  ```
  "/d/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe" -l
  ```
- Thấy gì là đúng: một khối như
  ```
  ===== STLink debug probes =====
  -------- Connected ST-LINK Probes List --------
  ST-LINK Probe 0 :
     ST-LINK SN  : 0670FF...
     ST-LINK FW  : V2J45M30
  ```
  Dòng `ST-LINK FW` là giá trị cần. Nếu thấy thêm `===== UART ... =====`
  liệt kê cổng COM thì ghi luôn.
- Nếu sai: `No ST-LINK detected` hoặc `Error: No debug probe detected`
  → rút cáp, cắm lại, chờ 5 giây, chạy lại. Vẫn không được → mở
  Device Manager (Windows: bấm phím Windows, gõ `Device Manager`, Enter),
  nhìn mục `Universal Serial Bus devices` có `ST-Link Debug` không, và
  mục `Ports (COM & LPT)` có `STMicroelectronics STLink Virtual COM Port`
  không. Gửi lại: toàn bộ dòng in ra, và ảnh chụp hai mục đó của Device
  Manager.

**A4. Tìm cổng COM của Nucleo.**
- Ở đâu: cùng terminal.
- Làm gì: chép nguyên, dán, Enter:
  ```
  .venv/Scripts/python.exe -m serial.tools.list_ports -v
  ```
- Thấy gì là đúng: hai cổng. Một là `COM9` với `desc: USB-Enhanced-SERIAL
  CH343` — đó là bo S3, KHÔNG dùng. Cổng kia có `desc: STMicroelectronics
  STLink Virtual COM Port (COMx)` với `hwid: USB VID:PID=0483:374B` —
  số `COMx` đó là cổng của Nucleo, ghi lại. Nếu bo S3 không cắm thì chỉ
  thấy một cổng ST-LINK.
- Nếu sai: chỉ thấy `COM9` hoặc `0 ports found` → bo chưa được nhận,
  quay lại A3. Lệnh báo `No module named serial` → gõ
  `.venv/Scripts/python.exe -m pip install -r pc/requirements.txt` rồi
  chạy lại. Gửi lại: nguyên văn kết quả lệnh.

**A5. Gửi lại cho tôi** hai giá trị: dòng `ST-LINK FW : ...` và `COMx` của
ST-LINK. Tôi ghi vào `ENVIRONMENT.md`. Nếu tiện, chụp một ảnh mặt trên
bo đủ thấy nhãn `NUCLEO-F446RE` và cổng USB, lưu vào
`docs/logs/nucleo-board-2026-09-16.jpg` cho `docs/HARDWARE.md`.

### B. Nạp firmware NucleoPing — ĐÃ LÀM 16/09, người dùng báo chạy đúng

**B1. Kiểm tra tệp cần nạp có sẵn.**
- Ở đâu: cùng terminal Git Bash tại `/d/scanner3d`.
- Làm gì: chép nguyên, dán, Enter:
  ```
  ls -l firmware/stm32/NucleoPing/build/NucleoPing.bin
  ```
- Thấy gì là đúng: một dòng có `8256` (số byte) và tên tệp. Con số có thể
  khác vài byte nếu tôi đã build lại sau khi ghi hướng dẫn này, nhưng
  phải trong khoảng 8000–9000.
- Nếu sai: `No such file` → tệp build không có trên máy này (thư mục
  `build/` không vào Git). Build lại theo mục "Build trong Git Bash" của
  `firmware/stm32/README.md`: bốn lệnh, chép nguyên từng dòng. Dòng cuối
  phải in bảng `text data bss`. Gửi lại: dòng lỗi nếu có.

**B2. Nạp bằng lệnh.**
- Ở đâu: cùng terminal.
- Làm gì: chép nguyên MỘT dòng dài dưới đây, dán, Enter. Trong lúc chạy
  không rút cáp.
  ```
  "/d/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe" -c port=SWD -w firmware/stm32/NucleoPing/build/NucleoPing.bin 0x08000000 -v -rst
  ```
- Thấy gì là đúng: các dòng lần lượt có `ST-LINK SN`, `Device ID : 0x421`,
  `Device name : STM32F446`, rồi `Memory Programming ...`, `File download
  complete`, `Time elapsed during download operation`, và quan trọng nhất
  `Verification...OK` hoặc `Download verified successfully`. Cuối cùng
  `MCU Reset` hoặc `Software reset is performed`. Ngay sau đó LED `LD2`
  xanh lá trên bo nháy đều: 0,5 giây sáng, 0,5 giây tắt.
- Nếu sai: `Error: No debug probe detected` → quay lại A3. `Error: Target
  not found` hoặc `Unable to connect` → thử thêm `mode=UR` vào lệnh:
  `-c port=SWD mode=UR`, chạy lại. `Error: Verification failed` → chạy
  lại lệnh một lần. LD2 không nháy sau khi nạp xong → bấm nút reset đen
  `B2` trên bo một lần. Gửi lại: toàn bộ dòng in ra của lệnh.

**B3. Cách thay thế nếu B2 không được:** kéo thả. Mở File Explorer, mở ổ
`NODE_F446RE`, kéo tệp `D:\scanner3d\firmware\stm32\NucleoPing\build\NucleoPing.bin`
thả vào ổ đó. Ổ tự biến mất rồi hiện lại sau vài giây, đó là dấu hiệu
nạp xong; LED `LD2` nháy đều. Nếu trong ổ xuất hiện tệp `FAIL.TXT` thì mở
nó và gửi lại nội dung.

### C. Chạy phép thử PING lần 1 — ĐÃ LÀM: FAIL vì lỗi script, sau đó PASS 18:54

**C1. Đóng mọi thứ đang giữ cổng COM.** Serial Monitor của Arduino IDE
(tab Serial Monitor, nếu mở thì đóng), CubeIDE, PuTTY, Tera Term. Cổng
COM của Nucleo chỉ được một chương trình mở một lúc.

**C2. Chạy script.**
- Ở đâu: terminal Git Bash tại `/d/scanner3d`.
- Làm gì: thay `COMx` bằng cổng ghi ở A4, dán, Enter:
  ```
  .venv/Scripts/python.exe pc/nucleo_ping.py --port COMx --count 100 --label run1
  ```
- Thấy gì là đúng: dòng đầu `Phien: ping_2026..._... cong: COMx`; rồi
  `ID? -> ID NUCLEO-F446RE NucleoPing 0.1.0 <hash>`; rồi cứ 10 PING một
  dòng `PING 10 -> PONG 10 uptime ... ms, tre ... ms` cho tới `PING 100`.
  Toàn bộ chạy dưới 15 giây. Trong lúc chạy LED `LD2` nháy loạn hơn bình
  thường vì mỗi PING đảo LED một nhịp. Cuối cùng khối:
  ```
  === TONG KET (gui lai khoi nay) ===
  Phien ping_... (run1) tren cong COMx
  Firmware tra loi ID?: ID NUCLEO-F446RE NucleoPing 0.1.0 ...
  PING gui / PONG dung: 100 / 100 (yeu cau 100)
  Timeout: 0, sai thu tu: 0, dong la: 0
  Uptime bo dau/cuoi (ms): ... / ...
  Tre PC->bo->PC (ms) min/mean/max: ... / ... / ...
  Commit repo: ... (sach)
  Ket qua: PASS
  Ho so: D:\scanner3d\docs\logs\ping_...
  ```
- Nếu sai: `KHONG MO DUOC CONG` → sai số COM hoặc chương trình khác
  đang giữ cổng, xem C1. `ID? -> None` rồi `Ket qua: FAIL - khong nhan
  duoc dong ID hop le` → firmware chưa chạy: kiểm tra LD2 có nháy không,
  bấm reset, chạy lại; vẫn không → gửi lại toàn bộ màn hình. `Ket qua:
  FAIL - timeout o PING n` hoặc `sai thu tu` → KHÔNG chạy lại ngay; gửi
  tôi khối tổng kết và thư mục `docs/logs/ping_...` để tôi xem `pairs.csv`
  trước.

### D. Rút cắm nguồn, nạp lại, chạy lần 2 — ĐÃ LÀM 16/09 19:05, PASS

**D0. Kiểm tra đang ở bản script đã sửa.**
- Ở đâu: terminal Git Bash trong VS Code, tại `/d/scanner3d` (gõ `pwd` để
  chắc).
- Làm gì: chép nguyên, dán, Enter:
  ```
  grep -c "del timeout" pc/nucleo_ping.py
  ```
- Thấy gì là đúng: in `1`.
- Nếu sai: in `0` → bạn đang ở bản cũ; gõ `git status` và gửi lại kết
  quả, đừng chạy tiếp.

**D1. Rút cắm nguồn.** Rút cáp USB khỏi Nucleo, đếm đến 5, mọi LED trên
bo tắt. Cắm lại, chờ khoảng 5 giây cho LED `LD1` cạnh cổng USB ổn định.

**D2. Lấy phiên bản ST-LINK và nạp lại.**
- Ở đâu: cùng terminal.
- Làm gì: chép nguyên hai dòng, dán từng dòng, Enter:
  ```
  "/d/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe" -l
  "/d/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe" -c port=SWD -w firmware/stm32/NucleoPing/build/NucleoPing.bin 0x08000000 -v -rst
  ```
- Thấy gì là đúng: lệnh 1 in khối có `ST-LINK SN` và `ST-LINK FW : V2J...`
  — **chép nguyên dòng `ST-LINK FW`**, đây là giá trị còn thiếu. Lệnh 2
  in `File download complete` và `Verification...OK` hoặc `Download
  verified successfully`, rồi reset; LED `LD2` xanh lá nháy 0,5 s sáng /
  0,5 s tắt.
- Nếu sai: xem bảng E bên dưới: `No ST-LINK detected` → rút cắm
  lại cáp; `Verification failed` → chạy lại lệnh 2 một lần. Gửi lại
  nguyên văn output.

**D3. Chạy script lần 2.**
- Ở đâu: cùng terminal. Không mở Serial Monitor hay CubeIDE.
- Làm gì:
  ```
  .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --count 100 --label run2-sau-rut-nguon
  ```
- Thấy gì là đúng: `ID? -> ID NUCLEO-F446RE NucleoPing 0.1.0 3eccab9`,
  mười dòng `PING 10 ... PING 100`, chạy dưới 10 giây, rồi khối tổng kết
  với `PING gui / PONG dung: 100 / 100` và `Ket qua: PASS`. Dòng
  `Uptime bo dau/cuoi (ms)` phải có số đầu **nhỏ hơn 302799** (uptime
  cuối của phiên 18:54) — thường chỉ vài nghìn tới vài chục nghìn ms vì
  bo vừa reset. Đó là bằng chứng bo chạy lại từ đầu.
- Nếu sai: `ID? -> None` → bấm nút reset đen trên bo, chạy lại một lần.
  `FAIL - timeout` hoặc `sai thu tu` → không chạy lại, gửi khối tổng kết
  và tên thư mục `docs/logs/ping_...`.

**D4. Gửi lại:** dòng `ST-LINK FW : ...`, khối `=== TONG KET ===` của lần
này, và LED `LD2` có nháy đều hay không (một câu). Tôi đọc `pairs.csv`,
đưa thư mục vào Git, đánh dấu chỉ tiêu ĐẠT nếu PASS, rồi gộp nhánh.

### E. Lỗi thường gặp, tra nhanh

| Thấy gì | Nghĩa là | Làm gì |
| --- | --- | --- |
| `No ST-LINK detected` | PC không thấy ST-LINK | Đổi cáp có dây dữ liệu; cắm cổng USB khác trên máy; xem Device Manager |
| Chỉ có `COM9` trong list_ports | Chưa có driver VCP hoặc bo chưa nhận | Xem Device Manager mục Ports; nếu có dấu chấm than vàng thì gửi ảnh |
| `could not open port` / `PermissionError` | Cổng đang bị chương trình khác giữ | Đóng Serial Monitor, CubeIDE, PuTTY; rút cắm lại cáp |
| `ID? -> None` | Bo không trả lời | LD2 có nháy không? Không nháy → chưa nạp được, quay lại B. Có nháy → sai cổng COM |
| PONG có nhưng `sai thu tu` | Mất hoặc dư byte trên đường truyền | Không chạy lại ngay; gửi `pairs.csv` |
| `Ket qua: FAIL - timeout o PING 1` | Bo không nhận được PING 1 hoặc không trả | Bấm reset đen, chạy lại một lần; vẫn vậy thì gửi màn hình |

### F. Gửi lại gì

1. Dòng `ST-LINK FW : ...` và số `COMx` (từ A3, A4).
2. Toàn bộ dòng in ra của lệnh nạp B2 lần đầu (chép từ terminal).
3. Hai khối `=== TONG KET ===` của run1 và run2, chép nguyên.
4. Tên hai thư mục `docs/logs/ping_...` (script đã tự ghi vào repo, tôi
   sẽ tự đọc `pairs.csv`, không cần chép thêm).
5. Ảnh bo nếu chụp được (A5).

Tôi sẽ đối chiếu `pairs.csv`, đưa hai thư mục vào Git, ghi kết quả vào
bảng chỉ tiêu, và chỉ khi cả hai run PASS mới đánh dấu chỉ tiêu B
"Giao tiếp Nucleo" ĐẠT.
