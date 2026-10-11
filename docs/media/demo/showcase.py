#!/usr/bin/env python3
"""Cut a short showcase video from a gauge recording: title card, captioned clips, end card.

    python3 docs/media/demo/showcase.py --video "<recording> (gauge).mp4"
    python3 docs/media/demo/showcase.py --video "..." --no-title --output out/twitter.mp4

--no-title starts straight on gameplay (no title card or fade-in), for social feeds.

The clip list (CLIPS) is hand-picked for the 2026-10-10 recording using its depth log; edit
the times for a new recording. Captions sit bottom-left, above the game's control hints and opposite the key gauge. Uses only the
"Game" audio track (OBS track 3) so no mic or chat audio ends up in the video.
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import make_media as mm  # noqa: E402
from composite import font, PANEL, BORDER, CREAM, ROSE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 60
FADE = 0.5           # crossfade between shots
GAME_AUDIO = "0:a:2"  # OBS track 3, "Game"
HIDE_FPS = "delogo=x=926:y=1058:w=68:h=20"  # FPS counter in the 2026-10-10 recording

# (start s, end s, caption) in the source recording
CLIPS = [
    (157.4, 164.6, "Press lightly for slow, careful curves"),
    (14.0, 19.95, "Press harder to speed up"),
    (180.6, 185.45, "Full press, full speed"),
    (173.2, 178.7, "Ease off whenever you need to"),
    (207.0, 214.5, "Take every curve at your own pace"),
    (242.9, 246.2, None),  # the finished dress (OBS appears at 246.5)
]
TITLE_S, END_S = 3.5, 4.5


def title_card():
    body = f"""
  <text x="960" y="400" text-anchor="middle" class="title" style="font-size:150px">Analog Sewing</text>
  <text x="960" y="480" text-anchor="middle" class="sub" style="font-size:40px">A Dressmaker mod for Wooting analog keyboards</text>
  {mm.switch_key(960, 560, 14)}
  {mm.stitches(620, 850, 800, 850, dash=(8, 26), width=7)}
  {mm.stitches(830, 850, 1060, 850, dash=(16, 16), width=7)}
  {mm.stitches(1090, 850, 1300, 850, dash=(34, 8), width=7)}
  <text x="620" y="900" class="sub" style="font-size:26px">slow</text>
  <text x="1300" y="900" text-anchor="end" class="sub" style="font-size:26px">fast</text>
"""
    return mm.svg(W, H, body)


def end_card():
    body = f"""
  <text x="960" y="390" text-anchor="middle" class="title" style="font-size:130px">Analog Sewing</text>
  <text x="960" y="480" text-anchor="middle" class="sub" style="font-size:42px;fill:{mm.CREAM}">Your keyboard is the foot pedal.</text>
  {mm.stitches(660, 560, 1260, 560, dash=(18, 12), width=6)}
  <text x="960" y="660" text-anchor="middle" class="body" style="font-size:40px">Free on Nexus Mods</text>
  <text x="960" y="718" text-anchor="middle" class="mono" style="font-size:32px;fill:{mm.MUSTARD}">nexusmods.com/dressmaker/mods/516</text>
  <text x="960" y="808" text-anchor="middle" class="sub" style="font-size:28px">Requires BepInEx 5 and a Wooting analog keyboard</text>
  <text x="960" y="862" text-anchor="middle" class="mono" style="font-size:24px;fill:{mm.MUTED}">github.com/xamspanda/dressmaker-analog-sewing</text>
"""
    return mm.svg(W, H, body)


def caption_png(text, path):
    """Transparent full-frame PNG with a caption panel in the bottom-left corner."""
    ss = 2
    f = font(46 * ss, 800)
    # Sits above the game's control hints, which run along the bottom-left edge.
    pad_x, pad_y, margin, bottom = 44 * ss, 30 * ss, 40 * ss, 96 * ss
    tw = f.getbbox(text)[2]
    pw, ph = tw + 2 * pad_x, 46 * ss + 2 * pad_y + 18 * ss
    img = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y1 = margin, H * ss - bottom
    y0 = y1 - ph
    d.rounded_rectangle([x0, y0, x0 + pw, y1], radius=24 * ss, fill=PANEL, outline=BORDER, width=2 * ss)
    d.text((x0 + pad_x, y0 + pad_y - 6 * ss), text, font=f, fill=CREAM)
    # a row of stitches under the text
    sy = y1 - pad_y + 2 * ss
    x = x0 + pad_x
    while x + 18 * ss < x0 + pad_x + tw:
        d.rounded_rectangle([x, sy, x + 18 * ss, sy + 5 * ss], radius=3 * ss, fill=ROSE)
        x += 30 * ss
    img.resize((W, H), Image.LANCZOS).save(path)


def cuts_within(src, start, end):
    """Times of camera cuts inside [start, end] of the source, via ffmpeg scene detection."""
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{start}", "-t", f"{end - start}", "-i", src, "-an",
         "-vf", "fps=30,scale=480:-1,select='gt(scene,0.25)',showinfo", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    return [start + float(part.split()[0]) for part in out.split("pts_time:")[1:]]


def run(cmd):
    subprocess.run(cmd, check=True)


ENC = ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def clip(src, start, end, caption, out, tmp):
    dur = end - start
    inputs = ["-ss", f"{start}", "-t", f"{dur}", "-i", src]
    if caption:
        png = os.path.join(tmp, f"cap-{abs(hash(caption))}.png")
        caption_png(caption, png)
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", png]
        vf = (f"[0:v]fps={FPS},scale={W}:{H},{HIDE_FPS}[base];"
              f"[1:v]format=rgba,fade=t=in:st={FADE}:d=0.4:alpha=1,fade=t=out:st={dur - FADE - 0.4}:d=0.4:alpha=1[cap];"
              f"[base][cap]overlay=0:0:shortest=1[v]")
    else:
        vf = f"[0:v]fps={FPS},scale={W}:{H},{HIDE_FPS}[v]"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", vf,
         "-map", "[v]", "-map", GAME_AUDIO, *ENC, out])


def still(png, dur, out):
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{dur}", "-i", png,
         "-f", "lavfi", "-t", f"{dur}", "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", f"fps={FPS},scale={W}:{H},format=yuv420p", "-map", "0:v", "-map", "1:a", *ENC, out])


def join(parts, durations, out, fade_in=True):
    """Crossfade all parts together (video and audio)."""
    inputs = sum((["-i", p] for p in parts), [])
    fv, fa, offset = [], [], 0.0
    v, a = "[0:v]", "[0:a]"
    for i in range(1, len(parts)):
        offset += durations[i - 1] - FADE
        fv.append(f"{v}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[v{i}]")
        fa.append(f"{a}[{i}:a]acrossfade=d={FADE}[a{i}]")
        v, a = f"[v{i}]", f"[a{i}]"
    last = len(parts) - 1
    total = sum(durations) - FADE * last
    fades = (["fade=t=in:st=0:d=0.6"] if fade_in else []) + [f"fade=t=out:st={total - 0.8:.3f}:d=0.8"]
    graph = ";".join(fv + fa) + f";{v}{','.join(fades)}[vout]"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph,
         "-map", "[vout]", "-map", a, *ENC, "-movflags", "+faststart", out])
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", required=True, help="the '(gauge).mp4' recording")
    p.add_argument("--output", default=os.path.join(HERE, "out", "analog-sewing-showcase.mp4"))
    p.add_argument("--no-title", action="store_true", help="start straight on gameplay: no title card or fade-in")
    args = p.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # A cut inside a clip shows up as a flash of another scene, worse when crossfaded.
    bad = [(start, end, t) for start, end, _ in CLIPS for t in cuts_within(args.video, start, end)]
    if bad:
        sys.exit("Camera cuts inside clips; adjust CLIPS:\n" + "\n".join(f"  {s}-{e}: cut at {t:.2f}" for s, e, t in bad))

    with tempfile.TemporaryDirectory() as tmp:
        parts, durs = [], []
        for name, make, dur in (("title", title_card, TITLE_S), ("end", end_card, END_S)):
            svg_path = os.path.join(tmp, f"{name}.svg")
            with open(svg_path, "w") as f:
                f.write(make())
            mm.render(pathlib_path(svg_path), os.path.join(tmp, f"{name}.png"), W, H)

        if not args.no_title:
            still(os.path.join(tmp, "title.png"), TITLE_S, os.path.join(tmp, "00-title.mp4"))
            parts.append(os.path.join(tmp, "00-title.mp4")); durs.append(TITLE_S)
        for i, (start, end, caption) in enumerate(CLIPS, 1):
            out = os.path.join(tmp, f"{i:02d}-clip.mp4")
            print(f"Clip {i}/{len(CLIPS)}: {caption or 'finished dress'}", file=sys.stderr)
            clip(args.video, start, end, caption, out, tmp)
            parts.append(out); durs.append(end - start)
        still(os.path.join(tmp, "end.png"), END_S, os.path.join(tmp, "99-end.mp4"))
        parts.append(os.path.join(tmp, "99-end.mp4")); durs.append(END_S)

        total = join(parts, durs, args.output, fade_in=not args.no_title)
    print(f"Wrote {args.output} ({total:.1f}s)", file=sys.stderr)


def pathlib_path(p):
    import pathlib
    return pathlib.Path(p)


if __name__ == "__main__":
    main()
