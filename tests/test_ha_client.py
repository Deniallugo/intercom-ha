import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import ha_client  # noqa: E402
from ha_client import HAClient  # noqa: E402


@pytest.fixture
def env_token(monkeypatch):
    monkeypatch.setitem(os.environ, "SUPERVISOR_TOKEN", "tok")


async def test_get_states_calls_supervisor(env_token):
    fake_resp = MagicMock(status=200)
    fake_resp.json = AsyncMock(return_value=[{"entity_id": "media_player.x"}])
    fake_session = MagicMock()
    fake_session.get = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    states = await client.get_states()

    assert states == [{"entity_id": "media_player.x"}]
    fake_session.get.assert_awaited_once()
    url, kwargs = fake_session.get.await_args.args[0], fake_session.get.await_args.kwargs
    assert url == "http://supervisor/core/api/states"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


async def test_get_states_raises_on_non_200(env_token):
    fake_resp = MagicMock(status=503)
    fake_session = MagicMock()
    fake_session.get = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    with pytest.raises(RuntimeError):
        await client.get_states()


async def test_play_media_posts_correct_body(env_token):
    fake_resp = MagicMock(status=200)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    await client.play_media("media_player.kitchen", "http://ha/local/x.wav")

    url = fake_session.post.await_args.args[0]
    body = fake_session.post.await_args.kwargs["json"]
    assert url == "http://supervisor/core/api/services/media_player/play_media"
    assert body == {
        "entity_id": "media_player.kitchen",
        "media_content_id": "http://ha/local/x.wav",
        "media_content_type": "music",
    }


async def test_pause_posts_pause_service(env_token):
    fake_resp = MagicMock(status=200)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    await client.pause("media_player.kitchen")

    url = fake_session.post.await_args.args[0]
    body = fake_session.post.await_args.kwargs["json"]
    assert url == "http://supervisor/core/api/services/media_player/media_pause"
    assert body == {"entity_id": "media_player.kitchen"}


async def test_play_posts_play_service(env_token):
    fake_resp = MagicMock(status=200)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    await client.play("media_player.kitchen")

    url = fake_session.post.await_args.args[0]
    body = fake_session.post.await_args.kwargs["json"]
    assert url == "http://supervisor/core/api/services/media_player/media_play"
    assert body == {"entity_id": "media_player.kitchen"}


async def test_tts_get_audio_posts_then_fetches(env_token):
    post_resp = MagicMock(status=200)
    post_resp.json = AsyncMock(return_value={
        "url": "http://ha/api/tts_proxy/x.wav",
        "path": "/api/tts_proxy/x.wav",
    })
    get_resp = MagicMock(status=200)
    get_resp.read = AsyncMock(return_value=b"RIFFfakeaudio")
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=post_resp)
    fake_session.get = AsyncMock(return_value=get_resp)

    client = HAClient(session=fake_session)
    audio = await client.tts_get_audio("tts.piper", "hello there")

    assert audio == b"RIFFfakeaudio"
    post_url = fake_session.post.await_args.args[0]
    post_kwargs = fake_session.post.await_args.kwargs
    assert post_url == "http://supervisor/core/api/tts_get_url"
    assert post_kwargs["json"] == {"engine_id": "tts.piper", "message": "hello there"}
    assert post_kwargs["headers"]["Authorization"] == "Bearer tok"
    get_url = fake_session.get.await_args.args[0]
    assert get_url == "http://supervisor/core/api/tts_proxy/x.wav"


async def test_tts_get_audio_raises_when_get_url_fails(env_token):
    post_resp = MagicMock(status=500)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=post_resp)
    client = HAClient(session=fake_session)
    with pytest.raises(RuntimeError):
        await client.tts_get_audio("tts.piper", "hi")


async def test_tts_get_audio_raises_on_missing_path(env_token):
    post_resp = MagicMock(status=200)
    post_resp.json = AsyncMock(return_value={"url": "http://ha/x.wav"})
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=post_resp)
    client = HAClient(session=fake_session)
    with pytest.raises(RuntimeError):
        await client.tts_get_audio("tts.piper", "hi")


class FakeWS:
    """Scripted WebSocket: replies to auth and to each command by type."""

    def __init__(self, replies, auth_ok=True):
        self.sent = []
        self._queue = [{"type": "auth_required", "ha_version": "2026.11.0"}]
        self._replies = replies
        self._auth_ok = auth_ok

    async def receive_json(self, timeout=None):
        return self._queue.pop(0)

    async def send_json(self, msg):
        self.sent.append(msg)
        if msg["type"] == "auth":
            self._queue.append({"type": "auth_ok" if self._auth_ok else "auth_invalid",
                                "message": "bad token"})
            return
        # An unrelated message first: the client must skip it.
        self._queue.append({"id": 999, "type": "event", "event": {}})
        result = self._replies[msg["type"]]
        if isinstance(result, Exception):
            self._queue.append({"id": msg["id"], "type": "result", "success": False,
                                "error": {"code": "x", "message": str(result)}})
        else:
            self._queue.append({"id": msg["id"], "type": "result", "success": True,
                                "result": result})


def ws_session(*sockets):
    session = MagicMock()
    connects = []

    def ws_connect(url, **kw):
        connects.append(url)
        ws = sockets[len(connects) - 1]
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=ws)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    session.ws_connect = ws_connect
    session.connects = connects
    return session


DEVICES = [{"id": "d1", "name": "Atom Echo", "config_entries": ["e1"]}]
ENTITIES = [{"entity_id": "media_player.atom_echo_player", "device_id": "d1",
             "platform": "esphome"}]
REPLIES = {"config/device_registry/list": DEVICES,
           "config/entity_registry/list": ENTITIES}


@pytest.fixture
def no_config_entries(monkeypatch, tmp_path):
    monkeypatch.setattr(ha_client, "CONFIG_ENTRIES_FILE", str(tmp_path / "missing"))


async def test_ws_commands_authenticates_and_returns_results(env_token):
    ws = FakeWS(REPLIES)
    client = HAClient(session=ws_session(ws))
    devices, entities = await client.ws_commands(
        "config/device_registry/list", "config/entity_registry/list")
    assert devices == DEVICES and entities == ENTITIES
    assert client.session.connects == ["ws://supervisor/core/websocket"]
    assert ws.sent[0] == {"type": "auth", "access_token": "tok"}
    assert ws.sent[1] == {"id": 1, "type": "config/device_registry/list"}
    assert ws.sent[2] == {"id": 2, "type": "config/entity_registry/list"}


async def test_ws_commands_raises_on_bad_auth(env_token):
    client = HAClient(session=ws_session(FakeWS(REPLIES, auth_ok=False)))
    with pytest.raises(RuntimeError, match="auth"):
        await client.ws_commands("config/device_registry/list")


async def test_ws_commands_raises_on_failed_command(env_token):
    client = HAClient(session=ws_session(FakeWS(
        {"config/device_registry/list": RuntimeError("unauthorized")})))
    with pytest.raises(RuntimeError, match="unauthorized"):
        await client.ws_commands("config/device_registry/list")


async def test_get_registry_caches_until_forced(env_token, no_config_entries):
    client = HAClient(session=ws_session(FakeWS(REPLIES), FakeWS(REPLIES)))
    first = await client.get_registry()
    assert first["devices"] == DEVICES and first["entities"] == ENTITIES
    assert first["esphome_names"] == {}
    assert await client.get_registry() is first
    assert len(client.session.connects) == 1
    await client.get_registry(force=True)
    assert len(client.session.connects) == 2


async def test_get_registry_invalidate_refetches(env_token, no_config_entries):
    client = HAClient(session=ws_session(FakeWS(REPLIES), FakeWS(REPLIES)))
    await client.get_registry()
    client.invalidate_registry()
    await client.get_registry()
    assert len(client.session.connects) == 2


async def test_get_registry_serves_stale_copy_when_refresh_fails(
    env_token, no_config_entries,
):
    broken = FakeWS({"config/device_registry/list": RuntimeError("down")})
    client = HAClient(session=ws_session(FakeWS(REPLIES), broken))
    first = await client.get_registry()
    assert await client.get_registry(force=True) is first


async def test_get_registry_raises_without_cache(env_token, no_config_entries):
    broken = FakeWS({"config/device_registry/list": RuntimeError("down")})
    client = HAClient(session=ws_session(broken))
    with pytest.raises(RuntimeError):
        await client.get_registry()


def test_read_esphome_node_names(tmp_path):
    f = tmp_path / "core.config_entries"
    f.write_text(json.dumps({"version": 1, "data": {"entries": [
        {"entry_id": "e1", "domain": "esphome",
         "data": {"host": "10.0.0.5", "device_name": "esphome-web-0f4600"}},
        {"entry_id": "e2", "domain": "esphome", "data": {"host": "10.0.0.6"}},
        {"entry_id": "e3", "domain": "hue", "data": {"device_name": "bridge"}},
    ]}}))
    assert ha_client.read_esphome_node_names(str(f)) == {"e1": "esphome-web-0f4600"}


def test_read_esphome_node_names_missing_or_garbage(tmp_path):
    assert ha_client.read_esphome_node_names(str(tmp_path / "nope")) == {}
    bad = tmp_path / "bad"
    bad.write_text("{not json")
    assert ha_client.read_esphome_node_names(str(bad)) == {}


async def test_tts_get_audio_raises_when_audio_fetch_fails(env_token):
    post_resp = MagicMock(status=200)
    post_resp.json = AsyncMock(return_value={"path": "/api/tts_proxy/x.wav"})
    get_resp = MagicMock(status=404)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=post_resp)
    fake_session.get = AsyncMock(return_value=get_resp)
    client = HAClient(session=fake_session)
    with pytest.raises(RuntimeError):
        await client.tts_get_audio("tts.piper", "hi")
