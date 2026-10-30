#!/usr/bin/env python3
"""Mangue OS fixes to Armbian's first-login wizard (B19, B22, B29).

- B19a: the Wi-Fi scan grepped every line containing "SSID", so iw's "* SSID List" capability
  line showed up as a network. Take only real "SSID:" lines.
- B19b: skipping Wi-Fi (Enter at "Enter a number of SSID") still wrote a netplan file with an
  empty SSID and applied it, up to 3 times -> netplan generator errors. Skip now leaves the loop.
- B22: an unattended (preset) run on a console left that console logged in as root with nobody
  at it (serial noise then typed into a root shell). Log the console out after setup; an SSH
  session is kept.
- B29: the locale "atomic write" renames a temp file over /etc/default/locale, which on trixie is a
  symlink to ../locale.conf: the rename replaced the symlink, so logins got the chosen locale but
  systemd/localectl (/etc/locale.conf) kept the image default. Write to the symlink's target instead.
- B31: offline (Wi-Fi skipped) the locale search matches every locale -> a 337-entry menu, then the
  tzselect menus; online with one match (UAE: only ar_AE) it was set without asking. Interactive runs
  now always get a short list (the country's own locales first, others can be typed) and a one-line
  timezone prompt.
- B32: an interactive run on a console also left it as a root shell. Log out after every console run
  (SSH kept) and say which user to log in as.

Usage: firstlogin-fixes.py /usr/lib/armbian/armbian-firstlogin
Exits non-zero (fails the image build) if Armbian changed the code this relies on.
"""
import subprocess
import sys

path = sys.argv[1]
s = open(path).read()


def need(cond, msg):
    if not cond:
        sys.exit(f"Mangue OS: firstlogin-fixes: {msg}")


SCAN_OLD = ("iw dev ${WIFI_DEVICE} scan 2> /dev/null | egrep 'SSID' | sed 's/^[ \\t]*//' "
            "| sed 's/\"//g' | sed 's/SSID: //' | sed '/^$/d'")
SCAN_NEW = ("iw dev ${WIFI_DEVICE} scan 2> /dev/null | sed -n 's/^[[:space:]]*SSID:[[:space:]]*//p' "
            "| sed 's/\"//g' | sed '/^$/d'")
need(s.count(SCAN_OLD) == 1, "Wi-Fi scan line changed (B19a)")
s = s.replace(SCAN_OLD, SCAN_NEW)

SKIP_ANCHOR = ('\t\t\t\t\t\t\tif [[ "$input" =~ ^[0-9]{,2}$ ]] ; then break; fi\n'
               '\t\t\t\t\t\tdone\n')
SKIP_NEW = SKIP_ANCHOR + ('\t\t\t\t\t\t# Mangue OS B19b: Enter = skip Wi-Fi; don\'t write an empty-SSID netplan file\n'
                          '\t\t\t\t\t\tif [[ -z "${input}" ]]; then broken=0; break; fi\n')
need(s.count(SKIP_ANCHOR) == 1, "SSID prompt loop changed (B19b)")
s = s.replace(SKIP_ANCHOR, SKIP_NEW)

LOC_OLD = '\t\t# change default locales (atomic write)\n\t\tlocal _f="/etc/default/locale"\n'
LOC_NEW = ('\t\t# change default locales (atomic write)\n'
           '\t\t# Mangue OS B29: write the symlink target (/etc/locale.conf), don\'t replace the symlink\n'
           '\t\tlocal _f="$(readlink -f /etc/default/locale)"\n')
need(s.count(LOC_OLD) == 1, "locale write changed (B29)")
s = s.replace(LOC_OLD, LOC_NEW)

LOCALE_ANCHOR = '\t\telif [[ "${#options[@]}" -gt 1 ]]; then\n\t\t\toptions+=("Skip generating locales")\n'
LOCALE_NEW = ('\t\telif [[ $preset_unattended != 1 ]]; then\n'
              '\t\t\t# Mangue OS B31: always ask: the country\'s locales first (none offline: the search then\n'
              '\t\t\t# matched every locale), then a short list; others can be typed\n'
              '\t\t\t[[ -z "${CCODE}" || -z "${options[0]}" ]] && options=()\n'
              '\t\t\tfor l in en_GB.UTF-8 en_US.UTF-8 de_DE.UTF-8 fr_FR.UTF-8 es_ES.UTF-8 ar_AE.UTF-8; do\n'
              '\t\t\t\t[[ " ${options[*]} " == *" ${l} "* ]] || options+=("${l}")\n'
              '\t\t\tdone\n'
              '\t\t\toptions+=("Other (type its name)" "Skip generating locales")\n'
              '\t\t\techo -e "\\nChoose your language and formats (locale):\\n"\n'
              "\t\t\tPS3='Please enter your choice:'\n"
              '\t\t\tselect opt in "${options[@]}"; do\n'
              '\t\t\t\tcase "${opt}" in\n'
              '\t\t\t\t"") ;;\n'
              '\t\t\t\t"Other (type its name)")\n'
              '\t\t\t\t\tread -r -p "Locale name (example: it_IT.UTF-8): " opt\n'
              '\t\t\t\t\tif awk -v l="${opt}" \'$1 == l {f = 1} END {exit !f}\' /usr/share/i18n/SUPPORTED; then LOCALES=${opt}; break; fi\n'
              '\t\t\t\t\techo "\'${opt}\' is not a known locale (capitals matter)." ;;\n'
              '\t\t\t\t*) LOCALES=${opt}; break ;;\n'
              '\t\t\t\tesac\n'
              '\t\t\tdone\n') + LOCALE_ANCHOR
need(s.count(LOCALE_ANCHOR) == 1, "locale menu changed (B31)")
s = s.replace(LOCALE_ANCHOR, LOCALE_NEW)

TZ_OLD = '\t\t\t\tTZDATA=$(tzselect | tail -1)\n'
TZ_NEW = ('\t\t\t\t# Mangue OS B31: one line instead of the tzselect menus (? still opens them)\n'
          '\t\t\t\twhile :; do\n'
          '\t\t\t\t\tread -r -p "Timezone (examples: Asia/Dubai, Europe/London, America/New_York; Enter = keep $(cat /etc/timezone 2>/dev/null || echo UTC), ? = menu): " TZDATA\n'
          '\t\t\t\t\t[[ -z ${TZDATA} ]] && break\n'
          '\t\t\t\t\tif [[ ${TZDATA} == "?" ]]; then TZDATA=$(tzselect | tail -1); break; fi\n'
          '\t\t\t\t\t[[ ${TZDATA} != *..* && -f /usr/share/zoneinfo/${TZDATA} ]] && break\n'
          '\t\t\t\t\techo "\'${TZDATA}\' is not a known timezone (capitals matter)."\n'
          '\t\t\t\tdone\n')
need(s.count(TZ_OLD) == 1, "tzselect call changed (B31)")
s = s.replace(TZ_OLD, TZ_NEW)

END_ANCHOR = "# Marker cleanup is handled by _firstlogin_cleanup EXIT trap.\n"
END_NEW = END_ANCHOR + '''
# Mangue OS B22/B32: don't leave a console logged in as root after setup (unattended: nobody is
# there; interactive: the owner would stay root). Clean up first (the HUP ends this script too).
# An SSH session is kept.
if [[ -z "${SSH_CONNECTION}" ]]; then
	if [[ ${preset_unattended:-0} != 1 ]]; then
		echo -e "\\nSetup done. Log in as \\e[0;92m${RealUserName:-your new user}\\x1B[0m with the password you just chose."
		sleep 5
	fi
	_firstlogin_cleanup
	kill -HUP "$PPID"
fi
'''
need(s.count(END_ANCHOR) == 1 and s.endswith(END_ANCHOR), "script end changed (B22)")
s = s.replace(END_ANCHOR, END_NEW)

open(path, "w").write(s)
need(subprocess.run(["bash", "-n", path]).returncode == 0, "patched script fails bash -n")
print("Mangue OS: firstlogin fixes B19a B19b B22 B29 B31 B32 applied")
