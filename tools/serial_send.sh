#!/bin/bash
# serial_send.sh 'text' 'expect-regex' [timeout_s] [--secret]
# Send text+CR to the board, then wait until expect-regex appears in output that arrived
# AFTER the send (byte offset, never a tail window). Prints the new output (ANSI stripped,
# Wi-Fi password masked). Exit 1 on timeout. Empty regex = just send and wait 3 s.
LOG=${LOG:?set LOG=<path to the serial capture log>}
TTY=${TTY:-/dev/ttyACM1}
text=$1 re=$2 to=${3:-30}
off=$(stat -c %s "$LOG")
printf '%s\r' "$text" > "$TTY"
new() { tail -c +$((off + 1)) "$LOG" | sed -e 's/\x1b\[[0-9;?]*[a-zA-Z]//g' -e 's/\r//g' ${MASK:+-e "s/$MASK/********/g"}; }
if [ -z "$re" ]; then sleep 3; new | tail -5; exit 0; fi
for i in $(seq 1 $((to * 2))); do
	new | grep -a -q -E "$re" && { new | tail -5; exit 0; }
	sleep 0.5
done
echo "TIMEOUT ($to s) waiting for /$re/ after sending '$([ -n "$4" ] && echo '<secret>' || echo "$text")'"; new | tail -8
exit 1
