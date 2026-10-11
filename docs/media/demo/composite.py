#!/usr/bin/env python3
"""Burn a key-depth gauge into the corner of a recording, using a depth log from obs_record.py.

    python3 docs/media/demo/composite.py --video rec.mkv --log depth.csv [--output out.mp4]
    python3 docs/media/demo/composite.py --preview

obs_record.py runs this automatically when a recording stops.
The gauge shows the keycap sinking, the depth in mm and the machine speed, computed with the
mod's settings from the game's BepInEx config (or the defaults). If the gauge looks early or
late against the in-game speed slider, nudge --offset (seconds; positive = gauge later). By
default it corrects for the recorder's startup delay, assuming the video and log end together.
"""
import argparse
import bisect
import configparser
import json
import os
import subprocess
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf"
FPS = 60

# Palette shared with make_media.py
PANEL = (42, 33, 53, 242)
BORDER = (53, 42, 68, 255)
CREAM = (246, 238, 227, 255)
MUTED = (201, 188, 207, 255)
ROSE = (232, 121, 140, 255)
MUSTARD = (240, 191, 90, 255)
TEAL = (108, 196, 184, 255)
TRACK = (32, 25, 41, 255)
KEY = (239, 230, 218, 255)
KEY_SIDE = (203, 191, 177, 255)
KEY_SHADE = (181, 168, 151, 255)

DEFAULTS = {"StartDepthMm": 0.4, "FullSpeedDepthMm": 3.6, "MinSpeedPercent": 5,
            "MaxSpeedPercent": 100, "Curve": 1.5, "KeyTravelMm": 4.0}


def load_settings(path):
    s = dict(DEFAULTS)
    if path and os.path.exists(path):
        cfg = configparser.ConfigParser()
        cfg.optionxform = str
        cfg.read(path)
        for section in cfg.sections():
            for key in s:
                if key in cfg[section]:
                    s[key] = float(cfg[section][key])
    return s


def speed_pct(mm, s):
    if mm < s["StartDepthMm"]:
        return 0.0
    span = s["FullSpeedDepthMm"] - s["StartDepthMm"]
    t = min(max((mm - s["StartDepthMm"]) / span, 0), 1) if span > 0 else 1
    return s["MinSpeedPercent"] + (s["MaxSpeedPercent"] - s["MinSpeedPercent"]) * t ** s["Curve"]


def font(size, weight):
    path = os.path.join(ROOT, "build", "cache", "Nunito.ttf")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(FONT_URL, path)
    f = ImageFont.truetype(path, size)
    f.set_variation_by_axes([weight])
    return f


def quad(p0, c, p1, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in (i / n for i in range(n + 1))]


def draw_switch(d, cx, top, depth_px, k):
    """Same keycap-on-switch drawing as make_media.py's switch_key, scaled by k."""
    def P(x, y):
        return (cx + x * k, top + y * k)

    def R(x, y, w, h):
        return [P(x, y), P(x + w, y + h)]

    cap = depth_px
    hy = 110
    d.rectangle(R(-34, hy + 54, 6, 20), fill=MUSTARD)
    d.rectangle(R(22, hy + 54, 6, 16), fill=MUSTARD)
    d.rounded_rectangle(R(-70, hy + 30, 140, 28), radius=5 * k, fill=(42, 34, 54, 255), outline=BORDER, width=max(1, round(2 * k)))
    d.rounded_rectangle(R(-130, hy + 30, 260, 9), radius=2 * k, fill=(154, 143, 166, 255))
    d.polygon([P(-56, hy), P(56, hy), P(70, hy + 32), P(-70, hy + 32)], fill=(91, 76, 110, 255))
    d.polygon([P(-40, hy + 6), P(40, hy + 6), P(46, hy + 22), P(-46, hy + 22)], fill=(111, 95, 132, 255))
    d.rounded_rectangle([P(-11, cap + 62), P(11, hy + 4)], radius=3 * k, fill=ROSE)
    top_edge = [P(*q) for q in quad((-80, cap + 4), (0, cap + 14), (80, cap + 4))]
    d.polygon([P(-100, cap + 70)] + top_edge + [P(100, cap + 70)], fill=KEY_SIDE)
    d.polygon([P(-100, cap + 70), P(-80, cap + 4), P(-68, cap + 9), P(-84, cap + 70)], fill=KEY_SHADE)
    under = [P(*q) for q in quad((77, cap + 14), (0, cap + 24), (-77, cap + 14))]
    d.polygon(top_edge + under, fill=KEY)


class Gauge:
    W, H = 560, 250
    SS = 2  # supersampling for smooth edges

    def __init__(self, settings, scale=1.0):
        self.s = settings
        self.W, self.H = round(Gauge.W * scale), round(Gauge.H * scale)
        k = self.SS * scale
        self.k = k
        self.f_label = font(round(19 * k), 800)
        self.f_big = font(round(52 * k), 800)
        self.f_val = font(round(30 * k), 800)

    def frame(self, depth01):
        k = self.k
        mm = depth01 * self.s["KeyTravelMm"]
        pct = speed_pct(mm, self.s)
        img = Image.new("RGBA", (self.W * self.SS, self.H * self.SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=26 * k, fill=PANEL, outline=BORDER, width=max(1, round(2 * k)))

        draw_switch(d, 140 * k, 28 * k, depth01 * 40, 0.92 * k)

        x = 300 * k
        d.text((x, 30 * k), "KEY DEPTH", font=self.f_label, fill=MUTED)
        d.text((x, 50 * k), f"{mm:.1f} mm", font=self.f_big, fill=CREAM)
        bar_w = 220 * k
        d.rounded_rectangle([x, 122 * k, x + bar_w, 136 * k], radius=7 * k, fill=TRACK)
        if depth01 > 0.005:
            d.rounded_rectangle([x, 122 * k, x + max(14 * k, bar_w * depth01), 136 * k], radius=7 * k, fill=ROSE)
        d.text((x, 158 * k), "SPEED", font=self.f_label, fill=MUTED)
        label = f"{pct:.0f}%" if pct > 0 else "stopped"
        d.text((x, 178 * k), label, font=self.f_val, fill=TEAL if pct > 0 else MUTED)
        return img.resize((self.W, self.H), Image.LANCZOS)


def load_depth(path):
    ts, ds = [], []
    with open(path) as f:
        next(f)
        for line in f:
            t, d = line.split(",")
            ts.append(float(t))
            ds.append(float(d))
    return ts, ds


def probe(path):
    """(width, height, duration in seconds) of a video file."""
    out = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
        "-of", "json", path]))
    return out["streams"][0]["width"], out["streams"][0]["height"], float(out["format"]["duration"])


def main():
    default_cfg = os.path.expanduser("~/Downloads/Dressmaker/game/BepInEx/config/xamspanda.dressmaker.analogsewing.cfg")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", help="recording to add the gauge to")
    p.add_argument("--log", help="depth CSV from obs_record.py")
    p.add_argument("--output", help="output file (default: '<video> (gauge).mp4')")
    p.add_argument("--offset", type=float, help="shift the gauge in time (seconds; default: auto)")
    p.add_argument("--config", default=default_cfg, help="mod .cfg to take speed settings from")
    p.add_argument("--margin", type=int, default=40, help="gap from the corner at 1080p (scaled with the video)")
    p.add_argument("--preview", action="store_true", help="only render a PNG of the gauge with the key half down")
    args = p.parse_args()

    settings = load_settings(args.config)
    if args.preview:
        path = os.path.join(HERE, "out", "gauge-preview.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Gauge(settings).frame(0.55).save(path)
        print(path)
        return
    if not (args.video and args.log):
        p.error("--video and --log are required")

    ts, ds = load_depth(args.log)
    width, height, video_s = probe(args.video)
    scale = height / 1080
    gauge = Gauge(settings, scale)
    frames = round(video_s * FPS)
    # The log starts when OBS reports the recording started and stops when it reports it stopped.
    offset = args.offset if args.offset is not None else -max(0.0, ts[-1] - video_s)
    print(f"Gauge offset {offset:+.3f}s", file=sys.stderr)
    dst = args.output or os.path.splitext(args.video)[0] + " (gauge).mp4"
    m = round(args.margin * scale)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error", "-i", args.video,
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{gauge.W}x{gauge.H}", "-framerate", str(FPS), "-i", "-",
        "-filter_complex", f"[0:v][1:v]overlay=x=W-w-{m}:y=H-h-{m}:eof_action=pass[v]",
        "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst,
    ], stdin=subprocess.PIPE)

    cache = {}
    for i in range(frames):
        t = i / FPS - offset
        j = bisect.bisect_right(ts, t) - 1
        depth = round(ds[j], 3) if j >= 0 else 0.0
        if depth not in cache:
            cache[depth] = gauge.frame(depth).tobytes()
        ff.stdin.write(cache[depth])
        if i % (FPS * 5) == 0:
            print(f"\r{i * 100 // frames}%", end="", file=sys.stderr, flush=True)
    ff.stdin.close()
    if ff.wait():
        sys.exit("ffmpeg failed")
    print(f"\rWrote {dst}", file=sys.stderr)


if __name__ == "__main__":
    main()
