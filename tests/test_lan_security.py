"""LAN port: optional shared token, per-request sample rate, trimmed options."""
import io
import json
import sys
import wave
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402
import players as players_mod  # noqa: E402
import recordings  # noqa: E402
from conftest import MEDIA_BASE  # noqa: E402

CONFIG_YAML = Path(__file__).parent.parent / "intercom-addon" / "config.yaml"
TOKEN = "s3cret-token-0123456789"


@pytest.fixture
def setup(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    p.write_text(json.dumps({"routes": {"src-a": ["media_player.kitchen"]},
                             "default": []}))
    monkeypatch.setattr(players_mod, "PLAYERS_FILE", str(p))
    monkeypatch.setattr(srv, "CONFIG_WWW", str(tmp_path / "www"))
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", str(tmp_path / "rec"))
    monkeypatch.setattr(srv, "load_options",
                        lambda: {"denoise": False, "keep_recordings": 5})
    for name, value in {"play_media": 204, "pause": 200, "play": 200,
                        "get_states": [], "tts_get_audio": b"",
                        "get_state": {"state": "idle", "attributes": {}},
                        "get_registry": {"devices": [], "entities": []}}.items():
        monkeypatch.setattr(srv.ha, name, AsyncMock(return_value=value))
    srv.ducker._snapshots.clear()
    srv.ducker._deadlines.clear()
    srv.ducker._tasks.clear()


def _post(client, path="/intercom", headers=None, **kw):
    h = {"X-Device-Name": "src-a"}
    h.update(headers or {})
    return client.post(path, data=b"\x01\x00" * 160, headers=h, **kw)


# ── lan_token ────────────────────────────────────────────────────────────────

async def test_no_token_configured_keeps_flashed_devices_working(aiohttp_client, setup):
    client = await aiohttp_client(srv.make_lan_app(token=""))
    assert (await _post(client)).status == 200


@pytest.mark.parametrize("path", ["/intercom", "/intercom/reply", "/announce"])
async def test_token_required_on_every_lan_endpoint(aiohttp_client, setup, path):
    client = await aiohttp_client(srv.make_lan_app(token=TOKEN))
    assert (await _post(client, path)).status == 401
    resp = await _post(client, path, headers={"Authorization": "Bearer wrong"})
    assert resp.status == 401
    assert resp.headers["WWW-Authenticate"] == "Bearer"
    assert srv.ha.play_media.await_count == 0


async def test_bearer_token_accepted(aiohttp_client, setup):
    client = await aiohttp_client(srv.make_lan_app(token=TOKEN))
    resp = await _post(client, headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    assert srv.ha.play_media.await_count == 1


async def test_query_token_accepted_for_url_only_firmware(aiohttp_client, setup):
    """uploader.h keeps the query in the path: intercom_url can carry it."""
    client = await aiohttp_client(srv.make_lan_app(token=TOKEN))
    assert (await _post(client, f"/intercom?token={TOKEN}")).status == 200
    assert (await _post(client, "/intercom?token=nope")).status == 401


async def test_media_needs_no_token(aiohttp_client, setup):
    """HA's ffmpeg proxy and Cast fetch the URL bare; the name is the secret."""
    client = await aiohttp_client(srv.make_lan_app(token=TOKEN))
    await _post(client, headers={"Authorization": f"Bearer {TOKEN}"})
    url = srv.ha.play_media.await_args.args[1]
    assert (await client.get(url[len(MEDIA_BASE):])).status == 200


def test_lan_token_option_parsing(monkeypatch):
    monkeypatch.setattr(srv, "load_options", lambda: {"lan_token": "  abc "})
    assert srv.lan_token() == "abc"
    monkeypatch.setattr(srv, "load_options", lambda: {})
    assert srv.lan_token() == ""
    monkeypatch.setattr(srv, "load_options", lambda: {"lan_token": None})
    assert srv.lan_token() == ""

    def broken():
        raise OSError("gone")
    monkeypatch.setattr(srv, "load_options", broken)
    assert srv.lan_token() == ""


# ── X-Sample-Rate ────────────────────────────────────────────────────────────

def test_parse_sample_rate():
    assert srv.parse_sample_rate(None) == 16000
    assert srv.parse_sample_rate("") == 16000
    assert srv.parse_sample_rate(" 48000 ") == 48000
    assert srv.parse_sample_rate("22050") == 22050
    for bad in ("abc", "0", "16001", "96000", "-16000"):
        assert srv.parse_sample_rate(bad) is None


async def test_upload_without_header_is_16k(aiohttp_client, setup):
    client = await aiohttp_client(srv.make_lan_app(token=""))
    await _post(client)
    [item] = recordings.listing()
    with wave.open(str(recordings.path_for(item["name"])), "rb") as w:
        assert w.getframerate() == 16000


async def test_upload_uses_x_sample_rate(aiohttp_client, setup, fake_streams):
    client = await aiohttp_client(srv.make_lan_app(token=""))
    resp = await _post(client, headers={"X-Sample-Rate": "48000"})
    assert resp.status == 200
    assert [s.sample_rate for s in fake_streams.made] == [48000]
    [item] = recordings.listing()
    with wave.open(str(recordings.path_for(item["name"])), "rb") as w:
        assert w.getframerate() == 48000
    url = srv.ha.play_media.await_args.args[1]
    body = await (await client.get(url[len(MEDIA_BASE):])).read()
    with wave.open(io.BytesIO(body), "rb") as w:
        assert w.getframerate() == 48000
        # chimes rendered at 48 kHz: 2 x 120 ms + 160 payload frames
        assert w.getnframes() == 2 * 5760 + 160
    assert srv.mixer.sample_rate == 16000      # announcements unaffected


async def test_bad_sample_rate_is_rejected(aiohttp_client, setup):
    client = await aiohttp_client(srv.make_lan_app(token=""))
    resp = await _post(client, headers={"X-Sample-Rate": "12345"})
    assert resp.status == 400
    assert srv.ha.play_media.await_count == 0


# ── options ──────────────────────────────────────────────────────────────────

def _section(name: str) -> dict:
    out, inside = {}, False
    for line in CONFIG_YAML.read_text().splitlines():
        if not line.startswith(" "):
            inside = line.rstrip() == f"{name}:"
            continue
        if inside and ":" in line:
            key, _, value = line.strip().partition(":")
            out[key] = value.strip().strip('"')
    return out


def test_manifest_drops_options_that_could_only_break_things():
    options, schema = _section("options"), _section("schema")
    for gone in ("port", "ha_url", "sample_rate", "bits_per_sample", "channels"):
        assert gone not in options and gone not in schema
    assert options["keep_recordings"] == "0"
    assert schema["lan_token"] == "password?"
    assert "lan_token" not in options          # optional: absent = auth off
    assert _section("ports") == {"9999/tcp": "9999"}


def test_access_log_hides_query_token_and_media_names():
    from unittest.mock import MagicMock
    logger = MagicMock()
    access = srv.PathOnlyAccessLogger(logger, "")
    req = MagicMock(remote="10.0.0.5", method="POST", path="/intercom")
    access.log(req, MagicMock(status=200), 0.1)
    req2 = MagicMock(remote="10.0.0.5", method="GET", path="/media/SECRETNAME.wav")
    access.log(req2, MagicMock(status=200), 0.1)
    lines = [c.args[0] % c.args[1:] for c in logger.info.call_args_list]
    assert "/intercom" in lines[0] and "token" not in lines[0]
    assert "SECRETNAME" not in lines[1]
