# Test `ping_proto.c` trên PC với HAL giả

Chạy mã giao thức **thật** (`Core/Src/ping_proto.c`) trên máy tính với một
HAL giả (`test/fake/`) để kiểm các nhánh khó tạo trên bo: tràn số cuối chuỗi
`PING` (review 20/09 R07), mất byte UART không được ghép thành lệnh hợp lệ
(R08), arm lại RX khi `HAL_UART_Receive_IT` thất bại, LED qua biên tick.

Đây **không phải** thử trên phần cứng: không có ngắt thật, không có thời
gian thật, không có driver VCP của ST-LINK. Kết quả PASS ở đây chỉ nói mã
xử lý đúng với chuỗi byte đưa vào; phải nạp và chạy `pc/nucleo_ping.py`
trên bo mới là bằng chứng phần cứng.

## Chạy (Git Bash, từ thư mục `firmware/stm32/NucleoPing`)

Cần MinGW gcc trên máy (`ENVIRONMENT.md`: `D:\MinGW\bin\gcc`, 9.2.0).

```
cd /d/scanner3d/firmware/stm32/NucleoPing
/d/MinGW/bin/gcc -std=c99 -Wall -Wextra -O0 -Itest/fake -ICore/Inc -DFW_GIT_HASH='"hosttest"' test/test_ping_proto.c Core/Src/ping_proto.c -o build/test_ping_proto.exe
./build/test_ping_proto.exe
```

Thấy gì là đúng: dòng cuối `== N PASS, 0 FAIL ==` và không có dòng `FAIL`.
Nếu sai: chép toàn bộ output; dòng `FAIL ... (nhan: ...)` cho biết phản hồi
thực tế của mã.

`-Itest/fake` đứng trước `-ICore/Inc` để `stm32f4xx_hal.h` và `main.h` giả
che bản thật. `build/` bị Git bỏ qua.

## Các trường hợp

- Nhánh thường: `PING n`, `ID?`, CRLF, `PING` thiếu số, đuôi rác, lệnh lạ,
  dòng rỗng, `PING 0`, dòng quá 64 byte rồi phục hồi.
- R07: `PING 4294967295` → PONG; `4294967296`, `4294967299`, `4294967300`,
  11 chữ số → `ERR badarg` (trước sửa: cuộn về `PONG 0`…`PONG 3`).
- R08: lỗi UART giữa dòng (`PING 1` + lỗi + `2`) → `ERR overrun`, không
  `PONG 12`; lỗi khi ring rỗng; ring đầy (249 LF + `PING 1`, byte `9` mất);
  lệnh hoàn chỉnh trước chỗ đứt vẫn được trả lời, lệnh ngay sau chỗ đứt bị
  bỏ; hai chỗ đứt chưa xử lý → bỏ cả ring (bảo thủ).
- Arm lại RX: `HAL_UART_Receive_IT` trả `HAL_BUSY` trong ISR → `ping_poll()`
  thấy `RxState == READY` và arm lại, đếm `ping_rx_rearm_count()`.

Kết quả lần chạy 2026-09-20: `docs/logs/nucleo-ping-hosttest-2026-09-20.log`.
