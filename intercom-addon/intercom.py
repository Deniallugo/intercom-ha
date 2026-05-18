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

# Loaded once at startup from options.json
sample_rate: int = 16000
sample_width: int = 2   # bytes (bits_per_sample / 8)
channels: int = 1


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

    pcm = await request.read()
    if not pcm:
        log.warning("empty body from session=%s, ignoring", session_id[:8])
        return web.Response(status=400)

    duration = len(pcm) / (sample_rate * sample_width * channels)
    log.info("received  session=%s  pcm=%d bytes  duration=%.1fs",
             session_id[:8], len(pcm), duration)

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

    token = os.environ["SUPERVISOR_TOKEN"]
    media_url = f"{ha_url}/local/{filename}"
    players = opts.get("media_players", [])
    log.info("playing on %d player(s): %s", len(players), players)

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
            log.info("HA API  player=%s  status=%d", player, resp.status)

    log.info("file kept for download: %s/local/%s", ha_url, filename)
    return web.Response(status=204)


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
