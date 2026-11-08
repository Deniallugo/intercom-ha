import array
import io
import logging
import wave

from chimes import ChimeMixer

log = logging.getLogger(__name__)

# Assumed length of undecodable TTS, so restore/cleanup don't cut it short.
FALLBACK_DURATION_SECONDS = 30.0

# MPEG audio frame header tables (layer III only; TTS MP3 is always layer III).
_MP3_BITRATES = {  # kbit/s by version: MPEG-1, MPEG-2/2.5
    1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
}
_MP3_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def mp3_duration(data: bytes):
    """Seconds of MPEG layer III audio in ``data`` (frames summed, so VBR
    works), or None if no frames are found."""
    i = 0
    if data[:3] == b"ID3" and len(data) >= 10:
        size = 0
        for b in data[6:10]:
            size = (size << 7) | (b & 0x7F)
        i = 10 + size
    total, frames, n = 0.0, 0, len(data)
    while i + 4 <= n:
        h = int.from_bytes(data[i:i + 4], "big")
        ver, layer = (h >> 19) & 3, (h >> 17) & 3
        br_i, sr_i, pad = (h >> 12) & 0xF, (h >> 10) & 3, (h >> 9) & 1
        if (h >> 21) & 0x7FF != 0x7FF or ver == 1 or layer != 1 \
                or br_i in (0, 15) or sr_i == 3:
            if frames:
                break      # trailing tag/garbage after the audio
            i += 1         # still looking for the first frame
            continue
        rate = _MP3_RATES[ver][sr_i]
        bitrate = _MP3_BITRATES[1 if ver == 3 else 2][br_i] * 1000
        samples = 1152 if ver == 3 else 576
        size = (samples // 8) * bitrate // rate + pad
        if size < 4:
            break
        total += samples / rate
        frames += 1
        i += size
    return total if frames else None


def parse_tts_wav(audio: bytes):
    """Return (pcm, sample_rate, sample_width, channels), or None if the bytes
    are not a parseable PCM WAV (e.g. the engine returned mp3)."""
    try:
        with wave.open(io.BytesIO(audio), "rb") as w:
            channels = w.getnchannels()
            width = w.getsampwidth()
            rate = w.getframerate()
            pcm = w.readframes(w.getnframes())
    except (wave.Error, EOFError, ValueError):
        return None
    return pcm, rate, width, channels


def _downmix_to_mono(samples: array.array, channels: int) -> array.array:
    """Average interleaved 16-bit channels down to a single mono channel."""
    if channels <= 1:
        return samples
    n_frames = len(samples) // channels
    out = array.array("h", bytes(2 * n_frames))
    for i in range(n_frames):
        base = i * channels
        out[i] = sum(samples[base : base + channels]) // channels
    return out


def _resample_mono16(samples: array.array, src_rate: int, dst_rate: int) -> array.array:
    """Linear-interpolation resample of a mono 16-bit signal. Dependency-free
    (the addon image ships only python3 + aiohttp); fine for speech."""
    if src_rate == dst_rate:
        return samples
    n = len(samples)
    if n <= 1:
        return samples
    dst_n = max(1, round(n * dst_rate / src_rate))
    if dst_n == 1:
        return array.array("h", samples[:1])
    out = array.array("h", bytes(2 * dst_n))
    step = (n - 1) / (dst_n - 1)
    for i in range(dst_n):
        pos = i * step
        i0 = int(pos)
        i1 = min(i0 + 1, n - 1)
        frac = pos - i0
        s0 = samples[i0]
        out[i] = int(s0 + (samples[i1] - s0) * frac)
    return out


def build_announcement_wav(audio: bytes, mixer: ChimeMixer):
    """Return (bytes, ext, duration_seconds), chimed and at ``mixer``'s rate.

    Must be resampled: a 22.05 kHz Piper WAV makes the Atom Echo's speaker fail
    its DMA allocation. Non-16-bit / unparseable TTS plays without chimes.
    """
    parsed = parse_tts_wav(audio)
    if parsed is None:
        duration = mp3_duration(audio)
        log.warning("TTS audio not a parseable WAV; playing without chime "
                    "(%s)", f"MP3 {duration:.1f}s" if duration
                    else f"unknown length, assuming {FALLBACK_DURATION_SECONDS:.0f}s")
        return audio, "mp3", duration or FALLBACK_DURATION_SECONDS
    pcm, rate, width, channels = parsed
    if width != 2:
        # Can't mix non-16-bit, but the length is still known.
        duration = len(pcm) / (rate * width * channels)
        log.warning("TTS WAV is %d-bit, not 16-bit; playing without chime", width * 8)
        return audio, "wav", duration

    samples = array.array("h")
    samples.frombytes(pcm)
    samples = _downmix_to_mono(samples, channels)
    samples = _resample_mono16(samples, rate, mixer.sample_rate)
    if mixer.channels > 1:
        # Chimes are rendered at mixer.channels; match them.
        interleaved = array.array("h", bytes(2 * len(samples) * mixer.channels))
        for i, s in enumerate(samples):
            for c in range(mixer.channels):
                interleaved[i * mixer.channels + c] = s
        samples = interleaved

    out_pcm = samples.tobytes()
    if rate != mixer.sample_rate:
        log.info("resampled TTS %d Hz -> %d Hz for playback", rate, mixer.sample_rate)
    wav = mixer.build_wav(out_pcm)
    duration = mixer.total_duration_seconds(out_pcm)
    return wav, "wav", duration
