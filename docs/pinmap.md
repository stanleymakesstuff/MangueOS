# MQ Pro 40-pin header map

Source: https://github.com/easytarget/MQ-Pro-IO (fetched 2026-10-10). 3.3 V logic only.
Pins 3, 5, 27, 28 have fixed 10k pull-ups to 3V3. Pins 8/10 = serial console (UART0).

| Pin | GPIO | Alternate functions |
|---|---|---|
| 1 | 3V3 | |
| 2 | 5V | |
| 3 | PG13 | i2c0-sda, uart1-rx, pwm2 |
| 4 | 5V | |
| 5 | PG12 | i2c0-scl, uart1-tx, pwm0 |
| 6 | GND | |
| 7 | PB7 | i2c3-sda, uart3-rx |
| 8 | PB8 | i2c2-sck, spi1-hold, **uart0-tx (console)**, uart1-tx, pwm5 |
| 9 | GND | |
| 10 | PB9 | i2c2-sda, spi1-miso, **uart0-rx (console)**, uart1-rx, pwm6 |
| 11 | PD21 | i2c2-sda, uart1-tx, pwm5 |
| 12 | PB5 | i2c1-sda, uart5-rx, pwm0 |
| 13 | PD22 | uart1-rx, pwm7 |
| 14 | GND | |
| 15 | PB0 | i2c2-sck, spi1-wp, uart0-tx, uart2-tx, pwm3 |
| 16 | PB1 | i2c2-sda, uart0-rx, uart2-rx, pwm4 |
| 17 | 3V3 | |
| 18 | PD14 | spi1-hold, uart3-cts |
| 19 | PD12 | i2c0-sda, spi1-mosi |
| 20 | GND | |
| 21 | PD13 | spi1-miso, uart3-rts |
| 22 | PC1 | i2c2-sda, uart2-rx |
| 23 | PD11 | spi1-clk, uart3-rx |
| 24 | PD10 | spi1-cs, uart3-tx |
| 25 | GND | |
| 26 | PD15 | spi1-wp |
| 27 | PE17 | i2c3-sda |
| 28 | PE16 | i2c3-sck, pwm7 |
| 29 | PB10 | i2c0-sck, spi1-mosi, uart1-rts, pwm7 |
| 30 | GND | |
| 31 | PB11 | i2c0-sda, spi1-clk, uart1-cts, pwm2 |
| 32 | PC0 | i2c2-sck, uart2-tx |
| 33 | PB12 | spi1-cs, pwm0 |
| 34 | GND | |
| 35 | PB6 | i2s3-sck, uart3-tx, pwm1 |
| 36 | PB2 | i2c0-sda, uart4-tx |
| 37 | PD17 | pwm1 |
| 38 | PB3 | i2c0-sck, uart4-rx |
| 39 | GND | |
| 40 | PB4 | i2c1-sck, uart5-tx |

PWM channels by pin: pwm0 → 5, 12, 33 · pwm1 → 35, 37 · pwm2 → 3, 31 · pwm3 → 15 · pwm4 → 16 · pwm5 → 8, 11 · pwm6 → 10 · pwm7 → 13, 28, 29.
Verified on 6.18: PWM7 on pin 13 (PD22, mux function `pwm7`) — 2026-10-10.
