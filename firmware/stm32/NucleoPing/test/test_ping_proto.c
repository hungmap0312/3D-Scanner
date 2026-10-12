/*
 * test_ping_proto.c - chay ping_proto.c that tren PC voi HAL gia.
 *
 * Bao gom:
 * - Kiem tra hoi quy 100% cac ca cu (R07, R08, PING, ID?).
 * - Cac ca moi cho P1 theo tieu chi Tester C4 (T1, T2, T3, T4).
 */
#include "ping_proto.h"
#include "main.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* ---------------- HAL gia ---------------- */
GPIO_TypeDef fake_gpioa;
GPIO_TypeDef fake_gpioc;
uint32_t fake_rcc_flags = 0;

static UART_HandleTypeDef huart;
static char tx_log[8192];
static size_t tx_len;
static uint32_t fake_tick;
static int led_toggles;
static int iwdg_refreshes;

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *h, const uint8_t *p, uint16_t n, uint32_t to)
{
  (void)h; (void)to;
  if (tx_len + n < sizeof(tx_log)) {
    memcpy(&tx_log[tx_len], p, n);
    tx_len += n;
    tx_log[tx_len] = 0;
  }
  return HAL_OK;
}

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *h, uint8_t *p, uint16_t n)
{
  (void)n;
  if (h->receive_it_fail_next > 0) {
    h->receive_it_fail_next--;
    return HAL_BUSY;                 /* arm that bai: RxState van READY */
  }
  h->rx_dst = p;
  h->rx_armed = 1;
  h->RxState = HAL_UART_STATE_BUSY_RX;
  return HAL_OK;
}

uint32_t HAL_GetTick(void) { return fake_tick; }
void HAL_GPIO_TogglePin(GPIO_TypeDef *g, uint16_t pin) { (void)g; (void)pin; led_toggles++; }

void HAL_GPIO_WritePin(GPIO_TypeDef *g, uint16_t pin, GPIO_PinState state)
{
  if (state == GPIO_PIN_SET) {
    g->pin_state |= pin;
  } else {
    g->pin_state &= (uint16_t)(~pin);
  }
}

GPIO_PinState HAL_GPIO_ReadPin(GPIO_TypeDef *g, uint16_t pin)
{
  return (g->pin_state & pin) ? GPIO_PIN_SET : GPIO_PIN_RESET;
}

HAL_StatusTypeDef HAL_IWDG_Refresh(IWDG_HandleTypeDef *hiwdg)
{
  (void)hiwdg;
  iwdg_refreshes++;
  return HAL_OK;
}

/* Gia lap mot byte den tu UART: nhu HAL_UART_IRQHandler -> RxCpltCallback. */
static void rx_byte(uint8_t b)
{
  if (!huart.rx_armed) {
    return;                          /* khong arm: byte mat, khong callback */
  }
  *huart.rx_dst = b;
  huart.rx_armed = 0;
  huart.RxState = HAL_UART_STATE_READY;
  HAL_UART_RxCpltCallback(&huart);
}

static void rx_str(const char *s)
{
  while (*s) {
    rx_byte((uint8_t)*s++);
  }
}

static void rx_error(void)
{
  huart.rx_armed = 0;
  huart.RxState = HAL_UART_STATE_READY;
  HAL_UART_ErrorCallback(&huart);
}

static void reset_board(void)
{
  memset(&huart, 0, sizeof(huart));
  huart.gState = HAL_UART_STATE_READY;
  huart.RxState = HAL_UART_STATE_READY;
  tx_len = 0;
  tx_log[0] = 0;
  fake_tick = 1000;
  led_toggles = 0;
  iwdg_refreshes = 0;

  /* Mac dinh: Cua dong / co nguon (PA9 = 1), ESTOP khong nhan (PC7 = 0) */
  fake_gpioa.pin_state = SENSE_PWR_Pin;
  fake_gpioc.pin_state = 0;

  ping_init(&huart);
  tx_len = 0;                         /* bo dong BOOT */
  tx_log[0] = 0;
}

/* Gui mot dong, poll, tra ve phan hoi (tx_log tu dau). */
static const char *cmd(const char *line)
{
  tx_len = 0;
  tx_log[0] = 0;
  rx_str(line);
  ping_poll();
  return tx_log;
}

/* Tao chuoi lenh P1 co checksum XOR tu chuoi bat ky truoc dau '*' */
static void make_raw_p1_cmd(char *out, const char *body_before_star)
{
  uint8_t chk = 0;
  for (size_t i = 0; i < strlen(body_before_star); i++) {
    chk ^= (uint8_t)body_before_star[i];
  }
  sprintf(out, "%s*%02X\n", body_before_star, chk);
}

/* Tao chuoi lenh P1 co checksum XOR */
static void make_p1_cmd(char *out, uint16_t seq, const char *body)
{
  char tmp[64];
  snprintf(tmp, sizeof(tmp), "%u %s", seq, body);
  make_raw_p1_cmd(out, tmp);
}

/* ---------------- khung kiem ---------------- */
static int n_pass, n_fail;

static void check(int cond, const char *label, const char *got)
{
  if (cond) {
    n_pass++;
    printf("  PASS %s\n", label);
  } else {
    n_fail++;
    printf("  FAIL %s  (nhan: %s)\n", label, got ? got : "");
  }
}

static int starts(const char *s, const char *pre) { return strncmp(s, pre, strlen(pre)) == 0; }

int main(void)
{
  const char *r;
  char buf[80];

  printf("== ping_proto.c tren PC voi HAL gia (Regression + C4 P1) ==\n");

  /* ================= 1. Nhanh thuong legacy ================= */
  reset_board();
  r = cmd("PING 1\n");
  check(strcmp(r, "PONG 1 1000\n") == 0, "PING 1 -> PONG 1 <tick>", r);
  r = cmd("ID?\n");
  check(starts(r, "ID NUCLEO-F446RE NucleoPing 0.2.0"), "ID? -> ID NucleoPing 0.2.0 ...", r);
  r = cmd("PING 1\r\n");
  check(strcmp(r, "PONG 1 1000\n") == 0, "CRLF duoc chap nhan", r);
  r = cmd("PING\n");
  check(strcmp(r, "ERR badarg\n") == 0, "PING khong so -> ERR badarg", r);
  r = cmd("PING x\n");
  check(strcmp(r, "ERR badarg\n") == 0, "PING x -> ERR badarg", r);
  r = cmd("PING 12 \n");
  check(strcmp(r, "ERR badarg\n") == 0, "PING 12<space> -> ERR badarg", r);
  r = cmd("HELLO\n");
  check(strcmp(r, "ERR unknown\n") == 0, "lenh la -> ERR unknown", r);
  r = cmd("\n");
  check(strcmp(r, "") == 0, "dong rong -> im lang", r);
  r = cmd("PING 0\n");
  check(strcmp(r, "PONG 0 1000\n") == 0, "PING 0 -> PONG 0", r);

  /* ================= 2. R07: bien uint32 legacy ================= */
  r = cmd("PING 4294967295\n");
  check(strcmp(r, "PONG 4294967295 1000\n") == 0, "R07: PING 4294967295 (max) -> PONG", r);
  r = cmd("PING 4294967296\n");
  check(strcmp(r, "ERR badarg\n") == 0, "R07: PING 4294967296 (max+1) -> ERR badarg", r);
  r = cmd("PING 4294967299\n");
  check(strcmp(r, "ERR badarg\n") == 0, "R07: PING 4294967299 (max+4) -> ERR badarg", r);
  r = cmd("PING 4294967300\n");
  check(strcmp(r, "ERR badarg\n") == 0, "R07: PING 4294967300 -> ERR badarg", r);
  r = cmd("PING 99999999999\n");
  check(strcmp(r, "ERR badarg\n") == 0, "R07: 11 chu so -> ERR badarg", r);
  r = cmd("PING 0000000000005\n");
  check(strcmp(r, "ERR badarg\n") == 0, "hon 10 chu so ke ca so 0 dau -> ERR badarg", r);

  /* ================= 3. Dong qua dai legacy roi phuc hoi ================= */
  {
    char longline[80];
    memset(longline, 'A', 70);
    longline[70] = '\n';
    longline[71] = 0;
    r = cmd(longline);
    check(strcmp(r, "ERR toolong\n") == 0, "dong 70 byte -> ERR toolong", r);
    r = cmd("PING 2\n");
    check(strcmp(r, "PONG 2 1000\n") == 0, "sau toolong nhan lenh moi binh thuong", r);
  }

  /* ================= 4. R08: loi UART giua dong legacy ================= */
  reset_board();
  rx_str("PING 1");
  rx_error();
  rx_str("2\n");
  ping_poll();
  check(strcmp(tx_log, "ERR overrun\n") == 0, "R08: 'PING 1' + loi UART + '2' -> ERR overrun", tx_log);
  r = cmd("PING 3\n");
  check(strcmp(r, "PONG 3 1000\n") == 0, "R08: sau ERR overrun nhan lenh moi dung", r);

  /* ================= 5. R08: loi UART khi ring rong legacy ================= */
  reset_board();
  r = cmd("PING 1\n");
  rx_error();
  ping_poll();
  r = cmd("PING 2\n");
  check(strcmp(r, "ERR overrun\n") == 0, "R08: loi khi ring rong -> lenh ke tiep ERR overrun", r);
  r = cmd("PING 3\n");
  check(strcmp(r, "PONG 3 1000\n") == 0, "R08: roi lenh sau do lai dung", r);

  /* ================= 6. R08: ring day legacy ================= */
  reset_board();
  {
    int i;
    for (i = 0; i < 249; i++) {
      rx_byte('\n');
    }
    rx_str("PING 19");
    rx_str("2\n");
    ping_poll();
    check(ping_rx_overrun_count() == 3u, "R08: ring day dem 3 byte mat", tx_log);
    check(strcmp(tx_log, "") == 0, "R08: chua co LF sau cho dut -> chua tra gi", tx_log);
    r = cmd("PING 5\n");
    check(strcmp(r, "ERR overrun\n") == 0, "R08: dong ke tiep sau cho dut -> ERR overrun", r);
    r = cmd("PING 6\n");
    check(strcmp(r, "PONG 6 1000\n") == 0, "R08: phuc hoi sau do", r);
  }

  /* ================= 7. R08: truoc/sau cho dut legacy ================= */
  reset_board();
  rx_str("PING 7\n");
  rx_error();
  rx_str("PING 8\n");
  ping_poll();
  check(strcmp(tx_log, "PONG 7 1000\nERR overrun\n") == 0, "R08: PING 7 -> PONG; PING 8 -> ERR overrun", tx_log);
  r = cmd("PING 9\n");
  check(strcmp(r, "PONG 9 1000\n") == 0, "R08: lenh ke tiep dung", r);

  /* ================= 8. Arm lai RX tu poll ================= */
  reset_board();
  huart.receive_it_fail_next = 1;
  rx_str("P");
  check(huart.rx_armed == 0, "arm trong ISR that bai -> RX khong con arm", NULL);
  ping_poll();
  check(huart.rx_armed == 1 && ping_rx_rearm_count() == 1u, "poll arm lai RX, dem rearm = 1", NULL);
  rx_str("ING 9\n");
  ping_poll();
  check(strcmp(tx_log, "PONG 9 1000\n") == 0, "sau arm lai, phan con lai ghep dung", tx_log);

  /* ================= 9. LED nhay ================= */
  reset_board();
  fake_tick = 0xFFFFFFF0u;
  ping_init(&huart);
  led_toggles = 0;
  fake_tick = 0x000001F0u;
  ping_poll();
  check(led_toggles == 1, "LED toggle dung khi tick cuon qua 0", NULL);

  /* ================= T1: P1 BINH THUONG ================= */
  printf("-- T1: P1 Binh thuong --\n");
  reset_board();
  check(ping_get_laser_state() == 0, "T1: Sau khoi dong laser tat (PA8 = 0)", NULL);

  /* LASER ON */
  make_p1_cmd(buf, 1, "LASER ON");
  r = cmd(buf);
  check(starts(r, "1 DONE ON 5000*"), "T1: 1 LASER ON -> 1 DONE ON 5000*<HH>", r);
  check(ping_get_laser_state() == 1, "T1: Sau LASER ON, PA8 bat (muc 1)", NULL);
  check(strcmp(ping_get_state_str(), "CAPTURING") == 0, "T1: Trang thai vao CAPTURING", NULL);

  /* STATUS khi CAPTURING */
  make_p1_cmd(buf, 2, "STATUS");
  r = cmd(buf);
  check(starts(r, "2 DONE CAPTURING 0 1 1 0 0 1000 NONE 5000*"), "T1: STATUS khi CAPTURING dung dinh dang", r);

  /* LASER OFF */
  make_p1_cmd(buf, 3, "LASER OFF");
  r = cmd(buf);
  check(starts(r, "3 DONE OFF 0*"), "T1: 3 LASER OFF -> 3 DONE OFF 0*<HH>", r);
  check(ping_get_laser_state() == 0, "T1: Sau LASER OFF, PA8 tat (muc 0)", NULL);
  check(strcmp(ping_get_state_str(), "IDLE") == 0, "T1: Trang thai tro ve IDLE", NULL);

  /* STATUS khi IDLE */
  make_p1_cmd(buf, 4, "STATUS");
  r = cmd(buf);
  check(starts(r, "4 DONE IDLE 0 0 1 0 0 1000 NONE 0*"), "T1: STATUS khi IDLE dung dinh dang", r);

  /* ================= T2: BIEN (SEQ, TOOLONG, TIMEOUTS) ================= */
  printf("-- T2: Bien (Seq, Toolong, Timeouts) --\n");
  reset_board();

  /* Seq min = 1 */
  make_p1_cmd(buf, 1, "HEARTBEAT");
  r = cmd(buf);
  check(starts(r, "1 DONE IDLE*"), "T2: Seq 1 hop le", r);

  /* Seq max = 65535 */
  make_p1_cmd(buf, 65535, "HEARTBEAT");
  r = cmd(buf);
  check(starts(r, "65535 DONE IDLE*"), "T2: Seq 65535 hop le", r);

  /* Seq 0 bi tu choi */
  make_raw_p1_cmd(buf, "0 HEARTBEAT");
  r = cmd(buf);
  check(starts(r, "0 ERROR BADARG*"), "T2: Seq 0 bi tu choi -> 0 ERROR BADARG", r);

  /* Seq 65536 bi tu choi */
  make_raw_p1_cmd(buf, "65536 HEARTBEAT");
  r = cmd(buf);
  check(starts(r, "0 ERROR BADARG*"), "T2: Seq 65536 bi tu choi -> 0 ERROR BADARG", r);

  /* Dong dung 64 byte hop le */
  {
    /* "50 HEARTBEAT                                                   *06\n" */
    char exact64[65];
    memset(exact64, ' ', 63);
    exact64[63] = '\n';
    exact64[64] = 0;
    memcpy(exact64, "50 HEARTBEAT ", 13);
    exact64[60] = '*';
    uint8_t chk = 0;
    for (int k = 0; k < 60; k++) chk ^= (uint8_t)exact64[k];
    sprintf(&exact64[61], "%02X\n", chk);
    r = cmd(exact64);
    check(starts(r, "50 DONE IDLE*"), "T2: Dong dung 64 byte duoc chap nhan", r);
  }

  /* Dong > 64 byte P1 -> 0 ERROR TOOLONG */
  {
    char long_p1[80];
    memset(long_p1, ' ', 75);
    long_p1[75] = '\n';
    long_p1[76] = 0;
    memcpy(long_p1, "51 HEARTBEAT", 12);
    r = cmd(long_p1);
    check(starts(r, "0 ERROR TOOLONG*"), "T2: Dong P1 > 64 byte -> 0 ERROR TOOLONG", r);
  }

  /* Timeout Heartbeat 3000 ms */
  reset_board();
  fake_tick = 1000;
  make_p1_cmd(buf, 100, "LASER ON");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T2: Laser ON o tick 1000", NULL);

  fake_tick = 3999; /* Da qua 2999 ms, chua toi 3000 ms */
  ping_poll();
  check(ping_get_laser_state() == 1 && strcmp(ping_get_state_str(), "CAPTURING") == 0,
        "T2: 2999 ms chua den han LINK_LOST, laser van bat", NULL);

  fake_tick = 4000; /* Dung 3000 ms im lang */
  ping_poll();
  check(ping_get_laser_state() == 0, "T2: Dung 3000 ms im lang -> PA8 ha muc thap", NULL);
  check(strcmp(ping_get_state_str(), "ERROR") == 0, "T2: Chuyen sang ERROR", NULL);
  check(strcmp(ping_get_last_error_str(), "LINK_LOST") == 0, "T2: last_err = LINK_LOST", NULL);

  /* Timeout Laser Max 5000 ms (co Heartbeat deu dan) */
  reset_board();
  fake_tick = 1000;
  make_p1_cmd(buf, 101, "LASER ON");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T2: Laser ON o tick 1000", NULL);

  /* Gui Heartbeat moi 1000 ms */
  fake_tick = 2000;
  make_p1_cmd(buf, 102, "HEARTBEAT");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T2: Tick 2000 nhan Heartbeat, laser van bat", NULL);

  fake_tick = 3000;
  make_p1_cmd(buf, 103, "HEARTBEAT");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T2: Tick 3000 nhan Heartbeat, laser van bat", NULL);

  fake_tick = 4000;
  make_p1_cmd(buf, 104, "HEARTBEAT");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T2: Tick 4000 nhan Heartbeat, laser van bat", NULL);

  fake_tick = 5000;
  make_p1_cmd(buf, 105, "HEARTBEAT");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T2: Tick 5000 nhan Heartbeat, laser van bat", NULL);

  fake_tick = 5999; /* 4999 ms tu luc LASER ON */
  ping_poll();
  check(ping_get_laser_state() == 1 && strcmp(ping_get_state_str(), "CAPTURING") == 0,
        "T2: 4999 ms chua den han LASER_TIMEOUT, laser van bat", NULL);

  fake_tick = 6000; /* Dung 5000 ms tu luc LASER ON */
  ping_poll();
  check(ping_get_laser_state() == 0, "T2: Dung 5000 ms -> PA8 ha muc thap", NULL);
  check(strcmp(ping_get_state_str(), "IDLE") == 0, "T2: Tro ve IDLE (khong phai ERROR)", NULL);
  check(strcmp(ping_get_last_error_str(), "LASER_TIMEOUT") == 0, "T2: last_err = LASER_TIMEOUT", NULL);

  /* ================= T3: DAU VAO LOI & CHONG LAP LENH ================= */
  printf("-- T3: Dau vao loi & Chong lap lenh --\n");
  reset_board();

  /* Sai checksum */
  r = cmd("200 LASER ON*00\n");
  check(starts(r, "200 ERROR BADCHK*"), "T3: Sai checksum -> 200 ERROR BADCHK", r);
  check(ping_get_laser_state() == 0, "T3: Laser van tat sau sai checksum", NULL);

  /* Checksum sai dinh dang */
  r = cmd("201 LASER ON*XYZ\n");
  check(starts(r, "0 ERROR BADCHK*"), "T3: Checksum khong phai 2 hex -> 0 ERROR BADCHK", r);

  /* Thua / thieu doi so */
  make_p1_cmd(buf, 202, "LASER");
  r = cmd(buf);
  check(starts(r, "202 ERROR BADARG*"), "T3: LASER thieu arg -> ERROR BADARG", r);

  make_p1_cmd(buf, 203, "LASER ON EXTRA");
  r = cmd(buf);
  check(starts(r, "203 ERROR BADARG*"), "T3: LASER ON thua arg -> ERROR BADARG", r);

  make_p1_cmd(buf, 204, "STATUS EXTRA");
  r = cmd(buf);
  check(starts(r, "204 ERROR BADARG*"), "T3: STATUS thua arg -> ERROR BADARG", r);

  make_p1_cmd(buf, 205, "HEARTBEAT EXTRA");
  r = cmd(buf);
  check(starts(r, "205 ERROR BADARG*"), "T3: HEARTBEAT thua arg -> ERROR BADARG", r);

  make_p1_cmd(buf, 206, "STOP EXTRA");
  r = cmd(buf);
  check(starts(r, "206 ERROR BADARG*"), "T3: STOP thua arg -> ERROR BADARG", r);

  make_p1_cmd(buf, 207, "CLEAR EXTRA");
  r = cmd(buf);
  check(starts(r, "207 ERROR BADARG*"), "T3: CLEAR thua arg -> ERROR BADARG", r);

  /* Lenh la */
  make_p1_cmd(buf, 208, "UNKNOWNCMD");
  r = cmd(buf);
  check(starts(r, "208 ERROR UNKNOWN*"), "T3: Lenh khong biet -> ERROR UNKNOWN", r);

  /* HOME / MOVE_ABS -> NOTIMPL */
  make_p1_cmd(buf, 209, "HOME");
  r = cmd(buf);
  check(starts(r, "209 ERROR NOTIMPL*"), "T3: HOME -> ERROR NOTIMPL", r);

  make_p1_cmd(buf, 210, "MOVE_ABS 40");
  r = cmd(buf);
  check(starts(r, "210 ERROR NOTIMPL*"), "T3: MOVE_ABS -> ERROR NOTIMPL", r);

  /* Chong lap lenh (Duplicate Seq): gui lap 10 lan */
  make_p1_cmd(buf, 300, "LASER ON");
  r = cmd(buf);
  check(starts(r, "300 DONE ON 5000*"), "T3: Lan 1 LASER ON thanh cong", r);
  char cached_resp[64];
  strcpy(cached_resp, r);

  /* Tang tick len 3000 */
  fake_tick = 3000;
  int dup_ok = 1;
  for (int k = 0; k < 10; k++) {
    r = cmd(buf);
    if (strcmp(r, cached_resp) != 0) {
      dup_ok = 0;
    }
  }
  check(dup_ok, "T3: Duplicate seq 10 lan deu tra lai nguyen van cached response", NULL);

  /* Gui heartbeat o tick 4500 de duy tri lien lac (khong bi LINK_LOST tai tick 6000) */
  fake_tick = 4500;
  char hb_buf[64];
  make_p1_cmd(hb_buf, 301, "HEARTBEAT");
  cmd(hb_buf);

  /* Kiem tra timer laser khong bi duplicate seq reset: tai 6000 ms (5000 ms tu luc bat o tick 1000) */
  fake_tick = 6000;
  ping_poll();
  check(ping_get_laser_state() == 0 && strcmp(ping_get_last_error_str(), "LASER_TIMEOUT") == 0,
        "T3: Duplicate seq khong gia han laser timer (laser tat dung tai 5000 ms dau)", NULL);

  /* ================= T4: THIET BI & LOI PHAN CUNG ================= */
  printf("-- T4: Thiet bi & Loi phan cung --\n");
  reset_board();

  /* 1. Nhan nut ESTOP (PC7 = 1) */
  fake_gpioc.pin_state = SENSE_ESTOP_Pin;
  make_p1_cmd(buf, 401, "LASER ON");
  r = cmd(buf);
  check(starts(r, "401 ERROR ESTOP*"), "T4: Khi ESTOP nhan, tu choi LASER ON -> ERROR ESTOP", r);
  check(ping_get_laser_state() == 0, "T4: PA8 van giu muc thap", NULL);

  /* Nhan ESTOP khi dang CAPTURING */
  fake_gpioc.pin_state = 0;
  make_p1_cmd(buf, 402, "CLEAR");
  cmd(buf);
  make_p1_cmd(buf, 403, "LASER ON");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T4: Bat laser truoc", NULL);

  fake_gpioc.pin_state = SENSE_ESTOP_Pin; /* ESTOP kich hoat! */
  ping_poll();
  check(ping_get_laser_state() == 0, "T4: ESTOP ngat -> PA8 ha ngay", NULL);
  check(strcmp(ping_get_state_str(), "ERROR") == 0, "T4: Chuyen sang ERROR", NULL);
  check(strcmp(ping_get_last_error_str(), "ESTOP") == 0, "T4: last_err = ESTOP", NULL);

  /* Thu CLEAR khi ESTOP van nhan */
  make_p1_cmd(buf, 404, "CLEAR");
  r = cmd(buf);
  check(starts(r, "404 ERROR ESTOP*"), "T4: CLEAR khi ESTOP van bi nhan -> ERROR ESTOP", r);

  /* Nha ESTOP roi CLEAR */
  fake_gpioc.pin_state = 0;
  make_p1_cmd(buf, 405, "CLEAR");
  r = cmd(buf);
  check(starts(r, "405 DONE IDLE*"), "T4: Nha ESTOP roi CLEAR -> DONE IDLE", r);
  check(strcmp(ping_get_state_str(), "IDLE") == 0, "T4: State ve IDLE", NULL);

  /* 2. Cua an toan mo (PA9 = 0) */
  fake_gpioa.pin_state = 0; /* Mat nguon/Cua mo */
  make_p1_cmd(buf, 406, "LASER ON");
  r = cmd(buf);
  check(starts(r, "406 ERROR DOOR_OPEN*"), "T4: Cua mo -> tu choi LASER ON", r);

  fake_gpioa.pin_state = SENSE_PWR_Pin; /* Dong cua */
  make_p1_cmd(buf, 407, "CLEAR");
  cmd(buf);
  make_p1_cmd(buf, 408, "LASER ON");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T4: Bat laser thanh cong", NULL);

  fake_gpioa.pin_state = 0; /* Mo cua khi dang CAPTURING */
  ping_poll();
  check(ping_get_laser_state() == 0, "T4: Cua mo -> PA8 ha ngay", NULL);
  check(strcmp(ping_get_state_str(), "ERROR") == 0, "T4: Chuyen sang ERROR", NULL);
  check(strcmp(ping_get_last_error_str(), "DOOR_OPEN") == 0, "T4: last_err = DOOR_OPEN", NULL);

  /* 3. Lenh STOP */
  fake_gpioa.pin_state = SENSE_PWR_Pin;
  make_p1_cmd(buf, 409, "CLEAR");
  cmd(buf);
  make_p1_cmd(buf, 410, "LASER ON");
  cmd(buf);
  check(ping_get_laser_state() == 1, "T4: Bat laser", NULL);

  make_p1_cmd(buf, 411, "STOP");
  r = cmd(buf);
  check(starts(r, "411 DONE PAUSED*"), "T4: Lenh STOP -> 411 DONE PAUSED", r);
  check(ping_get_laser_state() == 0, "T4: PA8 tat sau STOP", NULL);

  make_p1_cmd(buf, 412, "CLEAR");
  r = cmd(buf);
  check(starts(r, "412 DONE IDLE*"), "T4: CLEAR tu PAUSED -> DONE IDLE", r);

  /* 4. Watchdog reset simulation */
  fake_rcc_flags = RCC_FLAG_IWDGRST;
  reset_board();
  check(strcmp(ping_get_last_error_str(), "WDG_RESET") == 0, "T4: Watchdog reset dat last_err = WDG_RESET", NULL);
  check(ping_get_laser_state() == 0, "T4: Watchdog reset thi PA8 muc thap", NULL);

  /* IWDG refresh service */
  IWDG_HandleTypeDef test_iwdg;
  ping_set_iwdg(&test_iwdg);
  int before_ref = iwdg_refreshes;
  ping_poll();
  check(iwdg_refreshes == before_ref + 1, "T4: ping_poll() refresh IWDG watchdog", NULL);

  /* ================= T5 (VONG 7): REMAINING_MS & 64-BYTE FRAME (R02) ================= */
  printf("-- T5 (Vong 7): remaining_ms & 64-byte frame (R02) --\n");
  reset_board();

  /* 1. ON tai tick 1000: remaining = 5000 */
  fake_tick = 1000;
  make_p1_cmd(buf, 10, "LASER ON");
  cmd(buf);
  make_p1_cmd(buf, 11, "STATUS");
  r = cmd(buf);
  check(starts(r, "11 DONE CAPTURING 0 1 1 0 0 1000 NONE 5000*"), "V7: STATUS ngay sau ON: remaining = 5000", r);

  /* 2. Qua 1000 ms (tick 2000): remaining = 4000 */
  fake_tick = 2000;
  make_p1_cmd(buf, 12, "STATUS");
  r = cmd(buf);
  check(starts(r, "12 DONE CAPTURING 0 1 1 0 0 2000 NONE 4000*"), "V7: STATUS sau 1000 ms: remaining = 4000", r);

  /* 3. HEARTBEAT o tick 2000: khong lam gia han remaining_ms */
  make_p1_cmd(buf, 13, "HEARTBEAT");
  cmd(buf);
  make_p1_cmd(buf, 14, "STATUS");
  r = cmd(buf);
  check(starts(r, "14 DONE CAPTURING 0 1 1 0 0 2000 NONE 4000*"), "V7: HEARTBEAT khong lam gia han remaining_ms (van 4000)", r);

  /* 4. Duplicate seq LASER ON: gia lap gui lai cung seq 10 o tick 2000 */
  reset_board();
  fake_tick = 1000;
  make_p1_cmd(buf, 10, "LASER ON");
  cmd(buf);
  fake_tick = 2000;
  /* Gui lai dung seq 10 (duplicate) */
  make_p1_cmd(buf, 10, "LASER ON");
  cmd(buf);
  /* STATUS voi seq 11 o tick 2000: remaining van phai la 4000 (khong bi gia han ve 5000) */
  make_p1_cmd(buf, 11, "STATUS");
  r = cmd(buf);
  check(starts(r, "11 DONE CAPTURING 0 1 1 0 0 2000 NONE 4000*"), "V7: Duplicate seq khong lam gia han remaining_ms", r);

  /* 5. Gui HEARTBEAT deu moi 1000 ms, kiem tra tai tick 5999 (4999 ms tu ON): remaining = 1 */
  fake_tick = 3000;
  make_p1_cmd(buf, 12, "HEARTBEAT");
  cmd(buf);
  fake_tick = 4000;
  make_p1_cmd(buf, 13, "HEARTBEAT");
  cmd(buf);
  fake_tick = 5000;
  make_p1_cmd(buf, 14, "HEARTBEAT");
  cmd(buf);

  fake_tick = 5999;
  make_p1_cmd(buf, 15, "STATUS");
  r = cmd(buf);
  check(starts(r, "15 DONE CAPTURING 0 1 1 0 0 5999 NONE 1*"), "V7: STATUS o 4999 ms: remaining = 1", r);

  /* 6. Dung 5000 ms tu ON (tick 6000): poll() tat laser, ve IDLE, remaining = 0 */
  fake_tick = 6000;
  ping_poll();
  make_p1_cmd(buf, 16, "STATUS");
  r = cmd(buf);
  check(starts(r, "16 DONE IDLE 0 0 1 0 0 6000 LASER_TIMEOUT 0*"), "V7: STATUS sau timeout 5000 ms: IDLE, LASER_TIMEOUT, remaining = 0", r);

  /* 7. Tick wrap xung quanh uint32 max */
  reset_board();
  fake_tick = 0xFFFFFFF0u;
  make_p1_cmd(buf, 20, "LASER ON");
  cmd(buf);
  fake_tick = 0x00000010u; /* wrap qua 0, elapsed = 32 ms */
  make_p1_cmd(buf, 21, "STATUS");
  r = cmd(buf);
  check(starts(r, "21 DONE CAPTURING 0 1 1 0 0 16 NONE 4968*"), "V7: Tick wrap qua 0: remaining_ms = 4968 ms tinh dung", r);

  /* 8. Khung STATUS dai nhat (seq 65535, uptime 4294967295, CAPTURING, last_err LASER_TIMEOUT, remaining 5000) */
  reset_board();
  fake_tick = 1000;
  make_p1_cmd(buf, 1, "LASER ON");
  cmd(buf);
  fake_tick = 2000; make_p1_cmd(buf, 2, "HEARTBEAT"); cmd(buf);
  fake_tick = 3000; make_p1_cmd(buf, 3, "HEARTBEAT"); cmd(buf);
  fake_tick = 4000; make_p1_cmd(buf, 4, "HEARTBEAT"); cmd(buf);
  fake_tick = 5000; make_p1_cmd(buf, 5, "HEARTBEAT"); cmd(buf);
  fake_tick = 6000;
  ping_poll(); /* State -> IDLE, last_err -> LASER_TIMEOUT */

  /* Bat lai laser tai tick 4294967295 (last_err van la LASER_TIMEOUT) */
  fake_tick = 4294967295u;
  make_p1_cmd(buf, 6, "LASER ON");
  cmd(buf);
  /* Gui STATUS voi seq 65535 */
  make_p1_cmd(buf, 65535, "STATUS");
  r = cmd(buf);
  check(strlen(r) == 64u, "V7: Khung STATUS dai nhat dung 64 byte ca LF", r);
  check(strcmp(r, "65535 DONE CAPTURING 0 1 1 0 0 4294967295 LASER_TIMEOUT 5000*04\n") == 0,
        "V7: Khung STATUS dai nhat nguyen ven, checksum dung *04", r);

  printf("== %d PASS, %d FAIL ==\n", n_pass, n_fail);
  return n_fail == 0 ? 0 : 1;
}
