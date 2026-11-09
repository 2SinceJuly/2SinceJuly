#!/usr/bin/env python3
"""Generate the misty Wannan landscape banner (assets/banner.svg).

All geometry is procedural: value-noise ridgelines painted into SVG paths,
fog bands and soft focus done with Gaussian blur filters, so the result reads
like a monochrome photograph instead of hard pixel art.

Run from the repo root:  python3 tools/banner.py
"""

import random
from pathlib import Path

W, H = 1200, 600

CARD_X0, CARD_Y0, CARD_X1, CARD_Y1 = 28, 26, 1172, 574
WATER_Y = 452
HORIZON_Y = 470


def value_noise(rng, n, octaves=5, roughness=0.5):
    total = [0.0] * n
    amp_sum = 0.0
    amp = 1.0
    wavelength = n / 2.4
    for _ in range(octaves):
        points = max(3, int(n / wavelength) + 2)
        raw = [rng.random() for _ in range(points)]
        step = (points - 1) / (n - 1)
        for i in range(n):
            t = i * step
            i0 = int(t)
            i1 = min(i0 + 1, points - 1)
            f = t - i0
            f = f * f * (3 - 2 * f)
            total[i] += (raw[i0] * (1 - f) + raw[i1] * f) * amp
        amp_sum += amp
        amp *= roughness
        wavelength /= 2.0
    return [v / amp_sum for v in total]


def make_ridge(seed, base_y, height, w=W, lean=0.0):
    """Return [(x, y)] for a mountainside crest."""
    rng = random.Random(seed)
    noise = value_noise(rng, w, octaves=5, roughness=0.52)
    lo, hi = min(noise), max(noise)
    span = max(1e-6, hi - lo)
    pts = []
    for x in range(w):
        v = (noise[x] - lo) / span
        v = v ** 1.05
        y = base_y - height * v + lean * (x / w - 0.5) * height * 0.6
        pts.append((x, round(y, 2)))
    return pts


def ridge_path(pts, bottom=H + 20):
    parts = [f"M0,{bottom}"]
    parts.append(f"L{pts[0][0]},{pts[0][1]}")
    for x, y in pts[1:]:
        parts.append(f"L{x},{y}")
    parts.append(f"L{pts[-1][0]},{bottom}Z")
    return " ".join(parts)


def tree_texture(pts, h, color, opacity, seed, count=900, min_len=0.08, max_len=0.4):
    """Vertical strokes hugging the slope: reads as forest at a distance."""
    nr = random.Random(seed)
    out = []
    for _ in range(count):
        x = nr.randint(0, W - 1)
        top = pts[x][1] + nr.uniform(1.5, 9)
        length = h * nr.uniform(min_len, max_len)
        r = nr.uniform(0.7, 1.9)
        out.append(
            f'<path d="M{x - r:.1f},{top + r:.1f} q{r:.1f},{-r * 1.5:.1f} {r * 2:.1f},0 Z"/>'
        )
    return (
        f'<g fill="{color}" opacity="{opacity}" filter="url(#soft)">' + "".join(out) + "</g>"
    )


def arch_bridge(cx, cy, span, rise, color):
    """Dark stone bridge silhouette with three low arched openings."""
    w = span
    h = 24
    x0, x1 = cx - w / 2 - 18, cx + w / 2 + 18
    body = (
        f"M{x0:.1f},{cy:.1f} "
        f"C{cx - w / 4:.1f},{cy - rise * 2.2:.1f} {cx + w / 4:.1f},{cy - rise * 2.2:.1f} {x1:.1f},{cy:.1f} "
        f"L{x1:.1f},{cy + h:.1f} L{x0:.1f},{cy + h:.1f} Z"
    )
    pier = 10
    gap = (w - 2 * pier) / 3
    arches = []
    for i in range(3):
        ax0 = cx - w / 2 + i * (gap + pier)
        ax1 = ax0 + gap
        rx = gap / 2
        ry = h - 5
        arches.append(
            f'<path d="M{ax0:.1f},{cy + h + 1:.1f} L{ax0:.1f},{cy + h - ry:.1f} '
            f'A{rx:.1f},{ry:.1f} 0 0 1 {ax1:.1f},{cy + h - ry:.1f} '
            f'L{ax1:.1f},{cy + h + 1:.1f} Z" fill="#d9dcdc"/>'
        )
    # pier shadows
    shadows = []
    for i in range(4):
        px = cx - w / 2 + i * gap + max(0, i - 0.5) * pier
        shadows.append(
            f'<rect x="{px - 0.6:.1f}" y="{cy + 6:.1f}" width="1.2" height="{h - 6:.1f}" '
            f'fill="#3f4446" opacity="0.5"/>'
        )
    return f'<path d="{body}" fill="{color}"/>' + "".join(shadows) + "".join(arches)


def tree(cx, base_y, height, color, opacity=0.9):
    w = height * 0.3
    parts = []
    for dx, dy, rx, ry in (
        (0, -0.72, 1.0, 0.36),
        (-0.5, -0.56, 0.78, 0.28),
        (0.52, -0.58, 0.8, 0.29),
        (-0.22, -0.9, 0.68, 0.24),
        (0.24, -0.86, 0.64, 0.23),
        (-0.72, -0.42, 0.5, 0.18),
        (0.74, -0.44, 0.52, 0.19),
    ):
        parts.append(
            f'<ellipse cx="{cx + dx * w:.1f}" cy="{base_y + dy * height:.1f}" '
            f'rx="{rx * w:.1f}" ry="{ry * height:.1f}"/>'
        )
    parts.append(
        f'<rect x="{cx - 0.9:.1f}" y="{base_y - height * 0.5:.1f}" width="1.8" '
        f'height="{height * 0.5:.1f}"/>'
    )
    return (
        f'<g fill="{color}" opacity="{opacity}" filter="url(#treeblur)">'
        + "".join(parts)
        + "</g>"
    )


def house(cx, base_y, w, h, roof_h, wall="#fdfdfd", roof="#3f4143"):
    x = cx - w / 2
    top = base_y - h
    parts = [f'<rect x="{x:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{wall}"/>']
    # gable roof with slightly flared eaves
    parts.append(
        f'<path d="M{x - 2.5:.1f},{top + 0.6:.1f} L{cx:.1f},{top - roof_h:.1f} '
        f'L{x + w + 2.5:.1f},{top + 0.6:.1f} Z" fill="{roof}"/>'
    )
    parts.append(
        f'<rect x="{x - 2.5:.1f}" y="{top + 0.2:.1f}" width="{w + 5:.1f}" height="1.8" fill="{roof}"/>'
    )
    # a dark doorway
    dw = max(2.0, w * 0.18)
    parts.append(
        f'<rect x="{cx - dw / 2:.1f}" y="{base_y - h * 0.42:.1f}" width="{dw:.1f}" '
        f'height="{h * 0.42:.1f}" fill="#55585a" opacity="0.85"/>'
    )
    # window dots
    for k in (-0.28, 0.28):
        parts.append(
            f'<rect x="{cx + w * k - 1:.1f}" y="{top + h * 0.22:.1f}" width="2" height="2.4" fill="#6a6d6f"/>'
        )
    return "".join(parts)


def village(cx, base_y):
    rng = random.Random(31)
    parts = []
    x = cx - 250
    while x < cx + 250:
        w = rng.uniform(20, 42)
        h = rng.uniform(20, 34)
        parts.append(
            house(
                x + w / 2,
                base_y - rng.uniform(0, 6),
                w,
                h,
                rng.uniform(5, 9),
                wall=rng.choice(["#fcfcfc", "#f7f8f8", "#f2f3f3"]),
                roof=rng.choice(["#3f4143", "#4a4d4f", "#565a5c"]),
            )
        )
        x += w + rng.uniform(3, 9)
    return f'<g filter="url(#mid)">' + "".join(parts) + "</g>"


def streaks(seed, y0, y1, count, color, opacity, width_scale=1.0):
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        y = rng.uniform(y0, y1)
        x = rng.uniform(-40, W)
        w = rng.uniform(30, 220) * width_scale
        h = rng.uniform(0.6, 1.6)
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>')
    return (
        f'<g fill="{color}" opacity="{opacity}" filter="url(#soft)">' + "".join(out) + "</g>"
    )


def build():
    layers = []

    # far ridges
    rng_specs = [
        # seed, base_y, height, top fill, bottom fill, blur, lean
        (11, 430, 196, "#e3e5e5", "#fafbfb", 2.6, 0.10),
        (22, 438, 176, "#d6d9d9", "#f6f7f7", 2.0, -0.08),
        (33, 446, 152, "#c3c6c7", "#eef0f0", 1.6, 0.14),
        (44, 452, 128, "#a8acad", "#e1e4e4", 1.3, -0.12),
        (55, 456, 104, "#8b8f91", "#d2d5d6", 1.0, 0.18),
        (66, 460, 82, "#6f7375", "#c0c4c5", 0.8, -0.16),
    ]

    for i, (seed, base_y, height, top, bottom, blur, lean) in enumerate(rng_specs):
        pts = make_ridge(seed, base_y, height, lean=lean)
        layers.append(
            f'<g filter="url(#b{blur})">'
            f'<linearGradient id="g{i}" x1="0" y1="{base_y - height:.0f}" x2="0" y2="{base_y + 20}" '
            f'gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/>'
            f"</linearGradient>"
            f'<path d="{ridge_path(pts, base_y + 24)}" fill="url(#g{i})"/>'
            f"</g>"
        )
        # forest speckle on the nearer ridges
        if i >= 2:
            layers.append(
                tree_texture(pts, height, top, 0.42, seed + 900,
                             count=1500, min_len=0.10, max_len=0.42)
            )
            layers.append(
                tree_texture(pts, height, "#707577", 0.22, seed + 1500,
                             count=900, min_len=0.08, max_len=0.30)
            )
        # fog pooling at the foot of each ridge
        if i < 3:
            layers.append(
                f'<rect x="0" y="{base_y - 30:.0f}" width="{W}" height="44" fill="#fdfefe" '
                f'opacity="{0.5 if i < 2 else 0.34}" filter="url(#fog)"/>'
            )

    # near bank
    bank = make_ridge(77, 462, 34, lean=0.05)
    layers.append(
        f'<linearGradient id="gbank" x1="0" y1="424" x2="0" y2="472" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#7e8284"/><stop offset="1" stop-color="#d8dbdb"/>'
        f"</linearGradient>"
        f'<path d="{ridge_path(bank, HORIZON_Y + 4)}" fill="url(#gbank)"/>'
    )

    layers.append(f'<g filter="url(#mid)" opacity="0.9">{arch_bridge(168, 462, 178, 15, "#5d6264")}</g>')

    # village on the far shore
    layers.append(village(700, HORIZON_Y - 1))

    # trees framing the village
    for cx, h, op in ((470, 74, 0.9), (505, 54, 0.8), (930, 68, 0.85), (968, 46, 0.75), (116, 62, 0.8)):
        layers.append(tree(cx, HORIZON_Y - 1, h, "#6e7274", op))

    # bridge sits on the near bank, in front of the far shore
    layers.append(f'<g filter="url(#mid)" opacity="0.95">{arch_bridge(172, 458, 200, 12, "#4a4f51")}</g>')

    # water
    water = [
        f'<linearGradient id="gw" x1="0" y1="{HORIZON_Y}" x2="0" y2="{CARD_Y1}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#d9dcdc"/><stop offset="0.45" stop-color="#e9ebeb"/>'
        f'<stop offset="1" stop-color="#c9cccc"/></linearGradient>',
        f'<rect x="0" y="{HORIZON_Y}" width="{W}" height="{CARD_Y1 - HORIZON_Y}" fill="url(#gw)"/>',
    ]
    # mirror the shore into the water, softened and faded
    mirror = []
    mirror.append(f'<g opacity="0.30" filter="url(#mirror)" transform="translate(0,{2 * HORIZON_Y}) scale(1,-1)">')
    mirror.append(f'<rect x="0" y="{HORIZON_Y - 46}" width="{W}" height="46" fill="#9aa0a1"/>')
    mirror.append("</g>")
    water.append("".join(mirror))
    water.append(
        f'<rect x="0" y="{HORIZON_Y - 3}" width="{W}" height="7" fill="#c9cdcd" '
        f'opacity="0.55" filter="url(#soft)"/>'
    )
    water.append(streaks(91, HORIZON_Y + 8, CARD_Y1, 120, "#ffffff", 0.42))
    water.append(streaks(92, HORIZON_Y + 14, CARD_Y1, 70, "#a7acad", 0.22, width_scale=0.55))

    # birds
    birds = []
    rng = random.Random(5)
    for bx, by in ((812, 236), (846, 222), (880, 244)):
        birds.append(
            f'<path d="M{bx},{by} q7,-6 14,0 q7,-6 14,0" fill="none" stroke="#4c5052" '
            f'stroke-width="1.6" stroke-linecap="round" opacity="0.75"/>'
        )

    return "\n".join(layers + water + birds)


def svg():
    card_w = CARD_X1 - CARD_X0
    card_h = CARD_Y1 - CARD_Y0
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="ttl dsc">
<title id="ttl">Hi, I'm 2SinceJuly</title>
<desc id="dsc">Monochrome misty landscape of a Wannan-style village: layered ridges dissolving into fog, a stone arch bridge, white-walled houses along the water, and their reflection.</desc>
<defs>
<linearGradient id="sky" x1="0" y1="46" x2="0" y2="430" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#fdfdfd"/>
  <stop offset="0.55" stop-color="#f7f8f8"/>
  <stop offset="1" stop-color="#eceeee"/>
</linearGradient>
<clipPath id="card"><rect x="{CARD_X0}" y="{CARD_Y0}" width="{card_w}" height="{card_h}" rx="10"/></clipPath>
<clipPath id="scene"><rect x="{CARD_X0}" y="{CARD_Y0}" width="{card_w}" height="{card_h}" rx="10"/></clipPath>
<filter id="soft" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="0.7"/></filter>
<filter id="mid" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="1.1"/></filter>
<filter id="treeblur" x="-15%" y="-15%" width="130%" height="130%"><feGaussianBlur stdDeviation="1.2"/></filter>
<filter id="mirror" x="-10%" y="-10%" width="120%" height="120%">
  <feGaussianBlur stdDeviation="3.2"/>
</filter>
<filter id="fog" x="-20%" y="-70%" width="140%" height="240%"><feGaussianBlur stdDeviation="13"/></filter>
<filter id="b0.8" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="0.8"/></filter>
<filter id="b1.0" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="1.0"/></filter>
<filter id="b1.2" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="1.2"/></filter>
<filter id="b1.5" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="1.5"/></filter>
<filter id="b1.9" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="1.9"/></filter>
<filter id="b2.4" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="2.4"/></filter>
<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
  <feDropShadow dx="0" dy="6" stdDeviation="14" flood-color="#000000" flood-opacity="0.10"/>
</filter>
</defs>

<linearGradient id="page" x1="0" y1="0" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#eceeed"/><stop offset="1" stop-color="#dfe1e1"/>
</linearGradient>
<rect width="{W}" height="{H}" fill="url(#page)"/>
<g filter="url(#shadow)"><rect x="{CARD_X0}" y="{CARD_Y0}" width="{card_w}" height="{card_h}" rx="10" fill="#fdfdfd"/></g>

<g clip-path="url(#card)">
  <rect x="{CARD_X0}" y="{CARD_Y0}" width="{card_w}" height="{card_h}" fill="url(#sky)"/>
  {build()}
  <rect x="{CARD_X0}" y="{CARD_Y0}" width="{card_w}" height="250" fill="url(#topfade)"/>
</g>

<linearGradient id="topfade" x1="0" y1="{CARD_Y0}" x2="0" y2="270" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#fdfdfd" stop-opacity="1"/>
  <stop offset="0.72" stop-color="#fdfdfd" stop-opacity="0.88"/>
  <stop offset="1" stop-color="#fdfdfd" stop-opacity="0"/>
</linearGradient>

<g clip-path="url(#card)">
  <text x="78" y="112" font-family="'Courier New',Courier,monospace" font-size="10.5" letter-spacing="3.4" fill="#8b8f90">FIELD NOTES / WANNAN, CHINA</text>
  <text x="76" y="160" font-family="'Courier New',Courier,monospace" font-weight="700" font-size="34" fill="#1d1f20">Hi, I'm 2SinceJuly</text>
  <text x="78" y="192" font-family="'Courier New',Courier,monospace" font-size="15" fill="#4c5052">A student building AI agent workflows,</text>
  <text x="78" y="214" font-family="'Courier New',Courier,monospace" font-size="15" fill="#4c5052">and contributing to open source.</text>

  <rect x="1064" y="72" width="64" height="66" fill="none" stroke="#5f6365" stroke-width="1"/>
  <text x="1096" y="101" font-family="'PingFang SC','Hiragino Sans GB','Microsoft YaHei',serif" font-size="21" text-anchor="middle" fill="#2a2c2d">山</text>
  <text x="1096" y="127" font-family="'PingFang SC','Hiragino Sans GB','Microsoft YaHei',serif" font-size="21" text-anchor="middle" fill="#2a2c2d">水</text>

  <text x="78" y="548" font-family="'Courier New',Courier,monospace" font-size="9.5" letter-spacing="1.4" fill="#ffffff" opacity="0.9">山水之间</text>
  <text x="1122" y="548" font-family="'Courier New',Courier,monospace" font-size="9.5" text-anchor="end" letter-spacing="1.4" fill="#ffffff" opacity="0.9">BUILD / WANDER / REPEAT</text>
</g>
</svg>
'''


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets" / "banner.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg())
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
