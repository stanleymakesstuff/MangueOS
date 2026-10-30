#!/bin/bash
# reboot_loop.sh <cycles> <result log> <password>: B20 regression loop over the serial console (USER_=<login>).
# Each cycle: reboot from a logged-in serial shell, require "mqpro login:" on ttyS0 within TIMEOUT s and
# exactly one U-Boot SPL banner (= no extra reset), log in, record uptime / system state / gettys / locks.
# Stops at the first failure so the board stays in the failed state for inspection.
# Needs LOG= (running serial capture) and TTY=, like serial_send.sh. The password is only ever typed at
# a no-echo prompt (login / sudo), never on a command line, so it does not reach the capture log.
set -u
N=${1:?cycles} OUT=${2:?result log} PW=${3:?password}
: "${LOG:?}" "${TTY:?}"
TIMEOUT=${TIMEOUT:-240} HOST=${HOST:-mqpro} USER_=${USER_:?set USER_=<login name>}
D=$(dirname "$0")
send() { "$D/serial_send.sh" "$@"; }
clean() { sed -e 's/\x1b\[[0-9;?]*[a-zA-Z]//g' -e 's/\r//g'; }
login() {
	send '' 'login:|\$ $' 10 | grep -q '\$ $' && return 0
	send "$USER_" 'assword' 15 >/dev/null && send "$PW" '\$ $' 40 --secret >/dev/null
}
echo "=== B20 reboot loop start $(date -Is), $N cycles, timeout ${TIMEOUT}s" >> "$OUT"
login || { echo "cannot log in before cycle 1" | tee -a "$OUT"; exit 1; }
for c in $(seq 1 "$N"); do
	off=$(stat -c %s "$LOG")
	send 'sudo systemctl reboot' 'assword for' 8 | grep -q 'assword for' && send "$PW" '' 0 --secret >/dev/null
	t0=$(date +%s) ok=NO
	while [ $(( $(date +%s) - t0 )) -lt "$TIMEOUT" ]; do
		tail -c +$((off + 1)) "$LOG" | clean | grep -aq "^$HOST login:" && { ok=YES; break; }
		sleep 3
	done
	dt=$(( $(date +%s) - t0 ))
	spl=$(tail -c +$((off + 1)) "$LOG" | grep -ac 'U-Boot SPL ')
	line="cycle $c: serial_login=$ok after ${dt}s, SPL=$spl"
	if [ "$ok" = YES ] && login; then
		m=$(stat -c %s "$LOG")
		send 'clear; stty cols 200; echo "R: up=$(cut -d. -f1 /proc/uptime)s state=$(systemctl is-system-running) gs0=$(systemctl is-active serial-getty@ttyGS0) s0=$(systemctl is-active serial-getty@ttyS0) udc=$(cat /sys/class/udc/*/state | tr " " _) locks=$(wc -l < /proc/locks) failed=$(systemctl --failed --no-legend | wc -l)"' '^R: up=' 30 >/dev/null
		line="$line | $(tail -c +$((m + 1)) "$LOG" | clean | grep -a '^R: up=' | tail -1 | cut -c4-)"
	fi
	echo "$line" | tee -a "$OUT"
	[ "$ok" = YES ] && [ "$spl" = 1 ] || { echo "=== FAILED at cycle $c $(date -Is), board left as is" | tee -a "$OUT"; exit 1; }
done
echo "=== B20 reboot loop PASSED $N/$N $(date -Is)" | tee -a "$OUT"
