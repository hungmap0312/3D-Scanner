/* HAL gia cho test tren PC: chi cac ky hieu ping_proto.c dung.
 * KHONG phai HAL that; khong dung de build firmware. */
#ifndef FAKE_STM32F4XX_HAL_H
#define FAKE_STM32F4XX_HAL_H

#include <stdint.h>
#include <stddef.h>

typedef enum {
  HAL_OK = 0x00U, HAL_ERROR = 0x01U, HAL_BUSY = 0x02U, HAL_TIMEOUT = 0x03U
} HAL_StatusTypeDef;

typedef enum {
  HAL_UART_STATE_RESET = 0x00U,
  HAL_UART_STATE_READY = 0x20U,
  HAL_UART_STATE_BUSY = 0x24U,
  HAL_UART_STATE_BUSY_TX = 0x21U,
  HAL_UART_STATE_BUSY_RX = 0x22U,
  HAL_UART_STATE_BUSY_TX_RX = 0x23U,
  HAL_UART_STATE_TIMEOUT = 0xA0U,
  HAL_UART_STATE_ERROR = 0xE0U
} HAL_UART_StateTypeDef;

typedef struct {
  HAL_UART_StateTypeDef gState;
  HAL_UART_StateTypeDef RxState;
  /* phan gia lap */
  uint8_t *rx_dst;
  int rx_armed;
  int receive_it_fail_next;   /* >0: HAL_UART_Receive_IT tra HAL_BUSY n lan */
} UART_HandleTypeDef;

typedef enum {
  GPIO_PIN_RESET = 0U,
  GPIO_PIN_SET
} GPIO_PinState;

typedef struct { 
  int dummy;
  uint16_t pin_state; /* bitmask for fake pin states */
} GPIO_TypeDef;

#define GPIO_PIN_5 ((uint16_t)0x0020)
#define GPIO_PIN_7 ((uint16_t)0x0080)
#define GPIO_PIN_8 ((uint16_t)0x0100)
#define GPIO_PIN_9 ((uint16_t)0x0200)

typedef struct {
  void *Instance;
} IWDG_HandleTypeDef;

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *huart, const uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
uint32_t HAL_GetTick(void);
void HAL_GPIO_TogglePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);
void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, GPIO_PinState PinState);
GPIO_PinState HAL_GPIO_ReadPin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);

#define __HAL_UART_CLEAR_OREFLAG(h) ((void)(h))
#define __HAL_RCC_GPIOA_CLK_ENABLE() ((void)0)
#define __HAL_RCC_GPIOC_CLK_ENABLE() ((void)0)

/* Fake RCC reset flags */
#define RCC_FLAG_IWDGRST 0x01U
#define RCC_FLAG_PORRST  0x02U
#define RCC_FLAG_PINRST  0x04U
#define RCC_FLAG_SFTRST  0x08U

extern uint32_t fake_rcc_flags;
#define __HAL_RCC_GET_FLAG(f) ((fake_rcc_flags & (f)) != 0)
#define __HAL_RCC_CLEAR_RESET_FLAGS() (fake_rcc_flags = 0)

HAL_StatusTypeDef HAL_IWDG_Refresh(IWDG_HandleTypeDef *hiwdg);

/* callback do ping_proto.c dinh nghia */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart);
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart);

#endif
