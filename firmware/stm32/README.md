# Firmware Nucleo-F446RE

## NucleoPing — ví dụ tối thiểu, chỉ tiêu B "Giao tiếp Nucleo" tuần 1

Thư mục `NucleoPing/`. LED LD2 nháy 1 Hz; USART2 qua COM ảo của ST-LINK
115200 8N1 trả lời PING. Không cấp tải ra GPIO nào khác. Không có laser,
không có động cơ.

Trạng thái 2026-09-16: ĐÃ BUILD ĐẠT trên PC trong môi trường trợ lý,
log `docs/logs/build-2026-09-16-nucleo-ping.log`. CHƯA NẠP, CHƯA CHẠY
TRÊN BO. Script đối diện `pc/nucleo_ping.py` selftest PASS với bo giả
lập, chưa thử với bo thật.

### Giao thức

Một dòng ASCII một lệnh, kết thúc `LF`; `CR` bị bỏ qua. Chi tiết trong
`NucleoPing/Core/Inc/ping_proto.h`.

| PC gửi | Bo trả | Ghi chú |
| --- | --- | --- |
| `PING <n>` | `PONG <n> <uptime_ms>` | `uptime_ms` từ `HAL_GetTick()`, tính từ reset. Sau khi rút cắm nguồn giá trị này nhỏ lại |
| `ID?` | `ID NUCLEO-F446RE NucleoPing 0.1.1 <git>` | `<git>` là `git describe --always --dirty` lúc build, Makefile truyền vào |
| dòng rỗng | không trả | |
| khác | `ERR unknown` / `ERR badarg` / `ERR toolong` | `PING n` với n > 4294967295 → `ERR badarg` (sửa 20/09, R07; trước đó 4294967296–99 cuộn thành `PONG 0`–`3`) |
| mất/hỏng byte | `ERR overrun` | Thêm 20/09 (R08): ring đầy hoặc `HAL_UART_ErrorCallback` → dòng chứa chỗ đứt bị bỏ tới `LF`, trả `ERR overrun`, không ghép hai mảnh thành lệnh khác; lệnh hoàn chỉnh trước chỗ đứt vẫn được trả lời. `pc/nucleo_ping.py` coi đây là "dòng lạ" → FAIL |
| lúc khởi động | `BOOT NucleoPing 0.1.1 <git>` | in một lần |

FW_VERSION 0.1.1 (20/09) chỉ thay đổi hai điểm trên và thêm arm lại RX từ
`ping_poll()` khi `HAL_UART_Receive_IT` trong ISR thất bại (`RxState ==
READY`). Kiểm trên PC bằng HAL giả: `NucleoPing/test/README.md`, 35/35 PASS
(`docs/logs/nucleo-ping-hosttest-2026-09-20.log`). Build ARM đạt, text 8632
(`docs/logs/build-2026-09-20-nucleo-ping.log`). Đã nghiệm thu cổng U8
(2026-09-30) với 100/100 PING trên bo thật (`docs/logs/ping_20260930_093952/`).

## FW_VERSION 0.2.0 (2026-09-30, C4) — Mở rộng Giao thức P1 & Điều khiển Laser an toàn

Nâng cấp phục vụ đầu việc C4 theo thiết kế `docs/design/NUCLEO_PROTOCOL.md` (D021, D038):
1. **Khung bản tin P1**: `<seq> <CMD> [args...]*<HH>\n` (seq 1..65535, XOR checksum hex 2 chữ số).
2. **Tập lệnh P1**: `LASER ON/OFF`, `STATUS`, `HEARTBEAT`, `STOP`, `CLEAR`; `HOME`/`MOVE_ABS` trả `ERROR NOTIMPL`.
3. **Chống lặp lệnh**: Bộ đệm `last_p1_seq` và `last_p1_resp` gửi lại nguyên văn phản hồi khi trùng seq, không thực thi lại, không gia hạn timer.
4. **Hẹn giờ & An toàn**:
   - `T_hb = 3000 ms`: Không có bản tin trong 3000 ms khi đang `CAPTURING` -> ngắt laser, chuyển `ERROR LINK_LOST`.
   - `T_laser_max = 5000 ms`: Laser tự tắt sau 5000 ms độc lập, chuyển `IDLE`, `last_err = LASER_TIMEOUT`. `HEARTBEAT` gửi mỗi 1000 ms chỉ duy trì liên lạc, không gia hạn laser.
5. **GPIO an toàn & Watchdog**:
   - PA8 (`LASER_Pin`, D7): Ép mức LOW ngay dòng đầu của `main()`, chỉ HIGH khi `CAPTURING`.
   - PA9 (`SENSE_PWR_Pin`, D8): Ngõ vào giám sát nguồn/cửa an toàn; mất nguồn -> ngắt laser, báo `DOOR_OPEN`.
   - PC7 (`SENSE_ESTOP_Pin`, D9, pull-up): Giám sát tiếp điểm NC nút dừng; hở/nhấn -> ngắt laser, báo `ESTOP`.
   - Watchdog IWDG 1000 ms chạy ngầm, refresh trong `ping_poll()`; phát hiện và báo `WDG_RESET`.
6. **Kiểm tra**:
   - Host test: 96/96 PASS (`test/test_ping_proto.c`).
   - ARM build đạt: `build/c4-20260930/NucleoPing.bin` (SHA-256: `0D4CA5FF923500823AC251AD2F85DED6049CB2B1320F45D7E603AB428704B770`).
   - Quy trình thử không tải: `docs/procedures/quy-trinh-c4-nucleo-khong-tai.md`.


### Cách project được sinh ra

STM32CubeMX 6.12.1 bản độc lập, chế độ script không giao diện, ngày
2026-09-16. Script:

```
loadboard NUCLEO-F446RE allmodes
project name NucleoPing
project toolchain Makefile
project path D:/scanner3d/firmware/stm32
SetCopyLibrary "copy only"
SetStructure Advanced
project generate
exit
```

Chạy trong Git Bash:

```
"/c/Users/bestp/AppData/Local/Programs/STM32CubeMX/jre/bin/java.exe" -jar "/c/Users/bestp/AppData/Local/Programs/STM32CubeMX/STM32CubeMX.exe" -q script.txt
```

`loadboard ... allmodes` đặt sẵn LD2 = PA5, nút B1 = PC13, USART2 PA2/PA3
nối VCP của ST-LINK, clock HSI → PLL 84 MHz. `NucleoPing.ioc` là tệp
cấu hình thật, mở được bằng CubeMX.

Ba chỗ phải sửa tay sau khi sinh, vì chế độ script của CubeMX 6.12.1 có
lỗi; nếu sinh lại từ `.ioc` thì phải sửa lại:

1. `Makefile`, biến `C_SOURCES`: CubeMX ghi đường dẫn tuyệt đối, lặp đôi,
   và trỏ tới `sysmem.c`/`syscalls.c` không tồn tại. Đã đổi thành đường
   dẫn tương đối, bỏ trùng, thêm `Core/Src/ping_proto.c`,
   `Core/Src/syscalls.c`, `Core/Src/sysmem.c`. Cũng thêm `-Wextra` và
   biến `FW_GIT` truyền hash commit vào `FW_GIT_HASH`.
2. `STM32F446RETx_FLASH.ld`: bản CubeMX sinh ra thiếu tên vùng nhớ ở
   `_estack = ORIGIN() + LENGTH();` và `> AT> FLASH`, ld báo syntax
   error. Đã thay nguyên tệp bằng
   `STM32Cube_FW_F4_V1.28.3/Projects/STM32446E-Nucleo/Examples/GPIO/GPIO_IOToggle/STM32CubeIDE/STM32F446RETX_FLASH.ld`
   (sha256 đầu `ec6cb2d73abe`), cùng bản đồ bộ nhớ 512K flash / 128K RAM.
3. `Core/Src/syscalls.c` và `sysmem.c`: chép nguyên từ cùng ví dụ trên,
   thư mục `Example/User/`.

`Drivers/` được tỉa từ 57 MB / 1442 tệp xuống 7,2 MB / 127 tệp: giữ 18
tệp HAL `.c` mà Makefile dùng, toàn bộ `HAL_Driver/Inc` (kể cả `Legacy`),
`CMSIS/Include` chỉ 5 header cho Cortex-M4 + GCC, `CMSIS/Device` chỉ
`stm32f4xx.h`, `stm32f446xx.h`, `system_stm32f4xx.h`. Tất cả là bản chép
nguyên từ CubeF4 V1.28.3, không sửa. Build đạt chứng minh phần giữ lại
là đủ.

Mã ứng dụng nằm ở `Core/Src/ping_proto.c`, `Core/Inc/ping_proto.h`,
`Core/Inc/fw_version.h`, và vài dòng trong vùng `USER CODE` của `main.c`,
`stm32f4xx_hal_msp.c` (bật NVIC USART2), `stm32f4xx_it.c`
(`USART2_IRQHandler`). CubeMX giữ nguyên vùng `USER CODE` khi sinh lại.

### Build trong Git Bash, không cần mở CubeIDE

Toolchain lấy từ plugin của STM32CubeIDE 1.17.0 đã cài trên máy:

```
cd /d/scanner3d/firmware/stm32/NucleoPing
GCC="/c/ST/STM32CubeIDE_1.17.0/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.12.3.rel1.win32_1.1.0.202410251130/tools/bin"
MAKE="/c/ST/STM32CubeIDE_1.17.0/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.0.202409170845/tools/bin/make.exe"
"$MAKE" clean GCC_PATH="$GCC"
"$MAKE" -j4 GCC_PATH="$GCC"
```

Kết quả mong đợi: dòng cuối có bảng `text data bss` và hai lệnh
`objcopy` sinh `build/NucleoPing.hex` và `build/NucleoPing.bin`. Ba cảnh
báo `-Wunused-parameter` trong `stm32f4xx_hal_flash_ex.c` là của HAL,
không phải của dự án. `build/` bị Git bỏ qua.

Xem chuỗi phiên bản đã nhúng:

```
"$GCC/arm-none-eabi-strings.exe" build/NucleoPing.elf | grep "BOOT NucleoPing"
```

### Nạp bằng STM32CubeProgrammer CLI

Cắm Nucleo qua cổng USB ST-LINK (CN1, cạnh nút reset). Trong Git Bash ở
thư mục gốc repo:

```
"/d/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe" -l
"/d/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe" -c port=SWD -w firmware/stm32/NucleoPing/build/NucleoPing.bin 0x08000000 -v -rst
```

Lệnh đầu liệt kê ST-LINK và phiên bản firmware của nó. Lệnh sau nạp,
kiểm lại (`-v`) rồi reset bo (`-rst`). Cách thay thế không cần lệnh:
kéo `NucleoPing.bin` thả vào ổ USB tên `NODE_F446RE` mà ST-LINK tạo ra.
Cả hai cách CHƯA THỬ vì trợ lý không có bo. Quy trình từng bước cho
người dùng ở `docs/procedures/quy-trinh-kiem-tra-nucleo.md`.

### Việc còn thiếu để tái tạo hoàn toàn

- Gói CubeF4 dùng để chép HAL: script không ghim, CubeMX tự chọn bản mới
  nhất có trên máy; `NucleoPing.ioc:100` ghi
  `ProjectManager.FirmwarePackage=STM32Cube FW_F4 V1.28.3`.
- Chưa có project CubeIDE (`.project`/`.cproject`); nếu cần gỡ lỗi bằng
  CubeIDE thì import `.ioc` rồi chép phần `USER CODE` sang.
