#!/bin/sh
# Mangue OS Wi-Fi soak, runs ON the board (a sleeping PC can't break it).
# Start:  sudo systemd-run --unit=mangue-soak sh /home/<user>/board_soak.sh   (DURATION=86400 s default;
#         it stops itself and writes an "end" line, so the unit ends clean instead of 'failed')
# Log on the SD card (not the RAM journal), synced: /var/lib/mangueos/soak.log
#   FAIL lines: gateway unreachable; hourly heartbeat: tries, fails, uptime (a reset shows as a
#   smaller uptime / missing heartbeats), wifi-recover activations, Wi-Fi driver refusals.
GW=${GW:-$(ip -4 route show default dev wlan0 | awk '{print $3; exit}')}
LOG=/var/lib/mangueos/soak.log
mkdir -p /var/lib/mangueos
w() { echo "$(date '+%F %T') up=$(cut -d. -f1 /proc/uptime)s $*" >> "$LOG"; sync "$LOG"; }
START=$(cut -d. -f1 /proc/uptime)
w "start gw=$GW boot=$(cat /proc/sys/kernel/random/boot_id | cut -c1-8)"
DURATION=${DURATION:-86400}
n=0; f=0
while [ "$(cut -d. -f1 /proc/uptime)" -lt "$((START + DURATION))" ]; do
	n=$((n + 1))
	if ! ping -c1 -W3 "$GW" >/dev/null 2>&1; then
		f=$((f + 1)); w "FAIL #$f try $n $(ip -br -4 addr show wlan0 | tr -s ' ')"
	fi
	if [ $((n % 360)) -eq 0 ]; then
		rec=$(journalctl -q -b -t mangue-wifi-recover --no-pager 2>/dev/null | grep -c reloading)
		ref=$(journalctl -q -b -t wpa_supplicant --no-pager 2>/dev/null | grep -c 'driver failed')
		w "heartbeat tries=$n fails=$f wifi-recover=$rec driver-refusals=$ref"
	fi
	sleep 10
done
w "end tries=$n fails=$f after ${DURATION}s"
