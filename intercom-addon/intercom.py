import asyncio
import json
import logging
import re
import uuid
from pathlib import Path

from aiohttp import web

from ha_client import HAClient
from chimes import ChimeMixer
from ducking import Ducker
from talkback import TalkbackWindows
import players
import announce

ha = HAClient()

# Initialized at import with the addon's default audio format. _run()
# rebuilds it if options.json overrides any of the format fields. Module-level
# so tests can call handlers directly without going through _run().
mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
ducker = Ducker(ha)
talkback = TalkbackWindows()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OPTIONS_FILE = "/data/options.json"
CONFIG_WWW = "/config/www"
PICKER_HTML_FILE = Path(__file__).parent / "picker.html"

# X-Session-ID is attacker-controllable and is interpolated into a /config/www
# filename, so a value like "../../config/foo" would escape the directory and
# let a LAN client write an arbitrary .wav. Accept it for logging/correlation
# only when it's a safe token; otherwise fall back to a fresh random id.
_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def safe_session_id(raw: str) -> str:
    return raw if _SAFE_SESSION_ID.match(raw) else str(uuid.uuid4())


def load_options() -> dict:
    with open(OPTIONS_FILE) as f:
        return json.load(f)


async def fetch_media_players() -> list[dict]:
    """Return [{entity_id, friendly_name}, ...] for every media_player.* in HA."""
    states = await ha.get_states()
    out = []
    for s in states:
        eid = s.get("entity_id", "")
        if not eid.startswith("media_player."):
            continue
        friendly = (s.get("attributes") or {}).get("friendly_name") or eid
        out.append({"entity_id": eid, "friendly_name": friendly})
    return out


async def handle_picker_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(PICKER_HTML_FILE)


async def handle_picker_get(request: web.Request) -> web.Response:
    try:
        available = await fetch_media_players()
    except Exception as e:
        log.error("failed to fetch media players: %s", e)
        return web.json_response({"error": str(e)}, status=502)

    state = players.load_players()
    return web.json_response({
        "available": available,
        "routes":    state["routes"],
        "default":   state["default"],
        "aliases":   state["aliases"],
        "selves":    state["selves"],
    })


async def handle_picker_post(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)

    err = players.validate(body)
    if err:
        return web.json_response({"error": err}, status=400)

    players.save_players({
        "routes":  body["routes"],
        "default": body["default"],
        "aliases": body.get("aliases", {}),
        "selves":  body.get("selves", {}),
    })
    return web.Response(status=204)


async def handle_intercom(request: web.Request) -> web.Response:
    session_id = safe_session_id(request.headers.get("X-Session-ID", ""))
    source = (request.headers.get("X-Device-Name") or "unknown").strip() or "unknown"

    pcm = await request.read()
    if not pcm:
        log.warning("empty body from session=%s, ignoring", session_id[:8])
        return web.Response(status=400)

    duration = mixer.pcm_duration_seconds(pcm)
    log.info("received  session=%s  source=%s  pcm=%d bytes  duration=%.1fs",
             session_id[:8], source, len(pcm), duration)

    state = players.load_players()

    # Talkback: if this source has a live reply window, route ONLY to the
    # sender's self-player.
    reply_to = talkback.reply_target(source)
    if reply_to is not None:
        log.info("talkback  source=%s  reply-to=%s", source, reply_to)
        targets = [reply_to]
    elif source in state["routes"]:
        targets = state["routes"][source]
    else:
        state["routes"][source] = []
        players.save_players(state)
        log.info("enrolled new source=%s; using default targets", source)
        targets = state["default"]

    talkback.record_broadcast(
        source=source,
        targets=targets,
        selves=state["selves"],
    )

    wav = mixer.build_wav(pcm)
    total_duration = mixer.total_duration_seconds(pcm)
    log.info("WAV built  %s  (%.2fs incl. chimes)", session_id[:8], total_duration)

    await _play_on_targets(
        wav, "wav", total_duration, targets, name=f"intercom-{session_id}"
    )
    return web.Response(status=204)


async def handle_announce(request: web.Request) -> web.Response:
    """Speak `text` (Piper TTS) on `targets`. Shared by the LAN endpoint
    (automations) and the ingress endpoint (UI). If `targets` is omitted/empty,
    announce on every media_player in HA."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)

    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        return web.json_response(
            {"error": "'text' must be a non-empty string"}, status=400
        )
    text = text.strip()

    targets = body.get("targets")
    if targets is not None and not players._is_entity_list(targets):
        return web.json_response(
            {"error": "'targets' must be a list of media_player.* entity ids"},
            status=400,
        )
    if not targets:
        try:
            available = await fetch_media_players()
        except Exception as e:
            log.error("announce: failed to fetch media players: %s", e)
            return web.json_response({"error": str(e)}, status=502)
        targets = [p["entity_id"] for p in available]

    if not targets:
        log.warning("announce: no media players available; skipping")
        return web.Response(status=204)

    opts = load_options()
    tts_engine = opts.get("tts_engine", "tts.piper")
    try:
        audio = await ha.tts_get_audio(tts_engine, text)
    except Exception as e:
        log.error("announce: tts_get_audio failed: %s", e)
        return web.json_response({"error": str(e)}, status=502)

    wav, ext, duration = announce.build_announcement_wav(audio)
    log.info("announce  text=%r  targets=%d", text[:40], len(targets))
    await _play_on_targets(
        wav, ext, duration, targets, name=f"announce-{uuid.uuid4()}"
    )
    return web.Response(status=204)


async def _play_on_targets(
    wav_bytes: bytes, ext: str, duration: float, targets: list[str], *, name: str
) -> None:
    """Write the media to /config/www and play it on `targets` with the same
    duck/restore/cleanup behavior the intercom uses. Used by both the intercom
    and announcement handlers."""
    filename = f"{name}.{ext}"
    filepath = Path(CONFIG_WWW) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(wav_bytes)
    log.info("media written  %s  (%.2fs)", filepath, duration)

    if not targets:
        log.warning("no targets; skipping play for %s", filename)
        asyncio.create_task(_delete_after(filepath, duration + 10))
        return

    opts = load_options()
    ha_url = opts.get("ha_url", "http://homeassistant.local:8123")
    await ducker.snapshot_and_pause(targets)
    media_url = f"{ha_url}/local/{filename}"
    log.info("playing on %d player(s): %s", len(targets), targets)
    for player in targets:
        status = await ha.play_media(player, media_url)
        log.info("HA API  player=%s  status=%d", player, status)
    ducker.schedule_restore(list(targets), duration + 1.5)
    asyncio.create_task(_delete_after(filepath, duration + 10))


async def _delete_after(filepath: Path, delay: float) -> None:
    await asyncio.sleep(delay)
    try:
        filepath.unlink()
        log.info("cleaned up %s", filepath.name)
    except OSError as e:
        log.warning("cleanup failed for %s: %s", filepath.name, e)


def make_lan_app() -> web.Application:
    app = web.Application(client_max_size=10 * 1024 * 1024)
    app.router.add_post("/intercom", handle_intercom)
    app.router.add_post("/announce", handle_announce)
    return app


def make_ingress_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_picker_index)
    app.router.add_get("/api/players", handle_picker_get)
    app.router.add_post("/api/players", handle_picker_post)
    app.router.add_post("/api/announce", handle_announce)
    return app


async def _run() -> None:
    global mixer

    opts = load_options()
    port = opts.get("port", 9999)
    ingress_port = 8099

    sample_rate = opts.get("sample_rate", 16000)
    bits = opts.get("bits_per_sample", 16)
    channels = opts.get("channels", 1)
    mixer = ChimeMixer(
        sample_rate=sample_rate,
        sample_width=bits // 8,
        channels=channels,
    )

    log.info("starting intercom relay on port %d (LAN)", port)
    log.info("starting picker UI on port %d (ingress)", ingress_port)
    log.info("audio format: %d Hz, %d-bit, %d channel(s)",
             sample_rate, bits, channels)
    log.info("tts engine: %s", opts.get("tts_engine", "tts.piper"))

    lan_runner = web.AppRunner(make_lan_app())
    await lan_runner.setup()
    await web.TCPSite(lan_runner, host="0.0.0.0", port=port).start()

    ingress_runner = web.AppRunner(make_ingress_app())
    await ingress_runner.setup()
    await web.TCPSite(ingress_runner, host="0.0.0.0", port=ingress_port).start()

    await asyncio.Event().wait()  # run forever


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
