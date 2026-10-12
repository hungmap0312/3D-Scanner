/*
 * tester_c4_hal.c - HAL gia DOC LAP cua Tester C4 (khong dung chung voi test cua Coder).
 *
 * Chay ping_proto.c THAT tren PC. Khac HAL gia cua Coder o cho ghi LICH SU chan PA8:
 * moi lan ghi PA8 muc cao ma FSM khong o CAPTURING la mot "vi pham" (01_PLAN Vong 1
 * buoc 4: "HAL gia ghi lich su GPIO, chung minh khong co muc cao ngoai CAPTURING").
 * Xuat API sim_* de test C (tester_c4_test.c) va Python (ctypes, pc/test_nucleo_ping_p1.py)
 * cung dung. Day KHONG phai thu tren bo.
 */
#include "ping_proto.h"
#include "main.h"

#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#define SIM_API __declspec(dllexport)
#else
#define SIM_API
#endif

GPIO_TypeDef fake_gpioa;
GPIO_TypeDef fake_gpioc;
uint32_t fake_rcc_flags = 0;

static UART_HandleTypeDef s_huart;
static IWDG_HandleTypeDef s_hiwdg;
static char s_tx[32768];
static size_t s_txlen;
static uint32_t s_tick;
static uint32_t s_iwdg_refresh;
static uint32_t s_pa8_writes;
static uint32_t s_pa8_set_writes;
static uint32_t s_pa8_violations;
static char s_viol_note[256];
static int s_pa8_after_early = -1;

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *h, const uint8_t *p, uint16_t n, uint32_t to)
{
  (void)h; (void)to;
  if (s_txlen + n < sizeof(s_tx)) {
    memcpy(&s_tx[s_txlen], p, n);
    s_txlen += n;
    s_tx[s_txlen] = 0;
  }
  return HAL_OK;
}

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *h, uint8_t *p, uint16_t n)
{
  (void)n;
  if (h->receive_it_fail_next > 0) {
    h->receive_it_fail_next--;
    return HAL_BUSY;
  }
  h->rx_dst = p;
  h->rx_armed = 1;
  h->RxState = HAL_UART_STATE_BUSY_RX;
  return HAL_OK;
}

uint32_t HAL_GetTick(void) { return s_tick; }

static void note_pa8_write(GPIO_TypeDef *g, uint16_t pin, int level)
{
  if (g != LASER_GPIO_Port || (pin & LASER_Pin) == 0u) {
    return;
  }
  s_pa8_writes++;
  if (level) {
    s_pa8_set_writes++;
    if (strcmp(ping_get_state_str(), "CAPTURING") != 0) {
      s_pa8_violations++;
      snprintf(s_viol_note, sizeof(s_viol_note), "PA8 cao khi state=%s tick=%lu",
               ping_get_state_str(), (unsigned long)s_tick);
    }
  }
}

void HAL_GPIO_TogglePin(GPIO_TypeDef *g, uint16_t pin)
{
  note_pa8_write(g, pin, (g->pin_state & pin & LASER_Pin) ? 0 : 1);
  g->pin_state ^= pin;
}

void HAL_GPIO_WritePin(GPIO_TypeDef *g, uint16_t pin, GPIO_PinState state)
{
  note_pa8_write(g, pin, state == GPIO_PIN_SET);
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
  s_iwdg_refresh++;
  return HAL_OK;
}

static void set_inputs(int door, int estop)
{
  if (door) fake_gpioa.pin_state |= SENSE_PWR_Pin; else fake_gpioa.pin_state &= (uint16_t)~SENSE_PWR_Pin;
  if (estop) fake_gpioc.pin_state |= SENSE_ESTOP_Pin; else fake_gpioc.pin_state &= (uint16_t)~SENSE_ESTOP_Pin;
}

/* Mo phong reset: pa8_before = muc PA8 truoc reset (1 = dang cao). Goi dung thu tu main.c:
 * ping_early_safety_init() (USER CODE BEGIN 1) roi ping_init(). Dong BOOT de lai trong bo dem TX. */
SIM_API void sim_reset(int door, int estop, uint32_t rcc_flags, uint32_t tick, int pa8_before, int with_iwdg)
{
  memset(&s_huart, 0, sizeof(s_huart));
  s_huart.gState = HAL_UART_STATE_READY;
  s_huart.RxState = HAL_UART_STATE_READY;
  s_txlen = 0;
  s_tx[0] = 0;
  s_tick = tick;
  s_iwdg_refresh = 0;
  s_pa8_writes = s_pa8_set_writes = s_pa8_violations = 0;
  s_viol_note[0] = 0;
  fake_gpioa.pin_state = pa8_before ? LASER_Pin : 0u;
  fake_gpioc.pin_state = 0u;
  set_inputs(door, estop);
  fake_rcc_flags = rcc_flags;
  ping_set_iwdg(with_iwdg ? &s_hiwdg : NULL);
  ping_early_safety_init();
  s_pa8_after_early = (fake_gpioa.pin_state & LASER_Pin) ? 1 : 0;
  ping_init(&s_huart);
}

SIM_API void sim_set_inputs(int door, int estop) { set_inputs(door, estop); }
SIM_API void sim_set_tick(uint32_t t) { s_tick = t; }
SIM_API uint32_t sim_get_tick(void) { return s_tick; }
SIM_API void sim_poll(void) { ping_poll(); }

SIM_API void sim_rx(const char *bytes, int n)
{
  int i;
  for (i = 0; i < n; i++) {
    if (!s_huart.rx_armed) {
      continue;                       /* chua arm: byte mat, khong callback (nhu phan cung) */
    }
    *s_huart.rx_dst = (uint8_t)bytes[i];
    s_huart.rx_armed = 0;
    s_huart.RxState = HAL_UART_STATE_READY;
    HAL_UART_RxCpltCallback(&s_huart);
  }
}

SIM_API void sim_rx_error(void)
{
  s_huart.rx_armed = 0;
  s_huart.RxState = HAL_UART_STATE_READY;
  HAL_UART_ErrorCallback(&s_huart);
}

/* Lay va xoa bo dem TX; tra ve so byte. */
SIM_API int sim_take_tx(char *buf, int cap)
{
  int n = (int)s_txlen;
  if (n >= cap) n = cap - 1;
  memcpy(buf, s_tx, (size_t)n);
  buf[n] = 0;
  s_txlen = 0;
  s_tx[0] = 0;
  return n;
}

SIM_API int sim_pa8(void) { return (fake_gpioa.pin_state & LASER_Pin) ? 1 : 0; }
SIM_API int sim_pa8_after_early(void) { return s_pa8_after_early; }
SIM_API uint32_t sim_pa8_violations(void) { return s_pa8_violations; }
SIM_API uint32_t sim_pa8_set_writes(void) { return s_pa8_set_writes; }
SIM_API const char *sim_viol_note(void) { return s_viol_note; }
SIM_API uint32_t sim_iwdg_refresh(void) { return s_iwdg_refresh; }
SIM_API const char *sim_state(void) { return ping_get_state_str(); }
SIM_API const char *sim_last_err(void) { return ping_get_last_error_str(); }
