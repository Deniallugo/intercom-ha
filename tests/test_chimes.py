import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
from chimes import ChimeMixer, wav_header  # noqa: E402


def test_wav_header_is_44_bytes():
    assert len(wav_header(0, sample_rate=16000, channels=1, sample_width=2)) == 44


def test_wav_header_riff_tag():
    h = wav_header(100, sample_rate=16000, channels=1, sample_width=2)
    assert h[:4] == b"RIFF"


def test_wav_header_data_size_field():
    h = wav_header(200, sample_rate=16000, channels=1, sample_width=2)
    assert struct.unpack_from("<I", h, 40)[0] == 200


def test_chime_length_matches_duration():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    # 120ms chime at 16000 Hz mono 16-bit = 16000 * 0.120 * 2 = 3840 bytes
    assert len(mixer.chime_in) == 3840
    assert len(mixer.chime_out) == 3840


def test_chime_changes_with_sample_rate():
    a = ChimeMixer(sample_rate=8000, sample_width=2, channels=1).chime_in
    b = ChimeMixer(sample_rate=16000, sample_width=2, channels=1).chime_in
    assert len(b) == len(a) * 2


def test_build_wav_total_length():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x10\x20" * 100
    wav = mixer.build_wav(payload)
    expected_pcm_len = len(mixer.chime_in) + len(payload) + len(mixer.chime_out)
    assert len(wav) == 44 + expected_pcm_len


def test_build_wav_header_data_size_matches_pcm():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x10\x20" * 100
    wav = mixer.build_wav(payload)
    pcm_len = struct.unpack_from("<I", wav, 40)[0]
    assert pcm_len == len(mixer.chime_in) + len(payload) + len(mixer.chime_out)


def test_build_wav_payload_position():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\xAA\xBB" * 50
    wav = mixer.build_wav(payload)
    start = 44 + len(mixer.chime_in)
    end = start + len(payload)
    assert wav[start:end] == payload


def test_pcm_duration_seconds():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x00" * (16000 * 2)  # exactly 1s at 16k/16/1
    assert mixer.pcm_duration_seconds(payload) == pytest.approx(1.0)


def test_total_duration_includes_chimes():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x00" * (16000 * 2)  # 1s
    total = mixer.total_duration_seconds(payload)
    # 1s payload + 0.120s + 0.120s = 1.240s
    assert total == pytest.approx(1.240, abs=0.001)
