#!/usr/bin/env python3
"""Generate the Nexus/GitHub page images as SVG and render them to PNG with headless Chromium.

    python3 docs/media/make_media.py

Fonts (Fraunces, Nunito) load from Google Fonts at render time.
"""
import math
import pathlib
import subprocess
import tempfile

OUT = pathlib.Path(__file__).resolve().parent

# Cozy sewing-room palette on a dark plum ground (Nexus pages are dark).
BG = "#2a2135"
BG2 = "#352a44"
CARD = "#3d3150"
CREAM = "#f6eee3"
MUTED = "#c9bccf"
ROSE = "#e8798c"
MUSTARD = "#f0bf5a"
TEAL = "#6cc4b8"
KEY = "#efe6da"
KEY_SIDE = "#cbbfb1"

# Mod defaults (src/AnalogSewing/Plugin.cs)
START_MM, FULL_MM, MIN_PCT, MAX_PCT, CURVE, TRAVEL_MM = 0.4, 3.6, 5, 100, 1.5, 4.0

FONTS = "@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&amp;family=Nunito:wght@500;700;800&amp;display=block');"


def svg(w, h, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>{FONTS}
.title {{ font-family: Fraunces, Georgia, serif; font-weight: 700; fill: {CREAM}; }}
.sub {{ font-family: Nunito, 'Noto Sans', sans-serif; font-weight: 700; fill: {MUTED}; }}
.body {{ font-family: Nunito, 'Noto Sans', sans-serif; font-weight: 700; fill: {CREAM}; }}
.mono {{ font-family: 'iA Writer Mono S', 'Liberation Mono', monospace; fill: {CREAM}; }}
</style>
<defs>
  <pattern id="weave" width="14" height="14" patternUnits="userSpaceOnUse">
    <rect width="14" height="14" fill="{BG}"/>
    <path d="M0 7h14M7 0v14" stroke="{BG2}" stroke-width="1.2"/>
  </pattern>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.35"/>
  </filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#weave)"/>
{body}
</svg>"""


def speed(mm, curve=CURVE):
    t = min(max((mm - START_MM) / (FULL_MM - START_MM), 0), 1)
    return (MIN_PCT + (MAX_PCT - MIN_PCT) * t ** curve) if mm >= START_MM else 0


def stitches(x0, y0, x1, y1, color=ROSE, dash=(18, 12), width=5):
    return (f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-dasharray="{dash[0]} {dash[1]}"/>')


TRAVEL_PX = 40  # drawn key travel for TRAVEL_MM


def switch_key(cx, top_y, depth_px):
    """Side view of a 1u keycap on a mechanical switch in a plate, centred on cx.

    top_y is the top of the keycap at rest; depth_px (0..TRAVEL_PX) pushes the cap and stem down.
    The drawing is 190px tall.
    """
    cap_y = top_y + depth_px
    hy = top_y + 70 + TRAVEL_PX  # top of the switch housing
    return f"""
  <g filter="url(#shadow)">
    <rect x="{cx - 34}" y="{hy + 54}" width="6" height="20" rx="2" fill="{MUSTARD}"/>
    <rect x="{cx + 22}" y="{hy + 54}" width="6" height="16" rx="2" fill="{MUSTARD}"/>
    <rect x="{cx - 70}" y="{hy + 30}" width="140" height="28" rx="5" fill="#2a2236" stroke="{BG2}" stroke-width="2"/>
    <rect x="{cx - 130}" y="{hy + 30}" width="260" height="9" rx="2" fill="#9a8fa6"/>
    <path d="M{cx - 56} {hy} H{cx + 56} L{cx + 70} {hy + 32} H{cx - 70} Z" fill="#5b4c6e"/>
    <path d="M{cx - 40} {hy + 6} H{cx + 40} L{cx + 46} {hy + 22} H{cx - 46} Z" fill="#6f5f84"/>
    <rect x="{cx - 11}" y="{cap_y + 62}" width="22" height="{hy - cap_y - 58}" rx="3" fill="{ROSE}"/>
    <path d="M{cx - 100} {cap_y + 70} L{cx - 80} {cap_y + 4} Q{cx} {cap_y + 14} {cx + 80} {cap_y + 4} L{cx + 100} {cap_y + 70} Z" fill="{KEY_SIDE}"/>
    <path d="M{cx - 100} {cap_y + 70} L{cx - 80} {cap_y + 4} L{cx - 68} {cap_y + 9} L{cx - 84} {cap_y + 70} Z" fill="#b5a897"/>
    <path d="M{cx - 80} {cap_y + 4} Q{cx} {cap_y + 14} {cx + 80} {cap_y + 4} L{cx + 77} {cap_y + 14} Q{cx} {cap_y + 24} {cx - 77} {cap_y + 14} Z" fill="{KEY}"/>
  </g>"""


def header():
    w, h = 1300, 372
    key_cx = 1000  # centred over the slow-to-fast stitches (760..1240)
    body = f"""
  <text x="70" y="182" class="title" style="font-size:92px">Analog Sewing</text>
  <text x="76" y="236" class="sub" style="font-size:26px">A Dressmaker mod for Wooting analog keyboards</text>
  <path d="M{key_cx} 18 V62" stroke="{MUSTARD}" stroke-width="6" stroke-linecap="round"/>
  <path d="M{key_cx - 18} 46 L{key_cx} 66 L{key_cx + 18} 46" stroke="{MUSTARD}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  {switch_key(key_cx, 82, 12)}
  {stitches(760, 318, 870, 318, dash=(6, 22))}
  {stitches(890, 318, 1010, 318, dash=(12, 14))}
  {stitches(1030, 318, 1240, 318, dash=(26, 6))}
  <text x="760" y="352" class="sub" style="font-size:17px">slow</text>
  <text x="1240" y="352" text-anchor="end" class="sub" style="font-size:17px">fast</text>
"""
    return svg(w, h, body)


def pedal():
    w, h = 1920, 1080
    panels = []
    for i, (name, mm) in enumerate([("Light press", 0.9), ("Halfway", 2.2), ("Full press", 4.0)]):
        cx = 330 + i * 630
        pct = speed(mm)
        depth_px = mm / TRAVEL_MM * TRAVEL_PX
        gauge_w = 380
        dash = (6 + pct * 0.25, max(26 - pct * 0.22, 4))
        panels.append(f"""
  <rect x="{cx - 270}" y="290" width="540" height="660" rx="28" fill="{CARD}" opacity="0.92"/>
  <text x="{cx}" y="380" text-anchor="middle" class="title" style="font-size:50px">{name}</text>
  {switch_key(cx, 430, depth_px)}
  <rect x="{cx - gauge_w/2}" y="680" width="{gauge_w}" height="28" rx="14" fill="{BG}"/>
  <rect x="{cx - gauge_w/2}" y="680" width="{gauge_w * pct / 100:.1f}" height="28" rx="14" fill="{TEAL}"/>
  <text x="{cx}" y="770" text-anchor="middle" class="body" style="font-size:38px">{pct:.0f}% speed</text>
  {stitches(cx - 200, 860, cx + 200, 860, dash=dash, width=6)}""")
    body = f"""
  <text x="960" y="180" text-anchor="middle" class="title" style="font-size:86px">Your keyboard is the foot pedal</text>
  {''.join(panels)}
"""
    return svg(w, h, body)


def curve():
    w, h = 1920, 1080
    gx, gy, gw, gh = 250, 170, 1540, 720  # plot area

    def px(mm):
        return gx + mm / TRAVEL_MM * gw

    def py(pct):
        return gy + gh - pct / 100 * gh

    def path(c):
        pts = [f"M{px(0):.1f} {py(0):.1f}", f"L{px(START_MM):.1f} {py(0):.1f}"]
        steps = 100
        for k in range(steps + 1):
            mm = START_MM + (TRAVEL_MM - START_MM) * k / steps
            pts.append(f"L{px(mm):.1f} {py(speed(mm, c)):.1f}")
        return " ".join(pts)

    grid = "".join(
        f'<line x1="{gx}" y1="{py(p)}" x2="{gx + gw}" y2="{py(p)}" stroke="{BG2}" stroke-width="2"/>'
        f'<text x="{gx - 22}" y="{py(p) + 10}" text-anchor="end" class="sub" style="font-size:28px">{p}%</text>'
        for p in (0, 25, 50, 75, 100))
    xticks = "".join(
        f'<text x="{px(m)}" y="{gy + gh + 50}" text-anchor="middle" class="sub" style="font-size:28px">{m} mm</text>'
        for m in (0, 1, 2, 3, 4))

    lx, ly = gx + 40, gy + 30  # legend, in the empty upper-left of the plot

    def setting(row, key, value, color):
        y = ly + 82 + row * 56
        return f"""
  <circle cx="{lx + 34}" cy="{y - 9}" r="11" fill="{color}"/>
  <text x="{lx + 60}" y="{y}" class="mono" style="font-size:29px">{key} = <tspan style="fill:{color}">{value}</tspan></text>"""

    body = f"""
  <rect x="40" y="30" width="1840" height="1020" rx="32" fill="{CARD}" opacity="0.92"/>
  <text x="{gx}" y="118" class="title" style="font-size:64px">Tune the feel</text>
  {grid}{xticks}
  <text x="{gx + gw/2}" y="{gy + gh + 108}" text-anchor="middle" class="body" style="font-size:32px">How far you press the key</text>
  <text transform="translate(108 {gy + gh/2}) rotate(-90)" text-anchor="middle" class="body" style="font-size:32px">Machine speed</text>
  <path d="{path(1.0)}" fill="none" stroke="{MUTED}" stroke-width="3" stroke-dasharray="10 10" opacity="0.6"/>
  <path d="{path(3.0)}" fill="none" stroke="{MUTED}" stroke-width="3" stroke-dasharray="10 10" opacity="0.6"/>
  <text x="{px(2.3)}" y="{py(speed(2.3, 1.0)) - 24}" text-anchor="end" class="sub" style="font-size:26px">Curve 1.0</text>
  <text x="{px(2.9)}" y="{py(speed(2.9, 3.0)) + 44}" class="sub" style="font-size:26px">Curve 3.0</text>
  <path d="{path(CURVE)}" fill="none" stroke="{TEAL}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>
  <line x1="{px(START_MM)}" y1="{gy}" x2="{px(START_MM)}" y2="{gy + gh}" stroke="{ROSE}" stroke-width="3" stroke-dasharray="8 8"/>
  <line x1="{px(FULL_MM)}" y1="{gy}" x2="{px(FULL_MM)}" y2="{gy + gh}" stroke="{MUSTARD}" stroke-width="3" stroke-dasharray="8 8"/>
  <circle cx="{px(START_MM)}" cy="{py(MIN_PCT)}" r="13" fill="{ROSE}"/>
  <circle cx="{px(FULL_MM)}" cy="{py(MAX_PCT)}" r="13" fill="{MUSTARD}"/>
  <rect x="{lx}" y="{ly}" width="500" height="340" rx="22" fill="{BG}" opacity="0.92" stroke="{BG2}" stroke-width="2"/>
  <text x="{lx + 34}" y="{ly + 2 + 28}" class="sub" style="font-size:22px;letter-spacing:2px">DEFAULT SETTINGS</text>
  {setting(0, "StartDepthMm", START_MM, ROSE)}
  {setting(1, "FullSpeedDepthMm", FULL_MM, MUSTARD)}
  {setting(2, "MinSpeedPercent", MIN_PCT, ROSE)}
  {setting(3, "MaxSpeedPercent", MAX_PCT, MUSTARD)}
  {setting(4, "Curve", CURVE, TEAL)}
"""
    return svg(w, h, body)


def icon():
    """Square mod icon: a half-pressed key under a speed gauge. No text, so it still reads at thumbnail size."""
    w = h = 512
    cx, cy, r = 256, 304, 212  # gauge: a semicircle over the key
    fill = 0.62
    a = math.pi * (1 - fill)
    ex, ey = cx + r * math.cos(a), cy - r * math.sin(a)
    s = 1.42  # switch_key is drawn 260 x 190
    body = f"""
  <path d="M{cx - r} {cy} A{r} {r} 0 0 1 {cx + r} {cy}" stroke="{CARD}" stroke-width="28" fill="none" stroke-linecap="round"/>
  <path d="M{cx - r} {cy} A{r} {r} 0 0 1 {ex:.1f} {ey:.1f}" stroke="{TEAL}" stroke-width="28" fill="none" stroke-linecap="round"/>
  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="21" fill="{CREAM}"/>
  <g transform="translate({cx} {cy - 131}) scale({s})">{switch_key(0, 0, 18)}</g>
"""
    return svg(w, h, body)


IMAGES = {
    "header": (header, 1300, 372),
    "icon": (icon, 512, 512),
    "1-foot-pedal": (pedal, 1920, 1080),
    "2-tune-the-feel": (curve, 1920, 1080),
}


def render(svg_path, png_path, w, h):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([
            "chromium", "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
            "--virtual-time-budget=5000", f"--window-size={w},{h}", f"--screenshot={png_path}", svg_path.as_uri(),
        ], check=True, capture_output=True)


if __name__ == "__main__":
    for name, (make, w, h) in IMAGES.items():
        svg_path = OUT / f"{name}.svg"
        svg_path.write_text(make())
        render(svg_path, OUT / f"{name}.png", w, h)
        print(OUT / f"{name}.png")
