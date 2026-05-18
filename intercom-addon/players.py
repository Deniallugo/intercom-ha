import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

PLAYERS_FILE = "/data/players.json"


def _empty() -> dict:
    return {"routes": {}, "default": [], "aliases": {}, "selves": {}}


def load_players() -> dict:
    """Read PLAYERS_FILE. Returns an empty schema if missing or malformed."""
    try:
        with open(PLAYERS_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        log.warning("players.json not found; using empty routes")
        return _empty()
    except (json.JSONDecodeError, OSError) as e:
        log.error("players.json unreadable (%s); using empty routes", e)
        return _empty()

    if not isinstance(data, dict):
        data = {}
    routes  = data.get("routes")
    default = data.get("default")
    aliases = data.get("aliases")
    selves  = data.get("selves")
    return {
        "routes":  routes  if isinstance(routes,  dict) else {},
        "default": default if isinstance(default, list) else [],
        "aliases": aliases if isinstance(aliases, dict) else {},
        "selves":  selves  if isinstance(selves,  dict) else {},
    }


def save_players(data: dict) -> None:
    """Atomically write PLAYERS_FILE."""
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

    return None


def _is_entity_list(value) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(v, str) and v.startswith("media_player.") for v in value)
    )
