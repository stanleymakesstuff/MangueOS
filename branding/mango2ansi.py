#!/usr/bin/env python3
"""Convert the mango artwork PNG into terminal ASCII art with xterm-256 colours.

Usage: mango2ansi.py SOURCE.png ROWS OUT_PREFIX
Writes OUT_PREFIX.ans (ANSI colour), OUT_PREFIX.txt (plain), OUT_PREFIX.png (render preview).
"""
import sys
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont

RAMP = " .:-=+*#%@"       # sparse -> dense
CELL_ASPECT = 2.0          # terminal cells are ~2x taller than wide
BLUR = float(__import__("os").environ.get("BLUR", 0.5))  # blur radius as fraction of cell size
BRIGHT = 40                # pixel counts as "ink" above this max-channel value
MIN_COVER = float(__import__("os").environ.get("COVER", 0.10))  # blurred ink density below this -> empty cell


def xterm256(rgb):
    """Nearest colour in the 6x6x6 xterm cube (indices 16-231)."""
    levels = np.array([0, 95, 135, 175, 215, 255])
    idx = [int(np.abs(levels - c).argmin()) for c in rgb]
    return 16 + 36 * idx[0] + 6 * idx[1] + idx[2]


def main(src, rows, prefix):
    img = Image.open(src).convert("RGB")
    a = np.asarray(img).astype(float)
    ink = a.max(axis=2) > BRIGHT
    ys, xs = np.nonzero(ink)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    a, ink = a[y0:y1, x0:x1], ink[y0:y1, x0:x1]
    h, w = ink.shape

    cols = round(rows * (w / h) * CELL_ASPECT)
    ch, cw = h / rows, w / cols

    # Blur ink mask so the gaps between the source glyphs become a density field.
    dens = np.asarray(Image.fromarray((ink * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(min(ch, cw) * BLUR))) / 255.0
    lum = a.max(axis=2)

    plain, ansi, colours = [], [], []
    for r in range(rows):
        pl, an, last = "", "", None
        crow = []
        for c in range(cols):
            ya, yb = int(r * ch), int((r + 1) * ch)
            xa, xb = int(c * cw), int((c + 1) * cw)
            d = dens[ya:yb, xa:xb].mean()
            m = ink[ya:yb, xa:xb]
            if d < MIN_COVER or not m.any():
                pl += " "; an += " "; crow.append(None)
                continue
            rgb = a[ya:yb, xa:xb][m].mean(axis=0)
            rgb = rgb / max(rgb.max(), 1) * 255      # normalise: keep hue, full brightness
            bright = lum[ya:yb, xa:xb][m].mean() / 255
            k = min(len(RAMP) - 1, max(1, round((0.55 * d / 0.6 + 0.45 * bright) * (len(RAMP) - 1))))
            char = RAMP[k]
            code = xterm256(rgb)
            pl += char
            an += (f"\x1b[38;5;{code}m" if code != last else "") + char
            last = code
            crow.append((char, rgb))
        plain.append(pl.rstrip())
        ansi.append(an.rstrip() + "\x1b[0m")
        colours.append(crow)

    # Trim empty rows top/bottom.
    while plain and not plain[0].strip():
        plain.pop(0); ansi.pop(0); colours.pop(0)
    while plain and not plain[-1].strip():
        plain.pop(); ansi.pop(); colours.pop()

    open(prefix + ".txt", "w").write("\n".join(plain) + "\n")
    open(prefix + ".ans", "w").write("\n".join(ansi) + "\n")

    # Render a preview PNG so the result can be eyeballed without a terminal.
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    fw, fh = 10, 20
    out = Image.new("RGB", (cols * fw + 20, len(colours) * fh + 20), "black")
    dr = ImageDraw.Draw(out)
    for r, crow in enumerate(colours):
        for c, cell in enumerate(crow):
            if cell:
                dr.text((10 + c * fw, 10 + r * fh), cell[0], font=font,
                        fill=tuple(int(v) for v in cell[1]))
    out.save(prefix + ".png")
    print(f"{rows} rows -> {cols} cols, {len(plain)} rows after trim")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
