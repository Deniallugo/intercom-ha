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
