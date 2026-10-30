#!/bin/bash
# Merge a driver list (SYMBOL=value per line, # comments) into a kernel config file in place.
# Existing lines for each symbol ("CONFIG_X=…" or "# CONFIG_X is not set") are replaced.
# usage: tools/apply_kernel_drivers.sh <list> <config>
set -e
LIST=$1 CFG=$2
[ -f "$LIST" ] && [ -f "$CFG" ] || { echo "usage: $0 <list> <config>" >&2; exit 1; }
syms=$(grep -vE '^\s*(#|$)' "$LIST" | sed 's/=.*//')
pat=$(printf '%s\n' $syms | sed 's/.*/^(# )?CONFIG_&[= ]/' | paste -sd'|')
grep -vE "$pat" "$CFG" | grep -vxF "# --- Mangue OS: $(basename "$LIST") ---" > "$CFG.tmp"
{
	echo "# --- Mangue OS: $(basename "$LIST") ---"
	grep -vE '^\s*(#|$)' "$LIST" | sed -E 's/^(\w+)=n$/# CONFIG_\1 is not set/; t; s/^/CONFIG_/'
} >> "$CFG.tmp"
mv "$CFG.tmp" "$CFG"
