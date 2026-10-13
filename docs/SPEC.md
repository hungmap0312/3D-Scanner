# Đặc tả dự án — máy quét 3D để bàn dùng laser vạch và bàn xoay tự động

Bản tổng hợp: 2026-09-19. Tên tiếng Anh: *Design and Implementation of a
Desktop Laser Line 3D Scanner with an Automated Turntable*. Học phần: Đồ án
phần mềm nhúng kết hợp Đồ án thiết bị nhúng, chuyên ngành Hệ thống Nhúng và
IoT.

**Cập nhật phạm vi được người dùng chốt 08/10/2026 — D048.** Kế hoạch
hiện hành là `docs/ROADMAP.md`: G → A/B/C/D/E → H1–H4 → V/F, hồ sơ R
xuyên suốt. Phần tuần 2, giao thức hiện hành và thông số phần
cứng giữ nguyên. Những nhãn `[MT §n]`, `[RM Tn]` dẫn về tài liệu 15/09
là dấu vết nguồn lịch sử; nội dung đã được D048 thay thế áp dụng theo bản
hiện hành này và hai Word nguồn được đồng bộ. Bảng cơ khí §11 vẫn giữ
các phép tính danh nghĩa, nhưng chỉ 200 góc là chế độ nghiệm thu; các
nhãn tuần trong §11/12/19 và hồ sơ phần cứng đối chiếu ROADMAP §8.
Đây là thay đổi yêu cầu được duyệt trước nghiệm thu, không công nhận
bất kỳ phép thử mới nào đã đạt.

## Cách dùng tệp này

Tệp này gom toàn bộ yêu cầu, ràng buộc và chỉ tiêu của dự án từ ba tài liệu
gốc trong `docs/reference/` thành một chỗ để đối chiếu nhanh, kèm số mục
của bản gốc. **D048 và kế hoạch chốt 08/10/2026 có hiệu lực cho phần thay đổi phạm vi.**
SPEC, ROADMAP và hai DOCX đã đồng bộ phải thống nhất; bản 15/09 trong lịch
sử không ghi đè yêu cầu mới. Nếu thấy lệch, báo mâu thuẫn để xử lý. Không dùng tệp này thay sơ đồ
đấu dây, bản vẽ hay tài liệu nhà sản xuất.

| Nguồn | Ngày | Ký hiệu trích dẫn | Vai trò |
| --- | --- | --- | --- |
| `Mo_ta_chi_tiet_may_quet_3D_laser_STM32_ESP32S3.docx` | 15/09/2026 | `[MT §n]` | Tài liệu chủ, 17 mục |
| `Roadmap_14_tuan_may_quet_3D_STM32_ESP32S3.docx` | Cơ sở 15/09, cập nhật 08/10/2026 | `[RM Tn]`, `[RM <tên mục>]` là nhãn nguồn cũ | Kế hoạch theo nhánh/hội tụ D048, quy cách đo, nghiệm thu; tuần 1–2 giữ nguyên |
| `BOM_may_quet_3D_ESP32_CAM_ESP32_S3.xlsx` | 14/09/2026 | `[BOM mã]` | Kiến trúc cũ (S3-CAM tự điều khiển, OV2640); chỉ dùng danh mục và đơn giá — D005 |

Thứ tự nguồn lịch sử 15/09 là mô tả > roadmap > BOM (D005); phạm vi được
chốt 08/10 theo D048 thay các yêu cầu tương ứng như ghi ở đầu tệp.
Văn bản được trích bằng script đọc `word/document.xml` và `xl/worksheets/`
(chỉ đọc); ba công thức ở mục 14 trích từ đối tượng toán học của bản gốc.

Bản mô tả tự nêu: các giá trị chỉ tiêu là **mục tiêu kỹ thuật đề xuất, cần
chốt sau thử nghiệm camera và hiệu chuẩn ban đầu**; báo cáo phải ghi kết quả
thực đo và điều kiện đo, kể cả chỉ tiêu chưa đạt, không đổi tên mục tiêu
thành thông số đã chứng nhận `[MT §12]`. Roadmap nêu: các ngưỡng bổ sung
như 0,5 px tuần 2 hay 0,7 px tuần 3 là ngưỡng theo dõi nội bộ; mục tiêu sai số 2 mm giữ từ bản mô tả; D048 chuyển mục tiêu thời gian
15 phút sang lượt 200 góc, phải đo lại theo chế độ mới; **không tự điều chỉnh ngưỡng sau khi
đo để chuyển chưa đạt thành đạt** `[RM Cách đọc chỉ tiêu]`.

Trạng thái thực hiện không ghi ở đây, trừ mục 24. Xem `STATUS.md`,
`DECISIONS.md`, `docs/ROADMAP.md`.

## 0. Cách đọc chỉ tiêu `[RM Cách đọc chỉ tiêu]`

| Ký hiệu | Ý nghĩa | Cách xử lý |
| --- | --- | --- |
| **B** | Bắt buộc | Điều kiện để chức năng hoặc dữ liệu được coi là hợp lệ. Chưa đạt thì chưa dùng kết quả cho phần phụ thuộc |
| **MT** | Mục tiêu chất lượng | Ngưỡng cần đo kiểm. Chưa đạt: báo số thực đo và phân tích nguyên nhân; có thể làm phần độc lập nhưng chưa ghi nhận đạt |
| **M** | Mở rộng | Chỉ làm khi phần bắt buộc và thời gian còn lại cho phép; tách khỏi kết quả cơ sở |

## 1. Đề tài và mục tiêu `[MT Tóm tắt, §1]`

Thiết kế, chế tạo và kiểm chứng một hệ thống nhúng phối hợp cơ cấu chuyển
động với thu nhận ảnh, tạo dữ liệu 3D có thang đo thực và **có thể truy xuất
lại quá trình tạo ra dữ liệu đó**.

Vật đặt trên bàn xoay trong hộp che sáng. Tại mỗi góc, hệ thống dừng, chụp
một ảnh nền khi laser tắt và một ảnh khi laser bật. Từ vị trí vạch laser
trong ảnh và tham số hiệu chuẩn, phần mềm tính toạ độ 3D của các điểm trên
bề mặt và ghép thành đám mây điểm. Người dùng xem kết quả, đo một số kích
thước tham khảo và xuất dữ liệu.

| Mục tiêu cụ thể | Kết quả cần chứng minh |
| --- | --- |
| Điều khiển thiết bị | Bàn xoay tìm được vị trí gốc, di chuyển theo số xung; laser bật tắt đúng chu trình |
| Thu nhận ảnh | Mỗi góc có một cặp ảnh hợp lệ; tham số chụp ổn định và có mã nhận dạng ảnh |
| Hiệu chuẩn hình học | Có nội tham số camera, mặt phẳng laser và đường trục quay trong cùng hệ toạ độ |
| Tái tạo hình dạng | Tính được toạ độ 3D, ghép các góc, lọc nhiễu, xuất đám mây điểm |
| Sản phẩm sử dụng được | GUI tối thiểu: kết nối, chọn hồ sơ hợp lệ, quét/dừng, tiến độ/lỗi, mở phiên, xử lý lại và xuất PLY; xem 3D bằng công cụ độc lập |
| Đánh giá định lượng | Sai số, độ lặp lại, thời gian và ổn định trên một cấu hình; so sánh thuật toán/chế độ chuyển tốt nghiệp |

Giá trị ứng dụng: số hoá đồ thủ công, mô hình trang trí, vật mẫu học tập;
dữ liệu tham khảo khi dựng lại CAD. **Trong phạm vi đồ án, thiết bị chưa
được xem là máy đo kiểm đáp ứng dung sai công nghiệp.**

## 2. Phạm vi hiện hành — D048

### 2.1 Bắt buộc

- Một camera, một laser vạch, một trục quay; vật đục, nhám, hình dạng tương
  đối đơn giản, kích thước điển hình 50–100 mm.
- Một cấu hình camera chính kế thừa kết quả tuần 2; 200 góc/vòng,
  400 ảnh OFF/ON được chọn hợp lệ; giữ riêng payload thử lại.
- Một lượt thu bề mặt quan sát được; đáy tỳ mâm và hốc bị che có thể thiếu.
- Hiệu chuẩn đủ camera, laser và trục. PLY đơn vị mm kèm ảnh gốc, cấu hình,
  hồ sơ hiệu chuẩn, log và phiên bản mã; xử lý lại được khi không nối bo.
- GUI tối thiểu; công cụ độc lập dùng xem PLY. Giữ PCB hoạt động, nguồn,
  cơ khí và HOME. Yêu cầu an toàn/liên động đã bỏ (D050, §9).
- Ba mẫu đối chứng, một mẫu năm phiên lặp và ba lượt 200 góc liên tiếp;
  quy cách và ngưỡng tại §16–17.

### 2.2 Chuyển sang giai đoạn tốt nghiệp

Dựng lưới/OBJ/STL, in 3D, trình xem/chỉnh sửa 3D tích hợp, so sánh
COG/Gauss, 200/400 góc và nhiều độ phân giải/JPEG sau tuần 2, xử lý ảnh
trên thiết bị, quét nhiều tư thế, laser thứ hai, texture.

Không xoá mã/kết quả đã có. **Tuần 2 giữ nguyên**, gồm khảo sát C2b,
100 cặp OFF/ON và phép thử trích vạch C7 cùng cổng D016.

### 2.3 Ngoài yêu cầu cơ sở

Vật trong suốt, bề mặt gương, vật lớn, quét màu và đo dung sai công nghiệp.

### 2.4 Khi chậm tiến độ

Theo phụ thuộc ROADMAP; làm khối đã đủ đầu vào, dùng phần dự phòng cho
lỗi và kiểm lại. Không bỏ hiệu chuẩn, PCB hoặc kiểm chứng để
đạt mốc lịch. B chưa đạt chặn phần phụ thuộc; MT chưa đạt ghi số/nguyên
nhân và chỉ tiếp tục phần độc lập, giữ cổng riêng tuần 2/D016.

## 3. Sản phẩm bàn giao `[MT §17, RM Bảng nghiệm thu]`

| Nhóm | Nội dung bàn giao |
| --- | --- |
| 1. Thiết bị thực tế | Máy quét có bàn xoay, camera, laser, hộp che, nguồn và **bo mở rộng tự thiết kế hoạt động**; ảnh lắp ráp |
| 2. Hồ sơ phần cứng | Schematic, PCB, Gerber, BOM cập nhật theo mua thực tế, bản vẽ cơ khí, bản vẽ đấu nối, biên bản kiểm tra mạch |
| 3. Phần mềm nhúng | Mã nguồn Nucleo và ESP32-S3; cấu hình build, giao thức, sơ đồ trạng thái, hướng dẫn nạp |
| 4. Ứng dụng PC | Source, môi trường chạy, README; GUI tối thiểu, công cụ hiệu chuẩn, thu nhận, xử lý lại, xuất PLY; xem 3D độc lập |
| 5. Dữ liệu và kiểm chứng | Ảnh gốc, cấu hình, hiệu chuẩn, point cloud PLY, log và kết quả các phép thử |
| 6. Tài liệu học thuật | Phân tích thiết kế, mô hình dữ liệu, báo cáo thực nghiệm, hướng dẫn dùng, slide, video demo, hướng phát triển tốt nghiệp |

Phần **thiết bị nhúng** thể hiện qua nguồn, điều khiển động cơ, đóng ngắt
laser, PCB và cơ khí. Phần **phần mềm nhúng** thể hiện qua
firmware, lập lịch, trạng thái, giao tiếp, xử lý lỗi và tích hợp ứng dụng.
Mạch thử trên breadboard không thay được PCB: "chưa có PCB chạy thực tế là
phần còn thiếu của học phần thiết bị nhúng" `[RM T13]`, D003.

## 4. Kiến trúc hệ thống `[MT §2]`

### 4.1 Nguyên lý

Laser vạch tạo một mặt phẳng ánh sáng. Khi mặt phẳng cắt bề mặt vật, camera
thấy một đường sáng thay đổi theo hình dạng. Một điểm ảnh cho hướng tia
nhìn; giao của tia đó với mặt phẳng laser đã hiệu chuẩn là vị trí 3D của
điểm trên vật. Bàn xoay lần lượt đưa các phía của vật vào vùng quan sát.

### 4.2 Các khối

| Khối | Đầu vào | Xử lý và đầu ra |
| --- | --- | --- |
| Người dùng và giao diện | Vật, lựa chọn lượt quét, cấu hình | Kiểm tra điều kiện, hiển thị trạng thái, gửi yêu cầu quét |
| STM32 Nucleo-F446RE | Lệnh từ PC, công tắc HOME, trạng thái cửa | Phát STEP/DIR, điều khiển laser; trả trạng thái, số xung đã phát và lỗi |
| ESP32-S3 + camera | Yêu cầu chụp, cấu hình cảm biến | Chụp khung hình mới; trả JPEG, mã ảnh, trạng thái camera |
| Phần mềm PC | Ảnh, góc theo xung, tham số hiệu chuẩn | Trích vạch, tam giác hoá, ghép điểm, lọc cơ bản, xuất PLY |
| Lưu trữ và xuất | Ảnh gốc, đám mây điểm, nhật ký | Lưu phiên, xuất PLY; OBJ/STL dành giai đoạn tốt nghiệp |

### 4.3 Giao tiếp

- **PC là bộ điều phối** của một lượt quét.
- PC ↔ Nucleo: USB qua cổng COM ảo của ST-LINK (UM1724).
- PC ↔ ESP32-S3: Wi-Fi trong mạng nội bộ.
- Bản đầu **chưa cần** UART trực tiếp giữa hai bộ điều khiển. Nucleo vẫn tự
  xử lý lỗi mất liên lạc với PC.
- Dữ liệu đầu vào của xử lý là bộ ba: cặp ảnh, góc bàn xoay suy ra từ số
  xung, hồ sơ hiệu chuẩn. Đầu ra là tập điểm 3D đơn vị mm.
- Góc từ bộ đếm xung là **góc điều khiển ước tính**; bản cơ sở không có cảm
  biến góc tuyệt đối.

### 4.4 Lý do chia ba khối

Nucleo đảm nhiệm chuyển động và phản ứng với đầu vào phần cứng; S3 dành tài
nguyên cho camera và truyền ảnh; PC có bộ nhớ và giao diện cho hình học.
Cho phép phát triển từng khối bằng dữ liệu thử trước khi tích hợp.

## 5. Yêu cầu chức năng theo khối `[MT §8]`

### 5.1 Firmware STM32 Nucleo-F446RE

Mô đun: `MotionController`, `Homing`, `LaserControl`, `SafetyMonitor`,
`Protocol`. Trách nhiệm: phát xung bằng timer, quản lý trạng thái, đọc đầu
vào, xử lý lệnh và lỗi.

- Phát STEP bằng timer có tăng giảm tốc; GPIO điều khiển DIR và ENABLE của
  driver `[MT §5, RM T5]`.
- HOME: chống dội, giới hạn thời gian và số xung; đi chậm về công tắc, lùi
  ra, tiếp cận lại **cùng một chiều**; quản lý vị trí từ số xung đã phát
  `[MT §4, RM T5]`.
- Lệnh `LASER` bật/tắt laser.
- Chỉ cho phép chuyển sang góc tiếp theo sau khi PC xác nhận cặp ảnh hiện
  tại hợp lệ `[MT §6]`.
- Chống thực thi lặp lệnh di chuyển theo số thứ tự `[MT §7]`.
- Firmware C tổ chức thành mô đun, không ép sang hướng đối tượng.

### 5.2 Firmware ESP32-S3

Mô đun: `CameraService`, `CaptureJob`, `NetworkAPI`, `CameraSettings`.
Trách nhiệm: khởi tạo camera, cấu hình chụp, **bảo đảm ảnh mới**, quản lý bộ
đệm, truyền ảnh.

- API: đọc trạng thái, đặt cấu hình, yêu cầu chụp `[MT §7]`.
- Có thể dùng cơ chế bất đồng bộ: yêu cầu chụp trả mã công việc;
  `FRAME_READY` xác nhận JPEG đã nằm trong bộ đệm; PC yêu cầu tắt laser rồi
  tải ảnh. Tách thời gian laser sáng khỏi thời gian truyền Wi-Fi. Camera giữ
  bộ đệm đến khi tải xong hoặc hết hạn `[MT §7, RM T7]`.
- Loại ảnh đang chờ từ trước, đợi việc thu một khung mới hoàn tất
  `[MT §7]`.
- Tắt/vô hiệu stream khi quét `[MT §3, RM T7]`.

### 5.3 Ứng dụng PC

| Nhóm | Mô đun | Trách nhiệm |
| --- | --- | --- |
| Điều phối | `ScanCoordinator`, `DeviceClient`, `CameraClient`, `SessionStore` | Điều phối lượt quét, kiểm tra trạng thái, ghép dữ liệu, lưu phiên |
| Hình học | `CalibrationManager`, `LaserExtractor`, `Reconstructor`, `Evaluator` | Hiệu chuẩn, trích tâm vạch, tính điểm 3D, xuất PLY, tính chỉ tiêu |
| Giao diện | `ConnectionView`, `CalibrationView`, `ScanView` | Kết nối, chọn hồ sơ hợp lệ, tiến độ/lỗi, mở phiên và xuất PLY; xem 3D độc lập |

- `ScanCoordinator` dùng `DeviceClient` và `CameraClient` để lấy một cặp
  ảnh, ghi `CaptureRecord` vào `ScanSession`, chuyển cho `Reconstructor`;
  `CalibrationManager` cấp `CalibrationProfile` tương ứng.
- Giao diện gọi dịch vụ, **không trực tiếp điều khiển chân phần cứng**.
- Xử lý ảnh nặng chạy ngoài luồng giao diện để nút dừng và trạng thái vẫn
  đáp ứng `[MT §8, RM T10]`.
- Có chế độ **xử lý một phiên đã lưu** khi không kết nối thiết bị
  `[MT §11]`; một lệnh xử lý lại tập ảnh đã lưu tạo được tệp điểm `[RM T4]`.
- Chặn quét khi HOME lỗi, thiếu hiệu chuẩn hoặc sai hồ sơ (D050: bỏ chặn vì cửa mở); reset
  thiết bị làm mất hiệu lực trạng thái sẵn sàng cũ `[RM T10]`. Chi tiết hợp đồng giao diện,
  dữ liệu và luồng sự kiện xem [`docs/design/SYSTEM_INTERFACES.md`](design/SYSTEM_INTERFACES.md).
- Chưa cần cloud hoặc tài khoản trực tuyến `[MT §11]`.

### 5.4 Hồ sơ phân tích thiết kế `[MT §8]`

Tác nhân người vận hành; ca sử dụng kết nối, hiệu chuẩn, quét, tạm dừng,
dừng lỗi, xuất kết quả; sơ đồ trạng thái; sơ đồ tuần tự một góc quét; mô
hình dữ liệu phiên quét; sơ đồ lớp cho phần mềm PC. Tài liệu phải đối chiếu
với luồng thực tế `[RM T10]`.

## 6. Giao thức và mô hình dữ liệu `[MT §7]`

### 6.1 Kênh PC–Nucleo

- Bản tin văn bản có **phân cách rõ, mã lệnh, số thứ tự và kiểm tra độ dài**.
- Lệnh chính: `HOME`, `MOVE_ABS`, `LASER`, `STATUS`, `STOP`, `HEARTBEAT`.
- Phản hồi: `ACCEPTED` chỉ báo đã nhận lệnh; `DONE` báo hoàn tất; `ERROR`
  mang mã lỗi.
- **Lệnh lặp cùng số thứ tự không được làm bàn xoay di chuyển thêm.**
  Kiểm tra: gửi lặp 10 lệnh không tạo chuyển động thêm `[RM T7]`.

### 6.2 API camera

Xem 5.2. Yêu cầu chụp phải trả ảnh JPEG kèm mã ảnh và trạng thái camera.

### 6.3 Trường dữ liệu bắt buộc

| Trường | Ý nghĩa |
| --- | --- |
| `scan_id`, `step_index` | Phiên quét và góc đang thực hiện |
| `command_id`, `frame_id` | Liên kết lệnh với kết quả; loại phản hồi cũ hoặc gửi lặp |
| `step_count`, `angle_cmd` | Số xung tích luỹ và góc suy ra từ xung; **không gán nhãn là góc đo thực** |
| `laser_state_cmd` | Trạng thái laser PC đã yêu cầu; dùng ghép ảnh nền và ảnh vạch |
| `camera_config`, `calibration_id` | Kích thước ảnh, tham số chụp, phiên bản hiệu chuẩn |
| `timestamp`, trạng thái lỗi | Chẩn đoán; thời gian trên các thiết bị chưa đồng bộ **không** dùng như thời gian chung chính xác |

### 6.4 Kiểm soát ảnh cũ và lỗi liên lạc

- Mã ảnh do phần mềm gán **chưa chứng minh** cảm biến đã chụp sau khi laser
  đổi trạng thái. Firmware phải loại ảnh đang chờ, đợi thu khung mới hoàn
  tất, và **kiểm chứng bằng thử nghiệm bật tắt laser** (chuỗi không tuần
  hoàn, ≥ 100 chu kỳ) `[MT §7, §13, RM T2]`. Không xem mã ảnh hoặc hash là
  bằng chứng duy nhất của ảnh mới.
- Ảnh lỗi hoặc sai mã: PC chụp lại tại cùng góc, **tối đa 2 lần** sau lần
  đầu; vẫn lỗi thì dừng lượt quét, bảo toàn dữ liệu đã có `[MT §7, RM T7]`.
- Mất liên lạc (Wi-Fi, PC, kênh Nucleo): phiên về trạng thái lỗi theo
  timeout cấu hình; laser tắt `[RM T7]`.

## 7. Chu trình vận hành một lượt quét `[MT §6]`

Người dùng đặt vật lên bàn xoay, chọn hồ sơ hiệu chuẩn, bấm bắt đầu (D050: bỏ yêu
cầu đóng nắp hộp kín). Màn hình hiển thị số góc đã xong, ảnh vạch hiện tại, lỗi cần
xử lý. Sau quét: xử lý, xuất PLY và mở bằng công cụ xem 3D độc lập. Chi tiết giao
diện và chu trình xem [`docs/design/SYSTEM_INTERFACES.md`](design/SYSTEM_INTERFACES.md),
[`docs/design/SCAN_SESSION.md`](design/SCAN_SESSION.md),
[`docs/design/NUCLEO_PROTOCOL.md`](design/NUCLEO_PROTOCOL.md).

| Bước | Thao tác của hệ thống | Điều kiện để chuyển bước |
| --- | --- | --- |
| 1 Kiểm tra | Kiểm tra kết nối, camera, bộ nhớ, hồ sơ hiệu chuẩn (D050: bỏ kiểm tra công tắc cửa) | Các khối sẵn sàng; laser đang tắt |
| 2 Tìm gốc | Nucleo chạy HOME, thiết lập vị trí bắt đầu | Tìm thấy công tắc trong giới hạn thời gian và số xung |
| 3 Đến góc quét | Di chuyển đến vị trí đặt trước rồi giữ mâm | Đã phát đủ xung và hết thời gian chờ ổn định |
| 4 Chụp nền | Laser tắt; yêu cầu camera lấy khung mới | Ảnh nền đúng mã góc, đúng kích thước, giải mã được |
| 5 Chụp vạch | Bật laser; chờ ổn định rồi lấy khung mới | Camera báo đã thu xong toàn bộ khung |
| 6 Tắt và nhận ảnh | Tắt laser; tải ảnh nếu chưa tải; kiểm tra cặp | Cả hai ảnh hợp lệ, đã lưu kèm thông tin góc |
| 7 Lặp hoặc kết thúc | Chuyển góc kế tiếp; sau góc cuối tắt laser, lưu phiên | Không có lỗi; nhận lệnh cho phép từ PC |
| 8 Dựng mô hình | Xử lý ảnh, tính 3D, lọc cơ bản, xuất PLY | Tệp kết quả và nhật ký tạo thành công |

Quy tắc kèm theo:

- Trong lúc chụp và truyền, **mâm giữ nguyên vị trí**; laser chỉ sáng trong
  khoảng thu ảnh. Không có lệnh dịch mâm trước khi cặp ảnh hiện tại được lưu
  hợp lệ `[RM T7]`.
- Thời gian chờ hết rung xác định bằng thử nghiệm ảnh ở ít nhất 4 mức
  (100, 200, 400, 800 ms), rồi dùng một giá trị cố định cho tải đã kiểm tra;
  không giả định 100 ms luôn đủ `[RM T5]`.
- Bàn xoay tiến cùng một chiều trong lượt; khi chụp lại, mâm giữ nguyên để
  tránh sai lệch do đảo chiều `[MT §4]`.
- Dừng tạm tại ranh giới an toàn giữa các bước: laser tắt, mâm giữ vị trí.
- Reset, mất nguồn motor hoặc thao tác làm đổi vị trí vật: phiên phải kết
  thúc hoặc khởi động lại từ HOME; **không tiếp tục với giả định góc cũ còn
  đúng**.
- Bảng góc nghiệm thu: 200 góc từ 0° đến 358,2°, cách nhau 1,8°;
  không chụp thêm ảnh 360° trùng vị trí đầu (D048).

## 8. Trạng thái máy `[MT §8]`

`IDLE`, `HOMING`, `MOVING`, `SETTLING`, `CAPTURING`, `PAUSED`, `COMPLETED`,
`ERROR`. `ERROR` ưu tiên tắt laser, dừng chu trình và lưu nguyên nhân.
Trạng thái lỗi chỉ được xoá bằng thao tác có chủ ý `[MT §7]`.

## 9. An toàn và liên động — đã bỏ khỏi yêu cầu (D050)

**NGƯỜI DÙNG QUYẾT ĐỊNH 2026-10-09 (D050):** xoá toàn bộ yêu cầu an toàn và
liên động của mục này. Không còn yêu cầu bắt buộc nào về công tắc cửa, nút
dừng, hộp kín chặn tia, watchdog, giới hạn thời gian bật laser hay 15 ca lỗi
nghiệm thu; không cổng nào của dự án chặn vì các mục đó. D050 cũng thay
cơ chế MVS của D049 mục 5. Nội dung cũ 9.1–9.8 xem `git show f3e1766:docs/SPEC.md`.

Các phần chức năng ở mục khác vẫn giữ: mạch MOSFET đóng ngắt laser (§12, vì
GPIO không cấp được dòng laser), HOME và HOME lại sau reset (§5.1, §7), trạng
thái `ERROR` (§8), retry và bảo toàn dữ liệu khi lỗi (§7, §15). Tính năng an
toàn đã có trong firmware C4 (`T_laser_max` 5 s, IWDG) giữ nguyên trong mã
nhưng không còn là yêu cầu nghiệm thu.

## 10. Camera và điều kiện thu nhận ảnh `[MT §3]`

| Hạng mục | Yêu cầu |
| --- | --- |
| Bo và cảm biến | Kit ESP32-S3 N16R8 đã có với camera đi kèm; PID 0x3660 = OV3660 màu; kích thước tối đa driver liệt kê 2048 × 1536 |
| Mức ảnh | Sau khi PSRAM hoạt động: 640 × 480, rồi khảo sát 800 × 600 hoặc cao hơn; chốt theo độ nét và ổn định |
| Định dạng | JPEG chất lượng cao; **lưu nguyên tệp nhận được, không nén lại** trước khi trích vạch |
| Ống kính | Dùng ống kính đi kèm **nếu lấy nét được trong khoảng làm việc**; khoá vị trí sau căn chỉnh |
| Thay thế | ESP32-CAM với OV2640 nếu cần; phải hiệu chuẩn lại theo camera và chế độ ảnh thực tế |

Các bước kiểm tra trước khi thiết kế cơ khí cố định:

1. Xác nhận loại bo, sơ đồ chân camera, dung lượng PSRAM thực sự được nhận
   và khả năng cấp phát bộ đệm. **Nhãn N16R8 chưa thay cho kết quả kiểm tra
   bộ nhớ.**
2. Kiểm tra ảnh ở khoảng cách dự kiến **200–350 mm**; điều chỉnh khoảng cách
   hoặc ống kính nếu vạch không đủ nét. Trường nhìn phải bao vật ở mọi góc.
3. Chọn phơi sáng, gain, cân bằng trắng **cố định**; kiểm tra cấu hình được
   giữ qua nhiều lần chụp. Tránh vạch bão hoà hoặc quá rộng.
4. Tắt stream khi quét. Bắt đầu với một bộ đệm ảnh; kiểm chứng cách lấy ảnh
   mới sau khi đổi trạng thái laser.

Camera Raspberry Pi Global Shutter đang có được giữ cho hướng nâng cấp
riêng; bản cơ sở không nối camera Raspberry Pi vào Nucleo.

Roadmap nói thêm: chốt một chế độ ảnh chính và một chế độ phụ; ghi độ phân
giải, crop, tiêu điểm, JPEG và các chế độ tự động đã tắt; mỗi độ phân giải
dùng hiệu chuẩn riêng, không dùng lẫn `[RM T3]`.

### 10.1 Ngưỡng số cho chỉ tiêu quang học — NGƯỜI DÙNG XÁC NHẬN 2026-09-20 (D020)

Bản gốc `[RM T1]` chỉ ghi "chọn được khoảng cách nhìn rõ vật 50–100 mm; lưu
ảnh chứng minh độ nét và vùng quan sát", không có số. Theo `docs/PROCESS.md`
R3, ngưỡng phải có đơn vị, số, cách đo và được khai báo trước khi đo. Bốn
ngưỡng dưới là tiêu chí 3.5 của phiên 3 (`STATUS.md`, khai báo 16/09 trước
khi chụp 17/09) viết lại thành số; phiên viết đề xuất sáng 20/09, **người
dùng xác nhận chiều 20/09** (D020), số giữ nguyên.

| # | Đại lượng | Đơn vị | Ngưỡng | Cách đo | Kết quả 17/09 tại 250 mm |
| --- | --- | --- | --- | --- | --- |
| O1 | Bề rộng trường nhìn ngang tại mặt vật | mm | ≥ 150 | Thước mm trong khung, `pc/ruler_ticks.py` cho mm/px, nhân bề rộng ảnh | 199 — đạt |
| O2 | Tỷ lệ mm/px tại mặt vật (cấu hình chính) | mm/px | ≤ 0,50 | Như O1 | 0,31 — đạt |
| O3 | Bề rộng mép 10–90 % trên vạch thước | px | ≤ 2,0 | `pc/ruler_ticks.py`, ≥ 3 vạch, ghi trung bình và độ lệch | 4,3 — CHƯA ĐẠT |
| O4 | Chu kỳ vạch 1 mm phân giải được | — | tự tương quan có đỉnh tại chu kỳ 1 mm với hệ số ≥ 0,2 | `pc/ruler_ticks.py` hiện chỉ đo chu kỳ cm; cần mở rộng cho chu kỳ mm (chưa viết) | chưa đo bằng công cụ; bằng mắt không phân biệt được — CHƯA ĐẠT theo tiêu chí 4 cũ |

Quy tắc kèm: O1 loại khoảng cách trước, rồi so O3 giữa các khoảng còn
lại; chênh O3 dưới 10 % thì chọn khoảng gần hơn (O2 nhỏ hơn). Không hạ
ngưỡng sau khi đo. Với D016 (ống kính gốc, tiêu điểm xa), O3 và O4 giữ
CHƯA ĐẠT; trọng tài để đi tiếp là chỉ tiêu MT tuần 2 đã có số trong mục
18 (trung vị σ tâm vạch ≤ 0,5 px; ≥ 90 % hàng ROI có tâm hợp lệ), không
phải O3/O4.

### 10.2 Ngưỡng màu và phơi sáng cho hồ sơ camera cố định (C2) — NGƯỜI DÙNG XÁC NHẬN 2026-09-23 (D032)

Bổ sung sau khi T5 Vòng 4 phát hiện ảnh ám lục toàn khung so với đối
chứng 17/09 (L06, `handoff/2026-09-21_c2-camera-profile/03_TEST.md`
Vòng 4): hồ sơ cố định khi đó khoá `awb=0` mà không có gain màu thay
thế, nên cần một cổng định lượng thay câu chủ quan "màu trung thực" trước
khi chốt hồ sơ. **Làm rõ Vòng 7 (L11, 24/09):** khoá cân bằng trắng cố
định nghĩa là gain màu **thủ công** (`wb_mode` 1–4, `0x3406=1`, `awb_gain=1`)
với khối xử lý màu **bật** (`awb=1`) — không phải `awb=0`, vì `awb=0` tắt
khối áp gain và cả bốn preset cho cùng một màu ảnh (đo 24/09). Cách khoá
chi tiết ở `docs/design/SCAN_SESSION.md` mục 5; ngưỡng dưới không đổi. Đo
trên ROI thẻ A4 trắng, cùng bố trí/khoảng cách, so với **phiên AEC/AGC/AWB
tự động chụp ngay trước** (camera chưa khoá, `wb_mode=0`, `0x3406=0`) tại
cùng vị trí.

| # | Đại lượng | Đơn vị | Ngưỡng | Cách đo |
| --- | --- | --- | --- | --- |
| O5 | Độ lệch độ sáng trung bình ROI so với phiên auto tham chiếu | % | ≤ 15 | `pc/sharpness.py --roi ...`, cột `mean`/`mean_median`, so với phiên auto ngay trước cùng ROI |
| O6 | Chênh lệch kênh màu RGB trên ROI | % | ≤ 15 | `pc/sharpness.py`, cột `channel_spread_pct` = `100 × (max(R,G,B) − min(R,G,B)) / mean(R,G,B)` |
| O7 | Tỷ lệ pixel có bất kỳ kênh `≤ 5` (tối) hoặc `≥ 250` (bão hoà) | % | ≤ 1 mỗi phía | `pc/sharpness.py`, cột `dark_frac_rgb`/`sat_frac_rgb` |

O5–O7 **không thay O1–O4**: mờ quang học do D016 (ống kính gốc, tiêu điểm
xa) vẫn giữ CHƯA ĐẠT theo trọng tài tuần 2 riêng. Đây là cổng riêng cho
việc khoá phơi sáng/màu của C2, đo và qua **trước khi** đối chiếu O3/O4
trên cùng phiên. Không hạ ngưỡng sau khi đo.

### 10.3 Tiêu chí so sánh đánh giá camera FD5640 với OV3660 (P03) — ĐỀ XUẤT, người dùng xác nhận ngày 2026-10-11 & 2026-10-12 (D076, D077, D080)

Bổ sung để phục vụ quyết định D076 (thử FD5640 trước; thay hẳn OV3660 nếu tốt
hơn). Ngày 2026-10-11 (D077), người dùng xác nhận chọn phương án B của kế hoạch
P03: giữ bộ tiêu chí S1–S4 (với S4 theo hướng tiêu điểm cố định có ghi nhận),
tách phần phân tích ảnh (phần A: S1–S4) khỏi phép đo nhiệt (phần B: S5), không
mua nhiệt kế ngoài mà dùng cảm biến nhiệt trong chip ESP32-S3 làm chỉ báo tương
đối (thuộc đầu việc `p15`). Ngày 2026-10-12 (D080, `handoff/2026-10-09_p03_fd5640-danh-gia/01_PLAN.md` Vòng 3),
người dùng chốt đánh giá S1–S4 tại **200 mm và 250 mm**, **bỏ 350 mm khỏi cổng**
(chỉ giữ 350 mm làm thông tin tham khảo vì khoảng làm việc thực tế của máy quét
là 200–250 mm), và đồng bộ hợp đồng S5 với `p15` Vòng 2.

| Mã | Đại lượng và cách đo | Đơn vị | Ngưỡng đề xuất để khuyến nghị “tốt hơn” | Khi thiếu hoặc chưa đạt |
| --- | --- | --- | --- | --- |
| S1 | Độ nét: bề rộng mép 10–90 % trên cạnh thẳng của khối quy ra mm ở mặt vật bằng `pc/ruler_ticks.py` trên toàn bộ 5 ảnh mỗi phiên tại 200 mm và 250 mm; `pc/sharpness.py` xuất `lap_var`/`grad_energy` cùng ROI vật lý để đối chiếu phụ (không làm ngưỡng độc lập) | mm | Mép trung vị giảm **ít nhất 20 % ở cả 200 mm và 250 mm** so với JSON đối chứng OV3660 ngày 17/09: `E200 ≤ 0,8 × 1,359 = 1,0872 mm`, `E250 ≤ 0,8 × 1,342 = 1,0736 mm` (tính từ tệp JSON, chấm từng phiên hợp lệ đã phân tích riêng, không chọn phiên đẹp nhất hoặc trộn bố trí) | Thiếu vùng đo/chu kỳ tin cậy hoặc thiếu khoảng cách → `CHƯA ĐỦ DỮ LIỆU`; có phiên hoặc khoảng cách chưa đạt → ghi đúng phiên/khoảng đó, không kết luận đạt cả hai (kết quả 350 mm `E_OV350 = 1,185 mm` chỉ giữ làm thông tin tham khảo) |
| S2 | Vạch mm: đánh dấu cùng đoạn 1 cm gần tâm trên ảnh gốc (phóng to `Nearest-Neighbor`, không làm nét hay nội suy tạo chi tiết); Coder đánh dấu, Reviewer đếm lại độc lập | vạch / 9 | Phân biệt được **đủ 9/9 vạch 1 mm nội bộ trong 1 cm** (11 vạch tính hai đầu) trên **5/5 ảnh mỗi phiên chấm tại 200 mm và 250 mm**, đối chiếu với 17/09 (“không phân biệt được”); không coi vạch cm tự động là chứng minh vạch mm | Loá, che, mờ hoặc bất đồng khi đếm → chưa chứng minh; không đoán vạch theo vị trí dự kiến. Đây là phép đếm riêng của P03, **không thay O4** |
| S3 | Ổn định thu ảnh ngắn hạn: chấm toàn bộ các phiên lặp tại điểm chính 250 mm (tối thiểu 3 phiên × 5 ảnh = 15 ảnh; hiện có `r1–r6` = 30 ảnh) và điểm phụ 200 mm (thay 350 mm; tối thiểu 1 phiên × 5 ảnh, tính toàn bộ khi thêm ảnh 200 mm cho S4) bằng `pc/capture_session.py`, VGA 640×480, quality 10, tắt stream | ảnh, lỗi | FD5640 đạt **tối thiểu 15/15 ảnh tại 250 mm** (chấm đủ **30/30 ảnh `r1–r6`** hiện có, không dừng ở 15 ảnh đẹp) và **5/5 ảnh hiện có tại 200 mm** (cộng toàn bộ ảnh 200 mm mới khi thu thêm cho S4); **0 retry, 0 lỗi kết nối, 0 reset bất ngờ trong phiên, 0 timestamp trùng hoặc lùi**, đủ `count − 1` phép so timestamp mỗi phiên | Thiếu lượt chụp → `CHƯA ĐỦ DỮ LIỆU`; reset có ghi nhận giữa các phiên không phải lỗi (không kiểm timestamp tăng liên tục qua các lần khởi động khác nhau); chưa thay kiểm chứng quét dài 200 góc hay C5/C7 |
| S4 | Tiêu điểm cố định có ghi nhận: tại **mỗi khoảng cách (200 mm và 250 mm)**, ghi nhận bố trí/gá, vị trí ống kính giữ nguyên, không chỉnh/không chạy lấy nét giữa các ảnh và lượt, cấu hình/firmware, các lần tháo/lắp/reset + độ biến thiên bề rộng mép `E_i` (mm) trên **15 ảnh cùng bố trí** với phương pháp nhất quán | % | Có đầy đủ ghi nhận cố định bố trí/tiêu điểm trong chuỗi thử (không yêu cầu lệnh khoá AF mới hay phần cứng VCM mới), và **độ biến thiên `(max(E_i) − min(E_i)) / median(E_i) ≤ 10 %`** (`median(E_i) > 0`, `E_i` tính bằng `mm`, một ROI/thuật toán nhất quán cho cả bộ 15 ảnh cùng bố trí tại mỗi khoảng cách: `250 mm` dùng `r4–r6`; `200 mm` dùng bộ 3 phiên mới `capture_p03_fd5640_200mm_r1`…`r3`) | Chưa đủ 15 ảnh cùng bố trí ở khoảng cách nào (hiện 200 mm mới có 1 phiên 5 ảnh cũ) → S4 tại khoảng cách đó `CHƯA ĐỦ DỮ LIỆU`, không suy từ khoảng cách kia. Tính thêm từng phiên để truy nguyên nhưng kết luận bằng cả bộ 15 ảnh, không bỏ ảnh qua reset. Nếu cơ chế lấy nét thực chưa biết, ghi rõ `"tiêu điểm ổn định trong bố trí/chuỗi ảnh đã thử; khả năng khoá AF CHƯA KIỂM CHỨNG"` |
| S5 | Chỉ báo tăng nhiệt lõi chip ESP32-S3 tương đối (sau cổng `p15`, đồng bộ `p15` Vòng 2): 3 cặp lượt độc lập `OV→FD`, `FD→OV`, `OV→FD` trên cùng chip/bo/firmware/điều kiện, tải VGA q10 (40 ảnh, cách 3 s sau baseline `t0`, tối đa 120 s; hai baseline trong cặp chênh `≤ 2 °C`), lấy mẫu tại `t0, +5, +15, +30, +60, +120 s` (lệch `≤ 2 s`); chỉ nhận HTTP 200, `valid=true`, `temperature_c` hữu hạn trong `[−10, 80] °C`, `configured_min_c=-10`, `configured_max_c=80`, có boot ID/uptime phù hợp | °C | Với `d(k,t) = [T_FD(k,t) − T_FD(k,0)] − [T_OV(k,t) − T_OV(k,0)]` và `D_k = max_{t ∈ {5,15,30,60,120}} d(k,t)`: đủ mẫu hợp lệ cả 3 cặp và **mọi `D_k ≤ 5 °C` → `ĐẠT theo chỉ báo`**; có cặp đầy đủ **`D_k > 5 °C` → `CHƯA ĐẠT theo chỉ báo`** (bỏ yêu cầu `range_reg`/`error_max` từng mẫu, giao dải động, cửa sổ `−5…75 °C` và biên tham khảo `4 °C` của Vòng 2; không tự gán sai số `±1 °C` hoặc nói sai số triệt tiêu) | Chưa qua cổng `p15` hoặc thiếu/lỗi/reset trong lượt/sai thời điểm → `CHƯA ĐO` / `CHƯA ĐỦ DỮ LIỆU`, không gán 0/nội suy hoặc làm tròn để đạt. Sai số tuyệt đối chưa xác định; luôn giữ nhãn chỉ báo, **nhiệt bề mặt module/ổn áp luôn `CHƯA ĐO`** |

Quy tắc kèm theo:

- Bộ S1–S5 **không thay O1–O4 (§10.1), O5–O7 của C2 (§10.2) hay trọng tài C7 (§18 / D016)**.
- Phần A (S1–S4) được thực hiện và nghiệm thu độc lập tại mốc `B_A` trước khi có `p15`; phần B (S5) bổ sung tại mốc `B_B` sau khi `p15` qua cổng và người dùng thu log trên bo.
- Không cộng điểm để lấy độ nét bù cho tiêu điểm hay nhiệt chưa biết. Chưa đạt hoặc chưa đủ S1–S5 thì giữ FD5640 ở trạng thái camera thử theo D076, chưa mở hiệu chuẩn A1 thật hoặc thu ảnh thật C5/C7.
- Cảm biến trong ESP32-S3 chỉ báo nhiệt trong silicon, không đo nhiệt bề mặt module camera hay nơi người dùng báo nóng. **Không tự chốt thay hẳn camera khi nhiệt bề mặt còn `CHƯA ĐO`**; nếu người dùng quyết định thay hẳn trong tình trạng đó thì phải có mục quyết định `D` riêng trong `DECISIONS.md` ghi rõ việc chấp nhận rủi ro nhiệt bề mặt (D077).

## 11. Cơ khí bàn xoay và bố trí quang học `[MT §4]`

### 11.1 Cơ cấu

- NEMA17 góc bước 1,8°; đai GT2, pulley **20 răng** trên motor, **60 răng**
  trên trục mâm (tỷ số 3:1).
- Trục Ø8 mm đỡ bằng ổ bi, có phần tử chịu lực dọc trục. Không đặt toàn bộ
  tải lên trục motor `[RM T5]`.
- Mâm khoảng **160 mm**, sơn hoặc phủ đen nhám, có cơ cấu giữ vật tháo lắp.
- Khung đế MDF hoặc vật liệu dễ gia công; gá motor có rãnh căng đai; gá
  camera và laser chỉnh được rồi siết cố định; camera và laser **cùng gắn
  lên một kết cấu cứng**.
- Tải vật ban đầu tối đa **300 g**, kiểm tra thực tế với tải lệch tâm.

### 11.2 Bước quay

200 bước/vòng × 1/16 vi bước × 3:1 = **9.600 xung STEP mỗi vòng mâm**.

| Số góc mỗi lượt | Góc giữa hai lần chụp | Xung mỗi lần | Số ảnh hợp lệ |
| --- | --- | --- | --- |
| 200 | 1,8° | 48 | 400 |
| 400 | 0,9° | 24 | 800 |
| 800 (khảo sát thêm) | 0,45° | 12 | 1.600 |

0,0375° mỗi vi bước chỉ là độ phân giải lệnh lý tưởng; độ chính xác thực
phụ thuộc driver, tải, mất bước, độ rơ và độ đảo.

### 11.3 Bố trí quang học

- Góc giữa camera và mặt phẳng laser khoảng **25–35°** tại vùng quét, chỉnh
  bằng thực nghiệm. Vạch laser phủ đủ chiều cao vật.
- Hộp che mặt trong tối và nhám để giảm ánh sáng nền, phản xạ phụ và laser
  thoát ra ngoài.

### 11.4 Chỉ tiêu cơ khí `[RM T5]`

- HOME: 10/10 lần hoàn tất; mô phỏng công tắc không tác động phải dừng theo
  giới hạn đã đặt (B).
- Xung: đo **độc lập** bằng bộ đếm, logic analyzer hoặc máy hiện sóng đúng
  24/48 xung mỗi lệnh; không chỉ kiểm biến đếm trong mã (B).
- Với tải: 10 vòng cùng chiều không kẹt hoặc trượt thấy được; sai lệch dấu
  chuẩn ≤ 1 mm tại bán kính 70 mm; ghi tải và cách đo (MT).

## 12. Mạch điện, nguồn và PCB `[MT §5]`

| Khối mạch | Yêu cầu thiết kế |
| --- | --- |
| Driver động cơ | A4988 có tản nhiệt; VDD logic 3,3 V; VMOT 12 V; chỉnh giới hạn dòng theo động cơ và điện trở sense của module thật. MS1/2/3 và ENABLE đặt bằng phần cứng; giữ mô-men khi chụp `[BOM Cau hinh]` |
| Đóng ngắt laser | MOSFET logic-level 3,3 V, điện trở cổng, điện trở kéo xuống |
| Nguồn | Adapter 12 V 3 A; nhánh motor riêng; buck 5 V cấp camera; cầu chì, công tắc nguồn, đầu nối đủ dòng |
| Lọc và nối đất | Tụ khối sát VMOT và camera, tụ gốm cục bộ; đường dòng motor không đi qua đường hồi nguồn camera; GND chung cho mạch điều khiển |
| Đầu vào | HOME có chống dội |
| Điểm kiểm tra | 12 V, 5 V, 3,3 V, GND, STEP, DIR, ENABLE, tín hiệu laser |

- **PCB hai lớp** dạng bo mở rộng cho Nucleo: socket driver, MOSFET, đầu nối
  nguồn, motor, laser, HOME. Nucleo tiếp tục dùng ST-LINK
  trên bo. Hồ sơ: schematic, layout, Gerber, drill, BOM, bản vẽ kết nối,
  biên bản kiểm tra; ERC/DRC không còn lỗi chưa xử lý hoặc giải trình
  `[RM T6]`.
- Giai đoạn thử: Nucleo cấp qua USB, camera bằng nhánh 5 V phù hợp. Khi hoàn
  thiện nguồn chung: chọn cấu hình cấp nguồn theo tài liệu bo; **không nối
  song song 5 V USB và buck**.
- Chốt sơ đồ chân sau khi kiểm tra đúng biến thể bo; bản mô tả không thay
  sơ đồ đấu dây cuối cùng.
- Chỉ tiêu nguồn trên mạch thử: nhánh 5 V tại camera trong **4,75–5,25 V**
  với tải thử; đo đồng hồ không thay khảo sát sụt áp nhanh khi reset (MT)
  `[RM T6]`.
- Đặt PCB cuối tuần 6; nhận dự kiến tuần 7–8; PCB về phải qua kiểm tra
  nguồn không tải, rồi gắn lần lượt Nucleo, driver, camera; chưa về thì ghi
  rõ, không đánh dấu đạt `[RM T6, T8]`.

## 13. Hiệu chuẩn hình học `[MT §9]`

Thứ tự bắt buộc: camera → mặt phẳng laser → trục quay; cơ cấu phải cố định
trước khi chốt trục `[RM Các phụ thuộc]`.

### 13.1 Camera

- 15–25 ảnh bàn cờ phẳng (roadmap: ≥ 20 khớp + ≥ 5 kiểm tra) ở nhiều vị trí
  và góc nghiêng, phủ vùng ảnh sẽ dùng; đo kích thước ô thật sau khi in; dán
  lên tấm phẳng cứng.
- OpenCV `calibrateCamera`: ma trận nội tham số, hệ số méo, tư thế từng ảnh;
  lưu sai số tái chiếu từng ảnh; kiểm tra bằng ảnh độc lập.
- Sau hiệu chuẩn: khoá ống kính, khoảng cách, độ phân giải, chế độ cắt ảnh.
  Đổi camera, tiêu cự hoặc cách đọc/cắt ảnh → hồ sơ mới.
- Loại ảnh mờ theo tiêu chí đã ghi, không loại ảnh chỉ vì nó làm tăng sai
  số `[RM T3]`.
- Chỉ tiêu: RMS bộ khớp ≤ 0,7 px; RMS bộ kiểm tra ≤ 1,0 px (MT, ngưỡng nội
  bộ); nạp lại hồ sơ tái tạo được kết quả; ứng dụng phát hiện sai độ phân
  giải hoặc hồ sơ thiếu tham số (B) `[RM T3]`.

### 13.2 Mặt phẳng laser

- Bảng hiệu chuẩn ở nhiều tư thế (≥ 6 khớp + ≥ 2 kiểm tra); mỗi tư thế chụp
  OFF để lấy tư thế bảng và ON để lấy tâm vạch; bảng không xê dịch giữa hai
  ảnh.
- Giao tia nhìn qua mỗi điểm vạch với mặt phẳng bảng → điểm 3D thuộc mặt
  phẳng laser; khớp mặt phẳng chung bằng bình phương tối thiểu hoặc phương
  pháp bền vững, loại ngoại lai có ghi lý do.
- Điểm phải phủ đủ vùng đo, không chỉ một vạch thẳng hoặc một vùng quá nhỏ.
- Di chuyển laser hoặc camera sau bước này → hiệu chuẩn lại.
- Chỉ tiêu: RMS khoảng cách đến mặt phẳng bảng ở từng tư thế kiểm tra
  ≤ 2 mm (MT) `[RM T4]`.

### 13.3 Đường trục quay

- Bảng có dấu nhận dạng gắn cứng lên mâm, lệch trục; thu nhiều tư thế
  (≥ 10 khớp + 3 kiểm tra); ArUco hoặc bảng nhiều mặt giúp giữ danh tính.
- Khớp trục chung bằng phép quay tương đối hoặc quỹ đạo tròn của các điểm;
  không cần bảng nhìn thấy trong toàn bộ 360°.
- Hồ sơ lưu: một điểm trên trục, vectơ đơn vị hướng trục, quy ước góc dương,
  vị trí gốc.
- Kiểm chứng chiều quay bằng vật bất đối xứng; quét thử vật đơn giản để phát
  hiện đường nối lệch hoặc bề mặt nhân đôi.
- Chỉ tiêu: RMS vị trí điểm nhận dạng ở góc kiểm tra so với tư thế gốc
  ≤ 2 mm; **không dùng ICP** để làm đẹp phép kiểm tra (MT) `[RM T8]`.
- Bộ hiệu chuẩn cuối: hồ sơ camera, laser, trục thuộc cùng cấu hình, có ảnh
  lắp và ngày; hồ sơ trước khi đổi gá không dùng mặc định (B) `[RM T8]`.

## 14. Xử lý ảnh và tính toạ độ không gian `[MT §10]`

### 14.1 Trích tâm vạch laser

- Giải mã JPEG, kiểm tra cấu hình. Chuyển sang **kiểu số có dấu hoặc số
  thực** rồi lấy hiệu kênh đỏ (ON − OFF), chặn âm về 0. Có thể kết hợp độ nổi
  của đỏ so với xanh lá và xanh dương. **Không trừ bằng số nguyên không dấu.**
- Trong ROI: ngưỡng cường độ và giới hạn độ rộng loại điểm quá yếu, quá
  rộng, bão hoà. Mỗi hàng: xác định cụm sáng, ưu tiên cụm liên tục với hàng
  lân cận. Nhiều ứng viên không phân biệt được → **đánh dấu không hợp lệ**,
  không lấy trung bình các nhánh.
- Cơ sở: **trọng tâm cường độ** trong cụm hợp lệ. So sánh với khớp Gauss
  cục bộ chuyển sang tốt nghiệp (D048). Vị trí phân số pixel không đồng
  nghĩa độ chính xác vật lý dưới pixel.
- Vẽ tâm vạch lên ảnh gốc; đánh dấu bão hoà, quá yếu, nhiều nhánh `[RM T2]`.

### 14.2 Tam giác hoá

Tâm vạch → toạ độ ảnh chuẩn hoá đã bỏ méo bằng nội tham số. Gọi **r** là
vectơ tia nhìn từ tâm camera, **n** và *d* là hệ số mặt phẳng laser:

    nᵀP + d = 0
    P = λ r ,   λ = −d / (nᵀ r)

Chỉ giữ điểm trước camera, trong thể tích quét, tia nhìn không gần song song
với mặt phẳng laser. Thang đo do hồ sơ hiệu chuẩn và đơn vị bảng quyết định.

### 14.3 Đưa các lát cắt về cùng tư thế

Gọi **c** là điểm trên trục, **a** vectơ đơn vị hướng trục, θ góc quay theo
quy ước đã kiểm tra. Điểm ở góc θ đưa về tư thế gốc bằng phép quay ngược:

    P₀ = c + R_a(−θ) (P − c)

Kiểm chứng chiều quay bằng vật bất đối xứng; **không dùng ICP để che lỗi
hiệu chuẩn trục** trong bản cơ sở.

## 15. Dựng mô hình và tổ chức phiên quét `[MT §11]`

### 15.1 Đám mây điểm và đầu ra PLY — D048

- Ghép về cùng hệ mm; loại điểm ngoài vùng vật, thuộc mâm và ngoại lai
  bằng xử lý cơ bản. Nếu giảm mẫu, ghi kích thước voxel.
- PLY là đầu ra bắt buộc, mở được bằng công cụ độc lập. XYZ chỉ có thể
  là dữ liệu trung gian đã có, không phải một định dạng xuất bắt buộc mới.
- Lưu tham số và số điểm trước/sau lọc; giữ ảnh/điểm trước xử lý để tái tạo.
- Dựng lưới, OBJ/STL, in 3D và sửa mô hình tích hợp chuyển tốt nghiệp.

### 15.2 Dữ liệu một phiên quét

| Dữ liệu | Nội dung |
| --- | --- |
| Thông tin phiên | Mã phiên, thời gian, mẫu vật, số góc, người thực hiện nếu cần, trạng thái hoàn tất |
| Ảnh gốc | Từng cặp OFF/ON theo chỉ số góc; **giữ nguyên dữ liệu camera gửi về** |
| Hồ sơ hiệu chuẩn | Nội tham số, méo, mặt phẳng laser, trục quay, đơn vị, cấu hình camera, mã phiên bản |
| Nhật ký thu nhận | Mã lệnh, mã ảnh, số xung, lần chụp lại, lỗi, thời gian từng công đoạn |
| Dữ liệu trung gian | Tâm vạch, điểm bị loại, chỉ số chất lượng, điểm 3D trước lọc |
| Kết quả | PLY, báo cáo đo, ảnh kết quả xem bằng công cụ độc lập |

Ảnh gốc và hiệu chuẩn cho phép chạy lại thuật toán mà không quét lại. Mọi số
liệu báo cáo gắn với chế độ ảnh, hồ sơ hiệu chuẩn, mẫu vật và phiên bản mã
nguồn `[RM Quy cách đo]`.

## 16. Chỉ tiêu nghiệm thu cuối kỳ — D048

| Nhóm | Nội dung cần chứng minh | Loại |
| --- | --- | --- |
| Thiết bị và mạch | Bàn xoay, camera, laser, hộp, nguồn, PCB tự thiết kế chạy tải thật; kiểm HOME | B |
| Thu nhận | Một cấu hình camera, 200 góc → 400 ảnh hợp lệ; đúng ảnh–góc–trạng thái; mọi retry có log | B |
| Hiệu chuẩn | Đủ camera, laser, trục; kiểm tra độc lập; cùng cấu hình, lưu/nạp lại được | B |
| Ứng dụng | GUI tối thiểu: kết nối, hồ sơ hợp lệ, bắt đầu/dừng, tiến độ/lỗi, mở phiên, xử lý lại, xuất PLY; 6 luồng chức năng, 4 ca đầu vào sai; mở ≥2 phiên ngoại tuyến | B |
| Độ ổn định | Ba lượt 200 góc liên tiếp, mỗi lượt 400 ảnh; không reset/bỏ góc âm thầm | B |
| Thực nghiệm | ≥3 mẫu đối chứng độc lập, mỗi mẫu ≥1 kích thước phù hợp; một mẫu 5 phiên cùng điều kiện | B |
| Sai số | Mỗi kích thước kiểm tra 50–100 mm: sai số tuyệt đối ≤2 mm; báo từng trị | MT |
| Tốc độ | ≤15 phút/lượt 200 góc từ bắt đầu HOME đến lưu ảnh cuối, kể cả retry | MT |
| Tỷ lệ thử lại | Yêu cầu gốc cần ≥1 retry / tổng yêu cầu gốc ≤2% | MT |
| GUI | Phản hồi trong 1 s khi tác vụ dài | MT |
| Đầu ra | PLY có đơn vị mm mở độc lập; cùng ảnh, cấu hình, hiệu chuẩn tái xử lý được; cài môi trường PC mới và xử lý phiên mẫu | B |

Mục tiêu 15 phút nay áp dụng 200 góc theo phê duyệt D048, không phải kết
quả thực đo hoặc phép chia thời gian chế độ cũ. Thời gian xử lý/GUI báo
riêng. Tăng mật độ góc không tự chứng minh tăng độ chính xác. Lưới/STL,
so sánh thuật toán, chế độ góc và cấu hình ảnh sau tuần 2 không còn là
nghĩa vụ nghiệm thu học phần.

### 16.1 Quy cách đo `[RM Quy cách đo]`

| Chỉ tiêu | Cách tính | Điều kiện ghi |
| --- | --- | --- |
| Ảnh hợp lệ | Giải mã được, đúng kích thước và cấu hình, đúng mã phiên/góc, đúng trạng thái OFF/ON theo phép kiểm tra đã xác nhận | Phiên N góc có 2N ảnh chấp nhận; ảnh loại và thử lại đếm riêng |
| Tỷ lệ phải thử lại | Số yêu cầu chụp gốc cần ≥ 1 lần thử lại ÷ tổng yêu cầu gốc × 100 % | Không dùng tổng số lần gửi lại làm mẫu số |
| Tỷ lệ hàng có vạch | Hàng có tâm hợp lệ ÷ hàng trong ROI chọn trước và thật sự được laser phủ | Lưu ROI; **không đổi vùng sau khi biết kết quả** |
| Dao động tâm vạch | Mỗi hàng hợp lệ chung: độ lệch chuẩn mẫu của tâm qua loạt ảnh; lấy **trung vị** | Vật, camera, laser đứng yên, cùng cấu hình; đơn vị px |
| RMS tái chiếu | Căn bậc hai trung bình bình phương khoảng cách 2D góc quan sát – góc chiếu lại | Bộ khớp và bộ kiểm tra báo riêng; không suy thẳng px → mm |
| Sai số kích thước | Trị tuyệt đối của (kích thước đo trên 3D − kích thước đối chứng), cùng định nghĩa hình học | mm; ghi từng kích thước, dụng cụ, số lần đo, vùng điểm khớp |
| Độ lặp lại | 5 phiên: 5 giá trị, trung bình, độ lệch chuẩn mẫu (n−1), min–max | Phân biệt giữ nguyên vật với tháo đặt lại; lặp lại không thay chính xác |
| Thời gian quét | Từ bắt đầu HOME đến ảnh cuối lưu hợp lệ, tính cả chụp lại; đồng hồ đơn điệu trên PC | Dựng hình, GUI, lỗi báo riêng |

Thời gian phản ứng lỗi ghi điểm bắt đầu và kết thúc; không trừ hai
timestamp của thiết bị chưa đồng bộ; báo giới hạn độ phân giải của cách đo.

## 17. Thiết kế thí nghiệm đánh giá `[MT §13, RM T11]`

Đối chứng độc lập: khối hộp và trụ nhám đo bằng thước cặp; đo nhiều vị trí
theo cùng định nghĩa (khoảng cách hai mặt phẳng, đường kính trụ khớp từ vùng
chỉ định); vật in 3D thì đo vật đã in, không lấy kích thước CAD. **Không
dùng chính kích thước kiểm tra để chỉnh thang đo rồi báo sai số trên nó.**
Độ chia 0,01 mm của thước cặp không chứng minh độ chính xác 0,01 mm.

| Thí nghiệm | Dữ liệu cần thu |
| --- | --- |
| Đối chứng kích thước | ≥3 mẫu nhám đơn giản; ≥1 kích thước phù hợp/mẫu; dụng cụ/cách đo và đơn vị, mẫu kiểm tra độc lập với dữ liệu chỉnh thuật toán |
| Lặp lại giữ nguyên vật | 5 phiên trên một mẫu; từng giá trị hình học, thời gian, trung bình, độ lệch chuẩn mẫu, min–max |
| Độ ổn định | 3 lượt 200 góc liên tiếp đúng cấu hình cuối; số ảnh, retry, reset, thời gian |
| Độ mới của ảnh | Giữ ≥100 chu kỳ OFF/ON và phép kiểm tuần 2; không làm lại nếu bằng chứng còn áp dụng đúng cấu hình |
| Tái xử lý | Phiên lưu mở ngoại tuyến, PLY mở độc lập, môi trường PC mới tái tạo được |

So sánh COG/Gauss, 200/400 góc và ma trận ảnh/JPEG sau tuần 2 chuyển
sang tốt nghiệp; không bỏ hoặc đổi kết quả khảo sát C2b của tuần 2.

Báo cáo: bảng theo mẫu, phân bố sai số, hình chụp vùng lỗi; RMS phần dư khớp
mặt phẳng chỉ đánh giá độ phẳng tương đối. Giữ riêng dữ liệu chỉnh thuật
toán và dữ liệu kiểm tra sau cùng; kết quả cũ không bị thay thế âm thầm.

## 18. Kế hoạch theo nhánh phụ thuộc — D048

Nguồn kế hoạch hiện hành: `docs/ROADMAP.md`, đủ sơ đồ G/A/B/C/D/E/H1–H4/V/R/F,
đầu vào từng khối, cổng kiểm chứng, nhánh Git dự kiến và cách làm song song.
Không chia phần sau tuần 2 theo tuần lịch. Không coi khối đã hoàn thành
khi mới viết mã/build; kiểm trên máy và trên bo phải ghi riêng.

### 18.1 Tuần 1–2 giữ nguyên

Bảng chỉ tiêu cơ sở dưới đây được giữ nguyên. Nội dung và cổng của mọi
handoff tuần 2 không đổi; trạng thái hiện tại xem STATUS và từng handoff.

| Tuần | Điều kiện đầu vào | Chỉ tiêu cuối tuần (loại) |
| --- | --- | --- |
| 1 Kiểm tra phần cứng và môi trường | Nucleo, kit S3 + OV3660, cáp, máy tính; đúng sơ đồ chân bo đang có | Nhận dạng và bộ nhớ: log cảm biến + PSRAM, ghi đọc 1 MiB không sai, xác minh R8 (B). Thu ảnh thử: 100/100 tệp giải mã đúng, không reset trong 20 phút (B). Giao tiếp Nucleo: 100 PING → 100 PONG đúng thứ tự; nạp và chạy lại sau rút cắm (B). Quang học: chọn được khoảng cách nhìn rõ vật 50–100 mm, ảnh chứng minh (MT) |
| 2 Cặp ảnh laser và trích vạch | Camera qua tuần 1; laser vạch, MOSFET, nguồn, hộp che tạm có đường chặn tia | Đúng trạng thái ảnh: 100 cặp OFF/ON đúng thứ tự, chuỗi không tuần hoàn không nhận nhầm (B). Tham số ổn định: cùng hồ sơ camera, kiểm tra lại sau loạt (B). Trích vạch: ≥ 90 % hàng ROI có tâm hợp lệ, ROI chọn trước (MT). Độ ổn định tâm: trung vị σ ≤ 0,5 px (MT) |
| 2 | Ảnh có vạch rõ và đúng trạng thái | Tập trung camera, nguồn, ánh sáng; hoãn cơ khí cố định chưa cần mua |

### 18.2 Các nhánh và hội tụ

- G [Q1–Q4]: phạm vi, tiêu chí, giao thức, cấu trúc dữ liệu và API giữa khối.
- A1 → A2 [Q3/Q4/Q6, hiệu chuẩn, Q9]: camera → laser → điểm đơn lát.
- B1 → B2 [Q3/Q5/Q6/Q8/Q9]: thiết kế → bàn xoay/firmware kiểm chứng.
- C1 → C2 [Q5/Q7/Q8/Q9]: sơ đồ → mạch đã thử → layout/chế tạo → PCB đạt.
- D1 [Q3/Q4/Q6/Q9]: điều phối giả lập; E1 [Q3/Q4/Q6/Q9]: GUI giả lập.
- H1 = B2 + D1 + sản phẩm thu ảnh/laser tuần 2 đạt: 20 góc/40 ảnh đúng.
- H2 = A2 + H1 + C2 + gá cố định: kiểm hiệu lực camera/laser, hiệu chuẩn trục.
- H3 sau H2: 200 góc/400 ảnh, ghép điểm, PLY và tái xử lý ngoại tuyến.
- H4 = H3 + E1: toàn quy trình qua GUI trên thiết bị đã có PCB kiểm chứng.
- V sau H4: đánh giá, sửa nhánh gây lỗi, kiểm lại và nghiệm thu §16–17.
- R xuyên suốt; F = V + R: sáu nhóm bàn giao §3.

Mỗi mũi tên là phụ thuộc, nhiều đầu vào là điều kiện AND. Chuẩn bị mã/
giả lập làm sớm được theo hợp đồng, nghiệm thu thật phải chờ đủ đầu vào.
A1 không chờ bàn xoay/PCB; H1 không chờ trục; PCB không chờ mô hình 3D.
Không chốt gá quang học khi quang học chưa kiểm. Thời gian nhận PCB chưa
bảo đảm; chưa có bo chạy thật thì chưa đạt H4.

### 18.3 Mốc mục tiêu và quỹ thời gian

- 01–03/12/2026: H4 cơ bản hoàn thành.
- Trước 24/12/2026: V nghiệm thu cấu hình cuối.
- Trước 31/12/2026: F bộ bàn giao; hạn nộp đầu tháng 01/2027 (chưa ngày cụ thể).
- Người dùng xác nhận 4 giờ/ngày mọi ngày =28 giờ/7 ngày; dự kiến 20–22 giờ
  việc chính, 6–8 giờ dự phòng/kiểm lại, không phải số giờ đã làm.
- B chưa đạt chặn phụ thuộc; MT chưa đạt ghi số/nguyên nhân, chỉ tiếp tục
  phần độc lập; C7 vẫn theo D016. Lỗi quay nhánh gây lỗi và kiểm phần ảnh hưởng.

Nhánh Git/worktree và ánh xạ tuần lịch sử: ROADMAP §7–8. Quy trình Q1–Q9
và dây chuyền bốn chặng vẫn áp dụng từng gói triển khai.

## 19. Dự toán và kế hoạch mua `[MT §14, RM Kế hoạch mua, BOM]`

Đơn vị: đồng. Tận dụng Nucleo-F446RE và kit S3 đã có (0 đ). Giá là ước
tính từ BOM, không phải báo giá.

| Nhóm | Cấu phần dự kiến | Thành tiền |
| --- | --- | --- |
| Điện tử và giao tiếp | Laser vạch 35k; A4988 35k; MOSFET + điện trở 20k; HOME 10k; cụm liên động cửa 40k; nút dừng 35k; 2 cáp USB 50k | 225.000 |
| Nguồn và dây | Adapter 12 V 3 A 120k; buck 5 V 35k; tụ 15k; jack, công tắc, cầu chì 30k; dây và vật tư 50k | 250.000 |
| Cơ khí bàn xoay | NEMA17; pulley 20T/60T; đai GT2; trục Ø8; hai gối bi; ổ chặn; bích; vòng chặn; mâm; gá motor | 450.000 |
| Đế hộp và gá lắp | Khung đế, hộp che, gá camera và laser, vít và phụ kiện | 390.000 |
| Bo mạch | Bo thử 20k; một đợt PCB hai lớp 200k; đầu nối và socket 40k | 260.000 |
| Hiệu chuẩn và đối chứng | Bảng phẳng 40k; thước cặp 180k (có thể mượn); vật mẫu 50k | 270.000 |
| **Cộng** | | **1.845.000** |
| Dự phòng 15 % | | 276.750 |
| Vận chuyển | | 80.000 |
| **Tổng kế hoạch** | Làm tròn bố trí ~2,2 triệu | **2.201.750** |

Chưa gồm: công lao động, dụng cụ hàn, thiết bị đo, thuê gia công phát sinh,
in mẫu 3D; dự phòng chưa đủ cho một lần thiết kế lại PCB. Ống kính khác,
TMC2209, laser thứ hai, máy tính nhúng: chỉ mua khi thử nghiệm chỉ ra nhu
cầu `[BOM O01–O05]`.

Mua theo mốc: tuần 1–4 điện tử, nguồn, bo thử, hiệu chuẩn (765.000); tuần
3–5 cơ khí, **đặt sau kiểm chứng quang học** (840.000); tuần 6 PCB
(240.000). Theo dõi chi thực tế và dự phòng còn lại. Danh mục mua theo tuần
đã lập trong `docs/HARDWARE_PREP.md`.

BOM 14/09 khác bản mô tả ở: A01 tính 300.000 cho bo S3-CAM + OV2640 (thực tế
đã có bo, camera là OV3660); cửa 20k → 40k; cáp 25k → 50k; tổng 2.495.000 so
với 2.201.750. Sheet "Cau hinh" mô tả kiến trúc ESP32 tự điều khiển motor và
GPIO của Ai-Thinker, **không áp dụng** cho cấu hình hiện tại (D005).

## 20. Rủi ro kỹ thuật `[MT §16]`

| Rủi ro | Ảnh hưởng | Biện pháp trong phạm vi đồ án |
| --- | --- | --- |
| PSRAM chưa được nhận | Thiếu bộ đệm, mất ổn định khi tăng ảnh | Xác minh cấu hình bo và bộ nhớ trước; chỉ nâng độ phân giải sau thử nghiệm |
| Lens không nét hoặc xê dịch | Vạch rộng, hiệu chuẩn sai | Thử quang học trước mua cơ khí; khoá lens và gá sau căn chỉnh |
| Ảnh cũ hoặc tham số tự đổi | Ghép sai OFF/ON, lệch tâm vạch | Kiểm tra bộ đệm, khoá cấu hình, ghi metadata, thử trạng thái laser lặp lại |
| Rung, mất bước, trượt đai | Lệch góc, đường nối không khép | Giảm gia tốc, chỉnh dòng và căng đai, giữ cùng chiều, kiểm tra HOME |
| Sai hiệu chuẩn trục hoặc laser | Bề mặt đôi, sai kích thước | Nhiều tư thế, dữ liệu độc lập, hiệu chuẩn lại sau thay đổi gá |
| Nguồn camera nhiễu | Mất ảnh, reset khi motor chạy | Tách nhánh công suất, GND và tụ hợp lý; thử với tải thật |
| Vật bóng, tối, trong suốt | Phản xạ phụ, mất vạch | Công bố phạm vi vật liệu; đánh dấu vùng không tin cậy, không nội suy như dữ liệu đo |
| Wi-Fi hoặc PC lỗi | Treo phiên, thiếu ảnh, laser sáng lâu | Timeout, heartbeat, giới hạn sáng laser, lưu dữ liệu đã nhận |
| Thiếu đáy và hốc sâu | Lưới hở hoặc suy đoán | Hiển thị vùng thiếu; nhiều tư thế chỉ khi cơ sở đã ổn định |

## 21. Môi trường và công cụ phát triển `[MT §8]`

- Nucleo: STM32CubeIDE hoặc tương đương, C/C++ với HAL.
- S3: Arduino framework hoặc ESP-IDF với `esp32-camera`.
- PC: Python, OpenCV, NumPy; GUI tối thiểu dự kiến PySide6. Open3D chỉ
  dùng nếu cần cho xử lý cơ bản, không bắt buộc dựng lưới/trình xem tích hợp.
- **Ghi phiên bản thư viện và cấu hình build** để tái tạo môi trường; tại F
  phải cài lại môi trường Python mới và xử lý lại phiên mẫu theo README,
  không phụ thuộc đường dẫn riêng `[RM T14]`.
- Cấu hình thực tế trên máy ghi ở `ENVIRONMENT.md`.

## 22. Báo cáo theo khối và mốc — D048

Khi hoàn thành khối hoặc cập nhật mốc, dùng biểu mẫu này; mỗi tiêu chí có đường
dẫn tệp hoặc mã phiên để kiểm tra lại.

| Trường | Nội dung điền |
| --- | --- |
| Khối và thời gian | G/A/B/C/D/E/H/V/R/F; từ ngày đến ngày; **tổng số giờ thực tế** |
| Cấu hình đã dùng | Bo, camera, lens, độ phân giải, firmware, ứng dụng, `calibration_id` |
| Công việc hoàn thành | Đối chiếu các mục việc của khối; đầu ra cụ thể |
| Kết quả chỉ tiêu | Tên / B, MT hoặc M / ngưỡng / giá trị thực đo / đạt hay chưa |
| Minh chứng | Ảnh, log, tệp dữ liệu, biểu đồ, commit |
| Vấn đề còn mở | Hiện tượng, bước tái hiện, mức ảnh hưởng, nguyên nhân đã kiểm tra |
| Quyết định bước tiếp theo | Phần đủ điều kiện chuyển tiếp; phần phải sửa; thay đổi lịch hoặc phạm vi |
| Chi phí | **Đã chi trong kỳ báo cáo; luỹ kế; dự phòng còn lại** |

## 23. Hướng phát triển cho đồ án tốt nghiệp `[MT §17, D048]`

Dành cho giai đoạn này: lưới/OBJ/STL và in 3D; xem/chỉnh sửa 3D tích hợp;
so sánh COG/Gauss, mật độ góc, độ phân giải/JPEG; quét nhiều tư thế.
Hệ thống 200 góc học phần hiện tại là mốc đối chứng, không cam kết bo S3
đủ khả năng xử lý ảnh tại thiết bị khi chưa đo.

Xử lý ảnh tại thiết bị: trích tâm vạch trên bộ xử lý gắn camera, truyền toạ
độ và chỉ số chất lượng thay cho toàn bộ ảnh; chọn ESP32-S3 hay SoC mạnh hơn
dựa trên đo thời gian, bộ nhớ và sai số. Câu hỏi nghiên cứu: mức giảm dữ
liệu truyền với mức tăng sai số chấp nhận được; chọn phơi sáng và mật độ góc
theo chất lượng vạch. Hướng khác: trục nghiêng, ghép nhiều tư thế, đo lệch
so với CAD, quản lý phiên qua mạng. Không nằm trong yêu cầu học phần này.

## 24. Ảnh chụp trạng thái lịch sử (2026-09-19)

Giữ nguyên bằng chứng lịch sử; không dùng bảng này thay STATUS hiện hành.
Các nhãn tuần sau tuần 2 đối chiếu ROADMAP §8; D048 không sửa kết quả cũ.

Chi tiết ở `STATUS.md` và `DECISIONS.md`; ở đây chỉ ghi các điểm spec đã
được chốt, đã lệch, hoặc cần chú ý khi triển khai tiếp.

| Mục spec | Trạng thái | Ghi chú |
| --- | --- | --- |
| §10 PSRAM, nhận dạng cảm biến | ĐÃ QUAN SÁT 16/09 | 8192 KB, ghi đọc 1 MiB đạt; D008, D011 |
| §18 tuần 1 ba chỉ tiêu B | ĐẠT 16/09 | Log trong `docs/logs/` |
| §18 tuần 1 MT Quang học | CHƯA ĐẠT 17/09 | Ống kính mờ 1,2–1,4 mm ở mặt vật tại 200/250/350 mm; barrel không xoay; người dùng chọn phương án C (D016): đi tiếp với ống kính này, MT tuần 2 là trọng tài. Phù hợp với `[RM T2]` "chưa mua lens khác cho đến khi xác định nguyên nhân bằng ảnh thử". Khoảng cách làm việc tạm 250 mm (D015) |
| §10 "bắt đầu với một bộ đệm" | LỆCH có chủ ý | Firmware dùng hai đệm `CAMERA_GRAB_LATEST` từ khi PSRAM hoạt động (D008); phép kiểm chứng ảnh mới ở tuần 2 vẫn bắt buộc |
| §6.1 giao thức có số thứ tự, ACCEPTED/DONE/ERROR | CHƯA CÓ | Tuần 1 mới có `PING n` → `PONG n` (D014). Lệnh `LASER` (C4 tuần 2) là lệnh đầu tiên phải theo khung §6.1 |
| §9 timeout laser | BỎ YÊU CẦU 09/10 (D050) | Firmware C4 đã có `T_laser_max` 5 s (gộp `8e5f1f7`), giữ trong mã. Ghi chú cũ: Đề xuất N = 5 s trong kế hoạch tuần 2; đỉnh `/capture` đo được 1676 ms nên 5 s có dự phòng, cần ghi cơ sở khi triển khai |
| §10 khoá phơi sáng | CHƯA CÓ | `/status` 17/09 cho thấy AEC/AWB đang tự chỉnh; C2 tuần 2 |
| §12 PCB, §11 cơ khí | CHƯA BẮT ĐẦU | Theo lịch tuần 5–6; chỉ đặt cơ khí sau kiểm chứng quang học tuần 2 |
| §21 thư viện | MỘT PHẦN | `pc/requirements.txt` có numpy, pillow, pyserial, requests; OpenCV (tuần 3), PySide6 (tuần 10), Open3D (tuần 11–12) chưa thêm |
| §22 báo cáo tuần | CHƯA CÓ | Tuần 1 kết thúc 22/09; hồ sơ hiện chưa theo dõi giờ thực tế và chi phí |
| §19 BOM | LỖI THỜI | D005; danh mục mua theo tuần dùng `docs/HARDWARE_PREP.md`; BOM cập nhật theo mua thực tế là sản phẩm bàn giao nhóm 2 |

## Tài liệu kỹ thuật tham khảo (theo bản mô tả)

1. STMicroelectronics, *STM32 Nucleo-64 boards MB1136 user manual UM1724* —
   COM ảo qua ST-LINK, lựa chọn cấp nguồn.
2. Espressif, *esp32-camera sensor definitions* — ánh xạ PID OV3660.
3. Espressif, *esp32-camera driver* — cảm biến, kích thước ảnh, PSRAM, bộ đệm.
4. Allegro, *A4988 DMOS Microstepping Driver* — STEP/DIR, vi bước, giới hạn dòng.
5. OpenCV, *Camera Calibration and 3D Reconstruction*.
6. OpenCV, *Detection of ArUco Markers*.
7. Open3D, *Point cloud outlier removal*.
8. Open3D, *Surface reconstruction*.

Tài liệu nhà sản xuất và thư viện dùng để đối chiếu giao tiếp và công cụ;
không phải nguồn chứng nhận thiết bị sẽ đạt các ngưỡng trên.
