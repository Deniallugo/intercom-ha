#!/usr/bin/env python3
"""Catch a chunked PCM upload from a device and write it to a WAV file.

A bench tool for debugging a microphone: stands in for the /intercom endpoint of
intercom-addon (it speaks enough of it for include/uploader.h), writes the raw
PCM to a WAV you can listen to, and prints the statistics that distinguish real
audio from wiring faults.

Usage:
    python3 tools/mic-capture.py                    # listens on 0.0.0.0:9999

Then point the device at this machine and trigger a recording:
    1. in devices/<device>.yaml set
           intercom_url: "http://<this-machine-ip>:9999/intercom"
    2. flash, then press the device's "Mic test recording" button in Home
       Assistant (or hold the PTT button)
    3. WAVs land next to this script as mic-01.wav, mic-02.wav, ...

Reading the output — the decisive number is zero-crossings per second, which
this prints indirectly via the verdict:
    * speech produces hundreds to thousands of sign changes per second
    * under ~50/s is not sound at all, no matter how large the level looks
    * "impossible jumps" counts neighbouring samples differing by >16000, which
      audio at 16 kHz cannot do — a non-zero count means bit errors on the wire
"""
import math
import socket
import struct
import sys
import wave
from pathlib import Path

HOST, PORT = "0.0.0.0", 9999
RATE, WIDTH, CHANNELS = 16000, 2, 1
OUTDIR = Path(__file__).parent


def read_headers(conn):
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(1)
        if not chunk:
            return None, b""
        buf += chunk
    head, _, rest = buf.partition(b"\r\n\r\n")
    return head.decode("latin-1"), rest


def read_chunked(conn, rest):
    """Dechunk the body, returning raw PCM bytes."""
    body = bytearray()
    buf = bytearray(rest)

    def fill(n):
        while len(buf) < n:
            data = conn.recv(65536)
            if not data:
                return False
            buf.extend(data)
        return True

    while True:
        # chunk size line
        while b"\r\n" not in buf:
            if not fill(len(buf) + 1):
                return bytes(body)
        line, _, remainder = bytes(buf).partition(b"\r\n")
        buf = bytearray(remainder)
        try:
            size = int(line.strip().split(b";")[0], 16)
        except ValueError:
            return bytes(body)
        if size == 0:
            return bytes(body)
        if not fill(size + 2):
            return bytes(body)
        body.extend(buf[:size])
        del buf[: size + 2]  # payload + trailing CRLF


def report(pcm, path):
    n = len(pcm) // 2
    if n == 0:
        print("  !! empty upload")
        return
    samples = struct.unpack("<%dh" % n, pcm[: n * 2])
    peak = max(abs(s) for s in samples)
    mean = sum(abs(s) for s in samples) / n
    dc = sum(samples) / n
    clipped = sum(1 for s in samples if abs(s) >= 32700)
    # A glitch is a jump between neighbours too large to be sound at 16 kHz.
    jumps = sum(1 for a, b in zip(samples, samples[1:]) if abs(b - a) > 16000)
    # The decisive statistic: speech crosses zero hundreds of times a second.
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0) != (b < 0))
    per_sec = crossings / (n / RATE)
    # Quietest vs loudest quarter-second = a crude but honest SNR.
    win = RATE // 4
    levels = sorted(
        sum(abs(s) for s in samples[i : i + win]) / win
        for i in range(0, max(n - win, 1), win)
    ) or [0]

    print(f"  wrote {path}  ({n} samples = {n / RATE:.2f} s)")
    print(f"  peak {peak}  mean {mean:.0f}  dc {dc:.0f}")
    print(f"  clipped {100 * clipped / n:.2f}%   impossible jumps {jumps}")
    print(f"  zero crossings {per_sec:.0f}/s")
    if levels[0] > 0:
        print(f"  noise floor {levels[0]:.0f}  loudest {levels[-1]:.0f}"
              f"  SNR ~{20 * math.log10(levels[-1] / levels[0]):.0f} dB")

    if mean == 0:
        print("  --> SILENT: nothing arriving. Dead wire, or mic not clocked.")
    elif jumps > n * 0.001:
        print("  --> GLITCHING: bit errors on the wire, not audio.")
    elif per_sec < 50:
        print("  --> NOT AUDIO: sub-audio wander. Check gain and DC handling.")
    elif clipped > n * 0.01:
        print("  --> CLIPPING: reduce gain_factor / the shift in the callback.")
    else:
        print("  --> looks like real audio.")


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(4)
    print(f"listening on {HOST}:{PORT} — hold the button on voice-s3 and speak")
    count = 0
    while True:
        conn, addr = srv.accept()
        try:
            head, rest = read_headers(conn)
            if head is None:
                continue
            device = ""
            for line in head.split("\r\n"):
                if line.lower().startswith("x-device-name:"):
                    device = line.split(":", 1)[1].strip()
            print(f"\n[{addr[0]}] upload from {device or '?'}")
            pcm = read_chunked(conn, rest)
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n"
                         b"Connection: close\r\n\r\nok")
            count += 1
            path = OUTDIR / f"mic-{count:02d}.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(CHANNELS)
                w.setsampwidth(WIDTH)
                w.setframerate(RATE)
                w.writeframes(pcm)
            report(pcm, path)
        except Exception as exc:  # keep serving after a bad upload
            print(f"  error: {exc}")
        finally:
            conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
