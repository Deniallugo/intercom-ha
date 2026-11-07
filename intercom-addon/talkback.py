import logging
import time
from typing import Callable, Optional

log = logging.getLogger(__name__)

WINDOW_SECONDS = 30


class TalkbackWindows:
    """After a broadcast, a receiving device's next upload within
    WINDOW_SECONDS goes back to the sender only. Windows expire or are
    overwritten; they are not consumed on use.
    """

    def __init__(self, now_func: Callable[[], float] = time.monotonic):
        self._now = now_func
        # device_name -> (sender_self_player_entity, expires_at_monotonic)
        self._windows: dict[str, tuple[str, float]] = {}

    def record_broadcast(
        self,
        source: str,
        targets: list[str],
        selves: dict[str, str],
    ) -> None:
        """For each target media_player that maps back to a known source,
        open a 30s reply window pointing at `selves[source]`."""
        sender_self = selves.get(source)
        if not sender_self:
            return  # sender has no self-player; replies impossible
        target_to_source = {v: k for k, v in selves.items()}
        expires = self._now() + WINDOW_SECONDS
        for tgt in targets:
            receiver = target_to_source.get(tgt)
            if receiver is None:
                continue  # not a source; no upload path
            self._windows[receiver] = (sender_self, expires)
            log.info(
                "talkback  %s reply-window → %s  (expires in %.0fs)",
                receiver, sender_self, WINDOW_SECONDS,
            )

    def reply_target(self, device: str) -> Optional[str]:
        entry = self._windows.get(device)
        if entry is None:
            return None
        target, expires_at = entry
        if self._now() >= expires_at:
            self._windows.pop(device, None)
            return None
        return target
