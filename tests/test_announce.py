import io
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import announce  # noqa: E402


def _make_wav(pcm: bytes, rate: int = 22050, width: int = 2, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def test_parse_tts_wav_extracts_format_and_pcm():
    pcm = b"\x01\x02" * 50
    wav = _make_wav(pcm, rate=22050, width=2, channels=1)
    parsed = announce.parse_tts_wav(wav)
    assert parsed is not None
    out_pcm, rate, width, channels = parsed
    assert out_pcm == pcm
    assert (rate, width, channels) == (22050, 2, 1)


def test_parse_tts_wav_returns_none_for_non_wav():
    assert announce.parse_tts_wav(b"ID3\x03not an mp3 really") is None


def test_build_announcement_wav_mixes_chime_at_native_rate():
    pcm = b"\xAA\xBB" * 100  # 200 bytes
    wav_in = _make_wav(pcm, rate=22050, width=2, channels=1)
    out, ext, duration = announce.build_announcement_wav(wav_in)
    assert ext == "wav"
    with wave.open(io.BytesIO(out), "rb") as w:
        assert w.getframerate() == 22050
        total_frames = w.getnframes()
    speech_frames = len(pcm) // 2
    assert total_frames > speech_frames
    assert duration > speech_frames / 22050


def test_build_announcement_wav_falls_back_for_non_wav():
    raw = b"ID3 this is actually mp3 bytes"
    out, ext, duration = announce.build_announcement_wav(raw)
    assert out == raw
    assert ext == "mp3"
    # Unmeasurable audio: a generous floor so ducking/cleanup don't truncate it.
    assert duration == announce.FALLBACK_DURATION_SECONDS


def test_build_announcement_wav_reports_real_duration_for_non_16bit_wav():
    # 24-bit WAV: ChimeMixer can't mix it (16-bit only), but we can still
    # measure its true length from the PCM so ducking/cleanup aren't truncated.
    rate, width, channels = 22050, 3, 1
    frames = 5000
    pcm = b"\x00\x00\x00" * frames
    wav_in = _make_wav(pcm, rate=rate, width=width, channels=channels)
    out, ext, duration = announce.build_announcement_wav(wav_in)
    assert out == wav_in  # raw bytes, no chime
    assert ext == "wav"
    expected = frames / rate
    assert abs(duration - expected) < 1e-6
