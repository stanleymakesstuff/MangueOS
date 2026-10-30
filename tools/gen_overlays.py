#!/usr/bin/env python3
"""Generate Mangue OS header overlays from overlays/header_table.py.

Outputs (all derived, never edit by hand):
  overlays/dtso/<name>.dtso                                   review copies
  userpatches/kernel/archive/d1-6.18/0013-...-header-overlays.patch   overlay dir + Makefile hook
  userpatches/kernel/archive/d1-6.18/0014-...-aliases-line-names.patch base DT numbering + names
  userpatches/overlay/mangueos/mqpro-io.json                  conflict DB for mqpro-io

usage: tools/gen_overlays.py [--kernel <6.18 tree with patches 0001-0012 applied>]
The kernel tree supplies the files the patches diff against and the pin-mux table that every
pin/function in the table is checked against.
"""
import argparse, difflib, importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DTS_DIR = "arch/riscv/boot/dts/allwinner"
BOARD_DTS = f"{DTS_DIR}/sun20i-d1-mangopi-mq-pro.dts"
PATCH_DIR = os.path.join(ROOT, "userpatches/kernel/archive/d1-6.18")
MK_MARK = "\n\n# Mangue OS: MQ Pro header overlays\n"
DTS_MARK = "\n\n/* Mangue OS: bus devices "
DEFAULT_KERNEL = os.path.expanduser(
    "~/mangopi_mqpro/build/cache/sources/linux-kernel-worktree/6.18__d1__riscv64")

spec = importlib.util.spec_from_file_location("t", os.path.join(ROOT, "overlays/header_table.py"))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def port(pin):
    return T.HEADER[pin]


def gpio(pin, flags="GPIO_ACTIVE_HIGH"):
    p = port(pin)
    return f"<&pio {ord(p[1]) - ord('A')} {int(p[2:])} ({flags})>"


def irq(pin, flags="IRQ_TYPE_LEVEL_LOW"):
    p = port(pin)
    return f"<&pio {ord(p[1]) - ord('A')} {int(p[2:])} {flags}>"


def label(o, suffix="pins"):
    return re.sub(r"\W", "_", f"mq_{o['name']}_{suffix}")


def pin_of(o, role):
    return next(p for p, r in o["pins"].items() if r == role)


def mux_group(o, function, roles=None, pull=None):
    """&pio subnode muxing the overlay's pins (optionally only some roles) to one function."""
    pins = [p for p, r in o["pins"].items() if roles is None or r in roles]
    if pull is None:
        pull = not any(p in T.BOARD_PULLUPS for p in pins)
    names = ", ".join(f'"{port(p)}"' for p in pins)
    bias = "\t\tbias-pull-up;\n" if pull else ""
    return (f"&pio {{\n\t{label(o)}: {o['name']}-pins {{\n\t\tpins = {names};\n"
            f"\t\tfunction = \"{function}\";\n{bias}\t}};\n}};\n")


def pinctrl(o):
    return f'\tpinctrl-names = "default";\n\tpinctrl-0 = <&{label(o)}>;\n'


SPI_ROLES = ("mosi", "miso", "clk", "cs0")


def spi_bus(o, children, cs1_gpio=False):
    cs = f"\tcs-gpios = <0>, {gpio(pin_of(o, 'cs1-gpio'), 'GPIO_ACTIVE_LOW')};\n" if cs1_gpio else ""
    return (mux_group(o, "spi1", SPI_ROLES, pull=False) + "\n&spi1 {\n" + pinctrl(o) + cs +
            "\t#address-cells = <1>;\n\t#size-cells = <0>;\n\tstatus = \"okay\";\n\n" +
            children + "};\n")


def root(body):
    return "&{/} {\n" + body + "};\n"


def body(o):
    k, name = o["kind"], o["name"]
    if k == "i2c":
        fn = o["ctrl"]
        return (mux_group(o, fn) + f"\n&{fn} {{\n" + pinctrl(o) +
                "\tclock-frequency = <100000>;\n\tstatus = \"okay\";\n};\n")
    if k == "i2c-gpio":
        pu = "GPIO_ACTIVE_HIGH | GPIO_OPEN_DRAIN" + (
            "" if set(o["pins"]) & T.BOARD_PULLUPS else " | GPIO_PULL_UP")
        return root(f"\t{name} {{\n\t\tcompatible = \"i2c-gpio\";\n"
                    f"\t\tsda-gpios = {gpio(pin_of(o, 'sda'), pu)};\n"
                    f"\t\tscl-gpios = {gpio(pin_of(o, 'scl'), pu)};\n"
                    "\t\ti2c-gpio,delay-us = <5>;\n"
                    "\t\t#address-cells = <1>;\n\t\t#size-cells = <0>;\n\t};\n")
    if k == "spidev":
        two = "cs1-gpio" in o["pins"].values()
        kids = "".join(f"\tspidev@{i} {{\n\t\tcompatible = \"rohm,dh2228fv\";\n\t\treg = <{i}>;\n"
                       "\t\tspi-max-frequency = <50000000>;\n\t};\n" for i in range(2 if two else 1))
        return spi_bus(o, kids, cs1_gpio=two)
    if k == "uart":
        fn = o["ctrl"]
        flow = "\tuart-has-rtscts;\n" if "rts" in o["pins"].values() else ""
        return (mux_group(o, fn, pull=True) + f"\n&{fn} {{\n" + pinctrl(o) + flow +
                "\tstatus = \"okay\";\n};\n")
    if k == "pwm":
        # Several PWM pins can be enabled at once; each overlay setting pinctrl-0 on &pwm would
        # overwrite the others, so each pin's mux lives on its own holder node.
        fn = o["ctrl"]
        return (mux_group(o, fn, pull=False) + "\n&pwm {\n\tstatus = \"okay\";\n};\n\n" +
                root(f"\t{name}-mux {{\n\t\tcompatible = \"simple-pm-bus\";\n" +
                     pinctrl(o).replace("\t", "\t\t") + "\t};\n"))
    if k == "can":
        return f"&{o['ctrl']} {{\n\tstatus = \"okay\";\n}};\n"
    if k in ("mcp2515", "mcp251xfd"):
        osc = label(o, "osc")
        compat, speed = (("microchip,mcp2515", 10000000) if k == "mcp2515"
                         else ("microchip,mcp251xfd", 20000000))
        kid = (f"\tcan@0 {{\n\t\tcompatible = \"{compat}\";\n\t\treg = <0>;\n"
               f"\t\tclocks = <&{osc}>;\n\t\tinterrupts-extended = {irq(pin_of(o, 'int'))};\n"
               f"\t\tspi-max-frequency = <{speed}>;\n\t\tvdd-supply = <&reg_vcc_3v3>;\n\t}};\n")
        return (root(f"\t{osc}: {name}-osc {{\n\t\tcompatible = \"fixed-clock\";\n"
                     f"\t\t#clock-cells = <0>;\n\t\tclock-frequency = <{o['osc']}>;\n\t}};\n") +
                "\n" + spi_bus(o, kid))
    if k == "mcp3008":
        kid = ("\tadc@0 {\n\t\tcompatible = \"microchip,mcp3008\";\n\t\treg = <0>;\n"
               "\t\tspi-max-frequency = <1000000>;\n\t\tvref-supply = <&reg_vcc_3v3>;\n"
               "\t\t#io-channel-cells = <1>;\n\t};\n")
        return spi_bus(o, kid)
    p = next(iter(o["pins"]))
    if k == "w1":
        return root(f"\t{name} {{\n\t\tcompatible = \"w1-gpio\";\n\t\tgpios = {gpio(p)};\n\t}};\n")
    if k == "dht11":
        return root(f"\t{name} {{\n\t\tcompatible = \"dht11\";\n\t\tgpios = {gpio(p)};\n\t}};\n")
    if k == "gpio-ir":
        return root(f"\t{name} {{\n\t\tcompatible = \"gpio-ir-receiver\";\n"
                    f"\t\tgpios = {gpio(p, 'GPIO_ACTIVE_LOW')};\n"
                    "\t\tlinux,rc-map-name = \"rc-rc6-mce\";\n\t};\n")
    if k == "pwm-ir-tx":
        ch = int(o["ctrl"][3:])
        return (mux_group(o, o["ctrl"], pull=False) + "\n&pwm {\n\tstatus = \"okay\";\n};\n\n" +
                root(f"\t{name} {{\n\t\tcompatible = \"pwm-ir-tx\";\n\t\tpwms = <&pwm {ch} 0 0>;\n" +
                     pinctrl(o).replace("\t", "\t\t") + "\t};\n"))
    if k == "pps":
        return root(f"\t{name} {{\n\t\tcompatible = \"pps-gpio\";\n\t\tgpios = {gpio(p)};\n\t}};\n")
    if k == "shutdown":
        return root(f"\t{name} {{\n\t\tcompatible = \"gpio-keys\";\n\n\t\tshutdown {{\n"
                    "\t\t\tlabel = \"Shutdown\";\n\t\t\tlinux,code = <KEY_POWER>;\n"
                    f"\t\t\tgpios = {gpio(p, 'GPIO_ACTIVE_LOW')};\n"
                    "\t\t\tdebounce-interval = <100>;\n\t\t};\n\t};\n")
    raise SystemExit(f"{name}: unknown kind {k}")


def device(o):
    k, c = o["kind"], o["ctrl"]
    if k == "i2c":
        return f"/dev/i2c-{c[3:]}"
    if k == "i2c-gpio":
        return "/dev/i2c-N (first free number >= 4; HDMI DDC also takes one; see i2cdetect -l)"
    if k == "spidev":
        return "/dev/spidev1.0" + (" + /dev/spidev1.1" if len(o["pins"]) > 4 else "")
    if k == "uart":
        return f"/dev/ttyS{c[4:]}"
    if k == "pwm":
        return f"/sys/class/pwm/pwmchip0 channel {c[3:]}"
    if k in ("can", "mcp2515", "mcp251xfd"):
        return "network interface canN (ip link set canN up type can bitrate ...)"
    return {"mcp3008": "/sys/bus/iio/devices/iio:deviceN", "w1": "/sys/bus/w1/devices",
            "dht11": "/sys/bus/iio/devices/iio:deviceN", "gpio-ir": "/dev/lirc0 + input device",
            "pwm-ir-tx": "/dev/lircN (transmit)", "pps": "/dev/ppsN",
            "shutdown": "KEY_POWER -> systemd-logind poweroff"}[k]


def header(o):
    lines = [f"{p:>2} {port(p):<5} {r}" for p, r in o["pins"].items()]
    extra = [o[k] for k in ("note", "warn") if k in o]
    return ("// SPDX-License-Identifier: (GPL-2.0+ OR MIT)\n"
            f"// Mangue OS header overlay {o['name']} — GENERATED by tools/gen_overlays.py,\n"
            "// edit overlays/header_table.py instead.\n//\n// pin port  role\n" +
            "".join(f"//  {l}\n" for l in lines) + f"// device: {device(o)}\n" +
            "".join(f"// {e}\n" for e in extra) +
            "\n/dts-v1/;\n/plugin/;\n\n#include <dt-bindings/gpio/gpio.h>\n"
            "#include <dt-bindings/interrupt-controller/irq.h>\n"
            "#include <dt-bindings/input/linux-event-codes.h>\n\n")


# --- validation ---------------------------------------------------------------------------------
def load_mux(kernel):
    src = open(os.path.join(kernel, "drivers/pinctrl/sunxi/pinctrl-sun20i-d1.c")).read()
    mux = {}
    for b in re.split(r"SUNXI_PIN\(\s*SUNXI_PINCTRL_PIN\(", src)[1:]:
        m = re.match(r"([A-G]),\s*(\d+)\)", b)
        mux[f"P{m.group(1)}{m.group(2)}"] = set(re.findall(r'SUNXI_FUNCTION\(0x[0-9a-f]+,\s*"(\w+)"\)', b))
    return mux


MUX_KINDS = {"i2c": None, "uart": None, "pwm": None, "pwm-ir-tx": None, "can": None,
             "spidev": "spi1", "mcp2515": "spi1", "mcp251xfd": "spi1", "mcp3008": "spi1"}


def validate(mux):
    errs, names = [], set()
    for o in T.OVERLAYS:
        if o["name"] in names:
            errs.append(f"duplicate overlay {o['name']}")
        names.add(o["name"])
        for p, role in o["pins"].items():
            if p not in T.HEADER:
                errs.append(f"{o['name']}: pin {p} is not a header GPIO")
            elif p in T.RESERVED:
                errs.append(f"{o['name']}: pin {p} is reserved ({T.RESERVED[p]})")
            elif o["kind"] in MUX_KINDS and role not in ("int", "cs1-gpio"):
                fn = MUX_KINDS[o["kind"]] or o["ctrl"]
                if fn not in mux[port(p)]:
                    errs.append(f"{o['name']}: {port(p)} (pin {p}) has no mux function {fn}")
    return errs


# --- patches ------------------------------------------------------------------------------------
def new_file_diff(path, text):
    lines = text.splitlines(keepends=True)
    return (f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n"
            f"@@ -0,0 +1,{len(lines)} @@\n" + "".join("+" + l for l in lines))


def mod_file_diff(path, old, new):
    d = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                             f"a/{path}", f"b/{path}")
    return f"diff --git a/{path} b/{path}\n" + "".join(d)


def mail(subject, msg, diff):
    return ("From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001\n"
            "From: Mangue OS <noreply@mangueos>\nDate: Tue, 13 Oct 2026 12:00:00 +0400\n"
            f"Subject: [PATCH] {subject}\n\n{msg}\n---\n{diff}")


def line_names():
    names = {port: f"P{pin}" for pin, port in T.HEADER.items() if pin not in T.RESERVED}
    names.update({T.HEADER[p]: f"P{p}-CONSOLE" for p in T.RESERVED})
    names.update(T.ONBOARD_LINES)
    idx = {(ord(p[1]) - ord("A")) * 32 + int(p[2:]): n for p, n in names.items()}
    out = [idx.get(i, "") for i in range(max(idx) + 1)]
    rows = []
    for bank in range(0, len(out), 32):
        chunk = out[bank:bank + 32]
        rows.append(f"\t\t/* P{chr(ord('A') + bank // 32)} */\n" + "".join(
            "\t\t" + ", ".join(f'"{n}"' for n in chunk[i:i + 8]) + ",\n" for i in range(0, len(chunk), 8)))
    return "".join(rows).rstrip(",\n") + ";\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", default=DEFAULT_KERNEL)
    a = ap.parse_args()

    errs = validate(load_mux(a.kernel))
    if errs:
        sys.exit("table errors:\n  " + "\n  ".join(errs))

    os.makedirs(os.path.join(ROOT, "overlays/dtso"), exist_ok=True)
    dtso = {}
    for o in T.OVERLAYS:
        dtso[o["name"]] = header(o) + body(o)
    for f in os.listdir(os.path.join(ROOT, "overlays/dtso")):
        if f.endswith(".dtso") and f[:-5] not in dtso:
            os.remove(os.path.join(ROOT, "overlays/dtso", f))
    for n, t in dtso.items():
        open(os.path.join(ROOT, "overlays/dtso", n + ".dtso"), "w").write(t)

    # 0013: overlay directory + hook into the allwinner Makefile
    # The worktree may already carry 0013/0014 (re-applied by every build): strip our own appended
    # blocks first so the patches are always generated against the pre-patch files.
    mk = os.path.join(a.kernel, DTS_DIR, "Makefile")
    old_mk = open(mk).read().split(MK_MARK)[0].rstrip("\n") + "\n"
    new_mk = old_mk.rstrip("\n") + MK_MARK + "subdir-y += overlay\n"
    ov_mk = ("# SPDX-License-Identifier: GPL-2.0\n# Mangue OS: MangoPi MQ Pro header overlays "
             "(generated by tools/gen_overlays.py)\n" +
             "".join(f"dtb-$(CONFIG_ARCH_SUNXI) += {n}.dtbo\n" for n in sorted(dtso)))
    diff = mod_file_diff(f"{DTS_DIR}/Makefile", old_mk, new_mk)
    diff += new_file_diff(f"{DTS_DIR}/overlay/Makefile", ov_mk)
    for n in sorted(dtso):
        diff += new_file_diff(f"{DTS_DIR}/overlay/{n}.dtso", dtso[n])
    p13 = mail("riscv: dts: allwinner: MangoPi MQ Pro header overlays",
               f"{len(dtso)} overlays for the 40-pin header, all off by default; enabled with\n"
               "fdtoverlays in extlinux.conf (mqpro-io). Generated by tools/gen_overlays.py.", diff)

    # 0014: fixed bus numbering (= controller numbers) + GPIO line names (= physical pins)
    old_dts = open(os.path.join(a.kernel, BOARD_DTS)).read().split(DTS_MARK)[0].rstrip("\n") + "\n"
    aliases = "".join(f"\t\t{k} = &{v};\n" for k, v in T.ALIASES.items())
    new_dts = (old_dts.rstrip("\n") + DTS_MARK + "keep D1 controller numbers "
               "(/dev/i2c-0 = i2c0 ...), header GPIO lines are named by physical pin. */\n"
               f"/ {{\n\taliases {{\n{aliases}\t}};\n}};\n\n&pio {{\n\tgpio-line-names =\n"
               + line_names() + "};\n")
    p14 = mail("riscv: dts: allwinner: mangopi-mq-pro: fixed bus numbers, GPIO line names",
               "Aliases pin every I2C/SPI/UART controller to its own number so device nodes never\n"
               "depend on probe order; header GPIO lines are named P<physical pin>.",
               mod_file_diff(BOARD_DTS, old_dts, new_dts))

    for fn, txt in [("0013-riscv-dts-mangopi-mq-pro-header-overlays.patch", p13),
                    ("0014-riscv-dts-mangopi-mq-pro-aliases-line-names.patch", p14)]:
        open(os.path.join(PATCH_DIR, fn), "w").write(txt)

    db = {"generated_by": "tools/gen_overlays.py",
          "header": {str(p): {"port": port(p), "voltage": T.PIN_VOLTAGE.get(p, 3.3),
                              "pi_bcm": T.PI_BCM.get(p), "board_pullup": p in T.BOARD_PULLUPS,
                              "reserved": T.RESERVED.get(p)} for p in sorted(T.HEADER)},
          "overlays": {o["name"]: {"kind": o["kind"], "pins": {str(p): r for p, r in o["pins"].items()},
                                   "resource": o["ctrl"], "device": device(o),
                                   "note": o.get("note"), "warn": o.get("warn")} for o in T.OVERLAYS}}
    out = os.path.join(ROOT, "userpatches/overlay/mangueos/mqpro-io.json")
    open(out, "w").write(json.dumps(db, indent=1) + "\n")
    print(f"{len(dtso)} overlays, patches 0013/0014, {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
