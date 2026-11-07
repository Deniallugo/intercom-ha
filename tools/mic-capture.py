#!/usr/bin/env python3
"""Catch a chunked PCM upload from a device and write it to a WAV file.

A bench tool for debugging a microphone: stands in for the /intercom endpoint of
intercom-addon (it speaks enough of it for include/uploader.h), writes the raw
PCM to a WAV you can listen to, and prints the statistics that distinguish real
audio from wiring faults.

Usage:
    python3 tools/mic-capture.py                    # listens on 0.0.0.0:9999

Then point the device's mic test at this machine and trigger a recording:
    1. in devices/<device>.yaml set
           mic_test_url: "http://<this-machine-ip>:9999/intercom"
       (by default it points at the add-on, which keeps the test in its panel
       and also plays it on the speakers; PTT broadcasts use ${intercom_url}
       and keep going to the add-on either way)
    2. flash, then press the device's "Mic test recording" button in Home
       Assistant — it records 5 s with Wi-Fi quiet, then uploads
    3. WAVs land next to this script as mic-<device>-01.wav, -02, ... (never
       overwriting an earlier capture)

Reading the output — the decisive number is zero-crossings per second, printed
as "zero crossings N/s" and summed up in the verdict:
    * speech produces hundreds to thousands of sign changes per second
    * under ~50/s is not sound at all, no matter how large the level looks
    * "isolated spikes" counts single samples that jump away from both their
      neighbours; when most of them land on a power of two (512, 1024, 16384)
      they are flipped bits in the I2S word, not sound
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


def bit_error_stats(samples):
    """(isolated single-sample spikes, how many of them are a power of two).

    A flipped bit in the I2S word moves ONE sample by exactly 2^k and leaves its
    neighbours untouched, so it stands out against the local baseline at a
    power-of-two magnitude. Real audio's local deviations are smoothly
    distributed and do not pile up on 512 / 1024 / 16384, so the second number
    is what separates a wiring fault from loud speech.

    Measured here: healthy captures give 0.00-0.07% spikes with few on a power
    of two; a failing mic gave 3.5-12.6% with 81-91% of them on one.

    This replaces a fixed "neighbour delta > 16000" test that was wrong in both
    directions — it called any loud capture glitchy, since a real speech
    transient clears 16000 easily, and it missed bit errors riding on a large
    baseline, where the flipped bit is big but the absolute delta is not.
    """
    n = len(samples)
    if n < 3:
        return 0, 0
    # Deviation from the mean of both neighbours: an isolated spike survives,
    # slow baseline wander cancels.
    dev = [samples[i] - (samples[i - 1] + samples[i + 1]) / 2 for i in range(1, n - 1)]
    typical = sorted(abs(d) for d in dev)[len(dev) // 2]
    spikes = [abs(d) for d in dev if abs(d) > max(20 * typical, 40)]
    on_power = sum(1 for a in spikes if abs(a - 2 ** round(math.log2(a))) / a < 0.12)
    return len(spikes), on_power


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
    spikes, on_power = bit_error_stats(samples)
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
    print(f"  clipped {100 * clipped / n:.2f}%   "
          f"isolated spikes {100 * spikes / n:.2f}% "
          f"({on_power} of {spikes} on a power of two)")
    print(f"  zero crossings {per_sec:.0f}/s")
    if levels[0] > 0:
        print(f"  noise floor {levels[0]:.0f}  loudest {levels[-1]:.0f}"
              f"  SNR ~{20 * math.log10(levels[-1] / levels[0]):.0f} dB")

    if mean == 0:
        print("  --> SILENT: nothing arriving. Dead wire, or mic not clocked.")
    elif spikes > n * 0.005 and on_power > spikes * 0.5:
        print("  --> BIT ERRORS on the I2S data word, not audio. Check SD/SCK/WS")
        print("      wiring and the L/R tie — this is not a gain problem, and the")
        print("      inflated level and noise floor are the errors themselves.")
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
    print(f"listening on {HOST}:{PORT} — press 'Mic test recording' on a device and speak")
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
            # Name by device and never overwrite: earlier captures are the
            # baseline a new one is compared against.
            tag = "".join(c if c.isalnum() or c == "-" else "_" for c in device) or "unknown"
            count = 1
            while (path := OUTDIR / f"mic-{tag}-{count:02d}.wav").exists():
                count += 1
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
