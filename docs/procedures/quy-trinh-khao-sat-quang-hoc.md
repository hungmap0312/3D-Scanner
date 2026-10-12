# Quy trình khảo sát quang học — bước 3.3, ĐÃ CHẠY 17/09, giữ để chụp lại sau khi chỉnh tiêu điểm

Mục đích: lấy số đo và ảnh cho chỉ tiêu MT "Quang học" tuần 1: chọn khoảng
cách camera–vật để vật 50–100 mm hiện rõ, và biết khung ảnh bao được bao
nhiêu mm. Ba phiên chụp ngắn ở 200, 250 và 350 mm, mỗi phiên 5 ảnh.

Thời gian cần: khoảng 30–40 phút, phần lớn là bố trí; mỗi lệnh chụp chạy
chừng 30 giây. Cần: bo S3 và cáp USB, khối hộp (vật mẫu A1), thước mm
(A3), băng dính, một chỗ gá bo (kẹp, băng dính hai mặt hoặc chân đế điện
thoại), điện thoại để chụp ảnh bố trí. Không cần mua gì.

**Nguyên tắc cho cả ba phiên:** thứ duy nhất được đổi là khoảng cách của
hộp. Bo không xê dịch, đèn không đổi, thước vẫn dán trên hộp, cùng độ phân
giải VGA. Đổi bất kỳ thứ gì khác thì ba phiên không so được với nhau.

**Quy tắc đo, khai báo trước:** vùng đo độ nét (ROI) của mỗi phiên là hình
chữ nhật trùm đoạn thước nhìn thấy trong ảnh và mặt trước hộp; xác định
riêng cho từng phiên vì hộp ở gần hiện to hơn ở xa. Thước mm dán trên mặt
trước hộp cũng là mốc tính mm/pixel. Tiêu chí chọn khoảng cách nằm ở mục
"Mục tiêu phiên 3" phía trên.

#### Phần A. Bố trí vật và chỗ đặt (chưa cần máy tính)

**A1. Đo vật mẫu.**
- Ở đâu: trên bàn, với thước mm.
- Làm gì: đo ba cạnh của vật, ghi ra giấy theo dạng dài×rộng×cao để lát
  điền vào `--note`. KHÔNG viết gì lên vật. Chọn một mặt phẳng, có chữ
  hoặc hoạ tiết nếu có, làm **mặt trước**; mặt này sẽ hướng về camera.
- Vật đã chốt, NGƯỜI DÙNG CUNG CẤP 17/09 kèm ảnh: khối gỗ `30x32x49` mm,
  mặt trước là mặt 30×49 mm có chữ viết tay và vạch bút chì; chữ và vạch
  là chi tiết tốt để đo độ nét, để nguyên. Dựng khối đứng, cạnh 49 mm
  theo chiều cao. Khối này nhỏ hơn dải 50–100 mm của roadmap; đủ cho
  khảo sát hôm nay vì thang mm lấy từ thước, nhưng từ tuần 2 nên có thêm
  hộp cạnh 60–100 mm (xem `docs/HARDWARE_PREP.md` A1).
- Thấy gì là đúng: ba số mm đã ghi ra giấy; mặt trước phẳng, không bóng.
- Nếu sai: vật bóng loáng hoặc trong suốt thì chọn vật khác đục, nhám;
  báo tôi vật đã dùng.

**A2. Đặt thước cùng mặt phẳng với mặt trước vật.**
- Ở đâu: ngay trước mặt trước vật, tại vạch khoảng cách đang làm.
- Làm gì, với vật hẹp như khối gỗ 32 mm: dựng thước **tựa vào mặt trước
  khối**, cạnh dưới thước đặt trên bàn sát vạch khoảng cách, thân thước
  ngả nhẹ về sau tựa lên khối, vạch số hướng về camera, vạch `0` ở phía
  tay trái hoặc ở dưới. Cạnh dưới thước cách mặt khối không quá 10 mm;
  khi đó thước lệch khoảng cách dưới 2 %, chấp nhận được. Không dán thước
  lên mặt 32 mm vì thước dài hơn nhiều sẽ lật. Làm lại bước này ở mỗi
  khoảng cách vì thước di chuyển cùng khối.
- Làm gì, nếu sau này dùng hộp to hơn thước: đặt thước nằm ngang áp sát
  mặt trước, dán hai mẩu băng dính ở hai đầu, không che vạch.
- Thấy gì là đúng: nhìn từ phía camera thấy thước và vạch mm rõ, thước
  không cong. Thước trong suốt che chữ trên khối vẫn được vì chữ nhìn
  xuyên qua.
- NGƯỜI DÙNG ĐÃ DỰNG THỬ 17/09, ảnh gửi trong chat, chưa lưu repo: thước
  nhựa trong, thang cm/mm khoảng 15 cm, vạch `0` ở dưới sát bàn, thân
  thước tựa lên mặt trước khối gần thẳng đứng, chân thước sát chân khối.
  Đạt yêu cầu A2. Lưu ý rút từ ảnh: vạch trên đoạn thước nhô cao hơn
  khối chỉ đọc được nếu nền sau sáng màu (A3); mặt nhựa có vệt loá, nếu
  ảnh `/capture` thấy vệt trắng trên thước thì xoay vài độ hoặc dịch đèn.
- Nếu sai: thước ngả nhiều (cạnh dưới cách khối hơn 10 mm) thì mm/pixel
  tính ra sai vì thước ở khoảng cách khác vật; dựng lại.

**A3. Chọn chỗ và ánh sáng.**
- Ở đâu: một mặt bàn phẳng, dài ít nhất 50 cm theo hướng nhìn.
- Làm gì: phía sau chỗ sẽ đặt hộp là tường hoặc tấm bìa màu đồng nhất.
  Bật đèn phòng như bình thường. Không để nắng chiếu trực tiếp lên hộp,
  không dùng đèn pin hay đèn bàn chiếu riêng.
- Thấy gì là đúng: hộp sáng đều, không có bóng gắt, không có vệt nắng.
- Nếu sai: phải đổi đèn giữa chừng thì làm lại cả ba phiên từ đầu; ghi
  vào `--note`.

**A4. Gá bo S3 và đưa vật lên ngang tầm ống kính.**
- Ở đâu: một đầu bàn.
- Làm gì: cố định bo sao cho ống kính camera hướng ngang dọc theo bàn,
  bo thẳng đứng, không chúc xuống. Cắm cáp USB vào bo và máy tính; để cáp
  có độ chùng, không kéo bo.
- NGƯỜI DÙNG ĐÃ GÁ 17/09, ảnh gửi trong chat: bo S3 (nhãn module
  `ESP32-S3 WROOM`, module camera ở đỉnh bo, hai cổng USB-C) gắn trên
  tấm perfboard xanh, kẹp trong chân đế trắng có kẹp đen; ống kính hướng
  ngang. Đạt phần gá. Nhưng ống kính cao ước 17–20 cm trên bàn, còn tâm
  khối gỗ cao 2,5 cm: camera ngang sẽ không thấy khối. KHÔNG chúc camera
  xuống: mặt vật sẽ không vuông góc với trục quang, mm/pixel và độ nét đổi
  theo chiều cao, hỏng giả định đo. Thay vào đó **kê vật lên**:
  1. Đo chiều cao tâm ống kính so với mặt bàn bằng thước, ghi lại (ví dụ
     `180`).
  2. Xếp một bệ phẳng (chồng sách, hộp cứng) cao bằng số đó trừ 25–50 mm
     (ví dụ 130–155 mm), để trục ống kính rơi vào khoảng từ tâm tới đỉnh
     khối; khối ở giữa khung, phần thước nhô lên vẫn có chỗ.
  3. Bệ đi cùng khối tới cả ba vạch; không đổi chồng sách giữa các phiên.
  4. Kẻ mốc 0 (A5) ngay dưới mặt trước ống kính: dựng thước thẳng đứng từ
     bàn lên chạm mặt ống kính để lấy điểm. Khi đặt khối ở vạch, dựng
     thước thẳng đứng tại vạch, mặt trước khối chạm thước.
  Ghi chiều cao ống kính và chiều cao bệ vào `--note`.
- CẬP NHẬT 17/09, ảnh thứ hai trong chat: người dùng đã lật bo 180° trong
  kẹp, module camera xuống sát mép trên kẹp đen, cổng USB-C và cáp ở
  trên; tâm ống kính cao ƯỚC 6–7 cm, chưa đo. Với `H` đo được, bệ cao
  `H − 49` đến `H − 25` mm (ví dụ `H` = 65 → bệ 16–40 mm, một cuốn sách
  mỏng); `H` ≤ 50 thì không cần kê. Ảnh chụp ra sẽ lộn ngược so với chiều
  16/09; không ảnh hưởng phép đo.
- NGƯỜI DÙNG ĐO 17/09: `H` = 65 mm; kê khối bằng miếng gỗ 20 mm → khối
  chiếm 20–69 mm, trục ở 65 mm, trong khoảng cho phép 16–40 mm của bệ.
  Ảnh bố trí toàn cảnh gửi trong chat (bo bên phải, dải băng dính trục,
  ba dải ngang có vạch, khối và thước trên bệ bên trái, cửa sổ sau lưng
  bo). Trợ lý chưa đọc được vạch nào là 200/250/350 từ ảnh; đã yêu cầu
  xác nhận thứ tự và điểm gốc đo (mép trước ống kính), mặt chữ quay về
  camera, phông sau khối, ánh sáng cửa sổ, cắm USB. Ảnh này dùng cho A6
  với tên `quang-hoc-bo-tri-2026-09-17.jpg`, chưa lưu.
- Ảnh gá ĐÃ LƯU: `docs/logs/s3-board-mounted-2026-09-17.jpg` (ảnh gá lần
  đầu, camera ở đỉnh; NGƯỜI DÙNG CUNG CẤP, ĐÃ KIỂM Ở ĐÂY bằng Pillow, vào
  Git 17/09). Đây là một nửa của bước 3.6: mặt trước bo với nhãn
  `ESP32-S3 WROOM`; còn thiếu mặt sau và ảnh cận đầu nối camera.
- Thấy gì là đúng: lay nhẹ cáp, bo không xê dịch. Ống kính không bị cáp
  hay kẹp che. Nhìn ngang từ bên cạnh, tâm ống kính nằm trong khoảng từ
  tâm tới đỉnh khối trên bệ.
- Nếu sai: bo dễ trượt thì dán thêm băng dính; bo lệch giữa ba phiên là
  phải làm lại cả ba. Bệ lệch cao thấp giữa các phiên thì khối lệch
  khung, vẫn đo được nhưng ghi vào `--note`.

**A5. Kẻ ba mốc khoảng cách trên bàn.**
- Ở đâu: mặt bàn, phía trước ống kính.
- Làm gì: dán một dải băng dính lên bàn ngay dưới **mặt trước ống kính**
  (mép ngoài của ống kính tròn nhỏ trên module camera) và kẻ một vạch: đó
  là **mốc 0**. Đặt thước nằm dọc theo hướng nhìn, đầu `0` của thước trùng
  mốc 0, kẻ vạch tại `200` và `250`. Với `350`: nếu thước dài đủ thì kẻ
  luôn; thước 300 mm thì kẻ vạch tại `300`, dời thước để đầu `0` trùng
  vạch 300 rồi kẻ tại `50`. Ghi số bên cạnh từng vạch.
- Thấy gì là đúng: ba vạch `200`, `250`, `350` thẳng hàng với hướng nhìn
  của ống kính.
- Nếu sai: đo lệch quá 5 mm thì kẻ lại; sai số 2–3 mm chấp nhận được, ghi
  khoảng cách thực đo vào `--note` nếu khác số tròn.

**A6. Chụp ảnh bố trí bằng điện thoại.**
- Ở đâu: đứng chéo phía sau bo, lấy cả bo, ba vạch và hộp.
- Làm gì: chụp một ảnh khi hộp đang ở vạch 200. Sau khi xong cả ba phiên,
  chép ảnh vào `D:\scanner3d\docs\logs\` với tên
  `quang-hoc-bo-tri-2026-09-16.jpg` (đổi ngày nếu làm ngày khác).
- Vì sao: ảnh này vào báo cáo `docs/tests/` làm "ảnh cấu hình đi kèm", và
  là bằng chứng khoảng cách đã đo thế nào.
- Tiện thể cho bước 3.6: khi tháo bo khỏi gá lúc kết thúc, chụp thêm hai
  mặt bo S3 đủ đọc nhãn module và đầu nối camera, cùng cổng USB đang cắm.
  Chưa cần làm ngay bây giờ.

#### Phần B. Kiểm tra bo đang chạy sketch camera

**B1. Kiểm tra bo trả lời.**
- Ở đâu: trình duyệt trên máy tính, sau khi cắm cáp USB ở A4 chừng 15 giây.
- Làm gì: gõ vào thanh địa chỉ `http://192.168.31.9/status` rồi `Enter`.
  IP `192.168.31.9` là giá trị chiều 16/09; có thể đã đổi.
- Thấy gì là đúng: một dòng chữ dài dạng `{"0x3400":...,"framesize":...}`.
- Nếu sai: trang không tải được thì IP đã đổi hoặc bo không chạy sketch
  camera. Mở Arduino IDE, menu `Tools` > `Serial Monitor`, chọn
  `115200 baud` ở góc phải dưới, bấm nút `RST` trên bo một lần, đọc dòng
  `WiFi connected, IP ...` và dùng IP đó thay cho `192.168.31.9` ở mọi lệnh
  dưới. Nếu Serial in `psramFound` hoặc `RESULT_1MIB` thì bo đang chạy
  `PsramTest`: nạp lại sketch camera bằng `File` > `Open...` >
  `D:\scanner3d\firmware\esp32s3\CameraWebServerTest\CameraWebServerTest.ino`;
  `Tools`: `Board` = `ESP32S3 Dev Module`, `PSRAM` = `OPI PSRAM` (menu hay
  trở về `Disabled`, phải nhìn), `Port` = `COM9`; bấm `Upload`; rồi làm
  lại B1.

**B2. Căn khung hình.**
- Ở đâu: trình duyệt, sau khi đặt hộp vào vạch đang làm.
- Làm gì: gõ `http://192.168.31.9/capture` rồi `Enter`. Trình duyệt hiện
  một ảnh chụp tức thời. Nhìn ảnh, dịch hộp sang trái phải hoặc chỉnh độ
  cao hộp bằng cách kê giấy dưới hộp, KHÔNG chỉnh bo, cho tới khi: hộp ở
  gần giữa ảnh, thấy trọn mặt trước hộp, và thấy ít nhất đoạn thước `0`
  tới `100`. Mỗi lần chỉnh xong bấm `F5` để chụp lại.
- Thấy gì là đúng: hộp và thước trọn trong ảnh, không bị cắt mép.
- NGƯỜI DÙNG ĐÃ LÀM 17/09 tại vạch 200, ảnh `/capture` QVGA gửi trong
  chat: khối trọn, hơi dưới tâm; thước thẳng nhô lên trên; phông tường
  trắng đều; vạch thước trên nền tường rõ hơn đoạn đè lên gỗ, nên mm/pixel
  sẽ đọc ở đoạn 5–10 cm phía trên khối. Ước thô từ ảnh: khối 49 mm ≈ 95 px
  → ≈ 0,52 mm/px → khung ≈ 165 mm ở 200 mm, sát ngưỡng 150 mm; số thật
  chờ ảnh VGA. Người dùng xác nhận: vạch gần bo nhất là 200, rồi 250,
  350; mốc 0 là hình chiếu mặt camera xuống bàn. Đạt, chuyển D1.
- Nếu sai: ảnh có thể lật ngược hoặc đối xứng gương, đó là cài đặt của
  firmware, không cần chỉnh. Ảnh lúc này có thể nhỏ 320×240; chỉ dùng để
  căn khung, lệnh chụp ở phần D sẽ đặt 640×480. Ở vạch 200 mà hộp không
  vừa khung thì vẫn chụp; đó là dữ liệu cho tiêu chí trường nhìn.

**B3. Đóng trình duyệt.**
- Ở đâu: mọi tab đang mở trang của bo.
- Làm gì: đóng hết trước khi gõ lệnh chụp. Serial Monitor để mở được.
- Vì sao: tab đang xem stream sẽ tranh camera với `/capture`; tab
  `/capture` tĩnh thì vô hại nhưng đóng cho chắc.

#### Phần C. Mở terminal đúng chỗ (VS Code)

**C1. Mở thư mục dự án.**
- Ở đâu: VS Code.
- Làm gì: menu `File` > `Open Folder...`, chọn `D:\scanner3d`, bấm
  `Select Folder`. VS Code đang mở sẵn dự án thì bỏ qua.
- Thấy gì là đúng: cột trái hiện các thư mục `docs`, `firmware`, `pc`.

**C2. Mở terminal Git Bash.**
- Ở đâu: VS Code.
- Làm gì: menu `Terminal` > `New Terminal`, hoặc giữ `Ctrl` và bấm phím
  dấu huyền (phím nằm ngay dưới `Esc`, bên trái số `1`).
- Thấy gì là đúng: dòng nhắc có chữ `MINGW64` và kết thúc bằng
  `/d/scanner3d`, ví dụ `bestp@MÁY MINGW64 /d/scanner3d (main)`.
- Nếu sai: dòng nhắc `PS D:\scanner3d>` là PowerShell: bấm mũi tên xuống
  cạnh dấu `+` góc phải khung terminal, chọn `Git Bash`; hoặc dùng các lệnh
  ở phần E. Không có `/d/scanner3d` thì gõ `cd /d/scanner3d` rồi `Enter`.

**C3. Selftest, chưa cần bo.**
- Ở đâu: terminal ở C2.
- Làm gì: gõ đúng dòng sau rồi `Enter`:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --selftest
  ```
- Thấy gì là đúng: các dòng kết thúc bằng `OK`, một dòng
  `(gioi han, khong chan)` là bình thường, dòng cuối `SELFTEST: PASS`.
- Nếu sai: `No such file or directory` là sai thư mục hoặc sai shell,
  quay lại C2. `ModuleNotFoundError` thì chụp màn hình gửi tôi.

#### Phần D. Ba phiên chụp (Git Bash, gõ nguyên văn từng dòng rồi Enter)

**D1. Phiên 200 mm.**
- Ở đâu: bàn, rồi terminal.
- Làm gì: đặt vật sao cho **mặt trước vật** trùng vạch `200`, mặt vật
  vuông góc với hướng nhìn (hai mép cách đều hai bên vạch); dựng thước
  theo A2. Căn khung theo B2, đóng tab theo B3. Trong dòng lệnh dưới, thay `000x000x000` bằng
  ba số đo ở A1 và thay IP nếu B1 cho IP khác. Gõ rồi `Enter`:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_200mm --meta-copy docs/logs --note "quang hoc 200 mm; hop 000x000x000 mm; thuoc dan mat truoc, vach 0 ben trai; den phong"
  ```
- Thấy gì là đúng: trong 10 giây đầu `Phien: capture_qh_200mm`, rồi
  `/control framesize=10 (VGA): http 200`, rồi `Kich thuoc mong doi: (640, 480)`,
  rồi `Lam nong (khong dem): [...]` với 5 khung. Sau đó 5 dòng cách nhau
  3 giây dạng `[  1/5] OK  http=200  xxxxx B  640x480 ...`. Kết thúc là khối
  tổng kết có `Ket qua: PASS`, `anh dat/yeu cau : 5/5`, rồi
  `Da ghi: D:\scanner3d\data\raw\capture_qh_200mm` và
  `Da chep ho so phien (khong gom anh) vao: D:\scanner3d\docs\logs\capture_qh_200mm`.
- Nếu sai: xem phần F.

**D2. Xem nhanh một ảnh vừa chụp.**
- Ở đâu: Windows Explorer.
- Làm gì: mở `D:\scanner3d\data\raw\capture_qh_200mm`, bấm đúp
  `img_0003.jpg`.
- Thấy gì là đúng: trọn mặt trước hộp và đoạn thước có trong ảnh. Không
  cần nhận xét nét hay mờ ở bước này; đó là việc của số đo.
- Nếu sai: hộp hoặc thước bị cắt mép thì chỉnh hộp (không chỉnh bo), rồi
  chạy lại lệnh D1 với `--session-id capture_qh_200mm_lan2`. KHÔNG xoá thư
  mục cũ; ảnh gốc giữ bất biến theo `data/README.md`. Báo tôi phiên nào
  là phiên dùng.

**D3. Phiên 250 mm.**
- Ở đâu: bàn, rồi terminal.
- Làm gì: nhấc vật đặt mặt trước trùng vạch `250`, dựng lại thước theo
  A2, không đụng bo. Căn khung theo B2, đóng tab. Gõ rồi `Enter` (thay số đo và IP như D1):
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_250mm --meta-copy docs/logs --note "quang hoc 250 mm; hop 000x000x000 mm; thuoc dan mat truoc, vach 0 ben trai; den phong"
  ```
- Thấy gì là đúng: như D1 với `capture_qh_250mm`. Mở nhanh `img_0003.jpg`
  như D2.

**D4. Phiên 350 mm.**
- Làm gì: vật tới vạch `350`, dựng lại thước, căn khung, đóng tab, gõ rồi `Enter`:
  ```
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_350mm --meta-copy docs/logs --note "quang hoc 350 mm; hop 000x000x000 mm; thuoc dan mat truoc, vach 0 ben trai; den phong"
  ```
- Thấy gì là đúng: như D1 với `capture_qh_350mm`.

Ba phiên nên làm liền nhau trong cùng một lần bật đèn. Xong D4 thì chụp
ảnh bố trí (A6) nếu chưa chụp, rồi có thể tháo bo và chụp ảnh bo cho 3.6.

#### Phần E. Nếu terminal là PowerShell, dùng các lệnh này thay cho C3, D1, D3, D4

```
.venv\Scripts\python.exe pc\capture_session.py --selftest
.venv\Scripts\python.exe pc\capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_200mm --meta-copy docs/logs --note "quang hoc 200 mm; hop 000x000x000 mm; thuoc dan mat truoc, vach 0 ben trai; den phong"
.venv\Scripts\python.exe pc\capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_250mm --meta-copy docs/logs --note "quang hoc 250 mm; hop 000x000x000 mm; thuoc dan mat truoc, vach 0 ben trai; den phong"
.venv\Scripts\python.exe pc\capture_session.py --host 192.168.31.9 --framesize VGA --count 5 --interval 3 --warmup 5 --session-id capture_qh_350mm --meta-copy docs/logs --note "quang hoc 350 mm; hop 000x000x000 mm; thuoc dan mat truoc, vach 0 ben trai; den phong"
```

#### Phần F. Lỗi thường gặp

- `Thu muc phien da ton tai, khong ghi de`: đã có phiên tên đó. Thêm
  `_lan2` vào sau `--session-id`, ví dụ `capture_qh_200mm_lan2`. Không xoá
  thư mục cũ.
- `Khong doc duoc /status: ConnectionError` hoặc `timed out`: máy không
  tới được bo. Làm lại B1 để lấy IP đúng; kiểm tra máy tính và bo cùng
  Wi-Fi.
- `Bo bao framesize = 6 khac yeu cau 10`: bo không đổi được độ phân giải.
  Chụp màn hình gửi tôi, không chạy lại.
- `Ket qua: FAIL` kèm các dòng `ERR` về mạng: giữ nguyên thư mục, chạy lại
  với `_lan2`, và báo tôi số lần phải chạy lại. FAIL kèm
  `nghi reset (ts lui)` khác 0: dừng, gửi tôi khối tổng kết; đây là lỗi bo,
  không phải lỗi bố trí.
- Ảnh tối đen hoặc trắng xoá khi mở ở D2: kiểm tra đèn và nắng (A3). Nếu
  phải đổi đèn thì làm lại cả ba phiên với `_lan2`.

#### Phần G. Gửi lại gì

1. Báo "xong ba phiên" kèm tên ba phiên đã dùng (kể cả `_lan2` nếu có).
   Hồ sơ đã tự nằm ở `docs/logs/capture_qh_*/`, ảnh ở `data/raw/capture_qh_*/`
   trên máy này, tôi đọc trực tiếp; không cần dán khối tổng kết, trừ khi
   có FAIL.
2. Ba cạnh hộp (mm), chiều dài thước, đoạn thước nhìn thấy trong ảnh
   (ví dụ `0–100`), và khoảng cách thực đo nếu khác 200/250/350.
3. Ảnh bố trí đã chép vào `docs/logs/quang-hoc-bo-tri-2026-09-16.jpg`.
4. Nhận xét bằng mắt, chỉ để tham khảo: mở `img_0003.jpg` của ba phiên,
   phóng 100 %, ở phiên nào vạch mm phân biệt rõ nhất.

Phần tiếp theo (3.4) là việc của tôi: đọc toạ độ hai vạch thước và ROI
trên ảnh của từng phiên, chạy `pc/sharpness.py`, đưa lại ảnh chú thích để
bạn xác nhận điểm đánh dấu đúng vạch, rồi lập bảng và báo cáo.
