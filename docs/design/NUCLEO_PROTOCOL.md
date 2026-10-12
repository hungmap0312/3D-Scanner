# Giao thức PC ↔ Nucleo và máy trạng thái — bước Q3

Ngày lập: 2026-09-20; cập nhật hợp đồng G (p02): 2026-10-09.
Trạng thái:
- **C4 đã gộp (`8e5f1f7`):** Đã hiện thực giao thức P1 (tối đa 64 byte, PA8 laser, lệnh `LASER`, `STATUS`, `HEARTBEAT`, `STOP`, `CLEAR`, IWDG; `HOME` và `MOVE_ABS` trả `ERROR NOTIMPL`).
- **An toàn SPEC §9 đã bỏ (D050, 2026-10-09):** Người dùng quyết định xoá toàn bộ yêu cầu an toàn/liên động SPEC §9. Các kiểm tra cửa (`door`), nút dừng (`estop`) và bảo vệ thời gian trong firmware C4 được duy trì như **hành vi tương thích hiện có (legacy/compatibility)**, không còn là điều kiện cổng nghiệm thu của dự án.
- **Hợp đồng đích P2 (chuyển động motor bàn xoay — người dùng xác nhận 2026-10-09):** Thiết kế đích cho p04 (B1) và p08 (D1), mở rộng khung tối đa lên **96 byte**, bổ sung cache motor riêng và quy tắc chống lặp độc lập với telemetry. PC chỉ mở đường motor sau khi xác nhận firmware hỗ trợ P2.

Sửa tệp này khi đổi giao thức; firmware và `pc/` phải trỏ tới phiên bản giao thức ghi ở mục 1.

## 1. Khung bản tin

- Kênh: USART2 qua COM ảo ST-LINK, 115200 8N1, như D014.
- Một dòng ASCII một bản tin, kết thúc `LF`; `CR` bị bỏ qua.
- **Phiên bản giao thức và độ dài khung:**
  - **P1 (C4 hiện có):** Dài tối đa **64 byte** kể cả `LF` (`PING_LINE_MAX` hiện có); dài hơn → bỏ cả dòng, trả `0 ERROR TOOLONG`. Banner khởi động: `BOOT NucleoScan <fw_ver> <git> P1`.
  - **P2 (Hợp đồng đích có motor, người dùng duyệt 2026-10-09):** Dài tối đa **96 byte** kể cả `LF` (`P2_LINE_MAX = 96`); dài hơn → bỏ cả dòng, trả `0 ERROR TOOLONG`. Banner khởi động: `BOOT NucleoScan <fw_ver> <git> P2`. Lý do nâng lên 96 byte: phản hồi `STATUS` đầy đủ khi có bước motor lớn (ví dụ step 9552, seq 65535, uptime lớn) dài tới 67 byte (ví dụ: `65535 DONE CAPTURING 9552 1 1 0 1 4294967295 LASER_TIMEOUT 5000*3E\n`), vượt quá giới hạn 64 byte của P1. P2 bảo đảm không cắt cụt dữ liệu.
- Dạng lệnh: `<seq> <CMD> [arg ...]*<hh>`
  - `<seq>`: số thứ tự thập phân 1–65535 do PC tăng dần đơn điệu; **0 không dùng** cho lệnh (bo dùng `0` khi trả lỗi cho bản tin không đọc được seq). PC không quay vòng seq trong cùng một phiên quét.
  - `<CMD>`: chữ hoa, tối đa 10 ký tự.
  - `*<hh>`: **tổng kiểm XOR** của mọi byte trước dấu `*` (kiểu NMEA), hai chữ số hex viết hoa. **Bắt buộc** với mọi lệnh có `<seq>` (D021).
- Dạng phản hồi: `<seq> ACCEPTED`, `<seq> DONE [data]`, `<seq> ERROR <code> [text]`. Phản hồi cũng mang `*<hh>` để PC kiểm.
- **Lệnh nhận diện và tương thích ngược:**
  - `PING <n>` (kế thừa tuần 1, không seq, không checksum): `PONG <n> <uptime_ms>`.
  - `ID?`:
    + **Trong P1 (C4 hiện có):** Phản hồi `ID NUCLEO-F446RE NucleoScan <fw_ver> <git>` (hoặc `<seq> ID ...*<cs>`), không chứa token giao thức.
    + **Trong P2 (Hợp đồng đích có motor):** Phản hồi bổ sung token nhận diện giao thức `PROTOCOL_P2`:
      - Khi PC gửi lệnh kế thừa không seq (`ID?`): `ID NUCLEO-F446RE NucleoScan <fw_ver> <git> PROTOCOL_P2`
      - Khi PC gửi lệnh có seq (`<seq> ID?*<hh>`): `<seq> ID NUCLEO-F446RE NucleoScan <fw_ver> <git> PROTOCOL_P2*<hh>`
    + **Quy tắc nhận diện P2 của PC (`DeviceClient`):**
      1. Nếu PC nhận được banner khởi động lúc mở cổng COM: kiểm tra token cuối là `P2` (`BOOT NucleoScan ... P2`).
      2. Nếu PC kết nối sau khi bo đã khởi động (không đọc được banner `BOOT`): PC gửi `ID?` (hoặc `1 ID?*23`). Bo kiểm tra seq và checksum hợp lệ trước khi phân tích token `PROTOCOL_P2`. PC tách các trường (tokens): nếu token thứ 6 (hoặc thứ 7 nếu có seq) bằng đúng chuỗi `PROTOCOL_P2`, PC xác nhận bo hỗ trợ P2 và kích hoạt điều khiển motor; nếu token này vắng mặt, PC xác định firmware là P1 và chặn các lệnh chuyển động motor (`FIRMWARE_P1_MOTOR_UNSUPPORTED`).
- Kiểm tra độ dài (`SPEC` 6.1): ngoài giới hạn độ dài dòng, mỗi lệnh có **số đối số cố định** (bảng mục 2); thừa hoặc thiếu → `ERROR BADARG`.

### 1.1 Số thứ tự và chống lặp

- **Trong C4 (P1):** Bo lưu `s_last_p1_seq` và phản hồi cuối `s_last_p1_resp` chung cho mọi lệnh.
- **Trong P2 (Hợp đồng đích motor):**
  - Bo duy trì **cache lệnh motor riêng biệt** (`motor_cache`):
    Lưu `seq`, `cmd` (tên lệnh + đối số), `initial_reply` (`ACCEPTED`), và `terminal_reply` (`DONE <steps>` hoặc `ERROR <reason>`, ban đầu là `None`).
  - Các lệnh telemetry và truy vấn trạng thái (`STATUS`, `HEARTBEAT`, `PING`, `ID?`) tuyệt đối **không ghi đè `motor_cache`**.
  - **Quy tắc xử lý lệnh motor (`HOME`, `MOVE_ABS`):**
    + `seq == last_motor_seq` và **cùng payload**:
      - Nếu lệnh vẫn đang chạy (`terminal_reply == None`): gửi lại phản hồi đã lưu `initial_reply` (`<seq> ACCEPTED`). Motor tiếp tục di chuyển bình thường, không ngắt quãng.
      - Nếu lệnh đã kết thúc: gửi lại `terminal_reply` (`<seq> DONE <step_count>` hoặc `<seq> ERROR <reason>`).
      - Tuyệt đối **không thực thi lại**, không phát thêm xung nào (bảo toàn tính lũy đẳng).
    + `seq == last_motor_seq` nhưng **khác payload** → từ chối, trả `<seq> ERROR SEQ_PAYLOAD_MISMATCH`.
    + `seq < last_motor_seq` → từ chối, trả `<seq> ERROR SEQ_OLD` (PC cấp seq tăng dần đơn điệu).
    + `seq > last_motor_seq`:
      - Nếu bo đang bận (`MOVING` hoặc `SETTLING`) → từ chối, trả `<seq> ERROR MOTOR_BUSY`. **Đặc biệt:** Bo **KHÔNG** cập nhật `last_motor_seq` và **KHÔNG** ghi đè `motor_cache`. Lệnh đang chạy tiếp tục giữ `last_motor_seq` và cache cho tới khi hoàn tất.
      - Nếu bo rảnh (`IDLE` với `homed = 1` cho `MOVE_ABS`, hoặc `IDLE`/`COMPLETED` cho `HOME`) → tiếp nhận thực thi lệnh mới, cập nhật `last_motor_seq = seq`, ghi mới `motor_cache` (`initial_reply = ACCEPTED`, `terminal_reply = None`).
  - **Hành vi ngắt lệnh bởi `STOP` và cached terminal response:**
    Ví dụ kịch bản:
    1. PC gửi `100 MOVE_ABS 500` → Bo tiếp nhận, trả `100 ACCEPTED`. Motor bắt đầu quay. `motor_cache` lưu `seq=100`, `cmd=MOVE_ABS 500`, `terminal=None`.
    2. Người dùng bấm dừng khẩn hoặc huỷ: PC gửi `101 STOP` → Bo ngắt xung timer ngay lập tức, hạ laser, chuyển trạng thái sang `PAUSED`, đặt `homed = 0` (vị trí mất tính toàn vẹn).
    3. Vì lệnh 100 đang ở trạng thái pending (chưa hoàn tất), Bo cập nhật kết quả kết thúc của lệnh 100 trong cache: `motor_cache.terminal = "100 ERROR MOTOR_STOPPED"`. Bo phản hồi lệnh STOP: `101 DONE PAUSED`.
    4. Nếu sau đó PC (hoặc retry trễ từ đường truyền) gửi lại `100 MOVE_ABS 500`: Bo đối chiếu `motor_cache` thấy `seq == 100`, payload khớp, và `terminal_reply` đã có giá trị `"100 ERROR MOTOR_STOPPED"` → Bo trả ngay `100 ERROR MOTOR_STOPPED`. Mâm **hoàn toàn đứng yên**, không phát thêm bất kỳ xung nào, không trả lại `ACCEPTED`.
    5. *Ngược lại, nếu lệnh motor trước đó đã hoàn tất dứt điểm* (`motor_cache.terminal` đã lưu `"100 DONE 500"` và bo ở `IDLE`): Khi nhận lệnh `101 STOP`, bo chuyển sang `PAUSED` nhưng **giữ nguyên kết quả terminal đã có** (`100 DONE 500`), tuyệt đối không ghi đè thành `MOTOR_STOPPED`. Nhờ đó, nếu lệnh motor đã hoàn tất bị retry muộn, bo vẫn trả lại `DONE 500`.
  - **Quy tắc chống lặp cho các lệnh không phải motor (`LASER`, `STOP`, `CLEAR`):**
    Các lệnh này có tính chất lũy đẳng tự nhiên (idempotent). Việc gửi lại cùng seq hay seq mới đều thực thi gán trạng thái an toàn:
    + `LASER ON`: bật chân PA8 mức cao, làm mới hẹn giờ `T_laser_max`; trả `<seq> DONE ON <remaining_ms>`.
    + `LASER OFF`: hạ chân PA8 mức thấp; trả `<seq> DONE OFF 0`.
    + `STOP`: dừng xung timer, hạ laser, đặt `homed = 0`; trả `<seq> DONE <state>`. Nếu có lệnh motor đang pending (`MOVING`/`SETTLING`/`HOMING`), chuyển `motor_cache.terminal = "<last_motor_seq> ERROR MOTOR_STOPPED"`; nếu lệnh motor trước đó đã kết thúc terminal (`DONE`/`ERROR`), giữ nguyên cache kết quả cũ.
    + `CLEAR`: xoá lỗi về IDLE (nếu đang ở ERROR/PAUSED); trả `<seq> DONE IDLE`.
    Bản thân các lệnh này không làm thay đổi danh tính lệnh motor (`last_motor_seq` và `motor_cache.cmd` không bị chiếm bởi seq của chúng) và không bị từ chối bởi các kiểm tra `SEQ_OLD` hay `SEQ_PAYLOAD_MISMATCH` của motor cache.
  - **Phân biệt lỗi trước thực thi (`OVERRUN`, `BADCHK`, `BADFRAME`) và bất biến retry motor:**
    + Khi bo phát hiện lỗi tầng nhận byte (ring buffer UART tràn gây `OVERRUN`, sai tổng kiểm `BADCHK`, sai khung `BADFRAME`), bản tin bị huỷ bỏ trước khi được tiếp nhận vào logic điều khiển: bản tin hiện tại **chưa từng được đưa vào thực thi** và `last_motor_seq`/`motor_cache` **hoàn toàn giữ nguyên không đổi**.
    + **Bất biến retry motor (Bảo toàn danh tính lệnh):** Lỗi tầng nhận byte chỉ chứng minh bản tin mang lỗi hiện tại bị loại bỏ trước thực thi; nó **tuyệt đối không xoá bỏ sự không chắc chắn** của bất kỳ lần gửi nào trước đó với cùng seq (ví dụ: lần gửi đầu đã thực thi xong `DONE` trên bo nhưng phản hồi bị thất lạc do nhiễu, lần gửi retry bị `BADCHK`). Do đó:
      - Khi thực hiện một thao tác motor (`HOME`, `MOVE_ABS`), PC **BẮT BUỘC giữ nguyên `seq` và payload** cho mọi lần retry cho đến khi nhận được phản hồi kết thúc xác định (`DONE` hoặc `ERROR`) từ bo hoặc huỷ phiên bằng `STOP`.
      - PC **tuyệt đối không được tự ý cấp `seq` mới** cho cùng một thao tác chuyển động motor chỉ vì nhận lỗi tầng nhận byte (bởi vì nếu lệnh trước đó thực chất đã chạy xong, việc gửi `seq` mới `seq > last_motor_seq` khi bo đã `IDLE` sẽ khiến bo thực thi chuyển động thêm một lần nữa, gây tích luỹ bước thừa hoặc HOME lặp).
      - `seq` mới cho motor chỉ được phép cấp khi bắt đầu một góc chuyển động mới, hoặc khi thao tác trước đó đã nhận phản hồi kết thúc dứt điểm.
  - Sau reset bo, `last_motor_seq = 0`.

## 2. Bảng lệnh

Trạng thái cho phép theo mục 4. `T_*` là hằng ở mục 5.

| Lệnh | Đối số | Cho phép ở | Phản hồi | Ghi chú |
| --- | --- | --- | --- | --- |
| `HOME` | 0 | `IDLE`, `COMPLETED` | `ACCEPTED` ngay; `DONE 0` sau khi tìm thấy công tắc, lùi ra, tiếp cận lại lần 2 cùng chiều và **hết `T_settle`** (HOMING → SETTLING → IDLE); `ERROR HOME_TIMEOUT` hoặc `HOME_STEPS` | Đặt `step_count = 0`, `homed = 1`. Laser phải đang tắt, nếu không `ERROR LASER_ON`. Tìm công tắc chậm, lùi ra rồi tiếp cận lại lần 2 cùng chiều. Hoàn tất sau settle |
| `MOVE_ABS <steps>` | 1: vị trí tuyệt đối 0…`STEPS_PER_REV−1` | `IDLE` với `homed = 1` | `ACCEPTED` ngay; `DONE <step_count>` **sau khi hết `T_settle`** (MOVING → SETTLING → IDLE) | Chỉ tiến **cùng chiều** trong lượt: nếu `đích > hiện tại` → phát đủ xung tới đích; nếu `đích < hiện tại` → đi vòng thêm một vòng (`STEPS_PER_REV - hiện tại + đích` xung), không đảo chiều (`SPEC` 7); nếu `đích == hiện tại` → **không phát xung, không đi thêm vòng**, chuyển sang `SETTLING` rồi trả `DONE <step_count>`. Laser đang bật → `ERROR LASER_ON`. `homed = 0` → `ERROR NOT_HOMED`. Ngoài dải → `ERROR RANGE` |
| `LASER ON` | 1 | `IDLE` | `DONE ON <remaining_ms>` | Vào `CAPTURING`; hẹn giờ tự tắt sau `T_laser_max = 5000 ms`; mỗi `LASER ON` lặp (seq mới hoặc cùng seq) đặt lại hẹn giờ. Đang `MOVING`/`SETTLING`/`HOMING` → `ERROR BUSY`. C4 kiểm tra cửa/estop như hành vi tương thích cũ |
| `LASER OFF` | 1 | mọi trạng thái | `DONE OFF 0` | Luôn thực thi, kể cả trong `ERROR`; `CAPTURING` → `IDLE` |
| `STATUS` | 0 | mọi | `DONE <state> <step_count> <laser> <door> <estop> <homed> <uptime_ms> <last_err> <remaining_ms>` | `laser`, `door`, `estop`, `homed` là 0/1; `door` 1 = đóng; `last_err` mã lỗi gần nhất hoặc `NONE`; `remaining_ms` thời gian laser còn bật tối đa (ms), 0 khi laser tắt hoặc hết hạn. Trong P2, giới hạn khung mở rộng 96 byte, không bị cắt cụt (T8) |
| `STOP` | 0 | mọi | `DONE <state>` | Tắt laser ngay, ngừng phát xung timer ngay. Từ `MOVING`/`SETTLING`/`HOMING` → `PAUSED` và đặt `homed = 0` (vị trí không còn bảo đảm, `SPEC` 7/8); từ `CAPTURING` → `PAUSED`; từ `IDLE` → `PAUSED`; từ `ERROR` giữ `ERROR`. Nếu có lệnh motor đang pending (`MOVING`/`SETTLING`/`HOMING`), ghi `motor_cache.terminal = "<last_motor_seq> ERROR MOTOR_STOPPED"`; nếu lệnh motor đã hoàn tất trước đó (đã terminal `DONE`/`ERROR`), giữ nguyên kết quả cache cũ |
| `HEARTBEAT` | 0 | mọi | `DONE <state>` | PC gửi mỗi 1000 ms khi duy trì phiên (tối đa `T_hb/2`). Bo không nhận **bất kỳ** bản tin nào trong `T_hb = 3000 ms` → tắt laser; nếu đang `CAPTURING`/`MOVING`/`SETTLING`/`HOMING` → `ERROR LINK_LOST`. `HEARTBEAT` chỉ đặt lại timer mất liên lạc, **không** gia hạn hẹn giờ laser `T_laser_max`, **không** ghi đè `motor_cache` |
| `CLEAR` | 0 | `ERROR`, `PAUSED` | `DONE IDLE` | Xoá lỗi có chủ ý (`SPEC` 8). Không tự khôi phục vị trí: nếu lỗi/dừng xảy ra khi đang di chuyển/homing thì `homed = 0`, bắt buộc HOME lại |
| `PING <n>` | kế thừa | mọi | `PONG <n> <uptime_ms>` | Không seq; cũng tính là "có nhận bản tin" cho `T_hb` |
| `ID?` | kế thừa / P2 | mọi | `ID ...` (P1) hoặc `... PROTOCOL_P2` (P2) | Nhận diện firmware và phiên bản giao thức P1/P2 |

Lệnh không có trong bảng → `<seq> ERROR UNKNOWN`. Lệnh có trong bảng nhưng firmware hiện tại chưa làm (giai đoạn C4) → `<seq> ERROR NOTIMPL`.

## 3. Mã lỗi

| Mã | Nghĩa | Vào `ERROR`? |
| --- | --- | --- |
| `TOOLONG`, `BADFRAME`, `BADCHK`, `UNKNOWN`, `BADARG`, `NOTIMPL` | Lỗi bản tin; không đổi trạng thái | không |
| `SEQ_PAYLOAD_MISMATCH` | P2: Lệnh motor có cùng `seq` với lệnh motor trước nhưng khác payload | không |
| `SEQ_OLD` | P2: Lệnh motor có `seq < last_motor_seq` | không |
| `MOTOR_BUSY` | P2: Lệnh motor mới bị từ chối vì cơ cấu đang `MOVING` hoặc `SETTLING`. Không cập nhật `last_motor_seq` | không |
| `MOTOR_STOPPED` | P2: Lệnh motor bị ngắt giữa chừng do lệnh `STOP` | không (trả cho retry seq cũ) |
| `OVERRUN` | Bo mất/hỏng byte RX (ring đầy, lỗi UART) trong bản tin này; bản tin bị bỏ tới `LF`, không ghép hai mảnh (review 20/09 R08; đã có ở firmware 0.1.1 dạng `ERR overrun` cho lệnh kế thừa). Lệnh chưa thực thi, không thay đổi cache; PC gửi lại lệnh | không |
| `BUSY`, `NOT_HOMED`, `RANGE`, `LASER_ON`, `IN_ERROR` | Lệnh bị từ chối vì trạng thái | không |
| `DOOR_OPEN` | Hành vi tương thích C4: Cửa mở lúc yêu cầu bật laser hoặc khi đang chạy (D050: không còn là cổng an toàn dự án) | có (C4), khi đang chạy |
| `ESTOP` | Hành vi tương thích C4: Nút dừng (tiếp điểm NC hở) | có (C4) |
| `HOME_TIMEOUT`, `HOME_STEPS` | HOME quá `T_home_max` hoặc quá `HOME_STEPS_MAX` xung (tham số p04 chốt) | có |
| `LINK_LOST` | Không nhận bản tin trong `T_hb` khi đang chạy | có |
| `LASER_TIMEOUT` | Laser bật quá `T_laser_max` không có lệnh mới; laser đã tự tắt | không vào `ERROR` (về `IDLE`), nhưng ghi `last_err` để PC thấy |
| `WDG_RESET` | Bo vừa khởi động lại do watchdog (đọc cờ reset) | `last_err` sau boot; trạng thái `IDLE`, `homed = 0` |

## 4. Máy trạng thái

Trạng thái theo `SPEC` mục 8: `IDLE`, `HOMING`, `MOVING`, `SETTLING`,
`CAPTURING`, `PAUSED`, `COMPLETED`, `ERROR`. `COMPLETED` là trạng thái PC
báo sau góc cuối (`SPEC` 7 bước 7); bản đầu chưa cần lệnh riêng — coi như
`IDLE`; giữ tên để hồ sơ khớp.

| Từ | Sự kiện | Đến | Hành động |
| --- | --- | --- | --- |
| (reset) | nguồn / watchdog | `IDLE` | chân laser mức thấp **trước mọi khởi tạo khác**; `homed = 0`; `last_motor_seq = 0`; `last_err = WDG_RESET` nếu cờ IWDG |
| `IDLE`, `COMPLETED` | `HOME` hợp lệ | `HOMING` | phát xung chậm về công tắc; đếm xung và thời gian |
| `HOMING` | thấy công tắc → lùi → tiếp cận lại cùng chiều xong | `SETTLING` | giữ mô-men tại step 0; bắt đầu `T_settle`; `step_count = 0`, `homed = 1` |
| `HOMING` | quá thời gian / quá xung | `ERROR` | ngừng xung; `ERROR HOME_*` |
| `IDLE` | `MOVE_ABS` hợp lệ | `MOVING` | phát xung timer có tăng giảm tốc theo cùng một chiều |
| `MOVING` | đủ xung | `SETTLING` | giữ mô-men; bắt đầu `T_settle` |
| `SETTLING` | hết `T_settle` sau HOME | `IDLE` | gửi `DONE 0` (hoàn tất HOME) |
| `SETTLING` | hết `T_settle` sau MOVE | `IDLE` | gửi `DONE <step_count>` (hoàn tất MOVE) |
| `IDLE` | `LASER ON` hợp lệ | `CAPTURING` | chân laser cao; hẹn giờ `T_laser_max = 5000 ms` |
| `CAPTURING` | `LASER OFF` | `IDLE` | chân laser thấp |
| `CAPTURING` | hết `T_laser_max = 5000 ms` | `IDLE` | chân laser thấp; `last_err = LASER_TIMEOUT` |
| bất kỳ trừ `ERROR` | `STOP` | `PAUSED` | laser thấp; ngừng xung ngay; huỷ settle; `homed = 0` nếu đang `MOVING`/`SETTLING`/`HOMING`; nếu có lệnh motor đang pending, ghi `MOTOR_STOPPED` vào `motor_cache` (nếu cache đã terminal thì giữ nguyên) |
| `PAUSED` | `CLEAR` | `IDLE` | chuyển về IDLE; nếu `homed == 0` giữ nguyên `0` (bắt buộc HOME lại) |
| bất kỳ | cửa mở / estop (hành vi tương thích C4) | `ERROR` | laser thấp; ngừng xung; `last_err = DOOR_OPEN`/`ESTOP` |
| `CAPTURING`/`MOVING`/`SETTLING`/`HOMING` | im lặng > `T_hb = 3000 ms` | `ERROR` | laser thấp; ngừng xung; huỷ settle; `last_err = LINK_LOST`, `homed = 0` |
| `ERROR` | `CLEAR` | `IDLE` | `homed` giữ giá trị trước lỗi chỉ khi lỗi xảy ra ở `IDLE`/`CAPTURING`; nếu lỗi xảy ra khi chuyển động/homing thì `homed = 0` |
| `ERROR` | mọi lệnh khác trừ `LASER OFF`, `STATUS`, `STOP`, `HEARTBEAT`, `CLEAR`, `PING`, `ID?` | `ERROR` | `ERROR IN_ERROR` |

**Quy tắc an toàn và hiệu lực D050:**
- D050 đã xoá toàn bộ yêu cầu an toàn/liên động SPEC §9 khỏi danh mục nghiệm thu và điều kiện cổng.
- Bất biến chức năng kỹ thuật vẫn giữ:
  1. Chân laser chỉ ở mức cao khi `state == CAPTURING`. Mọi lối vào trạng thái khác đều hạ chân laser trước.
  2. Watchdog IWDG tự nạp lại trong vòng lặp chính; treo → reset → chân laser thấp theo phần cứng kéo xuống.
  3. Lệnh `STOP` luôn lập tức ngắt xung timer và hạ chân laser.
  4. Lỗi giữa chuyển động làm mất tính toàn vẹn vị trí (`homed = 0`), không tự ý suy đoán vị trí cũ còn đúng.

## 5. Hằng thời gian và giới hạn

| Tên | Giá trị | Cơ sở / cách chốt |
| --- | --- | --- |
| `T_hb` | 3000 ms | D038: PC gửi `HEARTBEAT` mỗi 1000 ms khi duy trì phiên; im lặng > 3000 ms khi đang chạy gây `ERROR LINK_LOST` |
| `T_laser_max` | 5000 ms | D021, D038: thời gian bật laser tối đa của firmware C4; mỗi `LASER ON` hợp lệ với seq mới đặt lại hẹn giờ; `HEARTBEAT` không gia hạn laser |
| `T_settle` | 400 ms (tạm thời) | `SPEC` 7, người dùng xác nhận 2026-10-09: giá trị thiết kế tạm; chốt thực tế sau bài đo 100/200/400/800 ms tại B2 |
| `T_home_max` | 30 000 ms (ứng viên) | Giá trị tham số, do p04 (B1) chốt theo thông số động cơ thật |
| `HOME_STEPS_MAX` | 1,2 × `STEPS_PER_REV` (ứng viên) | Giá trị tham số, do p04 (B1) chốt |
| `STEPS_PER_REV` | 9600 xung/vòng (thiết kế) | 200 bước × 16 vi bước × tỉ số truyền 3:1 (`SPEC` 12, D048); số xung đo thực tế xác nhận tại B2 |
| Watchdog IWDG | 1000 ms | Firmware C4 duy trì |
| Độ dài khung P1 | Tối đa 64 byte kể cả `\n` | Giao thức C4 hiện có (`PING_LINE_MAX = 64`) |
| Độ dài khung P2 | Tối đa 96 byte kể cả `\n` | Giao thức đích có motor (`P2_LINE_MAX = 96`), bảo đảm không cắt cụt bản tin `STATUS` đầy đủ |

## 6. Trình tự một góc quét (văn bản, thay sequence diagram)

```
PC                          Nucleo                         S3
|-- 101 MOVE_ABS 48 ------->|                              |
|<-- 101 ACCEPTED ----------|  MOVING -> SETTLING          |
|<-- 101 DONE 48 -----------|  IDLE (sau T_settle)         |
|-- GET /capture_fresh (laser OFF) -------------------------->|
|<-- JPEG + 5 headers (frame_id=k, boot_id, ts...) ----------|
|   PC kiểm tra ảnh nền hợp lệ                             |
|-- 102 LASER ON ---------->|  CAPTURING, hẹn giờ 5 s      |
|<-- 102 DONE ON 5000 ------|                              |
|   (chờ T_laser_settle nếu có)                            |
|-- GET /capture_fresh (laser ON) --------------------------->|
|<-- JPEG + 5 headers (frame_id=k+1, boot_id, ts...) --------|
|-- 103 LASER OFF --------->|  IDLE                        |
|<-- 103 DONE OFF 0 --------|                              |
|   PC kiểm tra cặp ảnh (off/on) hợp lệ, lưu vào đĩa;       |
|   Chỉ khi cặp ảnh được lưu hợp lệ mới gửi MOVE_ABS tiếp   |
|-- 104 HEARTBEAT --------->|  IDLE                        |
|<-- 104 DONE IDLE ---------|                              |
```

Ảnh lỗi: PC chụp lại tại chỗ tối đa 2 lần (`attempt = 2, 3`), mâm không dịch (`SPEC` 6.4);
lần chụp lại cũng đi qua chu trình `LASER ON`/`OFF` với seq mới. Nếu sau 3 lần vẫn lỗi → dừng phiên, bảo toàn dữ liệu đã có.

## 7. Phân công triển khai cho p04 (B1) và các nhánh

- **C4 (đã gộp `8e5f1f7`):** Hoàn thành giao thức P1 (seq, checksum, độ dài 64 byte, chống lặp cơ bản); lệnh `LASER`, `STATUS`, `HEARTBEAT`, `STOP`, `CLEAR`; chân PA8 điều khiển laser.
- **p04 (B1 — Thiết kế và hiện thực điều khiển bàn xoay Nucleo P2):**
  - Hiện thực giao thức P2 (96 byte, banner `BOOT ... P2`, cache motor riêng, chống lặp lệnh motor).
  - Lệnh `HOME`, `MOVE_ABS <steps>`, quản lý FSM `HOMING`/`MOVING`/`SETTLING`.
  - **Khảo sát và chốt chân phần cứng trên Nucleo-F446RE:**
    + Laser: giữ nguyên PA8 (D7) đã kiểm chứng ở C4.
    + Chân STEP: chọn chân Timer phù hợp trên header Morpho/Arduino để phát xung chính xác.
    + Chân DIR, ENABLE: chọn chân GPIO đầu ra phù hợp.
    + Chân HOME: chọn chân GPIO đầu vào có pull-up/pull-down thích hợp cho công tắc hành trình, tránh xung đột USART2 (PA2/PA3) và ST-LINK.
  - Chốt thông số giới hạn: `T_home_max`, `HOME_STEPS_MAX`, tần số phát xung và độ dốc tăng giảm tốc.
- **B2 (Thực nghiệm bàn xoay):** Đo đếm xung độc lập và đo thực nghiệm thời gian ổn định rung `T_settle` tại các mức 100, 200, 400, 800 ms.

## 8. Quyết định kỹ thuật được áp dụng

1. **D021 (2026-09-20):** Checksum XOR `*<hh>` bắt buộc cho mọi lệnh có seq và mọi phản hồi.
2. **D050 (2026-10-09):** Xoá bỏ toàn bộ yêu cầu an toàn/liên động của SPEC §9. Không coi việc thiếu công tắc cửa, nút dừng hay vỏ kín là lý do chặn cổng dự án.
3. **Người dùng xác nhận 2026-10-09 (p02 G):**
   - Hợp đồng motor đích nâng lên P2 với giới hạn dòng 96 byte, giữ nguyên P1 64 byte cho C4.
   - Cache motor riêng, không bị telemetry (`STATUS`, `HEARTBEAT`) ghi đè.
   - Chốt chân STEP/DIR/ENABLE/HOME và thông số chuyển động giao cho p04 (B1); `T_settle = 400 ms` là tạm thời, đo thực nghiệm ở B2.
   - PC kiểm tra định danh P2 trước khi phát lệnh motor.
