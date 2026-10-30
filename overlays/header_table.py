"""Mangue OS — MangoPi MQ Pro 40-pin header: single source of truth.

tools/gen_overlays.py turns this into the .dtso overlays, the kernel patches (overlay build +
base-DT aliases/line names) and the conflict database used by mqpro-io.

Sources: pin mux = drivers/pinctrl/sunxi/pinctrl-sun20i-d1.c (6.18.56); bank voltages =
MQ Pro schematic v1.2 (docs/reference/); decisions = docs/batch2_overlays_PROPOSAL.md.
Numbering is MangoPi/D1 everywhere: physical pin numbers, D1 controller numbers.
"""

# Physical pin -> D1 port. Power/ground pins are omitted.
HEADER = {
    3: "PG13", 5: "PG12", 7: "PB7", 8: "PB8", 10: "PB9", 11: "PD21", 12: "PB5", 13: "PD22",
    15: "PB0", 16: "PB1", 18: "PD14", 19: "PD12", 21: "PD13", 22: "PC1", 23: "PD11", 24: "PD10",
    26: "PD15", 27: "PE17", 28: "PE16", 29: "PB10", 31: "PB11", 32: "PC0", 33: "PB12", 35: "PB6",
    36: "PB2", 37: "PD17", 38: "PB3", 40: "PB4",
}

# Pi BCM GPIO number at the same physical position — lookup only (mqpro-io pin GPIO17).
PI_BCM = {
    3: 2, 5: 3, 7: 4, 8: 14, 10: 15, 11: 17, 12: 18, 13: 27, 15: 22, 16: 23, 18: 24, 19: 10, 21: 9,
    22: 25, 23: 11, 24: 8, 26: 7, 27: 0, 28: 1, 29: 5, 31: 6, 32: 12, 33: 13, 35: 19, 36: 16, 37: 26,
    38: 20, 40: 21,
}

# Pins with fixed pull-ups to 3V3 on the board (schematic). No internal pull-up needed there.
BOARD_PULLUPS = {3, 5, 27, 28}

# Header pins that are not 3.3 V I/O (VCC-PE = AVDD2V8 via R38; everything else VCC3V3).
PIN_VOLTAGE = {27: 2.8, 28: 2.8}

# Pins owned by the system: never offered by an overlay.
RESERVED = {8: "UART0 TX (serial console)", 10: "UART0 RX (serial console)"}

# On-board GPIO line names (base DT gpio-line-names), from sun20i-d1-mangopi-mq-pro.dts.
ONBOARD_LINES = {
    "PD18": "LED-STATUS", "PF6": "SD-DETECT", "PG10": "WIFI-HOST-WAKE", "PG17": "WIFI-RESET",
    "PG14": "BT-HOST-WAKE", "PG15": "BT-ENABLE", "PG18": "BT-DEVICE-WAKE",
}

# Fixed device numbering = controller numbering (base DT /aliases).
ALIASES = {
    "i2c0": "i2c0", "i2c1": "i2c1", "i2c2": "i2c2", "i2c3": "i2c3",
    "spi0": "spi0", "spi1": "spi1",
    "serial1": "uart1", "serial2": "uart2", "serial3": "uart3", "serial4": "uart4", "serial5": "uart5",
}

# --- Overlays -----------------------------------------------------------------------------------
# kind     template in gen_overlays.py
# pins     {physical pin: role}; for mux kinds the role is the D1 mux function name
# res      exclusive resources (controller, PWM channel, ...): two overlays sharing one conflict
# dev      what the user gets
# warn     printed by mqpro-io when the overlay is enabled
I2C_DEV = "/dev/i2c-{n}"

OVERLAYS = [
    # I2C (controller numbering; see BOARD_PULLUPS for which pinsets have pull-ups)
    dict(name="i2c0-pins3-5", kind="i2c", ctrl="i2c0", pins={3: "sda", 5: "scl"}),
    dict(name="i2c0-pins29-31", kind="i2c", ctrl="i2c0", pins={31: "sda", 29: "scl"}),
    dict(name="i2c0-pins36-38", kind="i2c", ctrl="i2c0", pins={36: "sda", 38: "scl"}),
    dict(name="i2c1-pins12-40", kind="i2c", ctrl="i2c1", pins={12: "sda", 40: "scl"}),
    dict(name="i2c2-pins15-16", kind="i2c", ctrl="i2c2", pins={16: "sda", 15: "scl"}),
    dict(name="i2c2-pins22-32", kind="i2c", ctrl="i2c2", pins={22: "sda", 32: "scl"}),
    dict(name="i2c3-pins27-28", kind="i2c", ctrl="i2c3", pins={27: "sda", 28: "scl"},
         warn="Pins 27/28 are 2.8 V I/O (board pull-ups to 3.3 V). Open-drain I2C only: "
              "no 3.3 V push-pull signals, no extra pull-ups."),
    dict(name="i2c3-pins7-35", kind="i2c", ctrl="i2c3", pins={7: "sda", 35: "scl"}),
    dict(name="i2c-gpio-pins16-18", kind="i2c-gpio", ctrl="i2c-gpio", pins={16: "sda", 18: "scl"},
         note="bit-banged, ~100 kHz; bus number is the first free one >= 4 (see i2cdetect -l)"),

    # SPI (spi1 only; spi0 is not on the header). CS1 on pin 26 is a GPIO chip select.
    dict(name="spi1-pins19-21-23-24", kind="spidev", ctrl="spi1",
         pins={19: "mosi", 21: "miso", 23: "clk", 24: "cs0"}),
    dict(name="spi1-pins19-21-23-24-26", kind="spidev", ctrl="spi1",
         pins={19: "mosi", 21: "miso", 23: "clk", 24: "cs0", 26: "cs1-gpio"}),

    # UART (uart0 = console, uart1 = Bluetooth: not offered)
    dict(name="uart2-pins15-16", kind="uart", ctrl="uart2", pins={15: "tx", 16: "rx"}),
    dict(name="uart2-pins22-32", kind="uart", ctrl="uart2", pins={32: "tx", 22: "rx"}),
    dict(name="uart3-pins7-35", kind="uart", ctrl="uart3", pins={35: "tx", 7: "rx"}),
    dict(name="uart3-pins18-21-23-24", kind="uart", ctrl="uart3",
         pins={24: "tx", 23: "rx", 21: "rts", 18: "cts"}, note="with RTS/CTS flow control"),
    dict(name="uart4-pins36-38", kind="uart", ctrl="uart4", pins={36: "tx", 38: "rx"}),
    dict(name="uart5-pins12-40", kind="uart", ctrl="uart5", pins={40: "tx", 12: "rx"}),

    # PWM: one overlay per pin; channel N is shared by its pins -> exclusive resource pwmN
    *[dict(name=f"pwm{ch}-pin{pin}", kind="pwm", ctrl=f"pwm{ch}", pins={pin: f"pwm{ch}"})
      for ch, pin in [(0, 5), (0, 12), (0, 33), (1, 35), (1, 37), (2, 3), (2, 31), (3, 15),
                      (4, 16), (5, 11), (7, 13), (7, 28), (7, 29)]],

    # CAN: native D1 controllers (need an external 3.3 V transceiver, e.g. SN65HVD230)
    dict(name="can0-pins36-38", kind="can", ctrl="can0", pins={36: "tx", 38: "rx"},
         warn="Needs an external 3.3 V CAN transceiver (e.g. SN65HVD230). Classic CAN, no FD."),
    dict(name="can1-pins12-40", kind="can", ctrl="can1", pins={40: "tx", 12: "rx"},
         warn="Needs an external 3.3 V CAN transceiver (e.g. SN65HVD230). Classic CAN, no FD."),
    # CAN over SPI (INT on pin 22), one overlay per oscillator (extlinux has no parameters)
    *[dict(name=f"mcp2515-{mhz}mhz", kind="mcp2515", ctrl="spi1", osc=mhz * 1000000,
           pins={19: "mosi", 21: "miso", 23: "clk", 24: "cs0", 22: "int"})
      for mhz in (8, 12, 16)],
    dict(name="mcp251xfd-40mhz", kind="mcp251xfd", ctrl="spi1", osc=40000000,
         pins={19: "mosi", 21: "miso", 23: "clk", 24: "cs0", 22: "int"}),

    # SPI ADC with the kernel driver (IIO) instead of spidev
    dict(name="mcp3008-pins19-21-23-24", kind="mcp3008", ctrl="spi1",
         pins={19: "mosi", 21: "miso", 23: "clk", 24: "cs0"},
         note="IIO driver (/sys/bus/iio); use spi1-pins19-21-23-24 instead for spidev access"),

    # Single-pin devices
    dict(name="w1-gpio-pin7", kind="w1", ctrl="w1-gpio", pins={7: "data"},
         note="1-Wire (DS18B20 ...); external 4.7 k pull-up to 3.3 V required"),
    dict(name="dht11-pin7", kind="dht11", ctrl="dht11", pins={7: "data"}),
    dict(name="gpio-ir-pin12", kind="gpio-ir", ctrl="gpio-ir", pins={12: "rx"}),
    dict(name="pwm-ir-tx-pin12", kind="pwm-ir-tx", ctrl="pwm0", pins={12: "pwm0"}),
    dict(name="pps-gpio-pin12", kind="pps", ctrl="pps-gpio", pins={12: "pps"}),
    dict(name="gpio-shutdown-pin5", kind="shutdown", ctrl="gpio-shutdown", pins={5: "button"},
         note="button to GND on pin 5 = clean shutdown (pin has a board pull-up)"),
]
