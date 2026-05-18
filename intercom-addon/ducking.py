import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class Snapshot:
    state: str
    volume_level: Optional[float]


class Ducker:
    """Snapshots target media_player state, pauses playing ones for the
    duration of a broadcast, and restores them.

    Concurrent broadcasts to the same target: keep the FIRST snapshot;
    later calls are no-ops. restore() consumes the snapshot.
    """

    def __init__(self, ha):
        self._ha = ha
        self._snapshots: dict[str, Snapshot] = {}

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
