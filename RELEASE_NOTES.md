# Mangue OS — release notes (draft)

Minimal Debian 13 (trixie) image for the MangoPi MQ Pro (Allwinner D1, RISC-V), built with the Armbian
build framework. **Headless-first and beginner-friendly:** set up from a text file on your PC, then log
in over Wi-Fi or one USB-C cable. HDMI console supported.

## 0.1 (unreleased)

**Download:** `MangueOS-0.1_mqpro_6.18.56.img.xz` (compressed, `<fill in>` MB; unpacks to a 1.93 GB
`.img`). sha256 of the `.xz`: `<fill in>`, of the `.img`: `<fill in>`. Check it before flashing:
`sha256sum` (Linux/macOS) or `Get-FileHash` (PowerShell). Needs a microSD card of 4 GB or more.

### Getting started (no screen or keyboard needed)
1. Flash the image. **Raspberry Pi Imager** ("Choose OS" → "Use custom" → the `.img.xz`) and
   **balenaEtcher** take the `.xz` file directly; for other tools unpack it first with 7-Zip.
   - Imager asks "Would you like to apply OS customisation settings?" → answer **No**. Those settings
     are written for Raspberry Pi OS; Mangue OS ignores them. Use `mangue-setup.txt` instead (step 2).
2. Re-insert the card in your PC. Open the drive **MANGUEOS** and edit **`mangue-setup.txt`** in
   Notepad/TextEdit: your username and password, Wi-Fi name and password, and choose country, timezone
   and language by deleting the `#` in front of one line each. The file explains itself.
   - Windows may offer to *format* the card's other (Linux) part — click **Cancel**.
3. Put the card in the board and power it. First start takes 3–5 minutes.
4. Connect from PowerShell/Terminal:
   - Wi-Fi: `ssh yourname@mqpro.local`
   - USB-C: plug the board's **OTG** port (the one that powers it) into your PC with a data cable, then
     `ssh yourname@10.55.0.1`. (The other USB-C port is for USB devices only: no login there.) The board also appears as a serial port (login prompt) on the same cable.
     Uses the drivers built into Windows 11 (tested); macOS and Linux have standard drivers for it (not
     tested yet).
5. Something wrong? Put the card back in the PC: `mangue-setup-result.txt` says what setup did,
   `mangue-status.txt` shows the board's addresses and state.

Your passwords are erased from `mangue-setup.txt` after the first start.

### Setting up on a screen + keyboard or a serial cable instead
Leave username and password in `mangue-setup.txt` empty. At first start the console (HDMI + USB
keyboard, or a 3.3 V serial adapter on the header's UART pins at 115200 baud) shows
"Press Enter to start the first login setup on this console". The wizard asks for a root password, your
username and password, Wi-Fi (optional), language and timezone, then logs out: log in with your new
account. Language: a short list (your country's languages first when timezone detection is on; any
other can be typed). Timezone without detection: type it (example: `Asia/Dubai`).

**Changing settings later:** edit `mangue-setup.txt` again on the PC and start the board. Changes are
applied on that start: a new password or a new user, Wi-Fi, hostname, SSH and USB-C on/off, timezone,
language. Passwords are erased again; `mangue-setup-result.txt` lists what was changed. A new language
is generated in the background (a few minutes) and finishes on the next start if the board is switched
off first.

### Security defaults
- **No default login.** Every board gets the account its owner creates.
- **No root login over SSH.** Log in as yourself and use `sudo`. After a file-based setup the root
  password is locked (as on Raspberry Pi OS). The screen/serial wizard asks for a root password, so
  there root can log in on the console (never over SSH).
- SSH uses password login (no keys required); keys can be added as usual.

### Header I/O (40-pin)
- 43 device-tree overlays for the header (I2C, SPI, UART, PWM, CAN, 1-Wire, DHT11, IR, PPS, shutdown
  button, MCP2515/MCP251xFD, MCP3008), all off by default. Manage them with **`mqpro-io`**:
  `mqpro-io list`, `mqpro-io pins`, `mqpro-io pin GPIO17`, `sudo mqpro-io enable i2c0-pins3-5`, reboot.
  Conflicting choices (same pin or same controller) are refused.
- **MangoPi numbering:** GPIO lines are named by physical pin (`gpioget P11`), buses keep the D1
  controller numbers (`/dev/i2c-0` = pins 3/5). `mqpro-io pin GPIO17` translates Raspberry Pi numbers.
- GPIO, I2C, SPI and PWM work without sudo for members of the `gpio`, `i2c`, `spi` groups (new users
  are added automatically).
- About 300 kernel drivers for common sensors, ADCs/DACs, RTCs, displays, GPIO expanders, CAN, IR and
  touch controllers (Raspberry Pi kernel config as the baseline). Add an I2C sensor with
  `sudo mqpro-io i2c-add 0 bme280 0x76 --persist`.
- Tools included: i2c-tools, gpiod, can-utils, pps-tools, ir-keytable, v4l-utils, libiio-utils,
  lm-sensors, python3-libgpiod/smbus2/spidev/can/serial, picocom.
- **Pins 27/28 are 2.8 V I/O** (board pull-ups to 3.3 V): open-drain I2C only.

### Build
- Kernel: Linux 6.18.56 (pinned tag `v6.18.56`) + Mangue OS patches (D1 HDMI, D1 PWM, MQ Pro DT,
  header overlays, bus aliases and GPIO line names).
- Armbian framework commit: `813ae7cf3ccd` (2026-10-08). U-Boot 2024.01-rc1 (smaeul `d1-wip`, commit
  `2e89b706`), watchdog autostart disabled, autoboot stops only on the string `mq`.
- Debian packages as of 2026-10-26 (rootfs built that day). Updates come from `deb.debian.org` with
  `apt`; kernel, U-Boot and board packages are held (no Armbian repository).
- Hang recovery: systemd drives the D1 hardware watchdog (15 s; also during reboot).

### Privacy
- The first-login wizard checks for internet access by contacting `deb.debian.org`.
- **Automatic timezone detection is opt-in** in the console wizard ("Detect timezone from your IP?
  [y/N]"): **y** sends your public IP to **ipinfo.io** and **ipwhois.app**; **n** (default) contacts
  neither. A file-based setup never asks and never contacts them.
- No telemetry, no automatic update checks, no Armbian tips/quotes download. The board announces its
  name on the local network (mDNS, `mqpro.local`).

### Hardware notes
- **Power:** a dedicated 5 V supply rated **2 A or more**, or a PC USB port through the OTG port.
  Multi-port USB-C PD chargers that briefly cut all ports when another device renegotiates cause silent
  resets.
- **Wi-Fi** (RTL8723DS) is 2.4 GHz only. Driver power saving and driver-internal roaming are off; a
  watchdog timer reloads the driver if it stops accepting connections (rare vendor-driver wedge).
- **HDMI:** 1920x1080, 1280x720 and 720x480/576 only (fixed D1 PHY setup, 297 MHz PLL). Monitors with a
  higher native mode get the best of these (tested: a 2160x1440 monitor runs at 1920x1080). A monitor
  whose EDID offers none of these gets no picture. A monitor plugged in while the board runs shows a
  fresh login prompt. The screens show only kernel errors; everything else is in `dmesg` / the journal.
- No GPU (the D1 has none): software rendering only. No RTC: the clock is right once the board reaches
  the internet (an I2C RTC module is supported).

### Known issues and limits
- **Header overlays are not yet tested with real parts** (I2C/SPI/UART/CAN/... devices). They are built and
  checked for pin conflicts; whether every bus works with a device attached is still open.
- **Rare reset during the very first start** (seen once on a test build, cause unknown, not seen on the
  two builds since). If it happens, leave the board powered: it starts again by itself.
- **Wi-Fi:** in a 24 h test the board lost about 1 ping in 2000 (4 of 8603) and
  reconnected after an access-point disconnect on its own. The vendor driver can still wedge in rare cases; the driver-reload watchdog covers that.
- **File-based setup with a screen or serial cable attached:** setup runs on one console; the other shows
  "First login setup is already running on another console", then a login prompt.
- **HDMI:** see the mode list under Hardware notes.
- **Moving to another Wi-Fi network from the setup file:** type the new name **and** its password. A
  new name with an empty password is refused (the old network is kept; `wifi_open=yes` for a network
  without a password). A **wrong** password for the new network is not caught: the board drops off
  Wi-Fi. Reach it over the USB-C cable (`ssh yourname@10.55.0.1`) and fix the file.
