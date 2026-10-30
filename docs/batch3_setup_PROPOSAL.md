# Batch 3 — first-boot setup (decisions 2026-10-14; implemented in userpatches, not yet built)

## Decided (user, 2026-10-14)
- **No root login over SSH.** Users log in as themselves with a password every time and use `sudo`.
  No SSH keys required. (`PermitRootLogin no`; password authentication stays on.)
- **No default login.** First boot always creates the user's own account and password (Pi Imager model).
  No `admin`/`password` — universal default passwords are banned for consumer connectable products in the
  UK (PSTI, 2024) and are the reason Raspberry Pi OS dropped `pi`/`raspberry` in 2022.
- **Setup file on the FAT boot partition**, editable from Windows/macOS/Linux: `mangue-setup.txt`.
- **No Wi-Fi hotspot / captive portal.** With the setup file there is no point (user). → hostapd + dnsmasq
  can leave the image; the AP-mode test of the RTL8723DS is no longer needed.
- **SSH over USB-C (gadget)** as the cable path.

## Hardware: USB-C ports (schematic v1.2, docs/reference/mq-pro-sch-v12.pdf p.3)
| Port | Controller | CC resistors | Powers the board |
|---|---|---|---|
| J1 "OTG" | USB0 (musb, the only device-capable controller; DT `dr_mode = "peripheral"`) | 5.1 k pull-downs (sink) | yes — VBUS → VCCIN |
| J2 "HOST" | USB1 (EHCI/OHCI) | 36 k pull-ups (source) | no |
→ One cable laptop ↔ J1 = power + USB gadget (like a Pi Zero). User confirms one port is power+OTG.

## Setup paths (proposed order)
1. `mangue-setup.txt` on the boot partition (offline, any OS).
2. USB-C gadget on J1: USB-Ethernet (+ serial console) → `ssh <user>@mqpro.local` or a fixed address.
3. Serial console / HDMI + keyboard: the wizard, as today (fixed: hidden SSID, junk SSID entry, B7b).
4. ~~Bluetooth (Improv Wi-Fi over BLE)~~ — dropped (user: the setup file covers Wi-Fi).

## `mangue-setup.txt` (draft format)
```
# Mangue OS first-boot setup. Fill in, save, put the card in the board.
# Lines starting with # are ignored. Passwords are erased from this file after first boot.
username=
password=            # plain text; or password_hash= (from: openssl passwd -6)
hostname=mqpro
wifi_ssid=
wifi_password=
wifi_hidden=no       # yes for networks that don't broadcast their name
wifi_country=AE      # regulatory domain (channels/power)
timezone=Asia/Dubai
locale=en_GB.UTF-8
ssh=yes
```
- Read once at first boot (before any login); the stock wizard then runs unattended from presets and
  password lines are emptied with a `# password: used at first boot and erased` note.
- Incomplete file (no username/password) → the console wizard runs as today.
- Plain-text password accepted because Windows users can't produce a crypt hash without tools; it lives on
  the card only until first boot. `password_hash=` for those who prefer it.

## Implementation (2026-10-14)
- `mangue-setup` (+ `.service`, before `systemd-user-sessions`): translates the file into Armbian's own
  unattended presets (`PRESET_USER_NAME/PASSWORD/TIMEZONE/LOCALE`, random `PRESET_ROOT_PASSWORD`) in
  `/root/.not_logged_in_yet` → the stock wizard runs unattended on the autologin console (tested logic,
  incl. autologin cleanup). Writes Wi-Fi netplan itself (hidden SSID, regulatory domain, JSON-escaped).
  Hostname, SSH off, USB gadget off. Run-once marker; secrets scrubbed from the FAT file; result in
  `/boot/mangue-setup-result.txt`. Next boot: `passwd -l root` (+ apply `password_hash=`).
  Tested in a fake root: BOM/CRLF, password with `# " ' $ \`, hidden SSID (YAML re-parsed), bad/reserved
  usernames, hash path, reboot before the wizard finished (Wi-Fi config not clobbered).
- `PermitRootLogin no` via `/etc/ssh/sshd_config.d/10-mangue-ssh.conf`.
- USB gadget: kernel `USB_ETH=n` (built-in legacy g_ether held the OTG port) → `mangue-usb-gadget`
  configfs composite NCM (+ `WINNCM` MS OS descriptor) + ACM (`serial-getty@ttyGS0`), stable MACs from
  machine-id; networkd `usb0` 10.55.0.1/24 with DHCP server (no router/DNS offered, RequiredForOnline=no).
  `avahi-daemon` for `<hostname>.local`. hostapd/dnsmasq removed from the image.
- **To prove on hardware (image #7):** Windows 11 binds NCM without a driver (else fall back to RNDIS +
  driver like rpi-usb-gadget); ACM console on Windows; unattended first boot end-to-end from a file edited
  on Windows; root locked on boot 2; hidden SSID joins.

## Open
- USB gadget: Windows binding is the one unproven assumption (see "To prove"). Addressing decided:
  fixed 10.55.0.1 + DHCP for the PC + mDNS; ACM serial console included.
- Wizard fixes: hidden SSID entry, `* SSID List` junk entry, skipped-Wi-Fi netplan generator errors (B19),
  path-dependent default locale (B7b).
