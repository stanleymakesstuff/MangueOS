# Mangue OS vs. the other options for the MangoPi MQ Pro

Two kinds of evidence, kept apart:

- **Tested on a real board:** stock Armbian `mangopi-mq` (built from upstream `armbian/build` in October
  2026) vs. Mangue OS 0.1.
- **From other people's write-ups only (not tested here):** MangoPi's Tina Linux and the Ubuntu images
  people run on this board. See the second half.

## Stock Armbian vs. Mangue OS (both tested)

Mangue OS *is* built with Armbian's framework, so the base is the same: Debian 13 (trixie), minimal,
systemd, `apt`. Everything below is what changes on top.

| | Stock Armbian `mangopi-mq` | Mangue OS 0.1 |
|---|---|---|
| Maintenance | Community board, **no maintainer** | Own build; every release rebuildable from this repo |
| Kernel | 6.1.0-rc3 "edge" (smaeul `d1-wip`), a **release candidate** that gets no security fixes | **6.18.56 LTS** mainline + 14 patches (HDMI, PWM, MQ Pro device tree, header overlays, …) |
| First login | Serial or HDMI console only: `root` / `1234`, forced password change, then a wizard | **No screen needed:** fill in `mangue-setup.txt` on the card from your PC; user, Wi-Fi, hostname, timezone, language and SSH are set up on the first start. The console wizard is still there if you want it |
| Getting in without a screen | Only once Wi-Fi was set up from a console | Wi-Fi from the setup file, **or one USB-C cable**: the board shows up on Windows 11 as a network adapter + COM port, `ssh you@10.55.0.1` |
| "Where's my board?" | — | `mangue-status.txt` on the card: its addresses, setup state, how to connect |
| Changing settings later | Console tools only | Edit `mangue-setup.txt` again and boot: new password/user, Wi-Fi, hostname, timezone, language, SSH/USB-C on/off |
| Root | Root password login, root login over SSH allowed | No default login, **no root SSH**, root locked after a file-based setup; log in as yourself and `sudo` |
| Privacy | Wizard sends your public IP to `ipinfo.io` and `ipwhois.app` without asking | Asks first, default **no**; the file-based setup never sends it. No telemetry |
| Wi-Fi (RTL8723DS) | **Wedged 1–5 min after connecting**; only a driver reload brought it back | Fixed driver settings + automatic recovery. 24 h test: no reset, no wedge, 4 lost pings of 8603, one access-point drop recovered on its own in 6 s |
| Hangs | Hardware watchdog off | Hardware watchdog on: a hung board resets itself after 15 s |
| HDMI | Picture only at a forced 1080p; a 2K monitor gets **no picture** | Only modes the D1 can generate exactly (1080p/720p/480p) are offered, so 2K/4K monitors fall back to 1080p. Plug a monitor in while running → fresh login prompt |
| Header pins | Edit the device tree by hand | **43 ready-made overlays**, all off by default; `mqpro-io` switches them and **refuses pin conflicts** |
| Pin and bus names | Raw SoC line numbers, bus numbers follow probe order | GPIO lines named by physical pin (`P11`); fixed bus numbers (pins 3/5 = `/dev/i2c-0`); `mqpro-io pin GPIO17` translates Raspberry Pi numbers |
| GPIO/I2C/SPI as a normal user | root only | `gpio`/`i2c`/`spi` groups, new users get them |
| Drivers and tools | Armbian defaults; no `bluetoothctl`/`rfkill` | ~300 extra kernel drivers (sensors, ADC/DAC, RTC, CAN, IR, displays, …); i2c-tools, gpiod, can-utils, bluez, Python GPIO/I2C/SPI libs |
| Background activity | `unattended-upgrades`, apt timers, cron jobs contacting GitHub, an `apt` check at every boot | All removed; logs kept in RAM (less SD card wear) |
| Serial console | Left as a **root shell** after setup; line noise could freeze it | Logged out after setup; noise can't freeze it |
| Look | Armbian MOTD with tips and quotes | Mango logo, fastfetch, clean login banner |

### What Mangue OS doesn't have (be honest with yourself before you flash)

- **No kernel updates through `apt`.** The Armbian repository is removed and the kernel and U-Boot are
  held, so `apt upgrade` can't replace the custom device tree and overlays. Debian packages still update
  normally; a new kernel means a new Mangue OS image.
- **One person's project, version 0.1.** No Armbian forum support (Armbian doesn't support custom builds).
- **Header overlays not yet tested with real parts.** They're built and conflict-checked; whether every
  bus works with a device attached is still open.
- **No desktop, no GPU, no hardware video decoding.** The D1 has no GPU; its video engine has no
  mainline driver. HDMI is a text console.
- **HDMI modes:** 1080p, 720p and 480p only.
- **Wi-Fi is 2.4 GHz only** (that's the board's chip, same on every OS).

**Same on every OS:** a single 1 GHz RISC-V core and 1 GB RAM. Mangue OS doesn't make it faster.

## Other OS options (from write-ups, not tested here)

| OS | What it is | Status for the MQ Pro |
|---|---|---|
| **Tina Linux** (MangoPi/Allwinner) | Allwinner's SDK distro, based on **OpenWrt 14.07**, kernel **5.4** | The only image distributed by MangoPi; needs the OpenixCard tool to write; listed as "seems to be deprecated". The SDK needs a registration on Allwinner's site, docs mostly in Chinese |
| **Ubuntu** | No MQ Pro image. People boot the **Allwinner Nezha** or **Sipeed LicheeRV** image (same D1 chip) and swap in the MQ Pro device tree | 24.04 LTS (kernel 6.8) works this way. Out of the box only the serial console is on the header; I2C/SPI need device-tree edits; no overlays. **From 25.10 Ubuntu requires the RVA23 profile**, which the D1's C906 core predates, so 24.04 is most likely the last usable release (our conclusion; no source names the D1 explicitly) |
| **RVBoards Debian** | Debian build originally for the Nezha | Third-party; the 6.1 version also needs OpenixCard |
| Others | Arch, Fedora, openSUSE, Gentoo, NixOS, postmarketOS, … | Community ports; status varies |

## So why use it?

If you want the MQ Pro to be a **small headless Linux box you can set up from your PC and wire things to**,
Mangue OS is the shortest path: a current LTS kernel with security fixes, Wi-Fi that stays up, SSH over
one USB-C cable when it doesn't, and the header ready to use without editing device trees. If you need
a desktop, video playback or kernel updates through `apt`, it isn't for you (and on this chip, nothing
really is for the first two).

Sources:
- [awesome-mango-pi-mq-pro](https://github.com/boosterl/awesome-mango-pi-mq-pro) (OS list, Tina "distributed by MangoPi", OpenixCard, "seems to be deprecated")
- [easytarget/MQ-Pro-IO](https://github.com/easytarget/MQ-Pro-IO) (Ubuntu 24.04.1 via the LicheeRV image, what works by default)
- [bret.dk: Ubuntu on the MangoPi MQ Pro (22.04.1)](https://bret.dk/?p=1663) (Nezha image boots on the MQ Pro)
- [CNX: MangoPi MQ Pro](https://www.cnx-software.com/2022/04/09/mangopi-mq-pro-a-20-risc-v-alternative-to-raspberry-pi-zero-w/) (Tina or Debian)
- [CNX: Allwinner D1 SDK](https://cnx-software.com/2021/05/02/allwinner-d1-sdk-linux-risc-v-documentation) and [T113 Tina build guide](https://ohmbedkernel.substack.com/p/embedded-linux-with-t113-s3-part) (OpenWrt 14.07, kernel 5.4, `d1_mq_pro-tina`)
- [CNX: Ubuntu 25.10 mandates RVA23](https://www.cnx-software.com/news/RISC-V/page/7/?amp=1)
