/*
 * Giao thuc PING/PONG qua USART2 (COM ao cua ST-LINK), 115200 8N1.
 *
 * Moi lenh la mot dong ASCII ket thuc bang LF; CR bi bo qua.
 *   PING <n>   -> PONG <n> <uptime_ms>
 *   ID?        -> ID NUCLEO-F446RE NucleoPing <FW_VERSION> <FW_GIT_HASH>
 *   (dong rong) -> bo qua, khong tra loi
 *   lenh khac  -> ERR unknown
 *   PING thieu hoac sai so -> ERR badarg
 *   dong dai qua PING_LINE_MAX -> ERR toolong (phan du bi bo)
 *   mat/hong byte (ring day, loi UART) -> bo toi LF ke tiep, ERR overrun
 *                 (them 20/09, review R08; khong ghep hai manh thanh lenh)
 *   PING <n> voi n > 4294967295 -> ERR badarg (sua 20/09, review R07)
 * Khi khoi dong bo in: BOOT NucleoPing <FW_VERSION> <FW_GIT_HASH>
 *
 * uptime_ms lay tu HAL_GetTick(), tinh tu luc reset. Sau khi rut cam
 * nguon, gia tri nay nho lai; PC dung no lam bang chung bo da chay lai.
 *
 * Nhan byte bang ngat RX mot byte mot lan, day vao ring buffer; xu ly
 * dong trong vong lap chinh. Khong cap tai ra GPIO nao ngoai LD2.
 */
#ifndef PING_PROTO_H
#define PING_PROTO_H

#include "stm32f4xx_hal.h"

#define PING_LINE_MAX 64u
#define PING_T_HB_MS 3000u
#define PING_T_LASER_MAX_MS 5000u

/* Goi rat som o dau main() de keo chan Laser xuong muc thap */
void ping_early_safety_init(void);

/* Dang ky handle IWDG de tu dong refresh trong ping_poll() */
void ping_set_iwdg(IWDG_HandleTypeDef *hiwdg);

/* Goi mot lan sau khi HAL_UART_Init(&huart2) xong. In dong BOOT. */
void ping_init(UART_HandleTypeDef *huart);

/* Goi lien tuc trong while(1). Xu ly dong da nhan du va nhay LD2. */
void ping_poll(void);

/* Chan doan: so su kien mat/hong byte RX va so lan poll phai arm lai RX. */
uint32_t ping_rx_overrun_count(void);
uint32_t ping_rx_rearm_count(void);

/* Getter trang thai dung cho selftest tren PC va chan doan */
const char *ping_get_state_str(void);
const char *ping_get_last_error_str(void);
uint8_t ping_get_laser_state(void);

#endif /* PING_PROTO_H */
