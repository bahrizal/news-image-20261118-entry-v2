"""Draw one image summing up the world's news of Wednesday 18 November 2026.

The program renders a 1024x1024 newspaper-style front page with six verified
stories from that day and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(or /output/entry.png when the variable is not set).

It uses only the Python standard library (os, struct, zlib), reads nothing
from disk, reaches no network, runs no subprocess, and is fully
deterministic: the same input always produces the same bytes.

Stories (each verified against reporting from 18 November 2026):
  1. Gulf war flares: US jets strike an Iranian missile site on Qeshm
     Island; Iran hits back at bases in Kuwait and Bahrain.
  2. Xi Jinping and Vladimir Putin meet in Shenzhen ahead of a trilateral
     summit with Donald Trump at the APEC meeting.
  3. Democrat Mary Peltola wins Alaska's Senate race; Democrats take a
     56-44 Senate majority.
  4. NASA's Voyager 1 reaches one light-day from Earth, about 16 billion
     miles out, the farthest any human-made object has travelled.
  5. Cyclone Akvan brings mass evacuations to Odisha, India.
  6. Grand Theft Auto VI begins its midnight rollout around the world.
"""

import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

# Palette.
NAVY = (14, 27, 46)        # page background
PANEL = (22, 40, 63)       # story panel background
INK = (245, 241, 230)      # main text, warm white
MUTED = (184, 196, 208)    # secondary text
GOLD = (201, 162, 39)      # header rule and date
WHITE = (255, 255, 255)

# One accent colour per story.
ACCENTS = [
    (228, 87, 46),    # Gulf: burnt orange
    (201, 162, 39),   # Summit: gold
    (46, 134, 171),   # Senate: steel blue
    (123, 94, 167),   # Voyager: violet
    (42, 157, 143),   # Cyclone: teal
    (247, 37, 133),   # GTA 6: neon pink
]

# 5x7 bitmap font. Each glyph is seven rows of five pixels, '#' on, '.' off.
# Only the characters the page actually uses are defined.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
}


# ---------------------------------------------------------------------------
# A tiny RGB framebuffer and drawing helpers. Everything is plain arithmetic
# on a bytearray; there is no image library involved.
# ---------------------------------------------------------------------------

def new_canvas(width, height, color):
    """A width*height RGB framebuffer filled with one colour."""
    buf = bytearray(width * height * 3)
    r, g, b = color
    for i in range(0, len(buf), 3):
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b
    return buf


def set_pixel(buf, width, x, y, color):
    if 0 <= x < width and 0 <= y < HEIGHT:
        i = (y * width + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = color


def fill_rect(buf, width, x, y, w, h, color):
    for yy in range(y, y + h):
        if 0 <= yy < HEIGHT:
            for xx in range(x, x + w):
                if 0 <= xx < width:
                    i = (yy * width + xx) * 3
                    buf[i], buf[i + 1], buf[i + 2] = color


def draw_line(buf, width, x0, y0, x1, y1, color, thick=1):
    """Bresenham line, optionally thickened by drawing parallel lines."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for t in range(thick):
            set_pixel(buf, width, x0 + t, y0, color)
            set_pixel(buf, width, x0, y0 + t, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def fill_circle(buf, width, cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        dx = int((r * r - (yy - cy) * (yy - cy)) ** 0.5) if abs(yy - cy) <= r else 0
        for xx in range(cx - dx, cx + dx + 1):
            set_pixel(buf, width, xx, yy, color)


def circle_outline(buf, width, cx, cy, r, color, thick=2):
    for yy in range(cy - r - thick, cy + r + thick + 1):
        for xx in range(cx - r - thick, cx + r + thick + 1):
            d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
            if r - thick < d <= r:
                set_pixel(buf, width, xx, yy, color)


def fill_triangle(buf, width, x0, y0, x1, y1, x2, y2, color):
    """Filled triangle by horizontal scanlines."""
    top = min(y0, y1, y2)
    bottom = max(y0, y1, y2)
    for yy in range(top, bottom + 1):
        xs = []
        for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x0, y0)):
            if ay == by:
                continue
            if min(ay, by) <= yy < max(ay, by):
                xs.append(ax + (yy - ay) * (bx - ax) / (by - ay))
        if len(xs) >= 2:
            for xx in range(int(min(xs)), int(max(xs)) + 1):
                set_pixel(buf, width, xx, yy, color)


def text_width(text, scale):
    return len(text) * 6 * scale


def draw_text(buf, width, x, y, text, scale, color):
    """Draw text with the 5x7 bitmap font at the given scale."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(buf, width, cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale


# ---------------------------------------------------------------------------
# Minimal PNG writer: signature, IHDR, one IDAT, IEND. Filter 0 on every row.
# ---------------------------------------------------------------------------

def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def png_bytes(buf, width, height):
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Story pictograms. Each draws inside a 122x184 box centred on (cx, cy)
# using only the rectangle / line / circle helpers above.
# ---------------------------------------------------------------------------

def icon_ship(buf, cx, cy, accent):
    draw_line(buf, WIDTH, cx - 8, cy + 8, cx - 8, cy - 52, INK, 3)
    fill_triangle(buf, WIDTH, cx - 8, cy - 52, cx - 8, cy + 4, cx + 34, cy + 4, WHITE)
    fill_rect(buf, WIDTH, cx - 52, cy + 8, 104, 24, accent)
    fill_triangle(buf, WIDTH, cx + 52, cy + 8, cx + 52, cy + 32, cx + 72, cy + 32, accent)
    draw_line(buf, WIDTH, cx - 56, cy + 46, cx + 56, cy + 46, MUTED, 2)
    draw_line(buf, WIDTH, cx - 40, cy + 58, cx + 40, cy + 58, MUTED, 2)
    draw_line(buf, WIDTH, cx - 24, cy + 70, cx + 24, cy + 70, MUTED, 2)


def icon_flags(buf, cx, cy, accent):
    for px, col in ((cx - 44, (228, 87, 46)), (cx, GOLD), (cx + 44, (46, 134, 171))):
        draw_line(buf, WIDTH, px, cy - 56, px, cy + 40, INK, 3)
        fill_rect(buf, WIDTH, px, cy - 56, 30, 18, col)
    draw_line(buf, WIDTH, cx - 60, cy + 40, cx + 60, cy + 40, MUTED, 3)


def icon_ballot(buf, cx, cy, accent):
    draw_line(buf, WIDTH, cx - 30, cy - 22, cx - 12, cy - 2, INK, 4)
    draw_line(buf, WIDTH, cx - 12, cy - 2, cx + 34, cy - 48, INK, 4)
    fill_rect(buf, WIDTH, cx - 46, cy - 6, 92, 66, accent)
    fill_rect(buf, WIDTH, cx - 24, cy + 2, 48, 6, NAVY)


def icon_voyager(buf, cx, cy, accent):
    circle_outline(buf, WIDTH, cx, cy, 42, INK, 3)
    draw_line(buf, WIDTH, cx, cy - 42, cx + 30, cy - 72, INK, 3)
    fill_circle(buf, WIDTH, cx + 30, cy - 72, 5, accent)
    fill_circle(buf, WIDTH, cx, cy, 10, accent)
    for sx, sy in ((cx - 70, cy - 60), (cx + 64, cy + 10), (cx - 60, cy + 50)):
        fill_rect(buf, WIDTH, sx, sy, 4, 4, GOLD)


def icon_cyclone(buf, cx, cy, accent):
    circle_outline(buf, WIDTH, cx, cy, 26, accent, 3)
    circle_outline(buf, WIDTH, cx, cy, 46, accent, 3)
    circle_outline(buf, WIDTH, cx, cy, 64, MUTED, 3)
    fill_circle(buf, WIDTH, cx, cy, 8, WHITE)


def icon_controller(buf, cx, cy, accent):
    fill_rect(buf, WIDTH, cx - 56, cy - 26, 112, 56, accent)
    fill_rect(buf, WIDTH, cx - 40, cy - 10, 10, 20, NAVY)
    fill_rect(buf, WIDTH, cx - 45, cy - 5, 20, 10, NAVY)
    fill_circle(buf, WIDTH, cx + 28, cy - 8, 6, WHITE)
    fill_circle(buf, WIDTH, cx + 42, cy + 6, 6, WHITE)


ICONS = (icon_ship, icon_flags, icon_ballot, icon_voyager, icon_cyclone, icon_controller)

# The six stories: kicker, two headline lines, two sub lines, icon index.
STORIES = [
    ("MIDDLE EAST", ("US-IRAN WAR", "FLARES"),
     ("US STRIKES QESHM ISLAND", "IRAN HITS GULF BASES"), 0),
    ("CHINA", ("SUMMIT IN", "SHENZHEN"),
     ("XI AND PUTIN MEET", "TRUMP JOINS THURSDAY"), 1),
    ("UNITED STATES", ("DEMOCRATS", "TAKE SENATE"),
     ("PELTOLA WINS ALASKA", "56-44 MAJORITY"), 2),
    ("SPACE", ("VOYAGER 1", "MAKES HISTORY"),
     ("ONE LIGHT-DAY FROM EARTH", "16 BILLION MILES OUT"), 3),
    ("WEATHER", ("CYCLONE AKVAN", "HITS INDIA"),
     ("MASS EVACUATIONS", "IN ODISHA"), 4),
    ("CULTURE", ("GTA 6", "LAUNCHES"),
     ("MIDNIGHT ROLLOUT", "BEGINS WORLDWIDE"), 5),
]


def draw_globe(buf, cx, cy, r):
    circle_outline(buf, WIDTH, cx, cy, r, GOLD, 3)
    draw_line(buf, WIDTH, cx, cy - r, cx, cy + r, GOLD, 2)
    draw_line(buf, WIDTH, cx - r, cy, cx + r, cy, GOLD, 2)
    circle_outline(buf, WIDTH, cx, cy, r // 2, GOLD, 2)


def draw_panel(buf, x, y, w, h, story, accent, icon_fn):
    kicker, headline, subs, _ = story
    fill_rect(buf, WIDTH, x, y, w, h, PANEL)
    fill_rect(buf, WIDTH, x, y, w, 10, accent)
    tx = x + 20
    draw_text(buf, WIDTH, tx, y + 64, kicker, 2, accent)
    draw_text(buf, WIDTH, tx, y + 94, headline[0], 3, INK)
    draw_text(buf, WIDTH, tx, y + 119, headline[1], 3, INK)
    draw_text(buf, WIDTH, tx, y + 164, subs[0], 2, MUTED)
    draw_text(buf, WIDTH, tx, y + 186, subs[1], 2, MUTED)
    icon_fn(buf, x + 401, y + 132, accent)


def main():
    buf = new_canvas(WIDTH, HEIGHT, NAVY)

    # Header.
    draw_text(buf, WIDTH, 24, 26, "WORLD NEWS", 7, INK)
    draw_text(buf, WIDTH, 24, 88, "WEDNESDAY 18 NOVEMBER 2026", 3, GOLD)
    draw_globe(buf, 928, 72, 44)
    fill_rect(buf, WIDTH, 24, 132, 976, 4, GOLD)

    # Six story panels, two columns by three rows.
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        x = 24 + col * 494
        y = 152 + row * 276
        draw_panel(buf, x, y, 482, 264, story, ACCENTS[i], ICONS[story[3]])

    # Footer.
    footer = "SIX STORIES FROM 18 NOVEMBER 2026"
    draw_text(buf, WIDTH, (WIDTH - text_width(footer, 2)) // 2, 980,
              footer, 2, MUTED)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png_bytes(buf, WIDTH, HEIGHT))
    print("wrote", path)


if __name__ == "__main__":
    main()
