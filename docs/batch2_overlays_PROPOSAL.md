# Batch 2 — header overlays, aliases, kernel additions (PROPOSAL, not approved)

Drafted 2026-10-13. Nothing here is built. Open items 1–4 decided (see Decisions); overlays not yet written.

## Decisions (user, 2026-10-13)
1. **MangoPi numbering, no Pi remap.** GPIO line names = physical header pins (`P3`, `P11`, …). Bus devices keep
   D1 controller numbers, pinned by DT aliases so they never go dynamic: i2c0 (pins 3/5) → `/dev/i2c-0`,
   i2c1 → `/dev/i2c-1`, i2c2 → `/dev/i2c-2`, i2c3 (pins 27/28) → `/dev/i2c-3`; spi1 → `/dev/spidev1.0` / `1.1`.
   Reason: some pins don't match the Pi (PWM on 32/33, UART on 8/10), so a partial Pi mapping would confuse.
   Pi lookups stay available as a translation in `mqpro-io pin GPIO17` / Python `mqpro.pi_pin()` only.
   → The alias columns in the tables below are SUPERSEDED.
2. **All overlays kept**, including `/dev/serial0` (→ ttyS0 console), `uart3-pins24-23-flow`, MCP251xFD,
   MCP3008 driver overlay (spidev stays the default), default bit-bang I2C.
3. **Kernel drivers: broad set.** `tools/batch2_kernel_drivers.txt` (Pi bcm2711_defconfig rpi-6.18.y minus
   Broadcom/PCIe/DSI/I2S-only, plus hobby parts the Pi lacks) merged into `userpatches/linux-d1-current.config`
   by `tools/apply_kernel_drivers.sh`. Verified with `olddefconfig` in the Armbian docker toolchain: every
   requested symbol survives, nothing previously enabled is removed or demoted; modules 1400 → 1740.

## Sources checked
- Pin mux: parsed from `drivers/pinctrl/sunxi/pinctrl-sun20i-d1.c` in the 6.18.56 build tree (primary).
  It confirms `docs/pinmap.md` (community, easytarget/MQ-Pro-IO) and adds functions it omits:
  `ir.RX/TX`, `ledc` (pins 3, 32), `can0/can1`, `i2c3.SCK` on pin 35, `spdif`, `jtag`.
- Controllers: `sunxi-d1s-t113.dtsi` (6.18) has nodes for uart0–5, i2c0–3, spi0–1, pwm, can0/can1,
  gpadc, lradc. No ledc and no IR node.
- Board DTS: `sun20i-d1-mangopi-mq-pro.dts` (+ our patches 0001–0011).

## Hard exclusions
| What | Why |
|---|---|
| Pins 8/10 (PB8/PB9) | UART0 serial console. Loses the pwm5/pwm6, i2c2, spi1 muxes on these two pins (pwm5 still on pin 11) |
| uart1 (any header pinset: 3/5, 11/13, 29/31) | uart1 is the Bluetooth HCI (PG6–9) |
| uart0 alternate on 15/16 | console stays on 8/10 |
| GPADC | no gpadc function on any header pin → not reachable |
| Existing groups `i2c2_pd_pins`, `i2c3_pg_pins` | PD20 not on header; PG10 = Wi-Fi host-wake IRQ. Overlays define their own groups |

## Rule: one pinset per controller
Each controller can be routed to only one pinset at a time. `mqpro-io` refuses: (a) two overlays sharing a
pin, (b) two overlays using the same controller (e.g. `i2c-pins3-5` + `i2c-pins29-31`, both i2c0).
Single source table → `tools/gen_overlays.py` generates the `.dtso` files AND the conflict DB `mqpro-io` reads.

## Overlay table (all off by default)
> **Superseded by the implementation (2026-10-13):** the source of truth is `overlays/header_table.py`
> (generated: `overlays/dtso/`, patches 0013/0014, `mqpro-io.json`). Final names carry the controller:
> `i2c0-pins3-5`, `i2c3-pins27-28`, `spi1-pins19-21-23-24[-26]`, `uart3-pins18-21-23-24`, `mcp3008-pins19-21-23-24`,
> `i2c-gpio-pins16-18` (Pi i2c-gpio default positions). Alias columns below are void (controller numbering).
> The tables are kept as the design record only.
`P` = primary (Pi-compatible position). Pin order in names: as on the header (low→high).

### I2C (3.3 V, 100 kHz default)
| Overlay | Controller | SDA / SCL pins | Alias → device | Notes |
|---|---|---|---|---|
| `i2c-pins3-5` **P** | i2c0 | 3 / 5 (PG13/PG12) | `i2c1` → `/dev/i2c-1` | = Pi I2C1. Board pull-ups to 3V3 (value not readable in schematic crop) |
| `i2c-pins27-28` **P** | i2c3 | 27 / 28 (PE17/PE16) | `i2c0` → `/dev/i2c-0` | = Pi ID-EEPROM bus. **2.8 V I/O** (open item 1); shared with touch-panel FFC |
| `i2c-pins12-40` | i2c1 | 12 / 40 (PB5/PB4) | `i2c3` → `/dev/i2c-3` | only pinset of i2c1; conflicts with can1, uart5 |
| `i2c-pins15-16` | i2c2 | 16 / 15 (PB1/PB0) | `i2c2` → `/dev/i2c-2` | conflicts uart2-pins15-16, pwm3/4 |
| `i2c-pins22-32` | i2c2 | 22 / 32 (PC1/PC0) | `i2c2` | alternate of i2c2 |
| `i2c-pins29-31` | i2c0 | 31 / 29 (PB11/PB10) | `i2c1` | alternate of i2c0 |
| `i2c-pins36-38` | i2c0 | 36 / 38 (PB2/PB3) | `i2c1` | alternate of i2c0 |
| `i2c-pins7-35` | i2c3 | 7 / 35 (PB7/PB6) | `i2c0` | alternate of i2c3, 3.3 V bank |
| `i2c-gpio-pinsX-Y` | bit-bang | any free pair | `/dev/i2c-10+` | needs `I2C_GPIO`; ship one default (pins 7/35?) or leave to `mqpro-io` — **decide** |

Alias mapping is fixed in the base DT (all four declared, so numbers never go dynamic). Downside: `/dev/i2c-N`
≠ controller number (`i2c-1` is controller i2c0). Documented in `mqpro-io pins` output.

### SPI
| Overlay | Controller | Pins (MOSI/MISO/CLK/CS0) | Device | Notes |
|---|---|---|---|---|
| `spi-pins19-21-23-24` **P** | spi1 | 19/21/23/24 (PD12/13/11/10) | `/dev/spidev0.0` (alias `spi0` → spi1) | = Pi SPI0 positions exactly |
| `spi-pins19-21-23-24-26` | spi1 | + CE1 on 26 (PD15, `cs-gpios`) | + `/dev/spidev0.1` | PD15 has no hardware CS mux → GPIO CS |

spidev child compatible: `rohm,dh2228fv` (in 6.18 `spidev_dt_ids[]`; bare `"spidev"` is rejected).
spi1 on PB pins (29/31/33 + MISO on console pin 10) → impossible. spi0 not on header.

### UART
| Overlay | Controller | TX / RX pins | Device | Notes |
|---|---|---|---|---|
| `uart2-pins15-16` | uart2 | 15 / 16 (PB0/PB1) | `/dev/ttyS2` | |
| `uart2-pins32-22` | uart2 | 32 / 22 (PC0/PC1) | `/dev/ttyS2` | alternate |
| `uart3-pins35-7` | uart3 | 35 / 7 (PB6/PB7) | `/dev/ttyS3` | existing group `uart3_pb_pins` |
| `uart3-pins24-23-flow` | uart3 | 24 / 23 + RTS 21, CTS 18 | `/dev/ttyS3` | conflicts SPI — low value, **drop?** |
| `uart4-pins36-38` | uart4 | 36 / 38 (PB2/PB3) | `/dev/ttyS4` | conflicts can0 |
| `uart5-pins40-12` | uart5 | 40 / 12 (PB4/PB5) | `/dev/ttyS5` | conflicts can1, i2c1 |

No Pi-compatible UART on 8/10 (that's our console). `/dev/serial0` symlink → **decide** (point at ttyS0 = console, like Pi with console enabled, or omit).

### PWM (driver `pwm-sun20i`, `/sys/class/pwm/pwmchip0`, channel = pwmN)
One overlay per pin: `pwm0-pin5`, `pwm0-pin12`, `pwm0-pin33`, `pwm1-pin35`, `pwm1-pin37`, `pwm2-pin3`, `pwm2-pin31`,
`pwm3-pin15`, `pwm4-pin16`, `pwm5-pin11`, `pwm7-pin13`, `pwm7-pin28`, `pwm7-pin29` (13 overlays).
pwm5 is usable on pin 11 (only its pin-8 mux is lost to the console); pwm6 exists only on pin 10 → unavailable.
Pi overlap: pin 12 = Pi PWM0 ✓, pin 35 = Pi PWM1 ✓ (Pi also has PWM0 on 32 / PWM1 on 33 — ours differ there).
One channel per pin rule in `mqpro-io` (two pins on the same channel would output the same signal — refused).
pwm7-pin13 already verified on 6.18 (2026-10-10).

### CAN
| Overlay | What | Pins | Notes |
|---|---|---|---|
| `can0-pins36-38` | native D1 CAN (TX/RX) | 36 / 38 (PB2/PB3) | `sun4i_can` has `allwinner,sun20i-d1-can`; **needs `CAN_SUN4I=m`** (currently not set). External 3.3 V transceiver required (e.g. SN65HVD230). Classic CAN only, no FD |
| `can1-pins40-12` | native D1 CAN | 40 / 12 (PB4/PB5) | same |
| `mcp2515-8mhz` / `-12mhz` / `-16mhz` | MCP2515 on spi1 CS0, INT pin 22 | SPI P + 22 | = Pi `mcp2515-can0` defaults (GPIO25 = pin 22). Needs `CAN_MCP251X=m` |
| `mcp251xfd-40mhz` | MCP2517FD/2518FD on spi1 CS0, INT pin 22 | SPI P + 22 | needs `CAN_MCP251XFD=m`. Keep? **decide** |

U-Boot extlinux has no `dtparam`, so oscillator/INT variants = separate overlays.

### Single-wire / misc devices
| Overlay | Driver | Pin | Pi default it mirrors |
|---|---|---|---|
| `w1-gpio-pin7` | w1-gpio (already `=m`) | 7 | `w1-gpio` GPIO4 = pin 7 |
| `dht11-pin7` | IIO dht11 | 7 | `dht11` GPIO4 = pin 7 |
| `gpio-ir-pin12` | gpio-ir-recv | 12 | `gpio-ir` GPIO18 = pin 12 |
| `pwm-ir-tx-pin12` | pwm-ir-tx on pwm0 | 12 | `pwm-ir-tx` GPIO18 |
| `pps-gpio-pin12` | pps-gpio | 12 | `pps-gpio` GPIO18 |
| `gpio-shutdown-pin5` | gpio-keys KEY_POWER | 5 | `gpio-shutdown` GPIO3 = pin 5 (has board pull-up) |

Native D1 IR receiver (`ir.RX` on 7/13/26/33) not usable: `sunxi-cir` has no D1 compatible and no DT node → gpio-ir instead.

### Maybe / later
- **LEDC** (WS2812 chain on pin 3 or 32): driver `leds-sun50i-a100` already `=m` and binding accepts `sun20i-d1-ledc`,
  but no node in 6.18 → needs reg/irq/clock/DMA values from smaeul d1-wip, not invented. Later batch.
- I2C sensor devices (BME280, ADS1115, …): no overlay — instantiated at runtime
  (`echo bme280 0x76 > /sys/bus/i2c/devices/i2c-1/new_device`), wrapped by `mqpro-io`.
- MCP3008: `mcp3008-spi-cs0` overlay vs. spidev — **decide** (driver gives `/sys/bus/iio`, spidev gives Python access; one or the other per CS).

## GPIO line names
`gpio-line-names` on `&pio` (7 banks × 32 lines): header pins named `P3`, `P5`, … ; on-board lines named by function
(`LED-STATUS` PD18, `WIFI-RESET` PG17, `BT-EN` PG15, …), the rest empty. `gpioinfo` / `gpiofind P11` then work.

## Kernel config additions (all `=m` unless noted; modules cost ~nothing until loaded)
`CAN_SUN4I`, `CAN_MCP251X`, `CAN_MCP251XFD`, `IIO` (=y), `TI_ADS1015`, `MCP320X`, `BMP280` (+I2C/SPI parts, covers BME280),
`DHT11`, `I2C_GPIO`, `RC_CORE`, `IR_GPIO_CIR`, `IR_PWM_TX`, `PPS_CLIENT_GPIO`, `KEYBOARD_GPIO`.
Candidates to add (user prunes): `SENSORS_LM75`, `AHT10`, `SHT3x`, `BH1750`, `VEML7700`, `INA219`, `MCP4725` (DAC), `MAX31855`.

## Build mechanics
Overlays as `.dtso` in a kernel patch → `arch/riscv/boot/dts/allwinner/overlay/` + Makefile (`dtb-y += *.dtbo`,
`subdir-y += overlay`). Armbian runs `make dtbs_install`, which installs them to `/boot/dtb/allwinner/overlay/`.
Source of truth: `tools/gen_overlays.py` + its table in project `overlays/`; generated patch lands in
`userpatches/kernel/archive/d1-6.18/0012-…`. Enable/disable = `fdtoverlays` line in `extlinux.conf` via `mqpro-io`.
U-Boot already has the moved `fdtoverlay_addr_r` (patch 0004).

## Open items before build
1. ~~**Pins 27/28 voltage.**~~ **Resolved 2026-10-13 from the schematic** (`docs/reference/mq-pro-sch-v12.pdf`, v1.2 —
   no v1.4 schematic found; v1.4 changes per linux-sunxi are vias/antenna only, so the rails are assumed the same):
   - `VCC-PE` = net `VCC-RMII-CSI` ← `AVDD2V8` via R38 (0 Ω) → **PE bank (pins 27/28) runs at 2.8 V**.
   - PE16/PE17 have R33/R34 **10 k pull-ups to VCC3V3** and are shared with the DSI/touch-panel FFC (pins 19/20, SCL/SDA).
   - D1 datasheet Table 5-4: VIH max = VCC-IO + 0.3 V = **3.1 V** → the board's own pull-ups idle the bus 0.2 V over spec.
     Current is negligible (10 k, below an ESD diode's forward drop), and it's the vendor's intended TWI3 bus.
   - All other header banks are 3.3 V: VCC-PG, VCC-PC, VDD-PD, VCC-IO (PB) = VCC3V3.
   - **Decision proposed:** ship `i2c-pins27-28` (open-drain I2C is fine), but `mqpro-io` warns that pins 27/28 are 2.8 V I/O:
     no 3.3 V push-pull outputs into them, no additional pull-ups. Logic-high from the D1 on these pins is 2.8 V
     (still above a 3.3 V device's 0.7×VDD = 2.31 V threshold).
2. Pi alias remap (`i2c-1` = controller i2c0, etc.) — confirm you want Pi device numbers over controller numbers.
3. `/dev/serial0`, `uart3-pins24-23-flow`, MCP251xFD, MCP3008 overlay, default bit-bang I2C — keep or drop.
4. Sensor driver list — prune or extend.
5. Image #6 also carries: systemd watchdog, B11 (tmpfiles journal), B15 (PHY log level) — bugs, standing approval.
