# Mangue OS

A minimal Debian 13 (trixie) image for the **MangoPi MQ Pro** (Allwinner D1, RISC-V), built with the
[Armbian build framework](https://github.com/armbian/build). *Mangue* is French for mango.

**Headless-first and beginner-friendly:** set the board up from a text file on your PC, then log in over
Wi-Fi or a single USB-C cable. No screen, keyboard or serial adapter needed (all three still work).

- Linux 6.18 with D1 HDMI (1080p/720p console), hardware PWM and the MQ Pro device tree
- Set up from `mangue-setup.txt` on the card's FAT partition: user, Wi-Fi, hostname, timezone, language,
  SSH, USB-C gadget. Edit it again later to change settings; passwords are erased after use.
- SSH over USB-C (USB Ethernet + serial gadget; tested with Windows 11's built-in drivers, standard NCM/ACM classes for macOS and Linux)
- 43 header overlays (I2C, SPI, UART, PWM, CAN, 1-Wire, …), all off by default, managed by `mqpro-io`
  with pin-conflict checking; GPIO lines named by physical pin (`P11`); Raspberry Pi pin lookup
- No default login, no root login over SSH, no telemetry

## Download and getting started

Get the `.img.xz` from [Releases](../../releases) and follow **[RELEASE_NOTES.md](RELEASE_NOTES.md)**:
flashing, the setup file, connecting, security defaults, hardware notes and known issues.

## Status

Version 0.1, the first release. Tested on hardware: both setup paths (setup file and screen/serial
wizard), changing settings from the card, Wi-Fi (24 h test), USB-C gadget, HDMI, repeated reboots.
**Not yet tested with real parts:** the header overlays (buses with devices attached). Reports welcome.

## Building from source

Needs an x86-64 Linux machine (or WSL2 on a Linux filesystem, not `/mnt/c`) with Docker; 25 GB or more
of free disk.

```sh
git clone https://github.com/armbian/build armbian-build
cd armbian-build
git checkout 813ae7cf3ccd40df1d287733e1838ed0812ceeb8   # the framework commit 0.1 was built with
cp -r /path/to/this/repo/userpatches .
./compile.sh mangueos
```

The image lands in `output/images/`. `userpatches/` holds everything Mangue OS adds:

| Path | What |
|---|---|
| `userpatches/config-mangueos.conf` | Build profile (board `mangopi-mq`, branch `current`, trixie, minimal) |
| `userpatches/kernel/archive/d1-6.18/` | Kernel patches on top of Linux `v6.18.56`: D1 HDMI, D1 PWM, MQ Pro DT, header overlays, bus aliases, GPIO line names |
| `userpatches/linux-d1-current.config` | Kernel config |
| `userpatches/u-boot/` | U-Boot patch (overlay load address); U-Boot itself is smaeul's `d1-wip` |
| `userpatches/customize-image.sh` | Image customisation: services, setup, branding, wizard fixes |
| `userpatches/overlay/mangueos/` | Files installed into the image (`mangue-setup`, `mqpro-io`, units, …) |
| `overlays/header_table.py` | Single source for the header pins and overlays; `tools/gen_overlays.py` generates the overlays, kernel patches 0013/0014 and `mqpro-io.json` |
| `tools/` | Development helpers (overlay generator, kernel-config helper, image verifier, serial test scripts, soak/benchmark tools). Some assume the Armbian tree at `~/mangopi_mqpro/build`; edit the path if yours differs. |
| `docs/` | Header pin map and design notes |
| `branding/` | Logo sources and converters |

## Credits

- [Armbian](https://github.com/armbian/build): build framework, board support, first-login wizard
- Samuel Holland ([smaeul](https://github.com/smaeul)): D1 U-Boot and the D1 HDMI work the HDMI patches
  are ported from
- The authors of the sun20i PWM driver series (see the patch headers)
- [easytarget/MQ-Pro-IO](https://github.com/easytarget/MQ-Pro-IO): MQ Pro header pin map
- Debian

## License

GPL-2.0, see [LICENSE](LICENSE). Kernel and U-Boot patches keep the authorship and sign-offs in their
headers. The images contain Debian packages and firmware under their own licenses (see
`/usr/share/doc/*/copyright` on the board). The kernel and U-Boot sources for each release are the
upstream versions named above plus the patches in this repository.
