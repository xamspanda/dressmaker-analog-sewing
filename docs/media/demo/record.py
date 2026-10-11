#!/usr/bin/env python3
"""Record a demo clip: the game's monitor (with audio) plus a log of the sew key's depth.

    python3 docs/media/demo/record.py --seconds 40

After a countdown (switch to the game during it), records the monitor with gpu-screen-recorder
while reading Space's analog depth straight from the Wooting keyboard's HID interface, so
nothing on screen changes and the game keeps focus. Writes <out>/raw.mp4 and <out>/depth.csv;
then run composite.py to add the on-screen key gauge. Linux only.
"""
import argparse
import glob
import json
import os
import select
import signal
import subprocess
import sys
import time

WOOTING_VID = "31E3"
# Usage page at the start of the report descriptor -> bytes per key entry (see read_depth).
ANALOG_PAGES = {bytes([0x06, 0x54, 0xFF]): 3, bytes([0x06, 0x53, 0xFF]): 4}
SPACE = 0x2C


def find_analog_hidraw():
    for node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            if f":{WOOTING_VID}:" not in os.path.realpath(os.path.join(node, "device")).upper():
                continue
            with open(os.path.join(node, "device/report_descriptor"), "rb") as f:
                stride = ANALOG_PAGES.get(f.read(3))
            if stride:
                return "/dev/" + os.path.basename(node), stride
        except OSError:
            pass
    sys.exit("Wooting analog interface not found")


def read_depth(report, usage, stride):
    """Depth 0..1 of `usage` in an analog report, which lists only the keys currently pressed.

    0xFF54 (older firmware): [HID usage u16 BE][depth u8]
    0xFF53 (firmware 2.50+): [key id][HID usage][depth low 2 bits << 6 | flags][depth high 8 bits]
    """
    for i in range(0, len(report) - stride + 1, stride):
        if report[i] == 0 and report[i + 1] == 0:
            break
        if stride == 3 and (report[i] << 8 | report[i + 1]) == usage:
            return report[i + 2] / 255.0
        if stride == 4 and report[i + 1] == usage:
            return ((report[i + 3] << 2) | (report[i + 2] >> 6)) / 1023.0
    return 0.0


def game_monitor():
    """Name of the monitor showing the Dressmaker window, if it's open."""
    clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"]))
    monitors = {m["id"]: m["name"] for m in json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"]))}
    for c in clients:
        if c["title"].strip() == "Dressmaker" or "dressmaker.exe" in c["class"].lower():
            return monitors.get(c["monitor"])
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seconds", type=float, default=40, help="clip length (default 40)")
    p.add_argument("--countdown", type=int, default=5, help="seconds to switch to the game (default 5)")
    p.add_argument("--monitor", help="monitor to record (default: the one showing Dressmaker)")
    p.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    args = p.parse_args()

    monitor = args.monitor or game_monitor()
    if not monitor:
        sys.exit("Dressmaker window not found; start the game or pass --monitor (e.g. DP-2)")
    path, stride = find_analog_hidraw()
    os.makedirs(args.out, exist_ok=True)
    raw, log = os.path.join(args.out, "raw.mp4"), os.path.join(args.out, "depth.csv")

    for n in range(args.countdown, 0, -1):
        print(f"Recording {monitor} in {n}... switch to the game now", file=sys.stderr)
        time.sleep(1)

    fd = os.open(path, os.O_RDONLY)
    rec = subprocess.Popen(
        ["gpu-screen-recorder", "-w", monitor, "-f", "60", "-fm", "cfr", "-k", "h264",
         "-a", "default_output", "-ac", "aac", "-cursor", "no", "-o", raw],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    t0 = time.monotonic()
    depth = 0.0
    print(f"Recording for {args.seconds:.0f}s", file=sys.stderr)
    with open(log, "w") as out:
        out.write("t,depth\n")
        while (now := time.monotonic()) - t0 < args.seconds:
            if rec.poll() is not None:
                sys.exit(f"gpu-screen-recorder exited early:\n{rec.stderr.read().decode()}")
            ready, _, _ = select.select([fd], [], [], 0.01)
            if ready:
                depth = read_depth(os.read(fd, 128), SPACE, stride)
            out.write(f"{now - t0:.4f},{depth:.4f}\n")

    rec.send_signal(signal.SIGINT)  # lets the recorder finish writing the file
    rec.wait(timeout=30)
    os.close(fd)
    print(f"Wrote {raw} and {log}", file=sys.stderr)


if __name__ == "__main__":
    main()
