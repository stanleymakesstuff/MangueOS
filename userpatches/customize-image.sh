#!/bin/bash
# Mangue OS image customization (runs in the image chroot; userpatches/overlay → /tmp/overlay).
# arguments: $RELEASE $LINUXFAMILY $BOARD $BUILD_DESKTOP
set -e
RELEASE=$1 LINUXFAMILY=$2 BOARD=$3
OV=/tmp/overlay/mangueos
MANGUE_VERSION=0.1
export DEBIAN_FRONTEND=noninteractive

echo "Mangue OS: customize-image for ${BOARD} ${RELEASE}"

# --- Packages ---------------------------------------------------------------
apt-get update
apt-get install -y --no-install-recommends \
	gpiod python3-libgpiod i2c-tools spi-tools python3-smbus2 python3-spidev \
	bluez rfkill \
	fastfetch dosfstools device-tree-compiler usbutils \
	can-utils pps-tools ir-keytable v4l-utils libiio-utils lm-sensors \
	python3-can python3-serial picocom \
	avahi-daemon
# (Batch 3: no setup hotspot -> no hostapd/dnsmasq. avahi-daemon = <hostname>.local over Wi-Fi and USB.)

# --- Strip auto-updates and periodic apt work ----------------------------------
apt-get purge -y unattended-upgrades 2>/dev/null || true
for t in apt-daily.timer apt-daily-upgrade.timer man-db.timer; do
	systemctl disable "$t" 2>/dev/null || true
	systemctl mask "$t" 2>/dev/null || true
done

# --- Repo lockdown: no Armbian repo, Armbian kernel/U-Boot/base-files held -----
apt-get purge -y armbian-config 2>/dev/null || true
rm -f /etc/apt/sources.list.d/armbian*.sources /etc/apt/sources.list.d/armbian*.list
# Installed packages only: dpkg-query also lists virtual names (linux-image-armbian ...) that can't be held.
dpkg-query -W -f '${db:Status-Abbrev} ${Package}\n' 'linux-image-*' 'linux-dtb-*' 'linux-u-boot-*' 'armbian-*' 2>/dev/null \
	| awk '$1 == "ii" {print $2}' | xargs -r apt-mark hold

# --- Branding -------------------------------------------------------------------
install -d /usr/share/mangueos
install -m 0644 "$OV/logo_motd.ans" "$OV/logo_large.ans" "$OV/wordmark.ans" /usr/share/mangueos/

cat > /usr/lib/os-release <<OSR
PRETTY_NAME="Mangue OS ${MANGUE_VERSION} (trixie)"
NAME="Mangue OS"
VERSION_ID="${MANGUE_VERSION}"
VERSION="${MANGUE_VERSION} (trixie)"
VERSION_CODENAME=trixie
ID=mangueos
ID_LIKE=debian
OSR
ln -sf ../usr/lib/os-release /etc/os-release

install -m 0644 "$OV/issue" /etc/issue
printf 'Mangue OS %s\n' "$MANGUE_VERSION" > /etc/issue.net

# SSH MOTD: our header replaces Armbian's header/sysinfo/tips/commands/ip/ap blocks.
# Deleted, not chmod -x: armbian-firstlogin runs `chmod +x /etc/update-motd.d/*` when the
# wizard finishes. path-exclude keeps a bsp-cli reinstall/upgrade from bringing them back.
install -m 0755 "$OV/10-mangue-header" /etc/update-motd.d/10-mangue-header
ARMBIAN_MOTD="10-armbian-header 15-ap-info 20-ip-info 25-containers-info 30-armbian-sysinfo 35-armbian-tips 41-commands"
# B12: cron jobs that only fed those blocks: armbian-quotes downloads a tips file from
# github.armbian.com daily (third-party call, writes /etc/update-motd.d/quotes.txt);
# armbian-updates runs `apt-get upgrade -s` twice at every boot + daily for the sysinfo line.
ARMBIAN_CRON="/etc/cron.daily/armbian-quotes /etc/cron.d/armbian-updates"
{
	for f in $ARMBIAN_MOTD; do
		rm -f "/etc/update-motd.d/$f"
		echo "path-exclude=/etc/update-motd.d/$f"
	done
	for f in $ARMBIAN_CRON; do
		rm -f "$f"
		echo "path-exclude=$f"
	done
} > /etc/dpkg/dpkg.cfg.d/mangueos-motd
rm -f /etc/update-motd.d/quotes.txt

# --- Bug fixes found on hardware (README "Bug hunt 2026-10-12") -------------------
# B1: 8723ds options: power saving + driver-internal roaming off (see 8723ds.conf).
install -m 0644 "$OV/8723ds.conf" /etc/modprobe.d/8723ds.conf
# B1 safety net: reload the driver when it refuses associations (see wifi-recover header).
install -D -m 0755 "$OV/wifi-recover" /usr/lib/mangueos/wifi-recover
install -m 0644 "$OV/mangue-wifi-recover.service" "$OV/mangue-wifi-recover.timer" /etc/systemd/system/
systemctl enable mangue-wifi-recover.timer

# Hang recovery (user decision 2026-10-12): U-Boot no longer arms the watchdog, so a hung
# headless board would stay dead. systemd feeds the D1 watchdog (sunxi-wdt, max 16 s) and the
# chip resets if the system stops responding for 15 s. RebootWatchdogSec covers a stuck reboot;
# it must fit the D1 watchdog's 16 s maximum (2min was rejected by systemd-shutdown: EINVAL).
install -d /etc/systemd/system.conf.d
printf '[Manager]\nRuntimeWatchdogSec=15s\nRebootWatchdogSec=15s\n' > /etc/systemd/system.conf.d/mangue-watchdog.conf

# B13: first-login wizard must not send the public IP to ipinfo.io/ipwhois.app without consent.
# python3 is already in the image (python3-libgpiod). Fails the build if Armbian changed the code.
python3 "$OV/firstlogin-privacy.py" /usr/lib/armbian/armbian-firstlogin
# B19 (junk "* SSID List" entry, empty-SSID netplan file on skip) + B22 (log out the console
# after an unattended setup). Fails the build if Armbian changed the code.
python3 "$OV/firstlogin-fixes.py" /usr/lib/armbian/armbian-firstlogin

# B24: no XON/XOFF on serial consoles. Line noise (adapter unplugged or dropped) sent an XOFF and
# froze all console output for hours. 00- so it runs before the first-login wizard's profile.d hook.
printf '%s\n' '# Mangue OS: no XON/XOFF on serial consoles (a stray ^S from line noise froze all output)' \
	'case $(tty 2>/dev/null) in /dev/ttyS*|/dev/ttyGS*) stty -ixon 2>/dev/null ;; esac' \
	> /etc/profile.d/00-mangue-serial.sh

# B11: armbian-ramlog makes /var/log/journal a symlink to /var/log.hdd/journal; systemd's
# journal-nocow.conf then fails to set +C on it at every boot. +C (no-COW) only matters on btrfs;
# the rootfs is ext4, so mask the file.
ln -sf /dev/null /etc/tmpfiles.d/journal-nocow.conf

# B5: don't take the hostname from DHCP (networkd isn't allowed to set it → error on every lease).
install -d /etc/systemd/network/10-netplan-wlan0.network.d
printf '[DHCPv4]\nUseHostname=no\n' > /etc/systemd/network/10-netplan-wlan0.network.d/mangue-no-dhcp-hostname.conf

# B9: Debian alsa-utils 1.2.14-1 rule defines LABEL alsa_restore_go twice and alsa_restore_std
# never (udev logs 2 errors per sound card). Ship a fixed copy only while the bug is present.
ALSA_RULE=/usr/lib/udev/rules.d/90-alsa-restore.rules
if [ -f "$ALSA_RULE" ] && ! grep -q 'LABEL="alsa_restore_std"' "$ALSA_RULE" \
	&& [ "$(grep -c 'LABEL="alsa_restore_go"' "$ALSA_RULE")" = 2 ]; then
	awk '/LABEL="alsa_restore_go"/ && ++n == 2 {sub(/alsa_restore_go/, "alsa_restore_std")} {print}' \
		"$ALSA_RULE" > /etc/udev/rules.d/90-alsa-restore.rules
fi

install -D -m 0644 "$OV/fastfetch.jsonc" /etc/xdg/fastfetch/config.jsonc

# --- First-boot setup (batch 3) ---------------------------------------------------------------
# /boot/mangue-setup.txt (FAT, editable on any PC) drives Armbian's first-login wizard unattended.
install -D -m 0755 "$OV/mangue-setup" /usr/lib/mangueos/mangue-setup
install -m 0644 "$OV/mangue-setup.service" /etc/systemd/system/
systemctl enable mangue-setup.service
# Locale from the setup file: generated after boot, retried every boot until it succeeded (B27).
install -m 0755 "$OV/mangue-locale" /usr/lib/mangueos/mangue-locale
install -m 0644 "$OV/mangue-locale.service" /etc/systemd/system/
systemctl enable mangue-locale.service
install -m 0644 "$OV/mangue-setup.txt" /boot/mangue-setup.txt
# B20 diagnostics: no RAM logging until the first login was reached (journal survives a hung first boot).
install -D -m 0644 "$OV/ramlog-firstboot.conf" /etc/systemd/system/armbian-ramlog.service.d/10-mangue-firstboot.conf
# armbian-truncate-logs (cron) checks only ENABLED=true and runs `journalctl --relinquish-var`, which
# sends the journal back to RAM even while ramlog is skipped -> act only when ramlog is really active.
TL=/usr/lib/armbian/armbian-truncate-logs
grep -q '^\[ "\$ENABLED" != true \] && exit 0$' "$TL" || { echo "Mangue OS: armbian-truncate-logs changed" >&2; exit 1; }
sed -i 's/^\[ "\$ENABLED" != true \] && exit 0$/&\nsystemctl is-active -q armbian-ramlog.service || exit 0  # Mangue OS (B20)/' "$TL"
grep -q 'Mangue OS (B20)' "$TL" || { echo "Mangue OS: truncate-logs patch failed" >&2; exit 1; }
# No root login over SSH (users log in as themselves and use sudo); Debian reads sshd_config.d first.
install -D -m 0644 "$OV/10-mangue-ssh.conf" /etc/ssh/sshd_config.d/10-mangue-ssh.conf
# SSH over USB-C: NCM + serial gadget on the OTG port, DHCP for the PC from networkd, login on ttyGS0.
install -m 0755 "$OV/mangue-usb-gadget" /usr/lib/mangueos/mangue-usb-gadget
install -m 0644 "$OV/mangue-usb-gadget.service" /etc/systemd/system/
systemctl enable mangue-usb-gadget.service
install -m 0644 "$OV/50-mangue-usb0.network" /etc/systemd/network/
# serial-getty@ttyGS0 is pulled in by mangue-usb-gadget.service (Wants=), not enabled on its own (B28).
install -D -m 0644 "$OV/ttyGS0-noreset.conf" /etc/systemd/system/serial-getty@ttyGS0.service.d/10-mangue-noreset.conf
# Board status on the FAT partition (addresses, setup state, stuck boot jobs): readable on any PC.
install -m 0755 "$OV/mangue-status" /usr/lib/mangueos/mangue-status
install -m 0644 "$OV/mangue-status.service" "$OV/mangue-status.timer" /etc/systemd/system/
systemctl enable mangue-status.timer

# --- Header I/O (batch 2): mqpro-io + its overlay/conflict DB (generated by tools/gen_overlays.py)
install -D -m 0755 "$OV/mqpro-io" /usr/bin/mqpro-io
install -D -m 0644 "$OV/mqpro-io.json" /usr/share/mangueos/mqpro-io.json
install -m 0644 "$OV/mangue-i2c-devices.service" /etc/systemd/system/
systemctl enable mangue-i2c-devices.service
install -m 0644 "$OV/90-mangue-serial0.rules" /etc/udev/rules.d/
# Console: kernel errors only on tty1/ttyS0; monitor plugged in while running -> fresh tty1 login (B16 test).
install -D -m 0644 "$OV/10-mangue-console.conf" /etc/sysctl.d/10-mangue-console.conf
install -m 0755 "$OV/mangue-hdmi-login" /usr/lib/mangueos/mangue-hdmi-login
install -m 0644 "$OV/mangue-hdmi-login.service" /etc/systemd/system/
install -m 0644 "$OV/70-mangue-hdmi.rules" /etc/udev/rules.d/
# GPIO/SPI/PWM access for group members (Pi convention); the wizard adds new users to gpio i2c spi.
groupadd --system gpio 2>/dev/null || true
groupadd --system spi 2>/dev/null || true
groupadd --system i2c 2>/dev/null || true
install -m 0644 "$OV/60-mangue-gpio.rules" /etc/udev/rules.d/
FL=/usr/lib/armbian/armbian-firstlogin
grep -q 'for additionalgroup in sudo ' "$FL" || { echo "Mangue OS: armbian-firstlogin group list changed" >&2; exit 1; }
sed -i 's/for additionalgroup in sudo /for additionalgroup in gpio i2c spi sudo /' "$FL"
# A second autologin console used to drop to a ROOT SHELL while the wizard ran on another one.
# Instead: show the message, wait until setup is done, then log that console out.
perl -0pi -e 's/(echo -e "\\nFirst login setup is already running on \$\{holder:-another console\}\.\\n"\n)(\s*)exit 0/${1}${2}trap "" INT\n${2}while [[ -f \/root\/.not_logged_in_yet ]]; do sleep 2; done\n${2}[[ -z "\$\{SSH_CONNECTION\}" ]] \&\& kill -HUP "\$PPID"\n${2}exit 0/' "$FL"
grep -q 'while \[\[ -f /root/.not_logged_in_yet \]\]; do sleep 2; done' "$FL" && bash -n "$FL" \
	|| { echo "Mangue OS: firstlogin second-console patch failed" >&2; exit 1; }
# Overlays must be in the image (kernel dtbs_install → /boot/dtb/allwinner/overlay); fail the build if not.
ls /boot/dtb/allwinner/overlay/*.dtbo >/dev/null 2>&1 || { echo "Mangue OS: no header overlays in /boot/dtb" >&2; exit 1; }

echo "Mangue OS: customize-image done"
