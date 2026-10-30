# Mangue OS vs. the original OS options for the MangoPi MQ Pro

Written 2026-10-15 (image #10). Two kinds of evidence, kept apart:

- **Tested by us:** stock Armbian `mangopi-mq` (our phase-1 build, 2026-10-09/10) vs. Mangue OS 0.1 (images #6–#10), both on our board.
- **From sources only (not tested by us):** MangoPi's own Tina Linux and the Ubuntu images people use on this board. See the bottom section.

## Stock Armbian vs. Mangue OS (both tested on our board)

| Area | Stock Armbian `mangopi-mq` (phase 1) | Mangue OS 0.1 |
|---|---|---|
| Support status | Community board, **no maintainer** | Our own build on upstream `armbian/build`; every image rebuildable from a git tag |
| Kernel | 6.1.0-rc3 "edge" (smaeul `d1-wip` branch) — a **release candidate** that gets no security fixes | **6.18.56 LTS** mainline, pinned, + 14 patches (HDMI port, mode filter, header overlays, …) |
| Kernel/U-Boot updates | Through the Armbian apt repo (could replace a custom DTB) | Armbian repo removed, kernel/U-Boot **held**; Debian packages only |
| Base | Debian trixie, minimal | Debian trixie, minimal |
| First login | Serial/HDMI console only: `root` / `1234`, forced password change, then the wizard | **Headless:** edit `mangue-setup.txt` on the FAT boot partition (readable on Windows) → user, Wi-Fi, hostname, timezone, locale, SSH set up unattended. Console wizard still there as plan B |
| Root access | Root password login, `PermitRootLogin yes` over SSH | **No root SSH, no default login**; root locked after a file-based setup; you log in as yourself and use `sudo` |
| Privacy | Wizard sends your public IP to `ipinfo.io` and `ipwhois.app` without asking | Asks first, default **no**; unattended setup never sends it |
| Getting connected without a screen | Wi-Fi only after you configured it on a console | Wi-Fi from the setup file, **or one USB-C cable**: board shows up on Windows 11 as a network adapter + COM port (no drivers), `ssh user@10.55.0.1` |
| "Where is my board?" | — | `mangue-status.txt` on the boot partition: addresses, setup state, how to connect, failed services (USB-C line fixed in #10) |
| Wi-Fi reliability | RTL8723DS **wedged 1–5 min after connecting** (only a driver reload recovered it) | Roaming off + automatic driver recovery; **24 h soak: no reset, no wedge**, 0 failures after hour 1 |
| Crash recovery | Hardware watchdog not enabled | Hardware watchdog: the board resets itself if it hangs for 15 s |
| HDMI | Picture only at a forced 1080p; a 2K monitor gets **no picture** at its native mode | Ported to 6.18; only modes the D1 can make exactly (1080p/720p/480p) are offered, so 2K/4K monitors fall back to 1080p automatically. Text console only; the D1 has no GPU |
| Header pins (I2C/SPI/UART/PWM/1-Wire/CAN/IR) | Hand-edit the device tree | **43 ready-made overlays**, all off by default; `mqpro-io` turns them on and **refuses pin conflicts** |
| Pin naming | Raw SoC line numbers | Lines named by physical pin (`P11`, …); `mqpro-io pin GPIO17` translates Raspberry Pi names |
| Bus numbering | Not pinned (follows probe order) | Fixed: pins 3/5 = `/dev/i2c-0`, SPI = `/dev/spidev1.0`, … |
| Drivers | Armbian defaults | ~300 extra drivers (Pi-defconfig baseline: sensors/IIO, CAN, IR, I2C-GPIO, RTCs, …) |
| User permissions for GPIO/I2C/SPI | root only | `gpio`/`i2c`/`spi` groups + udev rules; new users get them automatically |
| Userland for the header | Not installed (no `bluetoothctl`, no `rfkill`) | bluez, rfkill, libgpiod, i2c-tools, spidev and the other protocol tools |
| Background traffic & wear | `unattended-upgrades`, apt timers, cron jobs that contact GitHub, `apt-get upgrade -s` at every boot | All removed; logs in RAM |
| Serial console | Root shell left open after setup; line noise could freeze it | Logged out after unattended setup (B22); XON/XOFF off so noise can't freeze output (B24) — **both new in #10, to verify on hardware** |
| Look | Armbian MOTD with tips/quotes and update counter | Mangue OS branding: mango logo, fastfetch, clean `/etc/issue` |

**Kept the same:** Debian base, `apt`, systemd, netplan, the RTL8723DS vendor driver (no mainline alternative), the D1's speed (single 1 GHz core, 1 GB RAM).

**Not better (yet):** no GPU or video acceleration (the chip has none); HDMI modes beyond 1080p/720p/480p untested (B16); per-bus hardware tests with real parts still to do (phase 3).

## Other OS options (from sources, not tested by us)

| OS | What it is | Status for the MQ Pro |
|---|---|---|
| **Tina Linux** (MangoPi/Allwinner) | Allwinner's SDK distro, based on **OpenWrt 14.07**, kernel **5.4** (SDK target `d1_mq_pro-tina`) | The only image "distributed by MangoPi"; needs the OpenixCard tool to write; listed as "seems to be deprecated". SDK needed a registration on Allwinner's site, docs mostly in Chinese |
| **Ubuntu** (Canonical) | No MQ Pro image. People boot the **Allwinner Nezha** or **Sipeed LicheeRV** image (same D1 chip) and swap in the MQ Pro device tree | 24.04 LTS (kernel 6.8) works this way. Default device tree only gives you the serial console on the header; I2C/SPI need device-tree edits; Wi-Fi only if preconfigured before first boot; no overlays. From **25.10, Ubuntu requires the RVA23 profile**. The D1's C906 core predates RVA23 (its vector unit is the pre-standard 0.7.1 draft), so 24.04 is most likely the last usable release. That is our conclusion; no source names the D1 explicitly |
| **RVBoards Debian** | Debian build originally for the Nezha | Third-party; the 6.1 version also needs OpenixCard |
| Others | Arch, Fedora, openSUSE, Gentoo, NixOS, Deepin, Slackware, FreeBSD, postmarketOS, … | Community ports listed in the awesome-mango-pi-mq-pro list; status varies |

The point of Mangue OS: a **current LTS kernel** with the D1 bits ported forward, plus the **beginner/headless and header-I/O tooling** none of the options above ship.

Sources:
- [awesome-mango-pi-mq-pro](https://github.com/boosterl/awesome-mango-pi-mq-pro) (OS list, Tina "distributed by MangoPi", OpenixCard, "seems to be deprecated")
- [easytarget/MQ-Pro-IO](https://github.com/easytarget/MQ-Pro-IO) (Ubuntu 24.04.1 via the LicheeRV image, what works by default)
- [bret.dk: Ubuntu on the MangoPi MQ Pro (22.04.1)](https://bret.dk/?p=1663) (Nezha image boots on the MQ Pro)
- [CNX: MangoPi MQ Pro](https://www.cnx-software.com/2022/04/09/mangopi-mq-pro-a-20-risc-v-alternative-to-raspberry-pi-zero-w/) (Tina or Debian)
- [CNX: Allwinner D1 SDK](https://cnx-software.com/2021/05/02/allwinner-d1-sdk-linux-risc-v-documentation) and [T113 Tina build guide](https://ohmbedkernel.substack.com/p/embedded-linux-with-t113-s3-part) (OpenWrt 14.07, kernel 5.4, `d1_mq_pro-tina`)
- [CNX: Ubuntu 25.10 mandates RVA23](https://www.cnx-software.com/news/RISC-V/page/7/?amp=1)
- Stock-Armbian column: our phase-1 tests and bug list B1–B13 in `README.md`
