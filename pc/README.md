# Phần mềm trên PC

Thư mục dành cho thu ảnh, điều phối, hiệu chuẩn, trích vạch và tái tạo.
Theo D048, kế hoạch hiện hành tại [ROADMAP](../docs/ROADMAP.md): một cấu
hình camera, 200 góc/400 ảnh, PLY đơn vị mm và GUI tối thiểu. GUI E1 được
làm với dữ liệu giả song song bộ điều phối D1 khi giao diện đã chốt ở G;
tích hợp thật tại H4. Xem 3D bằng công cụ độc lập; dựng lưới và trình xem
tích hợp chuyển tốt nghiệp. Đây là phạm vi dự kiến, không phải chức năng
đã có. Công cụ và phép thử tuần 2 bên dưới giữ nguyên.

## Môi trường

`.venv` ở thư mục gốc, tạo ngày 2026-09-16 từ Python 3.11.9 tại
`C:\Program Files\Python311\python.exe`. Gói đã cài và đóng băng trong
[requirements.txt](requirements.txt): `requests`, `Pillow`, từ 16/09
`pyserial` 3.5 và từ 16/09 tối `numpy` 2.4.6 (cho `sharpness.py`), cùng phụ
thuộc. Chưa cài OpenCV, Open3D; chỉ thêm phụ thuộc khi gói triển khai cần.
Open3D không phải yêu cầu bắt buộc của phạm vi rút gọn.

Tạo lại môi trường trên máy khác, gõ trong Git Bash ở thư mục gốc repo:

```
"/c/Program Files/Python311/python.exe" -m venv .venv
.venv/Scripts/python.exe -m pip install -r pc/requirements.txt
```

## capture_session.py

Thu ảnh thử từ ESP32-S3 CameraWebServer qua `/capture`, phục vụ chỉ tiêu
B "Thu ảnh thử" tuần 1: 100/100 tệp giải mã đúng, đúng kích thước, không
reset trong 20 phút, ghi số lần chụp lại. Mỗi lần chạy là một phiên có ID
riêng, không ghi đè. JPEG giữ nguyên gốc như nhận từ bo. Metadata theo
`data/README.md`: commit nguồn, trạng thái working tree, cấu hình camera
từ `/status` trước và sau phiên, thời gian và kết quả kiểm tra từng ảnh,
số lần chụp lại, lỗi. Trường chưa có ở tuần 1 ghi "chưa áp dụng".

Phát hiện reset: `X-Timestamp` của `/capture` là thời gian từ lúc bo khởi
động; nếu nó lùi lại giữa hai ảnh thì bo đã khởi động lại. Phát hiện ảnh
cũ: so sha256 và `X-Timestamp` với ảnh trước.

Chạy từ thư mục gốc repo. Shell của dự án là Git Bash trong VS Code theo `ENVIRONMENT.md`, lệnh dùng dấu `/`:

```
.venv/Scripts/python.exe pc/capture_session.py --selftest
.venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA --count 100 --interval 12 --meta-copy docs/logs
```

Nếu dùng PowerShell hoặc cmd thì thay `/` bằng dấu gạch chéo ngược kiểu
Windows trong hai đường dẫn đầu của mỗi lệnh. Quy trình từng bước cho
người dùng nằm ở mục "Quy trình chạy phép thử 100 ảnh" trong `STATUS.md`.

`--selftest` không cần bo. `--meta-copy docs/logs` chép hồ sơ phiên, không
gồm ảnh, vào `docs/logs/<session_id>/` vì `data/raw/` không vào Git.

Thêm 21/09 (C2), sửa lại Vòng 3 sau review (xử lý G01–G04): `--profile
<đường dẫn>.json` thay cho `--framesize` — áp đúng framesize/quality/14
control của hồ sơ camera (`camera_profile.py` tạo ra), đọc lại `/status`
ngay sau khi áp rồi so **giá trị `expected_registers` ghi TRONG CHÍNH HỒ
SƠ** (không phải giá trị vừa đọc được) — lệch thì FAIL ngay, KHÔNG chụp
ảnh nào. Cuối phiên đọc `/status` lần nữa và so lại cùng hồ sơ đó, cả
thanh ghi **và** framesize/quality/14 control — lệch ở đâu FAIL ở đó,
nêu rõ trường/giá trị yêu cầu/giá trị bo báo; ảnh đã chụp vẫn giữ nguyên.
`session.json` khi dùng `--profile` có `schema_version: 2`, `status`
(`running` ngay khi bắt đầu áp; `completed`/`error` khi kết thúc;
`aborted` nếu bị ngắt `Ctrl+C` — dữ liệu đã nhận không mất), `requested.framesize`/`quality`
lấy đúng hồ sơ (không còn ghi "giu nguyen tren bo"), `camera_profile_id`,
`camera_config` (`stream_disabled` là `null` kèm `stream_disabled_reason`
khi chưa có bằng chứng, KHÔNG tự ghi `true`) theo `docs/design/SCAN_SESSION.md`
mục 3, 5. Không dùng cùng `--framesize`.

```
.venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 \
    --profile data/calibration/camera_profiles/cam_VGA_q10_20260922.json \
    --count 5 --interval 2 --meta-copy docs/logs
```

## camera_profile.py

Thêm 21/09 (C2/C2b). Tạo, áp và đối chiếu hồ sơ camera cố định
(`data/calibration/camera_profiles/<id>.json`) theo
`docs/design/SCAN_SESSION.md` mục 5: khoá `framesize`, `quality` và 14
control tự động (`aec`, `agc`, `awb`, `aec_value`, `agc_gain`,
`awb_gain`, `wb_mode`, `brightness`, `contrast`, `saturation`,
`hmirror`, `vflip`, `lenc`, `dcw`) qua `/control` đã có sẵn trong
`app_httpd.cpp`, rồi đọc `/status` để xác nhận đúng giá trị và lưu bảy
thanh ghi bắt buộc (`0x3500`, `0x350a`, `0x3400`, `0x3404`, `0x3402`,
`0x3406`, `0x3503`, thêm ba thanh ghi Vòng 5 — xem đoạn dưới) làm mốc.

Giới hạn đã biết: firmware hiện tại KHÔNG có nhánh xử lý biến
`sharpness` trong `/control` (chỉ đọc được qua `/status`), dù
`SCAN_SESSION.md` liệt kê nó trong `controls`; script vì vậy không áp
hay yêu cầu trường này. Muốn khoá `sharpness` phải sửa firmware trước,
thuộc một đầu việc khác.

**Vòng 5 (xử lý L05–L07, `03_TEST.md` Vòng 4 — T5 trên OV3660 thật cho
ảnh lật ngược và ám lục):** `DEFAULT_CONTROLS` trong mã chỉ còn khoá ba
giá trị CHẮC CHẮN của OV3660 — `vflip=1`, `brightness=1`, `saturation=-2`
(firmware tự đặt cho đúng PID này, không phụ thuộc AEC/AGC/AWB; khoá về
`0` như trước Vòng 5 làm ảnh lật ngược, L05). Bốn giá trị `aec_value`,
`agc_gain`, `awb_gain`, `wb_mode` **KHÔNG còn mặc định**: `--create`
BẮT BUỘC truyền cả bốn qua `--set VAR=GIA_TRI` (lặp lại được), thiếu một
trong bốn bị từ chối TRƯỚC HTTP, nêu đúng tên trường — mặc định im lặng
trước đây (Vòng 3–4) từng tạo hồ sơ "hợp lệ" nhưng ảnh tối 12,8 lần và ám
lục (L06). Bảy trường trên cộng `vflip`/`brightness`/`saturation` có
miền giá trị kiểm trước HTTP theo bằng chứng Espressif/firmware
(`CONTROL_DOMAINS` trong mã): `aec_value` 0–1200, `agc_gain` 0–30,
`awb_gain` 0/1, `wb_mode` 0–4, `vflip` 0/1, `brightness`/`saturation`
−2–2. `aec`/`agc`/`awb` vẫn bắt buộc bằng `0` (Vòng 3: hồ sơ cố định
không được để camera tự động phơi sáng/cân bằng trắng; `--set aec=1` bị
từ chối trước khi chạm bo). **Từ Vòng 7, `awb` bắt buộc bằng `1`** —
xem đoạn Vòng 7 dưới; `aec`/`agc` vẫn bằng `0`. Hồ sơ tạo ra luôn có `"verified": null` cho
tới khi có một phiên trên bo thật kèm bằng chứng (T5). `--create`/
`--verify` kiểm `--quality` (0–63) và `--timeout` (số hữu hạn > 0, chặn
cả `Infinity`/`NaN`) TRƯỚC khi gửi bất kỳ `/control` nào. Một `/control`
lỗi (HTTP/kết nối) làm dừng ngay, không gửi tiếp các lệnh còn lại.

**Vòng 6 (xử lý L08/L10, `03_TEST.md` Vòng 5 phần bo — lần đo đầu tiên
trên OV3660 thật dừng ở preset 1):** `aec_value` đặt tay qua `--create`
bị BO KẸP CỨNG ở **783** trên VGA và SVGA (đo trực tiếp: gửi 784–1200 bo
đều báo lại `783`); miền `0–1200` ở trên chỉ đúng khi AEC **tự động**
(không qua hàm kẹp). `--create --framesize VGA|SVGA` với `aec_value > 783`
bị từ chối TRƯỚC HTTP, nêu rõ trần (`AEC_VALUE_HARD_CAP`); framesize khác
chưa đo, chưa áp trần. Đồng thời, `awb_gain` là **cờ bật/tắt** gain AWB
thủ công, không phải giá trị gain — nếu `wb_mode > 0` mà `awb_gain = 0`
thì preset không có tác dụng (nghi vấn L10, khớp hiện tượng ám lục quan
sát được); hồ sơ cố định vì vậy dùng **`awb_gain=1`** khi chọn một trong
bốn preset `wb_mode ∈ {1,2,3,4}` — cặp `wb_mode>0` với `awb_gain=0` bị
từ chối TRƯỚC HTTP (bất biến chéo, không phải lỗi từng trường).

**Vòng 7 (xử lý L11, `03_TEST.md` Vòng 6 — bốn preset trên bo thật đều
cho `channel_spread_pct` 26,2–26,4%, trượt O6):** gain preset đã GHI đúng
thanh ghi nhưng không lên ảnh, vì `awb=0` tắt cả khối xử lý cân bằng
trắng (bit 0 của `0x5001` theo driver OV3660 của Espressif; `/status`
chưa xuất thanh ghi này). `awb` là công tắc khối đó; chế độ thủ công do
`wb_mode` 1–4 chọn (đặt `0x3406=1` và ba gain). Hồ sơ cố định vì vậy là
**`aec=0`, `agc=0`, `awb=1`, `awb_gain=1`, `wb_mode ∈ {1,2,3,4}`**:
`awb` khác `1` (kể cả `0`, `2`, `true`) và `wb_mode=0` bị từ chối TRƯỚC
HTTP. `expected_registers` của hồ sơ phải có `0x3406=1` và ba gain
`0x3400`/`0x3402`/`0x3404` đúng bảng preset (`WB_MODE_REGISTERS` trong
mã); sau khi áp, `--create`/`--verify` đối chiếu bốn thanh ghi này trong
`/status` với bảng trước khi ghi hồ sơ — bo trả HTTP 200 mà thanh ghi
không đổi vẫn là lệch. **Hồ sơ `awb=0` tạo ở Vòng 3–6 không còn dùng
được:** `--verify` và `capture_session.py --profile` từ chối ngay, nêu
L11, không gửi request nào; script không tự sửa tệp cũ — tạo hồ sơ mới
bằng `--create` với ID mới. Mock chỉ chứng minh giao thức; gain có thật
sự lên JPEG hay không chỉ kiểm được bằng ảnh trên bo (cổng O5–O7).

**`--probe` (Vòng 5, L07; kẹp thêm ở Vòng 6, L08; reset tự động đủ ở
Vòng 7, L11)** — chưa biết `aec_value`/`agc_gain` phù hợp với ánh sáng
hiện tại thì chạy trước: đưa camera về tự động hoàn toàn theo thứ tự
`aec=1`, `agc=1`, `awb=1`, `awb_gain=1`, `wb_mode=0` (mode cuối cùng, xoá
preset thủ công còn sót, `0x3406` về `0`; một lệnh lỗi là dừng), bỏ qua
`--warmup` khung `/capture` cho camera tự chỉnh ổn định, đọc `--samples`
mẫu `/status` liên tiếp — mẫu nào chưa đúng trạng thái tự động (năm
control trên và `0x3406=0`) thì probe THẤT BẠI, không phát ứng viên; log
JSON ghi trạng thái đó ở trường `auto_state` (mặc định 5 mẫu, cách
nhau `--interval` giây) rồi đề xuất ỨNG VIÊN `aec_value = round(0x3500 ÷
16)`, `agc_gain = round((0x350a + 1) ÷ 16)` từ giá trị trung vị. Vì AEC
tự động ghi thẳng thanh ghi (không qua hàm kẹp) nhưng `--create` thì kẹp,
ứng viên thô có thể vượt 783; đầu ra và log JSON (nếu có `--out`) tách rõ
bốn trường `aec_value_raw` (chưa kẹp), `aec_value_effective` (đã kẹp,
dùng thẳng được cho `--create`), `aec_value_cap` (783),
`aec_value_clamped` (`true`/`false`) — trường `aec_value` giữ nghĩa cũ =
**effective**. `--probe` KHÔNG tạo hay đánh dấu hồ sơ nào — chỉ in ra để
người dùng tự `--create` với giá trị đó rồi đối chiếu `/status` thật. Sau
`--probe`, camera còn ở trạng thái tự động cho tới khi `--create` áp lại
control khoá.

Vòng 4 (R02, `04_REVIEW.md`): `validate_profile()` và `--id` tuỳ chỉnh
đều bị kiểm chặt hơn TRƯỚC HTTP — `camera_profile_id` phải đúng mẫu
`cam_<framesize>_q<quality>_<YYYYMMDD>`, không chứa `/`, `\` hay `..`, và
phải khớp đúng `--framesize`/`--quality` đang tạo; `board`/`sensor` phải
đúng `ESP32-S3 N16R8`/`OV3660 PID 0x3660`; `created_at` phải có múi giờ;
`source.commit` phải là hash Git đủ 40 ký tự hex. `--id` tự đặt sai mẫu
bị từ chối trước khi chạm bo, không chờ tới lúc ghi tệp. **Vòng 5:** ID
có thể có hậu tố retry `_rNN` hai chữ số (`_r01`…`_r99`) — khi `--id`
không truyền và tên gốc `cam_<framesize>_q<quality>_<ngay>.json` đã tồn
tại trong `--out`, `--create` tự chọn hậu tố kế tiếp còn trống thay vì
từ chối, để nhiều lần thử trong cùng ngày/cấu hình không ghi đè lần
trước; `--id` tự đặt vẫn bị từ chối nếu tệp đã tồn tại (không tự thêm
hậu tố cho ID người dùng chỉ định).

```
.venv/Scripts/python.exe pc/camera_profile.py --selftest

# Chua biet muc phoi sang: doc ung vien truoc (khong tao ho so)
.venv/Scripts/python.exe pc/camera_profile.py --probe --host 192.168.31.9

# Tao ho so chinh VGA q10 - BAT BUOC ca bon --set (Vong 5); awb=1, awb_gain=1 va
# wb_mode=1..4 di cung nhau (Vong 7, L11); aec_value toi da 783 tren VGA/SVGA (L08)
.venv/Scripts/python.exe pc/camera_profile.py --create --host 192.168.31.9 \
    --framesize VGA --quality 10 \
    --set aec_value=490 --set agc_gain=2 --set awb=1 --set awb_gain=1 --set wb_mode=1

# Tao bon cau hinh C2b: VGA/SVGA x quality 10/20 (doi gia tri hieu chinh theo --probe moi khoang cach/anh sang; giu dung wb_mode da chon)
.venv/Scripts/python.exe pc/camera_profile.py --create --host 192.168.31.9 --framesize VGA  --quality 10 --set aec_value=490 --set agc_gain=2 --set awb=1 --set awb_gain=1 --set wb_mode=1
.venv/Scripts/python.exe pc/camera_profile.py --create --host 192.168.31.9 --framesize VGA  --quality 20 --set aec_value=490 --set agc_gain=2 --set awb=1 --set awb_gain=1 --set wb_mode=1
.venv/Scripts/python.exe pc/camera_profile.py --create --host 192.168.31.9 --framesize SVGA --quality 10 --set aec_value=490 --set agc_gain=2 --set awb=1 --set awb_gain=1 --set wb_mode=1
.venv/Scripts/python.exe pc/camera_profile.py --create --host 192.168.31.9 --framesize SVGA --quality 20 --set aec_value=490 --set agc_gain=2 --set awb=1 --set awb_gain=1 --set wb_mode=1

# Doi chieu lai mot ho so da co (khong tao moi)
.venv/Scripts/python.exe pc/camera_profile.py --verify --host 192.168.31.9 \
    --profile data/calibration/camera_profiles/cam_VGA_q10_20260922.json
```

Nếu `--create` báo lệch (`KHONG tao ho so, lech: ...`): đọc đúng dòng
`/control <var> = <val> LOI <lý do>` hoặc dòng lệch giá trị, không có
tệp nào được ghi (không ghi đè, không ghi hồ sơ nửa vời). Chạy lại sau
khi sửa nguyên nhân (ví dụ bo chưa nhận `/control`, mất kết nối Wi-Fi).
`--create` không `--id` tự chọn tên còn trống trong `--out` (mặc định
`data/calibration/camera_profiles/`, xem hậu tố retry ở trên); `--id` tự
đặt mà tên đã tồn tại thì bị từ chối, đổi `--id` khác hoặc bỏ `--id` để
script tự chọn hậu tố.

Selftest không cần bo (lược đồ, so thanh ghi, ID/board/sensor/created_at/
source.commit, miền giá trị control, ID retry, kiểm tham số Vòng 3–5; số
mục đổi theo từng vòng sửa, xem `--selftest` in ra "SELFTEST: PASS" kèm
số dòng thực tế thay vì đếm ở đây); kết quả chạy ghi trong
`handoff/2026-09-21_c2-camera-profile/02_BUILD.md`, chưa có log riêng
trong `docs/logs/` (ngoài danh sách trắng của đầu việc này). Tiêm lỗi cho
`camera_profile.py`/`capture_session.py --profile` nằm ở `mock_camera.py`
(`--ignore-controls`, `--fail-controls`, `--drift-registers` +
`--drift-after`, `--status-drop-fields`, `--control-drift-fields` +
`--control-drift-after`, `--registers` (Vòng 5, ghi đè thanh ghi ban đầu
cho kịch bản `--probe`), `--status-fail-at-count` (Vòng 5, lỗi `/status`
đúng lần thứ N theo `/_counts`, dùng cho `--probe` nhiều mẫu), `/_counts`
đếm request theo loại) và các tình huống trong `e2e_capture_mock.py`
(`profile_baseline`, `profile_register_drift`, `profile_control_rejected`,
`profile_status_missing_field`, `profile_invalid_schema`,
`profile_and_framesize_conflict`, bốn tình huống Vòng 3
`profile_register_mismatch_at_start_G02`, `profile_control_drift_at_end_G03`,
`profile_locked_control_rejected_G04`, `profile_first_control_fails_fast_G04`,
cộng tám tình huống Vòng 5 `cp_create_missing_explicit`,
`cp_create_explicit_ok`, `cp_create_domain_out_of_range`,
`cp_create_id_retry`, `cp_probe_ok`, `cp_probe_missing_register`,
`cp_probe_status_fail_at_count`, `cp_probe_control_reject`, cộng năm
tình huống Vòng 6 (L08/L10) `cp_create_aec_over_cap`,
`cp_create_aec_at_cap`, `cp_create_wb_ambiguous`,
`cp_create_wb_registers_L10`, `cp_probe_clamp_L08`, cộng bảy tình huống
Vòng 7 (L11) `cp_create_awb0_rejected_L11`,
`cp_create_wb_mode0_rejected_L11`, `cp_create_wb_registers_stuck_L11`,
`cp_probe_reset_control_fails_L11`, `cp_probe_stuck_manual_wb_L11`,
`profile_awb0_legacy_rejected_L11`, `cp_probe_after_preset_L11`; mock
thêm `--wb-registers-stuck`).

Bảng `--framesize` lấy từ `sensor.h` của core esp32 3.3.11 và KHÁC bảng cũ
trong nhiều tài liệu: `QVGA`=6, `VGA`=10, `SVGA`=11, `UXGA`=15.

Giới hạn đã biết: JPEG bị cắt giữa chừng nhưng vẫn có dấu kết thúc FF D9
thì Pillow giải mã được với phần dưới màu xám, script không chặn được.
Trường hợp truyền thiếu thật sự được bắt bằng `Content-Length` khớp số
byte nhận. Selftest in rõ giới hạn này.

Điều kiện PASS (sửa 2026-09-20 theo `docs/reviews/REVIEW_2026-09-20_main_full.md`
R02–R05, cộng hai điểm trong ma trận review): đủ `count` ảnh đạt; không có
`X-Timestamp` lùi; **mọi ảnh đều có `X-Timestamp` hợp lệ** (thiếu thì không
kết luận được "không reset" → FAIL, không PASS ngầm); **`/status` đầu và cuối
đều đọc được** (JSON object có `framesize`) — không đọc được một đầu thì
`summary.txt` ghi `KHONG DOI CHIEU DUOC`, không ghi "không đổi". Tên header
tra không phân biệt hoa/thường. `Content-Length` không phải số, HTTP 200
body rỗng, `--count 0` đều bị coi là lỗi. Mỗi lần thử ghi một dòng vào
`attempts.jsonl`; payload của lần thử không đạt giữ ở `img_NNNN_tryK.jpg`
(JPEG) hoặc `.bin` (body lỗi HTTP); ảnh cuối được chọn vẫn là `img_NNNN.jpg`.
`--meta-copy` từ chối đích đã tồn tại, kiểm trước khi thu.

## nucleo_ping.py

Kiểm tra giao tiếp với Nucleo-F446RE qua COM ảo của ST-LINK, phục vụ
chỉ tiêu B "Giao tiếp Nucleo" tuần 1: 100 PING có 100 phản hồi đúng thứ
tự; nạp và chạy lại được sau khi rút cắm nguồn. Firmware đối diện là
`firmware/stm32/NucleoPing`, giao thức trong README ở đó.

Mỗi lần chạy là một phiên `ping_YYYYMMDD_HHMMSS`, ghi thẳng vào
`docs/logs/<id>/` vì không có ảnh: `session.json` (commit, cổng, tham số,
dòng `ID?`, kết quả), `pairs.csv` (từng cặp PING/PONG, độ trễ, uptime của
bo), `summary.txt` (khối tổng kết). PASS chỉ khi N/N PONG đúng số thứ
tự; sai ở đâu dừng ở đó, không gửi lại ngầm. `uptime_ms` trong PONG nhỏ
lại ở lần chạy sau khi rút cắm nguồn là bằng chứng bo đã chạy lại.

Chạy từ thư mục gốc repo, Git Bash:

```
.venv/Scripts/python.exe pc/nucleo_ping.py --selftest
.venv/Scripts/python.exe -m serial.tools.list_ports -v
.venv/Scripts/python.exe pc/nucleo_ping.py --port COM5 --count 100 --label run1
```

`--port` lấy từ lệnh `list_ports` ở trên, dòng có `STLink Virtual COM
Port`. KHÔNG dùng COM9: đó là CH343 của bo S3. `--selftest` chạy với bo
giả lập, kết quả 16/09 tại `docs/logs/pc-nucleo-ping-selftest-2026-09-16.log`.
Với bo thật 16/09 tối: 100/100 PASS trên COM3, `docs/logs/ping_20260916_185412/`.

Bài học 16/09: bản đầu gán `ser.timeout` sau mỗi byte; trên Windows pyserial
gọi `SetCommState` mỗi lần và driver VCP của ST-LINK xoá bộ đệm nhận, làm
mất byte xen kẽ (`ID NUCLEO-F4P3eccab9`). Selftest không bắt được vì bo
giả không đi qua driver. Nay timeout đặt đúng một lần đầu phiên.

Sửa 2026-09-20 (review R06): thư mục phiên, `session.json` và tiêu đề
`pairs.csv` được tạo **trước khi mở cổng**; mỗi cặp ghi dần ngay khi nhận.
Rút cáp, lỗi I/O của cổng (`OSError`, gồm `SerialException`) hay Ctrl+C
giữa phiên không còn làm mất hồ sơ: `session.json` ghi `FAIL - mat ket
noi ... sau PING n`, trường `aborted` = `io_error` hoặc `user_interrupt`.
Không mở được cổng → rc 3 và `session.json` ghi lý do; `--count 0` bị chặn.
Selftest 21 mục (thêm 6 mục R06), kết quả 20/09 tại
`docs/logs/pc-nucleo-ping-selftest-2026-09-20.log`. Nghiệm thu U8 trên bo thật
30/09: `docs/logs/ping_20260930_093952/` 100/100 PONG PASS.

**Thêm 2026-09-30 (C4), cập nhật 2026-10-01/02 (Vòng 7, Vòng 8/10, Vòng 11, Vòng 12 và Vòng 13):** Mở rộng hỗ trợ giao thức P1 (`--p1`) và các phép thử an toàn trên bo không tải:
- Đóng gói khung P1 `<seq> <CMD> [args...]*<HH>\n`, tính XOR checksum.
- Schema phản hồi `STATUS` chuẩn 10 token theo Q3 / D039: `DONE <state> <step_count> <laser> <door> <estop> <homed> <uptime_ms> <last_err> <remaining_ms>`.
- Gửi chuỗi kiểm tra tự động 11 bước (`--p1`): `STATUS`, `LASER ON/OFF`, `HEARTBEAT`, `STOP`, `CLEAR`, `HOME`/`MOVE_ABS` (`NOTIMPL`), kiểm tra trùng seq. Toàn bộ các bước kiểm tra chính xác nội dung/schema Q3 theo từng lệnh (L19: loại bỏ so khớp tiền tố `startswith` lỏng lẻo; `LASER ON` kiểm tra `DONE ON 5000`, `HEARTBEAT` kiểm tra `DONE CAPTURING`, `STATUS` kiểm tra 10 token, các lệnh còn lại so khớp nguyên văn; bất kỳ phản hồi sai lệch/thừa token nào sau ON đều kích hoạt `abort_emergency` tắt laser và kết luận FAIL).
- **R03/R05 (Dừng an toàn & Bảo vệ trước lần ghi ON):** Ghi nhận khả năng PA8 bật trước khi `send_line` gửi lệnh ON. Nếu có bất kỳ lỗi I/O (`OSError`, `SerialException`), lỗi phản hồi (thiếu, sai định dạng/checksum/seq) hoặc dừng sớm (`Ctrl+C`) sau khi đã gửi hoặc chuẩn bị gửi `LASER ON`, công cụ chủ động gọi `abort_emergency` gửi `LASER OFF` với seq mới và kiểm tra lại `STATUS` để xác nhận `laser=0` (PA8 thấp) trước khi đóng cổng. Giữ nguyên mã lỗi gốc của lần thử; nếu không xác nhận được qua giao thức (hoặc cổng mất hẳn), in cảnh báo nguy hiểm yêu cầu người vận hành nhìn VOM 0.00V và chờ timeout độc lập 3/5 s trên bo.
- **R04/R06/R07/L19/R09 (Kiểm tra liên động chặt chẽ, kiểm soát nội dung Q3 & Giữ lỗi đầu tiên):** Các phép thử liên động (`--test-door`, `--test-estop`, `--test-interlock`) và chuỗi P1 (`--p1`) kiểm tra nghiêm ngặt seq, checksum và cấu trúc nội dung của mọi phản hồi giám sát (HEARTBEAT, ON gia hạn, STATUS, OFF, STOP, HOME). Kiểm tra đầy đủ schema và miền giá trị theo Q3: `HEARTBEAT` phải là `DONE <state>` (2 token, state thuộc 8 trạng thái chuẩn) hoặc `ERROR <err_code>`; `LASER ON` phải là `DONE ON <remaining_ms>` (3 token, remaining_ms là số từ 0 đến 5000) hoặc `ERROR <err_code>`. **R09:** Parser `parse_status_tokens` dùng chung kiểm soát nghiêm ngặt `0 <= remaining_ms <= 5000` và `last_err` phải thuộc `NONE ∪ VALID_ERROR_CODES` (chấp nhận các mã lỗi cũ hợp lệ như `LASER_TIMEOUT`, `WDG_RESET` theo Q3). Bất kỳ phản hồi bị mất, sai seq, sai checksum, chứa chuỗi rác (kể cả rác chứa chữ ERROR hay thừa token như `DONE ERROR EXTRA`, `DONE ON 5000 X`), thiếu remaining_ms hoặc remaining_ms ngoài miền 0..5000 (như `5001`, `999999`), mã lỗi không xác định (`NO_SUCH_ERROR`), hoặc STATUS có trạng thái bất thường (`remaining_ms != 0`, `last_err` khác mã lỗi mục tiêu, `laser=1`) đều lập tức dừng phép thử, kích hoạt dừng khẩn cấp và trả về mã lỗi khác 0, không in `PHEP THU DAT` hay `DEU DAT`; tuyệt đối không bỏ qua lỗi để chờ phản hồi sau. Phép thử chỉ công nhận trip sau khi nhận phản hồi `STATUS` hợp lệ (`state=ERROR`, `laser=0`, đúng mã lỗi `DOOR_OPEN` hoặc `ESTOP`, `remaining_ms=0`; bit door/estop phản ánh mức hiện tại theo N3/N8). Kết luận `PHEP THU DAT` chỉ khi người vận hành xác nhận được điện áp PA8 đã về 0.00V (hỏi xác nhận tương tác console, tự động nhận diện trên bo giả lập `SIM`/`FAKE`, hoặc qua cờ `--confirm-vom-0v` trong script tự động).
- Lệnh chạy thử P1 trên bo không tải:
  ```bash
  .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --p1
  ```
- Lệnh chạy thử ngắt liên động cửa an toàn / estop:
  ```bash
  .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --test-door
  .venv/Scripts/python.exe pc/nucleo_ping.py --port COM3 --test-estop
  ```
- Quy trình đo đạc và thử nghiệm chi tiết trên bo: `docs/procedures/quy-trinh-c4-nucleo-khong-tai.md`.
- Chạy selftest (gồm hồi quy PING, P1, parser 10 token, R03/R05 cứu hộ, R04/R06 kiểm soát toàn vẹn liên động, R07/L19/R09 kiểm tra cấu trúc phản hồi và VOM):
  ```bash
  .venv/Scripts/python.exe pc/nucleo_ping.py --selftest
  ```

## sharpness.py

Đo độ nét và ước lượng trường nhìn cho các phiên ảnh của `capture_session.py`,
phục vụ chỉ tiêu MT "Quang học" tuần 1: chọn khoảng cách nhìn rõ vật 50–100 mm
trong ba mức 200, 250, 350 mm. Cần NumPy (thêm vào `.venv` ngày 16/09 tối vì
Pillow không lọc được ảnh có giá trị âm).

Mỗi ảnh chuyển sang thang xám, cắt ROI, tính: `lap_var` (phương sai Laplacian
4 lân cận), `grad_energy` (trung bình Gx²+Gy² Sobel), `mean`/`std` độ sáng,
`sat_frac` (tỷ lệ điểm ≥ 250), `dark_frac` (≤ 5). Hai số đầu càng cao càng
nét, nhưng phụ thuộc nội dung ảnh và tương phản: chỉ so tương đối giữa các
phiên chụp cùng vật, cùng ánh sáng, và ROI phải trùm vật hoặc vạch thước —
ROI rơi vào tường trơn cho `lap_var` ≈ 3 dù ống kính có nét hay không (đã
thấy trên 110 ảnh ngày 16/09, `docs/logs/sharpness_20260916_thu_110anh/`).

**Vòng 5 (L06, cổng O5–O7 `docs/SPEC.md` mục 10.2):** thêm bộ số RGB trên
cùng ROI, độc lập với các số thang xám trên — `mean_r`/`mean_g`/`mean_b`
(độ sáng trung bình từng kênh), `channel_spread_pct` = `100 ×
(max(R,G,B) − min(R,G,B)) / trung bình ba kênh` (anh xám thật R=G=B cho
0, ám màu cho số dương lớn), `dark_frac_rgb`/`sat_frac_rgb` (tỷ lệ pixel
có ÍT NHẤT MỘT kênh ≤ 5 hoặc ≥ 250). Có trong `per_image.csv`,
`summary.json` (`*_median`/`*_max` như các số cũ) và dòng "mau RGB ROI"
của `summary.txt`; không đổi định nghĩa hay cột của bốn số thang xám cũ.

Trường nhìn: người dùng đọc toạ độ pixel hai điểm trên thước trong ảnh gốc
(mở bằng Paint, toạ độ hiện ở góc dưới trái) và khoảng cách thật giữa chúng;
script tính mm/pixel và bề rộng, bề cao trường nhìn tại mặt thước, giả định
pixel vuông và thước vuông góc với trục quang.

Chạy từ thư mục gốc repo, Git Bash:

```
.venv/Scripts/python.exe pc/sharpness.py --selftest
.venv/Scripts/python.exe pc/sharpness.py capture_20260916_154847 --roi center
.venv/Scripts/python.exe pc/sharpness.py capture_A capture_B capture_C --roi 160,120,320,240 --ruler capture_A=120,300,520,300,100 --ruler capture_B=... --ruler capture_C=... --out docs/logs --annotate
```

Tên phiên không có đường dẫn được tìm trong `data/raw/`. `--roi` nhận
`[ID=]X,Y,W,H` theo pixel hoặc `[ID=]center` (nửa giữa khung); có `ID=` thì
chỉ áp cho phiên đó, lặp lại cho từng phiên vì vật ở gần hiện to hơn ở xa;
không `ID=` thì áp cho mọi phiên. `--ruler` dạng `[ID=]x1,y1,x2,y2,mm`,
lặp lại cho từng phiên vì mỗi khoảng cách một thước.
`--out docs/logs` ghi thư mục `sharpness_YYYYMMDD_HHMMSS/` (đổi tên bằng
`--report-id`), không ghi đè, gồm `per_image.csv`, `summary.json`,
`summary.txt`, và với `--annotate` một ảnh đại diện mỗi phiên (ảnh có
`lap_var` gần trung vị) vẽ ROI xanh và đoạn thước đỏ, lưu JPEG q92 riêng,
không sửa ảnh gốc. Ảnh `decode_ok=False` trong `frames.csv` bị bỏ và đếm.

Selftest không cần ảnh thật: ảnh phẳng cho 0, mờ dần Gaussian 0/1/2/4
giảm đơn điệu, sọc, qua nén JPEG, parse ROI/thước kể cả tham số sai,
phiên giả 3 ảnh có một ảnh hỏng, ghi hồ sơ đúng LF, từ chối ghi đè, cộng
bộ RGB Vòng 5 (ảnh xám/ám lục/đen/trắng); số mục đổi theo từng vòng sửa,
xem `--selftest` in ra "SELFTEST: PASS". Kết quả 16/09 tại
`docs/logs/pc-sharpness-selftest-2026-09-16.log` (chưa chạy lại log mới
cho Vòng 5, xem `handoff/2026-09-21_c2-camera-profile/02_BUILD.md`).

## ruler_ticks.py

Đo khách quan trên ảnh khảo sát quang học, bổ sung cho `sharpness.py`, viết
17/09 khi thấy vạch mm không đọc được bằng tay trên ảnh mờ:

1. **Chu kỳ vạch cm của thước dựng** (px/cm): hồ sơ cường độ theo hàng
   trong một dải cột chứa vạch (`--band X0,X1,Y0,Y1`, phải nằm trên nền
   tường, không đè lên vật), trừ xu hướng, tự tương quan lấy chu kỳ trong
   khoảng `--lag LO,HI` (thu hẹp khi tín hiệu yếu để không bắt bội 2×), rồi
   tìm cực tiểu và khớp thẳng `y = a + b·k`. Cho mm/pixel, trường nhìn và
   sinh sẵn chuỗi `--ruler` cho `sharpness.py` từ hai đầu đường khớp.
2. **Bề rộng mép** (`--edge X,Y0,Y1`): trên cạnh thẳng đứng của vật tối
   trên nền sáng, bề rộng vùng chuyển 10–90 % từng hàng, trung vị; tính px
   và quy ra mm ở mặt vật. Không lợi cho vật ở xa như `lap_var`, nên dùng
   để so độ nét vật lý giữa các khoảng cách.

```
.venv/Scripts/python.exe pc/ruler_ticks.py --selftest
.venv/Scripts/python.exe pc/ruler_ticks.py capture_qh_250mm --band 322,340,4,188 --lag 18,60 --edge 280,205,340 --json docs/logs/ruler-ticks-2026-09-17-qh250.json
```

Selftest 13 mục: thước tổng hợp chu kỳ 37,5 px, bắt bội 2× khi `--lag` rộng,
mép sắc < 1 px và mép mờ 5 px cho 3–5 px, phiên giả trên đĩa. Kết quả 17/09
tại `docs/logs/pc-ruler-ticks-selftest-2026-09-17.log`; ba phiên thật tại
`docs/logs/ruler-ticks-2026-09-17-qh*.json` và
`docs/tests/2026-09-17_s3_quang_hoc.md`.

Sửa 2026-09-20 (review R09): `--band`, `--lag`, `--edge` được kiểm theo kích
thước ảnh thật trước khi đo (thứ tự X0<X1, Y0<Y1, nằm trong khung, LO<HI,
không âm) → lỗi `Loi: --edge: ...` rc 3 thay vì `IndexError`/NaN; phiên
không có `img_NNNN.jpg` bị từ chối thay vì in 640×480 mặc định; bỏ qua
`img_NNNN_tryK.jpg` (payload lần thử của capture). `sharpness.py` cùng ngày:
`--ruler` phải là số hữu hạn, không âm, hai đầu nằm trong ảnh; phiên rỗng →
lỗi rõ. Selftest 49 (sharpness) và 20 (ruler_ticks) mục, log `docs/logs/pc-optics-selftest-2026-09-20.log`.
Chạy lại ba phiên thật 17/09 sau khi sửa: số đo khớp JSON đã lưu.

## mock_camera.py

Server giả lập `/status`, `/control`, `/capture` để thử `capture_session.py`
và `camera_profile.py` khi không có bo. Không thay thế bo thật. Tuỳ chọn
`--reset-at N` giả reset ở khung N để thử bộ phát hiện. Kết quả thử ngày
2026-09-16 tại `docs/logs/pc-capture-mock-2026-09-16.log`.

Tiêm lỗi (thêm 2026-09-20): `--fail-frames 2,5` (khung 2 và 5 trả 503 một
lần), `--drop-ts-frames 3` (khung 3 không có `X-Timestamp`),
`--lowercase-headers`, `--status-mode ok|invalid|list|http503`,
`--status-fail-after N`.

Tiêm lỗi cho hồ sơ camera (thêm 2026-09-21, xem `camera_profile.py`):
`--ignore-controls VAR[,VAR...]` (`/control` trả 200 OK nhưng không đổi
giá trị, giả lập firmware âm thầm không áp), `--fail-controls
VAR[,VAR...]` (`/control` trả 500 cho biến này dù firmware có hỗ trợ),
`--drift-registers 0xNNNN[,...]` cùng `--drift-after N` (từ lần
`/capture` thứ N, các thanh ghi này đổi giá trị, giả lập AEC/AGC/AWB tự
chỉnh lại giữa phiên), `--status-drop-fields NAME[,...]` (bỏ trường khỏi
JSON `/status`). Gửi `/control?var=sharpness&...` (biến firmware thật
không hỗ trợ) luôn trả 500, giống bo thật.

Thêm Vòng 3 (xử lý G03/G04 của Tester): `--control-drift-fields
VAR=VAL[,...]` cùng `--control-drift-after N` (từ lần `/capture` thứ N,
các biến này đổi thẳng sang giá trị mới trong `/status`, giả lập control
tự trôi mà KHÔNG kèm thanh ghi đổi — khác `--drift-registers`, dùng được
cùng lúc hoặc riêng); `GET /_counts` trả JSON đếm request theo loại
(`{"control": N, "capture": N, "status": N}`) để đối chiếu cơ học "dừng
ngay khi lỗi" hoặc "0 request" thay vì đoán qua thời gian chạy.

Thêm Vòng 5 (xử lý L05–L07): mặc định khởi động của mock nay khớp firmware
thật cho OV3660 — `vflip=1`, `brightness=1`, `saturation=-2` (trước là cả
ba bằng 0); bảy thanh ghi mặc định (`0x3500`, `0x350a`, `0x3400`,
`0x3404`, `0x3402`, `0x3406`, `0x3503`). `--registers 0xNNNN=V[,...]` ghi
đè giá trị thanh ghi ban đầu (vd `0x3500=8000,0x350a=32`), dùng để kiểm
công thức ứng viên của `camera_profile.py --probe`. `--status-fail-at-count
N` làm `/status` trả 503 đúng lần thứ N (đếm theo `/_counts.status`,
KHÔNG phụ thuộc số `/capture` như `--status-fail-after`) — mô phỏng lỗi
giữa chừng một phiên `--probe` nhiều mẫu.

Thêm Vòng 6 (xử lý L08/L10): `/control?var=aec_value` gửi trên
`AEC_VALUE_HARD_CAP` (783) chỉ echo lại 783 trong `/status`, giả lập
`set_aec_value()` kẹp cứng ở trần thiết bị đã đo; `/control?var=wb_mode`
gửi `1..4` đổi thẳng `0x3400`/`0x3402`/`0x3404` và đặt `0x3406=1` theo
`WB_MODE_REGISTERS` (bảng driver OV3660 chuẩn), không chỉ đổi trường
`status` như trước.

Thêm Vòng 7 (xử lý L11): mock khởi động ở WB tự động (`wb_mode=0`,
`0x3406=0`); `/control?var=wb_mode&val=0` chỉ xoá bit thủ công
(`0x3406=0`, giữ nguyên ba gain), `1..4` áp bảng như Vòng 6;
`/control?var=awb_gain` áp lại preset của `wb_mode` hiện tại, giống
`set_awb_gain_dsp()` của driver. `--wb-registers-stuck` làm `wb_mode`/
`awb_gain` trả 200 và echo trong `/status` nhưng KHÔNG đổi bốn thanh ghi
WB — giả lập "HTTP OK mà không áp". Mock không mô phỏng màu quang học.

Bộ chạy 21 tình huống đầu-cuối không cần bo:
`.venv/Scripts/python.exe pc/e2e_capture_mock.py` (mock nhúng trong tiến trình,
thư mục tạm tự dọn) — 11 tình huống `capture_session.py` gốc (2026-09-20,
`docs/logs/pc-capture-mock-2026-09-20.log`) cộng 10 tình huống hồ sơ
camera: sáu tình huống 21/09 (`profile_baseline`, `profile_register_drift`,
`profile_control_rejected`, `profile_status_missing_field`,
`profile_invalid_schema`, `profile_and_framesize_conflict`) và bốn tình
huống Vòng 3 kiểm trực tiếp G02–G04 (`profile_register_mismatch_at_start_G02`,
`profile_control_drift_at_end_G03`, `profile_locked_control_rejected_G04`,
`profile_first_control_fails_fast_G04`); kết quả ghi trong
`handoff/2026-09-21_c2-camera-profile/02_BUILD.md`, chưa có log riêng
trong `docs/logs/`.

## line_extract.py

Thêm 2026-09-28 (C3, bước `[Q6]`). Trích tâm vạch laser từ cặp ảnh JPEG OFF/ON
bằng phương pháp trọng tâm cường độ theo từng hàng trong vùng quan tâm (ROI),
không truy cập thiết bị hay điều khiển camera/laser. Cơ sở: `docs/SPEC.md`
mục 14.1, 16.1 và `docs/design/SCAN_SESSION.md` mục 2.

Nguyên lý:
- Chuyển kênh đỏ của hai ảnh sang kiểu có dấu `int16`, trừ `ON - OFF`, chặn
  âm về `0`. Cặp ảnh đầu vào bắt buộc cùng kích thước và cùng chế độ màu
  (`mode`, ví dụ cả hai đều là `RGB` hoặc cùng là `L`); từ chối nếu khác chế độ.
- Trên từng hàng trong ROI nửa mở `[x0, x1) × [y0, y1)` (tọa độ gốc 0, tâm pixel chỉ số `i` tại `i.0`):
  tìm các cụm pixel liên tục có hiệu đỏ đạt ngưỡng `--min-diff`.
- Tính bề rộng và trọng tâm phân số pixel cho cụm laser. Nếu phát hiện bão hoà
  (điểm ảnh ON đạt `--sat-thresh`), quá rộng (`width > --max-width`), chạm biên ROI
  (`edge` — vạch bị cắt gây sai số hệ thống), không có tín hiệu, tín hiệu yếu hoặc
  có nhiều nhánh ngang sức không phân biệt được / đốm sáng đơn lẻ nhảy xa
  (`ambiguous`), hàng đó bị gắn cờ không hợp lệ (`valid=false`) kèm lý do cụ thể;
  tuyệt đối không lấy trung bình hai nhánh và không nội suy hàng lỗi.
- Xuat CSV theo quy uoc `row_y,center_x_px,valid,reason,width_px` (moi hang ROI
  dung mot dong; ma `reason in {ok, no_signal, weak, saturated, wide, ambiguous, edge}`)
  va xuat anh PNG chu thich rieng tren ban sao; khong sua doi hay
  ghi de anh goc; tu choi chay neu duong dan dau ra trung dau vao, hai dau ra
  trung nhau, hoac tep dau ra da ton tai (khong co tuy chon ghi de, tuan thu
  chat che nguyen tac bao toan du lieu). Neu xuat ca CSV va PNG chu thich, bat buoc
  hai tep phai nam trong cung mot thu muc cha.
- Hop dong sieu du lieu `params.json` (Quy tac mot thu muc / mot cau hinh theo Phuong an a):
  + Moi thu muc dau ra (`run_id` theo `docs/design/SCAN_SESSION.md`) tuong ung dung mot bo cau hinh xu ly co dinh gom 6 truong:
    `roi`, `min_diff`, `max_width`, `sat_thresh`, `img_width`, `img_height` (lay gia tri thuc dung sau khi giai ma anh va giai ROI mac dinh).
  + Neu `params.json` chua co trong thu muc dau ra: tu dong tao tep chua dung 6 truong tren truoc khi ghi bat ky dau ra CSV/PNG nao.
  + Neu `params.json` da co va khop hoan toan ca 6 truong: tai su dung nguyen byte tep da co (khong ghi de, khong sua dinh dang). Chap nhan tep C3 cu co them mot phan/toan bo 3 khoa thong ke cu (`total_rows`, `ok_count`, `valid_pct`), bo qua chung khi so khop va giu nguyen tep.
  + Neu `params.json` da co nhung lech bat ky truong nao trong 6 truong cau hinh: tu choi truoc khi ghi dau ra voi loi `params_mismatch` (neu ro truong lech, khong tao CSV/PNG, khong sua `params.json` cu); doi tham so bat buoc phai dung thu muc chay moi.
  + Neu `params.json` la thu muc, JSON hong, khong phai object, thieu/sai kieu truong, ngoai mien hoac chua khoa la (vi du tep cua cong cu khac chi co `scan_id`/`commit`): tu choi voi loi `params_invalid`, khong tao dau ra.
  + Vong doi metadata params.json (Vong 10, D037): cau hinh chung gan voi thu muc chay (run_id), khong thuoc ve rieng luot tao ra no; khong tu xoa hoac ghi de params.json trong bat ky duong loi nao (ke ca write_params_json hay khoi loi ngoai process_pair). Metadata hoan chinh giu nguyen byte ngay ca khi luot tao bi loi CSV/PNG o buoc sau, cho phep luot sau cung cau hinh tai su dung, khac cau hinh bi chan voi params_mismatch. Neu loi xay ra ngay khi dang ghi metadata khien JSON bi ghi do/hong, tep ghi do duoc giu nguyen tren dia (khong tu xoa, khong sua lai), cac luot sau vao thu muc nay bi tu choi voi params_invalid va bat buoc phai dung thu muc chay moi.
  + Khi gap loi ghi hoac xu ly giua chung: chi don dep cac tep dau ra CSV/PNG do chinh lan goi hien tai tao ra (csv_created_by_us, ann_created_by_us); khong hua hen xoa moi tep metadata khi loi; metadata chung, ket qua hop le cua luot khac va anh tho duoc bao toan tuyet doi.
- Cac nguong la tham so cong khai khi chay, khong duoc tu y dien giai mac dinh
  thanh ket luan nghiem thu Q9 tren anh that (viec danh gia Q9 tren anh that
  thuoc C5/C7).

Cac doi so CLI chinh:
- `--off <duong_dan>`: duong dan anh JPEG khi laser tat (bat buoc tru khi `--selftest`).
- `--on <duong_dan>`: duong dan anh JPEG khi laser bat (bat buoc tru khi `--selftest`).
- `--roi <x0,y0,x1,y1>`: vung quan tam nua mo `[x0, x1) x [y0, y1)` theo toa do goc 0
  (vi du: `--roi 100,50,540,430`). Mac dinh la toan bo anh `0,0,W,H`.
- `--min-diff <so>`: nguong hieu kenh do toi thieu de nhan dien pixel laser (huu han, `0 < min_diff <= 255`, mac dinh 20.0).
- `--max-width <so>`: be rong cum toi da tinh bang pixel (nguyen duong `> 0`, mac dinh 30).
- `--sat-thresh <so>`: nguong gia tri bao hoa (huu han, `0 < sat_thresh <= 255`, phai lon hon `min_diff` de tranh to hop nguong vo ly, mac dinh 250.0).
- `--csv <duong_dan>`: duong dan tep CSV luu toa do tam tung hang (khong trung dau vao hay anh chu thich, khong ghi de neu da co; ap dung hop dong `params.json` cung thu muc).
- `--annotate <duong_dan>`: duong dan tep PNG chu thich (ve ROI va danh dau tam/loi, khong trung dau vao hay CSV, phai cung thu muc cha voi CSV neu co ca hai, khong ghi de neu da co; ap dung hop dong `params.json` cung thu muc).
- `--selftest`: chay bo kiem tra tu dong doc lap vat tu (ma tran be rong 1/2/4/6 px,
  >=30 lan lap/cau hinh, do sai so tam va do lech chuan mau n-1; kiem tra tinh toan ven
  hash anh goc; kiem tra bat loi dau vao va tin hieu mo phong, bao gom kiem tra hop dong
  metadata params.json khoa tham so mot thu muc/mot cau hinh L09, bao toan metadata tai su dung,
  vach cham bien ROI, dom sang don le nhay xa va cac cap nguong).

Cach chay tu thu muc goc repo (Git Bash):
```
.venv/Scripts/python.exe pc/line_extract.py --selftest
.venv/Scripts/python.exe pc/line_extract.py --off data/raw/session/img_0000_off.jpg --on data/raw/session/img_0000_on.jpg --roi 100,50,540,430 --csv data/processed/session/run_01/centers_0000.csv --annotate data/processed/session/run_01/annotated_0000.png
```

## fresh_capture_probe.py

Thêm 2026-10-03 (D043, đầu việc C5a chặng Q6). Công cụ thăm dò và kiểm thử độc lập endpoint `/capture_fresh` trên ESP32-S3 hoặc trên mock.

Đặc điểm và kiểm tra bắt buộc:
- Bắt buộc đủ 5 headers chẩn đoán: `X-Frame-Id`, `X-Boot-Id`, `X-Timestamp`, `X-Request-Timestamp`, `X-Discarded-Frames`.
- Kiểm tra định dạng micro-giây đúng 6 chữ số (`%06d`) và quan hệ thời gian nghiêm ngặt $t_{\text{frame}} > t_{\text{req}}$ (phân tích số nguyên).
- Kiểm tra tính đơn điệu của `X-Frame-Id` và phát hiện khởi động lại bo qua `X-Boot-Id` (token 128-bit hex thường).
- Kiểm tra tính toàn vẹn JPEG (SOI `0xFFD8`, EOI `0xFFD9`, kích thước nhị phân hợp lệ).
- Cơ chế bảo vệ và giới hạn an toàn (R11 & R12): socket inactivity timeout 5.0 s (co dần theo thời gian còn lại), deadline tổng từng request 10.0 s bảo vệ bởi watchdog Timer và clock monotonic, thu hồi Timer và socket an toàn trong cùng tiến trình (không rò rỉ luồng/worker). Chẩn đoán phân biệt rõ hai lớp lỗi: `TIMEOUT_SOCKET` (inactivity quá 5 s trước hạn tổng) và `TIMEOUT_TOTAL_DEADLINE` (vượt hạn 10 s).
- Tích hợp `--selftest` tự khởi chạy mock server nội bộ kiểm thử trọn vẹn 10 kịch bản: 20 capture liên tiếp, stale frames, reboot bo, thiếu header, các lỗi HTTP 503 (`CAMERA_BUSY_STREAM`, `CAMERA_BUSY_CAPTURE`, `CAMERA_NO_BUFFER`, `CAMERA_TIMEOUT_NO_FRESH_FRAME`), lỗi HTTP 500 (`CAMERA_UNSUPPORTED_FORMAT`, `FRAME_ID_OVERFLOW`), và ảnh JPEG cắt cụt.

Cách chạy:
```bash
# Chay selftest noi bo khong can bo:
python pc/fresh_capture_probe.py --selftest

# Tham do bo that ESP32-S3 (20 khung lien tiep):
python pc/fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 20 --interval 0.2
```
Xem quy trình vận hành chi tiết tại `docs/procedures/quy-trinh-c5a-fresh-capture.md`.
