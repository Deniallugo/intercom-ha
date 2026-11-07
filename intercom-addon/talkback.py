import logging
import time
from typing import Callable, Optional

log = logging.getLogger(__name__)

WINDOW_SECONDS = 30


class TalkbackWindows:
    """Remembers who last spoke to each device, for WINDOW_SECONDS.

    Consulted only when an upload explicitly asks for a reply
    (POST /intercom/reply or X-Intercom-Reply: 1); a plain PTT always goes to
    the channel. Windows expire or are overwritten; not consumed on use.
    """

    def __init__(self, now_func: Callable[[], float] = time.monotonic):
        self._now = now_func
        # receiver key -> (sender_self_player_entity, expires_at_monotonic).
        # The add-on keys receivers by their own media_player, so a device
        # that has never talked (name unknown yet) still gets a window.
        self._windows: dict[str, tuple[str, float]] = {}

    def record(self, sender_player: str, receivers: list[str]) -> None:
        """Open a window on each receiver key pointing back at `sender_player`."""
        expires = self._now() + WINDOW_SECONDS
        for receiver in receivers:
            if receiver == sender_player:
                continue
            self._windows[receiver] = (sender_player, expires)
            log.info("talkback  %s reply-window → %s  (expires in %.0fs)",
                     receiver, sender_player, WINDOW_SECONDS)

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
