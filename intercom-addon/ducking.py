import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class Snapshot:
    state: str
    volume_level: Optional[float]


class Ducker:
    """Snapshots target media_player state, pauses playing ones for the
    duration of a broadcast, and restores them. A target found paused is left
    paused on restore (the broadcast un-pauses it), so it stays as we found it.

    Concurrent broadcasts to the same target: keep the FIRST snapshot; later
    calls only extend the restore deadline. Exactly one in-flight restore
    task per target, regardless of how many broadcasts overlapped.
    """

    def __init__(self, ha, now_func: Callable[[], float] = time.monotonic):
        self._ha = ha
        self._now = now_func
        self._snapshots: dict[str, Snapshot] = {}
        self._deadlines: dict[str, float] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    async def snapshot_and_pause(self, targets: list[str]) -> None:
        for target in targets:
            if target in self._snapshots:
                continue
            snap = await self._snapshot(target)
            self._snapshots[target] = snap
            if snap.state == "playing":
                try:
                    await self._ha.pause(target)
                    log.info("ducking   %s  state=%s  → paused",
                             target, snap.state)
                except Exception as e:
                    log.warning("ducking pause failed for %s: %s", target, e)
            else:
                log.info("ducking   %s  state=%s  → no-op", target, snap.state)

    def schedule_restore(self, targets: list[str], delay: float) -> None:
        """Restore each target `delay` seconds from now. If a restore is
        already pending for a target, extend its deadline (don't stack tasks).
        """
        deadline = self._now() + delay
        for target in targets:
            had_deadline = target in self._deadlines
            self._deadlines[target] = max(
                self._deadlines.get(target, 0.0), deadline,
            )
            if not had_deadline:
                self._tasks[target] = asyncio.create_task(
                    self._restore_when_ready(target),
                )

    async def _restore_when_ready(self, target: str) -> None:
        while True:
            now = self._now()
            deadline = self._deadlines.get(target, 0.0)
            if now >= deadline:
                break
            await asyncio.sleep(deadline - now)
        self._deadlines.pop(target, None)
        self._tasks.pop(target, None)
        await self.restore(target)

    async def _snapshot(self, target: str) -> Snapshot:
        try:
            data = await self._ha.get_state(target)
        except Exception as e:
            log.warning("ducking snapshot failed for %s: %s", target, e)
            return Snapshot(state="idle", volume_level=None)
        return Snapshot(
            state=data.get("state", "idle"),
            volume_level=(data.get("attributes") or {}).get("volume_level"),
        )

    async def restore(self, target: str) -> None:
        snap = self._snapshots.pop(target, None)
        if snap is None:
            return
        if snap.state == "playing":
            try:
                await self._ha.play(target)
                log.info("restored  %s  state=playing", target)
            except Exception as e:
                log.warning("ducking restore failed for %s: %s", target, e)
        elif snap.state == "paused":
            # Injecting a one-shot media_url un-pauses a paused player — it
            # auto-resumes the queue when the broadcast ends. Re-pause to leave
            # it as we found it.
            try:
                await self._ha.pause(target)
                log.info("restored  %s  state=paused", target)
            except Exception as e:
                log.warning("ducking restore failed for %s: %s", target, e)
