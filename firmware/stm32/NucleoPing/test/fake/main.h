/* main.h gia cho test tren PC. */
#ifndef FAKE_MAIN_H
#define FAKE_MAIN_H
#include "stm32f4xx_hal.h"
extern GPIO_TypeDef fake_gpioa;
extern GPIO_TypeDef fake_gpioc;

#define LD2_Pin GPIO_PIN_5
#define LD2_GPIO_Port (&fake_gpioa)

#define LASER_Pin GPIO_PIN_8
#define LASER_GPIO_Port (&fake_gpioa)

#define SENSE_PWR_Pin GPIO_PIN_9
#define SENSE_PWR_GPIO_Port (&fake_gpioa)

#define SENSE_ESTOP_Pin GPIO_PIN_7
#define SENSE_ESTOP_GPIO_Port (&fake_gpioc)

void Early_GPIO_Init_LaserSafe(void);

#endif

