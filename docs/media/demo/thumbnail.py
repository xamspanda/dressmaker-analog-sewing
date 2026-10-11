#!/usr/bin/env python3
"""Make the YouTube thumbnail (1280x720) from a full-speed frame of the gauge recording.

    python3 docs/media/demo/thumbnail.py --video "<recording> (gauge).mp4" [--at 175.0]
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import make_media as mm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720
# FPS counter and a resting mouse cursor in the 2026-10-10 recording (1080p coordinates)
CLEANUP = "delogo=x=926:y=1058:w=68:h=20,delogo=x=1036:y=716:w=28:h=32"


def card(frame_uri):
    body = f"""
  <image href="{frame_uri}" x="0" y="0" width="{W}" height="{H}"/>
  <defs>
    <linearGradient id="fadeLeft" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="{mm.BG}" stop-opacity="0.96"/>
      <stop offset="0.42" stop-color="{mm.BG}" stop-opacity="0.85"/>
      <stop offset="0.62" stop-color="{mm.BG}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#fadeLeft)"/>
  <text x="64" y="200" class="title" style="font-size:112px">Analog</text>
  <text x="64" y="318" class="title" style="font-size:112px">Sewing</text>
  {mm.stitches(70, 372, 470, 372, dash=(22, 12), width=7)}
  <text x="66" y="460" class="body" style="font-size:52px">Press harder,</text>
  <text x="66" y="526" class="body" style="font-size:52px">sew <tspan style="fill:{mm.TEAL}">faster</tspan>.</text>
  <text x="68" y="640" class="sub" style="font-size:28px">Wooting analog keyboard mod for Dressmaker</text>
"""
    # The weave background would never show; drop it to keep the frame crisp.
    return mm.svg(W, H, body).replace('<rect width="1280" height="720" fill="url(#weave)"/>', "", 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", required=True)
    p.add_argument("--at", type=float, default=175.0, help="source time of the frame (seconds)")
    p.add_argument("--output", default=os.path.join(HERE, "out", "youtube-thumbnail.png"))
    args = p.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        frame = pathlib.Path(tmp, "frame.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{args.at}", "-i", args.video, "-frames:v", "1",
                        "-vf", f"{CLEANUP},scale={W}:{H}:flags=lanczos", str(frame)], check=True)
        svg = pathlib.Path(tmp, "thumb.svg")
        svg.write_text(card(frame.as_uri()))
        mm.render(svg, args.output, W, H)
    print(args.output)


if __name__ == "__main__":
    main()
