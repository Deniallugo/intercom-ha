import json
import sys
import wave
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402
import recordings  # noqa: E402
import players as players_mod  # noqa: E402


@pytest.fixture
def rec_dir(monkeypatch, tmp_path):
    d = tmp_path / "recordings"
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", str(d))
    return d


def _wav(seconds: float = 0.5, rate: int = 16000) -> bytes:
    return srv.mixer.build_plain_wav(b"\x00\x00" * int(rate * seconds))


# ── storage ──────────────────────────────────────────────────────────────────

def test_save_writes_a_playable_wav(rec_dir):
    path = recordings.save(_wav(), source="voice-s3", session_id="abcdef123", keep=5)
    assert path is not None and path.exists()
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000
        assert w.getnframes() == 8000


def test_save_disabled_when_keep_is_zero(rec_dir):
    assert recordings.save(_wav(), source="a", session_id="b", keep=0) is None
    assert not rec_dir.exists()


def test_save_sanitises_source_and_session(rec_dir):
    path = recordings.save(
        _wav(), source="../../etc/pwn", session_id="../..", keep=5
    )
    assert path.parent == rec_dir
    assert "/" not in path.name and ".." not in path.name


def test_prune_keeps_newest(rec_dir):
    rec_dir.mkdir(parents=True)
    for i in range(5):
        p = rec_dir / f"20260101-00000{i}-dev-sid{i}.wav"
        p.write_bytes(_wav(0.1))
        import os
        os.utime(p, (1000 + i, 1000 + i))

    assert recordings.prune(2) == 3
    remaining = sorted(p.name for p in rec_dir.glob("*.wav"))
    assert remaining == ["20260101-000003-dev-sid3.wav", "20260101-000004-dev-sid4.wav"]


def test_listing_is_newest_first_with_metadata(rec_dir):
    import os
    rec_dir.mkdir(parents=True)
    for i, name in enumerate(["20260101-000000-kitchen-aaa.wav",
                              "20260101-000001-terrace-bbb.wav"]):
        p = rec_dir / name
        p.write_bytes(_wav(0.25))
        os.utime(p, (2000 + i, 2000 + i))

    items = recordings.listing()
    assert [i["name"] for i in items] == ["20260101-000001-terrace-bbb.wav",
                                          "20260101-000000-kitchen-aaa.wav"]
    assert items[0]["source"] == "terrace"
    assert items[0]["seconds"] == pytest.approx(0.25)
    assert items[0]["bytes"] > 0


def test_listing_ignores_partial_writes(rec_dir):
    rec_dir.mkdir(parents=True)
    (rec_dir / "20260101-000000-dev-aaa.wav.part").write_bytes(b"nope")
    assert recordings.listing() == []


def test_duration_is_none_for_a_corrupt_file(rec_dir):
    rec_dir.mkdir(parents=True)
    p = rec_dir / "20260101-000000-dev-aaa.wav"
    p.write_bytes(b"not a wav")
    assert recordings.listing()[0]["seconds"] is None


@pytest.mark.parametrize("name", [
    "../options.json",
    "..%2Foptions.json",
    "/etc/passwd",
    ".hidden.wav",
    "players.json",
    "",
])
def test_path_for_rejects_unsafe_names(rec_dir, name):
    assert recordings.path_for(name) is None


def test_path_for_accepts_a_stored_name(rec_dir):
    path = recordings.save(_wav(), source="dev", session_id="sid", keep=5)
    assert recordings.path_for(path.name) == path


def test_delete_removes_only_stored_files(rec_dir, tmp_path):
    outside = tmp_path / "secret.wav"
    outside.write_bytes(b"x")
    path = recordings.save(_wav(), source="dev", session_id="sid", keep=5)

    assert recordings.delete("../secret.wav") is False
    assert outside.exists()
    assert recordings.delete(path.name) is True
    assert not path.exists()


def test_source_of_handles_dashed_device_names():
    assert recordings.source_of("20260101-000000-voice-s3-abc12345.wav") == "voice-s3"
    assert recordings.source_of("garbage.wav") == "unknown"


# ── endpoints ────────────────────────────────────────────────────────────────

@pytest.fixture
def ingress_app():
    return srv.make_ingress_app()


@pytest.fixture
def lan_app():
    app = web.Application()
    app.router.add_post("/intercom", srv.handle_intercom)
    return app


@pytest.fixture
def options_file(monkeypatch, tmp_path):
    """Real options.json so keep_recordings() exercises its parsing."""
    p = tmp_path / "options.json"
    p.write_text(json.dumps({"ha_url": "http://ha.test:8123", "keep_recordings": 3}))
    monkeypatch.setattr(srv, "OPTIONS_FILE", str(p))
    return p


@pytest.fixture
def www_dir(monkeypatch, tmp_path):
    d = tmp_path / "www"
    d.mkdir()
    monkeypatch.setattr(srv, "CONFIG_WWW", str(d))
    return d


@pytest.fixture
def players_file(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    p.write_text(json.dumps({"routes": {}, "default": [], "aliases": {}, "selves": {}}))
    monkeypatch.setattr(players_mod, "PLAYERS_FILE", str(p))
    return p


@pytest.fixture
def fake_ha(monkeypatch):
    monkeypatch.setattr(srv.ha, "play_media", AsyncMock(return_value=204))
    monkeypatch.setattr(srv.ha, "get_state",
                        AsyncMock(return_value={"state": "idle", "attributes": {}}))
    monkeypatch.setattr(srv.ha, "pause", AsyncMock(return_value=200))
    monkeypatch.setattr(srv.ha, "play", AsyncMock(return_value=200))
    return srv.ha


def test_keep_recordings_defaults_when_option_missing(monkeypatch, tmp_path):
    p = tmp_path / "options.json"
    p.write_text(json.dumps({"ha_url": "x"}))
    monkeypatch.setattr(srv, "OPTIONS_FILE", str(p))
    assert srv.keep_recordings() == srv.DEFAULT_KEEP_RECORDINGS


def test_keep_recordings_survives_a_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "OPTIONS_FILE", str(tmp_path / "nope.json"))
    assert srv.keep_recordings() == srv.DEFAULT_KEEP_RECORDINGS


def test_keep_recordings_clamps_negative(monkeypatch, tmp_path):
    p = tmp_path / "options.json"
    p.write_text(json.dumps({"keep_recordings": -5}))
    monkeypatch.setattr(srv, "OPTIONS_FILE", str(p))
    assert srv.keep_recordings() == 0


async def test_list_endpoint_reports_items(aiohttp_client, ingress_app, rec_dir,
                                           options_file):
    recordings.save(_wav(), source="voice-s3", session_id="sid", keep=3)
    client = await aiohttp_client(ingress_app)
    body = await (await client.get("/api/recordings")).json()
    assert body["keep"] == 3
    assert len(body["items"]) == 1
    assert body["items"][0]["source"] == "voice-s3"


async def test_get_endpoint_serves_the_wav(aiohttp_client, ingress_app, rec_dir,
                                           options_file):
    path = recordings.save(_wav(), source="dev", session_id="sid", keep=3)
    client = await aiohttp_client(ingress_app)
    resp = await client.get(f"/api/recordings/{path.name}")
    assert resp.status == 200
    assert resp.headers["Content-Type"] == "audio/wav"
    assert (await resp.read())[:4] == b"RIFF"


async def test_get_endpoint_rejects_traversal(aiohttp_client, ingress_app, rec_dir,
                                              options_file):
    client = await aiohttp_client(ingress_app)
    assert (await client.get("/api/recordings/..%2Foptions.json")).status == 404
    assert (await client.get("/api/recordings/nope.wav")).status == 404


async def test_delete_endpoint(aiohttp_client, ingress_app, rec_dir, options_file):
    path = recordings.save(_wav(), source="dev", session_id="sid", keep=3)
    client = await aiohttp_client(ingress_app)
    assert (await client.delete(f"/api/recordings/{path.name}")).status == 204
    assert not path.exists()
    assert (await client.delete(f"/api/recordings/{path.name}")).status == 404


async def test_intercom_upload_is_retained_without_chimes(
    aiohttp_client, lan_app, rec_dir, options_file, www_dir, players_file, fake_ha,
):
    client = await aiohttp_client(lan_app)
    pcm = b"\x01\x00" * 1600  # 0.1 s
    resp = await client.post("/intercom", data=pcm,
                             headers={"X-Session-ID": "sid1", "X-Device-Name": "voice-s3"})
    assert resp.status == 204

    items = recordings.listing()
    assert len(items) == 1 and items[0]["source"] == "voice-s3"
    # Chime-free: exactly the PCM that was uploaded, no 120 ms tones added.
    with wave.open(str(recordings.path_for(items[0]["name"])), "rb") as w:
        assert w.getnframes() == 1600


async def test_intercom_still_broadcasts_when_retention_fails(
    monkeypatch, aiohttp_client, lan_app, rec_dir, options_file, www_dir,
    players_file, fake_ha,
):
    def boom(*a, **kw):
        raise OSError("read-only volume")
    monkeypatch.setattr(recordings, "save", boom)

    players_file.write_text(json.dumps({
        "routes": {"voice-s3": ["media_player.kitchen"]}, "default": [],
    }))
    client = await aiohttp_client(lan_app)
    resp = await client.post("/intercom", data=b"\x00" * 64,
                             headers={"X-Session-ID": "sid2", "X-Device-Name": "voice-s3"})
    assert resp.status == 204
    assert fake_ha.play_media.await_count == 1


async def test_retention_disabled_keeps_nothing(
    monkeypatch, aiohttp_client, lan_app, rec_dir, options_file, www_dir,
    players_file, fake_ha,
):
    options_file.write_text(json.dumps({"ha_url": "x", "keep_recordings": 0}))
    client = await aiohttp_client(lan_app)
    await client.post("/intercom", data=b"\x00" * 64,
                      headers={"X-Session-ID": "sid3", "X-Device-Name": "voice-s3"})
    assert recordings.listing() == []
