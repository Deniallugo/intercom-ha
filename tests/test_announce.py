import io
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import announce  # noqa: E402
from chimes import ChimeMixer  # noqa: E402

# Announcements must arrive at the add-on's format, not the TTS native rate.
TARGET = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)


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


def test_build_announcement_wav_resamples_to_target_rate():
    # 22.05 kHz in -> 16 kHz out (Atom Echo DMA buffers are sized for it).
    speech_frames = 22050
    pcm = b"\x01\x02" * speech_frames
    wav_in = _make_wav(pcm, rate=22050, width=2, channels=1)
    out, ext, duration = announce.build_announcement_wav(wav_in, TARGET)
    assert ext == "wav"
    with wave.open(io.BytesIO(out), "rb") as w:
        assert w.getframerate() == 16000
        assert w.getnchannels() == 1
        total_frames = w.getnframes()
    # ~1 s of resampled speech (16000 frames) plus the two chimes.
    resampled_speech = round(speech_frames * 16000 / 22050)
    chime_frames = total_frames - resampled_speech
    assert chime_frames > 0
    # Real-time duration is preserved across the resample: ~1 s of speech plus
    # the two chimes (2 * CHIME_MS = 0.24 s).
    assert abs(duration - 1.24) < 0.05


def test_build_announcement_wav_no_resample_when_rate_matches():
    pcm = b"\x01\x02" * 16000
    wav_in = _make_wav(pcm, rate=16000, width=2, channels=1)
    out, ext, duration = announce.build_announcement_wav(wav_in, TARGET)
    assert ext == "wav"
    with wave.open(io.BytesIO(out), "rb") as w:
        assert w.getframerate() == 16000


def test_build_announcement_wav_falls_back_for_non_wav():
    raw = b"ID3 this is actually mp3 bytes"
    out, ext, duration = announce.build_announcement_wav(raw, TARGET)
    assert out == raw
    assert ext == "mp3"
    # Unmeasurable audio: a generous floor so ducking/cleanup don't truncate it.
    assert duration == announce.FALLBACK_DURATION_SECONDS


def test_build_announcement_wav_reports_real_duration_for_non_16bit_wav():
    # 24-bit: not mixable, but the length is still measured.
    rate, width, channels = 22050, 3, 1
    frames = 5000
    pcm = b"\x00\x00\x00" * frames
    wav_in = _make_wav(pcm, rate=rate, width=width, channels=channels)
    out, ext, duration = announce.build_announcement_wav(wav_in, TARGET)
    assert out == wav_in  # raw bytes, no chime
    assert ext == "wav"
    expected = frames / rate
    assert abs(duration - expected) < 1e-6


def _mp3_frame(bitrate_idx: int, pad: int = 0) -> bytes:
    # MPEG-1 layer III, 44.1 kHz, no CRC.
    h = (0x7FF << 21) | (3 << 19) | (1 << 17) | (1 << 16) | (bitrate_idx << 12) | (pad << 9)
    bitrate = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320][bitrate_idx]
    size = 144 * bitrate * 1000 // 44100 + pad
    return h.to_bytes(4, "big") + b"\x00" * (size - 4)


def test_mp3_duration_sums_frames_after_id3_and_ignores_trailer():
    id3 = b"ID3\x04\x00\x00" + bytes([0, 0, 0, 10]) + b"\x00" * 10
    # VBR: frames of different bitrates, one padded.
    frames = _mp3_frame(9) * 30 + _mp3_frame(5, pad=1) * 10 + _mp3_frame(14) * 2
    data = id3 + frames + b"TAG" + b"\x00" * 125
    assert abs(announce.mp3_duration(data) - 42 * 1152 / 44100) < 1e-9


def test_mp3_duration_none_for_garbage():
    assert announce.mp3_duration(b"\x00" * 500) is None


def test_build_announcement_wav_times_mp3_tts():
    data = _mp3_frame(9) * 77          # ~2.0 s
    out, ext, duration = announce.build_announcement_wav(data, TARGET)
    assert (out, ext) == (data, "mp3")
    assert abs(duration - 77 * 1152 / 44100) < 1e-9
