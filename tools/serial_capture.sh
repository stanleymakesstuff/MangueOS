#!/bin/bash
# Record the MQ Pro serial console to a log file (115200 8N1, raw).
# Usage: serial_capture.sh [/dev/ttyACM0] [logfile]
# Send input from another shell with: printf 'text\r' > /dev/ttyACM0
DEV=${1:-/dev/ttyACM0}
LOG=${2:-$(dirname "$(readlink -f "$0")")/../logs/serial_firstboot.log}
# Two readers split the bytes between them: both logs then miss random chunks (2026-10-30).
for p in $(pgrep -x cat); do
	ls -l "/proc/$p/fd" 2>/dev/null | grep -q -- "-> $(readlink -f "$DEV")$" && { echo "already captured by PID $p ($(readlink "/proc/$p/fd/1")); stop it first" >&2; exit 1; }
done
stty -F "$DEV" 115200 cs8 -cstopb -parenb raw -echo -crtscts || exit 1
echo "=== capture start $(date -Is) on $DEV ===" >> "$LOG"
exec cat "$DEV" >> "$LOG"
