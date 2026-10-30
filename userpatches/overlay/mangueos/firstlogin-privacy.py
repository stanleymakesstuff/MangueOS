#!/usr/bin/env python3
"""B13: stop armbian-firstlogin from sending the public IP to third parties without asking.

- https://ipinfo.io/ip is its "are we online?" probe (3 call sites) -> probe deb.debian.org
  instead (apt contacts it anyway).
- http://ipwhois.app/json/<ip> guesses timezone/country (with an empty IP it geolocates the
  caller anyway) -> only after an explicit yes; default no, unattended = no. On no, the
  wizard falls back to its manual timezone menu.

Usage: firstlogin-privacy.py /usr/lib/armbian/armbian-firstlogin
Exits non-zero (fails the image build) if Armbian changed the code this relies on.
"""
import re
import subprocess
import sys

path = sys.argv[1]
s = open(path).read()

PROBE_OLD = 'PUBLIC_IP=$(curl --max-time 5 -s https://ipinfo.io/ip)'
PROBE_NEW = 'PUBLIC_IP=$(curl --max-time 5 -fsI http://deb.debian.org/debian/ >/dev/null && echo online)'
GEO_OLD = 'curl --max-time 5 -s "http://ipwhois.app/json/${PUBLIC_IP}" |'
GEO_NEW = ('{ [[ $MANGUE_GEO == y ]] && curl --max-time 5 -s '
           '"http://ipwhois.app/json/$(curl --max-time 5 -s https://ipinfo.io/ip)"; } |')
ANCHOR = '\t# Call the geolocation API and capture the output\n'
CONSENT = '''\t# Mangue OS: geolocation only with consent (privacy). Default no.
\tMANGUE_GEO=n
\tif [[ $preset_unattended != 1 && -n "$PUBLIC_IP" ]]; then
\t\techo ""
\t\techo "Detect your timezone automatically? This sends your public IP address"
\t\techo "to ipinfo.io and ipwhois.app. Answer n to pick the timezone manually."
\t\tread -r -p "Detect timezone from your IP? [y/N] " MANGUE_GEO
\t\t[[ $MANGUE_GEO =~ ^(Y|y)$ ]] && MANGUE_GEO=y || MANGUE_GEO=n
\tfi

'''


def need(cond, msg):
    if not cond:
        sys.exit(f"firstlogin-privacy: {msg} in {path}")


need(s.count(PROBE_OLD) == 3, f"expected 3 ipinfo probes, found {s.count(PROBE_OLD)}")
need(s.count(GEO_OLD) == 1, "ipwhois call not found")
need(s.count(ANCHOR) == 1, "geolocation anchor not found")

s = s.replace(PROBE_OLD, PROBE_NEW).replace(GEO_OLD, GEO_NEW).replace(ANCHOR, CONSENT + ANCHOR)

# Every remaining third-party call must sit behind the consent flag.
for line in s.splitlines():
    if re.search(r'curl[^\n]*(ipinfo\.io|ipwhois\.app)', line):
        need('$MANGUE_GEO == y' in line, f"unguarded call left: {line.strip()}")

open(path, 'w').write(s)
subprocess.run(['bash', '-n', path], check=True)
print(f"firstlogin-privacy: patched {path}")
