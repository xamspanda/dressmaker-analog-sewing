#!/usr/bin/env python3
"""Make the YouTube thumbnail and Nexus cover image from a half-pressed frame of the gauge recording.

    python3 docs/media/demo/thumbnail.py --video "<recording>.mkv" --log depth.csv [--at 177.0]

Takes the frame from the original recording and draws a fresh key gauge on top, so the gauge sits
above the fade that hides the game's control hints.

Writes out/youtube-thumbnail.png (1280x720) and docs/media/0-cover.png (1920x1080, the Nexus
gallery's first image, which Nexus uses as the mod's tile).
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import make_media as mm  # noqa: E402
from composite import Gauge, load_depth, load_settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720
# Resting mouse cursor in the 2026-10-10 recording (1080p coordinates). The control hints and
# FPS counter along the bottom edge are faded out in the card instead.
CLEANUP = "delogo=x=1036:y=716:w=28:h=32"


def card(frame_uri, gauge_uri, gauge_w, gauge_h):
    body = f"""
  <image href="{frame_uri}" x="0" y="0" width="{W}" height="{H}"/>
  <defs>
    <linearGradient id="fadeLeft" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="{mm.BG}" stop-opacity="0.96"/>
      <stop offset="0.42" stop-color="{mm.BG}" stop-opacity="0.85"/>
      <stop offset="0.62" stop-color="{mm.BG}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="fadeBottom" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="{mm.BG}" stop-opacity="0"/>
      <stop offset="0.42" stop-color="{mm.BG}" stop-opacity="1"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#fadeLeft)"/>
  <rect y="{H - 80}" width="{W}" height="80" fill="url(#fadeBottom)"/>
  <text x="64" y="200" class="title" style="font-size:112px">Analog</text>
  <text x="64" y="318" class="title" style="font-size:112px">Sewing</text>
  {mm.stitches(70, 372, 470, 372, dash=(22, 12), width=7)}
  <text x="66" y="460" class="body" style="font-size:52px">Press harder,</text>
  <text x="66" y="526" class="body" style="font-size:52px">sew <tspan style="fill:{mm.TEAL}">faster</tspan>.</text>
  <text x="68" y="640" class="sub" style="font-size:28px">Wooting analog keyboard mod for Dressmaker</text>
  <image href="{gauge_uri}" x="{W - gauge_w - 28}" y="{H - gauge_h - 44}" width="{gauge_w}" height="{gauge_h}"/>
"""
    # The weave background would never show; drop it to keep the frame crisp.
    return mm.svg(W, H, body).replace('<rect width="1280" height="720" fill="url(#weave)"/>', "", 1)


OUTPUTS = [
    (os.path.join(HERE, "out", "youtube-thumbnail.png"), 1280, 720),
    (os.path.join(HERE, "..", "0-cover.png"), 1920, 1080),
]


def main():
    default_cfg = os.path.expanduser("~/Downloads/Dressmaker/game/BepInEx/config/xamspanda.dressmaker.analogsewing.cfg")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", required=True, help="the original recording (without the gauge)")
    p.add_argument("--log", required=True, help="its depth CSV from obs_record.py")
    p.add_argument("--at", type=float, default=177.0, help="source time of the frame (seconds); 177.0 is 2.3 mm / 50%%")
    p.add_argument("--offset", type=float, default=-0.117, help="gauge offset used when compositing (see composite.py)")
    p.add_argument("--config", default=default_cfg, help="mod .cfg to take speed settings from")
    args = p.parse_args()

    ts, ds = load_depth(args.log)
    t = args.at - args.offset
    depth = ds[max(0, min(range(len(ts)), key=lambda i: abs(ts[i] - t)))]
    gauge = Gauge(load_settings(args.config))

    with tempfile.TemporaryDirectory() as tmp:
        frame = pathlib.Path(tmp, "frame.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{args.at}", "-i", args.video, "-frames:v", "1",
                        "-vf", CLEANUP, str(frame)], check=True)
        gauge_png = pathlib.Path(tmp, "gauge.png")
        gauge.frame(depth).save(gauge_png)
        # The gauge at 720p scale, like it appears in the video.
        gw, gh = gauge.W * H / 1080, gauge.H * H / 1080
        for out, w, h in OUTPUTS:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            # Same 1280x720 layout, rendered at the output size via the SVG's viewBox.
            svg = pathlib.Path(tmp, "thumb.svg")
            svg.write_text(card(frame.as_uri(), gauge_png.as_uri(), gw, gh)
                           .replace(f'width="{W}" height="{H}" viewBox', f'width="{w}" height="{h}" viewBox', 1))
            mm.render(svg, out, w, h)
            print(os.path.normpath(out))


if __name__ == "__main__":
    main()
