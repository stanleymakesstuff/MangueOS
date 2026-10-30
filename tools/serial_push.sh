#!/bin/bash
# serial_push.sh <local file> <remote path>: copy a file to the board over the logged-in serial shell
# (base64 heredoc into /tmp, sha256 compared). Needs LOG= and TTY= like serial_send.sh.
set -e
src=$1 dst=$2
: "${LOG:?}" "${TTY:?}"
D=$(dirname "$0")
"$D/serial_send.sh" "stty -echo; base64 -d > $dst <<'B64END'" '' >/dev/null
base64 -w 76 "$src" | while IFS= read -r l; do printf '%s\r' "$l" > "$TTY"; sleep 0.02; done
"$D/serial_send.sh" 'B64END' '' >/dev/null
want=$(sha256sum "$src" | cut -d' ' -f1)
"$D/serial_send.sh" "stty echo; sha256sum $dst" "$want|[0-9a-f]{64}" 20 | grep -q "$want" && echo "OK $dst" || { echo "MISMATCH $dst"; exit 1; }
