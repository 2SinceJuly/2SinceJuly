#!/usr/bin/env python3
"""Generate assets/banner.svg: an animated 4px pixel-art landscape.

Construction mirrors the technique used by the reference banner:
  * everything is drawn on a 4px grid and emitted as merged <rect> runs
  * the village is a reusable <g id="village">, mirrored below the waterline
    with <use transform="scale(1 -1)"> to make the reflection
  * drifting clouds, a bobbing boat, birds and water ripples move via CSS
    @keyframes transforms, which stay smooth inside GitHub's sanitised SVG

Run from the repo root:  python3 tools/banner.py
"""

import random
from pathlib import Path

W, H = 1200, 600
PX = 4
GW, GH = W // PX, H // PX          # 300 x 150 cells

WATER = 452
WATER_CELL = WATER // PX

INK = "#181818"
PAPER = "#fcfcfc"

C_FAR, C_FAR2 = "#eeeeee", "#e0e0e0"
C_MID, C_MID2 = "#c4c4c4", "#b0b0b0"
C_NEAR, C_NEAR2 = "#999999", "#737373"
C_VILLAGE, C_ROOF = "#f8f8f8", "#2b2b2b"

GLYPHS = {
    " ": ["....."] * 7,
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "i": ["#..", "...", "#..", "#..", "#..", "#..", "##."],
    ",": ["..", "..", "..", "..", "..", ".#", "#."],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "'": [".#.", ".#.", "#..", "...", "...", "...", "..."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"],
    "2": [".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "c": [".....", ".....", ".###.", "#....", "#....", "#....", ".###."],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "u": [".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"],
    "l": ["##...", ".#...", ".#...", ".#...", ".#...", ".#...", ".##.."],
    "y": [".....", ".....", "#...#", "#...#", ".####", "....#", ".###."],
}


class Grid:
    def __init__(self, w=GW, h=GH):
        self.w, self.h = w, h
        self.cells = {}

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cells[(x, y)] = color

    def box(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, color)

    def rows(self):
        for y in range(self.h):
            xs = sorted(x for (x, yy) in self.cells if yy == y)
            if not xs:
                continue
            start = prev = xs[0]
            color = self.cells[(start, y)]
            for x in xs[1:]:
                c = self.cells[(x, y)]
                if c != color or x != prev + 1:
                    yield start, y, prev - start + 1, color
                    start, color = x, c
                prev = x
            yield start, y, prev - start + 1, color

    def rects(self):
        return "".join(
            f'<rect x="{x * PX}" y="{y * PX}" width="{w * PX}" height="{PX}" fill="{c}"/>'
            for x, y, w, c in self.rows()
        )


def peaks(rng, n, count, wmin, wmax, lo, hi):
    prof = [int(lo * 0.6)] * n
    for _ in range(count):
        cx = rng.randint(-wmax, n + wmax)
        w = rng.randint(wmin, wmax)
        h = rng.randint(lo, hi)
        for x in range(max(0, cx - w), min(n, cx + w + 1)):
            v = int(round(h * (1 - abs(x - cx) / w)))
            if v > prof[x]:
                prof[x] = v
    for x in range(n):
        prof[x] += rng.choice((-1, 0, 0, 1))
    return prof


def ridge(g, rng, crest_px, height_px, color, count, wmin, wmax, stop=None):
    stop = stop or WATER_CELL
    prof = peaks(rng, GW, count, wmin, wmax, height_px // PX // 2, height_px // PX)
    lo, hi = min(prof), max(prof)
    span = max(1, hi - lo)
    crest = crest_px // PX
    max_h = max(1, stop - crest)
    tops = [stop - int(round(max_h * (0.5 + 0.5 * (p - lo) / span))) for p in prof]
    for x, top in enumerate(tops):
        for y in range(top, stop):
            g.px(x, y, color)
    return tops


def house(g, x, base_y, w, h, roof_h):
    top = base_y - h
    g.box(x, top, w, h, C_VILLAGE)
    for i in range(roof_h):
        inset = (w // 2) * i // max(1, roof_h)
        run = max(2, w - 2 * inset)
        g.box(x + inset - 1, top - 1 - i, run + 2, 1, C_ROOF)
    for side in (0, 1):
        for s in range(2):
            gx = x - 1 - s if side == 0 else x + w + s
            g.box(gx, top - 2 - s * 2, 1, 2, C_ROOF)
    for wy in (top + 3, top + 3 + max(3, h // 3)):
        if wy + 2 < base_y - 4:
            g.box(x + 1, wy, 1, 2, "#4a4a4a")
            g.box(x + w - 2, wy, 1, 2, "#4a4a4a")
    dw = 2 if w >= 8 else 1
    g.box(x + (w - dw) // 2, base_y - 4, dw, 4, "#4a4a4a")


def village(g, x0, base_y):
    widths = [9, 12, 10, 14, 11, 8, 12, 9, 11]
    heights = [11, 17, 13, 20, 15, 10, 16, 12, 14]
    roofs = [3, 4, 3, 5, 4, 3, 4, 3, 4]
    rng = random.Random(7)
    cx = x0
    for w, h, r in zip(widths, heights, roofs):
        house(g, cx, base_y, w, h, r)
        cx += w + rng.choice((1, 1, 2, 2, 3))
    return cx


def pine(g, x, base_y, tiers, color):
    """A soft conifer: narrowing bands, no hard ladder rungs."""
    g.box(x, base_y - 2, 1, 2, "#4a4a4a")
    total = tiers + 2
    for i in range(total):
        half = max(0, int(round((total - i) * 0.34)))
        g.box(x - half, base_y - 2 - total + i, half * 2 + 1, 1, color)


def bridge(g, x, base_y, span):
    """Stone bridge: gentle hump, thin deck, piers with open arches."""
    deck = base_y - 3
    for i in range(span):
        t = i / max(1, span - 1)
        lift = int(round(2 * (1 - (2 * t - 1) ** 2)))
        g.px(x + i, deck - lift, "#5c5c5c")
        g.px(x + i, deck - lift + 1, "#4a4a4a")
    for frac in (0.34, 0.67):
        px = x + int(span * frac)
        g.box(px, deck + 1, 1, 2, "#5c5c5c")
    g.box(x, base_y - 1, span, 1, "#8a8a8a")


def title(g, text, x, y):
    cx = x
    for ch in text:
        glyph = GLYPHS[ch]
        for row, line in enumerate(glyph):
            for col, bit in enumerate(line):
                if bit == "#":
                    g.px(cx + col, y + row, INK)
        cx += len(glyph[0]) + 1


def scene():
    rng = random.Random(2026)

    far = Grid()
    ridge(far, rng, 236, 208, C_FAR, 10, 22, 58)
    ridge(far, rng, 276, 176, C_FAR2, 11, 20, 52)

    mid = Grid()
    ridge(mid, rng, 312, 148, C_MID, 12, 18, 46)
    ridge(mid, rng, 346, 122, C_MID2, 12, 16, 42)

    near = Grid()
    tops1 = ridge(near, rng, 380, 98, C_NEAR, 12, 14, 36)
    ridge(near, rng, 410, 78, C_NEAR2, 11, 12, 32)
    # flecks of forest on the near slope, like the reference's texture
    trng = random.Random(303)
    for x, top in enumerate(tops1):
        for k in range(1, 10):
            if trng.random() < 0.30:
                near.px(x, top + k, C_NEAR2)

    trees = Grid()
    trng = random.Random(99)
    base_t = WATER_CELL - 1
    for x in range(0, GW):
        if trng.random() < 0.30:
            continue
        h = trng.randint(4, 10)
        col = trng.choice(("#9c9c9c", "#8e8e8e", "#828282"))
        for i in range(h):
            half = max(0, int(round((h - i) * 0.34))) if i > 1 else 0
            trees.box(x - half, base_t - i, half * 2 + 1, 1, col)

    vill = Grid()
    base = WATER_CELL - 1
    end_x = village(vill, 74, base)
    for x, t, c in ((28, 3, "#5c5c5c"), (35, 2, "#6f6f6f"),
                    (end_x + 4, 3, "#5c5c5c"), (end_x + 11, 2, "#6f6f6f"),
                    (end_x + 18, 3, "#5c5c5c"), (end_x + 26, 2, "#6f6f6f")):
        pine(vill, x, base, t, c)
    bridge(vill, 26, base, 34)

    water = Grid()
    water.box(0, WATER_CELL, GW, GH - WATER_CELL, "#f0f0f0")

    shore = Grid()
    shore.box(0, WATER_CELL - 1, GW, 1, "#8a8a8a")

    return far, mid, near, trees, vill, water, shore


def clouds():
    rng = random.Random(4242)
    out = []
    for cls, x0, y0 in (("cloud", 30, 22), ("cloud2", 175, 24)):
        g = Grid()
        for _ in range(5):
            cx = x0 + rng.randint(-8, 18)
            cy = y0 + rng.randint(-4, 4)
            w = rng.randint(4, 8)
            for dy, ww in ((0, w), (1, w + rng.randint(1, 3)), (2, w - rng.randint(1, 2))):
                if ww > 0:
                    g.box(cx, cy + dy, ww, 1, PAPER)
        out.append(f'<g class="{cls}">{g.rects()}</g>')
    return "".join(out)


def birds():
    g = Grid()
    for ox, oy in ((186, 55), (196, 50), (204, 58)):
        for r, line in enumerate(("#...#", ".#.#.", "..#..")):
            for c, ch in enumerate(line):
                if ch == "#":
                    g.px(ox + c, oy + r, "#444444")
    return g.rects()


def boat():
    g = Grid()
    g.box(243, 124, 5, 1, "#3c3c3c")
    g.box(244, 123, 3, 1, "#3c3c3c")
    g.box(247, 119, 1, 4, "#5c5c5c")
    g.box(245, 121, 1, 2, "#5c5c5c")
    return g.rects()


def ripples(seed, y0, y1, count, colors=("#e4e4e4", "#d8d8d8")):
    rng = random.Random(seed)
    g = Grid()
    for _ in range(count):
        x = rng.randint(2, GW - 8)
        y = rng.randint(y0, y1)
        g.box(x, y, rng.randint(2, 7), 1, rng.choice(colors))
    return g.rects()


def build():
    far, mid, near, trees, vill, water, shore = scene()
    vill_rects = vill.rects()
    mirror_y = WATER_CELL * 2 * PX

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">Hi, I'm 2SinceJuly</title>
<desc id="desc">Animated monochrome pixel-art landscape of a Wannan village: layered mountain ridges, white-walled houses, pines and a stone bridge on still water, with drifting clouds, birds, a bobbing boat and rippling reflections.</desc>
<style>
text{{font-family:'Courier New',Courier,monospace;fill:{INK}}}
.cloud{{animation:cloud 24s ease-in-out infinite alternate}}
.cloud2{{animation:cloud 31s ease-in-out -11s infinite alternate-reverse}}
.birds{{animation:birds 20s ease-in-out infinite}}
.boat{{animation:boat 14s ease-in-out infinite}}
.ripple{{animation:ripple 8s ease-in-out infinite}}
.ripple2{{animation:ripple 11s ease-in-out -4s infinite reverse}}
@keyframes cloud{{from{{transform:translateX(-12px);opacity:.45}}to{{transform:translateX(18px);opacity:.8}}}}
@keyframes birds{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(30px,-7px)}}}}
@keyframes boat{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(-18px,2px)}}}}
@keyframes ripple{{0%,100%{{transform:translateX(-8px);opacity:.2}}50%{{transform:translateX(8px);opacity:.65}}}}
@media(prefers-reduced-motion:reduce){{.cloud,.cloud2,.birds,.boat,.ripple,.ripple2{{animation:none!important}}}}
</style>
<defs>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="8"/></clipPath>
<clipPath id="reflection"><rect x="0" y="{WATER}" width="{W}" height="76"/></clipPath>
<g id="village">{vill_rects}</g>
</defs>

<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="{PAPER}"/>

<g shape-rendering="crispEdges">
{far.rects()}
{clouds()}
</g>

<g shape-rendering="crispEdges">
{mid.rects()}
{near.rects()}
{trees.rects()}
</g>

<g shape-rendering="crispEdges">{vill_rects}</g>
<g clip-path="url(#reflection)" opacity=".18">
  <use href="#village" transform="translate(0 {mirror_y + 8}) scale(1 -1)"/>
</g>

<g shape-rendering="crispEdges">
{water.rects()}
{shore.rects()}
<g class="ripple">{ripples(11, WATER_CELL + 4, GH - 4, 26)}</g>
<g class="ripple2">{ripples(12, WATER_CELL + 8, GH - 2, 24)}</g>
<g class="boat">{boat()}</g>
</g>

<g class="birds" shape-rendering="crispEdges">{birds()}</g>

<g shape-rendering="crispEdges">{title_svg()}</g>
<text x="49" y="150" font-size="18">A student building AI agent workflows,</text>
<text x="49" y="176" font-size="18">and contributing to open source.</text>

<rect x="1090" y="44" width="60" height="64" fill="none" stroke="#333333"/>
<text x="1120" y="71" font-size="21" text-anchor="middle">山</text>
<text x="1120" y="97" font-size="21" text-anchor="middle">水</text>
<text x="48" y="581" font-size="10" letter-spacing="1">山水之间</text>
<text x="1152" y="581" font-size="10" text-anchor="end" letter-spacing="1">BUILD / WANDER / REPEAT</text>
</g>
</svg>
'''


def title_svg():
    g = Grid()
    title(g, "Hi, I'm 2SinceJuly", 12, 13)
    return g.rects()


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets" / "banner.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build())
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
