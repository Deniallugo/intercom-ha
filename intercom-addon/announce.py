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


def build_announcement_wav(audio: bytes):
    """Return (bytes, ext, duration_seconds).

    If the TTS audio is a 16-bit PCM WAV, build a chime+speech+chime WAV at the
    audio's native format (the chime is generated per-rate, so no resampling).
    Otherwise return the raw bytes with no chime (degraded fallback).
    """
    parsed = parse_tts_wav(audio)
    if parsed is None:
        log.warning("TTS audio not a parseable WAV; playing without chime")
        return audio, "mp3", FALLBACK_DURATION_SECONDS
    pcm, rate, width, channels = parsed
    if width != 2:
        # Can't mix the chime (16-bit only), but we still know the true length
        # from the PCM, so report it accurately.
        duration = len(pcm) / (rate * width * channels)
        log.warning("TTS WAV is %d-bit, not 16-bit; playing without chime", width * 8)
        return audio, "wav", duration
    mixer = ChimeMixer(sample_rate=rate, sample_width=width, channels=channels)
    wav = mixer.build_wav(pcm)
    duration = mixer.total_duration_seconds(pcm)
    return wav, "wav", duration
