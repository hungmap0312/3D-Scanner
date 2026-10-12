# Quy trình nạp và kiểm tra Fresh Capture trên ESP32-S3 (Đầu việc C5a)

Tài liệu hướng dẫn người dùng thực hiện kiểm chứng phần cứng bo ESP32-S3 chặng Q6 (tiêu chí Q6-T9 và Q6-T10) cho endpoint `/capture_fresh`, xác minh cấu hình một buffer (`fb_count = 1`), 5 header chẩn đoán, loại trừ tranh chấp với `/stream`, telemetry heap `/status`, và các kịch bản ngoại lệ / ngắt kết nối theo kế hoạch Vòng 6 và Quyết định D043/D044.

> [!WARNING]
> **AN TOÀN LASER TUYỆT ĐỐI**: Trong đầu việc C5a (chặng kiểm chứng camera Q6), **HOÀN TOÀN KHÔNG BẬT LASER VÀ KHÔNG KẾT NỐI NGUỒN LASER**. Toàn bộ các phép đo kiểm tra camera và mạng ở chặng này chỉ thực hiện trong điều kiện ánh sáng môi trường phòng, vật thể tĩnh, không có laser.

---

## 1. Chuẩn bị phần cứng, bàn đo và thư mục phiên tổng độc quyền

Để đảm bảo toàn bộ bằng chứng đo (ảnh setup, log Serial, manifest, snapshot JSON, raw JPEG) không bị ghi đè khi chạy lại giữa các ngày hoặc các lần thử nghiệm khác nhau, mỗi buổi đo khởi tạo một thư mục phiên tổng độc quyền có nhãn thời gian (timestamp).

- **Ở đâu:** Bo mạch ESP32-S3 (Freenove ESP32-S3 WROOM N16R8 kèm camera OV3660) và máy tính:
  - Cáp USB Type-C dữ liệu nối cổng USB-UART của bo vào máy tính.
  - Cụm camera OV3660 đã được cài chặt vào socket FPC trên bo.
  - Máy tính và bo ESP32-S3 kết nối chung mạng Wi-Fi 2.4 GHz.
- **Làm gì:**
  1. **Khởi tạo biến thư mục phiên tổng:**
     - **Git Bash:**
       ```bash
       SESSION_DIR="docs/logs/c5a_q6_$(date +%Y%m%d_%H%M%S)"
       mkdir -p "$SESSION_DIR"
       echo "Thu muc phien: $SESSION_DIR"
       ```
     - **PowerShell:**
       ```powershell
       $SESSION_DIR = "docs/logs/c5a_q6_$(Get-Date -Format yyyyMMdd_HHmmss)"
       New-Item -ItemType Directory -Force -Path $SESSION_DIR | Out-Null
       Write-Host "Thu muc phien: $SESSION_DIR"
       ```
  2. **Bố trí bàn đo và lưu ảnh:**
     - Đặt bo ESP32-S3 cố định trên giá hoặc mặt phẳng hướng vào vật thể tĩnh trong phòng với đèn phòng bật sáng ổn định.
     - Dùng điện thoại chụp ảnh bố trí bàn đo thực tế (setup camera, khoảng cách tới vật và nguồn sáng phòng) và lưu ảnh bố trí vào tệp `$SESSION_DIR/setup.jpg` (Git Bash: `"$SESSION_DIR/setup.jpg"`, PowerShell: `"$SESSION_DIR\setup.jpg"`).
  3. Mở file cấu hình Wi-Fi `firmware/esp32s3/CameraWebServerTest/secrets.h` (sao chép từ `secrets.h.example` nếu chưa có) và điền đúng thông tin mạng Wi-Fi 2.4 GHz (`ssid` và `password`).
  4. Xác nhận cổng COM thực tế trong Device Manager (ví dụ `COM4` hoặc `COM6`).
- **Thấy gì là đúng:** Windows nhận diện cổng COM ổn định, tệp `secrets.h` đã có thông tin Wi-Fi, tệp ảnh setup đã được lưu tại thư mục phiên.
- **Nếu sai:** Không thấy cổng COM -> kiểm tra cáp USB dữ liệu, cài lại driver USB-UART (CH340/CP210x).

---

## 2. Lưu baseline firmware và Biên dịch/Nạp firmware Q6 qua Arduino CLI

Theo kế hoạch Vòng 6, **chỉ giữ luồng Arduino CLI có artifact và hash SHA-256 xác định** làm luồng nghiệm thu chính thức của Q6. Giao diện Arduino IDE GUI không sinh mã băm artifact xác định trong build log nên không thuộc luồng nghiệm thu.

- **Đường dẫn Arduino CLI trên hệ thống:**
  - `C:/Users/bestp/AppData/Local/Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe`
- **Ở đâu:** Terminal tại thư mục gốc `d:/scanner3d`.
- **Làm gì:**

### Bước 2.1: Lưu bản build Baseline từ commit `main` (không đổi nhánh)
Để lưu trữ artifact baseline làm mốc so sánh mà không làm ảnh hưởng cây làm việc chung, ta xuất mã nguồn từ commit `main` (`e92867eecf5eaad308ab1a222069de07d964e6fb`) ra thư mục tạm riêng biệt và biên dịch baseline:

- **Git Bash:**
  ```bash
  ARDUINO_CLI="C:/Users/bestp/AppData/Local/Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe"
  if [ -e "firmware/esp32s3/CameraWebServerTest/build/baseline" ]; then
    echo "Loi: Thu muc export baseline da ton tai, tu choi ghi de!"
    exit 1
  fi
  mkdir -p build/baseline/src
  mkdir firmware/esp32s3/CameraWebServerTest/build/baseline
  git archive e92867eecf5eaad308ab1a222069de07d964e6fb firmware/esp32s3/CameraWebServerTest | tar -x -C build/baseline/src/
  cp firmware/esp32s3/CameraWebServerTest/secrets.h build/baseline/src/firmware/esp32s3/CameraWebServerTest/
  "$ARDUINO_CLI" compile --fqbn esp32:esp32:esp32s3:PSRAM=opi --warnings all --export-binaries --output-dir firmware/esp32s3/CameraWebServerTest/build/baseline build/baseline/src/firmware/esp32s3/CameraWebServerTest
  ```
- **PowerShell:**
  ```powershell
  $ARDUINO_CLI = "C:\Users\bestp\AppData\Local\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
  if (Test-Path "firmware\esp32s3\CameraWebServerTest\build\baseline") {
      throw "Loi: Thu muc export baseline da ton tai, tu choi ghi de!"
  }
  New-Item -ItemType Directory -Force -Path build\baseline\src | Out-Null
  New-Item -ItemType Directory -Path firmware\esp32s3\CameraWebServerTest\build\baseline | Out-Null
  git archive e92867eecf5eaad308ab1a222069de07d964e6fb firmware/esp32s3/CameraWebServerTest | tar -x -C build/baseline/src/
  Copy-Item firmware\esp32s3\CameraWebServerTest\secrets.h build\baseline\src\firmware\esp32s3\CameraWebServerTest\
  & $ARDUINO_CLI compile --fqbn esp32:esp32:esp32s3:PSRAM=opi --warnings all --export-binaries --output-dir firmware\esp32s3\CameraWebServerTest\build\baseline build\baseline\src\firmware\esp32s3\CameraWebServerTest
  ```
*(Ghi chú: Binary baseline này tái build từ commit main, lưu làm đối chứng, chưa chứng minh trùng firmware đang có sẵn trên bo).*

### Bước 2.2: Biên dịch firmware Q6 từ nhánh hiện hành
Biên dịch firmware Q6 ra thư mục `build/q6/`:

- **Git Bash:**
  ```bash
  if [ -e "firmware/esp32s3/CameraWebServerTest/build/q6" ]; then
    echo "Loi: Thu muc export q6 da ton tai, tu choi ghi de!"
    exit 1
  fi
  mkdir firmware/esp32s3/CameraWebServerTest/build/q6
  "$ARDUINO_CLI" compile --fqbn esp32:esp32:esp32s3:PSRAM=opi --warnings all --export-binaries --output-dir firmware/esp32s3/CameraWebServerTest/build/q6 firmware/esp32s3/CameraWebServerTest
  ```
- **PowerShell:**
  ```powershell
  if (Test-Path "firmware\esp32s3\CameraWebServerTest\build\q6") {
      throw "Loi: Thu muc export q6 da ton tai, tu choi ghi de!"
  }
  New-Item -ItemType Directory -Path firmware\esp32s3\CameraWebServerTest\build\q6 | Out-Null
  & $ARDUINO_CLI compile --fqbn esp32:esp32:esp32s3:PSRAM=opi --warnings all --export-binaries --output-dir firmware\esp32s3\CameraWebServerTest\build\q6 firmware\esp32s3\CameraWebServerTest
  ```

### Bước 2.3: Tính SHA-256 đầy đủ, Niêm phong Bộ Artifact Nghiệm thu Bất biến và Lưu Manifest (R13)
Tính mã băm SHA-256 (64 hex) của binary Q6 và binary baseline, lưu bộ artifact độc quyền theo phiên và lưu manifest:

- **Git Bash:**
  ```bash
  COMMIT_SHA=$(git rev-parse HEAD)
  BUILD_BIN_SHA=$(sha256sum firmware/esp32s3/CameraWebServerTest/build/q6/CameraWebServerTest.ino.bin | awk '{print $1}')
  BASELINE_BIN_SHA=$(sha256sum firmware/esp32s3/CameraWebServerTest/build/baseline/CameraWebServerTest.ino.bin | awk '{print $1}')

  # R13: Niem phong bo artifact nghiem thu vao thu muc doc quyen
  ARCHIVE_DIR="build/c5a-artifacts/archive_$(date +%Y%m%d_%H%M%S)_q6"
  if [ -e "$ARCHIVE_DIR" ]; then
    echo "Loi: Thu muc bo luu $ARCHIVE_DIR da ton tai, tu choi ghi de!"
    exit 1
  fi
  mkdir -p build/c5a-artifacts
  mkdir "$ARCHIVE_DIR"

  # Nguon boot_app0.bin tu core Arduino-ESP32 3.3.11
  BOOT_APP0_SRC=""
  for p in "${LOCALAPPDATA//\\//}/Arduino15/packages/esp32/hardware/esp32/3.3.11/tools/partitions/boot_app0.bin" \
           "${USERPROFILE//\\//}/AppData/Local/Arduino15/packages/esp32/hardware/esp32/3.3.11/tools/partitions/boot_app0.bin" \
           "$LOCALAPPDATA/Arduino15/packages/esp32/hardware/esp32/3.3.11/tools/partitions/boot_app0.bin" \
           "$USERPROFILE/AppData/Local/Arduino15/packages/esp32/hardware/esp32/3.3.11/tools/partitions/boot_app0.bin" \
           "$HOME/AppData/Local/Arduino15/packages/esp32/hardware/esp32/3.3.11/tools/partitions/boot_app0.bin"; do
    if [ -f "$p" ]; then
      BOOT_APP0_SRC="$p"
      break
    fi
  done

  # Kiem tra 4 tep artifact bat buoc (R13), khong phu thuoc baseline
  Q6_BL="firmware/esp32s3/CameraWebServerTest/build/q6/CameraWebServerTest.ino.bootloader.bin"
  Q6_PT="firmware/esp32s3/CameraWebServerTest/build/q6/CameraWebServerTest.ino.partitions.bin"
  Q6_APP="firmware/esp32s3/CameraWebServerTest/build/q6/CameraWebServerTest.ino.bin"
  if [ ! -f "$Q6_BL" ] || [ ! -f "$Q6_PT" ] || [ ! -f "$Q6_APP" ]; then
    echo "LOI: Thieu tep build bat buoc trong bo q6!"
    exit 1
  fi
  if [ -z "$BOOT_APP0_SRC" ] || [ ! -f "$BOOT_APP0_SRC" ]; then
    echo "LOI: Khong tim thay boot_app0.bin tu Arduino15 core!"
    exit 1
  fi

  if [ -n "$BOOT_APP0_SRC" ] && [ -f "$BOOT_APP0_SRC" ]; then
    cp "$BOOT_APP0_SRC" "$ARCHIVE_DIR/boot_app0.bin"
  fi

  for f in CameraWebServerTest.ino.bootloader.bin CameraWebServerTest.ino.partitions.bin CameraWebServerTest.ino.bin; do
    src="firmware/esp32s3/CameraWebServerTest/build/q6/$f"
    if [ -f "$src" ]; then
      cp "$src" "$ARCHIVE_DIR/"
    fi
  done

  BOOTLOADER_SHA=""
  BOOTLOADER_SIZE=0
  if [ -f "$ARCHIVE_DIR/CameraWebServerTest.ino.bootloader.bin" ]; then
    BOOTLOADER_SHA=$(sha256sum "$ARCHIVE_DIR/CameraWebServerTest.ino.bootloader.bin" | awk '{print $1}')
    BOOTLOADER_SIZE=$(wc -c < "$ARCHIVE_DIR/CameraWebServerTest.ino.bootloader.bin" | tr -d ' ')
  fi

  PARTITIONS_SHA=""
  PARTITIONS_SIZE=0
  if [ -f "$ARCHIVE_DIR/CameraWebServerTest.ino.partitions.bin" ]; then
    PARTITIONS_SHA=$(sha256sum "$ARCHIVE_DIR/CameraWebServerTest.ino.partitions.bin" | awk '{print $1}')
    PARTITIONS_SIZE=$(wc -c < "$ARCHIVE_DIR/CameraWebServerTest.ino.partitions.bin" | tr -d ' ')
  fi

  BOOT_APP0_SHA=""
  BOOT_APP0_SIZE=0
  if [ -f "$ARCHIVE_DIR/boot_app0.bin" ]; then
    BOOT_APP0_SHA=$(sha256sum "$ARCHIVE_DIR/boot_app0.bin" | awk '{print $1}')
    BOOT_APP0_SIZE=$(wc -c < "$ARCHIVE_DIR/boot_app0.bin" | tr -d ' ')
  fi

  APP_SHA=""
  APP_SIZE=0
  if [ -f "$ARCHIVE_DIR/CameraWebServerTest.ino.bin" ]; then
    APP_SHA=$(sha256sum "$ARCHIVE_DIR/CameraWebServerTest.ino.bin" | awk '{print $1}')
    APP_SIZE=$(wc -c < "$ARCHIVE_DIR/CameraWebServerTest.ino.bin" | tr -d ' ')
  fi

  if [ -f "$ARCHIVE_DIR/CameraWebServerTest.ino.bootloader.bin" ] && [ -f "$ARCHIVE_DIR/CameraWebServerTest.ino.partitions.bin" ] && [ -f "$ARCHIVE_DIR/boot_app0.bin" ] && [ -f "$ARCHIVE_DIR/CameraWebServerTest.ino.bin" ]; then
    (cd "$ARCHIVE_DIR" && sha256sum CameraWebServerTest.ino.bootloader.bin CameraWebServerTest.ino.partitions.bin boot_app0.bin CameraWebServerTest.ino.bin > SHA256SUMS)
  fi

  cat <<EOF > "$SESSION_DIR/manifest.json"
  {
    "session_dir": "$SESSION_DIR",
    "git_commit": "$COMMIT_SHA",
    "fqbn": "esp32:esp32:esp32s3:PSRAM=opi",
    "esp32_core_version": "3.3.11",
    "binary_path": "firmware/esp32s3/CameraWebServerTest/build/q6/CameraWebServerTest.ino.bin",
    "binary_sha256": "$BUILD_BIN_SHA",
    "baseline_source_commit": "e92867eecf5eaad308ab1a222069de07d964e6fb",
    "baseline_binary_path": "firmware/esp32s3/CameraWebServerTest/build/baseline/CameraWebServerTest.ino.bin",
    "baseline_binary_sha256": "$BASELINE_BIN_SHA",
    "baseline_note": "baseline tái build từ main, chưa chứng minh trùng firmware trên bo",
    "artifact_archive_dir": "$ARCHIVE_DIR",
    "artifacts": [
      {"name": "bootloader", "offset": "0x00000000", "file": "CameraWebServerTest.ino.bootloader.bin", "sha256": "$BOOTLOADER_SHA", "size": $BOOTLOADER_SIZE},
      {"name": "partitions", "offset": "0x00008000", "file": "CameraWebServerTest.ino.partitions.bin", "sha256": "$PARTITIONS_SHA", "size": $PARTITIONS_SIZE},
      {"name": "boot_app0", "offset": "0x0000e000", "file": "boot_app0.bin", "sha256": "$BOOT_APP0_SHA", "size": $BOOT_APP0_SIZE},
      {"name": "app", "offset": "0x00010000", "file": "CameraWebServerTest.ino.bin", "sha256": "$APP_SHA", "size": $APP_SIZE}
    ]
  }
EOF
  cp "$SESSION_DIR/manifest.json" "$ARCHIVE_DIR/manifest.json"
  echo "Manifest da tao tai $SESSION_DIR/manifest.json va niem phong tai $ARCHIVE_DIR"
  ```
- **PowerShell:**
  ```powershell
  $COMMIT_SHA = (git rev-parse HEAD).Trim()
  $BUILD_BIN_SHA = (Get-FileHash firmware\esp32s3\CameraWebServerTest\build\q6\CameraWebServerTest.ino.bin -Algorithm SHA256).Hash.ToLower()
  $BASELINE_BIN_SHA = (Get-FileHash firmware\esp32s3\CameraWebServerTest\build\baseline\CameraWebServerTest.ino.bin -Algorithm SHA256).Hash.ToLower()

  # R13: Niem phong bo artifact nghiem thu vao thu muc doc quyen
  $ARCHIVE_DIR = "build\c5a-artifacts\archive_$(Get-Date -Format yyyyMMdd_HHmmss)_q6"
  if (Test-Path $ARCHIVE_DIR) {
      throw "Loi: Thu muc bo luu $ARCHIVE_DIR da ton tai, tu choi ghi de!"
  }
  if (-not (Test-Path "build\c5a-artifacts")) {
      New-Item -ItemType Directory -Path "build\c5a-artifacts" | Out-Null
  }
  New-Item -ItemType Directory -Path $ARCHIVE_DIR | Out-Null

  # Nguon boot_app0.bin tu core Arduino-ESP32 3.3.11
  $BOOT_APP0_SRC = "$env:LOCALAPPDATA\Arduino15\packages\esp32\hardware\esp32\3.3.11\tools\partitions\boot_app0.bin"

  # Kiem tra 4 tep artifact bat buoc (R13), khong phu thuoc baseline
  $Q6_BL = "firmware\esp32s3\CameraWebServerTest\build\q6\CameraWebServerTest.ino.bootloader.bin"
  $Q6_PT = "firmware\esp32s3\CameraWebServerTest\build\q6\CameraWebServerTest.ino.partitions.bin"
  $Q6_APP = "firmware\esp32s3\CameraWebServerTest\build\q6\CameraWebServerTest.ino.bin"
  if (-not (Test-Path -LiteralPath $Q6_BL -PathType Leaf) -or -not (Test-Path -LiteralPath $Q6_PT -PathType Leaf) -or -not (Test-Path -LiteralPath $Q6_APP -PathType Leaf)) {
      throw "LOI: Thieu tep build bat buoc trong bo q6!"
  }
  if (-not (Test-Path -LiteralPath $BOOT_APP0_SRC -PathType Leaf)) {
      throw "LOI: Khong tim thay boot_app0.bin tu Arduino15 core!"
  }

  if (Test-Path $BOOT_APP0_SRC) {
      Copy-Item $BOOT_APP0_SRC "$ARCHIVE_DIR\boot_app0.bin"
  }

  $build_files = @("CameraWebServerTest.ino.bootloader.bin", "CameraWebServerTest.ino.partitions.bin", "CameraWebServerTest.ino.bin")
  foreach ($f in $build_files) {
      $src = "firmware\esp32s3\CameraWebServerTest\build\q6\$f"
      if (Test-Path $src) {
          Copy-Item $src "$ARCHIVE_DIR\"
      }
  }

  $bootloader_file = "$ARCHIVE_DIR\CameraWebServerTest.ino.bootloader.bin"
  $partitions_file = "$ARCHIVE_DIR\CameraWebServerTest.ino.partitions.bin"
  $boot_app0_file = "$ARCHIVE_DIR\boot_app0.bin"
  $app_file = "$ARCHIVE_DIR\CameraWebServerTest.ino.bin"

  $bootloader_sha = if (Test-Path $bootloader_file) { (Get-FileHash $bootloader_file -Algorithm SHA256).Hash.ToLower() } else { "" }
  $bootloader_size = if (Test-Path $bootloader_file) { (Get-Item $bootloader_file).Length } else { 0 }

  $partitions_sha = if (Test-Path $partitions_file) { (Get-FileHash $partitions_file -Algorithm SHA256).Hash.ToLower() } else { "" }
  $partitions_size = if (Test-Path $partitions_file) { (Get-Item $partitions_file).Length } else { 0 }

  $boot_app0_sha = if (Test-Path $boot_app0_file) { (Get-FileHash $boot_app0_file -Algorithm SHA256).Hash.ToLower() } else { "" }
  $boot_app0_size = if (Test-Path $boot_app0_file) { (Get-Item $boot_app0_file).Length } else { 0 }

  $app_sha = if (Test-Path $app_file) { (Get-FileHash $app_file -Algorithm SHA256).Hash.ToLower() } else { "" }
  $app_size = if (Test-Path $app_file) { (Get-Item $app_file).Length } else { 0 }

  $manifest = [ordered]@{
      session_dir = $SESSION_DIR
      git_commit = $COMMIT_SHA
      fqbn = "esp32:esp32:esp32s3:PSRAM=opi"
      esp32_core_version = "3.3.11"
      binary_path = "firmware/esp32s3/CameraWebServerTest/build/q6/CameraWebServerTest.ino.bin"
      binary_sha256 = $BUILD_BIN_SHA
      baseline_source_commit = "e92867eecf5eaad308ab1a222069de07d964e6fb"
      baseline_binary_path = "firmware/esp32s3/CameraWebServerTest/build/baseline/CameraWebServerTest.ino.bin"
      baseline_binary_sha256 = $BASELINE_BIN_SHA
      baseline_note = "baseline tái build từ main, chưa chứng minh trùng firmware trên bo"
      artifact_archive_dir = $ARCHIVE_DIR
      artifacts = @(
          [ordered]@{ name = "bootloader"; offset = "0x00000000"; file = "CameraWebServerTest.ino.bootloader.bin"; sha256 = $bootloader_sha; size = $bootloader_size }
          [ordered]@{ name = "partitions"; offset = "0x00008000"; file = "CameraWebServerTest.ino.partitions.bin"; sha256 = $partitions_sha; size = $partitions_size }
          [ordered]@{ name = "boot_app0"; offset = "0x0000e000"; file = "boot_app0.bin"; sha256 = $boot_app0_sha; size = $boot_app0_size }
          [ordered]@{ name = "app"; offset = "0x00010000"; file = "CameraWebServerTest.ino.bin"; sha256 = $app_sha; size = $app_size }
      )
  }
  $manifest | ConvertTo-Json -Depth 5 | Set-Content "$SESSION_DIR\manifest.json" -Encoding UTF8
  Copy-Item "$SESSION_DIR\manifest.json" "$ARCHIVE_DIR\manifest.json"
  Write-Host "Manifest da tao tai $SESSION_DIR\manifest.json va niem phong tai $ARCHIVE_DIR"
  ```

### Bước 2.4: Nạp firmware Q6 lên bo và Lưu log Serial (R09)
*(Nhánh Vòng 8: Nếu bo mạch đang chạy đúng bản firmware Q6 ngày 04/10 đã đối chiếu khớp với `log_4-10.docx` với SHA app `e9dcc182af2e1c48a853c2c118878d5a96feb5bbe17c67f95ad6f68b2b847b3c`, Tester/người dùng không bắt buộc nạp lại hay chụp lại 60 ảnh Q6-T9, mà chuyển sang thực hiện đo bổ sung Ca 3 tại Mục 5.3. Nếu cần nạp lại để xác định firmware cho bộ đo RST mới, thực hiện nạp từ bộ artifact đã lưu ở Bước 2.3 và lưu đầy đủ log upload dưới đây).*

Nạp firmware Q6 (thay `<PORT>` bằng cổng COM thực tế, ví dụ `COM4` hoặc `COM9`):

- **Git Bash:**
  ```bash
  # Kiem tra SHA-256 cua bo artifact niem phong truoc khi nap
  echo "Kiem tra SHA-256 truoc khi nap:"
  for f in CameraWebServerTest.ino.bin CameraWebServerTest.ino.bootloader.bin CameraWebServerTest.ino.partitions.bin boot_app0.bin; do
    if [ ! -f "$ARCHIVE_DIR/$f" ]; then
      echo "LOI: Thieu tep artifact niem phong $ARCHIVE_DIR/$f!"
      exit 1
    fi
  done
  sha256sum "$ARCHIVE_DIR/CameraWebServerTest.ino.bin" "$ARCHIVE_DIR/CameraWebServerTest.ino.bootloader.bin" "$ARCHIVE_DIR/CameraWebServerTest.ino.partitions.bin" "$ARCHIVE_DIR/boot_app0.bin"

  # Doi chieu voi SHA256SUMS hoac manifest.json da niem phong
  if [ -f "$ARCHIVE_DIR/SHA256SUMS" ]; then
    (cd "$ARCHIVE_DIR" && sha256sum -c SHA256SUMS >/dev/null 2>&1)
    if [ $? -ne 0 ]; then
      echo "LOI: Checksum SHA-256 khong khop voi ban niem phong! Tu choi nap!"
      exit 1
    fi
  elif [ -f "$ARCHIVE_DIR/manifest.json" ]; then
    python -c '
import json, hashlib, sys, os
arch = sys.argv[1]
with open(os.path.join(arch, "manifest.json"), "r", encoding="utf-8-sig") as f:
    m = json.load(f)
for a in m.get("artifacts", []):
    fp = os.path.join(arch, a["file"])
    if not os.path.isfile(fp):
        sys.exit(1)
    if hashlib.sha256(open(fp, "rb").read()).hexdigest().lower() != a.get("sha256", "").lower():
        sys.exit(1)
' "$ARCHIVE_DIR"
    if [ $? -ne 0 ]; then
      echo "LOI: Checksum SHA-256 khong khop voi manifest.json! Tu choi nap!"
      exit 1
    fi
  else
    echo "LOI: Bo luu thieu ca SHA256SUMS va manifest.json! Tu choi nap!"
    exit 1
  fi

  # Nap firmware tu bo artifact da niem phong, giu nguyen exit code cua arduino-cli
  set -o pipefail
  "$ARDUINO_CLI" upload -p <PORT> --fqbn esp32:esp32:esp32s3:PSRAM=opi --input-dir "$ARCHIVE_DIR" firmware/esp32s3/CameraWebServerTest 2>&1 | tee "$SESSION_DIR/upload_output.log"
  UPLOAD_RC=${PIPESTATUS[0]}
  if [ $UPLOAD_RC -ne 0 ]; then
    echo "LOI: Nap firmware that bai voi exit code $UPLOAD_RC!"
    exit $UPLOAD_RC
  fi
  ```
- **PowerShell:**
  ```powershell
  # Kiem tra su ton tai va SHA-256 cua bo artifact niem phong truoc khi nap
  $artifacts = @("CameraWebServerTest.ino.bin", "CameraWebServerTest.ino.bootloader.bin", "CameraWebServerTest.ino.partitions.bin", "boot_app0.bin")
  foreach ($f in $artifacts) {
      if (-not (Test-Path "$ARCHIVE_DIR\$f")) {
          throw "LOI: Thieu tep artifact $ARCHIVE_DIR\$f!"
      }
  }

  if (Test-Path "$ARCHIVE_DIR\SHA256SUMS") {
      $lines = Get-Content "$ARCHIVE_DIR\SHA256SUMS"
      foreach ($line in $lines) {
          if ($line -match '^([0-9a-fA-F]{64})\s+(.+)$') {
              $exp = $matches[1].ToLower()
              $fn = $matches[2].Trim()
              $fp = Join-Path $ARCHIVE_DIR $fn
              $actual = (Get-FileHash $fp -Algorithm SHA256).Hash.ToLower()
              if ($actual -ne $exp) {
                  throw "LOI: Checksum SHA-256 cua $fn khong khop voi SHA256SUMS!"
              }
          }
      }
  } elseif (Test-Path "$ARCHIVE_DIR\manifest.json") {
      $manifest = Get-Content "$ARCHIVE_DIR\manifest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
      foreach ($art in $manifest.artifacts) {
          $fp = Join-Path $ARCHIVE_DIR $art.file
          $actual = (Get-FileHash $fp -Algorithm SHA256).Hash.ToLower()
          if ($actual -ne $art.sha256.ToLower()) {
              throw "LOI: Checksum SHA-256 cua $($art.file) khong khop voi manifest.json!"
          }
      }
  } else {
      throw "LOI: Bo luu thieu ca SHA256SUMS va manifest.json!"
  }

  # Nap firmware tu bo artifact da niem phong va kiem tra exit code
  & $ARDUINO_CLI upload -p <PORT> --fqbn esp32:esp32:esp32s3:PSRAM=opi --input-dir "$ARCHIVE_DIR" firmware\esp32s3\CameraWebServerTest 2>&1 | Tee-Object -FilePath "$SESSION_DIR\upload_output.log"
  $UPLOAD_RC = $LASTEXITCODE
  if ($UPLOAD_RC -ne 0) {
      Write-Error "LOI: Nap firmware that bai voi exit code $UPLOAD_RC!"
      exit $UPLOAD_RC
  }
  ```
- Sau khi nạp thành công, mở Serial Monitor ở tốc độ baud 115200 và chép lưu toàn bộ log khởi động vào tệp:
  `$SESSION_DIR/boot_serial.log`.
- **Thấy gì là đúng:**
  - Biên dịch báo `rc 0`, 0 cảnh báo.
  - Quá trình upload báo `100% Hash of data verified`.
  - Serial Monitor in cấu hình thực:
    ```text
    Camera Init OK: fb_count=1, grab_mode=1, fb_location=0
    WiFi connected, IP 192.168.1.xxx
    Boot ID: <32 hex characters>
    Camera Ready! Use 'http://192.168.1.xxx' to connect
    ```
- **Nếu sai:**
  - Nếu thiếu dòng `fb_count=1, grab_mode=1` -> kiểm tra xem đã build đúng từ thư mục `build/q6` chưa.
  - Nếu `Camera init failed` -> kiểm tra cáp FPC camera và tuỳ chọn `PSRAM=opi`.

---

## 3. Kiểm tra bằng Selftest Mock (Kiểm chứng công cụ PC)

Trước khi đo với bo thật, chạy selftest tự động của probe để xác nhận parser, tính toán timestamp, và kiểm tra kịch bản ngoại lệ trên host:

- **Git Bash:**
  ```bash
  .venv/Scripts/python.exe pc/fresh_capture_probe.py --selftest
  ```
- **PowerShell:**
  ```powershell
  .\.venv\Scripts\python.exe pc\fresh_capture_probe.py --selftest
  ```
- **Thấy gì là đúng:** Toàn bộ 10 kịch bản đạt `PASS`.

---

## 4. Kiểm chứng Q6-T9: 3 lượt x 20 Fresh Capture (SVGA q20), Đo Heap và Đối chiếu Profile chỉ đọc

Theo Quyết định D044:
- Profile chính thức nghiệm thu Q6-T9 là **`cam_SVGA_q20_20260928`** (800×600, quality 20).
- Đường dẫn: `data/calibration/camera_profiles/cam_SVGA_q20_20260928.json` (SHA-256: `5c32b27b4e52a2518cba01caee03d19d95db1c31a0e8dde4fa315635ad85dbe6`).
- Chuỗi thành công kỳ vọng từ `pc/camera_profile.py`: `Ho so khop bo: cam_SVGA_q20_20260928`.
- Khảo sát heap: Lấy snapshot `/status` trước và sau mỗi lượt (tổng 6 snapshot/3 cặp), trích xuất `heap_internal_free_bytes` và `heap_psram_free_bytes`, tính delta. Đây là số liệu khảo sát, không đặt ngưỡng "không leak".
- Đối chiếu profile sau mỗi lượt: **Chỉ đọc snapshot `/status`**, chạy `diff_controls` và `compare_registers`, **tuyệt đối không gửi lệnh `/control` hay `--verify` áp lại**.

- **Ở đâu:** Terminal tại thư mục gốc `d:/scanner3d`.
- **Làm gì:**

### Bước 4.1: Kiểm tra Hash Profile và Sao chép vào thư mục phiên
- **Git Bash:**
  ```bash
  PROF_SRC="data/calibration/camera_profiles/cam_SVGA_q20_20260928.json"
  PROF_SHA=$(sha256sum "$PROF_SRC" | awk '{print $1}')
  EXPECTED_SHA="5c32b27b4e52a2518cba01caee03d19d95db1c31a0e8dde4fa315635ad85dbe6"
  if [ "$PROF_SHA" != "$EXPECTED_SHA" ]; then
    echo "LOI: SHA-256 profile khong khop! Got: $PROF_SHA, Expected: $EXPECTED_SHA"
    exit 1
  fi
  cp "$PROF_SRC" "$SESSION_DIR/cam_SVGA_q20_20260928.json"
  echo "Profile SVGA q20 hop le, da sao chep vao $SESSION_DIR"
  ```
- **PowerShell:**
  ```powershell
  $PROF_SRC = "data\calibration\camera_profiles\cam_SVGA_q20_20260928.json"
  $PROF_SHA = (Get-FileHash $PROF_SRC -Algorithm SHA256).Hash.ToLower()
  $EXPECTED_SHA = "5c32b27b4e52a2518cba01caee03d19d95db1c31a0e8dde4fa315635ad85dbe6"
  if ($PROF_SHA -ne $EXPECTED_SHA) {
      Write-Error "LOI: SHA-256 profile khong khop! Got: $PROF_SHA, Expected: $EXPECTED_SHA"
      exit 1
  }
  Copy-Item $PROF_SRC "$SESSION_DIR\cam_SVGA_q20_20260928.json"
  Write-Host "Profile SVGA q20 hop le, da sao chep vao $SESSION_DIR"
  ```

### Bước 4.2: Áp Profile C2 lên Bo trước phiên đo
- **Git Bash:**
  ```bash
  .venv/Scripts/python.exe pc/camera_profile.py --host <IP_ESP32> --verify --profile "$PROF_SRC"
  ```
- **PowerShell:**
  ```powershell
  .\.venv\Scripts\python.exe pc\camera_profile.py --host <IP_ESP32> --verify --profile $PROF_SRC
  ```
- **Thấy gì là đúng:** Kết quả in `Ho so khop bo: cam_SVGA_q20_20260928`. Đóng toàn bộ tab trình duyệt hoặc stream nếu có.

### Bước 4.3: Thực hiện 3 lượt x 20 Fresh Capture và Khảo sát Heap

Lặp lại quy trình dưới đây cho từng lượt $K \in \{1, 2, 3\}$. Trước khi thực hiện mỗi lượt, thiết lập biến $K$ tương ứng:
- Cho Lượt 1:
  * Git Bash:
    ```bash
    K=1
    ```
  * PowerShell:
    ```powershell
    $K = 1
    ```
- Cho Lượt 2: chạy `K=2` (PowerShell: `$K = 2`).
- Cho Lượt 3: chạy `K=3` (PowerShell: `$K = 3`).

1. **Lấy Snapshot `/status` trước lượt đo (Snapshot Trước):**
   - **Git Bash:**
     ```bash
     date -u +"%Y-%m-%dT%H:%M:%SZ" > "$SESSION_DIR/status_before_run${K}_time.txt"
     curl -s "http://<IP_ESP32>/status" -o "$SESSION_DIR/status_before_run${K}.json"
     ```
   - **PowerShell:**
     ```powershell
     (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") | Set-Content "$SESSION_DIR\status_before_run${K}_time.txt" -Encoding UTF8
     Invoke-WebRequest -Uri "http://<IP_ESP32>/status" -OutFile "$SESSION_DIR\status_before_run${K}.json"
     ```

2. **Chạy Probe chụp 20 ảnh (thay `<IP_ESP32>`):**
   - **Git Bash:**
     ```bash
     .venv/Scripts/python.exe pc/fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 20 --interval 0.2 --output "$SESSION_DIR/probe_q6_t9_run${K}" --commit "$COMMIT_SHA" --build-sha "$BUILD_BIN_SHA"
     ```
   - **PowerShell:**
     ```powershell
     .\.venv\Scripts\python.exe pc\fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 20 --interval 0.2 --output "$SESSION_DIR\probe_q6_t9_run${K}" --commit $COMMIT_SHA --build-sha $BUILD_BIN_SHA
     ```

3. **Kiểm tra kích thước JPEG thật (800×600 SVGA) của 20 ảnh vừa chụp trong lượt:**
   - **Git Bash:**
     ```bash
     .venv/Scripts/python.exe -c "
     import glob, sys
     from PIL import Image
     files = sorted(glob.glob('$SESSION_DIR/probe_q6_t9_run${K}/frame_*.jpg'))
     if len(files) != 20:
         print('LOI: Chi tim thay %d/20 anh JPEG!' % len(files))
         sys.exit(1)
     for f in files:
         with Image.open(f) as img:
             w, h = img.size
             if (w, h) != (800, 600):
                 print('LOI: Anh %s co kich thuoc %dx%d (yeu cau 800x600 SVGA)!' % (f, w, h))
                 sys.exit(1)
     print('Luot ${K}: Toan bo %d anh JPEG deu dung kich thuoc 800x600 SVGA.' % len(files))
     "
     ```
   - **PowerShell:**
     ```powershell
     .\.venv\Scripts\python.exe -c "
     import glob, sys
     from PIL import Image
     files = sorted(glob.glob('$SESSION_DIR/probe_q6_t9_run${K}/frame_*.jpg'))
     if len(files) != 20:
         print('LOI: Chi tim thay %d/20 anh JPEG!' % len(files))
         sys.exit(1)
     for f in files:
         with Image.open(f) as img:
             w, h = img.size
             if (w, h) != (800, 600):
                 print('LOI: Anh %s co kich thuoc %dx%d (yeu cau 800x600 SVGA)!' % (f, w, h))
                 sys.exit(1)
     print('Luot ${K}: Toan bo %d anh JPEG deu dung kich thuoc 800x600 SVGA.' % len(files))
     "
     ```

4. **Lấy Snapshot `/status` sau lượt đo (Snapshot Sau):**
   - **Git Bash:**
     ```bash
     date -u +"%Y-%m-%dT%H:%M:%SZ" > "$SESSION_DIR/status_after_run${K}_time.txt"
     curl -s "http://<IP_ESP32>/status" -o "$SESSION_DIR/status_after_run${K}.json"
     ```
   - **PowerShell:**
     ```powershell
     (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") | Set-Content "$SESSION_DIR\status_after_run${K}_time.txt" -Encoding UTF8
     Invoke-WebRequest -Uri "http://<IP_ESP32>/status" -OutFile "$SESSION_DIR\status_after_run${K}.json"
     ```

5. **Trích xuất Telemetry Heap và ghi nhận Delta khảo sát:**
   - **Git Bash:**
     ```bash
     .venv/Scripts/python.exe -c "
     import datetime, json
     b = json.load(open('$SESSION_DIR/status_before_run${K}.json'))
     a = json.load(open('$SESSION_DIR/status_after_run${K}.json'))
     d_int = a['heap_internal_free_bytes'] - b['heap_internal_free_bytes']
     d_psr = a['heap_psram_free_bytes'] - b['heap_psram_free_bytes']
     print('Luot ${K} - Heap Internal: %d -> %d (delta: %d bytes)' % (b['heap_internal_free_bytes'], a['heap_internal_free_bytes'], d_int))
     print('Luot ${K} - Heap PSRAM:    %d -> %d (delta: %d bytes)' % (b['heap_psram_free_bytes'], a['heap_psram_free_bytes'], d_psr))
     survey = {
         'run': '${K}',
         'timestamp_pc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'heap_internal_before': b['heap_internal_free_bytes'],
         'heap_internal_after': a['heap_internal_free_bytes'],
         'heap_internal_delta': d_int,
         'heap_psram_before': b['heap_psram_free_bytes'],
         'heap_psram_after': a['heap_psram_free_bytes'],
         'heap_psram_delta': d_psr,
     }
     with open('$SESSION_DIR/heap_survey_run${K}.json', 'w', encoding='utf-8') as f:
         json.dump(survey, f, indent=2)
     "
     ```
   - **PowerShell:**
     ```powershell
     $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
     $b = Get-Content "$SESSION_DIR\status_before_run${K}.json" -Raw | ConvertFrom-Json
     $a = Get-Content "$SESSION_DIR\status_after_run${K}.json" -Raw | ConvertFrom-Json
     $d_int = $a.heap_internal_free_bytes - $b.heap_internal_free_bytes
     $d_psr = $a.heap_psram_free_bytes - $b.heap_psram_free_bytes
     Write-Host "Luot ${K} - Heap Internal: $($b.heap_internal_free_bytes) -> $($a.heap_internal_free_bytes) (delta: $d_int bytes)"
     Write-Host "Luot ${K} - Heap PSRAM:    $($b.heap_psram_free_bytes) -> $($a.heap_psram_free_bytes) (delta: $d_psr bytes)"
     $survey = [ordered]@{
         run = "${K}"
         timestamp_pc = $now
         heap_internal_before = $b.heap_internal_free_bytes
         heap_internal_after = $a.heap_internal_free_bytes
         heap_internal_delta = $d_int
         heap_psram_before = $b.heap_psram_free_bytes
         heap_psram_after = $a.heap_psram_free_bytes
         heap_psram_delta = $d_psr
     }
     $survey | ConvertTo-Json -Depth 5 | Set-Content "$SESSION_DIR\heap_survey_run${K}.json" -Encoding UTF8
     ```

6. **Đối chiếu Snapshot Profile Sau đo (CHỈ ĐỌC, KHÔNG GỌI /control):**
   - Chạy kiểm tra chỉ đọc bằng script so sánh trực tiếp trên `$SESSION_DIR/status_after_run${K}.json`:
     - **Git Bash:**
       ```bash
       .venv/Scripts/python.exe -c "
       import json, sys
       from pc.camera_profile import diff_controls, compare_registers
       prof = json.load(open('$SESSION_DIR/cam_SVGA_q20_20260928.json'))
       st = json.load(open('$SESSION_DIR/status_after_run${K}.json'))
       ok_c, m_c = diff_controls(st, prof['framesize'], prof['quality'], prof['controls'])
       ok_r, m_r = compare_registers(prof['expected_registers'], st, prof['expected_registers'].keys())
       if ok_c and ok_r:
           print('Luot ${K}: Doi chieu snapshot status khop profile 100% (Khong troi cau hinh)')
       else:
           print('Luot ${K}: TROI CAU HINH! Mismatches:', m_c, m_r)
           sys.exit(1)
       "
       ```
     - **PowerShell:**
       ```powershell
       .\.venv\Scripts\python.exe -c "
       import json, sys
       from pc.camera_profile import diff_controls, compare_registers
       prof = json.load(open('$SESSION_DIR/cam_SVGA_q20_20260928.json'))
       st = json.load(open('$SESSION_DIR/status_after_run${K}.json'))
       ok_c, m_c = diff_controls(st, prof['framesize'], prof['quality'], prof['controls'])
       ok_r, m_r = compare_registers(prof['expected_registers'], st, prof['expected_registers'].keys())
       if ok_c and ok_r:
           print('Luot ${K}: Doi chieu snapshot status khop profile 100% (Khong troi cau hinh)')
       else:
           print('Luot ${K}: TROI CAU HINH! Mismatches:', m_c, m_r)
           sys.exit(1)
       "
       ```

- **Thấy gì là đúng ở Q6-T9:**
  - Cả 3 lượt: probe trả lời `20/20` yêu cầu `HTTP 200 OK`, `Ket luan: PASS`.
  - Toàn bộ ảnh giải mã được độ phân giải **800×600** (SVGA).
  - Frame ID tăng đơn điệu liên tục không có gap (`FRAME_ID_GAP`), Boot ID không đổi qua toàn bộ 3 lượt.
  - Các thư mục `$SESSION_DIR/probe_q6_t9_run*` lưu đủ 20 ảnh `frame_XXXX.jpg`, 20 tệp `headers_XXXX.txt` và `summary.json`.
  - Snapshot status sau mỗi lượt đối chiếu khớp 100% với profile SVGA q20 (controls và 7 thanh ghi).
  - Số liệu heap được lưu đầy đủ vào các tệp snapshot và tệp `$SESSION_DIR/heap_survey_run*.json`.

---

## 5. Kiểm chứng Q6-T10: Loại trừ tranh chấp Mutex và Ngoại lệ mạng (lặp lại ≥ 3 lần mỗi ca)

Thực hiện mỗi ca thử nghiệm lặp lại ít nhất 3 lần (≥ 3 lần). Mỗi lần chạy đều xuất ra thư mục riêng biệt để bảo đảm các lần sau không bị probe từ chối vì thư mục đã tồn tại.

### 5.1. Ca 1: Loại trừ tranh chấp khi `/stream` đang mở (lặp lại 3 lần)

Lặp lại chu kỳ sau cho từng lần $K \in \{1, 2, 3\}$. Trước khi thực hiện mỗi lần, thiết lập biến $K$ tương ứng:
- Cho lần 1:
  * Git Bash:
    ```bash
    K=1
    ```
  * PowerShell:
    ```powershell
    $K = 1
    ```
- Cho lần 2: chạy `K=2` (PowerShell: `$K = 2`).
- Cho lần 3: chạy `K=3` (PowerShell: `$K = 3`).

1. Mở trình duyệt web, truy cập luồng video: `http://<IP_ESP32>:81/stream`.
2. Khi video stream đang chạy, trên Terminal gửi các lệnh thử nghiệm (in và lưu cả HTTP status code lẫn response body với timeout 5 giây vào tệp `$SESSION_DIR/busy_responses_run${K}.txt`):
   - **Git Bash:**
     ```bash
     .venv/Scripts/python.exe -c "
     import requests
     with open('$SESSION_DIR/busy_responses_run${K}.txt', 'w', encoding='utf-8') as f:
         for path in ['/capture', '/bmp', '/control?var=framesize&val=5']:
             try:
                 r = requests.get('http://<IP_ESP32>' + path, timeout=5)
                 line = '%s -> HTTP %d, Body: %s\n' % (path, r.status_code, r.text.strip())
             except Exception as e:
                 line = '%s -> Error: %s\n' % (path, e)
             print(line, end='')
             f.write(line)
     "
     ```
   - **PowerShell:**
     ```powershell
     .\.venv\Scripts\python.exe -c "
     import requests
     with open('$SESSION_DIR/busy_responses_run${K}.txt', 'w', encoding='utf-8') as f:
         for path in ['/capture', '/bmp', '/control?var=framesize&val=5']:
             try:
                 r = requests.get('http://<IP_ESP32>' + path, timeout=5)
                 line = '%s -> HTTP %d, Body: %s\n' % (path, r.status_code, r.text.strip())
             except Exception as e:
                 line = '%s -> Error: %s\n' % (path, e)
             print(line, end='')
             f.write(line)
     "
     ```
3. Chạy probe thử nghiệm chụp trong lúc stream đang giữ khóa, lưu vào thư mục riêng:
   - **Git Bash:**
     ```bash
     .venv/Scripts/python.exe pc/fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 1 --output "$SESSION_DIR/probe_q6_t10_busy_run${K}"
     ```
   - **PowerShell:**
     ```powershell
     .\.venv\Scripts\python.exe pc\fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 1 --output "$SESSION_DIR\probe_q6_t10_busy_run${K}"
     ```
4. **Kiểm tra hồi phục:** Đóng tab trình duyệt stream `/stream`. Chờ 1 giây, sau đó chạy probe với output riêng để xác nhận server phục hồi bình thường:
   - **Git Bash:**
     ```bash
     .venv/Scripts/python.exe pc/fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 1 --output "$SESSION_DIR/probe_q6_t10_busy_recovered_run${K}"
     ```
   - **PowerShell:**
     ```powershell
     .\.venv\Scripts\python.exe pc\fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 1 --output "$SESSION_DIR\probe_q6_t10_busy_recovered_run${K}"
     ```

- **Thấy gì là đúng:**
  - Khi stream mở: các lệnh gọi `/capture`, `/bmp`, `/control` và probe đều nhận HTTP 503 với body `ERROR CAMERA_BUSY_STREAM`.
  - Luồng video stream trên trình duyệt duy trì liên tục, không bị treo hoặc crash.
  - Sau khi đóng tab stream, probe chạy ở lượt hồi phục nhận HTTP 200 OK, kết luận `PASS`.

---

### 5.2. Ca 2: Ngoại lệ ngắt kết nối Wi-Fi / PC giữa lượt (lặp lại 3 lần)

Lặp lại cho từng lần $K \in \{1, 2, 3\}$. Trước khi thực hiện mỗi lần, thiết lập biến $K$ tương ứng:
- Cho lần 1:
  * Git Bash:
    ```bash
    K=1
    ```
  * PowerShell:
    ```powershell
    $K = 1
    ```
- Cho lần 2: chạy `K=2` (PowerShell: `$K = 2`).
- Cho lần 3: chạy `K=3` (PowerShell: `$K = 3`).

1. Chạy probe với 30 request, xuất ra thư mục riêng cho từng lần:
   - **Git Bash:**
     ```bash
     .venv/Scripts/python.exe pc/fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 30 --interval 0.5 --output "$SESSION_DIR/probe_q6_t10_disconnect_run${K}"
     ```
   - **PowerShell:**
     ```powershell
     .\.venv\Scripts\python.exe pc\fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 30 --interval 0.5 --output "$SESSION_DIR\probe_q6_t10_disconnect_run${K}"
     ```
2. Ở request thứ 3 hoặc 4, tắt adapter Wi-Fi trên máy tính hoặc rút dây mạng.
- **Thấy gì là đúng:**
  - Probe phát hiện mất kết nối socket, dừng toàn bộ phiên, kết luận `Ket luan: INVALID`.
  - Toàn bộ ảnh đã nhận thành công trước thời điểm mất mạng được giữ nguyên vẹn trong thư mục output của lần đó.
3. Bật lại Wi-Fi trước khi chạy lần tiếp theo.

---

### 5.3. Ca 3: Phát hiện khởi động lại bo qua nút vật lý RST và Đo Phục hồi Đóng kín (R10, lặp lại 3 lần)

Mỗi lần lặp đều là một chu trình đóng kín: ghi nhận trạng thái Trước RST -> bấm RST khi đang chạy probe -> ghi nhận INVALID và bảo toàn ảnh -> sau khi bo khởi động lại, ghi nhận Boot ID mới, snapshot status HTTP 200 và chụp 1 ảnh phục hồi ở phiên riêng biệt. Quy trình phải hoàn tất đầy đủ cho **cả 3 lần** $K \in \{1, 2, 3\}$, bao gồm cả sau lần thứ 3 (đóng triệt để R10).

> [!IMPORTANT]
> **CẢNH BÁO ỔN ĐỊNH CỔNG COM / SERIAL**: Trong suốt quá trình probe đang chạy, **tuyệt đối không mở/đóng hoặc bật/tắt lại Arduino IDE GUI hay Serial Monitor** trên máy tính, để tránh xung tín hiệu DTR/RTS trên cổng COM gây reset ngoài ý muốn. Thao tác reset duy nhất là nhấn nút vật lý RST trên bo mạch theo đúng chỉ dẫn của từng bước.

Lặp lại chu trình khép kín sau cho từng lần $K \in \{1, 2, 3\}$. Trước khi thực hiện mỗi lần, thiết lập biến $K$ tương ứng:
- Cho lần 1:
  * Git Bash:
    ```bash
    K=1
    ```
  * PowerShell:
    ```powershell
    $K = 1
    ```
- Cho lần 2: chạy `K=2` (PowerShell: `$K = 2`).
- Cho lần 3: chạy `K=3` (PowerShell: `$K = 3`).

1. **Bước 5.3.1: Ghi nhận trạng thái TRƯỚC khi nhấn RST:**
   - Lưu thời điểm PC và snapshot `/status` trước khi reset, đồng thời lưu thông tin phiên cho Terminal 2:
     - **Git Bash:**
       ```bash
       date -u +"%Y-%m-%dT%H:%M:%SZ" > "$SESSION_DIR/status_before_rst${K}_time.txt"
       curl -s "http://<IP_ESP32>/status" -o "$SESSION_DIR/status_before_rst${K}.json"
       mkdir -p docs/logs
       echo "SESSION_DIR=\"$SESSION_DIR\"" > docs/logs/.c5a_session_current
       echo "K=$K" >> docs/logs/.c5a_session_current
       echo "Trang thai truoc RST ${K} da luu."
       ```
     - **PowerShell:**
       ```powershell
       (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") | Set-Content "$SESSION_DIR\status_before_rst${K}_time.txt" -Encoding UTF8
       Invoke-WebRequest -Uri "http://<IP_ESP32>/status" -OutFile "$SESSION_DIR\status_before_rst${K}.json"
       if (-not (Test-Path "docs\logs")) { New-Item -ItemType Directory -Path "docs\logs" | Out-Null }
       "SESSION_DIR=`"$SESSION_DIR`"`nK=$K" | Set-Content "docs\logs\.c5a_session_current" -Encoding UTF8
       Write-Host "Trang thai truoc RST ${K} da luu."
       ```

2. **Bước 5.3.2: Chạy probe và nhấn nút vật lý RST trên bo:**
   - Chạy probe với 15 request, xuất ra thư mục riêng cho từng lần:
     - **Git Bash:**
       ```bash
       .venv/Scripts/python.exe pc/fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 15 --interval 0.5 --output "$SESSION_DIR/probe_q6_t10_reboot_run${K}"
       ```
     - **PowerShell:**
       ```powershell
       .\.venv\Scripts\python.exe pc\fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 15 --interval 0.5 --output "$SESSION_DIR\probe_q6_t10_reboot_run${K}"
       ```
   - **Ở đâu:** Trong VS Code, chọn **Terminal → New Terminal** để mở **Terminal thứ hai**, dùng cùng loại shell với Terminal 1 và đứng tại thư mục gốc `D:/scanner3d`. Terminal 1 phải vừa hoàn tất bước 5.3.1 cho lượt K đang đo.
   - **Làm gì:** Khi probe gửi đến request thứ 3 hoặc 4, nhấn nút vật lý **RST** trên bo ESP32-S3 rồi chạy khối ghi giờ dưới đây ở Terminal 2. Khối này đọc lại `docs/logs/.c5a_session_current` của Terminal 1 mỗi lần; không chép biến bằng tay, không tìm phiên mới nhất hay suy K từ tên thư mục. Tệp phiên chỉ dùng tại máy, không đưa vào commit.
     - **Git Bash (Terminal thứ hai):**
       ```bash
       # Chi doc tep phien do buoc 5.3.1 ghi, khong dung bien cu:
       unset SESSION_DIR K
       if [ ! -f "docs/logs/.c5a_session_current" ]; then
         echo "LOI: Thieu tep phien; quay lai buoc 5.3.1 o Terminal 1!"
         exit 1
       fi
       source docs/logs/.c5a_session_current || { echo "LOI: Khong doc duoc tep phien!"; exit 1; }

       # Kiem tra thu muc phien ton tai truoc khi ghi (thu muc khong ton tai thi dung):
       if [ -z "$SESSION_DIR" ] || [ ! -d "$SESSION_DIR" ]; then
         echo "LOI: Thu muc $SESSION_DIR khong ton tai!"
         exit 1
       fi
       case "$K" in
         1|2|3) ;;
         *) echo "LOI: Tep phien thieu K hoac K khong thuoc 1, 2, 3!"; exit 1 ;;
       esac

       date -u +"%Y-%m-%dT%H:%M:%SZ" > "$SESSION_DIR/rst${K}_action_time.txt"
       ```
     - **PowerShell (Terminal thứ hai):**
       ```powershell
       # Chi doc tep phien do buoc 5.3.1 ghi, khong dung bien cu:
       $SESSION_DIR = $null
       $K = $null
       if (-not (Test-Path -LiteralPath "docs\logs\.c5a_session_current" -PathType Leaf)) {
           throw "LOI: Thieu tep phien; quay lai buoc 5.3.1 o Terminal 1!"
       }
       Get-Content -LiteralPath "docs\logs\.c5a_session_current" -Encoding UTF8 -ErrorAction Stop | ForEach-Object {
           if ($_ -match '^SESSION_DIR="([^"]+)"$') { $SESSION_DIR = $matches[1] }
           if ($_ -match '^K=([123])$') { $K = [int]$matches[1] }
       }

       # Kiem tra thu muc phien ton tai truoc khi ghi (thu muc khong ton tai thi dung):
       if (-not $SESSION_DIR -or -not (Test-Path -LiteralPath $SESSION_DIR -PathType Container)) {
           throw "LOI: Thu muc $SESSION_DIR khong ton tai!"
       }
       if ($null -eq $K) {
           throw "LOI: Tep phien thieu K hoac K khong thuoc 1, 2, 3!"
       }

       (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") | Set-Content "$SESSION_DIR\rst${K}_action_time.txt" -Encoding UTF8
       ```
   - **Thấy gì là đúng:** Terminal 2 ghi đúng tệp `$SESSION_DIR/rst${K}_action_time.txt` của lượt đang đo; mở tệp sẽ thấy thời điểm UTC dạng `yyyy-MM-ddTHH:mm:ssZ`.
   - **Nếu sai:** Có thông báo `LOI` thì dừng lượt, không nhấn RST thêm hoặc tự chọn phiên/K. Kiểm tra thư mục làm việc của Terminal 2, quay lại bước 5.3.1 ở Terminal 1 với đúng SESSION_DIR/K rồi chạy lại; nếu vẫn lỗi, gửi nguyên thông báo và nội dung tệp phiên. `exit 1` đóng phiên Git Bash hiện tại khi lỗi; mở lại Terminal thứ hai để thực hiện sau khi đã sửa nguyên nhân.
   - **Kết quả probe cần có:**
     - Probe phát hiện mất kết nối socket hoặc phát hiện Boot ID thay đổi (`CAMERA_REBOOT: Boot ID thay doi`), dừng ngay lập tức phiên quét, kết luận `Ket luan: INVALID`.
     - Toàn bộ ảnh đã nhận thành công trước thời điểm reset được bảo toàn nguyên vẹn trong thư mục `$SESSION_DIR/probe_q6_t10_reboot_run${K}`.

3. **Bước 5.3.3: Ghi nhận trạng thái SAU khi bo khởi động lại, Áp lại Profile và Chụp ảnh Hồi phục (Đóng kín cặp RST):**
   - Chờ bo khởi động lại xong và kết nối lại mạng Wi-Fi (khoảng 3–5 giây sau khi nhấn RST).
   - Đọc từ Serial Monitor hoặc cổng COM log khởi động mới và lưu vào `$SESSION_DIR/boot_serial_rst${K}.log`:
     - **Git Bash:**
       ```bash
       echo "Doc va luu log Serial khoi dong moi vao $SESSION_DIR/boot_serial_rst${K}.log"
       ```
     - **PowerShell:**
       ```powershell
       Write-Host "Doc va luu log Serial khoi dong moi vao $SESSION_DIR\boot_serial_rst${K}.log"
       ```
   - Lưu thời điểm PC và snapshot `/status` sau khi reset:
     - **Git Bash:**
       ```bash
       date -u +"%Y-%m-%dT%H:%M:%SZ" > "$SESSION_DIR/status_after_rst${K}_time.txt"
       curl -s "http://<IP_ESP32>/status" -o "$SESSION_DIR/status_after_rst${K}.json"
       echo "Trang thai sau RST ${K} da luu."
       ```
     - **PowerShell:**
       ```powershell
       (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") | Set-Content "$SESSION_DIR\status_after_rst${K}_time.txt" -Encoding UTF8
       Invoke-WebRequest -Uri "http://<IP_ESP32>/status" -OutFile "$SESSION_DIR\status_after_rst${K}.json"
       Write-Host "Trang thai sau RST ${K} da luu."
       ```
   - **Áp lại profile SVGA C2 trước khi chụp ảnh hồi phục** (do sau RST cứng, firmware camera trên bo quay về cấu hình mặc định QVGA 320×240; cần áp lại profile SVGA để đưa camera về đúng độ phân giải 800×600):
     - **Git Bash:**
       ```bash
       .venv/Scripts/python.exe pc/camera_profile.py --host <IP_ESP32> --verify --profile "data/calibration/camera_profiles/cam_SVGA_q20_20260928.json"
       ```
     - **PowerShell:**
       ```powershell
       .\.venv\Scripts\python.exe pc\camera_profile.py --host <IP_ESP32> --verify --profile "data\calibration\camera_profiles\cam_SVGA_q20_20260928.json"
       ```
   - Chạy 1 request probe hồi phục ở thư mục phiên riêng biệt để xác nhận camera đã sẵn sàng phục vụ và Boot ID mới hợp lệ:
     - **Git Bash:**
       ```bash
       .venv/Scripts/python.exe pc/fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 1 --output "$SESSION_DIR/probe_q6_t10_rst${K}_recovered"
       ```
     - **PowerShell:**
       ```powershell
       .\.venv\Scripts\python.exe pc\fresh_capture_probe.py --host <IP_ESP32> --port 80 --count 1 --output "$SESSION_DIR\probe_q6_t10_rst${K}_recovered"
       ```
   - **Thấy gì là đúng:**
     - Log Serial boot mới sau RST được lưu đầy đủ vào `$SESSION_DIR/boot_serial_rst${K}.log`.
     - `/status` sau RST phản hồi HTTP 200 OK.
     - Lệnh áp profile in `Ho so khop bo: cam_SVGA_q20_20260928`.
     - Lượt hồi phục nhận `HTTP 200 OK`, kết luận `PASS`, ảnh JPEG giải mã đúng độ phân giải 800×600 SVGA với Boot ID mới (khác Boot ID ở tệp trước RST).
     - Toàn bộ bằng chứng được ghi nhận đầy đủ cho cả lần 1, lần 2 và lần 3 (kết thúc hoàn tất chu trình).
