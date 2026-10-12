// PsramTest - kiem tra ghi/doc PSRAM tren ESP32-S3.
//
// Phuc vu chi tieu B "Nhan dang va bo nho" cua tuan 1 trong roadmap:
//   "kiem tra ghi doc vung 1 MiB khong sai du lieu".
// Khong dung camera. Chay doc lap voi CameraWebServerTest.
//
// Cau hinh build: cung menu Tools voi sketch camera, PSRAM = OPI PSRAM.
//   arduino-cli compile --fqbn esp32:esp32:esp32s3:PSRAM=opi firmware/esp32s3/PsramTest
//
// Ket qua doc tren Serial 115200. Hai dong quyet dinh:
//   RESULT_1MIB    : PASS/FAIL  - dung cho chi tieu B tuan 1
//   RESULT_LARGEST : PASS/FAIL  - khoi lon nhat cap phat duoc, ghi word = chi so word
//                                de phat hien anh xa trung dia chi; khong gate chi tieu
//
// Ghi chu ky thuat: dung con tro volatile de trinh bien dich khong bo qua
// cac lan ghi/doc thuc su vao bo nho ngoai.

#include <Arduino.h>
#include <esp_heap_caps.h>
#include <esp_memory_utils.h>

static const size_t ONE_MIB = 1024u * 1024u;

typedef uint8_t (*pattern_fn)(size_t i);

static uint8_t pat_00(size_t)   { return 0x00; }
static uint8_t pat_FF(size_t)   { return 0xFF; }
static uint8_t pat_AA(size_t)   { return 0xAA; }
static uint8_t pat_55(size_t)   { return 0x55; }
static uint8_t pat_inc(size_t i){ return (uint8_t)(i & 0xFF); }
static uint8_t pat_lcg(size_t i){
  // gia ngau nhien, xac dinh theo i de doc lai so sanh duoc.
  // Lay byte CAO cua tich: moi bit cua i deu anh huong qua nho, nen mau
  // khong lap theo chu ky 2 MiB nhu ban dau (review 2026-09-16).
  uint32_t x = (uint32_t)i * 2654435761u;
  return (uint8_t)(x >> 24);
}

struct PatternCase { const char *name; pattern_fn fn; };

static const PatternCase kPatterns[] = {
  { "0x00", pat_00 },
  { "0xFF", pat_FF },
  { "0xAA", pat_AA },
  { "0x55", pat_55 },
  { "inc",  pat_inc },
  { "lcg",  pat_lcg },
};

// Ghi mau roi doc lai so tung byte. Tra true neu khong sai byte nao.
// Nhan ten va ham mau rieng le, khong nhan struct: bo tien xu ly cua Arduino
// chen prototype len dau tep truoc khi struct duoc dinh nghia.
static bool writeReadVerify(volatile uint8_t *buf, size_t n, const char *name, pattern_fn fn) {
  uint32_t t0 = millis();
  for (size_t i = 0; i < n; i++) buf[i] = fn(i);
  uint32_t t1 = millis();

  size_t bad = 0;
  size_t firstBad = 0;
  uint8_t gotAtFirst = 0, wantAtFirst = 0;
  for (size_t i = 0; i < n; i++) {
    uint8_t want = fn(i);
    uint8_t got = buf[i];
    if (got != want) {
      if (bad == 0) { firstBad = i; gotAtFirst = got; wantAtFirst = want; }
      bad++;
    }
  }
  uint32_t t2 = millis();

  Serial.printf("  pattern %-4s : write %4u ms, read %4u ms : ", name, (unsigned)(t1 - t0), (unsigned)(t2 - t1));
  if (bad == 0) {
    Serial.println("OK");
    return true;
  }
  Serial.printf("FAIL, %u byte sai, dau tien tai offset %u (doc 0x%02X, mong 0x%02X)",
                (unsigned)bad, (unsigned)firstBad, gotAtFirst, wantAtFirst);
  Serial.println();
  return false;
}

// Ghi moi word 32 bit = chi so word XOR hang so, roi doc lai. Neu vung dia
// chi lon bi anh xa trung vao bo nho nho hon, cac word o dia chi cach nhau
// mot boi cua kich thuoc that se de len nhau va sai khi doc. Mau byte
// khong lam duoc viec nay.
static bool writeReadVerifyWords(volatile uint32_t *w, size_t nwords) {
  const uint32_t K = 0xA5A5A5A5u;
  uint32_t t0 = millis();
  for (size_t j = 0; j < nwords; j++) w[j] = (uint32_t)j ^ K;
  uint32_t t1 = millis();

  size_t bad = 0;
  size_t firstBad = 0;
  uint32_t gotAtFirst = 0, wantAtFirst = 0;
  for (size_t j = 0; j < nwords; j++) {
    uint32_t want = (uint32_t)j ^ K;
    uint32_t got = w[j];
    if (got != want) {
      if (bad == 0) { firstBad = j; gotAtFirst = got; wantAtFirst = want; }
      bad++;
    }
  }
  uint32_t t2 = millis();

  Serial.printf("  pattern word : write %4u ms, read %4u ms : ", (unsigned)(t1 - t0), (unsigned)(t2 - t1));
  if (bad == 0) {
    Serial.println("OK");
    return true;
  }
  Serial.printf("FAIL, %u word sai, dau tien tai word %u = byte offset %u (doc 0x%08X, mong 0x%08X)",
                (unsigned)bad, (unsigned)firstBad, (unsigned)(firstBad * 4), (unsigned)gotAtFirst, (unsigned)wantAtFirst);
  Serial.println();
  return false;
}

static void printSizes(const char *label) {
  Serial.printf("%s: total %u KB, free %u KB, largest free block %u KB",
                label,
                (unsigned)(ESP.getPsramSize() / 1024),
                (unsigned)(ESP.getFreePsram() / 1024),
                (unsigned)(heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM) / 1024));
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println();
  Serial.println("=== PsramTest: ghi/doc PSRAM tren ESP32-S3 ===");
  Serial.printf("psramFound: %s", psramFound() ? "yes" : "no");
  Serial.println();
  printSizes("PSRAM truoc khi thu");

  if (!psramFound()) {
    Serial.println("RESULT_1MIB    : FAIL (khong nhan PSRAM)");
    Serial.println("RESULT_LARGEST : SKIP");
    Serial.println("GOI Y: firmware nay duoc build voi PSRAM tat. Trong Arduino IDE, menu");
    Serial.println("       Tools > PSRAM la thiet lap theo tung sketch dang mo; mo sketch moi");
    Serial.println("       thi no co the tro ve Disabled. Kiem tra lai roi nap lai.");
    return;
  }

  // ---- Test A: 1 MiB, sau mau, dung cho chi tieu B ----
  Serial.println();
  Serial.println("[A] Cap phat 1 MiB trong PSRAM va thu sau mau");
  uint8_t *bufA = (uint8_t *)heap_caps_malloc(ONE_MIB, MALLOC_CAP_SPIRAM);
  bool okA = false;
  if (!bufA) {
    Serial.println("  heap_caps_malloc 1 MiB trong PSRAM that bai");
  } else {
    bool ext = esp_ptr_external_ram(bufA);
    Serial.printf("  buffer tai %p, nam trong RAM ngoai: %s", bufA, ext ? "yes" : "NO");
    Serial.println();
    okA = ext;
    for (const PatternCase &pc : kPatterns) {
      okA = writeReadVerify((volatile uint8_t *)bufA, ONE_MIB, pc.name, pc.fn) && okA;
      yield();
    }
    heap_caps_free(bufA);
  }
  Serial.printf("RESULT_1MIB    : %s", okA ? "PASS" : "FAIL");
  Serial.println();

  // ---- Test B: khoi lon nhat cap phat duoc, mot mau, thong tin dung luong ----
  Serial.println();
  Serial.println("[B] Cap phat khoi lon nhat con trong, ghi word = chi so word");
  yield();
  size_t largest = heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM);
  Serial.printf("  khoi lon nhat con trong: %u KB", (unsigned)(largest / 1024));
  Serial.println();
  bool okB = false;
  uint8_t *bufB = largest ? (uint8_t *)heap_caps_malloc(largest, MALLOC_CAP_SPIRAM) : NULL;
  if (!bufB) {
    Serial.println("  heap_caps_malloc khoi lon nhat that bai");
  } else {
    bool ext = esp_ptr_external_ram(bufB);
    Serial.printf("  buffer tai %p, nam trong RAM ngoai: %s", bufB, ext ? "yes" : "NO");
    Serial.println();
    size_t nwords = largest / sizeof(uint32_t);
    okB = ext && writeReadVerifyWords((volatile uint32_t *)bufB, nwords);
    heap_caps_free(bufB);
  }
  Serial.printf("RESULT_LARGEST : %s (%u KB)", okB ? "PASS" : "FAIL", (unsigned)(largest / 1024));
  Serial.println();

  Serial.println();
  printSizes("PSRAM sau khi thu");
  Serial.println("=== het ===");
}

void loop() {
  delay(10000);
}
