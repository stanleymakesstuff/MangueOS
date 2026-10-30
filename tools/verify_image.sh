#!/bin/bash
# verify_image.sh <image> [previous image]: offline check of a built Mangue OS image (loop mount in the
# Armbian docker; WSL has no passwordless sudo). Compares every installed overlay file with the project
# source, checks units / drop-ins / patches / boot partition, and (with a previous image) lists the
# Debian package versions that changed. Exit 1 if any check fails.
set -u
P=$(dirname "$(dirname "$(readlink -f "$0")")")
IMG=$(realpath "${1:?image}") PREV=${2:+$(realpath "$2")}
exec docker run --rm --privileged -v /dev:/dev -v "$P:/p:ro" -v "$(dirname "$IMG"):/img:ro" \
	${PREV:+-v "$(dirname "$PREV"):/prev:ro"} \
	-e IMG="/img/$(basename "$IMG")" -e PREV="${PREV:+/prev/$(basename "$PREV")}" \
	ghcr.io/armbian/docker-armbian-build:armbian-debian-trixie-latest bash -c '
set -u; fail=0
ok() { echo "  ok   $*"; }; bad() { echo "  FAIL $*"; fail=1; }
mnt() { # image dir -> loop device; mounts p2 on dir, p1 on dir/boot
	local l; l=$(losetup -f --show -P -r "$1"); mkdir -p "$2"
	mount -o ro "${l}p2" "$2" && mount -o ro "${l}p1" "$2/boot"; echo "$l"; }
L=$(mnt "$IMG" /r); R=/r; O=/p/userpatches/overlay/mangueos
echo "== files vs source"
same() { cmp -s "$O/$1" "$R$2" && ok "$2" || bad "$2 differs from overlay/$1"; }
same mangue-setup /usr/lib/mangueos/mangue-setup
same mangue-locale /usr/lib/mangueos/mangue-locale
same mangue-status /usr/lib/mangueos/mangue-status
same mangue-usb-gadget /usr/lib/mangueos/mangue-usb-gadget
same mangue-hdmi-login /usr/lib/mangueos/mangue-hdmi-login
for u in mangue-setup.service mangue-locale.service mangue-usb-gadget.service mangue-status.service \
	mangue-status.timer mangue-hdmi-login.service mangue-wifi-recover.service mangue-wifi-recover.timer \
	mangue-i2c-devices.service; do same $u /etc/systemd/system/$u; done
same ttyGS0-noreset.conf /etc/systemd/system/serial-getty@ttyGS0.service.d/10-mangue-noreset.conf
same ramlog-firstboot.conf /etc/systemd/system/armbian-ramlog.service.d/10-mangue-firstboot.conf
same 10-mangue-console.conf /etc/sysctl.d/10-mangue-console.conf
same 70-mangue-hdmi.rules /etc/udev/rules.d/70-mangue-hdmi.rules
same 10-mangue-ssh.conf /etc/ssh/sshd_config.d/10-mangue-ssh.conf
same mangue-setup.txt /boot/mangue-setup.txt
echo "== units"
W=$R/etc/systemd/system
for w in multi-user.target.wants/mangue-setup.service multi-user.target.wants/mangue-locale.service \
	multi-user.target.wants/mangue-usb-gadget.service timers.target.wants/mangue-status.timer \
	timers.target.wants/mangue-wifi-recover.timer getty.target.wants/serial-getty@ttyS0.service; do
	[ -L "$W/$w" ] && ok "enabled $w" || bad "not enabled: $w"; done
[ -e "$W/getty.target.wants/serial-getty@ttyGS0.service" ] && bad "ttyGS0 getty enabled on its own (B28)" || ok "ttyGS0 getty not enabled on its own (B28)"
grep -qx "Wants=serial-getty@ttyGS0.service" "$W/mangue-usb-gadget.service" && ok "gadget Wants ttyGS0 getty" || bad "gadget lacks Wants="
ls "$W"/*scrub* "$W"/*/*scrub* >/dev/null 2>&1 && bad "mangue-setup-scrub still installed" || ok "no scrub service"
grep -qx "Type=exec" "$W/mangue-locale.service" && ok "mangue-locale Type=exec" || bad "mangue-locale not Type=exec"
echo "== patches"
grep -q "Mangue OS (B20)" "$R/usr/lib/armbian/armbian-truncate-logs" && ok "truncate-logs patch" || bad "truncate-logs patch missing"
for b in B19b B22 B29 B31 B32; do grep -qE "Mangue OS (B[0-9a-z]+/)*$b\b" "$R/usr/lib/armbian/armbian-firstlogin" && ok "wizard patch $b" || bad "wizard patch $b missing"; done
[ "$(readlink "$R/etc/default/locale")" = ../locale.conf ] && ok "/etc/default/locale -> ../locale.conf (B29)" || bad "/etc/default/locale not the locale.conf symlink"
[ -e "$R/var/lib/mangueos/locale-pending" ] && bad "locale-pending baked into image" || ok "no locale-pending in image"
ls "$R"/usr/lib/mangueos/__pycache__ >/dev/null 2>&1 && bad "pycache in image" || ok "no pycache"
echo "== boot partition"
t=$(sfdisk --part-type "$L" 1 2>/dev/null); lab=$(blkid -s LABEL -o value "${L}p1")
[ "${t^^}" = EBD0A0A2-B9E5-4433-87C0-68B6B72699C7 ] && ok "p1 type Microsoft basic data" || bad "p1 type $t"
[ "$lab" = MANGUEOS ] && ok "p1 label MANGUEOS" || bad "p1 label $lab"
echo "  overlays: $(ls $R/boot/dtb/allwinner/overlay/*.dtbo 2>/dev/null | wc -l) dtbo"
echo "  kernel:   $(ls $R/boot | grep -E "^vmlinuz|^Image" | tr "\n" " ")"
if [ -n "$PREV" ]; then
	echo "== Debian packages vs $(basename $PREV)"
	L2=$(mnt "$PREV" /q)
	pk() { awk "/^Package:/{p=\$2} /^Version:/{print p\" \"\$2}" "$1/var/lib/dpkg/status" | sort; }
	pk /q > /tmp/a; pk /r > /tmp/b
	echo "  packages: $(wc -l < /tmp/a) -> $(wc -l < /tmp/b)"
	join -a1 -a2 -e "-" -o 0,1.2,2.2 /tmp/a /tmp/b | awk "\$2 != \$3 {print \"  \" \$1\": \"\$2\" -> \"\$3}"
	umount /q/boot /q; losetup -d "$L2"
fi
umount /r/boot /r; losetup -d "$L"
[ $fail = 0 ] && echo "== ALL CHECKS PASSED" || { echo "== SOME CHECKS FAILED"; exit 1; }
'
