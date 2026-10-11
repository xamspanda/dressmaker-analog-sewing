#!/usr/bin/env python3
"""Log the sew key's depth while OBS records, then add the key gauge to the recording.

    python3 docs/media/demo/obs_record.py

Leave this running, then start and stop recording in OBS as usual (as many times as you like).
For each recording it logs Space's analog depth straight from the Wooting keyboard (nothing is
drawn on screen, so the game keeps focus) and, when the recording stops, runs composite.py to
write "<recording> (gauge).mp4" next to it. Needs OBS's WebSocket server enabled
(Tools > WebSocket Server Settings); the password is read from OBS's own config. Linux only.
"""
import base64
import hashlib
import json
import os
import select
import socket
import struct
import subprocess
import sys
import threading
import time

from record_depth import find_analog_hidraw, read_depth, SPACE

HERE = os.path.dirname(os.path.abspath(__file__))
OBS_CONFIG = os.path.expanduser("~/.config/obs-studio/plugin_config/obs-websocket/config.json")
EVENT_SUB_OUTPUTS = 1 << 6


class WebSocket:
    """Just enough of RFC 6455 for a local obs-websocket connection: text frames, ping/pong."""

    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port))
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET / HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                           f"Sec-WebSocket-Protocol: obswebsocket.json\r\n\r\n").encode())
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("OBS closed the connection during the handshake")
            response += chunk
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise ConnectionError(response.split(b"\r\n", 1)[0].decode())
        self.buf = response.split(b"\r\n\r\n", 1)[1]

    def _send(self, opcode, payload):
        mask = os.urandom(4)
        n = len(payload)
        head = bytes([0x80 | opcode])
        head += bytes([0x80 | n]) if n < 126 else (bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536
                                                    else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send(self, obj):
        self._send(0x1, json.dumps(obj).encode())

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("OBS closed the connection")
            self.buf += chunk
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def recv(self):
        message = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            opcode = b0 & 0x0F
            if opcode == 0x9:
                self._send(0xA, payload)
            elif opcode == 0x8:
                raise ConnectionError("OBS closed the connection")
            elif opcode in (0x0, 0x1):
                message += payload
                if b0 & 0x80:
                    return json.loads(message)


def connect():
    try:
        with open(OBS_CONFIG) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        sys.exit("OBS WebSocket config not found; enable it in OBS under Tools > WebSocket Server Settings")
    if not cfg.get("server_enabled"):
        sys.exit("Enable OBS's WebSocket server (Tools > WebSocket Server Settings)")
    try:
        ws = WebSocket(cfg.get("server_port", 4455))
    except OSError as e:
        sys.exit(f"Could not connect to OBS ({e}); is OBS running?")

    hello = ws.recv()["d"]
    identify = {"rpcVersion": 1, "eventSubscriptions": EVENT_SUB_OUTPUTS}
    if "authentication" in hello:
        auth = hello["authentication"]
        secret = base64.b64encode(hashlib.sha256((cfg["server_password"] + auth["salt"]).encode()).digest())
        identify["authentication"] = base64.b64encode(hashlib.sha256(secret + auth["challenge"].encode()).digest()).decode()
    ws.send({"op": 1, "d": identify})
    if ws.recv().get("op") != 2:
        sys.exit("OBS rejected the connection (check the WebSocket password)")
    return ws


class DepthLogger:
    """Logs (seconds since start, depth) for the sew key on a background thread."""

    def __init__(self, path):
        self.path = path
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        dev, stride = find_analog_hidraw()
        fd = os.open(dev, os.O_RDONLY)
        t0 = time.monotonic()
        depth = 0.0
        with open(self.path, "w") as out:
            out.write("t,depth\n")
            while self.running:
                ready, _, _ = select.select([fd], [], [], 0.01)
                if ready:
                    depth = read_depth(os.read(fd, 128), SPACE, stride)
                out.write(f"{time.monotonic() - t0:.4f},{depth:.4f}\n")
        os.close(fd)

    def stop(self):
        self.running = False
        self.thread.join()


def main():
    ws = connect()
    find_analog_hidraw()  # fail now, not mid-recording, if the keyboard isn't there
    print("Connected to OBS. Start recording in OBS whenever you're ready (Ctrl+C here to quit).", file=sys.stderr)
    log_dir = os.path.join(HERE, "out")
    os.makedirs(log_dir, exist_ok=True)
    logger = None
    log_path = None
    while True:
        msg = ws.recv()
        if msg.get("op") != 5 or msg["d"].get("eventType") != "RecordStateChanged":
            continue
        state = msg["d"]["eventData"]["outputState"]
        if state == "OBS_WEBSOCKET_OUTPUT_STARTED" and logger is None:
            log_path = os.path.join(log_dir, time.strftime("depth-%Y%m%d-%H%M%S.csv"))
            logger = DepthLogger(log_path)
            print("Recording: logging key depth...", file=sys.stderr)
        elif state == "OBS_WEBSOCKET_OUTPUT_STOPPED" and logger is not None:
            logger.stop()
            logger = None
            video = msg["d"]["eventData"].get("outputPath")
            if not video:
                print(f"OBS didn't report the file; run composite.py --video <file> --log {log_path}", file=sys.stderr)
                continue
            out = os.path.splitext(video)[0] + " (gauge).mp4"
            print(f"Stopped. Adding the gauge to {video}", file=sys.stderr)
            subprocess.run([sys.executable, os.path.join(HERE, "composite.py"),
                            "--video", video, "--log", log_path, "--output", out])
            print("Ready for the next recording.", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
