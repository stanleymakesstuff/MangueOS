#!/usr/bin/env python3
"""Render terminal output with ANSI colours (SGR 0/1/2/22/39 and 38;5;N) to a PNG.

Usage: ansi2png.py IN.ans OUT.png [--title TEXT]
Used for README/social screenshots of the login banner captured from the board:
    ssh mangopi@<board> 'TERM=xterm-256color bash /etc/update-motd.d/10-mangue-header' > banner.ans
"""
import re
import sys
from PIL import Image, ImageDraw, ImageFont

BG = (18, 18, 18)
FG = (204, 204, 204)
FG_BOLD = (255, 255, 255)
LEVELS = [0, 95, 135, 175, 215, 255]
BASE16 = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238), (205, 0, 205),
          (0, 205, 205), (229, 229, 229), (127, 127, 127), (255, 0, 0), (0, 255, 0),
          (255, 255, 0), (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
CW, CH, PAD, BAR = 10, 20, 24, 34


def xterm(n):
    if n < 16:
        return BASE16[n]
    if n < 232:
        n -= 16
        return (LEVELS[n // 36], LEVELS[n // 6 % 6], LEVELS[n % 6])
    g = 8 + 10 * (n - 232)
    return (g, g, g)


def parse(text):
    """-> list of rows, each a list of (char, rgb, bold)."""
    rows = []
    fg, bold, dim = None, False, False
    for line in text.replace("\r", "").split("\n"):
        row = []
        for tok in re.split(r"(\x1b\[[0-9;]*m)", line):
            m = re.fullmatch(r"\x1b\[([0-9;]*)m", tok)
            if not m:
                for ch in tok:
                    rgb = fg or (FG_BOLD if bold else FG)
                    if dim:
                        rgb = tuple(int(c * 0.55) for c in rgb)
                    row.append((ch, rgb, bold))
                continue
            codes = [int(c) if c else 0 for c in m.group(1).split(";")]
            i = 0
            while i < len(codes):
                c = codes[i]
                if c == 0:
                    fg, bold, dim = None, False, False
                elif c == 1:
                    bold = True
                elif c == 2:
                    dim = True
                elif c == 22:
                    bold = dim = False
                elif c == 39:
                    fg = None
                elif c == 38 and i + 2 < len(codes) and codes[i + 1] == 5:
                    fg = xterm(codes[i + 2])
                    i += 2
                i += 1
        rows.append(row)
    while rows and not rows[-1]:
        rows.pop()
    return rows


def main():
    src, out = sys.argv[1], sys.argv[2]
    title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else None
    rows = parse(open(src, encoding="utf-8", errors="replace").read())
    font = ImageFont.truetype("DejaVuSansMono.ttf", 16)
    bold_font = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 16)
    cols = max(len(r) for r in rows)
    top = PAD + (BAR if title else 0)
    img = Image.new("RGB", (cols * CW + 2 * PAD, len(rows) * CH + top + PAD), BG)
    d = ImageDraw.Draw(img)
    if title:  # minimal window title bar
        d.rectangle([0, 0, img.width, BAR - 1], fill=(40, 40, 40))
        for k, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([14 + k * 20, 11, 26 + k * 20, 23], fill=col)
        d.text((img.width // 2, BAR // 2), title, font=font, fill=(170, 170, 170), anchor="mm")
    for y, row in enumerate(rows):
        for x, (ch, rgb, b) in enumerate(row):
            if ch != " ":
                d.text((PAD + x * CW, top + y * CH), ch, font=bold_font if b else font, fill=rgb)
    img.save(out)
    print(f"{out}: {img.width}x{img.height}, {len(rows)} rows x {cols} cols")


if __name__ == "__main__":
    main()
