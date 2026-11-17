import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import players as p  # noqa: E402


@pytest.fixture
def players_file(monkeypatch, tmp_path):
    f = tmp_path / "players.json"
    monkeypatch.setattr(p, "PLAYERS_FILE", str(f))
    return f


EMPTY = {"version": 2, "routes": {}, "muted": [], "excluded": [],
         "default": [], "aliases": {}, "selves": {}}


def full(**kw):
    return {**EMPTY, **kw}


def test_load_missing_returns_empty(players_file):
    assert p.load_players() == EMPTY


def test_load_malformed_returns_empty(players_file):
    players_file.write_text("not json")
    assert p.load_players() == EMPTY


def test_save_then_load_roundtrip(players_file):
    original = full(
        routes={"a": ["media_player.x"]},
        default=["media_player.y"],
        muted=["b"],
        excluded=["media_player.tv"],
    )
    p.save_players(original)
    assert p.load_players() == original


def test_save_writes_atomically(players_file):
    p.save_players({"routes": {}, "default": []})
    assert players_file.exists()
    assert not (players_file.parent / "players.json.tmp").exists()


def test_validate_accepts_minimal_payload():
    assert p.validate({"routes": {}, "default": []}) is None


def test_validate_rejects_non_dict():
    assert p.validate("nope") is not None


def test_validate_rejects_missing_fields():
    assert p.validate({"routes": {}}) is not None


def test_validate_rejects_non_media_player_target():
    err = p.validate({"routes": {"a": ["light.bulb"]}, "default": []})
    assert err is not None


def test_validate_rejects_empty_source_key():
    err = p.validate({"routes": {"": ["media_player.x"]}, "default": []})
    assert err is not None


def test_load_returns_empty_aliases_and_selves_by_default(players_file):
    players_file.write_text(json.dumps({"routes": {}, "default": []}))
    data = p.load_players()
    assert data["aliases"] == {}
    assert data["selves"] == {}


def test_aliases_and_selves_roundtrip(players_file):
    original = full(
        routes={"a": []},
        aliases={"a": "Kitchen"},
        selves={"a": "media_player.atom_echo_kitchen_player"},
    )
    p.save_players(original)
    loaded = p.load_players()
    assert loaded == original


V1 = {
    "routes": {"kitchen": ["media_player.bedroom"], "hall": []},
    "default": ["media_player.bedroom"],
    "aliases": {"hall": "Hall"},
    "selves": {"hall": "media_player.hall_player"},
}


def test_migrate_v1_keeps_routes_aliases_selves(players_file):
    players_file.write_text(json.dumps(V1))
    assert p.migrate_file() is True
    saved = json.loads(players_file.read_text())
    assert saved == full(**V1)
    # Non-empty route = override; empty = the channel (no longer "nowhere").
    assert saved["routes"]["kitchen"] == ["media_player.bedroom"]
    assert saved["routes"]["hall"] == []
    assert saved["muted"] == []


def test_migrate_is_idempotent(players_file):
    players_file.write_text(json.dumps(V1))
    p.migrate_file()
    first = players_file.read_text()
    assert p.migrate_file() is False
    assert players_file.read_text() == first


def test_migrate_missing_file_is_noop(players_file):
    assert p.migrate_file() is False
    assert not players_file.exists()


def test_load_drops_malformed_route_values(players_file):
    players_file.write_text(json.dumps({
        "routes": {"a": "media_player.x", "b": ["media_player.y", 3], "": []},
        "default": [], "muted": "nope", "excluded": None,
    }))
    data = p.load_players()
    assert data["routes"] == {"b": ["media_player.y"]}
    assert data["muted"] == [] and data["excluded"] == []


def test_validate_muted_and_excluded():
    base = {"routes": {}, "default": []}
    assert p.validate({**base, "muted": ["a"], "excluded": ["media_player.x"]}) is None
    assert p.validate({**base, "muted": "a"}) is not None
    assert p.validate({**base, "muted": [""]}) is not None
    assert p.validate({**base, "excluded": ["light.x"]}) is not None


def test_validate_accepts_aliases_and_selves():
    body = {
        "routes": {},
        "default": [],
        "aliases": {"a": "Kitchen"},
        "selves": {"a": "media_player.kitchen"},
    }
    assert p.validate(body) is None


def test_validate_aliases_must_be_dict():
    body = {"routes": {}, "default": [], "aliases": ["nope"]}
    assert p.validate(body) is not None


def test_validate_aliases_rejects_non_string_value():
    body = {"routes": {}, "default": [], "aliases": {"a": 123}}
    assert p.validate(body) is not None


def test_validate_aliases_rejects_empty_value():
    body = {"routes": {}, "default": [], "aliases": {"a": ""}}
    assert p.validate(body) is not None


def test_validate_selves_must_be_dict():
    body = {"routes": {}, "default": [], "selves": "nope"}
    assert p.validate(body) is not None


def test_validate_selves_value_must_start_with_media_player():
    body = {"routes": {}, "default": [], "selves": {"a": "light.kitchen"}}
    assert p.validate(body) is not None


def test_validate_selves_rejects_empty_key():
    body = {"routes": {}, "default": [], "selves": {"": "media_player.x"}}
    assert p.validate(body) is not None
