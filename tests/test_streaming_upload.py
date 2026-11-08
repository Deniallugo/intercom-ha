"""/intercom works during the upload: routing, Ducker pauses and the denoise
start before the last byte; a failed upload restores what it paused."""
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
import recordings  # noqa: E402

PLAIN = 1 | 4 | 512 | 16384               # no MEDIA_ANNOUNCE: goes via the Ducker
ESPHOME = PLAIN | srv.MEDIA_ANNOUNCE


def st(entity, features, state="playing"):
    return {"entity_id": entity, "state": state,
            "attributes": {"supported_features": features}}


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Players file, recordings kept, Ducker/HA faked, nothing else on."""
    p = tmp_path / "players.json"
    monkeypatch.setattr(players_mod, "PLAYERS_FILE", str(p))
    p.write_text(json.dumps({"routes": {"src": ["media_player.cast",
                                                "media_player.echo"]},
                             "default": []}))
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", str(tmp_path / "rec"))
    monkeypatch.setattr(srv, "keep_recordings", lambda: 5)
    monkeypatch.setattr(srv, "load_options", lambda: {"denoise": False})
    monkeypatch.setattr(srv, "CONFIG_WWW", str(tmp_path / "www"))
    ha = srv.ha
    monkeypatch.setattr(ha, "get_states", AsyncMock(return_value=[
        st("media_player.cast", PLAIN), st("media_player.echo", ESPHOME)]))
    monkeypatch.setattr(ha, "get_state", AsyncMock(
        return_value={"state": "playing", "attributes": {}}))
    monkeypatch.setattr(ha, "pause", AsyncMock(return_value=200))
    monkeypatch.setattr(ha, "play", AsyncMock(return_value=200))
    monkeypatch.setattr(ha, "play_media", AsyncMock(return_value=200))
    monkeypatch.setattr(ha, "get_registry", AsyncMock(return_value={
        "devices": [], "entities": [], "esphome_names": {}, "fetched_at": 1.0}))

    async def no_delete(path, delay):
        pass

    monkeypatch.setattr(srv, "_delete_after", no_delete)
    for d in (srv.ducker._snapshots, srv.ducker._deadlines, srv.ducker._tasks):
        d.clear()
    srv.activity.clear()
    yield ha
    for t in list(srv.ducker._tasks.values()):
        t.cancel()
    for d in (srv.ducker._snapshots, srv.ducker._deadlines, srv.ducker._tasks):
        d.clear()


@pytest.fixture
def lan_app():
    app = web.Application()
    app.router.add_post("/intercom", srv.handle_intercom)
    return app


def headers(**extra):
    return {"X-Session-ID": str(uuid.uuid4()), "X-Device-Name": "src", **extra}


async def until(cond, timeout=2.0):
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while not cond():
        assert loop.time() < end, "timed out"
        await asyncio.sleep(0.01)


async def test_work_starts_before_the_last_byte(aiohttp_client, lan_app, env,
                                                fake_streams):
    """While the upload is open: the route is read, the Ducker target is
    paused (the announce one is not), the denoiser has the audio so far."""
    gate = asyncio.Event()
    first = b"\x01\x00" * 8000                 # 0.5 s: more than one batch

    async def body():
        yield first
        await gate.wait()
        yield b"\x02\x00" * 800

    client = await aiohttp_client(lan_app)
    post = asyncio.ensure_future(client.post("/intercom", data=body(), headers=headers()))
    await until(lambda: env.pause.await_count == 1)
    await until(lambda: fake_streams.made and fake_streams.made[0].fed)

    env.pause.assert_awaited_once_with("media_player.cast")
    assert env.play_media.await_count == 0
    assert srv.ducker.holds("media_player.cast")
    assert not srv.ducker.holds("media_player.echo")
    assert first.startswith(fake_streams.made[0].fed)
    assert not recordings.listing()            # nothing written yet

    gate.set()
    resp = await post
    assert resp.status == 200
    calls = {c.args[0]: c.kwargs for c in env.play_media.await_args_list}
    assert calls == {"media_player.cast": {}, "media_player.echo": {"announce": True}}
    # The Ducker was not asked twice: one snapshot, one pause.
    assert env.get_state.await_count == 1 and env.pause.await_count == 1
    assert fake_streams.made[0].fed == first + b"\x02\x00" * 800
    # Restored after the clip, not at once.
    assert env.play.await_count == 0
    assert srv.ducker._deadlines["media_player.cast"] > srv.ducker._now() + 1.0


async def test_dropped_upload_restores_what_it_paused(aiohttp_client, lan_app,
                                                      env, fake_streams):
    gate = asyncio.Event()

    async def body():
        yield b"\x01\x00" * 4000
        await gate.wait()
        raise ConnectionResetError("device rebooted mid-press")

    client = await aiohttp_client(lan_app)
    post = asyncio.ensure_future(client.post("/intercom", data=body(), headers=headers()))
    await until(lambda: env.pause.await_count == 1)
    gate.set()
    with pytest.raises(Exception):
        await post

    await until(lambda: env.play.await_count == 1)
    env.play.assert_awaited_once_with("media_player.cast")
    assert not srv.ducker.holds("media_player.cast")
    assert env.play_media.await_count == 0
    assert "src" not in srv.activity           # never counted as a press
    assert json.loads(Path(players_mod.PLAYERS_FILE).read_text())["routes"] == {
        "src": ["media_player.cast", "media_player.echo"]}


async def test_empty_upload_restores_what_it_paused(aiohttp_client, lan_app,
                                                    env, fake_streams):
    gate = asyncio.Event()

    async def body():
        yield b"\x01"                          # one odd byte = no whole frame
        await until(lambda: env.pause.await_count == 1)
        gate.set()

    client = await aiohttp_client(lan_app)
    resp = await client.post("/intercom", data=body(), headers=headers())
    assert gate.is_set()
    assert resp.status == 400
    await until(lambda: env.play.await_count == 1)
    assert not srv.ducker.holds("media_player.cast")
    assert env.play_media.await_count == 0
    assert not recordings.listing()


async def test_oversized_upload_is_refused_and_restored(aiohttp_client, env,
                                                        fake_streams):
    app = web.Application(client_max_size=4000)
    app.router.add_post("/intercom", srv.handle_intercom)
    client = await aiohttp_client(app)

    async def body():
        yield b"\x01\x00" * 500
        await until(lambda: env.pause.await_count == 1)
        for _ in range(4):
            yield b"\x01\x00" * 1000

    resp = await client.post("/intercom", data=body(), headers=headers())
    assert resp.status == 413
    await until(lambda: env.play.await_count == 1)
    assert env.play_media.await_count == 0


async def test_busy_speaker_is_not_paused_ahead(aiohttp_client, lan_app, env,
                                               fake_streams):
    """A speaker still playing an earlier broadcast ducks in its own slot,
    as before; pausing it now would cut into the earlier one's restore."""
    srv.airtime.book("media_player.cast", 0.3)
    client = await aiohttp_client(lan_app)
    resp = await client.post("/intercom", data=b"\x01\x00" * 400, headers=headers())
    assert resp.status == 200
    assert (await resp.json())["results"]["media_player.cast"]["outcome"] == "queued"
    assert env.pause.await_count == 0
    await until(lambda: env.play_media.await_count == 2)
    env.pause.assert_awaited_once_with("media_player.cast")


async def test_recording_is_saved_before_the_broadcast(aiohttp_client, lan_app,
                                                       env, fake_streams):
    seen = []

    async def play_media(entity, url, announce=False):
        seen.append(len(recordings.listing()))
        return 500

    env.play_media.side_effect = play_media
    client = await aiohttp_client(lan_app)
    resp = await client.post("/intercom", data=b"\x01\x00" * 400, headers=headers())
    assert resp.status == 502                  # nobody reached ...
    assert seen == [1, 1]                      # ... the recording was already there
    assert len(recordings.listing()) == 1


async def test_recording_survives_a_routing_failure(aiohttp_client, lan_app,
                                                    env, fake_streams,
                                                    monkeypatch):
    def broken():
        raise ValueError("players.json is garbage")

    monkeypatch.setattr(srv.players, "load_players", broken)
    client = await aiohttp_client(lan_app)
    resp = await client.post("/intercom", data=b"\x01\x00" * 400, headers=headers())
    assert resp.status == 500
    assert len(recordings.listing()) == 1
    assert env.play_media.await_count == 0


async def test_denoise_failure_broadcasts_raw_audio(aiohttp_client, lan_app, env,
                                                   fake_streams):
    def boom(pcm, full):
        raise RuntimeError("dsp bug")

    fake_streams.out = boom
    client = await aiohttp_client(lan_app)
    pcm = b"\x05\x00" * 400
    resp = await client.post("/intercom", data=pcm, headers=headers())
    assert resp.status == 200
    [name] = [n for n, lab in srv.media_store.items() if lab.startswith("intercom-")]
    wav = (srv.media_store.directory() / name).read_bytes()
    assert pcm in wav


async def test_real_denoise_streamed_matches_whole_message(aiohttp_client, lan_app,
                                                           env, monkeypatch):
    """End to end with the real Stream: what is broadcast is process() of
    the trimmed upload, however the network cut it."""
    monkeypatch.setattr(srv, "load_options", lambda: {"denoise": True})
    import random
    rnd = random.Random(3)
    pcm = bytes(rnd.getrandbits(8) for _ in range(16001))    # odd: last byte dropped

    async def body():
        i = 0
        while i < len(pcm):
            n = rnd.randint(1, 3000)
            yield pcm[i:i + n]
            i += n
            await asyncio.sleep(0)

    client = await aiohttp_client(lan_app)
    resp = await client.post("/intercom", data=body(), headers=headers())
    assert resp.status == 200
    [name] = [n for n, lab in srv.media_store.items() if lab.startswith("intercom-")]
    wav = (srv.media_store.directory() / name).read_bytes()
    mx = srv.mixer
    assert wav == mx.build_wav(srv.denoise.process(pcm[:16000], sample_rate=16000))
