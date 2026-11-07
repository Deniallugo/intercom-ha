"""Clean up raw mic PCM before it is broadcast.

Stages, in order: high-pass, multiband noise subtraction, downward expander,
level to TARGET_SPEECH_RMS behind a peak limiter. level() is the high-pass and
level stages alone (the `denoise: false` path).

Input is 16-bit mono PCM. Output is whole samples only: an odd trailing byte is
dropped, since chimes are appended after it. The raw copy in recordings.py is never processed.
"""
import array
import logging
import math
import struct

log = logging.getLogger(__name__)

# ── High-pass ────────────────────────────────────────────────────────────────
# Below the lowest male fundamental (~85 Hz): removes DC and rumble, not voice.
HIGHPASS_HZ = 80.0

# ── Spectral subtraction (multiband) ────────────────────────────────────────
# The only stage that lowers hiss *under* speech (67% of frames carry speech, so
# an expander alone moved audible hiss by 0.2 dB). 24 bands measured no better
# than 8 and cost 3x the CPU.
BAND_COUNT = 8
BAND_LO_HZ = 80.0
BAND_HI_HZ = 8000.0

# Above ~2.0 the voice thins for little extra hiss reduction.
OVERSUBTRACT = 2.0

# -12 dB floor per band; a hard zero produces "musical noise".
BAND_GAIN_FLOOR = 0.25

BAND_FRAME_MS = 16.0

# Per-band gain smoothing across frames; also fights musical noise.
BAND_SMOOTH = 0.6

# Per-band noise estimate: this percentile of frame energy.
BAND_NOISE_PERCENTILE = 0.15


# ── Expander ─────────────────────────────────────────────────────────────────
# Long enough for a stable RMS, short enough to track syllables.
FRAME_MS = 20.0

# Percentile, not minimum, so one freak-quiet frame cannot set the floor.
FLOOR_PERCENTILE = 0.10

# Threshold = geometric mean of floor and speech (their midpoint in dB). A fixed
# multiple of the floor landed above the speech on real captures. Clamped for
# all-speech or all-silence captures.
SPEECH_PERCENTILE = 0.90
THRESH_MIN_ABOVE_FLOOR = 1.5
THRESH_MAX_ABOVE_FLOOR = 8.0

# 1 dB under the threshold in -> 3 dB out. At 2.0 the make-up gain brought the
# noise back up.
RATIO = 3.0

# Deepest expander cut (-6 dB). Together with BAND_GAIN_FLOOR this sets how
# quiet the gaps get: 11-14 dB here; deeper sounded like the line dropped.
# A taste call — raise if gaps sound abrupt, lower if still hissy.
MAX_ATTENUATION = 0.50

# Fast attack keeps first consonants; release must settle within a pause
# between words (80 ms never did).
ATTACK_MS = 5.0
RELEASE_MS = 40.0

# ── Normalise ────────────────────────────────────────────────────────────────
# -16 dBFS speech (p90 frame RMS). Absolute, because broadcasts share a player
# with music (~-12 dBFS) and follow a chime (~-9); raw uploads arrive at -21 to
# -33 dBFS. Safe only because it runs after the noise is down: speech +11-15 dB,
# gaps still 1-4 dB below raw. The limiter in _set_level buys the last few dB
# that speech's crest factor would otherwise block.
TARGET_SPEECH_RMS = 5200.0

# Trim on top of the target, in dB. A knob; 0 = off.
MAKEUP_DB = 0.0

# -3 dBFS peak ceiling.
TARGET_PEAK = 0.70 * 32767

# ~-44 dBFS: below this there is no speech, only hiss not worth amplifying.
MIN_PEAK_TO_NORMALISE = 200

# Make-up gain cap (+18 dB).
MAX_MAKEUP = 8.0


def _unpack(pcm: bytes, tag: str):
    """Samples (an odd trailing byte dropped), or None if `pcm` cannot be read."""
    n = len(pcm) // 2
    try:
        samples = array.array("h")
        samples.frombytes(pcm[: n * 2])
    except (ValueError, struct.error) as e:
        log.warning("%s: cannot unpack PCM (%s) — passing through", tag, e)
        return None
    return samples


def process(pcm: bytes, *, sample_rate: int) -> bytes:
    """Full cleanup. Never raises: returns `pcm` unchanged if it cannot run."""
    if len(pcm) < 4:
        return pcm
    samples = _unpack(pcm, "denoise")
    if samples is None:
        return pcm

    work = _highpass(samples, sample_rate)

    floor, speech, thresh = _measure(work, sample_rate)

    bands = _split_bands(work, sample_rate)
    for band in bands:
        _subtract_noise(band, sample_rate)
    for i in range(len(work)):
        total = 0.0
        for band in bands:
            total += band[i]
        work[i] = total

    if thresh > 0:
        _expand(work, sample_rate, thresh)
    scale = _set_level(work, sample_rate, TARGET_SPEECH_RMS, tag="denoise")

    log.info("denoise: floor %.0f  speech %.0f  thresh %.0f  level x%.2f",
             floor, speech, thresh, scale)
    return to_pcm(work)


def level(pcm: bytes, *, sample_rate: int) -> bytes:
    """High-pass and level only (`denoise: false`). Hiss rises with the speech."""
    if len(pcm) < 4:
        return pcm
    samples = _unpack(pcm, "level")
    if samples is None:
        return pcm
    work = _highpass(samples, sample_rate)
    scale = _set_level(work, sample_rate, TARGET_SPEECH_RMS, tag="level")
    log.info("level: x%.2f", scale)
    return to_pcm(work)


def _highpass(samples: "array.array", sample_rate: int) -> "array.array":
    """One-pole high-pass, as array('d') so later stages do not requantise."""
    rc = 1.0 / (2.0 * math.pi * HIGHPASS_HZ)
    dt = 1.0 / sample_rate
    a = rc / (rc + dt)

    out = array.array("d", bytes(8 * len(samples)))
    prev_x = float(samples[0])
    prev_y = 0.0
    for i, raw in enumerate(samples):
        x = float(raw)
        y = a * (prev_y + x - prev_x)
        out[i] = y
        prev_x, prev_y = x, y
    return out


def _frame_rms(work, sample_rate: int) -> list:
    """Sorted per-frame RMS levels."""
    frame = max(1, int(sample_rate * FRAME_MS / 1000.0))
    out = []
    for start in range(0, len(work) - frame + 1, frame):
        acc = 0.0
        for i in range(start, start + frame):
            acc += work[i] * work[i]
        out.append(math.sqrt(acc / frame))
    out.sort()
    return out


def _measure(work: "array.array", sample_rate: int) -> tuple:
    """(noise floor, speech level, expander threshold) as RMS amplitudes."""
    rms = _frame_rms(work, sample_rate)
    if not rms:
        return 0.0, 0.0, 0.0
    floor = rms[min(len(rms) - 1, int(len(rms) * FLOOR_PERCENTILE))]
    speech = rms[min(len(rms) - 1, int(len(rms) * SPEECH_PERCENTILE))]
    if floor <= 0.0:
        return floor, speech, 0.0
    thresh = math.sqrt(floor * speech) if speech > floor else floor * THRESH_MIN_ABOVE_FLOOR
    thresh = max(floor * THRESH_MIN_ABOVE_FLOOR,
                 min(floor * THRESH_MAX_ABOVE_FLOOR, thresh))
    return floor, speech, thresh


def _split_bands(work, rate: int) -> list:
    """Split into BAND_COUNT bands that sum back to the input exactly.

    Each band is a low-pass of the residual, so there is no crossover ripple.
    """
    corners = [BAND_LO_HZ * (BAND_HI_HZ / BAND_LO_HZ) ** (i / (BAND_COUNT - 1))
               for i in range(BAND_COUNT - 1)]
    residual = list(work)
    bands = []
    dt = 1.0 / rate
    for fc in corners:
        alpha = dt / (1.0 / (2.0 * math.pi * fc) + dt)
        y = 0.0
        band = [0.0] * len(residual)
        for i, v in enumerate(residual):
            y += alpha * (v - y)
            band[i] = y
        for i in range(len(residual)):
            residual[i] -= band[i]
        bands.append(band)
    bands.append(residual)
    return bands


def _subtract_noise(band, rate: int) -> None:
    """Attenuate `band` in place by its own estimated noise, frame by frame."""
    frame = max(1, int(rate * BAND_FRAME_MS / 1000.0))
    rms = []
    for start in range(0, len(band), frame):
        end = min(start + frame, len(band))
        acc = 0.0
        for i in range(start, end):
            acc += band[i] * band[i]
        rms.append(math.sqrt(acc / (end - start)))
    if not rms:
        return
    noise = sorted(rms)[min(len(rms) - 1, int(len(rms) * BAND_NOISE_PERCENTILE))]

    gain = 1.0
    for k, start in enumerate(range(0, len(band), frame)):
        end = min(start + frame, len(band))
        level = rms[k]
        raw = ((level - OVERSUBTRACT * noise) / level) if level > 1e-9 else BAND_GAIN_FLOOR
        target = max(BAND_GAIN_FLOOR, raw)
        gain = BAND_SMOOTH * gain + (1.0 - BAND_SMOOTH) * target
        for i in range(start, end):
            band[i] *= gain


def _expand(work: "array.array", sample_rate: int, thresh: float) -> None:
    """Attenuate below `thresh`, in place, with smoothed per-sample gain."""
    frame = max(1, int(sample_rate * FRAME_MS / 1000.0))
    # One-pole coefficients: fraction of the remaining distance closed per sample.
    attack = 1.0 - math.exp(-1.0 / max(1e-9, sample_rate * ATTACK_MS / 1000.0))
    release = 1.0 - math.exp(-1.0 / max(1e-9, sample_rate * RELEASE_MS / 1000.0))

    gain = 1.0
    for start in range(0, len(work), frame):
        end = min(start + frame, len(work))
        acc = 0.0
        for i in range(start, end):
            acc += work[i] * work[i]
        level = math.sqrt(acc / (end - start))

        if level >= thresh:
            target = 1.0
        elif level <= 0.0:
            target = MAX_ATTENUATION
        else:
            # Downward expansion: (level/thresh) ** (ratio - 1).
            target = max(MAX_ATTENUATION, (level / thresh) ** (RATIO - 1.0))

        coeff = attack if target > gain else release
        for i in range(start, end):
            gain += (target - gain) * coeff
            work[i] *= gain


def _set_level(work: "array.array", sample_rate: int, target: float,
               *, tag: str = "denoise") -> float:
    """Bring speech to `target` RMS; returns the factor applied.

    Must run last, after noise reduction. Peaks are limited (not the factor
    shrunk), so one plosive cannot keep the whole broadcast quiet.
    """
    peak = 0.0
    for v in work:
        av = -v if v < 0 else v
        if av > peak:
            peak = av
    if peak < MIN_PEAK_TO_NORMALISE:
        log.info("%s: peak %.0f below %d — leaving level alone (no speech)",
                 tag, peak, MIN_PEAK_TO_NORMALISE)
        return 1.0

    rms = _frame_rms(work, sample_rate)
    now = rms[min(len(rms) - 1, int(len(rms) * SPEECH_PERCENTILE))] if rms else 0.0
    wanted = (target / now) if now > 0 else 1.0
    wanted *= 10.0 ** (MAKEUP_DB / 20.0)
    scale = min(MAX_MAKEUP, wanted)

    if scale != 1.0:
        for i, v in enumerate(work):
            work[i] = v * scale
    if peak * scale > TARGET_PEAK:
        _limit(work, sample_rate, TARGET_PEAK)
    return scale


# Lookahead makes the ceiling hard; release slow enough not to flutter.
LIMIT_LOOKAHEAD_MS = 2.0
LIMIT_RELEASE_MS = 80.0


def _limit(work: "array.array", sample_rate: int, ceiling: float) -> None:
    """Hold |work| <= ceiling in place: min gain over +-lookahead, smooth release."""
    n = len(work)
    look = max(1, int(sample_rate * LIMIT_LOOKAHEAD_MS / 1000.0))
    rel = 1.0 - math.exp(-1.0 / (sample_rate * LIMIT_RELEASE_MS / 1000.0))

    need = [1.0] * n
    for i, v in enumerate(work):
        av = -v if v < 0 else v
        if av > ceiling:
            need[i] = ceiling / av

    # Sliding-window minimum over [i - look, i + look] (monotonic deque).
    from collections import deque
    q = deque()
    env = 1.0
    for j in range(n + look):
        if j < n:
            while q and need[q[-1]] >= need[j]:
                q.pop()
            q.append(j)
        i = j - look
        if i < 0:
            continue
        while q[0] < i - look:
            q.popleft()
        g = need[q[0]]
        env = g if g < env else env + (g - env) * rel
        work[i] *= env


def to_pcm(work) -> bytes:
    """Round and clamp float samples back to 16-bit PCM bytes."""
    out = array.array("h", bytes(2 * len(work)))
    for i, v in enumerate(work):
        s = int(v + 0.5) if v >= 0 else int(v - 0.5)
        out[i] = 32767 if s > 32767 else (-32768 if s < -32768 else s)
    return out.tobytes()
