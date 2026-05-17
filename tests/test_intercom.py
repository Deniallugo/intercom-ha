import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv


def test_wav_header_is_44_bytes():
    assert len(srv.wav_header(0)) == 44


def test_wav_header_riff_tag():
    assert srv.wav_header(100)[:4] == b"RIFF"


def test_wav_header_wave_tag():
    assert srv.wav_header(100)[8:12] == b"WAVE"


def test_wav_header_total_size():
    h = srv.wav_header(100)
    total = struct.unpack_from("<I", h, 4)[0]
    assert total == 136   # 36 + 100


def test_wav_header_sample_rate_is_16000():
    h = srv.wav_header(0)
    assert struct.unpack_from("<I", h, 24)[0] == 16000


def test_wav_header_16bit():
    h = srv.wav_header(0)
    assert struct.unpack_from("<H", h, 34)[0] == 16


def test_wav_header_data_size():
    h = srv.wav_header(200)
    assert struct.unpack_from("<I", h, 40)[0] == 200
