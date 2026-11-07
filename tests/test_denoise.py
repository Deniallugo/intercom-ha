"""Broadcast cleanup: length/format kept, never raises or clips, silence not
amplified, and SNR improves on speech-shaped input."""
import array
import math
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "intercom-addon"))
import denoise  # noqa: E402

RATE = 16000


def pcm(samples) -> bytes:
    out = array.array("h")
    for s in samples:
        out.append(max(-32768, min(32767, int(s))))
    return out.tobytes()


def unpack(b) -> tuple:
    return struct.unpack("<%dh" % (len(b) // 2), b)


def speech_like(seconds=2.0, level=2000, noise=150, duty=0.5):
    """Bursts of a 200 Hz-fundamental tone over constant noise — loud passages
    alternating with noise-only gaps, which is the shape the expander targets."""
    n = int(RATE * seconds)
    out = []
    # Deterministic pseudo-noise: no seeding concerns, no numpy.
    state = 12345
    for i in range(n):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        hiss = ((state / 0x7FFFFFFF) - 0.5) * 2 * noise
        speaking = (i // int(RATE * 0.25)) % 2 == 0 if duty else False
        v = hiss
        if speaking:
            v += level * (math.sin(2 * math.pi * 200 * i / RATE)
                          + 0.4 * math.sin(2 * math.pi * 800 * i / RATE))
        out.append(v)
    return pcm(out)


def snr_db(b):
    s = unpack(b)
    win = RATE // 4
    levels = sorted(sum(abs(x) for x in s[i:i + win]) / win
                    for i in range(0, max(len(s) - win, 1), win)) or [0]
    if levels[0] <= 0:
        return float("inf")
    return 20 * math.log10(levels[-1] / levels[0])


def peak(b):
    return max(abs(x) for x in unpack(b))


# ── Structural guarantees ────────────────────────────────────────────────────

def test_preserves_length_and_format():
    src = speech_like()
    out = denoise.process(src, sample_rate=RATE)
    assert len(out) == len(src)
    assert len(out) % 2 == 0


@pytest.mark.parametrize("fn", [denoise.process, denoise.level])
def test_odd_length_keeps_the_trailing_byte(fn):
    """Output length equals input length; downstream timing depends on it."""
    src = speech_like()
    odd = src + b"\x7f"
    out = fn(odd, sample_rate=RATE)
    assert len(out) == len(odd)
    assert out[-1:] == b"\x7f"
    assert out[:-1] == fn(src, sample_rate=RATE)


@pytest.mark.parametrize("bad", [b"", b"\x00", b"\x01\x02\x03"])
def test_short_or_odd_input_passes_through(bad):
    assert denoise.process(bad, sample_rate=RATE) == bad


def test_never_clips():
    # Input already close to full scale must not be pushed over by normalising.
    src = speech_like(level=30000, noise=200)
    out = denoise.process(src, sample_rate=RATE)
    assert peak(out) <= 32767
    clipped = sum(1 for x in unpack(out) if abs(x) >= 32767)
    assert clipped == 0


def test_output_is_valid_int16():
    out = denoise.process(speech_like(), sample_rate=RATE)
    assert all(-32768 <= x <= 32767 for x in unpack(out))


# ── Behaviour ───────────────────────────────────────────────────────────────

def test_improves_snr_on_speech_like_input():
    src = speech_like()
    out = denoise.process(src, sample_rate=RATE)
    assert snr_db(out) > snr_db(src) + 3.0


def speech_level(b):
    """p90 frame RMS — the same measure the module uses to judge speech."""
    s = unpack(b)
    fr = int(RATE * denoise.FRAME_MS / 1000)
    rms = sorted(math.sqrt(sum(x * x for x in s[i:i + fr]) / fr)
                 for i in range(0, len(s) - fr + 1, fr))
    return rms[int(len(rms) * denoise.SPEECH_PERCENTILE)]


def test_brings_speech_to_the_target_level():
    """Speech lands near TARGET_SPEECH_RMS however quiet it arrived."""
    for level in (600, 1200, 3000):
        out = denoise.process(speech_like(level=level), sample_rate=RATE)
        ratio = speech_level(out) / denoise.TARGET_SPEECH_RMS
        # The peak ceiling can legitimately hold it short of the target.
        assert 0.5 < ratio <= 1.2, f"level={level}: speech at x{ratio:.2f} of target"


def _floor_of(b):
    """Quietest quarter-second's mean |sample| — the noise between words."""
    s = unpack(b)
    win = RATE // 4
    return min(sum(abs(x) for x in s[i:i + win]) / win
               for i in range(0, max(len(s) - win, 1), win))


def test_gain_does_not_undo_the_noise_reduction():
    """Make-up gain may not lift the floor >3 dB over raw (synthetic white noise
    is the hard case; real mic noise ends up below)."""
    src = speech_like(level=1200, noise=200)
    out = denoise.process(src, sample_rate=RATE)
    assert _floor_of(out) < _floor_of(src) * 10 ** (3 / 20), (
        "noise floor rose more than 3 dB above the raw original after make-up")
    assert speech_level(out) > speech_level(src), "speech should end up louder"


def test_lowers_the_noise_floor():
    """Floor drops relative to speech — what level() alone cannot do."""
    src = speech_like(level=1200, noise=200)

    def gap(b):
        return speech_level(b) / _floor_of(b)

    cleaned = gap(denoise.process(src, sample_rate=RATE))
    levelled = gap(denoise.level(src, sample_rate=RATE))
    assert cleaned > levelled * 2.0, (
        f"cleanup buys only x{cleaned / levelled:.2f} speech-to-floor over level()")


def test_silence_is_not_amplified():
    """Near-silence stays quiet: a dead mic is not normalised into hiss."""
    src = speech_like(noise=20, duty=0)
    out = denoise.process(src, sample_rate=RATE)
    assert peak(out) < denoise.MIN_PEAK_TO_NORMALISE * 2


def test_removes_dc_offset():
    n = RATE
    src = pcm([5000 + 800 * math.sin(2 * math.pi * 220 * i / RATE) for i in range(n)])
    out = unpack(denoise.process(src, sample_rate=RATE))
    mean = sum(out) / len(out)
    assert abs(mean) < 50, f"DC not removed: mean {mean}"


def test_level_restore_is_bounded():
    """Restoring level may never clip or exceed MAX_MAKEUP, even on quiet input."""
    src = speech_like(level=400, noise=30)
    out = denoise.process(src, sample_rate=RATE)
    assert peak(out) <= denoise.TARGET_PEAK + 1
    assert peak(out) <= peak(src) * denoise.MAX_MAKEUP * 1.1


def test_highpass_response():
    """-3 dB at the corner, flat over the speech band."""
    import array as _array

    def gain_at(hz):
        n = RATE
        sig = _array.array("h", [int(8000 * math.sin(2 * math.pi * hz * i / RATE))
                                 for i in range(n)])
        out = denoise._highpass(sig, RATE)
        settled = slice(RATE // 4, None)
        return 20 * math.log10(max(abs(x) for x in out[settled])
                               / max(abs(x) for x in sig[settled]))

    assert -4.0 < gain_at(denoise.HIGHPASS_HZ) < -2.0
    for hz in (500, 1000, 3000):
        assert gain_at(hz) > -0.5, f"{hz} Hz attenuated by {gain_at(hz):.2f} dB"


def test_is_deterministic():
    src = speech_like()
    assert denoise.process(src, sample_rate=RATE) == denoise.process(src, sample_rate=RATE)


# ── level(): the stage a broadcast gets with the cleanup off ─────────────────

def test_level_brings_quiet_speech_to_its_target():
    """level() alone still brings quiet speech up to the target."""
    # ~quietest real upload; much lower is capped by MAX_MAKEUP.
    for lvl in (900, 1500, 4000):
        out = denoise.level(speech_like(level=lvl), sample_rate=RATE)
        ratio = speech_level(out) / denoise.TARGET_SPEECH_RMS
        assert 0.7 < ratio <= 1.2, f"level={lvl}: speech at x{ratio:.2f} of target"


def test_level_limiter_holds_the_peak_ceiling():
    """The limiter, not a smaller factor, keeps peaks under TARGET_PEAK."""
    src = speech_like(level=2500)
    # Plosive-like spike far above the speech.
    s = list(unpack(src))
    for i in range(8000, 8040):
        s[i] = 20000 if i % 2 else -20000
    src = struct.pack("<%dh" % len(s), *s)
    out = denoise.level(src, sample_rate=RATE)
    assert peak(out) <= denoise.TARGET_PEAK + 1
    assert speech_level(out) > 0.7 * denoise.TARGET_SPEECH_RMS


def test_level_leaves_silence_alone():
    src = speech_like(noise=20, duty=0)
    out = denoise.level(src, sample_rate=RATE)
    # No make-up gain: only the high-pass's own few-LSB overshoot may show.
    assert peak(out) <= peak(src) * 1.5


def test_level_preserves_length_and_passes_bad_input_through():
    src = speech_like()
    assert len(denoise.level(src, sample_rate=RATE)) == len(src)
    assert denoise.level(b"\x01", sample_rate=RATE) == b"\x01"
