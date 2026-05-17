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


import os
import uuid
from unittest.mock import patch

from aiohttp import web


FAKE_OPTIONS = {
    "ha_url": "http://ha.test:8123",
    "port": 9999,
    "media_players": ["media_player.sonos_test"],
}


class _FakeResponse:
    status = 204


class _FakeSession:
    def __init__(self):
        self.calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeResponse()


@pytest.fixture(autouse=True)
def _clear_sessions():
    srv.sessions.clear()
    yield
    srv.sessions.clear()


@pytest.fixture
def fake_env(monkeypatch, tmp_path):
    monkeypatch.setitem(os.environ, "SUPERVISOR_TOKEN", "tok")
    monkeypatch.setattr(srv, "CONFIG_WWW", str(tmp_path))
    monkeypatch.setattr(srv, "load_options", lambda: FAKE_OPTIONS)


@pytest.fixture
def app():
    application = web.Application()
    application.router.add_post("/intercom", srv.handle_intercom)
    return application


async def test_single_chunk_creates_wav(aiohttp_client, app, fake_env, tmp_path):
    client = await aiohttp_client(app)
    pcm = b"\x10\x20" * 100
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=_FakeSession()):
        resp = await client.post(
            "/intercom", data=pcm,
            headers={"X-Session-ID": sid, "X-Chunk-Index": "0", "X-Final": "1"},
        )

    assert resp.status == 204
    wav = (tmp_path / f"intercom-{sid}.wav").read_bytes()
    assert wav[:4] == b"RIFF"
    assert wav[44:] == pcm


async def test_intermediate_chunk_no_file(aiohttp_client, app, fake_env, tmp_path):
    client = await aiohttp_client(app)
    sid = str(uuid.uuid4())
    resp = await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": sid, "X-Chunk-Index": "0"},
    )
    assert resp.status == 204
    assert not list(tmp_path.glob("*.wav"))


async def test_chunks_reassembled_in_order(aiohttp_client, app, fake_env, tmp_path):
    client = await aiohttp_client(app)
    sid = str(uuid.uuid4())
    chunk0, chunk1 = b"\x01" * 50, b"\x02" * 50
    fake_session = _FakeSession()

    with patch("intercom.ClientSession", return_value=fake_session):
        # Send chunk 1 first (out of order)
        await client.post(
            "/intercom", data=chunk1,
            headers={"X-Session-ID": sid, "X-Chunk-Index": "1"},
        )
        await client.post(
            "/intercom", data=chunk0,
            headers={"X-Session-ID": sid, "X-Chunk-Index": "0", "X-Final": "1"},
        )

    wav = (tmp_path / f"intercom-{sid}.wav").read_bytes()
    assert wav[44:] == chunk0 + chunk1


async def test_ha_api_called_with_correct_url(aiohttp_client, app, fake_env, tmp_path):
    client = await aiohttp_client(app)
    sid = str(uuid.uuid4())
    fake_session = _FakeSession()

    with patch("intercom.ClientSession", return_value=fake_session):
        await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Chunk-Index": "0", "X-Final": "1"},
        )

    assert len(fake_session.calls) == 1
    _url, kwargs = fake_session.calls[0]
    body = kwargs["json"]
    assert body["entity_id"] == "media_player.sonos_test"
    assert f"intercom-{sid}.wav" in body["media_content_id"]
    assert body["media_content_id"].startswith("http://ha.test:8123/local/")
