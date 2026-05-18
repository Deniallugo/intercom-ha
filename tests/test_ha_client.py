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
