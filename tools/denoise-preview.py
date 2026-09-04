#!/usr/bin/env python3
"""Run the add-on's broadcast cleanup over a WAV so you can judge it by ear.

The cleanup lives in the add-on and only touches audio on its way out to the
speakers, which makes it awkward to evaluate: the WAVs mic-capture.py writes are
raw by design, and the copies the add-on retains are raw too. This applies the
same code path offline and writes a `-clean` sibling to A/B against.

Usage:
    python3 tools/denoise-preview.py tools/mic-06.wav        # -> mic-06-clean.wav
    python3 tools/denoise-preview.py tools/*.wav             # batch

The numbers printed are the same ones mic-capture.py reports, before and after,
so a change is judged the same way the mic itself was characterised. The one to
watch is SNR: the cleanup should raise it. Device-side gain never could.
"""
import math
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "intercom-addon"))
import denoise  # noqa: E402


def measure(pcm, rate):
    n = len(pcm) // 2
    if n == 0:
        return None
    s = struct.unpack("<%dh" % n, pcm[: n * 2])
    win = rate // 4
    levels = sorted(
        sum(abs(x) for x in s[i : i + win]) / win
        for i in range(0, max(n - win, 1), win)
    ) or [0]
    return {
        "peak": max(abs(x) for x in s),
        "mean": sum(abs(x) for x in s) / n,
        "dc": sum(s) / n,
        "floor": levels[0],
        "loud": levels[-1],
        "snr": 20 * math.log10(levels[-1] / levels[0]) if levels[0] > 0 else float("inf"),
        "clip": 100 * sum(1 for x in s if abs(x) >= 32700) / n,
        "cross": sum(1 for a, b in zip(s, s[1:]) if (a < 0) != (b < 0)) / (n / rate),
    }


def row(label, m):
    return (f"  {label:<10} peak {m['peak']:>6}  mean {m['mean']:>5.0f}  dc {m['dc']:>5.0f}  "
            f"floor {m['floor']:>5.0f}  loud {m['loud']:>5.0f}  "
            f"SNR {m['snr']:>5.1f}  cross {m['cross']:>5.0f}/s  clip {m['clip']:.2f}%")


def main(paths):
    for arg in paths:
        src = Path(arg)
        if src.stem.endswith("-clean"):
            continue          # don't process our own output
        with wave.open(str(src), "rb") as w:
            if w.getsampwidth() != 2 or w.getnchannels() != 1:
                print(f"{src.name}: skipped (need 16-bit mono)")
                continue
            rate = w.getframerate()
            raw = w.readframes(w.getnframes())

        clean = denoise.process(raw, sample_rate=rate)
        before, after = measure(raw, rate), measure(clean, rate)
        if before is None:
            print(f"{src.name}: empty")
            continue

        out = src.with_name(src.stem + "-clean.wav")
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(clean)

        print(f"\n{src.name}  ({len(raw)//2} samples, {len(raw)/2/rate:.2f}s)")
        print(row("raw", before))
        print(row("clean", after))
        delta = after["snr"] - before["snr"]
        print(f"  {'->':<10} SNR {delta:+.1f} dB   floor x{after['floor']/max(before['floor'],1e-9):.2f}   "
              f"speech x{after['loud']/max(before['loud'],1e-9):.2f}   wrote {out.name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
