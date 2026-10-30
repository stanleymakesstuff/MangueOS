#!/usr/bin/env python3
"""Colour the figlet wordmark with the mango logo's palette (xterm-256).

Usage: wordmark2ansi.py WORDMARK.txt LOGO.ans OUT_PREFIX
Writes OUT_PREFIX.ans (gradient), OUT_PREFIX_white.ans (bold white),
OUT_PREFIX_preview.png (both variants above the logo, rendered like a terminal).
"""
import re
import sys
from PIL import Image, ImageDraw, ImageFont

# Mango body colours as they appear in logo_motd.ans: yellow -> orange -> red-orange.
STOPS = [226, 220, 214, 208, 202]
SLANT = 0.25    # how much the row adds to the gradient position (diagonal like the logo's light)
LEVELS = [0, 95, 135, 175, 215, 255]


def xterm_rgb(n):
    n -= 16
    return (LEVELS[n // 36], LEVELS[n // 6 % 6], LEVELS[n % 6])


def gradient(lines):
    w = max(len(l) for l in lines)
    h = len(lines)
    out, cells = [], []
    for y, line in enumerate(lines):
        an, last, crow = "", None, []
        for x, ch in enumerate(line):
            if ch == " ":
                an += " "; crow.append(None)
                continue
            t = (x / max(w - 1, 1)) * (1 - SLANT) + (y / max(h - 1, 1)) * SLANT
            code = STOPS[min(len(STOPS) - 1, int(t * len(STOPS)))]
            an += (f"\x1b[38;5;{code}m" if code != last else "") + ch
            last = code
            crow.append((ch, xterm_rgb(code)))
        out.append(an.rstrip() + "\x1b[0m")
        cells.append(crow)
    return out, cells


def parse_ans(text):
    """Turn an .ans file (38;5;N and 0 SGR codes only) into rows of (char, rgb) cells."""
    rows = []
    for line in text.splitlines():
        crow, colour = [], (255, 255, 255)
        for tok in re.split(r"(\x1b\[[0-9;]*m)", line):
            m = re.fullmatch(r"\x1b\[38;5;(\d+)m", tok)
            if m:
                colour = xterm_rgb(int(m.group(1)))
            elif tok.startswith("\x1b["):
                colour = (255, 255, 255)
            else:
                crow += [(c, colour) if c != " " else None for c in tok]
        rows.append(crow)
    return rows


def render(blocks, path):
    font = ImageFont.truetype("DejaVuSansMono.ttf", 16)
    fw, fh = 10, 20
    rows = [r for b in blocks for r in b]
    cols = max(len(r) for r in rows)
    img = Image.new("RGB", (cols * fw + 20, len(rows) * fh + 20), (12, 12, 12))
    dr = ImageDraw.Draw(img)
    for y, crow in enumerate(rows):
        for x, cell in enumerate(crow):
            if cell:
                dr.text((10 + x * fw, 10 + y * fh), cell[0], font=font, fill=cell[1])
    img.save(path)


def main(src, logo, prefix):
    lines = open(src).read().rstrip("\n").split("\n")
    ans, cells = gradient(lines)
    open(prefix + ".ans", "w").write("\n".join(ans) + "\n")
    white = ["\x1b[1;97m" + l.rstrip() + "\x1b[0m" for l in lines]
    open(prefix + "_white.ans", "w").write("\n".join(white) + "\n")

    logo_rows = parse_ans(open(logo).read())
    white_cells = [[(c, (255, 255, 255)) if c != " " else None for c in l] for l in lines]
    label = lambda s: [[(c, (150, 150, 150)) if c != " " else None for c in s]]
    render([label("A) logo palette gradient"), cells, [[]], logo_rows[:6], [[]],
            label("B) white"), white_cells, [[]], logo_rows[:6]],
           prefix + "_preview.png")


if __name__ == "__main__":
    main(*sys.argv[1:4])
