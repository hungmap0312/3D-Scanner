# Cấu trúc dữ liệu phiên quét — bước Q4

Ngày lập: 2026-09-20; cập nhật hợp đồng G (p02): 2026-10-09.
Trạng thái: **Hợp đồng chuẩn cho PC; các nhánh B1 (p04), C5 (p05), A1 (p06), D1 (p08), E1 (p12) tuân thủ tệp này.**
Cơ sở: `docs/SPEC.md` mục 6.3 (trường bắt buộc), 6.4, 15.2 (dữ liệu một phiên); `data/README.md`; định dạng tuần 1 của `pc/capture_session.py`, C2 (`camera_profile.py`), C3 (`line_extract.py`), C5a (`fresh_capture_probe.py`, `docs/design/S3_FRESH_CAPTURE.md`).

## 1. Nguyên tắc

1. **Ảnh thô bất biến.** Mỗi ảnh ghi một lần, tên duy nhất; lần chụp lại (retry) không ghi đè lần lỗi (`SPEC` 6.4). Giữ nguyên vẹn mọi payload lỗi để chẩn đoán. Thư mục phiên đã tồn tại → từ chối chạy, không dọn/xoá thư mục cũ.
2. **Mọi phiên gắn được với:** commit mã nguồn (PC), phiên bản firmware S3 và Nucleo (chuỗi `BOOT`/`ID?`), hồ sơ camera (`camera_profile_id`), hồ sơ hiệu chuẩn (`calibration_id`), cấu hình ảnh. Thiếu thì ghi chuỗi `"none"` kèm lý do, không bỏ trường.
3. **Nhật ký thu nhận ghi nối thêm** (append-only, một dòng JSON một sự kiện trong `captures.jsonl`) để mất điện/ngắt giữa chừng vẫn giữ được dữ liệu đã thu.
4. **Phân biệt ba khái niệm góc:**
   - `angle_cmd_deg`: góc lệnh suy từ xung lý thuyết theo cấu hình (ví dụ 0,0°..358,2°).
   - `theta_rad`: góc quay có dấu dùng cho tính toán hình học 3D (`theta_rad = rotation_sign × angle_cmd_deg × pi / 180`).
   - Góc đo thực: hiện chưa có cảm biến đo góc tuyệt đối; tuyệt đối **không** gán nhãn góc suy từ xung là góc đo thực (`SPEC` 6.3).
5. **Chỉ chuyển góc sau khi lưu hợp lệ:** Chỉ gửi lệnh `MOVE_ABS` sang góc kế tiếp khi cặp ảnh (OFF và ON) của góc hiện tại đã được thu và lưu hợp lệ vào đĩa (`SPEC` 7).
6. **Tách bạch metadata xử lý và metadata trích vạch C3:**
   - Cấp phiên xử lý (`run_id`): lưu tại `data/processed/<scan_id>/<run_id>/processing.json` (chứa `scan_id`, `calibration_id`, `source_commit`, tham số thuật toán tái tạo và bộ lọc).
   - Cấp trích vạch tâm vạch C3: thư mục con `centers/` lưu `params.json` nguyên sáu trường bất biến theo D037 và `pc/line_extract.py:591` (`roi`, `min_diff`, `max_width`, `sat_thresh`, `img_width`, `img_height`); tuyệt đối không thêm trường lạ (`scan_id`, `calibration_id`, `commit`) vào `params.json` của C3.

## 2. Cây thư mục

```
data/raw/<scan_id>/                 (junction → D:\datascanner3d\raw\)
  session.json                      đầu phiên ghi thông tin cấu hình; cuối phiên cập nhật status, finished_at, counts
  captures.jsonl                    nhật ký thu nhận append-only, một dòng JSON một sự kiện
  camera_status_start.json          /status nguyên văn trước khi quét
  camera_status_end.json            /status nguyên văn sau khi quét
  img_<step:04d>_<off|on>.jpg       ảnh ĐƯỢC CHỌN cho góc/trạng thái đó (400 ảnh cho 200 góc: 0000..0199)
  img_<step:04d>_<off|on>_try<k>.jpg|.bin  payload của lần thử thứ k KHÔNG được chọn (k = 1..3);
                                    .jpg nếu có header FF D8, .bin nếu là body lỗi HTTP/text/nhị phân
data/calibration/
  camera_profiles/<camera_profile_id>.json   hồ sơ camera cố định (C2)
  <calibration_id>/calibration.json          hồ sơ hiệu chuẩn hình học (A1/A2/Trục theo mục 7)
data/processed/<scan_id>/<run_id>/
  processing.json                   metadata cấp run: scan_id + calibration_id + commit + tham số 3D/lọc
  centers/                          thư mục chứa tâm vạch theo chuẩn C3 (D037)
    params.json                     tham số trích vạch C3 (đúng 6 trường bất biến theo pc/line_extract.py: roi, min_diff, max_width, sat_thresh, img_width, img_height)
    centers_<step:04d>.csv          tâm vạch theo hàng (quy ước 5 cột: row_y, center_x_px, valid, reason, width_px)
  points.ply                        đám mây điểm 3D đơn vị mm (hệ camera gốc tại HOME)
  points_raw.xyz                    tập điểm thô trước lọc (trung gian tuỳ chọn)
  report.md                         báo cáo thống kê, số đo và chỉ tiêu hình học
```

- `scan_id`: `scan_YYYYMMDD_HHMMSS` (giờ PC, +07:00).
- `run_id`: `run_YYYYMMDD_HHMMSS`; một `scan_id` có thể chạy nhiều `run_id` khi thử nghiệm các tham số xử lý khác nhau mà không đổi ảnh gốc.
- `centers_<step:04d>.csv` (quy ước C3, 2026-09-28): chứa toạ độ tâm vạch theo hàng trong ROI.
  Quy ước tối thiểu gồm năm cột: `row_y,center_x_px,valid,reason,width_px`.
  - `row_y`: toạ độ hàng toàn ảnh gốc 0 (số nguyên).
  - `center_x_px`: toạ độ thực hữu hạn trong ROI khi `valid` là `true`, để trống khi `valid` là `false`.
    Quy ước toạ độ tâm pixel: pixel chỉ số nguyên `i` nằm tại toạ độ `i.0` (gốc `(0, 0)` tại tâm pixel góc trên-trái ảnh, không cộng `0.5`).
  - `valid`: `true` hoặc `false` (chữ thường).
  - `reason`: `ok|no_signal|weak|saturated|wide|ambiguous|edge`.
  - `width_px`: bề rộng cụm pixel (để trống nếu không có cụm).
- Vòng đời `params.json` trong `centers/` (C3 Vòng 10, D037): bất biến và gắn liền với thư mục chạy; không tự xoá hoặc ghi đè trong bất kỳ đường lỗi nào; các lần chạy cùng cấu hình tái sử dụng, khác cấu hình từ chối với `params_mismatch`.

## 3. `session.json`

Giữ các trường tuần 1 và C2; bổ sung các trường điều phối quét 200 góc (D048). `session_id` = `scan_id`.

**Tập con camera-only của C2:** `capture_session.py --profile` không laser, không góc, không Nucleo — chỉ ghi các trường camera (`schema_version`, `status`, `camera_profile_id`, `camera_config`, `firmware.s3`), các trường motor/laser giữ vắng mặt, không ghi giá trị giả.

| Trường | Kiểu | Nội dung |
| --- | --- | --- |
| `schema_version` | int | `2` cho cấu trúc này |
| `status` | chuỗi | `running` / `paused` / `completed` / `aborted` / `error` |
| `sample` | chuỗi | Mẫu vật (tên, kích thước đo tay) |
| `camera_profile_id` | chuỗi | Tên hồ sơ trong `data/calibration/camera_profiles/` hoặc `"none"` |
| `calibration_id` | chuỗi | Tên thư mục trong `data/calibration/` hoặc `"none"` |
| `camera_config` | object | `framesize`, `quality`, `stream_disabled` (`bool` hoặc `null`), `lens_note` |
| `firmware` | object | `s3`: chuỗi phiên bản từ S3; `nucleo`: nguyên văn dòng `BOOT`/`ID?` |
| `protocol_version` | int | `1` (C4 legacy) hoặc `2` (Hợp đồng đích motor P2) |
| `motion` | object | `steps_per_rev` (9600), `angle_count` (200), `direction` (`cw`/`ccw`), `t_settle_ms` (400), `homed_at` (ISO 8601) |
| `laser` | object | `t_laser_max_ms` (5000), `t_laser_settle_ms`, `wavelength_nm` (650), `module_label` |
| `angle_table` | mảng | Mảng 200 phần tử `[{step_index, step_target, angle_cmd_deg}]`: `step_index` 0..199, `step_target = step_index * 48`, `angle_cmd_deg = step_target * 360 / 9600`. Bắt đầu tại 0 (0,0°), kết thúc tại step 9552 (358,2°). Không có góc 360° |
| `counts` | object | `angles_done` (0..200), `pairs_ok` (0..200), `retries`, `errors` |
| `abort_reason` | chuỗi | Mã lỗi hoặc `""` khi hoàn tất bình thường |

**Quy tắc miền trạng thái `status` và xử lý `paused`:**
- Miền trạng thái `status`:
  + `running`: Phiên quét đang thực hiện.
  + `paused`: Phiên quét tạm dừng bởi người dùng (`request_stop("pause")`). Mâm xoay mất tính toàn vẹn vị trí (`homed = 0`).
  + `completed`: Quét hoàn tất đủ 200 góc / 400 ảnh.
  + `aborted`: Phiên quét bị huỷ bởi người dùng (`request_stop("abort")`).
  + `error`: Phiên quét dừng do lỗi thiết bị, kết nối hoặc ghi đĩa.
- Quy tắc đọc phiên `paused` qua `open_session`:
  + `open_session` kiểm tra tính toàn vẹn phiên `paused`, nạp `angles_done`, `pairs_ok`, `angle_table`.
  + **Quy tắc HOME khi tiếp tục:** Vì thao tác pause ngắt xung motor và đặt `homed = 0`, nếu hệ thống tiếp tục quét (resume) hoặc mở lượt quét mới từ phiên `paused`, BẮT BUỘC thực hiện HOME lại trước khi di chuyển tới góc kế tiếp (`step_index = angles_done`), tuyệt đối không giả định mâm xoay vẫn giữ góc trước khi pause.
  + **Tập con camera-only C2:** `capture_session.py --profile` không dùng motor nên không có trạng thái `paused`; miền trạng thái giữ nguyên tập con tương thích gồm `running` / `completed` / `aborted` / `error`.


## 4. `captures.jsonl` — một dòng mỗi lần chụp hoặc sự kiện

| Trường | Nội dung |
| --- | --- |
| `t_pc` | ISO 8601 +07:00, đồng hồ PC |
| `event` | `capture` / `laser` / `move` / `home` / `error` / `retry` / `abort` |
| `step_index` | Chỉ số góc 0..199 |
| `step_count` | Số xung tích luỹ bo Nucleo báo lại qua `STATUS` hoặc `DONE` |
| `angle_cmd_deg` | Góc lệnh suy từ xung (`step_target * 360 / 9600`) |
| `laser_state_cmd` | `off` / `on` — trạng thái laser PC đã yêu cầu |
| `command_id` | `seq` gửi Nucleo (0 nếu không dùng) |
| `nucleo_reply` | Nguyên văn phản hồi từ Nucleo |
| `frame_id` | Mã ảnh từ header `X-Frame-Id` của S3 `/capture_fresh` (tăng đơn điệu) |
| `boot_id` | `X-Boot-Id` của S3 (128-bit hex string). Nếu `boot_id` thay đổi so với đầu phiên → phát hiện camera reset, dừng phiên ngay |
| `x_timestamp` | `X-Timestamp` (thời điểm DMA buffer đầu tiên của khung, giây.microgiây) |
| `x_request_timestamp` | `X-Request-Timestamp` (thời điểm nhận request tại S3, giây.microgiây) |
| `x_discarded_frames` | `X-Discarded-Frames` (số khung cũ bị loại trước khi lấy khung mới, số nguyên ≥ 0) |
| `file`, `bytes`, `sha256` | Tên tệp trong thư mục phiên (`img_0000_off.jpg`, payload lỗi `_try<k>`), kích thước, băm SHA-256 |
| `http_ms` | Thời gian gọi HTTP `/capture_fresh` |
| `attempt` | `1` (lần đầu), `2`–`3` (chụp lại, tối đa 2 lần chụp lại; tổng tối đa 3 lần thử) |
| `ok`, `error` | `bool`; chuỗi mã lỗi (`decode`, `size`, `timeout`, `http_<code>`, `stale`, `reboot_detected`) |

`sha256`, `frame_id` và `boot_id` được lưu để loại ảnh trùng và phát hiện reset; tính toàn vẹn của cặp ảnh OFF/ON được bảo đảm bằng chuỗi thu nhận không đổi mâm trong lúc retry.

**Quy tắc khi gặp lỗi ghi đĩa `DISK_WRITE_FAILED`:**
- Nếu quá trình ghi ảnh JPEG (`img_<step:04d>_<off|on>.jpg`) hoặc ghi log append vào `captures.jsonl` bị lỗi I/O (hết dung lượng đĩa, mất quyền ghi, ngắt ổ đĩa):
  + Cặp ảnh tại góc hiện tại được tính là **thất bại hoàn toàn**.
  + Hệ thống **TUYỆT ĐỐI KHÔNG** tăng `pairs_ok` và **KHÔNG** tăng `angles_done`.
  + `ScanCoordinator` lập tức dừng phiên quét, chuyển trạng thái trong `session.json` sang `error`, ghi `abort_reason = "DISK_WRITE_FAILED"`.
  + Toàn bộ các ảnh và dòng log đã ghi đĩa thành công ở các góc trước đó được giữ nguyên vẹn trên đĩa để phục vụ chẩn đoán, không bị xoá hay làm hỏng.

## 5. Hồ sơ camera `camera_profiles/<id>.json` — C2 phải tạo đúng

| Trường | Nội dung |
| --- | --- |
| `camera_profile_id` | `cam_<framesize>_q<quality>_<YYYYMMDD>` ví dụ `cam_VGA_q10_20260922`, có thể có hậu tố retry `_rNN` hai chữ số (`_r01`…`_r99`, Vòng 5 muc 3) khi cùng cấu hình/ngày đã có một lần thử — `pc/camera_profile.py --create` tự chọn hậu tố kế tiếp còn trống, không bao giờ ghi đè lần thử trước |
| `created_at`, `source.commit` | Khi tạo |
| `board`, `sensor` | `ESP32-S3 N16R8`, `OV3660 PID 0x3660` |
| `framesize`, `quality` | Như `/control` |
| `controls` | Đúng 14 biến `/control` firmware hiện có nhánh xử lý (`app_httpd.cpp` hàm `cmd_handler`): `aec`, `agc`, `awb`, `aec_value`, `agc_gain`, `awb_gain`, `wb_mode`, `brightness`, `contrast`, `saturation`, `hmirror`, `vflip`, `lenc`, `dcw`. **`aec`, `agc` bắt buộc bằng `0`; `awb` bắt buộc bằng `1` từ Vòng 7** (Vòng 3–6 ghi `awb=0` — cách hiểu đó đã bị L11 bác, xem đính chính cuối ô) — hồ sơ cố định không được để camera tự động phơi sáng, và cân bằng trắng phải là gain thủ công cố định (Vòng 3, xử lý phát hiện Tester; sửa cách khoá ở Vòng 7). **`sharpness` KHÔNG nằm trong danh sách này**: đọc được qua `/status` nhưng firmware hiện tại không có nhánh xử lý cho `/control?var=sharpness`, gửi lên sẽ nhận HTTP 500 "Unknown command" — đây là giới hạn firmware thật, không phải mã C2 làm khác thiết kế (đối chiếu 21/09, xem `pc/camera_profile.py` phần đầu tệp và `handoff/2026-09-21_c2-camera-profile/02_BUILD.md` mục 4). Muốn khoá `sharpness` phải sửa firmware trước, thuộc một kế hoạch khác. **Vòng 5 (L05–L07, xử lý `03_TEST.md` Vòng 4):** `vflip=1`, `brightness=1`, `saturation=-2` là giá trị CHẮC CHẮN của OV3660 (firmware tự đặt cho đúng PID này, `CameraWebServerTest.ino` dòng ~147-150; đối chứng `/status` 17/09) — mặc định khoá đúng ba giá trị này, khoá về `0` như trước Vòng 5 làm ảnh lật ngược (L05). Bốn giá trị `aec_value`, `agc_gain`, `awb_gain`, `wb_mode` CHƯA có số đo xác minh nên KHÔNG có mặc định: `--create` bắt buộc người gọi truyền rõ cả bốn qua `--set`, từ chối trước HTTP nếu thiếu (L06 — mặc định im lặng trước đây từng tạo hồ sơ "hợp lệ" nhưng ảnh tối 12,8 lần và ám lục). Bảy trường này (cộng `aec/agc/awb`) có miền giá trị kiểm trước HTTP theo bằng chứng Espressif/firmware: `aec_value` 0–1200, `agc_gain` 0–30, `awb_gain` 0/1, `wb_mode` 0–4, `vflip` 0/1, `brightness`/`saturation` −2–2 (`CONTROL_DOMAINS` trong mã). **Vòng 6 (L08, đo trực tiếp trên bo 23/09):** `aec_value` đặt qua `/control?var=aec_value` (đường `set_aec_value()`) bị **KẸP CỨNG ở 783** trên VGA và SVGA — gửi 784–1200 bo đều báo lại `783` (`0x3500=12528`); miền 0–1200 ở trên chỉ đúng cho AEC **tự động** (ghi thẳng thanh ghi, không qua hàm kẹp). Vì vậy hồ sơ C2 VGA/SVGA có `aec_value > 783` bị **từ chối trước HTTP** (`AEC_VALUE_HARD_CAP` trong mã); framesize khác chưa đo, chưa áp trần. `agc_gain = round((0x350a + 1) ÷ 16)` đã đối chiếu đúng 9/9 điểm đo, không đổi. **Vòng 6 (L10, giải quyết nghi vấn Vòng 5):** `awb_gain` là **cờ bật/tắt** gain AWB thủ công (`sensor.h`: tham số `enable`), không phải giá trị gain; nếu `wb_mode > 0` mà `awb_gain = 0` thì preset không có tác dụng (cả bốn preset cho cùng kết quả — đúng hiện tượng ám lục quan sát ở lần đo Vòng 5). Hồ sơ C2 cố định vì vậy dùng **`awb_gain = 1`** khi chọn một trong bốn preset `wb_mode ∈ {1,2,3,4}`; cặp `wb_mode > 0` với `awb_gain = 0` bị từ chối trước HTTP (bất biến chéo, không phải lỗi từng trường riêng). **Đính chính Vòng 7 (L11, `03_TEST.md` Vòng 6 — bốn preset ghi đúng bốn bộ gain vào thanh ghi nhưng màu ảnh gần như không đổi, spread 26,2–26,4 % cả bốn):** diễn giải L10 ở trên chỉ đúng một nửa. Theo driver OV3660 của Espressif (`sensors/ov3660.c`: `set_whitebal`, `set_wb_mode`, `set_awb_gain_dsp`; đối chiếu 24/09, xem `01_PLAN.md` Vòng 7 mục 2), `awb` điều khiển bit 0 của `0x5001` — **khối xử lý cân bằng trắng**; `wb_mode` chọn chế độ **thủ công** qua `0x3406=1` và ghi ba gain; `awb_gain` gọi lại bộ chọn mode, không phải một con số gain. Hai điều khiển khác nhau: `awb=0` tắt cả khối nên gain thủ công không bao giờ áp lên ảnh. Hợp đồng từ Vòng 7: **`aec=0`, `agc=0`, `awb=1`, `awb_gain=1`, `wb_mode ∈ {1,2,3,4}`** — `awb=1` ở đây là bật khối xử lý màu, KHÔNG phải cho phép WB tự động, vì `0x3406=1` giữ chế độ thủ công. `wb_mode=0` (chế độ tự động) và `awb_gain=0` bị từ chối trước HTTP cho hồ sơ cố định; miền phần cứng `CONTROL_DOMAINS` (`wb_mode` 0–4, `awb_gain` 0/1) giữ nguyên. Hồ sơ `awb=0` lưu từ Vòng 3–6 (gồm `cam_VGA_q10_20260923.json` và bốn hồ sơ 24/09) không còn áp/verify được — báo lý do L11, phải tạo hồ sơ mới, không sửa tệp cũ. `/status` hiện không xuất `0x5001`, nên trạng thái khối xử lý màu chỉ kiểm gián tiếp qua control `awb` và phép đo ảnh; L11 chỉ đóng khi ảnh thật đạt O5–O7 |
| `expected_registers` | Giá trị phải giữ nguyên trong phiên: `0x3500`, `0x350a`, `0x3400`, `0x3404`, cộng `0x3402`, `0x3406`, `0x3503` (Vòng 5, L07 — ba thanh ghi gain màu/chế độ manual AEC/AGC thêm để chứng minh chế độ khoá thực sự ổn định; không suy PID từ các thanh ghi này) |
| `lens_note` | Theo D016 |
| `verified` | `{session_id, mean_drift_pct, registers_stable: bool}` — ghi sau phiên kiểm trên bo, ban đầu `null` |

**`camera_profile.py --probe` (Vòng 5, L07):** trước khi `--create`, người
dùng có thể chạy `--probe` để bật tạm `aec`/`agc`/`awb=1` (camera tự
chỉnh), đọc nhiều mẫu `/status` liên tiếp và đề xuất **ứng viên**
`aec_value = round(0x3500 ÷ 16)`, `agc_gain = round((0x350a + 1) ÷ 16)`
từ giá trị trung vị. Đây chỉ là gợi ý CHƯA XÁC MINH — không tạo hay đánh
dấu hồ sơ; người dùng vẫn phải `--create` với giá trị đó rồi đối chiếu
`/status` thật để kết luận. Sau `--probe`, camera ở trạng thái tự động
cho tới khi `--create` áp lại control khoá. **Vòng 6 (L08):** vì AEC tự
động không bị kẹp còn `--create` thì bị (xem trần 783 ở trên), `--probe`
phân biệt bốn giá trị trong log/đầu ra: `aec_value_raw` (chưa kẹp, có thể
> 783), `aec_value_effective` (đã kẹp về `[0, 783]`, dùng thẳng được cho
`--create`), `aec_value_cap` (783), `aec_value_clamped` (`true`/`false`).
Trường `aec_value` giữ nghĩa cũ = giá trị **effective** để không phá
tương thích với script đọc log trước đó.

**Bảng thanh ghi gain màu theo `wb_mode` (Vòng 6, L10, driver OV3660
chuẩn — đối chiếu trên bo thật trước khi dùng để chọn preset):**

| `wb_mode` | `0x3400` | `0x3402` | `0x3404` | `0x3406` |
| --- | ---: | ---: | ---: | ---: |
| 1 Sunny | `0x05e0` | `0x0410` | `0x0540` | `1` |
| 2 Cloudy | `0x0650` | `0x0410` | `0x04f0` | `1` |
| 3 Office | `0x0520` | `0x0410` | `0x0660` | `1` |
| 4 Home | `0x0420` | `0x03f0` | `0x0710` | `1` |

Nếu bo thật trả bộ ba gain khác bảng này, đó là bằng chứng driver/binary
khác phiên bản — dừng, không tự sửa bảng hay chọn preset theo cảm tính
(xem `docs/procedures/quy-trinh-c2-camera-profile.md`).

**Xác thực chéo thanh ghi WB (Vòng 7, L11):** bảng trên là hợp đồng, không
chỉ là tài liệu tham khảo. (1) Hồ sơ lưu sẵn: `expected_registers` phải có
`0x3406=1` và `0x3400`/`0x3402`/`0x3404` đúng dòng của `controls.wb_mode`;
sai → từ chối trước HTTP (`--verify`, `capture_session.py --profile`). (2)
Khi áp (`--create`/`--verify`/capture): áp theo thứ tự `awb` → `awb_gain`
→ `wb_mode`, đọc lại `/status`, bốn thanh ghi WB phải khớp bảng **trước
khi** ghi hồ sơ — không lấy giá trị bo đang tự chỉnh làm mốc; HTTP 200 mà
thanh ghi không đổi là FAIL. (3) Cuối phiên, `0x3406` và ba gain nằm trong
bảy `expected_registers` nên drift bị bắt như các thanh ghi khác.

**Chuẩn bị phiên tham chiếu tự động (Vòng 7):** `--probe` và ảnh tham chiếu
(bước B của quy trình thao tác) phải chạy ở chế độ tự động THẬT, không sót
preset thủ công từ lần tạo hồ sơ trước. `--probe` đặt `aec=1`, `agc=1`,
`awb=1`, `awb_gain=1`, **`wb_mode=0` áp cuối** (mode 0 xoá thủ công,
`0x3406=0`), rồi đọc lại và đòi đúng năm control đó cùng `0x3406=0` ở mọi
mẫu trước khi phát ứng viên; trạng thái này ghi vào log probe (`auto_state`).
Một phiên còn `0x3406=1` không được gọi là phiên tự động.

`capture_session.py --profile <id>` (làm rõ Vòng 3, xử lý phát hiện G02/G03
của Tester — bản trước viết "so `expected_registers` trước–sau" đọc được
hai cách, nay chốt một cách): áp `controls`, đọc `/status` ngay sau khi áp
rồi so **giá trị `expected_registers` GHI TRONG CHÍNH HỒ SƠ ĐÃ LƯU** (không
phải giá trị vừa đọc được) — lệch thì dừng ngay, `status = error`, KHÔNG
chụp ảnh nào. Cuối phiên đọc lại `/status` một lần nữa và so lại CÙNG hồ
sơ đó (`expected_registers` **và** `framesize`/`quality`/14 `controls`) —
lệch ở bất kỳ trường nào cũng `status = error`, không PASS, dù ảnh đã
chụp vẫn được giữ nguyên. Không đọc được `/status` ở một trong hai thời
điểm → ghi `"khong doi chieu duoc"`/lỗi tương ứng, không kết luận "không
đổi" (review R02).

Đối chiếu 20/09 (D023): quy ước tên tệp `_try<k>` và trường `attempt`
bắt đầu từ 1 lấy theo mã đã có selftest (`pc/capture_session.py` từ
`eafc784`); bản đầu của tệp này ghi `_r<k>` và `attempt` từ 0, đã sửa ở
đây. `capture_session.py` (tuần 1, không laser, không góc) ghi
`attempts.jsonl` — tập con của `captures.jsonl` chỉ có sự kiện `capture`
với các trường `idx`, `try`, `t_request`, `http_status`, `bytes`,
`elapsed_ms`, `sha256_16`, `x_timestamp`, `error`, `accepted`, `file`.
`pair_capture.py` (C5) dùng đúng `captures.jsonl` như mục 4.

## 6. Việc mã phải làm theo tệp này

- C2 (Vòng 3, 21/09): ĐÃ CÓ mã — `pc/camera_profile.py` tạo
  `camera_profiles/<id>.json`, `pc/capture_session.py --profile` áp hồ sơ,
  ghi `schema_version = 2`, `status`, `camera_profile_id`, `camera_config`
  (`camera_status_*.json` đã tách tệp từ tuần 1, giữ nguyên). Đối chiếu
  hồ sơ thiết kế–firmware (`sharpness`, `aec/agc/awb=0`, `stream_disabled`)
  đã cập nhật ở mục 5 và 3 trên. Chưa làm: đánh dấu `verified` sau khi có
  bằng chứng bo thật (không có lệnh tự động, xem
  `docs/procedures/quy-trinh-c2-camera-profile.md`).
- C2 (Vòng 5, 22–23/09, xử lý L05–L07 của `03_TEST.md` Vòng 4): ĐÃ CÓ mã —
  `DEFAULT_CONTROLS` khoá đúng `vflip=1`/`brightness=1`/`saturation=-2`
  (L05); `--create` bắt buộc `aec_value`/`agc_gain`/`awb_gain`/`wb_mode`
  truyền tường minh qua `--set`, không còn mặc định chưa đo (L06);
  `--probe` đề xuất ứng viên phơi sáng CHƯA xác minh; `expected_registers`
  mặc định có bảy khoá (L07); ID hồ sơ chấp nhận hậu tố retry `_rNN`
  không ghi đè. `docs/SPEC.md` mục 10.2 (O5–O7, D032) là cổng định lượng
  màu/phơi sáng thay câu chủ quan. Chưa làm: đo O5–O7 và T5 trên bo thật
  với mã Vòng 5 (`CẦN BO`, xem thư mục thao tác ở trên).
- C2 (Vòng 6, 23/09, xử lý L08/L10 của `03_TEST.md` Vòng 5 phần bo — lần
  đo đầu tiên trên OV3660 thật dừng ở preset 1 vì ứng viên `--probe` vượt
  trần thiết bị và nghi vấn `wb_mode` vô tác dụng khi `awb_gain=0`): ĐÃ CÓ
  mã — trần `aec_value` 783 đo được cho VGA/SVGA, `--probe` tách rõ ứng
  viên thô/effective/cap/clamped, `--create` từ chối `aec_value > 783`
  trước HTTP; hồ sơ cố định chuyển sang `awb_gain=1` khi chọn preset
  `wb_mode`, cặp `wb_mode>0`/`awb_gain=0` bị từ chối trước HTTP; mock mô
  phỏng cả hai (kẹp AEC, bảng thanh ghi bốn preset) để kiểm được không
  cần bo. Chưa làm: xác nhận bảng thanh ghi WB và trần AEC trên chính
  binary đang nạp (`CẦN BO`), sau đó mới chạy lại T5/C2b với preset đã
  xác minh (ảnh/preset lần đo đầu đã xoá theo yêu cầu người dùng, không
  dùng làm bằng chứng Q9).
- C2 (Vòng 7, 24/09, xử lý L11 của `03_TEST.md` Vòng 6 — bảng thanh ghi và
  trần AEC đã ĐẠT trên bo, nhưng bốn preset cho cùng một màu ảnh vì
  `awb=0` tắt khối áp gain): ĐÃ CÓ mã — hợp đồng hồ sơ đổi sang `awb=1`
  (bật khối xử lý màu) cùng `awb_gain=1`, `wb_mode=1..4`, `0x3406=1`;
  `wb_mode=0`/`awb_gain=0`/`awb=0` bị từ chối trước HTTP; `expected_registers`
  phải khớp bảng WB của chính `wb_mode` (kiểm cả khi đọc hồ sơ và sau khi
  áp); `--probe` reset về tự động (`wb_mode=0`, `0x3406=0`) và kiểm lại
  trước khi phát ứng viên. Chưa làm: phép thử ảnh thật với `awb=1` + gain
  thủ công (`CẦN BO`) — L11 chỉ đóng khi có ít nhất một preset đạt O5–O7;
  nếu `awb=1` vẫn cho cùng kiểu lỗi thì dừng về Planner (xét đối chiếu/
  instrument firmware, `0x5001` chưa có trong `/status`).
- C5a (Vòng 2, 02/10; Vòng 5, 03/10 — D043; Vòng 6, 03/10 — D044): Triển khai Q6 endpoint `/capture_fresh` trên ESP32-S3 theo Phương án B (D041, D043); tài liệu đặc tả độc lập `docs/design/S3_FRESH_CAPTURE.md`; bảo đảm khung hình lấy sau mốc request (`frame_timestamp > request_timestamp`); cấp 5 headers chẩn đoán bắt buộc (`X-Frame-Id`, `X-Boot-Id`, `X-Timestamp`, `X-Request-Timestamp`, `X-Discarded-Frames`); cấu hình `fb_count = 1`, `CAMERA_GRAB_LATEST` cho JPEG PSRAM (SPEC §10); mutex chung `s_cam_mutex` (100 ms) bảo vệ mọi handler chạm camera/sensor; FSM lọc stale với hạn chót 1.5 s (dừng ở stale thứ 5); PC probe độc lập `pc/fresh_capture_probe.py` (deadline tổng 10 s, socket 5 s); giữ `/capture` cũ để tương thích. Bổ sung telemetry giám sát heap trong `/status` (D044): `heap_internal_free_bytes` và `heap_psram_free_bytes` là telemetry động, không thuộc controls hay expected_registers của profile, không làm đổi schema profile C2 hay params C3; biến động của 2 trường này trong `compare_status` phản ánh bộ nhớ runtime, không phải trôi cấu hình cảm biến. Profile chính áp dụng cho nghiệm thu bo thật Q6-T9 theo D044 là `cam_SVGA_q20_20260928` (800×600, quality 20, SHA-256 `5c32b27b4e52a2518cba01caee03d19d95db1c31a0e8dde4fa315635ad85dbe6`).
- C5: `pair_capture.py` ghi `img_<step>_off/on`, `command_id`,
  `laser_state_cmd`, `attempt`, không ghi đè; dùng `captures.jsonl` đầy đủ
  mục 4, khác tập con camera-only của C2.
- A1/A2/D1 (D048, p02 G): Lược đồ hồ sơ hiệu chuẩn `calibration.json` được chốt chi tiết tại mục 7 dưới đây.

## 7. Lược đồ hồ sơ hiệu chuẩn `calibration.json` (A1/A2/Trục quay)

> [!IMPORTANT]
> Dữ liệu trong tệp mẫu `calibration.json` dưới đây chỉ mang tính chất **minh hoạ cấu trúc schema và định dạng dữ liệu JSON**, TUYỆT ĐỐI KHÔNG phải là giá trị đo thực tế, giá trị mặc định hay tham số đã nghiệm thu của hệ thống thật. Các giá trị thực tế bắt buộc phải được sinh ra từ quy trình tính toán hiệu chuẩn thực nghiệm của nhánh A1 (`p06`), A2 (`p10`) và B2 (`p11`).

Định dạng JSON tại `data/calibration/<calibration_id>/calibration.json`:

```json
{
  "version": 1,
  "calibration_id": "calib_SVGA_20261009_01",
  "unit": "mm",
  "created_at": "2026-10-09T14:00:00+07:00",
  "source_commit": "9d3b86b",
  "camera_profile_id": "cam_SVGA_q20_20260928",
  "camera_config": {
    "framesize": "SVGA",
    "quality": 20,
    "img_width": 800,
    "img_height": 600
  },
  "camera": {
    "matrix_k": [
      [850.0, 0.0, 400.0],
      [0.0, 850.0, 300.0],
      [0.0, 0.0, 1.0]
    ],
    "distortion": [0.0, 0.0, 0.0, 0.0, 0.0],
    "distortion_model": "radtan_5",
    "reprojection_error_rms_px": 0.35
  },
  "laser": {
    "normal": [0.0, 0.0, 1.0],
    "d_mm": -100.0,
    "plane_equation": "normal[0]*x + normal[1]*y + normal[2]*z + d_mm = 0",
    "rms_fit_error_mm": 0.25
  },
  "turntable": {
    "center_mm": [0.0, 150.0, 300.0],
    "axis_vector": [0.0, -1.0, 0.0],
    "rotation_sign": 1,
    "zero_angle_deg": 0.0
  },
  "provenance": {
    "calibration_images_count": 25,
    "laser_images_count": 10,
    "operator_note": "Hồ sơ hiệu chuẩn A1+A2+B2"
  }
}
```

**Quy tắc hợp đồng hiệu chuẩn:**
1. **Đơn vị hình học:** Đơn vị không gian thế giới bắt buộc là `mm`.
2. **Quy ước mô hình méo ống kính (`distortion_model = "radtan_5"`):**
   - Áp dụng mô hình chuẩn OpenCV Brown-Conrady gồm 5 hệ số.
   - Thứ tự bắt buộc trong mảng `distortion` là: `[k1, k2, p1, p2, k3]`, trong đó:
     + \(k_1, k_2, k_3\): các hệ số méo xuyên tâm (radial distortion);
     + \(p_1, p_2\): các hệ số méo tiếp tuyến (tangential distortion).
3. **Quy tắc đối chiếu tương thích `camera_config` (`session.json` ↔ `calibration.json`):**
   - Thuật toán tái tạo 3D (`Reconstructor`) bắt buộc kiểm tra sự tương thích trước khi xử lý:
     + **So khớp bắt buộc:** `camera_config.framesize` trong `session.json` phải trùng khớp chính xác chuỗi ký tự với `calibration.json` (ví dụ: cùng là `"SVGA"`).
     + **Kích thước độ phân giải:** `img_width` và `img_height` của dữ liệu hiệu chuẩn phải khớp đúng với độ phân giải của ảnh thực tế (ví dụ: 800×600 cho SVGA, 640×480 cho VGA).
     + **Chất lượng nén (`quality`):** nên khớp nhau hoặc ghi log cảnh báo nếu lệch (mức nén JPEG không làm thay đổi tiêu cự quang học hay tâm quang trường, nhưng có thể ảnh hưởng chất lượng trích vạch tâm laser).
     + **Các trường đặc thù riêng:** Các trường chỉ thuộc phiên thu nhận (`stream_disabled`, `lens_note`) hoặc chỉ thuộc hồ sơ hiệu chuẩn (`reprojection_error_rms_px`, `provenance`) không bắt buộc phải có mặt chéo giữa hai bên.
     + Nếu `framesize` hoặc kích thước `(img_width, img_height)` bị lệch: lập tức từ chối xử lý với lỗi `CALIB_CAMERA_MISMATCH`.
4. **Phân tầng yêu cầu theo giai đoạn:**
   - **Giai đoạn A1 (Hiệu chuẩn camera):** Hồ sơ chỉ cần trường `camera` hợp lệ (`matrix_k`, `distortion`).
   - **Giai đoạn A2 (Hiệu chuẩn laser):** Bắt buộc có thêm trường `laser` (`normal` là vectơ đơn vị \(\|n\|=1\), `d_mm` hữu hạn).
   - **Giai đoạn D1 (Tái tạo 3D quét đa góc):** Bắt buộc có đủ cả `camera`, `laser` và `turntable` (`center_mm`, `axis_vector` đơn vị, `rotation_sign` \(\pm 1\)).
   - Thiếu phần bắt buộc cho bài toán tương ứng phải từ chối xử lý, không tự điền tham số rỗng hay số đo giả định để báo kết quả mm đã nghiệm thu.
5. **Quy ước tên tệp ảnh:** Chốt sử dụng theo `step_index` bốn chữ số: `img_<step:04d>_<off|on>.jpg` (từ `img_0000_off.jpg` đến `img_0199_on.jpg`).

## 8. Phạm vi triển khai sau tuần 2 — D048, 08/10/2026

Một cấu hình camera chính, 200 góc / 400 ảnh được chọn (0000..0199); PLY là đầu ra bắt buộc của quy trình tái tạo 3D. Các schema, trường metadata, cách lưu ảnh/retry và hợp đồng tuần 2 ở trên không thay đổi. `points_raw.xyz` nếu dùng là dữ liệu trung gian, không phải định dạng xuất mới bắt buộc. Các phần đã hiện thực/kiểm trên bo tiếp tục theo bằng chứng handoff, không suy từ roadmap.
