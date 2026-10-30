#!/bin/bash
# Record the MQ Pro serial console to a log file (115200 8N1, raw).
# Usage: serial_capture.sh [/dev/ttyACM0] [logfile]
# Send input from another shell with: printf 'text\r' > /dev/ttyACM0
DEV=${1:-/dev/ttyACM0}
LOG=${2:-$(dirname "$(readlink -f "$0")")/../logs/serial_firstboot.log}
stty -F "$DEV" 115200 cs8 -cstopb -parenb raw -echo -crtscts || exit 1
echo "=== capture start $(date -Is) on $DEV ===" >> "$LOG"
exec cat "$DEV" >> "$LOG"
