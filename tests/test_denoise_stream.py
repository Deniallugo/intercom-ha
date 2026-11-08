"""denoise.Stream: fed piecewise as an upload arrives, it must give exactly
what the original whole-message denoise gave (tests/denoise_reference.py)."""
import array
import math
import os
import random
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "intercom-addon"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import denoise  # noqa: E402
import denoise_reference as ref  # noqa: E402


def pcm(samples) -> bytes:
    return array.array("h", [max(-32768, min(32767, int(s))) for s in samples]).tobytes()


def hiss_and_bursts(seconds, rate, *, level=1600, noise=180, seed=1, dc=0):
    """Hiss plus syllable-like harmonic bursts, ~60% duty."""
    rnd = random.Random(seed)
    out = []
    for i in range(int(seconds * rate)):
        t = i / rate
        syl = (t * 4.0) % 1.0
        env = math.sin(math.pi * syl / 0.6) if syl < 0.6 else 0.0
        f0 = 140 + 30 * math.sin(2 * math.pi * 0.5 * t)
        v = sum(math.sin(2 * math.pi * f0 * k * t) / k for k in (1, 2, 3, 4))
        out.append(dc + rnd.gauss(0, noise) + level * env * v)
    return pcm(out)


SYNTHETIC = {
    "speech-16k": (hiss_and_bursts(3.0, 16000), 16000),
    "loud-clipping-16k": (hiss_and_bursts(1.5, 16000, level=12000, seed=2), 16000),
    "dc-offset-22k": (hiss_and_bursts(1.0, 22050, dc=900, seed=3), 22050),
    "speech-48k": (hiss_and_bursts(1.0, 48000, seed=4), 48000),
    "silence": (b"\x00\x00" * 8000, 16000),
    "hiss-only": (pcm(random.Random(5).gauss(0, 40) for _ in range(9000)), 16000),
    "odd-length": (hiss_and_bursts(0.5, 16000, seed=6) + b"\x07", 16000),
    "shorter-than-a-frame": (hiss_and_bursts(0.01, 16000, seed=7), 16000),
    "two-samples": (b"\x10\x00\xf0\xff", 16000),
    "three-bytes": (b"\x10\x00\xf0", 16000),
    "one-sample": (b"\x10\x00", 16000),
    "empty": (b"", 16000),
}


def real_captures() -> list:
    """Mic captures (tools/mic-*.wav, gitignored), or a dir in
    INTERCOM_MIC_WAVS. Absent in CI: the synthetic cases still run."""
    dirs = [ROOT / "tools"]
    if os.environ.get("INTERCOM_MIC_WAVS"):
        dirs.insert(0, Path(os.environ["INTERCOM_MIC_WAVS"]))
    found = []
    for d in dirs:
        found += sorted(d.glob("mic-*.wav"))[:: 1 if os.environ.get("INTERCOM_MIC_ALL") else 4]
    return found


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1
        return w.readframes(w.getnframes()), w.getframerate()


def chunked(data: bytes, rnd: random.Random, *, lo=1, hi=5000):
    """`data` cut at random places, odd sizes included."""
    i = 0
    while i < len(data):
        n = rnd.randint(lo, hi)
        yield data[i:i + n]
        i += n


def streamed(data: bytes, rate: int, *, full: bool, seed: int) -> bytes:
    s = denoise.Stream(sample_rate=rate, full=full)
    for piece in chunked(data, random.Random(seed)):
        s.feed(piece)
    return s.finish()


@pytest.mark.parametrize("name", list(SYNTHETIC))
def test_process_matches_the_original_bit_for_bit(name):
    data, rate = SYNTHETIC[name]
    want = ref.process(data, sample_rate=rate)
    assert denoise.process(data, sample_rate=rate) == want
    for seed in range(3):
        assert streamed(data, rate, full=True, seed=seed) == want


@pytest.mark.parametrize("name", list(SYNTHETIC))
def test_level_matches_the_original_bit_for_bit(name):
    data, rate = SYNTHETIC[name]
    want = ref.level(data, sample_rate=rate)
    assert denoise.level(data, sample_rate=rate) == want
    assert streamed(data, rate, full=False, seed=0) == want


def test_one_byte_at_a_time():
    data, rate = hiss_and_bursts(0.2, 16000, seed=9), 16000
    s = denoise.Stream(sample_rate=rate)
    for i in range(len(data)):
        s.feed(data[i:i + 1])
    assert s.finish() == ref.process(data, sample_rate=rate)


def test_chunks_on_frame_boundaries():
    """Pieces that end exactly where a band or expander frame does."""
    data, rate = hiss_and_bursts(1.0, 16000, seed=10), 16000
    want = ref.process(data, sample_rate=rate)
    for frame_ms in (denoise.BAND_FRAME_MS, denoise.FRAME_MS):
        step = int(rate * frame_ms / 1000) * 2
        s = denoise.Stream(sample_rate=rate)
        for i in range(0, len(data), step):
            s.feed(data[i:i + step])
        assert s.finish() == want


CAPTURES = real_captures()


@pytest.mark.skipif(not CAPTURES, reason="no mic captures in tools/ "
                    "(tools/mic-capture.py, or INTERCOM_MIC_WAVS=<dir>)")
@pytest.mark.parametrize("path", CAPTURES, ids=lambda p: p.name)
def test_real_captures_match_bit_for_bit(path):
    data, rate = read_wav(path)
    want = ref.process(data, sample_rate=rate)
    assert streamed(data, rate, full=True, seed=len(data)) == want
    assert streamed(data, rate, full=False, seed=1) == ref.level(data, sample_rate=rate)
