import json
import sys
from pathlib import Path

import pytest

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


import os
from unittest.mock import patch


class _FakeStatesResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def json(self):
        return self._payload

    async def text(self):
        return json.dumps(self._payload)


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


from aiohttp import web


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
