#!/usr/bin/env python3
"""Generate the wake-word chime played on-device.

    python3 tools/make-chime.py            # writes sounds/chime.wav

Two ascending sine tones with soft attacks, 48 kHz / 16-bit / stereo so it
matches the announcement pipeline exactly and needs no resampling on the device.

The shape is deliberate. The file opens with 60 ms of silence and each tone
fades in over 12 ms, because the first fraction of a second of any sound this
device plays is spent starting the I2S driver and un-muting the DAC. Anything
audible at t=0 is lost — which is exactly the bug this chime works around, so
the chime must not have the same flaw itself.

Keep it quiet (0.22 full scale). It is feedback, not an announcement, and it is
played while the microphone is about to start listening.
"""
import math
import struct
import wave
from pathlib import Path

RATE = 48000
LEAD_SILENCE = 0.060  # s — expendable head, see above
ATTACK = 0.012  # s — no clicks, and nothing lost if the very start is clipped
AMPLITUDE = 0.22
OUT = Path(__file__).resolve().parent.parent / "sounds" / "chime.wav"

# (frequency Hz, start s, duration s) — a rising two-note ding
NOTES = [
    (880.00, LEAD_SILENCE, 0.150),  # A5
    (1318.51, LEAD_SILENCE + 0.110, 0.240),  # E6, overlapping the first
]


def render():
    total = max(start + dur for _, start, dur in NOTES)
    n = int(total * RATE)
    buf = [0.0] * n

    for freq, start, dur in NOTES:
        i0 = int(start * RATE)
        length = int(dur * RATE)
        for i in range(length):
            if i0 + i >= n:
                break
            t = i / RATE
            # Exponential decay, plus a quiet octave partial for a bell-ish tone.
            env = math.exp(-t * 7.0)
            if t < ATTACK:
                env *= t / ATTACK
            sample = math.sin(2 * math.pi * freq * t)
            sample += 0.25 * math.sin(2 * math.pi * freq * 2 * t)
            buf[i0 + i] += sample * env

    peak = max(abs(v) for v in buf) or 1.0
    scale = AMPLITUDE / peak
    frames = bytearray()
    for v in buf:
        s = int(max(-1.0, min(1.0, v * scale)) * 32767)
        frames += struct.pack("<hh", s, s)  # same signal both channels
    return bytes(frames), n


def main():
    frames, n = render()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    print(f"wrote {OUT}")
    print(f"  {n / RATE:.3f} s, {RATE} Hz, stereo 16-bit, {len(frames) + 44} bytes")


if __name__ == "__main__":
    main()
