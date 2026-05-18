import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402


@pytest.fixture
def players_file(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    monkeypatch.setattr(srv, "PLAYERS_FILE", str(p))
    return p


def test_load_players_missing_file_returns_empty(players_file):
    data = srv.load_players()
    assert data == {"routes": {}, "default": []}


def test_load_players_malformed_returns_empty(players_file):
    players_file.write_text("not json")
    data = srv.load_players()
    assert data == {"routes": {}, "default": []}


def test_load_players_reads_existing(players_file):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.x"]},
        "default": ["media_player.y"],
    }))
    data = srv.load_players()
    assert data["routes"] == {"src-a": ["media_player.x"]}
    assert data["default"] == ["media_player.y"]


def test_save_players_writes_atomically(players_file):
    srv.save_players({"routes": {"a": ["media_player.x"]}, "default": []})
    assert json.loads(players_file.read_text()) == {
        "routes": {"a": ["media_player.x"]},
        "default": [],
    }
    # No leftover .tmp file
    assert not (players_file.parent / "players.json.tmp").exists()


def test_save_then_load_roundtrip(players_file):
    original = {"routes": {"a": ["media_player.x", "media_player.y"]}, "default": ["media_player.z"]}
    srv.save_players(original)
    assert srv.load_players() == original


class _FakeStatesResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def json(self):
        return self._payload


class _FakeStatesSession:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status
        self.calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeStatesResponse(self._payload, self._status)


@pytest.fixture
def supervisor_token(monkeypatch):
    monkeypatch.setitem(os.environ, "SUPERVISOR_TOKEN", "tok")


async def test_fetch_media_players_filters_and_maps(supervisor_token):
    states = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "light.bulb", "attributes": {"friendly_name": "Bulb"}},
        {"entity_id": "media_player.bedroom", "attributes": {}},
    ]
    fake = _FakeStatesSession(states)
    with patch("intercom.ClientSession", return_value=fake):
        result = await srv.fetch_media_players()

    assert result == [
        {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen"},
        {"entity_id": "media_player.bedroom", "friendly_name": "media_player.bedroom"},
    ]
    url, kwargs = fake.calls[0]
    assert url == f"{srv.HA_API}/states"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


async def test_fetch_media_players_raises_on_non_200(supervisor_token):
    fake = _FakeStatesSession([], status=503)
    with patch("intercom.ClientSession", return_value=fake):
        with pytest.raises(RuntimeError):
            await srv.fetch_media_players()


@pytest.fixture
def ingress_app():
    app = web.Application()
    app.router.add_get("/api/players", srv.handle_picker_get)
    app.router.add_post("/api/players", srv.handle_picker_post)
    return app


async def test_get_players_merges_available_and_routes(
    aiohttp_client, ingress_app, players_file, supervisor_token,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    states = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "media_player.bedroom", "attributes": {"friendly_name": "Bedroom"}},
    ]
    client = await aiohttp_client(ingress_app)
    with patch("intercom.ClientSession", return_value=_FakeStatesSession(states)):
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
    aiohttp_client, ingress_app, players_file, supervisor_token,
):
    client = await aiohttp_client(ingress_app)
    with patch("intercom.ClientSession", return_value=_FakeStatesSession([], status=503)):
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
    assert json.loads(players_file.read_text()) == payload


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


class _FakeMediaResponse:
    status = 204


class _FakeMediaSession:
    def __init__(self):
        self.calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeMediaResponse()


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
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        resp = await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
        )

    assert resp.status == 204
    assert [c[1]["json"]["entity_id"] for c in fake.calls] == ["media_player.kitchen"]


async def test_intercom_unknown_source_enrolls_and_uses_default(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "new-src"},
        )

    assert json.loads(players_file.read_text())["routes"] == {"new-src": []}
    assert [c[1]["json"]["entity_id"] for c in fake.calls] == ["media_player.bedroom"]


async def test_intercom_missing_device_header_uses_unknown(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {"unknown": ["media_player.kitchen"]},
        "default": [],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid},
        )

    assert [c[1]["json"]["entity_id"] for c in fake.calls] == ["media_player.kitchen"]


async def test_intercom_known_source_with_empty_route_plays_nowhere(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": []},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        resp = await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
        )

    assert resp.status == 204
    assert fake.calls == []


async def test_intercom_missing_players_file_returns_204_no_call(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    # players_file fixture monkeypatches PLAYERS_FILE but never creates it
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        resp = await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
        )

    assert resp.status == 204
    # source auto-enrolled, default is empty, so no HA calls
    assert fake.calls == []
    assert json.loads(players_file.read_text())["routes"] == {"src-a": []}
