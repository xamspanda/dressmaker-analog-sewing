#!/usr/bin/env python3
"""Generate the Nexus/GitHub page images as SVG and render them to PNG with headless Chromium.

    python3 docs/media/make_media.py

Fonts (Fraunces, Nunito) load from Google Fonts at render time.
"""
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


def keycap(x, y, w, depth_px, label="SPACE"):
    """Side-on keycap on a stem above a switch housing; depth_px (0..44) pushes the cap down."""
    cap_y = y + depth_px
    housing_y = y + 104
    return f"""
  <g filter="url(#shadow)">
    <rect x="{x + w*0.2}" y="{housing_y}" width="{w*0.6}" height="38" rx="8" fill="#251d30" stroke="{BG2}" stroke-width="2"/>
    <rect x="{x + w/2 - 13}" y="{cap_y + 50}" width="26" height="{housing_y - cap_y - 48}" rx="4" fill="{MUTED}"/>
    <path d="M{x} {cap_y + 58} L{x + 14} {cap_y + 8} H{x + w - 14} L{x + w} {cap_y + 58} Z" fill="{KEY_SIDE}"/>
    <rect x="{x + 14}" y="{cap_y}" width="{w - 28}" height="44" rx="9" fill="{KEY}"/>
    <text x="{x + w/2}" y="{cap_y + 29}" text-anchor="middle" class="body" style="fill:#6b5d70;font-size:18px;letter-spacing:3px">{label}</text>
  </g>"""


def header():
    w, h = 1300, 372
    body = f"""
  <text x="70" y="150" class="title" style="font-size:86px">Analog Sewing</text>
  <text x="74" y="208" class="sub" style="font-size:30px;fill:{CREAM}">Press lightly to sew slowly.</text>
  <text x="74" y="250" class="sub" style="font-size:30px;fill:{CREAM}">Press harder to sew faster.</text>
  <text x="74" y="306" class="sub" style="font-size:21px">A Dressmaker mod for Wooting analog keyboards</text>
  {keycap(790, 112, 330, 22)}
  <path d="M955 46 V92" stroke="{MUSTARD}" stroke-width="6" stroke-linecap="round"/>
  <path d="M937 76 L955 96 L973 76" stroke="{MUSTARD}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
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
        depth_px = mm / TRAVEL_MM * 44
        gauge_w = 380
        dash = (6 + pct * 0.25, max(26 - pct * 0.22, 4))
        panels.append(f"""
  <rect x="{cx - 270}" y="300" width="540" height="620" rx="28" fill="{CARD}" opacity="0.92"/>
  <text x="{cx}" y="380" text-anchor="middle" class="title" style="font-size:46px">{name}</text>
  {keycap(cx - 160, 440, 320, depth_px)}
  <text x="{cx}" y="650" text-anchor="middle" class="mono" style="font-size:30px">{mm:.1f} mm</text>
  <rect x="{cx - gauge_w/2}" y="700" width="{gauge_w}" height="26" rx="13" fill="{BG}"/>
  <rect x="{cx - gauge_w/2}" y="700" width="{gauge_w * pct / 100:.1f}" height="26" rx="13" fill="{TEAL}"/>
  <text x="{cx}" y="780" text-anchor="middle" class="body" style="font-size:34px">{pct:.0f}% speed</text>
  {stitches(cx - 200, 850, cx + 200, 850, dash=dash, width=6)}""")
    body = f"""
  <text x="960" y="150" text-anchor="middle" class="title" style="font-size:80px">Your keyboard is the foot pedal</text>
  <text x="960" y="220" text-anchor="middle" class="sub" style="font-size:34px">The sewing machine's speed follows how far you press Space</text>
  {''.join(panels)}
  <text x="960" y="1010" text-anchor="middle" class="sub" style="font-size:26px">Let go and the machine stops. Right-click sewing and the speed slider still work as normal.</text>
"""
    return svg(w, h, body)


def curve():
    w, h = 1920, 1080
    gx, gy, gw, gh = 260, 260, 1000, 620  # plot area

    def px(mm):
        return gx + mm / TRAVEL_MM * gw

    def py(pct):
        return gy + gh - pct / 100 * gh

    def path(c):
        pts = [f"M{px(0):.1f} {py(0):.1f}", f"L{px(START_MM):.1f} {py(0):.1f}"]
        steps = 80
        for k in range(steps + 1):
            mm = START_MM + (TRAVEL_MM - START_MM) * k / steps
            pts.append(f"L{px(mm):.1f} {py(speed(mm, c)):.1f}")
        return " ".join(pts)

    grid = "".join(
        f'<line x1="{gx}" y1="{py(p)}" x2="{gx + gw}" y2="{py(p)}" stroke="{BG2}" stroke-width="2"/>'
        f'<text x="{gx - 18}" y="{py(p) + 9}" text-anchor="end" class="sub" style="font-size:24px">{p}%</text>'
        for p in (0, 25, 50, 75, 100))
    xticks = "".join(
        f'<text x="{px(m)}" y="{gy + gh + 44}" text-anchor="middle" class="sub" style="font-size:24px">{m} mm</text>'
        for m in (0, 1, 2, 3, 4))

    def setting(y, key, value, desc, color):
        return f"""
  <circle cx="1388" cy="{y - 9}" r="10" fill="{color}"/>
  <text x="1412" y="{y}" class="mono" style="font-size:28px">{key} = <tspan style="fill:{color}">{value}</tspan></text>
  <text x="1412" y="{y + 38}" class="sub" style="font-size:24px">{desc}</text>"""

    body = f"""
  <text x="960" y="130" text-anchor="middle" class="title" style="font-size:80px">Tune the feel</text>
  <text x="960" y="196" text-anchor="middle" class="sub" style="font-size:32px">Every part of the response is configurable (defaults shown)</text>
  <rect x="150" y="230" width="1180" height="760" rx="28" fill="{CARD}" opacity="0.92"/>
  {grid}{xticks}
  <text x="{gx + gw/2}" y="{gy + gh + 92}" text-anchor="middle" class="body" style="font-size:28px">How far you press the key</text>
  <text transform="translate(186 {gy + gh/2}) rotate(-90)" text-anchor="middle" class="body" style="font-size:28px">Machine speed</text>
  <path d="{path(1.0)}" fill="none" stroke="{MUTED}" stroke-width="3" stroke-dasharray="10 10" opacity="0.6"/>
  <path d="{path(3.0)}" fill="none" stroke="{MUTED}" stroke-width="3" stroke-dasharray="10 10" opacity="0.6"/>
  <text x="{px(1.55)}" y="{py(speed(1.75, 1.0)) - 30}" class="sub" style="font-size:22px">Curve 1.0</text>
  <text x="{px(2.85)}" y="{py(speed(2.85, 3.0)) + 36}" class="sub" style="font-size:22px">Curve 3.0</text>
  <path d="{path(CURVE)}" fill="none" stroke="{TEAL}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/>
  <line x1="{px(START_MM)}" y1="{gy}" x2="{px(START_MM)}" y2="{gy + gh}" stroke="{ROSE}" stroke-width="3" stroke-dasharray="8 8"/>
  <line x1="{px(FULL_MM)}" y1="{gy}" x2="{px(FULL_MM)}" y2="{gy + gh}" stroke="{MUSTARD}" stroke-width="3" stroke-dasharray="8 8"/>
  <circle cx="{px(START_MM)}" cy="{py(MIN_PCT)}" r="11" fill="{ROSE}"/>
  <circle cx="{px(FULL_MM)}" cy="{py(MAX_PCT)}" r="11" fill="{MUSTARD}"/>
  {setting(330, "StartDepthMm", START_MM, "Press this far to start sewing", ROSE)}
  {setting(450, "FullSpeedDepthMm", FULL_MM, "Press this far for full speed", MUSTARD)}
  {setting(570, "MinSpeedPercent", MIN_PCT, "Speed when sewing starts", ROSE)}
  {setting(690, "MaxSpeedPercent", MAX_PCT, "Top speed", MUSTARD)}
  {setting(810, "Curve", CURVE, "Higher = finer control when slow", TEAL)}
  <text x="1388" y="950" class="sub" style="font-size:24px">Edit the .cfg file, or press F1 with</text>
  <text x="1388" y="986" class="sub" style="font-size:24px">ConfigurationManager installed</text>
"""
    return svg(w, h, body)


def install():
    w, h = 1920, 1080
    steps = [
        ("1", "Install BepInEx 5", ["Extract BepInEx 5 (x64) into", "the Dressmaker folder, next", "to Dressmaker.exe"], ROSE),
        ("2", "Add Analog Sewing", ["Extract this mod into the", "same folder. Wooting's", "Analog SDK is included."], MUSTARD),
        ("3", "Sew!", ["Launch the game and press", "Space gently, then harder.", "No other setup needed."], TEAL),
    ]
    cards = []
    for i, (num, title, lines, color) in enumerate(steps):
        x = 150 + i * 560
        text = "".join(
            f'<text x="{x + 50}" y="{620 + j * 50}" class="sub" style="font-size:31px;fill:{CREAM}">{line}</text>'
            for j, line in enumerate(lines))
        cards.append(f"""
  <rect x="{x}" y="300" width="500" height="520" rx="28" fill="{CARD}" opacity="0.92"/>
  <circle cx="{x + 110}" cy="420" r="62" fill="{color}"/>
  <text x="{x + 110}" y="446" text-anchor="middle" class="title" style="font-size:72px;fill:{BG}">{num}</text>
  <text x="{x + 50}" y="555" class="title" style="font-size:46px">{title}</text>
  {text}""")
    body = f"""
  <text x="960" y="160" text-anchor="middle" class="title" style="font-size:80px">Install in 3 steps</text>
  <text x="960" y="228" text-anchor="middle" class="sub" style="font-size:32px">Works on Windows and on Linux / Steam Deck through Proton</text>
  {''.join(cards)}
  <rect x="380" y="880" width="1160" height="110" rx="22" fill="{BG}" stroke="{BG2}" stroke-width="2"/>
  <text x="960" y="924" text-anchor="middle" class="sub" style="font-size:26px">Linux / Steam Deck launch options:</text>
  <text x="960" y="968" text-anchor="middle" class="mono" style="font-size:30px;fill:{MUSTARD}">WINEDLLOVERRIDES="winhttp=n,b" %command%</text>
"""
    return svg(w, h, body)


IMAGES = {
    "header": (header, 1300, 372),
    "1-foot-pedal": (pedal, 1920, 1080),
    "2-tune-the-feel": (curve, 1920, 1080),
    "3-install": (install, 1920, 1080),
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
