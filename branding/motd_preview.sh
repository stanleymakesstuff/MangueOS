#!/bin/bash
# Mangue OS login banner preview (draft). Y=mango body, G=leaf/stem.
Y=$'\e[38;5;214m'; G=$'\e[38;5;34m'; B=$'\e[1m'; D=$'\e[2m'; R=$'\e[0m'
L=(
"${G}         ,--.${R}"
"${G}    .---/ ,-'${R}"
"${G}   ( __/ /${R}"
"${Y}  .-'\"\"'-.._${R}"
"${Y}.'          \`-.${R}"
"${Y}/              \`.${R}"
"${Y}|                \\${R}"
"${Y};                 |${R}"
"${Y} \\                ;${R}"
"${Y}  \`.             /${R}"
"${Y}    \`-.       .-'${R}"
"${Y}       \`-.__.-'${R}"
)
I=(
"${B}${Y}Mangue OS${R} ${B}0.1${R} ${D}(Debian trixie)${R}"
"${D}──────────────────────────${R}"
"${B}Host${R}     maker@mqpro"
"${B}Board${R}    MangoPi MQ Pro v1.4"
"${B}Kernel${R}   6.18.x riscv64"
"${B}CPU${R}      Allwinner D1 · C906 @ 1 GHz"
"${B}Memory${R}   212M / 985M"
"${B}Disk${R}     3.1G / 29G"
"${B}IP${R}       192.168.1.42 (wlan0)"
"${B}Temp${R}     41°C"
"${B}Overlays${R} i2c-pins3-5 spi-pins19-24"
""
)
strip() { sed 's/\x1b\[[0-9;]*m//g' <<<"$1"; }
for i in "${!L[@]}"; do
  raw=$(strip "${L[$i]}"); pad=$((22 - ${#raw}))
  printf '%s%*s %s\n' "${L[$i]}" "$pad" "" "${I[$i]}"
done
