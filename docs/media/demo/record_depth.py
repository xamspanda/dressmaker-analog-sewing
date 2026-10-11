"""Read a key's analog depth straight from a Wooting keyboard's HID interface (Linux)."""
import glob
import os
import sys

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
