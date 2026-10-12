# Quy trình nạp và kiểm tra Nucleo không tải (Đầu việc C4)

Tài liệu hướng dẫn người dùng nạp firmware phiên bản 0.2.0 (giao thức P1) lên bo STM32 Nucleo-F446RE và kiểm tra an toàn logic trên bo **hoàn toàn không tải** (không nối module laser).

> [!WARNING]
> **AN TOÀN LASER TUYỆT ĐỐI**: Trong đầu việc C4, **KHÔNG ĐƯỢC CẤP NGUỒN HOẶC NỐI MODULE LASER** vào bo Nucleo. Mọi phép đo kiểm tín hiệu điều khiển laser được thực hiện bằng đồng hồ vạn năng (VOM) đo điện áp trên chân tín hiệu PA8 (D7) so với GND.
>
> **LƯU Ý VỀ XUNG ÁP NGẮN (GLITCH)**: Đồng hồ vạn năng hoặc đèn LED không có khả năng phát hiện các xung áp ngắn (cỡ micro-giây) xuất hiện trong quá trình khởi động hoặc chuyển trạng thái GPIO. Phép đo xung ngắn glitch theo Q9 bắt buộc phải thực hiện bằng máy hiện sóng (Oscilloscope) ở bước kiểm tra phần cứng tiếp theo khi có thiết bị.

---

## 1. Chuẩn bị phần cứng và cấu hình chân trên bo

Thực hiện toàn bộ phần đấu nối jumper và điện trở kéo xuống **trước khi** cấp nguồn và chạy bất kỳ lệnh kiểm tra nào.

- **Ở đâu:** Trên các hàng chân header Arduino Uno của bo Nucleo-F446RE:
  - Chân **D7** (`PA8`): Tín hiệu điều khiển laser (`LASER_CTRL`), mức logic 3.3V (HIGH = Bật, LOW = Tắt).
  - Chân **D8** (`PA9`): Tín hiệu cảm biến nguồn laser / cửa an toàn (`SENSE_PWR`), ngõ vào cấu hình không kéo (`GPIO_NOPULL`).
  - Chân **D9** (`PC7`): Tín hiệu nút dừng khẩn cấp (`SENSE_ESTOP`), ngõ vào kéo lên nội (`GPIO_PULLUP`). Tiếp điểm thường đóng NC nối xuống GND.
  - Chân **3V3**: Nguồn 3.3V trên header bo.
  - Chân **GND**: Các chân nối đất GND trên header bo.
- **Làm gì:**
  1. **Nối điện trở kéo xuống ngoài mạch R_down (10 kΩ):** Cắm 1 đầu điện trở 10 kΩ vào chân **D7** (`PA8`), đầu kia cắm vào chân **GND**. *(Bảo đảm chân PA8 luôn được giữ chặt ở 0V kể cả khi chip đang bị reset hoặc chân ở trạng thái trôi nổi).*
  2. **Cắm jumper giả lập tiếp điểm ESTOP nhả (an toàn):** Dùng 1 dây cắm test nối từ chân **D9** (`PC7`) xuống chân **GND**.
  3. **Cắm jumper giả lập cửa đóng / nguồn sẵn sàng:** Dùng 1 dây cắm test nối từ chân **D8** (`PA9`) lên chân **3V3** (do chân PA9 là ngõ vào NOPULL, bắt buộc phải cắm 3V3 để cửa đóng hoặc GND để cửa mở).
  4. **Kẹp que đo VOM:**
     - Que đen cắm vào chân **GND**.
     - Que đỏ chạm vào chân **D7** (`PA8`).
     - Bật thang đo đồng hồ ở mức **DC 20V**.
- **Thấy gì là đúng:** Các dây cắm chắc chắn, que đo tiếp xúc tốt, đồng hồ VOM hiển thị `0.00 V`.
- **Nếu sai:** Chân cắm lỏng lẻo -> cắm lại chặt vào hàng header bo.

---

## 2. Biên dịch và nạp firmware C4 (0.2.0) vào bo

**B1. Kết nối bo Nucleo.**
- **Ở đâu:** Cổng USB Mini-B trên bo Nucleo (cạnh nút reset đen B2).
- **Làm gì:** Cắm cáp USB vào máy tính.
- **Thấy gì là đúng:** LED nguồn `LD3` (đỏ) sáng cố định; LED `LD1` (ST-LINK) nháy rồi sáng ổn định. Windows nhận cổng COM (ví dụ `COM3` hoặc `COM5`).
- **Nếu sai:** LED không sáng -> kiểm tra cáp USB và cổng USB máy tính.

**B2. Biên dịch firmware sạch nhúng Git commit hash thật (BẮT BUỘC).**
- **Ở đâu:** Terminal tại thư mục gốc `d:/scanner3d`.
- **Làm gì:** Xoá sạch thư mục build cũ và gọi `make.exe` của CubeIDE với commit hash hiện tại:
  - Bản cho **Git Bash**:
    ```bash
    rm -rf firmware/stm32/NucleoPing/build/c4-20260930
    "/c/ST/STM32CubeIDE_1.17.0/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.0.202409170845/tools/bin/make.exe" -C firmware/stm32/NucleoPing GCC_PATH="C:/ST/STM32CubeIDE_1.17.0/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.12.3.rel1.win32_1.1.0.202410251130/tools/bin" BUILD_DIR="build/c4-20260930" FW_GIT=$(git rev-parse --short HEAD) -j4
    ```
  - Bản cho **PowerShell**:
    ```powershell
    if (Test-Path firmware\stm32\NucleoPing\build\c4-20260930) { Remove-Item -Recurse -Force firmware\stm32\NucleoPing\build\c4-20260930 }
    & "C:\ST\STM32CubeIDE_1.17.0\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.0.202409170845\tools\bin\make.exe" -C firmware/stm32/NucleoPing GCC_PATH="C:/ST/STM32CubeIDE_1.17.0/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.12.3.rel1.win32_1.1.0.202410251130/tools/bin" BUILD_DIR="build/c4-20260930" FW_GIT=$((git rev-parse --short HEAD).Trim()) -j4
    ```
- **Thấy gì là đúng:** Biên dịch hoàn tất không lỗi, sinh file `firmware/stm32/NucleoPing/build/c4-20260930/NucleoPing.bin`.

**B3. Nạp file binary `build/c4-20260930/NucleoPing.bin`.**
- **Ở đâu:** Terminal tại thư mục gốc `d:/scanner3d`.
- **Làm gì:** Chạy lệnh nạp qua STM32CubeProgrammer CLI:
  - Bản cho **Git Bash**:
    ```bash
    "/d/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe" -c port=SWD -w firmware/stm32/NucleoPing/build/c4-20260930/NucleoPing.bin 0x08000000 -v -rst
    ```
  - Bản cho **PowerShell**:
    ```powershell
    & "D:\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe" -c port=SWD -w "firmware\stm32\NucleoPing\build\c4-20260930\NucleoPing.bin" 0x08000000 -v -rst
    ```
- **Thấy gì là đúng:** Cuối output in dòng:
  ```text
  Download verified successfully
  File download complete
  Time elapsed...
  RUNNING Program...
  ```
  Và LED xanh `LD2` trên bo bắt đầu nhấp nháy chu kỳ 1 giây (500 ms ON / 500 ms OFF).
- **Nếu sai:** Báo lỗi `No debug probe detected` -> rút cáp USB cắm lại chặt, kiểm tra Device Manager.

---

## 3. Kiểm tra khởi động và tương thích ngược (Regression Legacy)

**C1. Chạy 10 lượt PING kế thừa.**
- **Ở đâu:** Terminal tại thư mục gốc `d:/scanner3d`.
- **Làm gì:** Chạy lệnh:
  - Cho **Git Bash**:
    ```bash
    .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --count 10
    ```
  - Cho **PowerShell**:
    ```powershell
    python pc\nucleo_ping.py --port COM3 --count 10
    ```
  *(Thay `COM3` bằng cổng COM thực tế của bo Nucleo).*
- **Thấy gì là đúng:**
  ```text
  ID? -> ID NUCLEO-F446RE NucleoPing 0.2.0 <git>
  ...
  PING 10 -> PONG 10 uptime ... ms, tre ... ms
  Ket qua: PASS
  ```
- **Nếu sai:** Báo lỗi `KHONG MO DUOC CONG` -> kiểm tra đúng số hiệu cổng COM trong Device Manager và tắt các chương trình đang chiếm cổng COM (CubeIDE, PuTTY, v.v.).

---

## 4. Chạy chuỗi kiểm tra giao thức P1 tự động

**D1. Thực hiện kịch bản kiểm tra P1 tự động.**
- **Ở đâu:** Terminal tại thư mục gốc `d:/scanner3d`.
- **Làm gì:** Chạy lệnh:
  - Cho **Git Bash**:
    ```bash
    .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --p1
    ```
  - Cho **PowerShell**:
    ```powershell
    python pc\nucleo_ping.py --port COM3 --p1
    ```
- **Thấy gì là đúng:** Nhờ đã cắm D9->GND và D8->3V3 ở Mục 1, output hiển thị toàn bộ các bài kiểm tra đều đạt `PASS` (mọi phản hồi `STATUS` đều mang đúng schema 10 token Q3 gồm `remaining_ms`):
  ```text
  === KIEM TRA GIAO THUC P1 TREN BO NUCLEO KHONG TAI ===
  1. ID? -> ID NUCLEO-F446RE NucleoPing 0.2.0 ...
  Gui: 1 STATUS*05 (Trang thai khoi dau IDLE)
  ...
  PASS: Bat laser (5000 ms)
  PASS: Kiem tra trang thai CAPTURING
  PASS: Gui Heartbeat 1 giay
  PASS: Kiem tra duy tri CAPTURING
  PASS: Tat laser
  PASS: Kiem tra duplicate seq 6
  PASS: Kiem tra tro ve IDLE
  PASS: Lenh STOP chuyen sang PAUSED
  PASS: Lenh CLEAR tro ve IDLE
  PASS: Lenh HOME tra ERROR NOTIMPL
  PASS: Lenh MOVE_ABS tra ERROR NOTIMPL
  === TAT CA CAC PHEP THU P1 DEU DAT ===
  ```
- **Nếu sai:** Nếu có bước nào báo FAIL, hoặc gặp lỗi I/O / lỗi phản hồi (mất, sai checksum, sai seq, sai schema) sau khi đã gửi `LASER ON`, công cụ kích hoạt cơ chế an toàn R03/R05: dừng chuỗi ngay lập tức, tự động gửi `LASER OFF` với seq mới để cứu hộ và đọc lại `STATUS` xác nhận `laser=0` (PA8 thấp) trước khi đóng cổng, giữ nguyên kết quả thất bại (mã thoát khác 0). Nếu không xác nhận được (hoặc cổng mất hẳn), công cụ in cảnh báo nguy hiểm yêu cầu người vận hành nhìn VOM 0.00V và chờ timeout độc lập 3 s / 5 s của bo. Khi gặp FAIL, tuyệt đối không gửi lại ON ngay; người vận hành cần kiểm tra lại tiếp xúc dây cắm D9/D8, gửi lệnh `CLEAR` để đưa bo về IDLE và bắt đầu một lần thử mới từ đầu.

---

## 5. Đo kiểm các nhánh an toàn thủ công (Thực hiện mỗi ca ≥ 3 lần)

Trong các bước dưới đây, sử dụng cờ `--cmd` của công cụ `pc/nucleo_ping.py` để gửi trực tiếp từng lệnh P1 (công cụ tự động tăng sequence và tính XOR checksum `*<HH>\n`).

### Phép thử 1: Bật / Tắt Laser chủ động
- **Ở đâu:** Terminal máy tính và đồng hồ VOM đo chân PA8 (D7).
- **Làm gì:**
  *(Lưu ý: Dùng lệnh nối chuỗi có khoảng chờ 1 giây để quan sát VOM và bảo đảm lệnh OFF tới bo trước ngưỡng mất liên lạc 3.0 giây `LINK_LOST`).*
  - Cho **Git Bash**:
    ```bash
    .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "10 LASER ON"; sleep 1; .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "11 LASER OFF"; .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "STATUS"
    ```
  - Cho **PowerShell**:
    ```powershell
    python pc\nucleo_ping.py --port COM3 --cmd "10 LASER ON"; Start-Sleep -Seconds 1; python pc\nucleo_ping.py --port COM3 --cmd "11 LASER OFF"; python pc\nucleo_ping.py --port COM3 --cmd "STATUS"
    ```
- **Thấy gì là đúng:**
  - Sau lệnh ON: bo phản hồi `10 DONE ON 5000*...`, VOM lập tức nhảy lên mức **3.2 V – 3.3 V**.
  - Sau lệnh OFF: bo phản hồi `11 DONE OFF 0*...`, VOM lập tức hạ về **0.00 V**.
  - Lệnh STATUS cuối phản hồi: `... DONE IDLE 0 0 1 0 0 <uptime> NONE 0*...`, xác nhận bo đã trở về trạng thái IDLE sẵn sàng, laser đã tắt và `remaining_ms=0` (không bị dính lỗi ngầm `LINK_LOST`).
- **Nếu sai:** VOM không nhảy lên ~3.3V hoặc không hạ về 0V -> kiểm tra que đo.

### Phép thử 2: Mất liên lạc UART (Timeout `T_hb = 3000 ms`)
- **Ở đâu:** Terminal máy tính và đồng hồ VOM đo chân PA8 (D7).
- **Làm gì:**
  - Cho **Git Bash**:
    ```bash
    .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "20 LASER ON"
    # GIỮ NGUYÊN NGUỒN BO (không rút cáp USB), không gửi gì trong 3.5 giây.
    # Sau đó kiểm tra trạng thái và xoá lỗi:
    .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "21 STATUS"
    .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "22 CLEAR"
    ```
  - Cho **PowerShell**:
    ```powershell
    python pc\nucleo_ping.py --port COM3 --cmd "20 LASER ON"
    # GIỮ NGUYÊN NGUỒN BO (không rút cáp USB), không gửi gì trong 3.5 giây.
    # Sau đó kiểm tra trạng thái và xoá lỗi:
    python pc\nucleo_ping.py --port COM3 --cmd "21 STATUS"
    python pc\nucleo_ping.py --port COM3 --cmd "22 CLEAR"
    ```
- **Thấy gì là đúng:**
  - VOM giữ ~3.3V trong đúng 3.0 giây, sau đó tự động sụt về **0.00 V** tại thời điểm 3000 ms.
  - Lệnh STATUS phản hồi: `21 DONE ERROR 0 0 1 0 0 <uptime> LINK_LOST 0*...` (đủ 10 token theo Q3, laser=0, `remaining_ms=0`).
  - Lệnh CLEAR phản hồi: `22 DONE IDLE*...` và đưa bo về trạng thái sẵn sàng.
- **Nếu sai:** Sau 3.0 giây laser không tắt -> vi phạm an toàn mất liên lạc, báo cáo ngay.

### Phép thử 3: Hết hạn bật Laser tối đa (Timeout `T_laser_max = 5000 ms`)
- **Ở đâu:** Terminal máy tính và đồng hồ VOM đo chân PA8 (D7).
- **Làm gì:**
  - **Cách A (Tự động — Khuyến nghị để tránh độ trễ tay):**
    - Cho **Git Bash**:
      ```bash
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --test-laser-timeout
      ```
    - Cho **PowerShell**:
      ```powershell
      python pc\nucleo_ping.py --port COM3 --test-laser-timeout
      ```
    *(Công cụ tự động bật laser và gửi HEARTBEAT đều đặn mỗi 1.0 giây trong 6 giây, in trạng thái từng giây và tự động kiểm tra STATUS ở giây thứ 6).*
  - **Cách B (Thủ công với lệnh rời rạc):**
    *(Lưu ý: Các lệnh HEARTBEAT gửi cách nhau ~1.0 giây để duy trì liên lạc. Lệnh STATUS chỉ gửi sau giây thứ 5.5 khi laser đã hết hạn).*
    - Cho **Git Bash**:
      ```bash
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "30 LASER ON"
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "31 HEARTBEAT"
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "32 HEARTBEAT"
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "33 HEARTBEAT"
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "34 HEARTBEAT"
      # Chờ qua giây thứ 5.5 rồi kiểm tra STATUS:
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "35 STATUS"
      ```
    - Cho **PowerShell**:
      ```powershell
      python pc\nucleo_ping.py --port COM3 --cmd "30 LASER ON"
      python pc\nucleo_ping.py --port COM3 --cmd "31 HEARTBEAT"
      python pc\nucleo_ping.py --port COM3 --cmd "32 HEARTBEAT"
      python pc\nucleo_ping.py --port COM3 --cmd "33 HEARTBEAT"
      python pc\nucleo_ping.py --port COM3 --cmd "34 HEARTBEAT"
      # Chờ qua giây thứ 5.5 rồi kiểm tra STATUS:
      python pc\nucleo_ping.py --port COM3 --cmd "35 STATUS"
      ```
- **Thấy gì là đúng:**
  - Dù vẫn nhận HEARTBEAT đều đặn mỗi 1 giây, đúng tại thời điểm 5.0 giây tính từ lúc ON, điện áp trên VOM tự động sụt về **0.00 V**.
  - Lệnh STATUS phản hồi: `... DONE IDLE 0 0 1 0 0 <uptime> LASER_TIMEOUT 0*...` (đủ 10 token theo Q3, bo về IDLE chứ không vào ERROR, ghi nhận lỗi cảnh báo `LASER_TIMEOUT`, `remaining_ms=0`).
- **Nếu sai:** Quá 5.0 giây mà VOM vẫn ở 3.3V -> vi phạm an toàn giới hạn thời gian laser. Nếu trong quá trình chạy xuất hiện lỗi I/O, lỗi phản hồi sai/mất (kể cả ở phản hồi ON hoặc HEARTBEAT), công cụ kích hoạt cơ chế an toàn R03/R05: dừng chuỗi ngay lập tức, tự động gửi `LASER OFF` với seq mới để cứu hộ và đọc lại STATUS, giữ nguyên kết quả thất bại (mã thoát khác 0). Người vận hành kiểm tra VOM đã về 0.00V, gửi lệnh `CLEAR` đưa bo về IDLE và bắt đầu lại lượt thử mới từ đầu.

### Phép thử 4: Lệnh dừng khẩn cấp phần mềm `STOP`
- **Ở đâu:** Terminal máy tính và đồng hồ VOM đo chân PA8 (D7).
- **Làm gì:**
  *(Lưu ý: Dùng lệnh nối chuỗi có khoảng chờ 1 giây để quan sát VOM và gửi lệnh STOP trước ngưỡng mất liên lạc 3.0 giây).*
  - Cho **Git Bash**:
    ```bash
    .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "40 LASER ON"; sleep 1; .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "41 STOP"; .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "42 CLEAR"
    ```
  - Cho **PowerShell**:
    ```powershell
    python pc\nucleo_ping.py --port COM3 --cmd "40 LASER ON"; Start-Sleep -Seconds 1; python pc\nucleo_ping.py --port COM3 --cmd "41 STOP"; python pc\nucleo_ping.py --port COM3 --cmd "42 CLEAR"
    ```
- **Thấy gì là đúng:**
  - Ngay khi nhận lệnh STOP, bo phản hồi `41 DONE PAUSED*...` và VOM lập tức sụt về **0.00 V**.
  - Lệnh CLEAR phản hồi `42 DONE IDLE*...` và đưa bo về sẵn sàng.

### Phép thử 5: Ngắt liên động mở cửa an toàn (D8 / PA9)
- **Ở đâu:** Header bo Nucleo (chân D8) và đồng hồ VOM đo chân PA8 (D7).
- **Làm gì:**
  - **Cách A (Khuyến nghị — Tự động giữ liên lạc với công cụ, tránh hết hạn 3s):**
    - Cho **Git Bash**:
      ```bash
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --test-door
      # Sau khi rút dây xong và kiểm tra sụt áp 0V, cắm lại D8 lên 3V3 rồi xoá lỗi:
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "CLEAR"
      ```
    - Cho **PowerShell**:
      ```powershell
      python pc\nucleo_ping.py --port COM3 --test-door
      # Sau khi rút dây xong và kiểm tra sụt áp 0V, cắm lại D8 lên 3V3 rồi xoá lỗi:
      python pc\nucleo_ping.py --port COM3 --cmd "CLEAR"
      ```
    *(Công cụ tự động bật laser và gửi HEARTBEAT đều đặn mỗi 1.0 giây để giữ liên lạc, người dùng có cửa sổ 12 giây thoải mái rút đầu dây D8 khỏi 3V3 và cắm xuống GND. Ngay khi cắm GND, công cụ phát hiện ngắt `DOOR_OPEN` và kiểm tra `STATUS` đủ 10 token theo Q3 (laser=0, remaining_ms=0). Theo N3/N8: bit `door` trong STATUS mô tả mức logic hiện tại của chân (0 khi đang ở GND, 1 khi đã cắm lại 3V3); bo duy trì `last_err=DOOR_OPEN` cho tới lệnh CLEAR; công cụ nhận diện trip hợp lệ khi trạng thái ERROR, laser=0, remaining_ms=0 và last_err đúng DOOR_OPEN. Theo R06/R07: công cụ kiểm soát toàn vẹn mọi phản hồi giám sát theo đúng cấu trúc Q3 (HEARTBEAT phải là `DONE <state>` hoặc `ERROR <code_hop_le>`, ON gia hạn phải là `DONE ON <remaining_ms>` với 0 <= rem <= 5000); nếu có phản hồi mất/sai checksum/sai seq/thừa thiếu token/rác hoặc STATUS bất thường, công cụ lập tức dừng, gửi lệnh dừng khẩn cấp và trả FAIL. Công cụ yêu cầu người vận hành xác nhận VOM đã về 0.00V (gõ 'y' khi chạy terminal tương tác, hoặc truyền cờ `--confirm-vom-0v` trong script tự động). Chỉ khi xác nhận VOM 0.00V, công cụ mới in `=== KET LUAN: PHEP THU DAT! ===` và thoát mã 0. Sau đó cắm lại D8 lên 3V3 và chạy lệnh CLEAR).*
  - **Cách B (Thủ công với lệnh rời rạc `--cmd`):**
    *(CẢNH BÁO QUAN TRỌNG VỀ THỜI GIAN: Bo Nucleo có timeout an toàn tự ngắt laser nếu mất liên lạc quá 3.0 giây (`LINK_LOST`). Do đó, thao tác rút dây D8 cắm xuống GND PHẢI HOÀN THÀNH TRONG VÒNG DƯỚI 2.5 GIÂY kể từ lệnh `50 LASER ON`. Nếu thao tác sau 3.0 giây, bo sẽ ngắt trước do `LINK_LOST`, không phân biệt được với ngắt liên động cửa).*
    - Cho **Git Bash**:
      ```bash
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "50 LASER ON"
      # Thao tác trong vòng dưới 2.5 giây: rút đầu dây D8 khỏi 3V3 và cắm xuống GND:
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "51 STATUS"
      # Cắm lại D8 lên 3V3 rồi xoá lỗi:
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "52 CLEAR"
      ```
    - Cho **PowerShell**:
      ```powershell
      python pc\nucleo_ping.py --port COM3 --cmd "50 LASER ON"
      # Thao tác trong vòng dưới 2.5 giây: rút đầu dây D8 khỏi 3V3 và cắm xuống GND:
      python pc\nucleo_ping.py --port COM3 --cmd "51 STATUS"
      # Cắm lại D8 lên 3V3 rồi xoá lỗi:
      python pc\nucleo_ping.py --port COM3 --cmd "52 CLEAR"
      ```
- **Thấy gì là đúng:**
  - Ngay khi rút D8 cắm xuống GND, VOM lập tức sụt về **0.00 V**.
  - STATUS phản hồi: `51 DONE ERROR 0 0 0 0 0 <uptime> DOOR_OPEN 0*...` (đủ 10 token theo Q3, laser=0, `remaining_ms=0`).
  - Sau khi cắm lại D8 vào 3V3, lệnh CLEAR phản hồi `52 DONE IDLE*...`.
- **Nếu sai:** Rút D8 mà VOM không tụt về 0V ngay lập tức -> liên động cửa không hoạt động. Nếu công cụ báo lỗi hoặc gặp phản hồi sai/mất (R06), công cụ dừng ngay và kích hoạt dừng cứu hộ; cắm lại D8 lên 3V3, gửi `CLEAR` và bắt đầu lại lượt thử mới từ đầu.

### Phép thử 6: Ngắt dừng khẩn cấp phần cứng ESTOP (D9 / PC7)
- **Ở đâu:** Header bo Nucleo (chân D9) và đồng hồ VOM đo chân PA8 (D7).
- **Làm gì:**
  - **Cách A (Khuyến nghị — Tự động giữ liên lạc với công cụ, tránh hết hạn 3s):**
    - Cho **Git Bash**:
      ```bash
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --test-estop
      # Sau khi rút dây xong và kiểm tra sụt áp 0V, cắm lại D9 xuống GND rồi xoá lỗi:
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "CLEAR"
      ```
    - Cho **PowerShell**:
      ```powershell
      python pc\nucleo_ping.py --port COM3 --test-estop
      # Sau khi rút dây xong và kiểm tra sụt áp 0V, cắm lại D9 xuống GND rồi xoá lỗi:
      python pc\nucleo_ping.py --port COM3 --cmd "CLEAR"
      ```
    *(Công cụ tự động bật laser và gửi HEARTBEAT đều đặn mỗi 1.0 giây để giữ liên lạc, người dùng có cửa sổ 12 giây thoải mái rút đầu dây D9 khỏi GND để hở mạch. Ngay khi rút khỏi GND, công cụ phát hiện ngắt `ESTOP` và kiểm tra `STATUS` đủ 10 token theo Q3 (laser=0, remaining_ms=0). Theo N3/N8: bit `estop` trong STATUS mô tả mức logic hiện tại của chân (1 khi hở mạch, 0 khi đã cắm lại GND); bo duy trì `last_err=ESTOP` cho tới lệnh CLEAR; công cụ nhận diện trip hợp lệ khi trạng thái ERROR, laser=0, remaining_ms=0 và last_err đúng ESTOP. Theo R06/R07: công cụ kiểm soát toàn vẹn mọi phản hồi giám sát theo đúng cấu trúc Q3 (HEARTBEAT phải là `DONE <state>` hoặc `ERROR <code_hop_le>`, ON gia hạn phải là `DONE ON <remaining_ms>` với 0 <= rem <= 5000); nếu có phản hồi mất/sai checksum/sai seq/thừa thiếu token/rác hoặc STATUS bất thường, công cụ lập tức dừng, gửi lệnh dừng khẩn cấp và trả FAIL. Công cụ yêu cầu người vận hành xác nhận VOM đã về 0.00V (gõ 'y' khi chạy terminal tương tác, hoặc truyền cờ `--confirm-vom-0v` trong script tự động). Chỉ khi xác nhận VOM 0.00V, công cụ mới in `=== KET LUAN: PHEP THU DAT! ===` và thoát mã 0. Sau đó cắm lại D9 xuống GND và chạy lệnh CLEAR).*
  - **Cách B (Thủ công với lệnh rời rạc `--cmd`):**
    *(CẢNH BÁO QUAN TRỌNG VỀ THỜI GIAN: Tương tự PT5, thao tác rút dây D9 khỏi GND PHẢI HOÀN THÀNH TRONG VÒNG DƯỚI 2.5 GIÂY kể từ lệnh `60 LASER ON` để tránh dính timeout mất liên lạc 3.0 giây `LINK_LOST`).*
    - Cho **Git Bash**:
      ```bash
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "60 LASER ON"
      # Thao tác trong vòng dưới 2.5 giây: rút dây D9 khỏi GND (để hở mạch):
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "61 STATUS"
      # Cắm lại D9 xuống GND rồi xoá lỗi:
      .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --cmd "62 CLEAR"
      ```
    - Cho **PowerShell**:
      ```powershell
      python pc\nucleo_ping.py --port COM3 --cmd "60 LASER ON"
      # Thao tác trong vòng dưới 2.5 giây: rút dây D9 khỏi GND (để hở mạch):
      python pc\nucleo_ping.py --port COM3 --cmd "61 STATUS"
      # Cắm lại D9 xuống GND rồi xoá lỗi:
      python pc\nucleo_ping.py --port COM3 --cmd "62 CLEAR"
      ```
- **Thấy gì là đúng:**
  - Ngay khi rút D9 khỏi GND, VOM lập tức sụt về **0.00 V**.
  - STATUS phản hồi: `61 DONE ERROR 0 0 1 1 0 <uptime> ESTOP 0*...` (đủ 10 token theo Q3, laser=0, `remaining_ms=0`).
  - Sau khi cắm lại D9 xuống GND, lệnh CLEAR phản hồi `62 DONE IDLE*...`.
- **Nếu sai:** Rút D9 mà VOM không tụt về 0V ngay lập tức -> ngắt ESTOP không hoạt động. Nếu công cụ báo lỗi hoặc gặp phản hồi sai/mất (R06), công cụ dừng ngay và kích hoạt dừng cứu hộ; cắm lại D9 xuống GND, gửi `CLEAR` và bắt đầu lại lượt thử mới từ đầu.

### Phép thử 7: Giữ mức 0V trong suốt quá trình Reset phần cứng
- **Ở đâu:** Nút nhấn RESET màu đen (B2) trên bo Nucleo và đồng hồ VOM đo chân PA8 (D7).
- **Làm gì:**
  1. Dùng ngón tay **nhấn và giữ chặt nút RESET đen** trên bo Nucleo trong khoảng 5 giây.
  2. Quan sát chỉ số hiển thị trên đồng hồ VOM trong suốt thời gian giữ nút.
  3. Thả tay khỏi nút RESET, tiếp tục quan sát chỉ số VOM khi bo khởi động lại.
- **Thấy gì là đúng:**
  - Nhờ có điện trở kéo xuống ngoài mạch R_down (10 kΩ) nối PA8 xuống GND, trong toàn bộ thời gian giữ nút RESET, đồng hồ VOM hiển thị chính xác **0.00 V**.
  - Khi thả nút RESET, LED LD2 bắt đầu nhấp nháy chu kỳ 1s, đồng hồ VOM vẫn duy trì **0.00 V** ổn định.
- **Nếu sai:** Xuất hiện điện áp > 0.5V lúc nhấn giữ hoặc lúc vừa thả reset -> dừng lại kiểm tra tiếp xúc của điện trở kéo xuống 10 kΩ.

---

## 6. Lưu trữ hồ sơ kết quả kiểm tra T5 (Log và ảnh bố trí)

Theo yêu cầu của kế hoạch T5:
1. **Lưu log output:** Sao chép toàn bộ log output từ terminal của các phép thử lưu thành tệp văn bản tại `docs/logs/c4-t5-<yyyy-mm-dd>/t5-output.log` (hoặc `t5-output.md`). Mọi lượt thử thất bại (FAIL do thao tác tay chậm hoặc lỗi I/O) đều phải được lưu giữ nguyên trạng trong log để theo dõi lịch sử, không xoá hoặc ghi đè log lỗi.
2. **Tiêu chuẩn nghiệm thu:** Phép thử bo thật T5 chỉ được kết luận ĐẠT khi mỗi phép thử (từ PT1 đến PT7) đạt liên tiếp ít nhất 3 lần với mã thoát 0, trạng thái bo hợp lệ và người vận hành đã trực tiếp xác nhận điện áp VOM 0.00V trên phần cứng.
3. **Lưu ảnh chụp bố trí:** Chụp ảnh góc rộng và ảnh cận cảnh bố trí phần cứng thực tế (bo Nucleo, vị trí cắm jumper D7/PA8, D8/PA9, D9/PC7, điện trở kéo xuống R_down 10 kΩ, que đo đồng hồ VOM) và lưu vào `docs/logs/c4-t5-<yyyy-mm-dd>/` để đối chiếu hồ sơ bằng chứng.
