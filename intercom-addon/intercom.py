import asyncio
import json
import logging
import os
import struct
import uuid
from pathlib import Path
from typing import Optional

from aiohttp import web, ClientSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OPTIONS_FILE = "/data/options.json"
CONFIG_WWW = "/config/www"
HA_API = "http://supervisor/core/api"
PLAYERS_FILE = "/data/players.json"

# Loaded once at startup from options.json
sample_rate: int = 16000
sample_width: int = 2   # bytes (bits_per_sample / 8)
channels: int = 1


def load_options() -> dict:
    with open(OPTIONS_FILE) as f:
        return json.load(f)


def load_players() -> dict:
    """Read /data/players.json. Returns {"routes": {}, "default": []} if
    missing or malformed."""
    try:
        with open(PLAYERS_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"routes": {}, "default": []}
    except (json.JSONDecodeError, OSError) as e:
        log.error("players.json unreadable (%s); using empty routes", e)
        return {"routes": {}, "default": []}

    routes = data.get("routes") if isinstance(data, dict) else None
    default = data.get("default") if isinstance(data, dict) else None
    return {
        "routes": routes if isinstance(routes, dict) else {},
        "default": default if isinstance(default, list) else [],
    }


def save_players(data: dict) -> None:
    """Atomically write /data/players.json."""
    tmp = PLAYERS_FILE + ".tmp"
    os.makedirs(os.path.dirname(PLAYERS_FILE), exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, PLAYERS_FILE)


async def fetch_media_players() -> list[dict]:
    """Return [{entity_id, friendly_name}, ...] for every media_player.* in HA."""
    token = os.environ["SUPERVISOR_TOKEN"]
    async with ClientSession() as session:
        resp = await session.get(
            f"{HA_API}/states",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status != 200:
            raise RuntimeError(f"supervisor /states returned {resp.status}")
        states = await resp.json()

    out = []
    for s in states:
        eid = s.get("entity_id", "")
        if not eid.startswith("media_player."):
            continue
        friendly = (s.get("attributes") or {}).get("friendly_name") or eid
        out.append({"entity_id": eid, "friendly_name": friendly})
    return out


async def handle_picker_get(request: web.Request) -> web.Response:
    try:
        available = await fetch_media_players()
    except Exception as e:
        log.error("failed to fetch media players: %s", e)
        return web.json_response({"error": str(e)}, status=502)

    players = load_players()
    return web.json_response({
        "available": available,
        "routes": players["routes"],
        "default": players["default"],
    })


async def handle_picker_post(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)

    err = _validate_players_payload(body)
    if err:
        return web.json_response({"error": err}, status=400)

    save_players({"routes": body["routes"], "default": body["default"]})
    return web.Response(status=204)


def _validate_players_payload(body) -> Optional[str]:
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
    return None


def _is_entity_list(value) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(v, str) and v.startswith("media_player.") for v in value)
    )


def wav_header(pcm_len: int) -> bytes:
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + pcm_len,
        b"WAVE",
        b"fmt ",
        16,
        1,                                              # PCM
        channels,
        sample_rate,
        sample_rate * channels * sample_width,          # byte rate
        channels * sample_width,                        # block align
        sample_width * 8,                               # bits per sample
        b"data",
        pcm_len,
    )


async def handle_intercom(request: web.Request) -> web.Response:
    session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
    source = (request.headers.get("X-Device-Name") or "unknown").strip() or "unknown"

    pcm = await request.read()
    if not pcm:
        log.warning("empty body from session=%s, ignoring", session_id[:8])
        return web.Response(status=400)

    duration = len(pcm) / (sample_rate * sample_width * channels)
    log.info("received  session=%s  source=%s  pcm=%d bytes  duration=%.1fs",
             session_id[:8], source, len(pcm), duration)

    players = load_players()
    if source in players["routes"]:
        targets = players["routes"][source]
    else:
        players["routes"][source] = []
        save_players(players)
        log.info("enrolled new source=%s; using default targets", source)
        targets = players["default"]

    opts = load_options()
    ha_url = opts.get("ha_url", "http://homeassistant.local:8123")
    filename = f"intercom-{session_id}.wav"
    filepath = Path(CONFIG_WWW) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(wav_header(len(pcm)))
        f.write(pcm)
    log.info("WAV written  %s  (%d Hz, %d-bit, %dch, %.2fs)",
             filepath, sample_rate, sample_width * 8, channels, duration)

    if not targets:
        log.warning("source=%s has no targets; skipping play", source)
        asyncio.create_task(_delete_after(filepath, duration + 10))
        return web.Response(status=204)

    token = os.environ["SUPERVISOR_TOKEN"]
    media_url = f"{ha_url}/local/{filename}"
    log.info("playing on %d player(s): %s", len(targets), targets)

    async with ClientSession() as session:
        for player in targets:
            resp = await session.post(
                f"{HA_API}/services/media_player/play_media",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "entity_id": player,
                    "media_content_id": media_url,
                    "media_content_type": "music",
                },
            )
            log.info("HA API  player=%s  status=%d", player, resp.status)

    asyncio.create_task(_delete_after(filepath, duration + 10))
    return web.Response(status=204)


async def _delete_after(filepath: Path, delay: float) -> None:
    await asyncio.sleep(delay)
    try:
        filepath.unlink()
        log.info("cleaned up %s", filepath.name)
    except OSError as e:
        log.warning("cleanup failed for %s: %s", filepath.name, e)


def main() -> None:
    global sample_rate, sample_width, channels

    opts = load_options()
    port = opts.get("port", 9999)

    sample_rate = opts.get("sample_rate", 16000)
    bits = opts.get("bits_per_sample", 16)
    sample_width = bits // 8
    channels = opts.get("channels", 1)

    log.info("starting intercom relay on port %d", port)
    log.info("audio format: %d Hz, %d-bit, %d channel(s)",
             sample_rate, bits, channels)
    log.info("target players: %s", opts.get("media_players", []))

    app = web.Application(client_max_size=10 * 1024 * 1024)
    app.router.add_post("/intercom", handle_intercom)
    web.run_app(app, host="0.0.0.0", port=port, print=None)


if __name__ == "__main__":
    main()
