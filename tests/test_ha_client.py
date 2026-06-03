import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
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
