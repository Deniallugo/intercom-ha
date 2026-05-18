import json
import logging
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402
import players as players_mod  # noqa: E402


@pytest.fixture
def players_file(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    monkeypatch.setattr(players_mod, "PLAYERS_FILE", str(p))
    return p


@pytest.fixture
def fake_ha(monkeypatch):
    """Replace srv.ha methods with AsyncMock stubs; tests configure them as needed."""
    monkeypatch.setattr(srv.ha, "get_states", AsyncMock(return_value=[]))
    monkeypatch.setattr(srv.ha, "play_media", AsyncMock(return_value=204))
    monkeypatch.setattr(srv.ha, "get_state", AsyncMock(return_value={"state": "idle", "attributes": {}}))
    monkeypatch.setattr(srv.ha, "pause", AsyncMock(return_value=200))
    monkeypatch.setattr(srv.ha, "play", AsyncMock(return_value=200))
    return srv.ha


def _drop_ducker_state():
    srv.ducker._snapshots.clear()
    srv.ducker._deadlines.clear()
    # Tasks were created in the previous test's event loop, which is now
    # gone — just drop the references; the loop closure already cancelled them.
    srv.ducker._tasks.clear()


@pytest.fixture(autouse=True)
def _reset_ducker():
    _drop_ducker_state()
    yield
    _drop_ducker_state()


@pytest.fixture(autouse=True)
def _reset_talkback():
    srv.talkback._windows.clear()
    yield
    srv.talkback._windows.clear()


async def test_fetch_media_players_filters_and_maps(fake_ha):
    fake_ha.get_states.return_value = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "light.bulb", "attributes": {"friendly_name": "Bulb"}},
        {"entity_id": "media_player.bedroom", "attributes": {}},
    ]
    result = await srv.fetch_media_players()
    assert result == [
        {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen"},
        {"entity_id": "media_player.bedroom", "friendly_name": "media_player.bedroom"},
    ]


async def test_fetch_media_players_raises_on_non_200(fake_ha):
    fake_ha.get_states.side_effect = RuntimeError("503")
    with pytest.raises(RuntimeError):
        await srv.fetch_media_players()


@pytest.fixture
def ingress_app():
    app = web.Application()
    app.router.add_get("/api/players", srv.handle_picker_get)
    app.router.add_post("/api/players", srv.handle_picker_post)
    return app


async def test_get_players_merges_available_and_routes(
    aiohttp_client, ingress_app, players_file, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    fake_ha.get_states.return_value = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "media_player.bedroom", "attributes": {"friendly_name": "Bedroom"}},
    ]
    client = await aiohttp_client(ingress_app)
    resp = await client.get("/api/players")
    body = await resp.json()

    assert resp.status == 200
    assert body["available"] == [
        {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen"},
        {"entity_id": "media_player.bedroom", "friendly_name": "Bedroom"},
    ]
    assert body["routes"] == {"src-a": ["media_player.kitchen"]}
    assert body["default"] == ["media_player.bedroom"]


async def test_get_players_supervisor_failure_returns_502(
    aiohttp_client, ingress_app, players_file, fake_ha,
):
    fake_ha.get_states.side_effect = RuntimeError("boom")
    client = await aiohttp_client(ingress_app)
    resp = await client.get("/api/players")
    body = await resp.json()

    assert resp.status == 502
    assert "error" in body


async def test_post_players_writes_file(aiohttp_client, ingress_app, players_file):
    client = await aiohttp_client(ingress_app)
    payload = {
        "routes": {"src-a": ["media_player.kitchen", "media_player.bedroom"]},
        "default": ["media_player.kitchen"],
    }
    resp = await client.post("/api/players", json=payload)

    assert resp.status == 204
    saved = json.loads(players_file.read_text())
    assert saved["routes"] == payload["routes"]
    assert saved["default"] == payload["default"]
    assert saved["aliases"] == {}
    assert saved["selves"] == {}


async def test_post_players_rejects_non_media_player_target(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {"src-a": ["light.bulb"]},
        "default": [],
    })
    assert resp.status == 400
    assert not players_file.exists()


async def test_post_players_rejects_non_list_route_value(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {"src-a": "media_player.kitchen"},  # str, not list
        "default": [],
    })
    assert resp.status == 400


async def test_post_players_rejects_empty_source_key(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {"": ["media_player.kitchen"]},
        "default": [],
    })
    assert resp.status == 400


async def test_post_players_rejects_non_media_player_default(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {},
        "default": ["light.bulb"],
    })
    assert resp.status == 400


async def test_post_players_rejects_missing_fields(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={"routes": {}})  # no default
    assert resp.status == 400


async def test_get_players_includes_aliases_and_selves(
    aiohttp_client, ingress_app, players_file, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"a": []},
        "default": [],
        "aliases": {"a": "Kitchen"},
        "selves": {"a": "media_player.kitchen_player"},
    }))
    fake_ha.get_states.return_value = []
    client = await aiohttp_client(ingress_app)
    resp = await client.get("/api/players")
    body = await resp.json()

    assert resp.status == 200
    assert body["aliases"] == {"a": "Kitchen"}
    assert body["selves"] == {"a": "media_player.kitchen_player"}


async def test_post_players_persists_aliases_and_selves(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    payload = {
        "routes": {"a": []},
        "default": [],
        "aliases": {"a": "Kitchen"},
        "selves": {"a": "media_player.kitchen_player"},
    }
    resp = await client.post("/api/players", json=payload)
    assert resp.status == 204
    assert json.loads(players_file.read_text()) == payload


async def test_post_players_rejects_invalid_selves(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {},
        "default": [],
        "selves": {"a": "light.bulb"},
    })
    assert resp.status == 400


async def test_post_players_rejects_empty_alias_value(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {"a": []},
        "default": [],
        "aliases": {"a": ""},
        "selves": {},
    })
    assert resp.status == 400


@pytest.fixture
def lan_app():
    app = web.Application()
    app.router.add_post("/intercom", srv.handle_intercom)
    return app


@pytest.fixture
def www_dir(monkeypatch, tmp_path):
    d = tmp_path / "www"
    d.mkdir()
    monkeypatch.setattr(srv, "CONFIG_WWW", str(d))
    return d


@pytest.fixture
def fake_options(monkeypatch):
    monkeypatch.setattr(srv, "load_options", lambda: {"ha_url": "http://ha.test:8123"})


async def test_intercom_known_source_uses_route(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    sid = str(uuid.uuid4())
    resp = await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
    )
    assert resp.status == 204
    called_entities = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert called_entities == ["media_player.kitchen"]


async def test_intercom_unknown_source_enrolls_and_uses_default(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    sid = str(uuid.uuid4())
    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": sid, "X-Device-Name": "new-src"},
    )
    assert json.loads(players_file.read_text())["routes"] == {"new-src": []}
    called_entities = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert called_entities == ["media_player.bedroom"]


async def test_intercom_missing_device_header_uses_unknown(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"unknown": ["media_player.kitchen"]},
        "default": [],
    }))
    client = await aiohttp_client(lan_app)
    sid = str(uuid.uuid4())
    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": sid},
    )
    called_entities = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert called_entities == ["media_player.kitchen"]


async def test_intercom_known_source_with_empty_route_plays_nowhere(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": []},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    sid = str(uuid.uuid4())
    resp = await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
    )
    assert resp.status == 204
    assert fake_ha.play_media.call_args_list == []


async def test_intercom_missing_players_file_returns_204_no_call(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha, caplog,
):
    # players_file fixture monkeypatches PLAYERS_FILE but never creates it
    client = await aiohttp_client(lan_app)
    sid = str(uuid.uuid4())

    with caplog.at_level(logging.WARNING, logger="intercom"):
        resp = await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
        )

    assert resp.status == 204
    # source auto-enrolled, default is empty, so no HA calls
    assert fake_ha.play_media.call_args_list == []
    assert json.loads(players_file.read_text())["routes"] == {"src-a": []}
    assert any("players.json" in record.message for record in caplog.records if record.levelname == "WARNING")


async def test_intercom_wav_includes_chimes(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    import struct
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": [],
    }))
    client = await aiohttp_client(lan_app)
    pcm = b"\xAA\xBB" * 100  # 200 bytes
    sid = str(uuid.uuid4())
    await client.post(
        "/intercom", data=pcm,
        headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
    )

    wav_files = list(www_dir.glob("intercom-*.wav"))
    assert len(wav_files) == 1
    wav = wav_files[0].read_bytes()
    pcm_len = struct.unpack_from("<I", wav, 40)[0]
    # Chime is 120ms at 16k/16/1 = 3840 bytes each side.
    # Total PCM = 3840 + 200 + 3840 = 7880.
    assert pcm_len == 7880
    assert wav[44 + 3840:44 + 3840 + 200] == pcm


async def test_intercom_pauses_playing_target_then_resumes(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    import asyncio as _asyncio
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": [],
    }))
    fake_ha.get_state.return_value = {
        "state": "playing", "attributes": {"volume_level": 0.4},
    }
    client = await aiohttp_client(lan_app)
    pcm = b"\xAA\xBB" * 100
    sid = str(uuid.uuid4())
    await client.post(
        "/intercom", data=pcm,
        headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
    )

    fake_ha.pause.assert_awaited_once_with("media_player.kitchen")
    # Restore is scheduled — total duration ~0.246s + 1.5s slack.
    await _asyncio.sleep(2.0)
    fake_ha.play.assert_awaited_once_with("media_player.kitchen")


async def test_talkback_routes_to_sender_self_not_normal_route(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    # kitchen-echo's broadcast targets living-echo's self_player, so a reply
    # window opens for living-echo. living-echo's normal route is the bedroom.
    # Talkback should override normal route.
    players_file.write_text(json.dumps({
        "routes": {
            "kitchen-echo": ["media_player.living_speaker"],
            "living-echo":  ["media_player.bedroom"],
        },
        "default": [],
        "aliases": {},
        "selves": {
            "kitchen-echo": "media_player.kitchen_speaker",
            "living-echo":  "media_player.living_speaker",
        },
    }))
    client = await aiohttp_client(lan_app)

    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": str(uuid.uuid4()), "X-Device-Name": "kitchen-echo"},
    )

    fake_ha.play_media.reset_mock()
    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": str(uuid.uuid4()), "X-Device-Name": "living-echo"},
    )
    called_entities = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert called_entities == ["media_player.kitchen_speaker"]


async def test_no_talkback_window_uses_normal_route(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.normal"]},
        "default": [],
        "aliases": {},
        "selves": {},
    }))
    client = await aiohttp_client(lan_app)
    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": str(uuid.uuid4()), "X-Device-Name": "src-a"},
    )
    called_entities = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert called_entities == ["media_player.normal"]
