/* Xem mo ta giao thuc trong ping_proto.h va docs/design/NUCLEO_PROTOCOL.md. */
#include "ping_proto.h"
#include "fw_version.h"
#include "main.h"

#include <stdint.h>
#include <string.h>

#define RX_RING_SIZE 256u   /* luy thua 2, xem rx_ring_push */
#define TX_TIMEOUT_MS 100u
#define LED_PERIOD_MS 500u

typedef enum {
  STATE_IDLE = 0,
  STATE_CAPTURING,
  STATE_PAUSED,
  STATE_ERROR
} fsm_state_t;

static UART_HandleTypeDef *s_uart;
static IWDG_HandleTypeDef *s_iwdg;

/* Ring buffer: ISR ghi, vong lap chinh doc. Chi so kieu volatile. */
static uint8_t s_ring[RX_RING_SIZE];
static volatile uint16_t s_ring_head;   /* ISR ghi */
static volatile uint16_t s_ring_tail;   /* main doc */
static volatile uint32_t s_rx_overrun;  /* ISR: dem su kien mat/hong byte (ring day, loi UART) */
static uint32_t s_rx_overrun_seen;      /* main: gia tri s_rx_overrun da xu ly */
static volatile uint16_t s_loss_pos;    /* ISR: vi tri ring cua byte dau tien SAU cho dut */
static volatile uint8_t s_loss_pending; /* ISR dat, main xoa: s_loss_pos con hieu luc */
static uint32_t s_rx_rearm;             /* main: so lan phai arm lai RX tu poll (chan doan) */
static uint8_t s_rx_byte;               /* dich cua HAL_UART_Receive_IT */

/* Dong dang gop */
static char s_line[PING_LINE_MAX + 1u];
static uint16_t s_line_len;
static uint8_t s_line_overflow;
static uint8_t s_line_broken;           /* R08: dong hien tai chua doan mat byte -> bo toi LF */
static uint8_t s_line_was_p1;           /* L02: dong bi mat/hong byte thuoc khung P1 */

static uint32_t s_led_next;

/* Trang thai FSM va thoi gian */
static fsm_state_t s_state = STATE_IDLE;
static const char *s_last_err = "NONE";
static const char *s_reset_cause = "OTHER";
static uint32_t s_last_msg_tick;
static uint32_t s_laser_on_tick;

/* Cache chong lap lenh P1 (duplicate seq) */
static uint16_t s_last_p1_seq = 0u;
static char s_last_p1_resp[PING_LINE_MAX + 1u];
static uint16_t s_last_p1_resp_len = 0u;

/* Thao tac GPIO an toan */
static inline void laser_pin_set(uint8_t on)
{
  HAL_GPIO_WritePin(LASER_GPIO_Port, LASER_Pin, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static inline uint8_t laser_pin_read(void)
{
  return (HAL_GPIO_ReadPin(LASER_GPIO_Port, LASER_Pin) == GPIO_PIN_SET) ? 1u : 0u;
}

static inline uint8_t estop_pin_read(void)
{
  /* Tiếp điểm NC kéo xuống GND: 0 là bình thường, 1 là hở/nhấn dừng */
  return (HAL_GPIO_ReadPin(SENSE_ESTOP_GPIO_Port, SENSE_ESTOP_Pin) == GPIO_PIN_SET) ? 1u : 0u;
}

static inline uint8_t door_pin_read(void)
{
  /* PA9 qua cầu phân áp: 1 là có nguồn/cửa đóng, 0 là mất nguồn/cửa mở */
  return (HAL_GPIO_ReadPin(SENSE_PWR_GPIO_Port, SENSE_PWR_Pin) == GPIO_PIN_SET) ? 1u : 0u;
}

void ping_early_safety_init(void)
{
  __HAL_RCC_GPIOA_CLK_ENABLE();
  laser_pin_set(0);
}

void ping_set_iwdg(IWDG_HandleTypeDef *hiwdg)
{
  s_iwdg = hiwdg;
}

const char *ping_get_state_str(void)
{
  switch (s_state) {
    case STATE_IDLE:      return "IDLE";
    case STATE_CAPTURING: return "CAPTURING";
    case STATE_PAUSED:    return "PAUSED";
    case STATE_ERROR:     return "ERROR";
    default:              return "UNKNOWN";
  }
}

const char *ping_get_last_error_str(void)
{
  return s_last_err;
}

uint8_t ping_get_laser_state(void)
{
  return laser_pin_read();
}

static void tx_str(const char *s)
{
  HAL_UART_Transmit(s_uart, (const uint8_t *)s, (uint16_t)strlen(s), TX_TIMEOUT_MS);
}

/* Ghi so khong dau ra chuoi thap phan; tra ve so ky tu. buf can >= 11 byte. */
static uint16_t u32_to_dec(uint32_t v, char *buf)
{
  char tmp[10];
  uint16_t n = 0u;
  uint16_t i;
  do {
    tmp[n++] = (char)('0' + (v % 10u));
    v /= 10u;
  } while (v != 0u);
  for (i = 0u; i < n; i++) {
    buf[i] = tmp[n - 1u - i];
  }
  buf[n] = 0;
  return n;
}

/* Doc so thap phan tu p; tra ve 1 neu hop le va het chuoi ngay sau so. */
static uint8_t parse_u32(const char *p, uint32_t *out)
{
  uint32_t v = 0u;
  uint16_t digits = 0u;
  while (*p >= '0' && *p <= '9') {
    uint32_t d = (uint32_t)(*p - '0');
    if (v > (UINT32_MAX - d) / 10u) {
      return 0u; /* v * 10 + d se vuot uint32 */
    }
    v = v * 10u + d;
    p++;
    digits++;
  }
  if (digits == 0u || digits > 10u || *p != 0) {
    return 0u;
  }
  *out = v;
  return 1u;
}

/* Tinh checksum XOR 8-bit */
static uint8_t calc_xor_checksum(const char *s, uint16_t len)
{
  uint8_t chk = 0;
  for (uint16_t i = 0u; i < len; i++) {
    chk ^= (uint8_t)s[i];
  }
  return chk;
}

static char hex_digit(uint8_t val)
{
  val &= 0x0Fu;
  return (val < 10u) ? (char)('0' + val) : (char)('A' + (val - 10u));
}

static int parse_hex_byte(char h, char l, uint8_t *out)
{
  uint8_t hi, lo;
  if (h >= '0' && h <= '9') hi = (uint8_t)(h - '0');
  else if (h >= 'A' && h <= 'F') hi = (uint8_t)(h - 'A' + 10);
  else if (h >= 'a' && h <= 'f') hi = (uint8_t)(h - 'a' + 10);
  else return 0;

  if (l >= '0' && l <= '9') lo = (uint8_t)(l - '0');
  else if (l >= 'A' && l <= 'F') lo = (uint8_t)(l - 'A' + 10);
  else if (l >= 'a' && l <= 'f') lo = (uint8_t)(l - 'a' + 10);
  else return 0;

  *out = (uint8_t)((hi << 4u) | lo);
  return 1;
}

/* Gui phan hoi P1 voi seq va noi dung body, kem *<HH>\n va luu vao cache neu save_cache != 0 va seq != 0 */
static void send_p1_response(uint16_t seq, const char *body, uint8_t save_cache)
{
  char resp[PING_LINE_MAX + 1u];
  uint16_t n = 0u;

  n += u32_to_dec(seq, &resp[n]);
  resp[n++] = ' ';

  uint16_t body_len = (uint16_t)strlen(body);
  if (n + body_len + 4u > PING_LINE_MAX) {
    /* Qua dai, gioi han de khong tran buffer (chua dung 4 byte cho *HH\n) */
    body_len = PING_LINE_MAX - n - 4u;
  }
  memcpy(&resp[n], body, body_len);
  n += body_len;

  uint8_t chk = calc_xor_checksum(resp, n);
  resp[n++] = '*';
  resp[n++] = hex_digit(chk >> 4u);
  resp[n++] = hex_digit(chk & 0x0Fu);
  resp[n++] = '\n';
  resp[n] = 0;

  if (save_cache && seq != 0u) {
    s_last_p1_seq = seq;
    memcpy(s_last_p1_resp, resp, n + 1u);
    s_last_p1_resp_len = n;
  }

  tx_str(resp);
}

/* ISR: ghi nhan mat/hong byte. */
static void note_loss_isr(void)
{
  if (!s_loss_pending) {
    s_loss_pos = s_ring_head;
    s_loss_pending = 1u;
  }
  s_rx_overrun++;
}

static void arm_rx(void)
{
  (void)HAL_UART_Receive_IT(s_uart, &s_rx_byte, 1u);
}

void ping_init(UART_HandleTypeDef *huart)
{
  s_uart = huart;
  s_ring_head = 0u;
  s_ring_tail = 0u;
  s_rx_overrun = 0u;
  s_rx_overrun_seen = 0u;
  s_loss_pos = 0u;
  s_loss_pending = 0u;
  s_rx_rearm = 0u;
  s_line_len = 0u;
  s_line_overflow = 0u;
  s_line_broken = 0u;
  s_line_was_p1 = 0u;
  s_led_next = HAL_GetTick() + LED_PERIOD_MS;

  s_state = STATE_IDLE;
  s_last_p1_seq = 0u;
  s_last_p1_resp_len = 0u;
  s_laser_on_tick = 0u;
  s_last_msg_tick = HAL_GetTick();

  /* Kiem tra co reset */
  if (__HAL_RCC_GET_FLAG(RCC_FLAG_IWDGRST)) {
    s_reset_cause = "WDG_RESET";
    s_last_err = "WDG_RESET";
  } else if (__HAL_RCC_GET_FLAG(RCC_FLAG_PORRST)) {
    s_reset_cause = "POWER_ON";
    s_last_err = "NONE";
  } else if (__HAL_RCC_GET_FLAG(RCC_FLAG_PINRST)) {
    s_reset_cause = "PIN_RESET";
    s_last_err = "NONE";
  } else if (__HAL_RCC_GET_FLAG(RCC_FLAG_SFTRST)) {
    s_reset_cause = "SOFTWARE";
    s_last_err = "NONE";
  } else {
    s_reset_cause = "OTHER";
    s_last_err = "NONE";
  }
  __HAL_RCC_CLEAR_RESET_FLAGS();

  laser_pin_set(0);
  arm_rx();

  char boot_msg[64];
  strcpy(boot_msg, "BOOT NucleoPing " FW_VERSION " " FW_GIT_HASH " P1 RESET=");
  strcat(boot_msg, s_reset_cause);
  strcat(boot_msg, "\n");
  tx_str(boot_msg);
}

uint32_t ping_rx_overrun_count(void)
{
  return s_rx_overrun;
}

uint32_t ping_rx_rearm_count(void)
{
  return s_rx_rearm;
}

/* ISR context */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart != s_uart) {
    return;
  }
  uint16_t next = (uint16_t)((s_ring_head + 1u) & (RX_RING_SIZE - 1u));
  if (next != s_ring_tail) {
    s_ring[s_ring_head] = s_rx_byte;
    s_ring_head = next;
  } else {
    note_loss_isr();
  }
  arm_rx();
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
  if (huart != s_uart) {
    return;
  }
  note_loss_isr();
  __HAL_UART_CLEAR_OREFLAG(huart);
  arm_rx();
}

/* Xu ly lenh P1 da xac nhan checksum va seq */
static void handle_p1_command(uint16_t seq, char *cmd_str)
{
  /* Tach lenh va cac doi so bang khoang trang */
  char *cmd = cmd_str;
  while (*cmd == ' ') cmd++;
  if (*cmd == '\0') {
    send_p1_response(seq, "ERROR BADARG", 1u);
    return;
  }

  char *p_space = strchr(cmd, ' ');
  char *arg1 = NULL;
  char *arg2 = NULL;
  if (p_space != NULL) {
    *p_space = '\0';
    arg1 = p_space + 1;
    while (*arg1 == ' ') arg1++;
    if (*arg1 == '\0') {
      arg1 = NULL;
    } else {
      char *p_space2 = strchr(arg1, ' ');
      if (p_space2 != NULL) {
        *p_space2 = '\0';
        arg2 = p_space2 + 1;
        while (*arg2 == ' ') arg2++;
        if (*arg2 == '\0') {
          arg2 = NULL;
        }
      }
    }
  }

  /* 1. LASER ON/OFF */
  if (strcmp(cmd, "LASER") == 0) {
    if (arg1 == NULL || arg2 != NULL) {
      send_p1_response(seq, "ERROR BADARG", 1u);
      return;
    }
    if (strcmp(arg1, "ON") == 0) {
      /* Kiem tra an toan */
      if (estop_pin_read() == 1u) {
        laser_pin_set(0);
        s_state = STATE_ERROR;
        s_last_err = "ESTOP";
        send_p1_response(seq, "ERROR ESTOP", 1u);
        return;
      }
      if (door_pin_read() == 0u) {
        laser_pin_set(0);
        s_state = STATE_ERROR;
        s_last_err = "DOOR_OPEN";
        send_p1_response(seq, "ERROR DOOR_OPEN", 1u);
        return;
      }
      if (s_state == STATE_ERROR) {
        send_p1_response(seq, "ERROR IN_ERROR", 1u);
        return;
      }
      if (s_state == STATE_PAUSED) {
        send_p1_response(seq, "ERROR BUSY", 1u);
        return;
      }

      /* IDLE hoac CAPTURING deu bat laser va dat lai hen gio 5000 ms */
      s_state = STATE_CAPTURING;
      s_laser_on_tick = HAL_GetTick();
      laser_pin_set(1);
      send_p1_response(seq, "DONE ON 5000", 1u);
      return;
    } else if (strcmp(arg1, "OFF") == 0) {
      laser_pin_set(0);
      if (s_state == STATE_CAPTURING) {
        s_state = STATE_IDLE;
      }
      send_p1_response(seq, "DONE OFF 0", 1u);
      return;
    } else {
      send_p1_response(seq, "ERROR BADARG", 1u);
      return;
    }
  }

  /* 2. STATUS */
  if (strcmp(cmd, "STATUS") == 0) {
    if (arg1 != NULL) {
      send_p1_response(seq, "ERROR BADARG", 1u);
      return;
    }
    char status_body[PING_LINE_MAX];
    uint16_t n = 0u;
    memcpy(&status_body[n], "DONE ", 5u); n += 5u;
    const char *st_str = ping_get_state_str();
    uint16_t slen = (uint16_t)strlen(st_str);
    memcpy(&status_body[n], st_str, slen); n += slen;
    status_body[n++] = ' ';

    /* step_count = 0 */
    status_body[n++] = '0';
    status_body[n++] = ' ';

    /* laser 0/1 */
    status_body[n++] = (char)('0' + laser_pin_read());
    status_body[n++] = ' ';

    /* door 0/1 */
    status_body[n++] = (char)('0' + door_pin_read());
    status_body[n++] = ' ';

    /* estop 0/1 */
    status_body[n++] = (char)('0' + estop_pin_read());
    status_body[n++] = ' ';

    /* homed = 0 */
    status_body[n++] = '0';
    status_body[n++] = ' ';

    /* uptime_ms */
    n += u32_to_dec(HAL_GetTick(), &status_body[n]);
    status_body[n++] = ' ';

    /* last_err */
    slen = (uint16_t)strlen(s_last_err);
    memcpy(&status_body[n], s_last_err, slen); n += slen;

    /* remaining_ms (D039): 0 khi laser tat; max(0, 5000 - elapsed) khi CAPTURING */
    status_body[n++] = ' ';
    uint32_t rem_ms = 0u;
    if (s_state == STATE_CAPTURING) {
      uint32_t now = HAL_GetTick();
      uint32_t elapsed = now - s_laser_on_tick;
      if (elapsed < PING_T_LASER_MAX_MS) {
        rem_ms = PING_T_LASER_MAX_MS - elapsed;
      }
    }
    n += u32_to_dec(rem_ms, &status_body[n]);
    status_body[n] = 0;

    send_p1_response(seq, status_body, 1u);
    return;
  }

  /* 3. HEARTBEAT */
  if (strcmp(cmd, "HEARTBEAT") == 0) {
    if (arg1 != NULL) {
      send_p1_response(seq, "ERROR BADARG", 1u);
      return;
    }
    /* Duy tri lien lac, KHONG gia han laser */
    char hb_body[24];
    strcpy(hb_body, "DONE ");
    strcat(hb_body, ping_get_state_str());
    send_p1_response(seq, hb_body, 1u);
    return;
  }

  /* 4. STOP */
  if (strcmp(cmd, "STOP") == 0) {
    if (arg1 != NULL) {
      send_p1_response(seq, "ERROR BADARG", 1u);
      return;
    }
    laser_pin_set(0);
    if (s_state != STATE_ERROR) {
      s_state = STATE_PAUSED;
    }
    char stop_body[24];
    strcpy(stop_body, "DONE ");
    strcat(stop_body, ping_get_state_str());
    send_p1_response(seq, stop_body, 1u);
    return;
  }

  /* 5. CLEAR */
  if (strcmp(cmd, "CLEAR") == 0) {
    if (arg1 != NULL) {
      send_p1_response(seq, "ERROR BADARG", 1u);
      return;
    }
    if (s_state == STATE_ERROR || s_state == STATE_PAUSED) {
      if (estop_pin_read() == 1u) {
        send_p1_response(seq, "ERROR ESTOP", 1u);
        return;
      }
      if (door_pin_read() == 0u) {
        send_p1_response(seq, "ERROR DOOR_OPEN", 1u);
        return;
      }
      s_state = STATE_IDLE;
      s_last_err = "NONE";
      send_p1_response(seq, "DONE IDLE", 1u);
      return;
    } else if (s_state == STATE_IDLE) {
      send_p1_response(seq, "DONE IDLE", 1u);
      return;
    } else {
      send_p1_response(seq, "ERROR BUSY", 1u);
      return;
    }
  }

  /* 6. NOT IMPLEMENTED (HOME, MOVE_ABS) */
  if (strcmp(cmd, "HOME") == 0 || strcmp(cmd, "MOVE_ABS") == 0) {
    send_p1_response(seq, "ERROR NOTIMPL", 1u);
    return;
  }

  /* Lenh la */
  send_p1_response(seq, "ERROR UNKNOWN", 1u);
}

static void handle_line(void)
{
  char out[48];
  uint16_t n;

  if (s_line_len == 0u) {
    return;
  }

  /* Kiem tra co phai lenh P1 co dau '*' khong */
  char *p_star = strrchr(s_line, '*');
  if (p_star != NULL) {
    /* Co dau '*', la khung P1 */
    uint16_t body_len = (uint16_t)(p_star - s_line);
    if (strlen(p_star + 1) != 2u) {
      /* Khong dung 2 ky tu hex */
      send_p1_response(0u, "ERROR BADCHK", 0u);
      return;
    }

    uint8_t received_chk = 0;
    if (!parse_hex_byte(p_star[1], p_star[2], &received_chk)) {
      send_p1_response(0u, "ERROR BADCHK", 0u);
      return;
    }

    uint8_t calc_chk = calc_xor_checksum(s_line, body_len);

    /* Parse seq truoc dau space dau tien */
    uint32_t seq_u32 = 0u;
    char *p_space = strchr(s_line, ' ');
    uint8_t seq_valid = 0u;
    if (p_space != NULL && p_space < p_star) {
      *p_space = '\0';
      if (parse_u32(s_line, &seq_u32) && seq_u32 >= 1u && seq_u32 <= 65535u) {
        seq_valid = 1u;
      }
      *p_space = ' '; /* khoi phuc */
    }

    if (calc_chk != received_chk) {
      send_p1_response(seq_valid ? (uint16_t)seq_u32 : 0u, "ERROR BADCHK", 0u);
      return;
    }

    if (!seq_valid) {
      send_p1_response(0u, "ERROR BADARG", 0u);
      return;
    }

    uint16_t seq = (uint16_t)seq_u32;
    s_last_msg_tick = HAL_GetTick();

    /* Chống lặp lệnh: neu trung seq va co cache thi gui lai nguyen van */
    if (seq == s_last_p1_seq && s_last_p1_resp_len > 0u) {
      tx_str(s_last_p1_resp);
      return;
    }

    /* Cat bo phan '*<HH>' */
    *p_star = '\0';

    /* cmd_str bat dau sau seq va khoang trang */
    char *cmd_str = p_space + 1;
    handle_p1_command(seq, cmd_str);
    return;
  }

  /* Khong co dau '*': xu ly legacy (PING, ID?, hoac loi) */
  if (strncmp(s_line, "PING ", 5u) == 0) {
    uint32_t seq;
    if (!parse_u32(&s_line[5], &seq)) {
      tx_str("ERR badarg\n");
      return;
    }
    s_last_msg_tick = HAL_GetTick();
    HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
    memcpy(out, "PONG ", 5u);
    n = 5u;
    n += u32_to_dec(seq, &out[n]);
    out[n++] = ' ';
    n += u32_to_dec(HAL_GetTick(), &out[n]);
    out[n++] = '\n';
    out[n] = 0;
    tx_str(out);
    return;
  }

  if (strcmp(s_line, "PING") == 0) {
    tx_str("ERR badarg\n");
    return;
  }

  if (strcmp(s_line, "ID?") == 0) {
    s_last_msg_tick = HAL_GetTick();
    tx_str("ID NUCLEO-F446RE NucleoPing " FW_VERSION " " FW_GIT_HASH "\n");
    return;
  }

  tx_str("ERR unknown\n");
}

static void mark_loss(uint8_t drop_all)
{
  uint32_t before = s_rx_overrun_seen;
  s_rx_overrun_seen = s_rx_overrun;
  s_loss_pending = 0u;
  s_line_broken = 1u;
  if (s_line_len > 0u && s_line[0] >= '0' && s_line[0] <= '9') {
    s_line_was_p1 = 1u;
  }
  s_line_len = 0u;
  s_line_overflow = 0u;
  if (drop_all || (s_rx_overrun_seen - before) > 1u) {
    s_ring_tail = s_ring_head;
  }
}

static void check_loss(void)
{
  if (s_loss_pending && s_ring_tail == s_loss_pos) {
    mark_loss(0u);
  } else if (!s_loss_pending && s_rx_overrun != s_rx_overrun_seen) {
    mark_loss(1u);
  }
}

void ping_poll(void)
{
  /* 0. Refresh IWDG neu co */
  if (s_iwdg != NULL) {
    HAL_IWDG_Refresh(s_iwdg);
  }

  /* 1. Kiem tra phan cung an toan lien tuc */
  if (estop_pin_read() == 1u) {
    laser_pin_set(0);
    if (s_state != STATE_ERROR) {
      s_state = STATE_ERROR;
      s_last_err = "ESTOP";
    }
  }

  if (s_state == STATE_CAPTURING) {
    if (door_pin_read() == 0u) {
      laser_pin_set(0);
      s_state = STATE_ERROR;
      s_last_err = "DOOR_OPEN";
    }
  }

  /* 2. Kiem tra timeout khi dang CAPTURING */
  if (s_state == STATE_CAPTURING) {
    uint32_t now = HAL_GetTick();
    /* Mất liên lạc > 3000 ms */
    if ((int32_t)(now - (s_last_msg_tick + PING_T_HB_MS)) >= 0) {
      laser_pin_set(0);
      s_state = STATE_ERROR;
      s_last_err = "LINK_LOST";
    }
    /* Timeout laser > 5000 ms */
    else if ((int32_t)(now - (s_laser_on_tick + PING_T_LASER_MAX_MS)) >= 0) {
      laser_pin_set(0);
      s_state = STATE_IDLE;
      s_last_err = "LASER_TIMEOUT";
    }
  }

  /* 3. Rut byte tu ring, gop thanh dong */
  while (s_ring_tail != s_ring_head) {
    uint8_t c;
    check_loss();
    if (s_ring_tail == s_ring_head) {
      break;
    }
    c = s_ring[s_ring_tail];
    s_ring_tail = (uint16_t)((s_ring_tail + 1u) & (RX_RING_SIZE - 1u));

    if (c == '\n') {
      if (s_line_broken) {
        if (s_line_was_p1) {
          send_p1_response(0u, "ERROR OVERRUN", 0u);
        } else {
          tx_str("ERR overrun\n");
        }
        s_line_broken = 0u;
        s_line_was_p1 = 0u;
      } else if (s_line_overflow) {
        if (s_line_was_p1) {
          send_p1_response(0u, "ERROR TOOLONG", 0u);
        } else {
          tx_str("ERR toolong\n");
        }
        s_line_overflow = 0u;
        s_line_was_p1 = 0u;
      } else {
        s_line[s_line_len] = 0;
        handle_line();
        s_line_was_p1 = 0u;
      }
      s_line_len = 0u;
      s_line_overflow = 0u;
    } else if (c == '\r') {
      /* bo qua */
    } else if (s_line_broken) {
      if (c == '*') {
        s_line_was_p1 = 1u;
      }
    } else if (s_line_len < PING_LINE_MAX - 1u) {
      if (s_line_len == 0u) {
        s_line_was_p1 = (c >= '0' && c <= '9') ? 1u : 0u;
      } else if (c == '*') {
        s_line_was_p1 = 1u;
      }
      s_line[s_line_len++] = (char)c;
    } else {
      if (c == '*') {
        s_line_was_p1 = 1u;
      }
      s_line_overflow = 1u;
    }
  }
  check_loss();

  /* 4. Arm lai RX neu can */
  if (s_uart->RxState == HAL_UART_STATE_READY) {
    s_rx_rearm++;
    arm_rx();
  }

  /* 5. LD2 nhay 500 ms ON / 500 ms OFF */
  uint32_t now = HAL_GetTick();
  if ((int32_t)(now - s_led_next) >= 0) {
    HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
    s_led_next += LED_PERIOD_MS;
  }
}
