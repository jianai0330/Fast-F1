"""
Generate F1 mini-program tab bar icons.
All icons: 54x54px, stroke 2.5px, F1 red (#e10600) / gray (#999999)
"""

import os
from PIL import Image, ImageDraw

SIZE = 54
GRAY = '#999999'
F1_RED = '#e10600'
WHITE = '#ffffff'
OUT = os.path.join(os.path.dirname(__file__), 'miniprogram', 'assets', 'icons')


def new_icon() -> ImageDraw:
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def save(name: str, img: Image):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, f'{name}.png'))


def circle(d: ImageDraw, cx, cy, r, fill=None, outline=None, width=1):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=width)


def line(d: ImageDraw, x1, y1, x2, y2, fill, width=2):
    d.line([x1, y1, x2, y2], fill=fill, width=width)


def rect(d: ImageDraw, x1, y1, x2, y2, fill=None, outline=None, width=1, rx=0):
    d.rounded_rectangle([x1, y1, x2, y2], radius=rx, fill=fill, outline=outline, width=width)


def rounded_rect(d: ImageDraw, x1, y1, x2, y2, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)


# ── 1. Calendar with checkmark ────────────────────────────

def draw_calendar(sel: bool):
    img, d = new_icon()
    s = F1_RED if sel else None
    t = WHITE if sel else GRAY

    # body
    rounded_rect(d, 9, 12, 45, 46, 4, fill=s, outline=GRAY, width=3)
    # top bar
    fb = F1_RED if sel else GRAY
    rounded_rect(d, 9, 18, 45, 25, 1, fill=fb)
    # rings
    circle(d, 17, 11, 2, fill=GRAY)
    circle(d, 37, 11, 2, fill=GRAY)
    # lines
    line(d, 16, 29, 38, 29, t, width=2)
    line(d, 16, 35, 32, 35, t, width=2)
    # checkmark
    d.line([30, 37, 34, 41, 42, 31], fill=F1_RED if not sel else WHITE, width=3)
    return img


# ── 2. Podium / Trophy ────────────────────────────────────

def draw_standings(sel: bool):
    img, d = new_icon()
    t = WHITE if sel else GRAY
    f = F1_RED if sel else None

    # cup
    d.arc([17.5, 14, 36.5, 29], 190, 350, fill=GRAY, width=3)
    d.line([18, 21, 18, 26], fill=GRAY, width=3)
    d.line([36, 21, 36, 26], fill=GRAY, width=3)
    # cup fill
    if sel:
        # draw cup body explicitly for fill
        d.polygon([(18, 21), (18, 26), (21, 29), (33, 29), (36, 26), (36, 21)], fill=F1_RED)
        d.polygon([(19, 20), (18, 21), (36, 21), (35, 20)], fill=F1_RED)
    else:
        d.polygon([(18, 21), (18, 26), (21, 29), (33, 29), (36, 26), (36, 21)], outline=GRAY, width=2)
        d.polygon([(19, 20), (18, 21), (36, 21), (35, 20)], outline=GRAY, width=2)
    # handles
    d.arc([9, 16, 18, 22], 70, 180, fill=GRAY, width=3)  # left handle
    d.arc([36, 16, 45, 22], 0, 110, fill=GRAY, width=3)   # right handle
    # star
    cx = 27
    # draw star manually
    d.text((cx - 5, 21), "★", fill=t, font_size=14)
    # stem
    rounded_rect(d, 24, 30, 30, 38, 2, fill=f or GRAY)
    # base
    rounded_rect(d, 16, 38, 38, 43, 2, fill=f or GRAY)
    return img


# ── 3. Open book with A-Z ─────────────────────────────────

def draw_glossary(sel: bool):
    img, d = new_icon()
    t = WHITE if sel else GRAY
    f = F1_RED if sel else None

    # left page
    d.polygon([(27, 14), (12, 12), (12, 40), (27, 42)], fill=f, outline=GRAY, width=3)
    # right page
    d.polygon([(27, 14), (42, 12), (42, 40), (27, 42)], fill=f, outline=GRAY, width=3)
    # spine
    d.line([27, 14, 27, 42], fill=GRAY, width=2)
    # A / Z
    d.text((13, 22), "A", fill=t, font_size=12)
    d.text((37, 22), "Z", fill=t, font_size=12)
    return img


# ── 4. Newspaper ──────────────────────────────────────────

def draw_news(sel: bool):
    img, d = new_icon()
    t = WHITE if sel else GRAY
    f = F1_RED if sel else None

    # body
    rounded_rect(d, 8, 10, 38, 44, 3, fill=f, outline=GRAY, width=3)
    # folded corner
    d.polygon([(38, 10), (38, 18), (30, 18)], fill=None, outline=GRAY, width=3)
    # headline
    rounded_rect(d, 12, 14, 30, 17, 1.5, fill=t)
    # lines
    line(d, 12, 20, 34, 20, t, width=2)
    line(d, 12, 24, 30, 24, t, width=2)
    # divider
    line(d, 12, 28, 34, 28, GRAY, width=1)
    # small text
    line(d, 12, 31, 26, 31, t, width=2)
    line(d, 12, 35, 28, 35, t, width=2)
    line(d, 12, 39, 22, 39, t, width=2)
    return img


# ── 5. Chat bubble ────────────────────────────────────────

def draw_forum(sel: bool):
    img, d = new_icon()
    t = WHITE if sel else GRAY
    f = F1_RED if sel else None

    # bubble - use polygon for custom shape
    # Main body rect with tail pointing down-left
    rounded_rect(d, 10, 14, 44, 34, 4, fill=f, outline=GRAY, width=3)
    # tail
    d.polygon([(24, 34), (16, 42), (20, 34)], fill=f, outline=GRAY, width=3)
    # dots
    circle(d, 20, 24, 2.5, fill=t)
    circle(d, 27, 24, 2.5, fill=t)
    circle(d, 34, 24, 2.5, fill=t)
    return img


# ── Generate all ──────────────────────────────────────────

icons = [
    ('calendar', draw_calendar),
    ('standings', draw_standings),
    ('glossary', draw_glossary),
    ('news', draw_news),
    ('forum', draw_forum),
]

for name, fn in icons:
    save(name, fn(sel=False))
    save(f'{name}_selected', fn(sel=True))
    print(f'  ✓ {name}.png + {name}_selected.png')

print(f'\nDone! All icons saved to {OUT}')
