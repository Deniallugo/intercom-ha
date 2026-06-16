import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
from ducking import Ducker  # noqa: E402


@pytest.fixture
def fake_ha():
    ha = AsyncMock()
    ha.get_state = AsyncMock()
    ha.pause = AsyncMock()
    ha.play = AsyncMock()
    return ha


async def test_pauses_playing_target(fake_ha):
    fake_ha.get_state.return_value = {
        "state": "playing",
        "attributes": {"volume_level": 0.5},
    }
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    fake_ha.pause.assert_awaited_once_with("media_player.x")


async def test_does_not_pause_idle_target(fake_ha):
    fake_ha.get_state.return_value = {"state": "idle", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    fake_ha.pause.assert_not_called()


async def test_restore_resumes_playing(fake_ha):
    fake_ha.get_state.return_value = {
        "state": "playing",
        "attributes": {"volume_level": 0.5},
    }
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    await d.restore("media_player.x")
    fake_ha.play.assert_awaited_once_with("media_player.x")


async def test_restore_repauses_paused_target(fake_ha):
    """A target paused before the broadcast auto-resumes when we inject a
    one-shot media_url, so restore must re-pause it to leave it as we found it.
    No pause at snapshot time — it's already paused."""
    fake_ha.get_state.return_value = {
        "state": "paused",
        "attributes": {"volume_level": 0.5},
    }
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    fake_ha.pause.assert_not_called()
    await d.restore("media_player.x")
    fake_ha.pause.assert_awaited_once_with("media_player.x")
    fake_ha.play.assert_not_called()


async def test_restore_idle_is_noop(fake_ha):
    fake_ha.get_state.return_value = {"state": "idle", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    await d.restore("media_player.x")
    fake_ha.play.assert_not_called()


async def test_concurrent_snapshot_skips_second(fake_ha):
    fake_ha.get_state.return_value = {"state": "playing", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    await d.snapshot_and_pause(["media_player.x"])
    assert fake_ha.get_state.await_count == 1
    assert fake_ha.pause.await_count == 1


async def test_restore_only_fires_once_after_overlap(fake_ha):
    fake_ha.get_state.return_value = {"state": "playing", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    await d.snapshot_and_pause(["media_player.x"])
    await d.restore("media_player.x")
    assert fake_ha.play.await_count == 1
    await d.restore("media_player.x")
    assert fake_ha.play.await_count == 1


async def test_get_state_error_is_treated_as_idle(fake_ha):
    fake_ha.get_state.side_effect = RuntimeError("404")
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    fake_ha.pause.assert_not_called()
    await d.restore("media_player.x")
    fake_ha.play.assert_not_called()


async def test_pause_error_does_not_block_other_targets(fake_ha):
    fake_ha.get_state.return_value = {"state": "playing", "attributes": {}}
    fake_ha.pause.side_effect = [RuntimeError("offline"), None]
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.broken", "media_player.ok"])
    assert fake_ha.pause.await_count == 2


async def test_schedule_restore_extends_deadline_no_stacked_tasks(fake_ha):
    """Two overlapping broadcasts to the same target → ONE restore task,
    fired after the later deadline (not the earlier)."""
    import asyncio as _asyncio
    fake_ha.get_state.return_value = {"state": "playing", "attributes": {}}
    d = Ducker(fake_ha)

    await d.snapshot_and_pause(["media_player.x"])
    d.schedule_restore(["media_player.x"], delay=0.05)  # would fire ~50ms
    # Second broadcast lands before the first restore fires
    await d.snapshot_and_pause(["media_player.x"])
    d.schedule_restore(["media_player.x"], delay=0.30)  # extend to ~300ms

    # Wait past the original deadline but before the extended one
    await _asyncio.sleep(0.15)
    fake_ha.play.assert_not_called()

    # Wait past the extended deadline
    await _asyncio.sleep(0.30)
    assert fake_ha.play.await_count == 1
    fake_ha.play.assert_awaited_with("media_player.x")
