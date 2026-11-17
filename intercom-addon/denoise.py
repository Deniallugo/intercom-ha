"""Clean up raw mic PCM before it is broadcast.

Stages, in order: high-pass, multiband noise subtraction, downward expander,
level to TARGET_SPEECH_RMS behind a peak limiter. level() is the high-pass and
level stages alone (the `denoise: false` path). Stream runs either one as the
upload arrives, leaving only the whole-message steps for the end.

Input is 16-bit mono PCM. Output is whole samples only: an odd trailing byte is
dropped, since chimes are appended after it. The raw copy in recordings.py is never processed.
"""
import array
import itertools
import logging
import math
import operator

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


def process(pcm: bytes, *, sample_rate: int) -> bytes:
    """Full cleanup. Never raises: returns `pcm` unchanged if it cannot run."""
    stream = Stream(sample_rate=sample_rate)
    stream.feed(pcm)
    return stream.finish()


def level(pcm: bytes, *, sample_rate: int) -> bytes:
    """High-pass and level only (`denoise: false`). Hiss rises with the speech."""
    stream = Stream(sample_rate=sample_rate, full=False)
    stream.feed(pcm)
    return stream.finish()


class Stream:
    """process() (or level(), full=False) fed piecewise, as an upload arrives.

    Everything causal runs in feed(): high-pass, the band split, per-frame RMS
    of the signal and of every band. finish() is left with what needs the
    whole message: the noise percentiles, band gains, expander and level.
    Output is identical, bit for bit, however the input is cut into pieces.
    """

    def __init__(self, *, sample_rate: int, full: bool = True):
        self.rate = sample_rate
        self.full = full
        self._size = 0          # bytes fed, odd ones included
        self._head = b""        # first bytes: short inputs pass through
        self._odd = b""         # a sample split between two feeds
        rc = 1.0 / (2.0 * math.pi * HIGHPASS_HZ)
        self._hp_a = rc / (rc + 1.0 / sample_rate)
        self._hp_state = None   # (prev_x, prev_y) once the first sample is in
        if not full:
            self._work = array.array("d")
            return
        # Expander measurement: whole FRAME_MS frames of the high-passed signal.
        self._frame = max(1, int(sample_rate * FRAME_MS / 1000.0))
        self._acc, self._fill, self._rms = 0.0, 0, []
        # Band split: one-pole low-passes of the residual (see _split_bands).
        dt = 1.0 / sample_rate
        corners = [BAND_LO_HZ * (BAND_HI_HZ / BAND_LO_HZ) ** (i / (BAND_COUNT - 1))
                   for i in range(BAND_COUNT - 1)]
        self._alphas = [dt / (1.0 / (2.0 * math.pi * fc) + dt) for fc in corners]
        self._ys = [0.0] * len(self._alphas)
        self._bands = [array.array("d") for _ in range(BAND_COUNT)]
        # Per-band BAND_FRAME_MS RMS; a trailing partial frame counts.
        self._bframe = max(1, int(sample_rate * BAND_FRAME_MS / 1000.0))
        self._bacc = [0.0] * BAND_COUNT
        self._bfill = 0
        self._brms = [[] for _ in range(BAND_COUNT)]

    def feed(self, pcm: bytes) -> None:
        if not pcm:
            return
        if len(self._head) < 4:
            self._head += pcm[: 4 - len(self._head)]
        self._size += len(pcm)
        data = self._odd + pcm if self._odd else pcm
        whole = len(data) - len(data) % 2
        self._odd = data[whole:]
        if not whole:
            return
        samples = array.array("h")
        samples.frombytes(data[:whole])
        work = self._highpass(samples)
        if not self.full:
            self._work.extend(work)
            return
        self._acc, self._fill = _frames(
            work, self._frame, self._acc, self._fill, self._rms, keep_partial=False)
        self._split(work)

    def finish(self) -> bytes:
        """The cleaned PCM. Inputs under 4 bytes come back unchanged."""
        if self._size < 4:
            return self._head
        if not self.full:
            work = self._work
            scale = _set_level(work, self.rate, TARGET_SPEECH_RMS, tag="level")
            log.info("level: x%.2f", scale)
            return to_pcm(work)

        self._rms.sort()
        floor, speech, thresh = _levels(self._rms)
        work = self._mix()
        if thresh > 0:
            _expand(work, self.rate, thresh)
        scale = _set_level(work, self.rate, TARGET_SPEECH_RMS, tag="denoise")

        log.info("denoise: floor %.0f  speech %.0f  thresh %.0f  level x%.2f",
                 floor, speech, thresh, scale)
        return to_pcm(work)

    def _highpass(self, samples) -> list:
        if self._hp_state is None:
            self._hp_state = (float(samples[0]), 0.0)
        out, prev_x, prev_y = _highpass_run(samples, self._hp_a, *self._hp_state)
        self._hp_state = (prev_x, prev_y)
        return out

    def _split(self, work: list) -> None:
        """Split into BAND_COUNT bands that sum back to the input exactly.

        Each band is a low-pass of the residual, so there is no crossover ripple.
        """
        residual = work
        bands = []
        for k, alpha in enumerate(self._alphas):
            y = self._ys[k]
            band = []
            append = band.append
            for v in residual:
                y += alpha * (v - y)
                append(y)
            self._ys[k] = y
            residual = list(map(operator.sub, residual, band))
            bands.append(band)
        bands.append(residual)

        fill = self._bfill
        for k, band in enumerate(bands):
            self._bands[k].extend(band)
            self._bacc[k], new_fill = _frames(
                band, self._bframe, self._bacc[k], fill, self._brms[k],
                keep_partial=True)
        self._bfill = new_fill

    def _mix(self) -> list:
        """Sum of the bands, each scaled by its noise-subtraction gain."""
        frame = self._bframe
        n = len(self._bands[0])
        work = [0.0] * n
        for k, band in enumerate(self._bands):
            rms = self._brms[k]
            if self._bfill:
                rms.append(math.sqrt(self._bacc[k] / self._bfill))
            gains = _band_gains(rms)
            per_sample = itertools.chain.from_iterable(
                itertools.repeat(g, frame) for g in gains)
            work = list(map(operator.add, work,
                            map(operator.mul, band, per_sample)))
        return work


def _frames(values, frame: int, acc: float, fill: int, out: list,
            *, keep_partial: bool) -> tuple:
    """Fold `values` into consecutive `frame`-sample RMS levels, appended to
    `out`; (acc, fill) carry an unfinished frame between calls."""
    i, n = 0, len(values)
    while i < n:
        take = min(frame - fill, n - i)
        for v in values[i:i + take]:
            acc += v * v
        i += take
        fill += take
        if fill == frame:
            out.append(math.sqrt(acc / frame))
            acc, fill = 0.0, 0
    return acc, fill


def _band_gains(rms: list) -> list:
    """Smoothed per-frame gain that subtracts a band's own noise estimate."""
    if not rms:
        return []
    noise = sorted(rms)[min(len(rms) - 1, int(len(rms) * BAND_NOISE_PERCENTILE))]
    gain = 1.0
    gains = []
    for level in rms:
        raw = ((level - OVERSUBTRACT * noise) / level) if level > 1e-9 else BAND_GAIN_FLOOR
        target = max(BAND_GAIN_FLOOR, raw)
        gain = BAND_SMOOTH * gain + (1.0 - BAND_SMOOTH) * target
        gains.append(gain)
    return gains


def _highpass_run(samples, a: float, prev_x: float, prev_y: float) -> tuple:
    """One-pole high-pass over `samples`: (out list, prev_x, prev_y)."""
    out = [0.0] * len(samples)
    for i, raw in enumerate(samples):
        x = float(raw)
        y = a * (prev_y + x - prev_x)
        out[i] = y
        prev_x, prev_y = x, y
    return out, prev_x, prev_y


def _highpass(samples: "array.array", sample_rate: int) -> "array.array":
    """One-pole high-pass, as array('d') so later stages do not requantise."""
    rc = 1.0 / (2.0 * math.pi * HIGHPASS_HZ)
    a = rc / (rc + 1.0 / sample_rate)
    out, _, _ = _highpass_run(samples, a, float(samples[0]), 0.0)
    return array.array("d", out)


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


def _levels(rms: list) -> tuple:
    """(noise floor, speech level, expander threshold) from sorted frame RMS."""
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
