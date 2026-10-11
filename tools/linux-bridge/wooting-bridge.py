#!/usr/bin/env python3
"""Stream one Wooting key's analog depth to the Dressmaker Analog Sewing mod.

Fallback for Linux/Proton setups where the mod's built-in Wooting SDK cannot
see the keyboard; the mod uses it automatically when it is running.

Reads the keyboard's analog HID interface directly, so no Wooting SDK is
needed, and sends the depth (0..1) as UDP text to 127.0.0.1. Each analog report
lists the keys currently pressed; a key missing from a report is up.

  Older firmware, usage page 0xFF54: 3-byte entries
      [HID usage u16 BE] [depth u8]
  Firmware 2.50+, usage page 0xFF53: 4-byte entries
      [key id u8] [HID usage u8] [depth low 2 bits << 6 | actuated bit] [depth high 8 bits]
"""
import argparse
import glob
import os
import select
import socket
import sys
import time

WOOTING_VID = "31E3"
# First item of the interface's report descriptor (usage page) -> entry size in bytes.
ANALOG_PAGES = {bytes([0x06, 0x54, 0xFF]): 3, bytes([0x06, 0x53, 0xFF]): 4}
KEYS = {"space": 0x2C, "lshift": 0xE1, "lctrl": 0xE0, "lalt": 0xE2, "capslock": 0x39, "tab": 0x2B, "f": 0x09}
HEARTBEAT = 0.02


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
    return None, None


def read_key(report, usage, stride):
    """Return (depth 0..1, actuated) for the key; actuated is None if the format lacks it."""
    for i in range(0, len(report) - stride + 1, stride):
        if report[i] == 0 and report[i + 1] == 0:
            break
        if stride == 3 and (report[i] << 8 | report[i + 1]) == usage:
            return report[i + 2] / 255.0, None
        if stride == 4 and report[i + 1] == usage:
            return ((report[i + 3] << 2) | (report[i + 2] >> 6)) / 1023.0, bool(report[i + 2] & 1)
    return 0.0, False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--key", default="space", help=f"key name ({', '.join(KEYS)}) or HID usage like 0x2C (default: space)")
    p.add_argument("--port", type=int, default=47613)
    p.add_argument("--show", action="store_true", help="print a live depth meter")
    p.add_argument("--debug", action="store_true", help="log each time the keyboard reports the key pressed/released")
    args = p.parse_args()
    usage = KEYS[args.key.lower()] if args.key.lower() in KEYS else int(args.key, 0)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = ("127.0.0.1", args.port)
    depth = 0.0
    actuated = False
    t0 = time.monotonic()

    while True:
        path, stride = find_analog_hidraw()
        if not path:
            print("Wooting analog interface not found; retrying...", file=sys.stderr)
            time.sleep(2)
            continue
        try:
            fd = os.open(path, os.O_RDONLY)
        except PermissionError:
            sys.exit(f"No permission to read {path}; check the Wooting udev rules (uaccess).")
        print(f"Reading {path} ({stride}-byte entries), key 0x{usage:02X}, sending to {target[0]}:{target[1]}", file=sys.stderr)
        try:
            while True:
                ready, _, _ = select.select([fd], [], [], HEARTBEAT)
                if ready:
                    depth, now_actuated = read_key(os.read(fd, 128), usage, stride)
                    if args.debug and now_actuated is not None and now_actuated != actuated:
                        state = "PRESSED " if now_actuated else "released"
                        print(f"\r{time.monotonic() - t0:7.2f}s keyboard says {state} at depth {depth:.2f}", file=sys.stderr)
                    actuated = bool(now_actuated)
                sock.sendto(f"{depth:.4f}".encode(), target)
                if args.show:
                    bar = "#" * round(depth * 40)
                    print(f"\r{depth:5.2f} [{bar:<40}]", end="", file=sys.stderr, flush=True)
        except OSError as e:
            print(f"\nLost {path} ({e}); reconnecting...", file=sys.stderr)
            depth = 0.0
            os.close(fd)
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
