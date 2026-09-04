"""Retain the raw mic audio of intercom uploads inside the add-on.

The device's "Mic test recording" button POSTs to the same /intercom endpoint a
PTT broadcast uses, and that path writes the mixed WAV to /config/www only long
enough to play it before deleting it (see intercom._play_on_targets). Keeping a
copy here means a mic test can be listened to from the ingress panel without
repointing the device's ${intercom_url} at tools/mic-capture.py and reflashing.

What is stored is the *raw* mic PCM — no chimes — because that is what tells you
whether the microphone itself is working.

Files live in the add-on's own /data volume (persistent across restarts, not
visible in /config), newest `keep` retained and older ones pruned on each save.
"""
import logging
import os
import re
import time
import wave
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

RECORDINGS_DIR = "/data/recordings"

# A name arrives from the URL path and is turned straight back into a
# filesystem path, so only ever accept the exact shape save() produces —
# anything with a slash or a leading dot is rejected before it can traverse.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.wav$")
_UNSAFE = re.compile(r"[^A-Za-z0-9]+")

# Written under a .part suffix and renamed, so listing() never sees a
# half-flushed file. The suffix is outside _SAFE_NAME, so it is also never
# servable or listable while in flight.
_PARTIAL_SUFFIX = ".part"


def _slug(text: str, limit: int) -> str:
    """Reduce arbitrary text (device name, session id) to filename-safe chars."""
    out = _UNSAFE.sub("-", str(text)).strip("-")
    return out[:limit] or "unknown"


def save(wav_bytes: bytes, *, source: str, session_id: str, keep: int) -> Optional[Path]:
    """Write `wav_bytes` as a new recording and prune to the newest `keep`.

    Returns the path written, or None when retention is disabled (keep <= 0).
    Raises OSError if the volume is not writable — the caller logs and carries
    on, since a failed capture must never cost the user the broadcast.
    """
    if keep <= 0:
        return None

    directory = Path(RECORDINGS_DIR)
    directory.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    name = f"{stamp}-{_slug(source, 40)}-{_slug(session_id, 8)}.wav"
    path = directory / name

    tmp = directory / (name + _PARTIAL_SUFFIX)
    tmp.write_bytes(wav_bytes)
    os.replace(tmp, path)

    prune(keep)
    return path


def prune(keep: int) -> int:
    """Delete all but the newest `keep` recordings. Returns the number removed."""
    entries = _entries()
    removed = 0
    for path, _ in entries[max(keep, 0):]:
        try:
            path.unlink()
            removed += 1
        except OSError as e:
            log.warning("could not prune %s: %s", path.name, e)
    return removed


def listing() -> list[dict]:
    """Metadata for every stored recording, newest first."""
    out = []
    for path, mtime in _entries():
        try:
            size = path.stat().st_size
        except OSError:
            continue
        out.append({
            "name": path.name,
            "source": source_of(path.name),
            "bytes": size,
            "modified": mtime,
            "seconds": duration_seconds(path),
        })
    return out


def path_for(name: str) -> Optional[Path]:
    """Resolve a listed name to a file on disk, or None if it is not one."""
    if not _SAFE_NAME.match(name or ""):
        return None
    path = Path(RECORDINGS_DIR) / name
    return path if path.is_file() else None


def delete(name: str) -> bool:
    path = path_for(name)
    if path is None:
        return False
    try:
        path.unlink()
        return True
    except OSError as e:
        log.warning("could not delete %s: %s", name, e)
        return False


def source_of(name: str) -> str:
    """Recover the device name from a filename: <date>-<time>-<source>-<sid>.wav"""
    parts = Path(name).stem.split("-")
    return "-".join(parts[2:-1]) if len(parts) >= 4 else "unknown"


def duration_seconds(path: Path) -> Optional[float]:
    """Playing length from the WAV header, or None if it is unreadable."""
    try:
        with wave.open(str(path), "rb") as w:
            rate = w.getframerate()
            return w.getnframes() / rate if rate else None
    except (wave.Error, OSError):
        return None


def _entries() -> list[tuple[Path, float]]:
    """(path, mtime) for stored recordings, newest first."""
    directory = Path(RECORDINGS_DIR)
    if not directory.is_dir():
        return []
    found = []
    for path in directory.glob("*.wav"):
        if not _SAFE_NAME.match(path.name):
            continue
        try:
            found.append((path, path.stat().st_mtime))
        except OSError:
            continue
    found.sort(key=lambda pair: pair[1], reverse=True)
    return found
