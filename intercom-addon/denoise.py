"""Clean up the raw mic PCM before it is broadcast.

Why here and not on the device: this is the one place in the chain with CPU to
spare, float headroom, and no reflash cycle. The measured lesson from the gain
experiments (docs/DEVICES.md -> the INMP441 section) is that a bigger multiplier
on the device raises the noise floor with the signal — SNR was 13-15 dB at
unity, at +18 dB and at +36 dB alike — and past a point it clips, destroying
information nothing downstream can recover. So the device now takes only a small
fixed boost that cannot clip, and the *level* is made up here, after the hiss
between words has been pushed down.

Three stages, in this order:

  1. high-pass   — kills the INMP441's DC bias and sub-audio wander. Cheap, and
                   it must run first: DC offset otherwise inflates every RMS
                   measurement the later stages depend on.
  2. expander    — attenuates frames that sit near the noise floor, so silence
                   between words goes quiet instead of hissing. A *downward
                   expander*, not a hard gate: gain moves continuously with
                   level, which is what stops speech onsets from being chopped.
  3. normalise   — one scale factor to bring the peak to TARGET_PEAK. Computed
                   in float over the whole buffer, so unlike device-side gain it
                   can never clip, and unlike an AGC it never pumps.

Length, sample rate and format are preserved exactly, so callers can keep using
the same duration arithmetic.

What this does NOT touch: the copy kept by recordings.py. That is deliberately
the raw mic audio — the thing that tells you whether the microphone works — and
processing it would hide the very faults it exists to expose.
"""
import array
import logging
import math
import struct

log = logging.getLogger(__name__)

# ── High-pass ────────────────────────────────────────────────────────────────
# 80 Hz. Below the lowest speech fundamental (~85 Hz for a low male voice), so
# it removes bias and rumble without thinning the voice.
HIGHPASS_HZ = 80.0

# ── Spectral subtraction (multiband) ────────────────────────────────────────
# The expander below only acts in the gaps between words. Measurement on a real
# capture showed that is 33% of the timeline — the other 67% carries speech, and
# an expander cannot touch the noise underneath it. With this mic's 10-13 dB
# in-band SNR, that made the whole thing inaudible: 1-8 kHz hiss moved -0.2 dB.
#
# This stage does what an expander cannot: it attenuates every frame by the
# noise it estimates for that band, so hiss under speech comes down too.
#
# Measured, 1-8 kHz median (audible hiss) vs 300-3000 Hz p90 (voice):
#
#   bands  over   hiss     voice    net
#       8   1.0   -3.7 dB  -1.8 dB  +1.9 dB
#       8   1.5   -5.4 dB  -2.7 dB  +2.7 dB
#       8   2.0   -7.4 dB  -3.6 dB  +3.8 dB
#      24   2.0   -6.8 dB  -3.3 dB  +3.5 dB
#
# More bands buy nothing and cost time linearly (0.18s at 8, 0.52s at 24), so
# 8 it is. The voice loss is given back by _restore_level, leaving hiss ~4 dB
# down. That is a real, audible improvement and also close to the ceiling: the
# microphone only delivers 10-13 dB of SNR, so there is not much more to win
# without artefacts.
BAND_COUNT = 8
BAND_LO_HZ = 80.0
BAND_HI_HZ = 8000.0

# How many times the estimated noise to subtract. Above ~2.0 the voice starts
# audibly thinning for very little extra hiss reduction.
OVERSUBTRACT = 2.0

# Never attenuate a band below this (-12 dB). A hard zero is what produces
# "musical noise" — isolated bands winking in and out. This and MAX_ATTENUATION
# multiply, so together they set how dead the silence between words sounds; the
# sweep is documented on MAX_ATTENUATION.
BAND_GAIN_FLOOR = 0.25

# Shorter frame than the expander: subtraction tracks the spectrum, not syllables.
BAND_FRAME_MS = 16.0

# Per-band gain smoothing across frames. Also fights musical noise.
BAND_SMOOTH = 0.6

# Percentile of per-band frame energy taken as that band's noise estimate.
BAND_NOISE_PERCENTILE = 0.15


# ── Expander ─────────────────────────────────────────────────────────────────
# Frame length for level measurement. 20 ms is long enough for a stable RMS at
# 16 kHz (320 samples) and short enough to track syllables.
FRAME_MS = 20.0

# The noise floor is taken as a low percentile of frame energy rather than the
# minimum, so one freak-quiet frame cannot define it. 10% of frames sit below.
FLOOR_PERCENTILE = 0.10

# The expander threshold has to sit BETWEEN the noise floor and the speech, and
# a fixed multiple of the floor does not: at 6x floor, measurement showed only
# 6-12% of frames above the threshold on real captures, i.e. speech was being
# attenuated along with the noise — and then normalisation scaled it all back up,
# so the result was uniform gain with the hiss fully intact.
#
#   file      floor(p10)  speech(p90)   6x floor   verdict
#   mic-03            82          538        494   just below speech
#   mic-06           107          593        643   ABOVE speech
#   mic-07           396         2185       2375   ABOVE speech
#
# So the threshold is derived from both: the geometric mean of the floor and the
# speech level, which is their midpoint in dB and therefore adapts to whatever
# SNR the capture actually has. The clamps keep it sane when a capture is all
# speech (no floor to measure) or all silence (no speech).
SPEECH_PERCENTILE = 0.90
THRESH_MIN_ABOVE_FLOOR = 1.5
THRESH_MAX_ABOVE_FLOOR = 8.0

# Expansion ratio below the threshold: 3.0 means 1 dB down in becomes 3 dB down
# out. 2.0 was too gentle to survive the make-up gain — the noise came back up
# with the speech, which is audibly just "louder", the complaint this exists to
# fix. 3.0 pushes the floor far enough below that normalising cannot undo it.
RATIO = 3.0

# Gating all the way to digital silence sounds like the line dropped. This
# multiplies with BAND_GAIN_FLOOR, and at -26 dB the pair drove the gaps to
# -38 dB — measurably clean, audibly broken. Swept for a gap that is clearly
# quieter but still a live room (hiss = 1-8 kHz median, gap = quietest 250 ms):
#
#   band floor / this   hiss             voice          gap
#         0.15 / 0.05   -8 to -19 dB     +-0.6 dB       -18 to -38 dB  dead
#         0.20 / 0.25   -8 to -18 dB     +-0.4 dB       -16 to -22 dB
#         0.25 / 0.50   -7 to -12 dB     +-0.5 dB       -11 to -14 dB  <- chosen
#     subtraction only  -4 to -7 dB      +-0.4 dB        -6 to -13 dB
#
# Dropping the expander entirely (last row) is the most natural but gives up
# half the hiss reduction; -26 dB is measurably best and sounds wrong. This is
# the compromise, and it is a taste call — move it if the gaps sound too abrupt
# (up) or still too noisy (down).
MAX_ATTENUATION = 0.50

# One-pole smoothing on the gain. Attack must be fast or the first consonant of
# a word is swallowed; release slow or the tail pumps.
#
# Release was 80 ms, and measurement showed the gain never arrived: 0% of frames
# reached the attenuation the expander asked for, because an 80 ms time constant
# cannot settle inside the gap between two words. 40 ms settles within a typical
# pause and still sounds like a room going quiet rather than a gate slamming.
ATTACK_MS = 5.0
RELEASE_MS = 40.0

# ── Normalise ────────────────────────────────────────────────────────────────
# This stage restores the speech to the level it arrived at — it does NOT make
# the broadcast louder. Getting this wrong is what made the first version sound
# like "louder, including the noise": it normalised to a fixed target, which on
# this material demanded 6x make-up and lifted the suppressed floor right back
# up with the voice. The expander lowers the noise; nothing here is allowed to
# undo that.
#
# Level is the device's job (a small fixed shift) and the media player's. If a
# broadcast genuinely needs more, raise this — in dB, so it is obvious that it
# costs noise.
MAKEUP_DB = 0.0

# -3 dBFS ceiling. Leaves headroom for the chimes concatenated around this
# payload, and no scale factor is allowed to push the peak past it.
TARGET_PEAK = 0.70 * 32767

# Refuse to normalise a buffer whose peak is below this (~-44 dBFS): there is no
# speech in it, and scaling would just present amplified hiss at full volume.
MIN_PEAK_TO_NORMALISE = 200

# Cap on make-up gain (+18 dB). Without it, a near-silent capture gets whatever
# enormous factor the arithmetic asks for.
MAX_MAKEUP = 8.0


def process(pcm: bytes, *, sample_rate: int, enabled: bool = True) -> bytes:
    """Return `pcm` high-passed, expanded and normalised.

    Falls back to returning the input unchanged — never raising — for anything
    it cannot handle (odd length, empty, disabled, silent). A broadcast must
    still go out if the cleanup cannot run.
    """
    if not enabled or len(pcm) < 4:
        return pcm

    n = len(pcm) // 2
    try:
        samples = array.array("h")
        samples.frombytes(pcm[: n * 2])
    except (ValueError, struct.error) as e:
        log.warning("denoise: cannot unpack PCM (%s) — passing through", e)
        return pcm

    work = _highpass(samples, sample_rate)

    # `speech` is measured here, before anything attenuates, and handed to
    # _restore_level so the voice ends up exactly where it started — see
    # MAKEUP_DB. Everything between the two only ever takes level away.
    floor, speech, thresh = _measure(work, sample_rate)

    # Multiband subtraction first: it is the only stage that reduces noise while
    # speech is present, and the expander that follows then cleans the gaps.
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
    scale = _restore_level(work, sample_rate, speech)

    log.info("denoise: floor %.0f  speech %.0f  thresh %.0f  level x%.2f",
             floor, speech, thresh, scale)
    # work holds float64; to_pcm rounds and clamps it back to int16.
    return to_pcm(work)


def _highpass(samples: "array.array", sample_rate: int) -> "array.array":
    """One-pole high-pass at HIGHPASS_HZ, returned as float-capable ints.

    y[n] = a * (y[n-1] + x[n] - x[n-1]) — the standard DC blocker. Kept in a
    Python list of floats while the later stages work on it, so repeated scaling
    does not requantise at every step.
    """
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
    """Sorted per-frame RMS levels, the basis for every level decision here."""
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
    """(noise floor, speech level, expander threshold) as RMS amplitudes.

    Percentiles rather than min/max so one freak-quiet or freak-loud frame
    cannot define either end. The threshold is their geometric mean — the
    midpoint in dB — so it tracks the capture's actual SNR instead of assuming
    one. Clamped in case a capture is all speech or all silence and the two
    measurements collapse together.
    """
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
    """Split into BAND_COUNT bands that sum back to the input EXACTLY.

    Each band is a one-pole low-pass of what is left, subtracted from the
    residual — so with all gains at 1 the sum reconstructs the input to within
    float error (measured 2e-13). A conventional filter bank would leave
    crossover ripple, which colours the voice even when nothing is being
    attenuated.
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
    """Attenuate `band` in place by its own estimated noise, frame by frame.

    gain = (level - OVERSUBTRACT * noise) / level, floored and smoothed. Unlike
    the expander, this bites while speech is present: a band whose level is near
    its noise estimate is attenuated even when other bands carry the voice.
    """
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

        # Rising gain (a word starting) uses the fast attack; falling gain
        # (settling back into silence) uses the slow release. Swapping these
        # swallows onsets and chops tails.
        coeff = attack if target > gain else release
        for i in range(start, end):
            gain += (target - gain) * coeff
            work[i] *= gain


def _restore_level(work: "array.array", sample_rate: int, was: float) -> float:
    """Bring speech back to `was` (its level before expansion). Returns the factor.

    Deliberately NOT a normaliser: the target is the level the audio already
    had, so the only audible change is that the noise between words is quieter.
    MAKEUP_DB adds deliberate extra level on top if it is set.

    Bounds that have each mattered: the peak may not exceed TARGET_PEAK (the
    chimes still have to fit, and nothing may clip), the factor is capped at
    MAX_MAKEUP, and a buffer with no speech in it is left alone so a dead mic is
    never presented as full-scale hiss.
    """
    peak = 0.0
    for v in work:
        av = -v if v < 0 else v
        if av > peak:
            peak = av
    if peak < MIN_PEAK_TO_NORMALISE:
        log.info("denoise: peak %.0f below %d — leaving level alone (no speech)",
                 peak, MIN_PEAK_TO_NORMALISE)
        return 1.0

    rms = _frame_rms(work, sample_rate)
    now = rms[min(len(rms) - 1, int(len(rms) * SPEECH_PERCENTILE))] if rms else 0.0
    wanted = (was / now) if now > 0 else 1.0
    wanted *= 10.0 ** (MAKEUP_DB / 20.0)
    scale = min(MAX_MAKEUP, wanted, TARGET_PEAK / peak)
    if scale == 1.0:
        return 1.0

    for i, v in enumerate(work):
        work[i] = v * scale
    return scale


def to_pcm(work) -> bytes:
    """Round and clamp float samples back to 16-bit PCM bytes."""
    out = array.array("h", bytes(2 * len(work)))
    for i, v in enumerate(work):
        s = int(v + 0.5) if v >= 0 else int(v - 0.5)
        out[i] = 32767 if s > 32767 else (-32768 if s < -32768 else s)
    return out.tobytes()
