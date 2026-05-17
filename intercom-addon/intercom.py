import json
import logging
import os
import struct
import uuid
from pathlib import Path

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
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2   # bytes, 16-bit
CHANNELS = 1

sessions: dict[str, list[tuple[int, bytes]]] = {}


def load_options() -> dict:
    with open(OPTIONS_FILE) as f:
        return json.load(f)


def wav_header(pcm_len: int) -> bytes:
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + pcm_len,
        b"WAVE",
        b"fmt ",
        16,
        1,                                          # PCM
        CHANNELS,
        SAMPLE_RATE,
        SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH,      # byte rate
        CHANNELS * SAMPLE_WIDTH,                    # block align
        SAMPLE_WIDTH * 8,                           # bits per sample
        b"data",
        pcm_len,
    )


async def handle_intercom(request: web.Request) -> web.Response:
    session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
    chunk_index = int(request.headers.get("X-Chunk-Index", "0"))
    is_final = request.headers.get("X-Final") == "1"
    data = await request.read()

    log.info("chunk received  session=%s index=%d size=%d final=%s",
             session_id[:8], chunk_index, len(data), is_final)

    sessions.setdefault(session_id, []).append((chunk_index, data))

    if not is_final:
        return web.Response(status=204)

    # Assemble chunks in order
    chunks = sorted(sessions.pop(session_id), key=lambda x: x[0])
    pcm = b"".join(d for _, d in chunks)
    duration = len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)

    log.info("assembling  session=%s chunks=%d pcm=%d bytes duration=%.1fs",
             session_id[:8], len(chunks), len(pcm), duration)

    opts = load_options()
    ha_url = opts.get("ha_url", "http://homeassistant.local:8123")
    filename = f"intercom-{session_id}.wav"
    filepath = Path(CONFIG_WWW) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(wav_header(len(pcm)))
        f.write(pcm)
    log.info("WAV written  %s", filepath)

    token = os.environ["SUPERVISOR_TOKEN"]
    media_url = f"{ha_url}/local/{filename}"
    players = opts.get("media_players", [])
    log.info("playing on %d player(s): %s", len(players), players)

    try:
        async with ClientSession() as session:
            for player in players:
                resp = await session.post(
                    f"{HA_API}/services/media_player/play_media",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "entity_id": player,
                        "media_content_id": media_url,
                        "media_content_type": "music",
                    },
                )
                log.info("HA API  player=%s status=%d", player, resp.status)
    finally:
        filepath.unlink(missing_ok=True)
        log.info("cleanup  %s", filename)

    return web.Response(status=204)


def main() -> None:
    opts = load_options()
    port = opts.get("port", 9999)
    players = opts.get("media_players", [])
    log.info("starting intercom relay on port %d", port)
    log.info("target players: %s", players)
    app = web.Application()
    app.router.add_post("/intercom", handle_intercom)
    web.run_app(app, host="0.0.0.0", port=port, print=None)


if __name__ == "__main__":
    main()
