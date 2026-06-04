import array
import io
import logging
import wave

from chimes import ChimeMixer

log = logging.getLogger(__name__)

# When we can't measure an announcement's length (the engine returned a format
# we can't decode), report this generous floor instead of 0 so the caller's
# duck-restore and file-cleanup grace windows don't truncate it mid-playback.
FALLBACK_DURATION_SECONDS = 30.0


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
    """Return (bytes, ext, duration_seconds).

    If the TTS audio is a 16-bit PCM WAV, resample it to ``mixer``'s format and
    build a chime+speech+chime WAV at that rate. The whole intercom chain (and
    the device I2S speakers, whose DMA buffers are sized for it) is built around
    the addon's configured rate, so announcements MUST be delivered at it — a
    native-rate TTS WAV (e.g. Piper's 22.05 kHz) makes the no-PSRAM Atom Echo's
    speaker fail to allocate its DMA buffers and spin in a retry loop.
    Non-16-bit / unparseable TTS output degrades to chime-less playback.
    """
    parsed = parse_tts_wav(audio)
    if parsed is None:
        log.warning("TTS audio not a parseable WAV; playing without chime")
        return audio, "mp3", FALLBACK_DURATION_SECONDS
    pcm, rate, width, channels = parsed
    if width != 2:
        # Can't resample/mix (16-bit only), but we still know the true length
        # from the PCM, so report it accurately.
        duration = len(pcm) / (rate * width * channels)
        log.warning("TTS WAV is %d-bit, not 16-bit; playing without chime", width * 8)
        return audio, "wav", duration

    samples = array.array("h")
    samples.frombytes(pcm)
    samples = _downmix_to_mono(samples, channels)
    samples = _resample_mono16(samples, rate, mixer.sample_rate)
    if mixer.channels > 1:
        # ChimeMixer pre-renders its chimes at mixer.channels, so the speech must
        # match. Duplicate the mono signal across channels.
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
