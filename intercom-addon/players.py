"""/data/players.json: per-device settings on top of the default channel.

Schema (version 2):

    {
      "version":  2,
      "routes":   {source: [media_player, ...]},  # non-empty = explicit override;
                                                  # [] or absent = the channel
      "muted":    [source, ...],                  # PTT from these goes nowhere
      "excluded": [media_player, ...],            # never receive channel audio
      "default":  [media_player, ...],            # fallback when the channel is
                                                  # empty (registry unreachable)
      "aliases":  {source: display name},
      "selves":   {source: media_player}          # manual "this device's own
                                                  # speaker", beats the registry
    }

`source` is the ESPHome node name the device sends as X-Device-Name.

Version 1 had no "version", "muted" or "excluded", and an empty route meant
"play nowhere". Migration keeps every route, alias and self; non-empty routes
stay overrides and empty ones now mean the channel.
"""
import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

PLAYERS_FILE = "/data/players.json"
VERSION = 2


def _empty() -> dict:
    return {
        "version": VERSION,
        "routes": {},
        "muted": [],
        "excluded": [],
        "default": [],
        "aliases": {},
        "selves": {},
    }


def _read_raw() -> Optional[dict]:
    try:
        with open(PLAYERS_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        log.warning("players.json not found; using defaults")
        return None
    except (json.JSONDecodeError, OSError) as e:
        log.error("players.json unreadable (%s); using defaults", e)
        return None
    return data if isinstance(data, dict) else {}


def normalize(data: dict) -> dict:
    """Coerce any stored version into the current schema (pure; no I/O)."""
    def get(key, kind):
        value = data.get(key)
        return value if isinstance(value, kind) else kind()

    routes = {
        k: [e for e in v if isinstance(e, str)]
        for k, v in get("routes", dict).items()
        if isinstance(k, str) and k and isinstance(v, list)
    }
    return {
        "version": VERSION,
        # v1 [] meant "nowhere"; in v2 it means "the channel". Kept as-is so
        # the source stays listed in the old /api/players UI.
        "routes": routes,
        "muted": [s for s in get("muted", list) if isinstance(s, str) and s],
        "excluded": [e for e in get("excluded", list) if isinstance(e, str)],
        "default": [e for e in get("default", list) if isinstance(e, str)],
        "aliases": get("aliases", dict),
        "selves": get("selves", dict),
    }


def load_players() -> dict:
    """Read PLAYERS_FILE in the current schema; defaults if missing/malformed."""
    raw = _read_raw()
    return _empty() if raw is None else normalize(raw)


def migrate_file() -> bool:
    """Rewrite an older players.json in the current schema. True if rewritten."""
    raw = _read_raw()
    if raw is None or raw.get("version") == VERSION:
        return False
    data = normalize(raw)
    overrides = sorted(k for k, v in data["routes"].items() if v)
    channel = sorted(k for k, v in data["routes"].items() if not v)
    log.info("players.json v%s → v%d: overrides=%s, channel=%s",
             raw.get("version", 1), VERSION, overrides, channel)
    save_players(data)
    return True


def save_players(data: dict) -> None:
    """Atomically write PLAYERS_FILE in the current schema."""
    data = normalize(data)
    tmp = PLAYERS_FILE + ".tmp"
    os.makedirs(os.path.dirname(PLAYERS_FILE), exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, PLAYERS_FILE)


def validate(body) -> Optional[str]:
    """Return an error message string, or None if the payload is valid."""
    if not isinstance(body, dict):
        return "body must be an object"
    if "routes" not in body or "default" not in body:
        return "missing 'routes' or 'default'"

    routes = body["routes"]
    if not isinstance(routes, dict):
        return "'routes' must be an object"
    for key, value in routes.items():
        if not isinstance(key, str) or not key:
            return "route keys must be non-empty strings"
        if not _is_entity_list(value):
            return f"routes[{key!r}] must be a list of media_player.* entity ids"

    if not _is_entity_list(body["default"]):
        return "'default' must be a list of media_player.* entity ids"

    aliases = body.get("aliases", {})
    if not isinstance(aliases, dict):
        return "'aliases' must be an object"
    for k, v in aliases.items():
        if not isinstance(k, str) or not k:
            return "alias keys must be non-empty strings"
        if not isinstance(v, str) or not v:
            return f"aliases[{k!r}] must be a non-empty string"

    selves = body.get("selves", {})
    if not isinstance(selves, dict):
        return "'selves' must be an object"
    for k, v in selves.items():
        if not isinstance(k, str) or not k:
            return "selves keys must be non-empty strings"
        if not isinstance(v, str) or not v.startswith("media_player."):
            return f"selves[{k!r}] must be a media_player.* entity id"

    muted = body.get("muted", [])
    if not isinstance(muted, list) or not all(isinstance(s, str) and s for s in muted):
        return "'muted' must be a list of device names"

    if not _is_entity_list(body.get("excluded", [])):
        return "'excluded' must be a list of media_player.* entity ids"

    return None


def _is_entity_list(value) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(v, str) and v.startswith("media_player.") for v in value)
    )
