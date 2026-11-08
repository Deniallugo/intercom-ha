"""Delivery: announce vs Ducker fallback, per-speaker queue, /intercom reply."""
import asyncio
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402
import players as players_mod  # noqa: E402
from airtime import Airtime  # noqa: E402
from conftest import MEDIA_BASE  # noqa: E402

ANNOUNCE = srv.MEDIA_ANNOUNCE
# PAUSE | VOLUME_SET | PLAY_MEDIA | PLAY ... without MEDIA_ANNOUNCE (e.g. Cast)
PLAIN = 1 | 4 | 512 | 16384
ESPHOME = PLAIN | ANNOUNCE | (1 << 21)


def st(entity, features, state="idle"):
    return {"entity_id": entity, "state": state,
            "attributes": {"supported_features": features}}


# ── airtime ──────────────────────────────────────────────────────────────────

class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_airtime_free_speaker_starts_now():
    a = Airtime(now_func=Clock(), tail=1.0)
    slot = a.book("mp.a", 3.0)
    assert slot.wait == 0 and slot.end == 104.0


def test_airtime_second_booking_waits_for_the_first():
    clock = Clock()
    a = Airtime(now_func=clock, tail=1.0)
    a.book("mp.a", 3.0)
    clock.t += 1.0
    second = a.book("mp.a", 2.0)
    assert second.wait == pytest.approx(3.0)       # first ends at 104
    third = a.book("mp.a", 2.0)
    assert third.wait == pytest.approx(6.0)        # FIFO, after the second
    assert a.book("mp.b", 2.0).wait == 0           # other speakers unaffected


def test_airtime_refuses_beyond_max_wait():
    a = Airtime(now_func=Clock(), tail=0.0, max_wait=30.0)
    a.book("mp.a", 25.0)
    assert a.book("mp.a", 10.0) is not None        # starts in 25 s
    assert a.book("mp.a", 1.0) is None             # would start in 35 s
    assert a.busy_for("mp.a") == pytest.approx(35.0)


def test_airtime_cancel_frees_only_the_last_slot():
    clock = Clock()
    a = Airtime(now_func=clock, tail=0.0)
    first = a.book("mp.a", 5.0)
    second = a.book("mp.a", 5.0)
    a.cancel(first)                                # someone booked after it
    assert a.busy_for("mp.a") == pytest.approx(10.0)
    a.cancel(second)
    assert a.busy_for("mp.a") == pytest.approx(5.0)
    a.cancel(first)
    assert a.busy_for("mp.a") == 0


def test_supports_announce_reads_the_feature_bit():
    assert srv.supports_announce(st("mp.x", ESPHOME))
    assert not srv.supports_announce(st("mp.x", PLAIN))
    assert not srv.supports_announce(None)
    assert not srv.supports_announce({"attributes": {"supported_features": "junk"}})


# ── _play_on_targets ─────────────────────────────────────────────────────────

@pytest.fixture
def www_dir(monkeypatch, tmp_path):
    d = tmp_path / "www"
    d.mkdir()
    monkeypatch.setattr(srv, "CONFIG_WWW", str(d))
    return d


@pytest.fixture
def fake_options(monkeypatch):
    monkeypatch.setattr(srv, "load_options", lambda: {})


def served(label: str) -> str:
    """The URL players got for the media published as `label`."""
    [name] = [n for n, lab in srv.media_store.items() if lab == label]
    return f"{MEDIA_BASE}/media/{name}"


@pytest.fixture
def fake_ha(monkeypatch):
    monkeypatch.setattr(srv.ha, "get_states", AsyncMock(return_value=[]))
    monkeypatch.setattr(srv.ha, "play_media", AsyncMock(return_value=200))
    monkeypatch.setattr(srv.ha, "get_state",
                        AsyncMock(return_value={"state": "playing", "attributes": {}}))
    monkeypatch.setattr(srv.ha, "pause", AsyncMock(return_value=200))
    monkeypatch.setattr(srv.ha, "play", AsyncMock(return_value=200))
    monkeypatch.setattr(srv.ha, "get_registry", AsyncMock(return_value={
        "devices": [], "entities": [], "esphome_names": {}, "fetched_at": 1.0}))
    return srv.ha


@pytest.fixture(autouse=True)
def _clean_ducker():
    def drop():
        srv.ducker._snapshots.clear()
        srv.ducker._deadlines.clear()
        srv.ducker._tasks.clear()
    drop()
    yield
    drop()


@pytest.fixture
def fast_delete(monkeypatch):
    deleted = []

    async def delete(path, delay):
        deleted.append(path)

    monkeypatch.setattr(srv, "_delete_after", delete)
    return deleted


async def test_announce_capable_player_gets_announce_and_no_ducking(
    www_dir, fake_options, fake_ha, fast_delete,
):
    fake_ha.get_states.return_value = [st("media_player.echo", ESPHOME, "playing")]
    results = await srv._play_on_targets(b"RIFF", "wav", 1.0, ["media_player.echo"], name="t1")

    fake_ha.play_media.assert_awaited_once_with(
        "media_player.echo", served("t1"), announce=True)
    # The player keeps its own music: no snapshot, pause or resume.
    fake_ha.get_state.assert_not_called()
    fake_ha.pause.assert_not_called()
    assert srv.ducker._deadlines == {}
    assert results == {"media_player.echo": {
        "ok": True, "outcome": "ok", "via": "announce", "status": 200}}


async def test_player_without_announce_falls_back_to_ducker(
    www_dir, fake_options, fake_ha, fast_delete,
):
    fake_ha.get_states.return_value = [st("media_player.cast", PLAIN, "playing")]
    results = await srv._play_on_targets(b"RIFF", "wav", 0.1, ["media_player.cast"], name="t2")

    fake_ha.play_media.assert_awaited_once_with(
        "media_player.cast", served("t2"))
    fake_ha.pause.assert_awaited_once_with("media_player.cast")
    assert results["media_player.cast"]["via"] == "duck"
    await asyncio.sleep(1.8)                       # 0.1 + 1.5 s restore
    fake_ha.play.assert_awaited_once_with("media_player.cast")


async def test_mixed_targets_each_take_their_own_path(
    www_dir, fake_options, fake_ha, fast_delete,
):
    fake_ha.get_states.return_value = [
        st("media_player.echo", ESPHOME), st("media_player.sonos_old", PLAIN)]
    results = await srv._play_on_targets(
        b"RIFF", "wav", 1.0, ["media_player.echo", "media_player.sonos_old"], name="t3")
    calls = {c.args[0]: c.kwargs for c in fake_ha.play_media.await_args_list}
    assert calls == {"media_player.echo": {"announce": True}, "media_player.sonos_old": {}}
    assert {k: v["via"] for k, v in results.items()} == {
        "media_player.echo": "announce", "media_player.sonos_old": "duck"}


async def test_unreadable_states_fall_back_to_the_old_path(
    www_dir, fake_options, fake_ha, fast_delete,
):
    fake_ha.get_states.side_effect = RuntimeError("503")
    results = await srv._play_on_targets(b"RIFF", "wav", 1.0, ["media_player.x"], name="t4")
    fake_ha.play_media.assert_awaited_once_with(
        "media_player.x", served("t4"))
    assert results["media_player.x"]["outcome"] == "ok"


async def test_unavailable_and_unknown_players_are_skipped(
    www_dir, fake_options, fake_ha, fast_delete,
):
    fake_ha.get_states.return_value = [
        st("media_player.off", ESPHOME, "unavailable"), st("media_player.on", ESPHOME)]
    results = await srv._play_on_targets(
        b"RIFF", "wav", 1.0, ["media_player.off", "media_player.gone", "media_player.on"],
        name="t5")
    assert [c.args[0] for c in fake_ha.play_media.await_args_list] == ["media_player.on"]
    assert results["media_player.off"] == {
        "ok": False, "outcome": "skipped", "reason": "unavailable"}
    assert results["media_player.gone"]["outcome"] == "skipped"


async def test_http_error_and_exception_are_reported(
    www_dir, fake_options, fake_ha, fast_delete,
):
    fake_ha.get_states.return_value = [st("media_player.a", ESPHOME), st("media_player.b", ESPHOME)]

    async def play_media(entity, url, announce=False):
        if entity == "media_player.a":
            return 500
        raise asyncio.TimeoutError()

    fake_ha.play_media.side_effect = play_media
    results = await srv._play_on_targets(
        b"RIFF", "wav", 1.0, ["media_player.a", "media_player.b"], name="t6")
    assert results["media_player.a"] == {
        "ok": False, "outcome": "error", "via": "announce", "status": 500,
        "error": "HA returned HTTP 500"}
    assert results["media_player.b"]["error"] == "timed out"
    # Failed slots are given back: the next broadcast plays at once.
    assert srv.airtime.busy_for("media_player.a") == 0
    assert srv.airtime.busy_for("media_player.b") == 0


async def test_busy_speaker_queues_instead_of_cutting_off(
    www_dir, fake_options, fake_ha, fast_delete, monkeypatch,
):
    monkeypatch.setattr(srv, "airtime", Airtime(tail=0.05))
    fake_ha.get_states.return_value = [st("media_player.a", ESPHOME), st("media_player.b", ESPHOME)]

    first = await srv._play_on_targets(b"RIFF", "wav", 0.3, ["media_player.a"], name="p1")
    second = await srv._play_on_targets(
        b"RIFF", "wav", 0.3, ["media_player.a", "media_player.b"], name="p2")

    assert first["media_player.a"]["outcome"] == "ok"
    assert second["media_player.b"]["outcome"] == "ok"      # free: plays now
    queued = second["media_player.a"]
    assert queued["outcome"] == "queued" and queued["ok"] is None
    assert 0.2 < queued["wait"] <= 0.4
    # Not yet sent to the busy speaker.
    assert [c.args[1] for c in fake_ha.play_media.await_args_list] == [
        served("p1"), served("p2")]
    assert fast_delete == [] or len(fast_delete) == 1      # p1's file only

    await asyncio.sleep(0.6)
    urls = [(c.args[0], c.args[1]) for c in fake_ha.play_media.await_args_list]
    assert urls[-1] == ("media_player.a", served("p2"))
    # The queued entry is replaced in place (it is the same dict that
    # last_broadcast holds).
    assert second["media_player.a"] == {
        "ok": True, "outcome": "ok", "via": "announce", "status": 200}
    assert len(fast_delete) == 2


async def test_queue_is_bounded(www_dir, fake_options, fake_ha, fast_delete):
    fake_ha.get_states.return_value = [st("media_player.a", ESPHOME)]
    await srv._play_on_targets(b"RIFF", "wav", srv.airtime.max_wait + 5, ["media_player.a"],
                               name="long")
    results = await srv._play_on_targets(b"RIFF", "wav", 1.0, ["media_player.a"], name="next")
    assert results["media_player.a"]["outcome"] == "busy"
    assert results["media_player.a"]["ok"] is False
    assert fake_ha.play_media.await_count == 1


# ── /intercom response ──────────────────────────────────────────────────────

@pytest.fixture
def players_file(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    monkeypatch.setattr(players_mod, "PLAYERS_FILE", str(p))
    return p


@pytest.fixture
def lan_app(monkeypatch, tmp_path):
    monkeypatch.setattr(srv.recordings, "RECORDINGS_DIR", str(tmp_path / "rec"), raising=False)
    monkeypatch.setattr(srv, "keep_recordings", lambda: 0)
    monkeypatch.setattr(srv, "denoise_enabled", lambda: False)
    app = web.Application()
    app.router.add_post("/intercom", srv.handle_intercom)
    return app


def _route(players_file, targets):
    players_file.write_text(json.dumps({"routes": {"src": targets}, "default": []}))


async def _press(client, device="src"):
    return await client.post("/intercom", data=b"\x00" * 64, headers={
        "X-Session-ID": str(uuid.uuid4()), "X-Device-Name": device})


async def test_intercom_reports_per_target_results(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha, fast_delete,
):
    _route(players_file, ["media_player.a", "media_player.b", "media_player.c"])
    fake_ha.get_states.return_value = [
        st("media_player.a", ESPHOME), st("media_player.b", ESPHOME),
        st("media_player.c", ESPHOME, "unavailable")]

    async def play_media(entity, url, announce=False):
        return 200 if entity == "media_player.a" else 500

    fake_ha.play_media.side_effect = play_media
    client = await aiohttp_client(lan_app)
    resp = await _press(client)

    assert resp.status == 200                      # someone heard it
    body = await resp.json()
    assert body["source"] == "src" and body["mode"] == "override"
    assert body["targets"] == ["media_player.a", "media_player.b", "media_player.c"]
    assert body["delivered"] == 1 and body["failed"] == 1 and body["skipped"] == 1
    assert body["queued"] == 0
    assert body["results"]["media_player.a"]["outcome"] == "ok"
    assert body["results"]["media_player.b"]["outcome"] == "error"
    assert body["results"]["media_player.c"]["outcome"] == "skipped"
    assert srv.activity["src"]["last_broadcast"]["results"] == body["results"]


async def test_intercom_502_when_nobody_is_reached(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha, fast_delete,
):
    _route(players_file, ["media_player.a"])
    fake_ha.play_media.side_effect = RuntimeError("HA down")
    client = await aiohttp_client(lan_app)
    resp = await _press(client)
    assert resp.status == 502
    body = await resp.json()
    assert body["delivered"] == 0 and body["failed"] == 1
    assert body["results"]["media_player.a"]["error"] == "HA down"


async def test_intercom_no_targets_is_200(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha, fast_delete,
):
    players_file.write_text(json.dumps({"routes": {}, "default": [], "muted": ["src"]}))
    client = await aiohttp_client(lan_app)
    resp = await _press(client)
    assert resp.status == 200
    body = await resp.json()
    assert body["mode"] == "muted" and body["targets"] == [] and body["delivered"] == 0


async def test_intercom_second_press_is_queued_and_answered_at_once(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha, fast_delete,
    monkeypatch,
):
    """Two devices talk at once to a shared speaker: the second is not cut
    off and not held either — answered now, played after the first."""
    players_file.write_text(json.dumps({
        "routes": {"a": ["media_player.shared"], "b": ["media_player.shared"]},
        "default": []}))
    fake_ha.get_states.return_value = [st("media_player.shared", ESPHOME)]
    monkeypatch.setattr(srv, "airtime", Airtime(tail=0.05))
    client = await aiohttp_client(lan_app)

    assert (await _press(client, "a")).status == 200
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    resp = await _press(client, "b")
    assert loop.time() - t0 < 1.0                  # no waiting in the request
    assert resp.status == 200
    body = await resp.json()
    assert body["queued"] == 1 and body["delivered"] == 0
    assert body["results"]["media_player.shared"]["outcome"] == "queued"
    assert fake_ha.play_media.await_count == 1

    lb = srv.activity["b"]["last_broadcast"]["results"]["media_player.shared"]
    wait = body["results"]["media_player.shared"]["wait"]
    await asyncio.sleep(wait + 0.3)
    assert fake_ha.play_media.await_count == 2
    assert srv.activity["b"]["last_broadcast"]["results"]["media_player.shared"]["outcome"] == "ok"
    assert lb["outcome"] == "queued"               # the old entry object, replaced
