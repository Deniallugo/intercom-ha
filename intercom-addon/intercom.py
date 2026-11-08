import asyncio
import json
import logging
import re
import signal
import time
import uuid
from pathlib import Path
from typing import Optional

from aiohttp import web

from ha_client import HAClient
from chimes import ChimeMixer
from ducking import Ducker
from airtime import Airtime
from talkback import TalkbackWindows
import channel
import players
import announce
import denoise
import recordings

ha = HAClient()

# Default format at import (so tests can call handlers directly); _run()
# rebuilds it from options.json.
mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
# Fallback for players without MEDIA_ANNOUNCE: pause, play, resume.
ducker = Ducker(ha)
# One broadcast at a time per speaker; later ones wait (bounded).
airtime = Airtime()
talkback = TalkbackWindows()

# In-memory, per source: {"last_seen": unix_ts, "last_broadcast": {...}}.
activity: dict[str, dict] = {}

# An unknown X-Device-Name forces a registry refresh, at most this often.
FORCED_REFRESH_INTERVAL = 30.0
_last_forced_refresh: float = float("-inf")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OPTIONS_FILE = "/data/options.json"
CONFIG_WWW = "/config/www"
PICKER_HTML_FILE = Path(__file__).parent / "picker.html"

# Speech is levelled either way; without cleanup the hiss rises with it
# (voice-s3: -42.9 dBFS floor instead of -60.2).
DEFAULT_DENOISE = True

DEFAULT_KEEP_RECORDINGS = 10

# X-Session-ID ends up in a /config/www filename: reject anything that could
# traverse out of it.
_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

# MediaPlayerEntityFeature.MEDIA_ANNOUNCE (homeassistant/components/
# media_player/const.py). ESPHome speaker media players report it.
MEDIA_ANNOUNCE = 1 << 20
# Reading player states (announce support, availability) before playing.
STATES_TIMEOUT = 2.0


def safe_session_id(raw: str) -> str:
    return raw if _SAFE_SESSION_ID.match(raw) else str(uuid.uuid4())


def load_options() -> dict:
    with open(OPTIONS_FILE) as f:
        return json.load(f)


def denoise_enabled() -> bool:
    """Full cleanup (True) or level only (False); default if options unreadable."""
    try:
        return bool(load_options().get("denoise", DEFAULT_DENOISE))
    except (OSError, json.JSONDecodeError, AttributeError) as e:
        log.warning("could not read the denoise option (%s) — using default", e)
        return DEFAULT_DENOISE


def keep_recordings() -> int:
    """How many mic recordings to retain, from options.json."""
    try:
        value = int(load_options().get("keep_recordings", DEFAULT_KEEP_RECORDINGS))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return DEFAULT_KEEP_RECORDINGS
    return max(0, value)


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
        "muted":     state["muted"],
        "excluded":  state["excluded"],
    })


async def handle_picker_post(request: web.Request) -> web.Response:
    """Legacy picker save. Fields it does not send (muted, excluded) are kept."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)

    err = players.validate(body)
    if err:
        return web.json_response({"error": err}, status=400)

    state = players.load_players()
    state.update({
        "routes":  body["routes"],
        "default": body["default"],
        "aliases": body.get("aliases", {}),
        "selves":  body.get("selves", {}),
    })
    for key in ("muted", "excluded"):
        if key in body:
            state[key] = body[key]
    players.save_players(state)
    return web.Response(status=204)


async def registry_members(source: Optional[str] = None) -> tuple[list, Optional[str]]:
    """Intercom devices from HA's registry, and an error string if it could
    not be read. A `source` the cached registry cannot place forces a
    refresh (rate-limited): a newly adopted device is heard at once."""
    global _last_forced_refresh
    try:
        registry = await ha.get_registry()
        members = channel.build_members(registry)
        if source and source != "unknown" and channel.match_source(source, members) is None:
            now = time.monotonic()
            if now - _last_forced_refresh >= FORCED_REFRESH_INTERVAL:
                _last_forced_refresh = now
                log.info("source=%s not in registry cache; refreshing", source)
                registry = await ha.get_registry(force=True)
                members = channel.build_members(registry)
        return members, None
    except Exception as e:
        log.warning("device registry unavailable (%s); channel falls back to "
                    "the 'default' players", e)
        return [], str(e)


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


async def handle_intercom(request: web.Request) -> web.Response:
    """POST /intercom — a PTT upload, heard by every other intercom device.

    POST /intercom/reply (or X-Intercom-Reply: 1) asks to answer whoever
    last spoke to this device within talkback.WINDOW_SECONDS; with nobody to
    answer it goes to the channel like a plain PTT."""
    session_id = safe_session_id(request.headers.get("X-Session-ID", ""))
    source = (request.headers.get("X-Device-Name") or "unknown").strip() or "unknown"
    want_reply = (request.path.rstrip("/").endswith("/reply")
                  or _truthy(request.headers.get("X-Intercom-Reply")))

    pcm = await request.read()
    # Whole frames only: a stray odd byte would shift the closing chime by one
    # byte and play it as noise.
    frame = mixer.sample_width * mixer.channels
    pcm = pcm[: len(pcm) - len(pcm) % frame]
    if not pcm:
        log.warning("empty body from session=%s, ignoring", session_id[:8])
        return web.Response(status=400)

    duration = mixer.pcm_duration_seconds(pcm)
    log.info("received  session=%s  source=%s  pcm=%d bytes  duration=%.1fs",
             session_id[:8], source, len(pcm), duration)

    # Saved before routing, so it survives a failed broadcast.
    try:
        kept = recordings.save(
            mixer.build_plain_wav(pcm),
            source=source,
            session_id=session_id,
            keep=keep_recordings(),
        )
        if kept is not None:
            log.info("recording kept  %s", kept.name)
    except OSError as e:
        log.warning("could not keep recording: %s", e)

    received_at = time.time()
    activity.setdefault(source, {})["last_seen"] = received_at

    state = players.load_players()
    if source not in state["routes"]:
        # [] = the channel; listed so the device shows up in the UI.
        state["routes"][source] = []
        players.save_players(state)
        log.info("enrolled new source=%s (channel)", source)

    members, _ = await registry_members(source)

    me = channel.self_player(source, state, members)
    reply_to = None
    if want_reply:
        # Windows are keyed by the receiving device's own player.
        reply_to = talkback.reply_target(me) if me else None
        if reply_to is None:
            log.info("reply from %s: nobody to answer; using the channel", source)

    plan = channel.plan(source, state, members, reply_to=reply_to)
    targets = plan.targets
    if me is None and source != "unknown":
        log.warning("source=%s matches no HA device; it may hear itself "
                    "(set its speaker in 'selves')", source)
    log.info("route  source=%s  mode=%s  targets=%s", source, plan.mode, targets)

    if me:
        talkback.record(me, targets)

    # Only the broadcast is cleaned; the saved recording stays raw. Pure-Python
    # DSP takes seconds, hence the thread. A failure falls back to raw audio.
    try:
        if denoise_enabled():
            clean = await asyncio.to_thread(
                denoise.process, pcm, sample_rate=mixer.sample_rate)
        else:
            clean = await asyncio.to_thread(
                denoise.level, pcm, sample_rate=mixer.sample_rate)
    except Exception:
        log.exception("denoise failed — broadcasting raw audio")
        clean = pcm

    wav = mixer.build_wav(clean)
    total_duration = mixer.total_duration_seconds(clean)
    log.info("WAV built  %s  (%.2fs incl. chimes)", session_id[:8], total_duration)

    results = await _play_on_targets(
        wav, "wav", total_duration, targets, name=f"intercom-{session_id}"
    )
    # Same dict as `results`: a queued target's outcome lands here later.
    activity[source]["last_broadcast"] = {
        "ts": received_at,
        "mode": plan.mode,
        "targets": list(targets),
        "results": results,
    }
    counts = delivery_counts(results)
    # 502 only when there was someone to reach and nobody was (or will be):
    # partial delivery is still a delivery, so 200 (207 is WebDAV's and tells
    # an HTTP client nothing that 200 + the per-target body does not).
    status = 502 if targets and not (counts["delivered"] or counts["queued"]) else 200
    log.info("delivery  session=%s  status=%d  %s", session_id[:8], status, counts)
    return web.json_response({
        "session": session_id,
        "source": source,
        "mode": plan.mode,
        "targets": list(targets),
        "results": results,
        **counts,
    }, status=status)


def delivery_counts(results: dict) -> dict:
    """{"delivered", "queued", "failed", "skipped"} over per-target results."""
    counts = {"delivered": 0, "queued": 0, "failed": 0, "skipped": 0}
    for r in results.values():
        outcome = r.get("outcome")
        if outcome == "ok":
            counts["delivered"] += 1
        elif outcome == "queued":
            counts["queued"] += 1
        elif outcome == "skipped":
            counts["skipped"] += 1
        else:
            counts["failed"] += 1
    return counts


async def handle_announce(request: web.Request) -> web.Response:
    """Speak `text` via TTS on `targets` (all media players if omitted)."""
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

    wav, ext, duration = announce.build_announcement_wav(audio, mixer)
    log.info("announce  text=%r  targets=%d", text[:40], len(targets))
    await _play_on_targets(
        wav, ext, duration, targets, name=f"announce-{uuid.uuid4()}"
    )
    return web.Response(status=204)


async def handle_devices_get(request: web.Request) -> web.Response:
    """GET /api/devices — every intercom device and how it is routed."""
    state = players.load_players()
    members, registry_error = await registry_members()
    try:
        entity_states = {s.get("entity_id"): s for s in await ha.get_states()}
        states_error = None
    except Exception as e:
        log.warning("devices: could not read player states: %s", e)
        entity_states, states_error = None, str(e)
    return web.json_response({
        "devices": channel.describe(state, members, activity, entity_states),
        "channel": channel.channel_players(state, members),
        "registry": {
            "ok": registry_error is None,
            "error": registry_error,
            "fetched_at": ha.registry_fetched_at,
        },
        "states_error": states_error,
    })


async def handle_device_patch(request: web.Request) -> web.Response:
    """PATCH /api/devices/{key} — key is a device name (X-Device-Name) or an
    HA device_id. Body, all optional:
      alias: str | null          display name (null clears)
      override: [media_player] | null   explicit targets (null/[] = channel)
      muted: bool                this device's PTT goes nowhere
      listen: bool               false = never receives channel audio
    """
    key = request.match_info.get("key", "")
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "body must be an object"}, status=400)

    state = players.load_players()
    members, _ = await registry_members()
    member = next((m for m in members if m.device_id == key), None)
    name = (member.node_name if member else None) or (None if member else key)
    if member and not name:
        # Registry device whose node name is unknown: use the source it matched.
        name = next((s for s in channel.known_sources(state, activity)
                     if channel.match_source(s, members) is member), None)

    source_fields = {"alias", "override", "muted"} & set(body)
    if source_fields and not name:
        return web.json_response(
            {"error": f"{sorted(source_fields)} need a device name; this device "
                      "has not talked yet"}, status=400)

    if "alias" in body:
        alias = body["alias"]
        if alias is None or alias == "":
            state["aliases"].pop(name, None)
        elif isinstance(alias, str):
            state["aliases"][name] = alias
        else:
            return web.json_response({"error": "'alias' must be a string or null"}, status=400)
    if "override" in body:
        override = body["override"] or []
        if not players._is_entity_list(override):
            return web.json_response(
                {"error": "'override' must be a list of media_player.* entity ids or null"},
                status=400)
        state["routes"][name] = override
    if "muted" in body:
        if not isinstance(body["muted"], bool):
            return web.json_response({"error": "'muted' must be a boolean"}, status=400)
        muted = [s for s in state["muted"] if s != name]
        state["muted"] = muted + [name] if body["muted"] else muted
    if "listen" in body:
        if not isinstance(body["listen"], bool):
            return web.json_response({"error": "'listen' must be a boolean"}, status=400)
        mp = (channel.self_player(name, state, members) if name else None) \
            or (member.media_player if member else None)
        if not mp:
            return web.json_response({"error": "device has no known media_player"}, status=400)
        excluded = [e for e in state["excluded"] if e != mp]
        state["excluded"] = excluded if body["listen"] else excluded + [mp]

    players.save_players(state)
    return web.Response(status=204)


async def handle_recordings_list(request: web.Request) -> web.Response:
    return web.json_response({
        "keep": keep_recordings(),
        "items": recordings.listing(),
    })


async def handle_recording_get(request: web.Request) -> web.StreamResponse:
    path = recordings.path_for(request.match_info.get("name", ""))
    if path is None:
        return web.Response(status=404, text="no such recording")
    return web.FileResponse(path, headers={"Content-Type": "audio/wav"})


async def handle_recording_delete(request: web.Request) -> web.Response:
    if not recordings.delete(request.match_info.get("name", "")):
        return web.Response(status=404, text="no such recording")
    return web.Response(status=204)


async def _play_on_targets(
    wav_bytes: bytes, ext: str, duration: float, targets: list[str], *, name: str
) -> dict:
    """Write the media to /config/www and play it on `targets`.

    Players with MEDIA_ANNOUNCE get play_media(announce=True) and handle
    their own music (ESPHome: announcement pipeline; Sonos: audio clip).
    Others go through the Ducker: pause, play, resume.

    A speaker still playing an earlier broadcast is not interrupted: this one
    is queued behind it (airtime.py) and played in the background, after the
    caller has its answer. Returns {entity_id: result}, result being one of

        {"ok": True,  "outcome": "ok",      "via": "announce"|"duck", "status": 200}
        {"ok": False, "outcome": "error",   "via": ..., "status"?: int, "error": str}
        {"ok": False, "outcome": "skipped", "reason": "unavailable"|...}
        {"ok": False, "outcome": "busy",    "error": str}   # queue too long
        {"ok": None,  "outcome": "queued",  "wait": seconds}

    A queued entry is replaced in place by its final result."""
    filename = f"{name}.{ext}"
    filepath = Path(CONFIG_WWW) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(wav_bytes)
    log.info("media written  %s  (%.2fs)", filepath, duration)

    results: dict = {}
    if not targets:
        log.warning("no targets; skipping play for %s", filename)
        _spawn(_delete_after(filepath, duration + 10))
        return results

    try:
        opts = load_options()
        ha_url = opts.get("ha_url", "http://homeassistant.local:8123")
        media_url = f"{ha_url}/local/{filename}"
        states = await _player_states()
    except Exception:
        _spawn(_delete_after(filepath, duration + 10))
        raise

    now_jobs, later_jobs = [], []
    for player in dict.fromkeys(targets):
        state = states.get(player) if states is not None else None
        reason = skip_reason(state, states is not None)
        if reason:
            log.info("skip  %s  (%s)", player, reason)
            results[player] = {"ok": False, "outcome": "skipped", "reason": reason}
            continue
        slot = airtime.book(player, duration)
        if slot is None:
            busy = airtime.busy_for(player)
            log.warning("busy  %s  (free in %.0fs); dropping %s", player, busy, filename)
            results[player] = {"ok": False, "outcome": "busy",
                               "error": f"speaker busy for another {busy:.0f}s"}
            continue
        job = (player, slot, supports_announce(state))
        if slot.wait > 0:
            log.info("queued  %s  starts in %.1fs", player, slot.wait)
            results[player] = {"ok": None, "outcome": "queued",
                               "wait": round(slot.wait, 1)}
            later_jobs.append(job)
        else:
            now_jobs.append(job)

    if now_jobs:
        log.info("playing on %d player(s): %s", len(now_jobs), [j[0] for j in now_jobs])
        done = await asyncio.gather(
            *(_deliver(p, media_url, duration, slot, a) for p, slot, a in now_jobs))
        for (player, _, _), result in zip(now_jobs, done):
            results[player] = result

    if later_jobs:
        _spawn(_deliver_later(later_jobs, results, media_url, duration, filepath))
    else:
        _spawn(_delete_after(filepath, duration + 10))
    return results


async def _player_states() -> Optional[dict]:
    """{entity_id: state object}, or None if HA's states cannot be read
    (then every target is tried the old way: no announce, Ducker)."""
    try:
        states = await asyncio.wait_for(ha.get_states(), STATES_TIMEOUT)
    except Exception as e:
        log.warning("could not read player states (%s); playing without "
                    "announce", str(e) or type(e).__name__)
        return None
    if not states:
        return None
    return {s.get("entity_id"): s for s in states if isinstance(s, dict)}


def supports_announce(state: Optional[dict]) -> bool:
    """True if the player declares MediaPlayerEntityFeature.MEDIA_ANNOUNCE."""
    attrs = (state or {}).get("attributes") or {}
    try:
        features = int(attrs.get("supported_features") or 0)
    except (TypeError, ValueError):
        return False
    return bool(features & MEDIA_ANNOUNCE)


def skip_reason(state: Optional[dict], states_known: bool) -> Optional[str]:
    """Why a target cannot play, or None. HA skips entity services on an
    unavailable entity yet answers 200, which would read as delivered."""
    if not states_known:
        return None
    if state is None:
        return "not in Home Assistant"
    if state.get("state") == "unavailable":
        return "unavailable"
    return None


async def _deliver(player: str, media_url: str, duration: float, slot,
                   use_announce: bool) -> dict:
    """play_media on one player in its booked slot; frees the slot on failure."""
    via = "announce" if use_announce else "duck"
    try:
        if use_announce:
            status = await ha.play_media(player, media_url, announce=True)
        else:
            # Restore in `finally`, or a failure leaves music paused and a
            # stale snapshot in the Ducker.
            try:
                await ducker.snapshot_and_pause([player])
                status = await ha.play_media(player, media_url)
            finally:
                ducker.schedule_restore([player], duration + 1.5)
    except Exception as e:
        if isinstance(e, asyncio.TimeoutError):
            error = "timed out"
        else:
            error = str(e) or type(e).__name__
        log.error("play_media failed for %s: %s", player, error)
        airtime.cancel(slot)
        return {"ok": False, "outcome": "error", "via": via, "error": error}
    log.info("HA API  player=%s  via=%s  status=%d", player, via, status)
    if 200 <= status < 300:
        return {"ok": True, "outcome": "ok", "via": via, "status": status}
    airtime.cancel(slot)
    return {"ok": False, "outcome": "error", "via": via, "status": status,
            "error": f"HA returned HTTP {status}"}


async def _deliver_later(jobs: list, results: dict, media_url: str,
                         duration: float, filepath: Path) -> None:
    """Play queued jobs as their slots open; the media file outlives them."""
    async def one(player, slot, use_announce):
        await asyncio.sleep(max(0.0, slot.start - airtime.now()))
        results[player] = await _deliver(player, media_url, duration, slot, use_announce)

    try:
        await asyncio.gather(*(one(*job) for job in jobs))
    finally:
        await _delete_after(filepath, duration + 10)


# The loop holds tasks weakly; keep them alive until done.
_background_tasks: set = set()


def _spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


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
    app.router.add_post("/intercom/reply", handle_intercom)
    app.router.add_post("/announce", handle_announce)
    return app


def make_ingress_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_picker_index)
    app.router.add_get("/api/players", handle_picker_get)
    app.router.add_post("/api/players", handle_picker_post)
    app.router.add_get("/api/devices", handle_devices_get)
    app.router.add_patch("/api/devices/{key}", handle_device_patch)
    app.router.add_post("/api/announce", handle_announce)
    app.router.add_get("/api/recordings", handle_recordings_list)
    app.router.add_get("/api/recordings/{name}", handle_recording_get)
    app.router.add_delete("/api/recordings/{name}", handle_recording_delete)
    return app


async def _run() -> None:
    global mixer

    opts = load_options()
    port = opts.get("port", 9999)
    ingress_port = 8099

    sample_rate = opts.get("sample_rate", 16000)
    bits = opts.get("bits_per_sample", 16)
    channels = opts.get("channels", 1)
    # Chimes and denoise handle 16-bit mono only (schema pins it; this catches
    # a hand-edited options.json).
    if bits != 16 or channels != 1:
        log.error("unsupported audio format %s-bit / %s channel(s) — only 16-bit "
                  "mono is supported; using that", bits, channels)
        bits, channels = 16, 1
    mixer = ChimeMixer(
        sample_rate=sample_rate,
        sample_width=bits // 8,
        channels=channels,
    )

    try:
        players.migrate_file()
    except OSError as e:
        log.error("could not migrate players.json: %s", e)

    log.info("starting intercom relay on port %d (LAN)", port)
    log.info("starting picker UI on port %d (ingress)", ingress_port)
    log.info("audio format: %d Hz, %d-bit, %d channel(s)",
             sample_rate, bits, channels)
    log.info("tts engine: %s", opts.get("tts_engine", "tts.piper"))
    keep = keep_recordings()
    log.info("denoise: %s", "on" if denoise_enabled() else "off")
    log.info("mic recordings: %s",
             f"keeping newest {keep} in {recordings.RECORDINGS_DIR}" if keep else "disabled")

    lan_runner = web.AppRunner(make_lan_app())
    await lan_runner.setup()
    await web.TCPSite(lan_runner, host="0.0.0.0", port=port).start()

    ingress_runner = web.AppRunner(make_ingress_app())
    await ingress_runner.setup()
    await web.TCPSite(ingress_runner, host="0.0.0.0", port=ingress_port).start()

    # Run until SIGTERM, then close servers and the HA session cleanly.
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    try:
        await stop.wait()
    finally:
        log.info("shutting down")
        await lan_runner.cleanup()
        await ingress_runner.cleanup()
        await ha.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
