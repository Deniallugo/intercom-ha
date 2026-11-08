"""Broadcast media served by the add-on (media.py) instead of /config/www."""
import json
import sys
import wave
import io
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402
import media  # noqa: E402
import players as players_mod  # noqa: E402
from conftest import MEDIA_BASE  # noqa: E402


# ── MediaStore ───────────────────────────────────────────────────────────────

def test_put_gives_unguessable_unique_names():
    store = media.MediaStore()
    a = store.put(b"a", "wav", 10)
    b = store.put(b"b", "wav", 10)
    assert a.name != b.name
    assert len(a.stem) == 32            # 192 random bits, url-safe
    assert store.lookup(a.name) == a and a.read_bytes() == b"a"


def test_lookup_rejects_unknown_malformed_and_expired():
    store = media.MediaStore()
    path = store.put(b"x", "wav", 5, now=100.0)
    assert store.lookup(path.name, now=104.9) == path
    assert store.lookup(path.name, now=105.0) is None   # expired...
    assert not path.exists()                            # ...and deleted
    assert store.lookup("../../etc/passwd") is None
    assert store.lookup("intercom-abc.wav") is None
    assert store.lookup("A" * 32 + ".wav") is None      # well-formed, unknown


def test_put_sweeps_expired_media():
    store = media.MediaStore()
    old = store.put(b"x", "wav", 1, now=0.0)
    store.put(b"y", "wav", 1, now=50.0)
    assert not old.exists()
    assert len(store.items()) == 1


def test_put_rejects_unknown_extension():
    with pytest.raises(ValueError):
        media.MediaStore().put(b"x", "html", 10)


def test_clear_removes_leftovers_from_a_previous_run():
    store = media.MediaStore()
    path = store.put(b"x", "wav", 10)
    media.MediaStore().clear()
    assert not path.exists()


# ── address discovery ────────────────────────────────────────────────────────

NETWORK_INFO = {"interfaces": [
    {"interface": "wlan0", "primary": False, "enabled": True, "connected": True,
     "ipv4": {"address": ["10.0.0.9/24"]}},
    {"interface": "eth0", "primary": True, "enabled": True, "connected": True,
     "ipv4": {"address": ["192.168.1.20/24"]}},
]}


def test_primary_ipv4_prefers_primary_connected_interface():
    assert media.primary_ipv4(NETWORK_INFO) == "192.168.1.20"
    assert media.primary_ipv4({"interfaces": [
        {"primary": True, "connected": False, "ipv4": {"address": ["1.1.1.1/8"]}},
        {"primary": False, "connected": True, "ipv4": {"address": ["10.0.0.9/24"]}},
    ]}) == "10.0.0.9"
    assert media.primary_ipv4({}) is None


def test_published_port_follows_network_section():
    assert media.published_port({"network": {"9999/tcp": 9999}}) == 9999
    assert media.published_port({"network": {"9999/tcp": 19999}}) == 19999
    assert media.published_port({"network": {"9999/tcp": None}}) is None
    assert media.published_port({"network": None}) is None


def fake_supervisor(addon=None, network=NETWORK_INFO, config=None):
    ha = AsyncMock()

    async def supervisor_get(path):
        value = {"/addons/self/info": addon, "/network/info": network}[path]
        if isinstance(value, Exception):
            raise value
        return value

    async def get_core_config():
        if isinstance(config, Exception):
            raise config
        return config or {}

    ha.supervisor_get.side_effect = supervisor_get
    ha.get_core_config.side_effect = get_core_config
    return ha


async def test_resolve_uses_host_ip_and_remapped_port():
    ha = fake_supervisor(addon={"network": {"9999/tcp": 19999}},
                         config={"internal_url": "http://ha.lan:8123/"})
    base, ha_url = await media.LanAddress().resolve(ha)
    assert base == "http://192.168.1.20:19999"
    assert ha_url == "http://ha.lan:8123"


async def test_resolve_falls_back_to_internal_url_host():
    ha = fake_supervisor(addon={"network": {"9999/tcp": 9999}},
                         network=RuntimeError("403"),
                         config={"internal_url": "http://192.168.7.7:8123"})
    base, _ = await media.LanAddress().resolve(ha)
    assert base == "http://192.168.7.7:9999"


async def test_resolve_without_published_port_returns_none():
    ha = fake_supervisor(addon={"network": {"9999/tcp": None}})
    base, ha_url = await media.LanAddress().resolve(ha)
    assert base is None
    assert ha_url == media.FALLBACK_HA_URL


async def test_resolve_caches_then_retries_sooner_after_errors():
    ha = fake_supervisor(addon=RuntimeError("down"), network=RuntimeError("down"),
                         config=RuntimeError("down"))
    addr = media.LanAddress()
    base, _ = await addr.resolve(ha)
    assert base == "http://homeassistant.local:9999"    # every fallback
    await addr.resolve(ha)
    assert ha.supervisor_get.await_count == 2           # cached (2 calls once)
    addr.invalidate()
    await addr.resolve(ha)
    assert ha.supervisor_get.await_count == 4


# ── end to end through the LAN app ───────────────────────────────────────────

@pytest.fixture
def setup(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    p.write_text(json.dumps({"routes": {"src-a": ["media_player.kitchen"]},
                             "default": []}))
    monkeypatch.setattr(players_mod, "PLAYERS_FILE", str(p))
    www = tmp_path / "www"
    www.mkdir()
    monkeypatch.setattr(srv, "CONFIG_WWW", str(www))
    monkeypatch.setattr(srv, "load_options", lambda: {"denoise": False})
    for name, value in {"play_media": 204, "pause": 200, "play": 200,
                        "get_states": [],
                        "get_state": {"state": "idle", "attributes": {}},
                        "get_registry": {"devices": [], "entities": []}}.items():
        monkeypatch.setattr(srv.ha, name, AsyncMock(return_value=value))
    srv.ducker._snapshots.clear()
    srv.ducker._deadlines.clear()
    srv.ducker._tasks.clear()
    return www


async def test_broadcast_is_served_by_the_addon_not_www(aiohttp_client, setup):
    client = await aiohttp_client(srv.make_lan_app(token=""))
    resp = await client.post("/intercom", data=b"\x01\x00" * 1600,
                             headers={"X-Device-Name": "src-a"})
    assert resp.status == 200
    assert list(setup.iterdir()) == []                 # nothing public in www
    url = srv.ha.play_media.await_args.args[1]
    assert url.startswith(MEDIA_BASE + "/media/")

    got = await client.get(url[len(MEDIA_BASE):])
    assert got.status == 200
    assert got.headers["Content-Type"] == "audio/wav"
    with wave.open(io.BytesIO(await got.read()), "rb") as w:
        assert w.getframerate() == 16000

    # Unknown names give nothing away.
    assert (await client.get("/media/" + "A" * 32 + ".wav")).status == 404
    assert (await client.get("/media/..%2Foptions.json")).status == 404


async def test_media_expires(aiohttp_client, setup):
    client = await aiohttp_client(srv.make_lan_app(token=""))
    await client.post("/intercom", data=b"\x01\x00" * 1600,
                      headers={"X-Device-Name": "src-a"})
    url = srv.ha.play_media.await_args.args[1]
    [(name, _)] = srv.media_store.items()
    srv.media_store._expires[name] = 0.0               # TTL has passed
    assert (await client.get(url[len(MEDIA_BASE):])).status == 404


async def test_unpublished_port_falls_back_to_www(aiohttp_client, setup,
                                                  media_server, monkeypatch):
    media_server.return_value = (None, "http://ha.test:8123")
    deleted = []

    async def fake_delete(path, delay):
        deleted.append((path, delay))

    monkeypatch.setattr(srv, "_delete_after", fake_delete)
    client = await aiohttp_client(srv.make_lan_app(token=""))
    await client.post("/intercom", data=b"\x01\x00" * 1600,
                      headers={"X-Device-Name": "src-a", "X-Session-ID": "sid-1"})
    url = srv.ha.play_media.await_args.args[1]
    assert url == "http://ha.test:8123/local/intercom-sid-1.wav"
    [(path, delay)] = deleted
    assert path.parent == setup
    assert delay < 1.0 + srv.WWW_GRACE_SECONDS         # short public window


def test_stale_www_media_removed_only_by_our_pattern(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "CONFIG_WWW", str(tmp_path))
    for n in ("intercom-abc.wav", "announce-1f2e.mp3", "photo.jpg",
              "intercom-notes.txt", "my-intercom-x.wav"):
        (tmp_path / n).write_bytes(b"x")
    assert srv.remove_stale_www_media() == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "intercom-notes.txt", "my-intercom-x.wav", "photo.jpg"]


def test_stale_www_media_tolerates_missing_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "CONFIG_WWW", str(tmp_path / "nope"))
    assert srv.remove_stale_www_media() == 0
