/*
 * tester_c4_test.c - test DOC LAP cua Tester C4 cho ping_proto.c that (P1, FSM, an toan PA8).
 *
 * Hop dong: handoff/2026-09-21_c4-nucleo-laser-control/01_PLAN.md Vong 5 "Tieu chi Tester hieu luc"
 * T1-T4 va docs/design/NUCLEO_PROTOCOL.md (Q3). HAL gia rieng cua Tester: test/tester_c4_hal.c
 * (ghi lich su PA8: muc cao ngoai CAPTURING la vi pham). Kiem them moi dong phan hoi P1:
 * checksum dung, dai <= 64 byte ke ca LF, ma loi thuoc bang Q3 muc 3.
 *
 * Chay (Git Bash, tu firmware/stm32/NucleoPing; <TMP> la thu muc tam bat ky):
 *   /d/MinGW/bin/gcc -std=c99 -Wall -Wextra -O0 -Itest/fake -ICore/Inc -DFW_GIT_HASH='"hosttest"' \
 *     test/tester_c4_test.c test/tester_c4_hal.c Core/Src/ping_proto.c -o <TMP>/tester_c4_test.exe
 *   <TMP>/tester_c4_test.exe
 * Thoat 0 khi khong co kich ban FAIL. NOTE la ghi nhan, khong tinh FAIL. Khong phai thu tren bo.
 */
#include "ping_proto.h"
#include "fw_version.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void sim_reset(int door, int estop, uint32_t rcc_flags, uint32_t tick, int pa8_before, int with_iwdg);
void sim_set_inputs(int door, int estop);
void sim_set_tick(uint32_t t);
void sim_poll(void);
void sim_rx(const char *bytes, int n);
void sim_rx_error(void);
int sim_take_tx(char *buf, int cap);
int sim_pa8(void);
int sim_pa8_after_early(void);
uint32_t sim_pa8_violations(void);
const char *sim_viol_note(void);
uint32_t sim_iwdg_refresh(void);
const char *sim_state(void);
const char *sim_last_err(void);

#define F_IWDG 0x01u
#define F_POR  0x02u

static char g_tx[8192];
static int g_scen_fail, g_scen_note;
static int n_pass, n_fail, n_note;
static char g_summary[64][160];
static int g_nsum;
static const char *g_sid;
static uint32_t g_viol_total;
static char g_viol_note[256];

/* ---- kiem moi dong phan hoi P1 ---- */
static const char *Q3_CODES[] = {"TOOLONG", "BADFRAME", "BADCHK", "UNKNOWN", "BADARG", "NOTIMPL", "OVERRUN",
                                 "BUSY", "NOT_HOMED", "RANGE", "LASER_ON", "IN_ERROR", "DOOR_OPEN", "ESTOP",
                                 "HOME_TIMEOUT", "HOME_STEPS", "LINK_LOST", "LASER_TIMEOUT", "WDG_RESET", NULL};
static int a_lines, a_badchk, a_toolong, a_badcode;
static char a_note[512];

static int hexv(char c)
{
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

static void audit_line(const char *s, size_t len)
{
  char line[160];
  size_t i;
  const char *star, *e;
  unsigned chk = 0;
  if (len == 0 || s[0] < '0' || s[0] > '9') return;   /* chi dong P1 (bat dau bang seq) */
  a_lines++;
  if (len >= sizeof(line)) len = sizeof(line) - 1;
  memcpy(line, s, len);
  line[len] = 0;
  if (len + 1u > 64u) {
    a_toolong++;
    snprintf(a_note + strlen(a_note), sizeof(a_note) - strlen(a_note), "[dai %u: %s] ", (unsigned)(len + 1u), line);
  }
  star = strrchr(line, '*');
  if (!star || strlen(star) != 3 || hexv(star[1]) < 0 || hexv(star[2]) < 0) {
    a_badchk++;
    snprintf(a_note + strlen(a_note), sizeof(a_note) - strlen(a_note), "[khung sai: %s] ", line);
    return;
  }
  for (i = 0; line + i < star; i++) chk ^= (unsigned char)line[i];
  if (chk != (unsigned)(hexv(star[1]) * 16 + hexv(star[2]))) {
    a_badchk++;
    snprintf(a_note + strlen(a_note), sizeof(a_note) - strlen(a_note), "[checksum sai: %s] ", line);
  }
  /* chi xet phan hoi dang '<seq> ERROR <ma>' (khong nham trang thai ERROR trong 'DONE ERROR ...') */
  e = strchr(line, ' ');
  if (e && strncmp(e, " ERROR ", 7) != 0) e = NULL;
  if (e) {
    char code[32];
    int k = 0, found = 0;
    e += 7;
    while (*e && *e != ' ' && *e != '*' && k < 31) code[k++] = *e++;
    code[k] = 0;
    for (k = 0; Q3_CODES[k]; k++) if (strcmp(Q3_CODES[k], code) == 0) found = 1;
    if (!found) {
      a_badcode++;
      snprintf(a_note + strlen(a_note), sizeof(a_note) - strlen(a_note), "[ma khong co trong Q3: %s] ", line);
    }
  }
}

static const char *take(void)
{
  const char *p, *nl;
  sim_take_tx(g_tx, (int)sizeof(g_tx));
  for (p = g_tx; (nl = strchr(p, '\n')) != NULL; p = nl + 1) audit_line(p, (size_t)(nl - p));
  return g_tx;
}

/* ---- khung kiem ---- */
static void scen(const char *sid, const char *title)
{
  g_sid = sid;
  g_scen_fail = g_scen_note = 0;
  printf("\n---- %s %s\n", sid, title);
}

static void scen_end(const char *title, int note_only)
{
  const char *st = g_scen_fail ? "FAIL" : (note_only ? "NOTE" : "PASS");
  if (g_scen_fail) n_fail++; else if (note_only) n_note++; else n_pass++;
  printf("==== %s %s\n", g_sid, st);
  if (g_nsum < 64) snprintf(g_summary[g_nsum++], 160, "%-8s  %-4s  %s", g_sid, st, title);
}

static void ok(int cond, const char *label, const char *got)
{
  char g[200];
  size_t i;
  snprintf(g, sizeof(g), "%s", got ? got : "");
  for (i = 0; g[i]; i++) if (g[i] == '\n') g[i] = '|';
  printf("  [%s] %s%s%s\n", cond ? "OK  " : "FAIL", label, g[0] ? "  | " : "", g);
  if (!cond) g_scen_fail = 1;
}

static void note(const char *label, const char *got)
{
  char g[200];
  size_t i;
  snprintf(g, sizeof(g), "%s", got ? got : "");
  for (i = 0; g[i]; i++) if (g[i] == '\n') g[i] = '|';
  printf("  [NOTE] %s  | %s\n", label, g);
  g_scen_note = 1;
}

/* ---- tien ich ---- */
static void mkframe(char *out, size_t cap, const char *body)
{
  unsigned chk = 0;
  const char *p;
  for (p = body; *p; p++) chk ^= (unsigned char)*p;
  snprintf(out, cap, "%s*%02X\n", body, chk);
}

static const char *send_raw(const char *bytes)
{
  sim_rx(bytes, (int)strlen(bytes));
  sim_poll();
  return take();
}

static const char *p1(unsigned seq, const char *cmd)
{
  char body[160], fr[200];
  snprintf(body, sizeof(body), "%u %s", seq, cmd);
  mkframe(fr, sizeof(fr), body);
  return send_raw(fr);
}

/* Phan hoi P1 mong doi cho "<seq> <body>" (co checksum va LF) */
static const char *expect(unsigned seq, const char *body)
{
  static char out[200];
  char b[160];
  snprintf(b, sizeof(b), "%u %s", seq, body);
  mkframe(out, sizeof(out), b);
  return out;
}

static void at(uint32_t t)
{
  sim_set_tick(t);
  sim_poll();
  take();
}

static void boot(int door, int estop, uint32_t tick)
{
  g_viol_total += sim_pa8_violations();
  if (sim_pa8_violations() && !g_viol_note[0]) snprintf(g_viol_note, sizeof(g_viol_note), "%s", sim_viol_note());
  sim_reset(door, estop, F_POR, tick, 0, 1);
  take();
}

static int starts(const char *s, const char *pre) { return strncmp(s, pre, strlen(pre)) == 0; }
static int is_state(const char *st) { return strcmp(sim_state(), st) == 0; }
static int has(const char *s, const char *sub) { return strstr(s, sub) != NULL; }

static char g_buf[256];
static const char *fmt_state(void)
{
  snprintf(g_buf, sizeof(g_buf), "state=%s last_err=%s PA8=%d", sim_state(), sim_last_err(), sim_pa8());
  return g_buf;
}

/* ================================================================ */
static void t1(void)
{
  const char *r;
  scen("T1", "binh thuong: frame P1 dung checksum, LASER ON/OFF, STATUS, PING/ID? ke thua, BOOT");
  g_viol_total += sim_pa8_violations();
  sim_reset(1, 0, F_POR, 1000, 0, 1);
  r = take();
  ok(starts(r, "BOOT NucleoPing " FW_VERSION " hosttest"), "BOOT co phien ban firmware", r);
  ok(strcmp(FW_VERSION, "0.2.0") == 0, "FW_VERSION tang len 0.2.0", FW_VERSION);
  ok(has(r, " P1"), "BOOT co danh dau giao thuc 'P1' (Q3 muc 1: 'BOOT NucleoScan <fw_ver> <git> P1')", r);
  r = p1(1, "STATUS");
  ok(strcmp(r, expect(1, "DONE IDLE 0 0 1 0 0 1000 NONE 0")) == 0, "1 STATUS -> DONE IDLE 0 0 1 0 0 <uptime> NONE 0 (Q3/D039: 10 token, remaining_ms cuoi)", r);
  r = p1(2, "LASER ON");
  ok(strcmp(r, expect(2, "DONE ON 5000")) == 0 && sim_pa8() == 1 && is_state("CAPTURING"),
     "2 LASER ON (cua dong, estop nha) -> DONE ON 5000, PA8 cao, CAPTURING", r);
  r = p1(3, "STATUS");
  ok(strcmp(r, expect(3, "DONE CAPTURING 0 1 1 0 0 1000 NONE 5000")) == 0, "3 STATUS khi CAPTURING ngay sau ON: laser=1, remaining_ms=5000", r);
  r = p1(4, "LASER OFF");
  ok(strcmp(r, expect(4, "DONE OFF 0")) == 0 && sim_pa8() == 0 && is_state("IDLE"), "4 LASER OFF -> DONE OFF 0, PA8 thap, IDLE", r);
  r = send_raw("PING 7\n");
  ok(strcmp(r, "PONG 7 1000\n") == 0, "ke thua: PING 7 -> PONG 7 <uptime>", r);
  r = send_raw("ID?\n");
  ok(strcmp(r, "ID NUCLEO-F446RE NucleoPing 0.2.0 hosttest\n") == 0, "ke thua: ID? mang phien ban C4", r);
  r = send_raw("PING 4294967296\n");
  ok(strcmp(r, "ERR badarg\n") == 0, "ke thua: PING tran uint32 -> ERR badarg (R07 con)", r);
  {
    char fr[200];
    mkframe(fr, sizeof(fr), "5 STATUS");
    fr[strlen(fr) - 1] = 0;
    strcat(fr, "\r\n");
    r = send_raw(fr);
    ok(starts(r, "5 DONE IDLE "), "frame P1 ket thuc CRLF duoc nhan (CR bo qua)", r);
  }
  scen_end("binh thuong: frame P1 dung checksum, LASER ON/OFF, STATUS, PING/ID? ke thua, BOOT", 0);
}

static void padded_frame(char *out, size_t cap, unsigned seq, int total_chars)
{
  /* frame "<seq> HEARTBEAT   ...*HH" dai dung total_chars ky tu (chua ke LF) */
  char body[128];
  int blen = total_chars - 3, n;
  n = snprintf(body, sizeof(body), "%u HEARTBEAT", seq);
  while (n < blen && n < (int)sizeof(body) - 1) body[n++] = ' ';
  body[n] = 0;
  mkframe(out, cap, body);
}

static void t2(void)
{
  const char *r;
  char fr[200];
  int k;
  uint32_t bases[3] = {1000u, 700000u, 0xFFFFF000u};
  scen("T2", "bien: seq 1/65535/0/65536, dong 64 byte ke ca LF, timeout 2999/3000 va 4999/5000 ms (3 moc tick, co tran uint32)");
  boot(1, 0, 1000);
  r = p1(1, "HEARTBEAT");
  ok(strcmp(r, expect(1, "DONE IDLE")) == 0, "seq 1 hop le", r);
  r = p1(65535, "HEARTBEAT");
  ok(strcmp(r, expect(65535, "DONE IDLE")) == 0, "seq 65535 hop le", r);
  r = p1(0, "LASER ON");
  ok(has(r, " ERROR ") && sim_pa8() == 0 && is_state("IDLE"), "seq 0 LASER ON -> bi tu choi, PA8 thap", r);
  r = p1(65536, "LASER ON");
  ok(has(r, " ERROR ") && sim_pa8() == 0 && is_state("IDLE"), "seq 65536 LASER ON -> bi tu choi, PA8 thap", r);
  padded_frame(fr, sizeof(fr), 70, 63);
  r = send_raw(fr);
  ok(starts(r, "70 DONE IDLE*"), "dong 63 ky tu + LF = 64 byte ke ca LF: duoc xet", r);
  padded_frame(fr, sizeof(fr), 71, 64);
  r = send_raw(fr);
  ok(starts(r, "0 ERROR TOOLONG*"), "dong 64 ky tu + LF = 65 byte ke ca LF: > 64 -> 0 ERROR TOOLONG (Q3 muc 1 'toi da 64 byte ke ca LF')", r);
  padded_frame(fr, sizeof(fr), 72, 65);
  r = send_raw(fr);
  ok(starts(r, "0 ERROR TOOLONG*"), "dong 65 ky tu + LF: 0 ERROR TOOLONG", r);
  r = p1(73, "HEARTBEAT");
  ok(starts(r, "73 DONE IDLE*"), "sau TOOLONG nhan lenh moi binh thuong", r);

  for (k = 0; k < 3; k++) {
    uint32_t t0 = bases[k];
    char lab[160];
    /* a. im lang: LINK_LOST tai 3000 ms */
    boot(1, 0, t0);
    p1(10, "LASER ON");
    at(t0 + 2999u);
    snprintf(lab, sizeof(lab), "moc %lu: khong ban tin, +2999 ms: van CAPTURING, PA8 cao", (unsigned long)t0);
    ok(is_state("CAPTURING") && sim_pa8() == 1, lab, fmt_state());
    at(t0 + 3000u);
    snprintf(lab, sizeof(lab), "moc %lu: +3000 ms: PA8 thap, ERROR LINK_LOST", (unsigned long)t0);
    ok(is_state("ERROR") && sim_pa8() == 0 && strcmp(sim_last_err(), "LINK_LOST") == 0, lab, fmt_state());
    /* b. heartbeat moi 1000 ms, khong ON moi: LASER_TIMEOUT tai 5000 ms */
    boot(1, 0, t0);
    p1(20, "LASER ON");
    sim_set_tick(t0 + 1000u); p1(21, "HEARTBEAT");
    sim_set_tick(t0 + 2000u); p1(22, "HEARTBEAT");
    sim_set_tick(t0 + 3000u); p1(23, "HEARTBEAT");
    sim_set_tick(t0 + 4000u); p1(24, "HEARTBEAT");
    at(t0 + 4999u);
    snprintf(lab, sizeof(lab), "moc %lu: heartbeat 1 s, +4999 ms: con trong han laser, PA8 cao", (unsigned long)t0);
    ok(is_state("CAPTURING") && sim_pa8() == 1, lab, fmt_state());
    at(t0 + 5000u);
    snprintf(lab, sizeof(lab), "moc %lu: +5000 ms: PA8 thap, IDLE, last_err LASER_TIMEOUT", (unsigned long)t0);
    ok(is_state("IDLE") && sim_pa8() == 0 && strcmp(sim_last_err(), "LASER_TIMEOUT") == 0, lab, fmt_state());
    r = p1(25, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: STATUS bao IDLE ... LASER_TIMEOUT", (unsigned long)t0);
    ok(starts(r, "25 DONE IDLE 0 0 1 0 0 ") && has(r, " LASER_TIMEOUT 0*"), lab, r);
    /* c. LASER ON moi (seq moi) dat lai han 5 s; HEARTBEAT khong */
    boot(1, 0, t0);
    p1(30, "LASER ON");
    sim_set_tick(t0 + 1000u); p1(31, "HEARTBEAT");
    sim_set_tick(t0 + 2000u); p1(32, "HEARTBEAT");
    sim_set_tick(t0 + 3000u); p1(33, "LASER ON");
    sim_set_tick(t0 + 4000u); p1(34, "HEARTBEAT");
    sim_set_tick(t0 + 5000u); p1(35, "HEARTBEAT");
    sim_set_tick(t0 + 6000u); p1(36, "HEARTBEAT");
    sim_set_tick(t0 + 7000u); p1(37, "HEARTBEAT");
    at(t0 + 7999u);
    snprintf(lab, sizeof(lab), "moc %lu: LASER ON moi o +3000 dat lai han: +7999 con cao", (unsigned long)t0);
    ok(is_state("CAPTURING") && sim_pa8() == 1, lab, fmt_state());
    at(t0 + 8000u);
    snprintf(lab, sizeof(lab), "moc %lu: +8000 PA8 thap LASER_TIMEOUT", (unsigned long)t0);
    ok(is_state("IDLE") && sim_pa8() == 0, lab, fmt_state());
  }
  {
    /* d. poll moi 1 ms: PA8 doi muc dung mot lan, tai dung +5000 */
    uint32_t t0 = 5000u, t, t_off = 0;
    int flips = 0, prev;
    boot(1, 0, t0);
    p1(40, "LASER ON");
    prev = sim_pa8();
    for (t = t0 + 1u; t <= t0 + 6000u; t++) {
      sim_set_tick(t);
      if ((t - t0) % 1000u == 0u && t - t0 < 5000u) {
        p1(41u + (t - t0) / 1000u, "HEARTBEAT");
      } else {
        sim_poll();
        take();
      }
      if (sim_pa8() != prev) { flips++; t_off = t; prev = sim_pa8(); }
    }
    snprintf(g_buf, sizeof(g_buf), "so lan doi muc %d, tat tai +%lu ms", flips, (unsigned long)(t_off - t0));
    ok(flips == 1 && t_off == t0 + 5000u, "poll moi 1 ms (heartbeat 1 s): PA8 doi muc dung 1 lan tai +5000 ms", g_buf);
  }
  scen_end("bien: seq 1/65535/0/65536, dong 64 byte ke ca LF, timeout 2999/3000 va 4999/5000 ms (3 moc tick, co tran uint32)", 0);
}

static void t3(void)
{
  const char *r;
  char fr[200], first[200];
  int i, same;
  scen("T3", "dau vao loi: sai XOR, thieu/thua doi so, lenh la, mat byte UART, trung seq 10 lan");
  boot(1, 0, 1000);
  /* sai XOR */
  r = send_raw("30 LASER ON*00\n");
  ok(has(r, "ERROR BADCHK") && sim_pa8() == 0 && is_state("IDLE"), "sai XOR -> ERROR BADCHK, khong bat, van IDLE", r);
  /* Q3 muc 3: BADCHK la loi ban tin, KHONG doi trang thai -> khong duoc ghi vao bo nho chong lap */
  r = p1(30, "LASER ON");
  ok(strcmp(r, expect(30, "DONE ON 5000")) == 0 && sim_pa8() == 1,
     "gui lai dung checksum cung seq 30 sau BADCHK: phai THUC THI (BADCHK khong duoc thanh 'phan hoi da luu')", r);
  p1(31, "LASER OFF");
  boot(1, 0, 1000);
  p1(31, "LASER ON");
  r = send_raw("32 LASER OFF*00\n");
  ok(has(r, "ERROR BADCHK") && sim_pa8() == 1, "LASER OFF sai XOR: khong thuc thi (dung), PA8 van cao", r);
  r = p1(32, "LASER OFF");
  ok(strcmp(r, expect(32, "DONE OFF 0")) == 0 && sim_pa8() == 0,
     "PC gui lai LASER OFF cung seq 32, checksum dung: PA8 PHAI ve thap ngay (khong cho 5 s)", r);
  if (sim_pa8()) p1(39, "LASER OFF");
  boot(1, 0, 1000);
  r = p1(33, "LASER ON");
  snprintf(first, sizeof(first), "%s", r);
  r = send_raw("33 RAC*00\n");
  r = p1(33, "LASER ON");
  ok(strcmp(r, first) == 0, "khung hong mang seq 33 (= seq hop le cuoi) khong duoc ghi de phan hoi da luu cua 33", r);
  p1(34, "LASER OFF");
  /* mat byte: checksum phat hien */
  mkframe(fr, sizeof(fr), "35 LASER ON");
  memmove(&fr[6], &fr[7], strlen(&fr[7]) + 1);   /* bo 1 byte ('A' cua LASER) */
  r = send_raw(fr);
  ok(has(r, "ERROR") && sim_pa8() == 0 && is_state("IDLE"), "mat 1 byte trong khung (LSER ON): khong thanh lenh hop le", r);
  /* thieu/thua doi so, lenh la */
  {
    const char *bad[] = {"LASER", "LASER ON X", "LASER BLINK", "STATUS X", "HEARTBEAT 1", "STOP 1", "CLEAR 1", NULL};
    for (i = 0; bad[i]; i++) {
      char lab[120];
      r = p1(40u + (unsigned)i, bad[i]);
      snprintf(lab, sizeof(lab), "'%s' -> ERROR BADARG, khong doi trang thai", bad[i]);
      ok(has(r, " ERROR BADARG*") && sim_pa8() == 0 && is_state("IDLE"), lab, r);
    }
  }
  r = p1(50, "FIRE");
  ok(has(r, "50 ERROR UNKNOWN*") && is_state("IDLE"), "lenh la FIRE -> ERROR UNKNOWN", r);
  r = p1(51, "laser on");
  ok(has(r, "51 ERROR UNKNOWN*") && sim_pa8() == 0, "chu thuong 'laser on' -> ERROR UNKNOWN, khong bat", r);
  mkframe(fr, sizeof(fr), "LASER ON");
  r = send_raw(fr);
  ok(has(r, " ERROR ") && sim_pa8() == 0, "khung khong co seq 'LASER ON*hh' -> tu choi", r);
  /* mat byte UART (loi UART giua khung) -> Q3 muc 3: OVERRUN, khong ghep */
  sim_rx("60 LASER ", 9);
  sim_rx_error();
  mkframe(fr, sizeof(fr), "60 LASER ON");
  sim_rx(strchr(fr, 'O'), (int)strlen(strchr(fr, 'O')));
  sim_poll();
  r = take();
  ok(sim_pa8() == 0 && is_state("IDLE"), "loi UART giua khung P1: khong bat laser, khong doi trang thai", r);
  ok(starts(r, "0 ERROR OVERRUN*"), "loi UART giua khung P1: phan hoi theo Q3 muc 3 '0 ERROR OVERRUN*hh'", r);
  r = p1(61, "HEARTBEAT");
  ok(starts(r, "61 DONE IDLE*"), "sau mat byte: lenh ke tiep binh thuong", r);
  /* trung seq 10 lan */
  {
    uint32_t t0 = 20000u;
    boot(1, 0, t0);
    r = p1(70, "LASER ON");
    snprintf(first, sizeof(first), "%s", r);
    same = 1;
    for (i = 1; i <= 10; i++) {
      sim_set_tick(t0 + 400u * (uint32_t)i);
      r = p1(70, "LASER ON");
      if (strcmp(r, first) != 0) same = 0;
    }
    ok(same, "70 LASER ON gui lai 10 lan (t0+400..4000 ms): 10 phan hoi y het phan hoi dau", first);
    at(t0 + 4999u);
    ok(sim_pa8() == 1, "sau 10 lan trung: +4999 ms con cao (dung han tu lan dau)", fmt_state());
    at(t0 + 5000u);
    ok(sim_pa8() == 0 && is_state("IDLE"), "+5000 ms tinh tu lan DAU: PA8 thap (trung seq khong dat lai hen gio)", fmt_state());
    same = 1;
    for (i = 0; i < 10; i++) {
      r = p1(70, "LASER ON");
      if (strcmp(r, first) != 0 || sim_pa8() != 0) same = 0;
    }
    ok(same, "sau khi da tat: 10 lan '70 LASER ON' chi gui lai phan hoi cu, khong bat lai", fmt_state());
  }
  scen_end("dau vao loi: sai XOR, thieu/thua doi so, lenh la, mat byte UART, trung seq 10 lan", 0);
}

static void t4(void)
{
  const char *r;
  int k;
  uint32_t before;
  scen("T4", "thiet bi: cua mo, estop NC ho, mat ban tin khi bo con nguon, RX overrun, reset/IWDG; CLEAR");
  for (k = 0; k < 3; k++) {
    char lab[160];
    /* cua mo khi dang CAPTURING */
    boot(1, 0, 1000u + 100000u * (uint32_t)k);
    p1(1, "LASER ON");
    sim_set_inputs(0, 0);
    sim_poll(); take();
    snprintf(lab, sizeof(lab), "lap %d: cua mo khi CAPTURING -> PA8 thap ngay o poll ke tiep, ERROR DOOR_OPEN", k);
    ok(sim_pa8() == 0 && is_state("ERROR") && strcmp(sim_last_err(), "DOOR_OPEN") == 0, lab, fmt_state());
    r = p1(2, "CLEAR");
    snprintf(lab, sizeof(lab), "lap %d: CLEAR khi cua con mo -> ERROR DOOR_OPEN, giu ERROR", k);
    ok(has(r, "2 ERROR DOOR_OPEN*") && is_state("ERROR"), lab, r);
    r = p1(3, "LASER ON");
    snprintf(lab, sizeof(lab), "lap %d: LASER ON trong ERROR -> tu choi, PA8 thap", k);
    ok(has(r, " ERROR ") && sim_pa8() == 0, lab, r);
    sim_set_inputs(1, 0);
    sim_poll(); take();
    snprintf(lab, sizeof(lab), "lap %d: cua dong lai: van ERROR cho toi CLEAR", k);
    ok(is_state("ERROR"), lab, fmt_state());
    r = p1(4, "CLEAR");
    snprintf(lab, sizeof(lab), "lap %d: CLEAR khi cua dong -> DONE IDLE", k);
    ok(strcmp(r, expect(4, "DONE IDLE")) == 0 && is_state("IDLE"), lab, r);
    /* estop khi CAPTURING */
    p1(5, "LASER ON");
    sim_set_inputs(1, 1);
    sim_poll(); take();
    snprintf(lab, sizeof(lab), "lap %d: estop (NC ho) khi CAPTURING -> PA8 thap, ERROR ESTOP", k);
    ok(sim_pa8() == 0 && is_state("ERROR") && strcmp(sim_last_err(), "ESTOP") == 0, lab, fmt_state());
    r = p1(6, "CLEAR");
    snprintf(lab, sizeof(lab), "lap %d: CLEAR khi estop con nhan -> ERROR ESTOP, giu ERROR", k);
    ok(has(r, "6 ERROR ESTOP*") && is_state("ERROR"), lab, r);
    sim_set_inputs(1, 0);
    sim_poll(); take();
    r = p1(7, "LASER ON");
    snprintf(lab, sizeof(lab), "lap %d: estop nha nhung chua CLEAR: LASER ON bi tu choi", k);
    ok(has(r, " ERROR ") && sim_pa8() == 0, lab, r);
    r = p1(8, "CLEAR");
    snprintf(lab, sizeof(lab), "lap %d: CLEAR sau khi nha estop -> DONE IDLE", k);
    ok(strcmp(r, expect(8, "DONE IDLE")) == 0, lab, r);
    /* estop khi IDLE: Q3 'bat ky -> ERROR' */
    sim_set_inputs(1, 1);
    sim_poll(); take();
    snprintf(lab, sizeof(lab), "lap %d: estop khi IDLE -> ERROR ESTOP", k);
    ok(is_state("ERROR") && strcmp(sim_last_err(), "ESTOP") == 0, lab, fmt_state());
    r = p1(9, "LASER ON");
    snprintf(lab, sizeof(lab), "lap %d: LASER ON khi estop -> ERROR ESTOP, PA8 thap", k);
    ok(has(r, "9 ERROR ESTOP*") && sim_pa8() == 0, lab, r);
    sim_set_inputs(1, 0);
    p1(10, "CLEAR");
    /* mat ban tin khi bo con nguon: LINK_LOST giu toi CLEAR */
    boot(1, 0, 50000u);
    p1(11, "LASER ON");
    at(53000u);
    r = p1(12, "HEARTBEAT");
    snprintf(lab, sizeof(lab), "lap %d: LINK_LOST: ban tin moi (HEARTBEAT) khong tu xoa loi", k);
    ok(strcmp(r, expect(12, "DONE ERROR")) == 0 && sim_pa8() == 0, lab, r);
    r = p1(13, "LASER ON");
    snprintf(lab, sizeof(lab), "lap %d: LASER ON khi LINK_LOST -> ERROR IN_ERROR, PA8 thap", k);
    ok(strcmp(r, expect(13, "ERROR IN_ERROR")) == 0 && sim_pa8() == 0, lab, r);
    r = p1(14, "CLEAR");
    snprintf(lab, sizeof(lab), "lap %d: CLEAR -> DONE IDLE", k);
    ok(strcmp(r, expect(14, "DONE IDLE")) == 0, lab, r);
    /* RX overrun khi CAPTURING: khong bat them, han 5 s van chay */
    boot(1, 0, 90000u);
    p1(15, "LASER ON");
    sim_rx("16 LAS", 6);
    sim_rx_error();
    sim_rx("ER OFF*00\n", 10);
    sim_poll(); take();
    sim_set_tick(91000u); p1(17, "HEARTBEAT");
    sim_set_tick(92000u); p1(18, "HEARTBEAT");
    sim_set_tick(93000u); p1(19, "HEARTBEAT");
    sim_set_tick(94000u); p1(20, "HEARTBEAT");
    at(95000u);
    snprintf(lab, sizeof(lab), "lap %d: RX overrun khi CAPTURING: han laser 5 s van tat dung luc", k);
    ok(sim_pa8() == 0 && is_state("IDLE"), lab, fmt_state());
    /* reset IWDG khi PA8 dang cao */
    g_viol_total += sim_pa8_violations();
    sim_reset(1, 0, F_IWDG, 7u, 1, 1);
    r = take();
    snprintf(lab, sizeof(lab), "lap %d: reset do IWDG khi PA8 dang cao: ping_early_safety_init ha PA8 truoc ping_init", k);
    ok(sim_pa8_after_early() == 0 && sim_pa8() == 0, lab, r);
    snprintf(lab, sizeof(lab), "lap %d: BOOT bao RESET=WDG_RESET", k);
    ok(has(r, "RESET=WDG_RESET"), lab, r);
    r = p1(1, "STATUS");
    snprintf(lab, sizeof(lab), "lap %d: sau IWDG reset: STATUS IDLE, laser 0, last_err WDG_RESET", k);
    ok(starts(r, "1 DONE IDLE 0 0 1 0 0 7 WDG_RESET 0*"), lab, r);
    /* reset nguon khi PA8 dang cao */
    g_viol_total += sim_pa8_violations();
    sim_reset(1, 0, F_POR, 7u, 1, 1);
    take();
    snprintf(lab, sizeof(lab), "lap %d: reset nguon khi PA8 dang cao: PA8 thap sau early init", k);
    ok(sim_pa8_after_early() == 0 && sim_pa8() == 0 && is_state("IDLE"), lab, fmt_state());
  }
  /* IWDG duoc nap lai moi vong poll */
  boot(1, 0, 1000);
  before = sim_iwdg_refresh();
  for (k = 0; k < 50; k++) sim_poll();
  snprintf(g_buf, sizeof(g_buf), "50 poll -> %lu lan refresh", (unsigned long)(sim_iwdg_refresh() - before));
  ok(sim_iwdg_refresh() - before == 50u, "IWDG duoc refresh moi lan ping_poll()", g_buf);
  /* STOP moi trang thai */
  boot(1, 0, 1000);
  p1(1, "LASER ON");
  r = p1(2, "STOP");
  ok(strcmp(r, expect(2, "DONE PAUSED")) == 0 && sim_pa8() == 0, "STOP khi CAPTURING -> DONE PAUSED, PA8 thap", r);
  r = p1(3, "LASER ON");
  ok(has(r, " ERROR ") && sim_pa8() == 0, "LASER ON khi PAUSED -> tu choi", r);
  r = p1(4, "CLEAR");
  ok(strcmp(r, expect(4, "DONE IDLE")) == 0, "CLEAR khi PAUSED -> DONE IDLE", r);
  r = p1(5, "STOP");
  ok(strcmp(r, expect(5, "DONE PAUSED")) == 0, "STOP khi IDLE -> DONE PAUSED", r);
  p1(6, "CLEAR");
  sim_set_inputs(1, 1); sim_poll(); take();
  r = p1(7, "STOP");
  ok(strcmp(r, expect(7, "DONE ERROR")) == 0, "STOP khi ERROR -> giu ERROR", r);
  r = p1(8, "LASER OFF");
  ok(strcmp(r, expect(8, "DONE OFF 0")) == 0 && is_state("ERROR"), "LASER OFF trong ERROR: luon thuc thi, giu ERROR", r);
  sim_set_inputs(1, 0);
  scen_end("thiet bi: cua mo, estop NC ho, mat ban tin khi bo con nguon, RX overrun, reset/IWDG; CLEAR", 0);
}

static void tx_extra(void)
{
  const char *r;
  char buf[200];
  scen("TX1", "PING/ID? ke thua tinh la ban tin cho T_hb (Q3 muc 2); IDLE im lang lau khong loi");
  boot(1, 0, 1000);
  p1(1, "LASER ON");
  sim_set_tick(3000u); send_raw("PING 1\n");
  at(5999u);
  ok(is_state("CAPTURING") && sim_pa8() == 1, "PING o +2000 gia han lien lac: +4999 chua LINK_LOST", fmt_state());
  boot(1, 0, 1000);
  p1(1, "LASER ON");
  sim_set_tick(3000u); send_raw("PING 1\n");
  sim_set_tick(5000u); send_raw("ID?\n");
  at(5999u);
  ok(is_state("CAPTURING") && sim_pa8() == 1, "PING +2000, ID? +4000 (khong P1): +4999 van CAPTURING", fmt_state());
  at(6000u);
  ok(is_state("IDLE") && strcmp(sim_last_err(), "LASER_TIMEOUT") == 0, "+5000: LASER_TIMEOUT (khong phai LINK_LOST)", fmt_state());
  boot(1, 0, 1000);
  at(60000u);
  ok(is_state("IDLE"), "IDLE im lang 59 s: khong vao ERROR (Q3: LINK_LOST chi khi dang chay)", fmt_state());
  scen_end("PING/ID? ke thua tinh la ban tin cho T_hb (Q3 muc 2); IDLE im lang lau khong loi", 0);

  scen("TX2", "khung STATUS dai nhat C4 (seq 65535, CAPTURING, uptime 4294967295, LASER_TIMEOUT, remaining 5000) dung 64 byte ke ca LF, khong bi cat");
  boot(1, 0, 0xFFFFFFFFu - 6000u);
  p1(1, "LASER ON");
  sim_set_tick(0xFFFFFFFFu - 5000u); p1(2, "HEARTBEAT");
  sim_set_tick(0xFFFFFFFFu - 4000u); p1(3, "HEARTBEAT");
  sim_set_tick(0xFFFFFFFFu - 3000u); p1(4, "HEARTBEAT");
  sim_set_tick(0xFFFFFFFFu - 2000u); p1(5, "HEARTBEAT");
  sim_set_tick(0xFFFFFFFFu - 1000u); p1(6, "HEARTBEAT");
  sim_set_tick(0xFFFFFFFFu);
  r = p1(65535, "STATUS");
  ok(strcmp(r, expect(65535, "DONE IDLE 0 0 1 0 0 4294967295 LASER_TIMEOUT 0")) == 0, "sau LASER_TIMEOUT: STATUS IDLE ... LASER_TIMEOUT 0", r);
  r = p1(7, "LASER ON");
  ok(strcmp(r, expect(7, "DONE ON 5000")) == 0, "LASER ON moi tai tick 4294967295 (last_err van LASER_TIMEOUT)", r);
  r = p1(65535, "STATUS");
  snprintf(buf, sizeof(buf), "%u byte: %s", (unsigned)strlen(r), r);
  ok(strcmp(r, expect(65535, "DONE CAPTURING 0 1 1 0 0 4294967295 LASER_TIMEOUT 5000")) == 0 && strlen(r) == 64u,
     "khung dai nhat '65535 DONE CAPTURING 0 1 1 0 0 4294967295 LASER_TIMEOUT 5000*hh' + LF: du token, checksum dung, DUNG 64 byte", buf);
  p1(8, "LASER OFF");
  scen_end("khung STATUS dai nhat C4 (seq 65535, CAPTURING, uptime 4294967295, LASER_TIMEOUT, remaining 5000) dung 64 byte ke ca LF, khong bi cat", 0);

  scen("TX3", "CLEAR khi CAPTURING: ma loi phai thuoc bang Q3 muc 3");
  boot(1, 0, 1000);
  p1(1, "LASER ON");
  r = p1(2, "CLEAR");
  snprintf(buf, sizeof(buf), "%s", r);
  {
    const char *e = strstr(buf, " ERROR ");
    int found = 0, k;
    if (e) {
      char code[32];
      int n = 0;
      e += 7;
      while (*e && *e != '*' && *e != ' ' && n < 31) code[n++] = *e++;
      code[n] = 0;
      for (k = 0; Q3_CODES[k]; k++) if (strcmp(Q3_CODES[k], code) == 0) found = 1;
    }
    ok(e == NULL || found, "CLEAR khi CAPTURING: neu tu choi thi ma loi co trong Q3 muc 3", buf);
  }
  p1(3, "LASER OFF");
  scen_end("CLEAR khi CAPTURING: ma loi phai thuoc bang Q3 muc 3", 0);

  scen("TX4", "ghi nhan: cac cho Q3 viet chua ro, Tester chi ghi hanh vi thuc");
  boot(0, 0, 1000);
  r = p1(1, "LASER ON");
  snprintf(buf, sizeof(buf), "%s -> %s", r, fmt_state());
  note("LASER ON tu IDLE khi cua mo: Q3 muc 3 DOOR_OPEN 'vao ERROR: co, khi dang chay'; ma vao", buf);
  boot(1, 0, 1000);
  sim_set_inputs(1, 1); sim_poll(); take();
  r = p1(2, "HOME");
  note("HOME khi ERROR: Q3 muc 4 noi 'ERROR IN_ERROR', muc 2/7 noi C4 tra NOTIMPL; ma tra", r);
  sim_set_inputs(1, 0); p1(3, "CLEAR");
  r = send_raw("PING 5*\n");
  note("dong ke thua co dau '*' ('PING 5*'): 0.1.1 tra 'ERR badarg'; 0.2.0 tra", r);
  r = send_raw("12 STATUS*00\n");
  sim_set_tick(1000u);
  note("khung sai checksum co tinh la 'ban tin' cho T_hb khong: ma chi tinh khung hop le (an toan hon)", r);
  p1(20, "LASER ON");
  r = p1(20, "LASER OFF");
  snprintf(buf, sizeof(buf), "%s -> %s", r, fmt_state());
  note("LASER OFF dung lai seq cua lenh truoc (PC loi): Q3 1.1 gui lai phan hoi cu -> laser KHONG tat toi 5 s", buf);
  p1(21, "LASER OFF");
  scen_end("ghi nhan: cac cho Q3 viet chua ro, Tester chi ghi hanh vi thuc", 1);
}

static uint32_t rem_of(const char *r)
{
  /* token cuoi truoc '*' cua dong STATUS */
  const char *star = strrchr(r, '*'), *sp;
  if (!star) return 0xFFFFFFFFu;
  for (sp = star - 1; sp > r && *sp != ' '; sp--) {}
  return (uint32_t)strtoul(sp + 1, NULL, 10);
}

static int ntok(const char *r)
{
  int n = 1;
  const char *p;
  const char *star = strrchr(r, '*');
  for (p = r; *p && p != star; p++) if (*p == ' ') n++;
  return n;
}

static void t_remaining(void)
{
  const char *r;
  char buf[200];
  int k;
  uint32_t bases[3] = {1000u, 700000u, 0xFFFFFF00u};
  scen("TR", "remaining_ms trong STATUS (D039): 5000 ngay sau ON, giam theo tick, HEARTBEAT/trung seq khong gia han, ON seq moi dat lai, 0 khi tat/het han/loi; qua tran uint32");
  for (k = 0; k < 3; k++) {
    uint32_t t0 = bases[k];
    char lab[180];
    boot(1, 0, t0);
    r = p1(1, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: IDLE: 11 token (seq + 10), remaining 0", (unsigned long)t0);
    ok(ntok(r) == 11 && rem_of(r) == 0u, lab, r);
    p1(2, "LASER ON");
    r = p1(3, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: ngay sau ON: remaining 5000", (unsigned long)t0);
    ok(rem_of(r) == 5000u && has(r, " CAPTURING "), lab, r);
    sim_set_tick(t0 + 1000u); p1(4, "HEARTBEAT");
    r = p1(5, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: +1000 (co HEARTBEAT): remaining 4000 - HEARTBEAT khong gia han", (unsigned long)t0);
    ok(rem_of(r) == 4000u, lab, r);
    sim_set_tick(t0 + 2000u); p1(2, "LASER ON");   /* trung seq 2? khong: seq cuoi la 5 -> seq 2 khong trung, dung seq 5 duoi day */
    r = p1(6, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: +2000 sau 'LASER ON' seq moi (2 != 5): dat lai 5000", (unsigned long)t0);
    ok(rem_of(r) == 5000u, lab, r);
    sim_set_tick(t0 + 3000u);
    r = p1(6, "STATUS");                            /* trung seq 6: gui lai phan hoi cu (5000) */
    snprintf(lab, sizeof(lab), "moc %lu: +3000 'STATUS' trung seq 6: tra lai nguyen phan hoi cu (khong tinh lai)", (unsigned long)t0);
    ok(rem_of(r) == 5000u, lab, r);
    r = p1(7, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: +3000 STATUS seq moi: remaining 4000", (unsigned long)t0);
    ok(rem_of(r) == 4000u, lab, r);
    p1(7, "LASER ON");                              /* trung seq 7 (lenh khac): gui lai phan hoi cu, khong dat lai hen gio */
    sim_set_tick(t0 + 4000u); p1(8, "HEARTBEAT");
    sim_set_tick(t0 + 5000u); p1(9, "HEARTBEAT");
    sim_set_tick(t0 + 6999u);
    r = p1(10, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: +6999 (ON hop le cuoi o +2000): remaining 1, van CAPTURING", (unsigned long)t0);
    ok(rem_of(r) == 1u && has(r, " CAPTURING ") && sim_pa8() == 1, lab, r);
    sim_set_tick(t0 + 7000u);
    r = p1(11, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: +7000: IDLE, LASER_TIMEOUT, remaining 0, PA8 thap", (unsigned long)t0);
    ok(rem_of(r) == 0u && has(r, " IDLE ") && has(r, " LASER_TIMEOUT 0*") && sim_pa8() == 0, lab, r);
    sim_set_tick(t0 + 8000u); p1(12, "LASER ON");
    sim_set_tick(t0 + 9500u);
    r = p1(13, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: ON seq moi o +8000, STATUS +9500: remaining 3500", (unsigned long)t0);
    ok(rem_of(r) == 3500u, lab, r);
    p1(14, "LASER OFF");
    r = p1(15, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: sau LASER OFF: IDLE, remaining 0", (unsigned long)t0);
    ok(rem_of(r) == 0u && has(r, " IDLE "), lab, r);
    p1(16, "LASER ON");
    p1(17, "STOP");
    r = p1(18, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: sau STOP: PAUSED, remaining 0", (unsigned long)t0);
    ok(rem_of(r) == 0u && has(r, " PAUSED "), lab, r);
    p1(19, "CLEAR");
    p1(20, "LASER ON");
    sim_set_inputs(1, 1); sim_poll(); take();
    r = p1(21, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: estop khi CAPTURING: ERROR ESTOP, remaining 0", (unsigned long)t0);
    ok(rem_of(r) == 0u && has(r, " ERROR ") && has(r, " ESTOP 0*"), lab, r);
    sim_set_inputs(1, 0); p1(22, "CLEAR");
    sim_set_tick(t0 + 20000u); p1(23, "LASER ON");
    at(t0 + 23000u);
    r = p1(24, "STATUS");
    snprintf(lab, sizeof(lab), "moc %lu: LINK_LOST: ERROR, remaining 0", (unsigned long)t0);
    ok(rem_of(r) == 0u && has(r, " LINK_LOST 0*"), lab, r);
    p1(25, "CLEAR");
  }
  snprintf(buf, sizeof(buf), "%d dong P1 da kiem, qua 64 byte %d", a_lines, a_toolong);
  ok(a_toolong == 0, "khong dong phan hoi nao vuot 64 byte ke ca LF", buf);
  scen_end("remaining_ms trong STATUS (D039): 5000 ngay sau ON, giam theo tick, HEARTBEAT/trung seq khong gia han, ON seq moi dat lai, 0 khi tat/het han/loi; qua tran uint32", 0);
}

static void invariants(void)
{
  char buf[600];
  g_viol_total += sim_pa8_violations();
  if (sim_pa8_violations() && !g_viol_note[0]) snprintf(g_viol_note, sizeof(g_viol_note), "%s", sim_viol_note());
  scen("TA", "bat bien toan bo phien test: PA8 chi cao khi CAPTURING (lich su GPIO); moi dong P1 dung checksum, <= 64 byte, ma loi thuoc Q3");
  snprintf(buf, sizeof(buf), "%lu vi pham %s", (unsigned long)g_viol_total, g_viol_note);
  ok(g_viol_total == 0u, "lich su ghi PA8: khong lan nao ghi muc cao ngoai CAPTURING", buf);
  snprintf(buf, sizeof(buf), "%d dong P1; checksum/khung sai %d; qua 64 byte %d; ma ngoai Q3 %d %s",
           a_lines, a_badchk, a_toolong, a_badcode, a_note);
  ok(a_badchk == 0 && a_toolong == 0, "moi dong phan hoi P1: khung '*hh' va checksum dung, <= 64 byte ke ca LF", buf);
  ok(a_badcode == 0, "moi ma 'ERROR <code>' bo gui ra deu co trong bang Q3 muc 3", buf);
  scen_end("bat bien toan bo phien test: PA8 chi cao khi CAPTURING; moi dong P1 dung checksum, <= 64 byte, ma loi thuoc Q3", 0);
}

int main(void)
{
  int i;
  printf("Tester C4 - ping_proto.c that + HAL gia rieng cua Tester (test/tester_c4_hal.c)\n");
  t1();
  t2();
  t3();
  t4();
  tx_extra();
  t_remaining();
  invariants();
  printf("\nMa        KQ    Kich ban\n");
  for (i = 0; i < g_nsum; i++) printf("%s\n", g_summary[i]);
  printf("\nTONG: %d PASS, %d FAIL, %d NOTE, %d kich ban\n", n_pass, n_fail, n_note, n_pass + n_fail + n_note);
  return n_fail ? 1 : 0;
}
