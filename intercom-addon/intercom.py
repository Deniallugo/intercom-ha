import asyncio
import hmac
import json
import logging
import re
import signal
import time
import uuid
from pathlib import Path
from typing import Optional

from aiohttp import web
from aiohttp.abc import AbstractAccessLogger

from ha_client import HAClient
from chimes import ChimeMixer
from ducking import Ducker
from airtime import Airtime
from talkback import TalkbackWindows
import channel
import players
import announce
import denoise
import media
import recordings

ha = HAClient()

# Uploads are 16-bit mono PCM; the rate comes per request in X-Sample-Rate
# (firmware without the header records at 16 kHz). Announcements use `mixer`.
DEFAULT_SAMPLE_RATE = 16000
# Standard rates only: each gets its own cached chimes.
SAMPLE_RATES = frozenset({8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000})
mixer = ChimeMixer(sample_rate=DEFAULT_SAMPLE_RATE, sample_width=2, channels=1)
_mixers: dict[int, ChimeMixer] = {DEFAULT_SAMPLE_RATE: mixer}
# Fallback for players without MEDIA_ANNOUNCE: pause, play, resume.
ducker = Ducker(ha)
# One broadcast at a time per speaker; later ones wait (bounded).
airtime = Airtime()
talkback = TalkbackWindows()
media_store = media.MediaStore()
lan_address = media.LanAddress()

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

# Off by default: every conversation on disk is a privacy cost to opt into.
DEFAULT_KEEP_RECORDINGS = 0

# A served media name lives this long past the audio's end (players may start
# late; the name is unguessable). The /config/www fallback is public, so it
# keeps the old short window.
MEDIA_GRACE_SECONDS = 60.0
WWW_GRACE_SECONDS = 10.0

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


def parse_sample_rate(raw: Optional[str]) -> Optional[int]:
    """X-Sample-Rate -> Hz; DEFAULT_SAMPLE_RATE if absent, None if invalid."""
    if raw is None or not raw.strip():
        return DEFAULT_SAMPLE_RATE
    try:
        rate = int(raw.strip())
    except ValueError:
        return None
    return rate if rate in SAMPLE_RATES else None


def mixer_for(sample_rate: int) -> ChimeMixer:
    """16-bit mono mixer at `sample_rate` (chimes are rendered once per rate)."""
    mx = _mixers.get(sample_rate)
    if mx is None:
        mx = _mixers[sample_rate] = ChimeMixer(
            sample_rate=sample_rate, sample_width=2, channels=1)
    return mx


def lan_token() -> str:
    """Shared secret for the LAN port; '' = no authentication."""
    try:
        value = load_options().get("lan_token") or ""
    except (OSError, json.JSONDecodeError, AttributeError) as e:
        log.warning("could not read the lan_token option (%s) — auth off", e)
        return ""
    return value.strip() if isinstance(value, str) else ""


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
    # no-cache: HA's ingress iframe otherwise keeps showing an old panel
    # after an update, even across a hard reload of the HA page.
    return web.FileResponse(PICKER_HTML_FILE,
                            headers={"Cache-Control": "no-cache"})


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
    rate = parse_sample_rate(request.headers.get("X-Sample-Rate"))
    if rate is None:
        return web.json_response(
            {"error": f"X-Sample-Rate must be one of {sorted(SAMPLE_RATES)}"},
            status=400)
    mx = mixer_for(rate)

    pcm = await request.read()
    # Whole frames only: a stray odd byte would shift the closing chime by one
    # byte and play it as noise.
    frame = mx.sample_width * mx.channels
    pcm = pcm[: len(pcm) - len(pcm) % frame]
    if not pcm:
        log.warning("empty body from session=%s, ignoring", session_id[:8])
        return web.Response(status=400)

    duration = mx.pcm_duration_seconds(pcm)
    log.info("received  session=%s  source=%s  pcm=%d bytes  %d Hz  duration=%.1fs",
             session_id[:8], source, len(pcm), rate, duration)

    # Saved before routing, so it survives a failed broadcast.
    try:
        kept = recordings.save(
            mx.build_plain_wav(pcm),
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
                denoise.process, pcm, sample_rate=rate)
        else:
            clean = await asyncio.to_thread(
                denoise.level, pcm, sample_rate=rate)
    except Exception:
        log.exception("denoise failed — broadcasting raw audio")
        clean = pcm

    wav = mx.build_wav(clean)
    total_duration = mx.total_duration_seconds(clean)
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
    """Speak `text` via TTS on `targets`; omitted or empty = every intercom
    device (the channel), never every media_player in HA."""
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
        state = players.load_players()
        members, _ = await registry_members()
        targets = channel.channel_players(state, members) or list(state["default"])

    if not targets:
        log.warning("announce: no intercom devices known; skipping")
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
    results = await _play_on_targets(
        wav, ext, duration, targets, name=f"announce-{uuid.uuid4()}"
    )
    # Same contract as /intercom: 502 only if nobody was (or will be) reached.
    counts = delivery_counts(results)
    ok = counts["delivered"] or counts["queued"]
    body = {"targets": list(targets), "results": results, **counts}
    if not ok:
        body["error"] = "not delivered to any speaker"
    return web.json_response(body, status=200 if ok else 502)


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


def resolve_device(key: str, state: dict, members: list):
    """(name, member) for a /api/devices/{key}: key is an HA device_id or a
    device name (X-Device-Name). Either may be None; both None = unknown."""
    member = next((m for m in members if m.device_id == key), None)
    if member:
        name = member.node_name or next(
            (s for s in channel.known_sources(state, activity)
             if channel.match_source(s, members) is member), None)
        return name, member
    if key not in channel.known_sources(state, activity):
        member = next((m for m in members if m.node_name == key), None)
        return (key, member) if member else (None, None)
    return key, channel.self_member(key, state, members)


async def handle_device_delete(request: web.Request) -> web.Response:
    """DELETE /api/devices/{key} — forget a device.

    Clears everything the add-on keeps for its name: alias, override, manual
    self speaker, mute, last_seen / last_broadcast. A device HA's registry
    lists cannot be made to vanish from here (it is back on the next poll),
    so for it "remove" also means "stop receiving the channel" (listen:
    false); remove it from HA to drop it for good. Any device that talks
    again is enrolled again, like a new one."""
    key = request.match_info.get("key", "")
    state = players.load_players()
    members, _ = await registry_members()
    name, member = resolve_device(key, state, members)
    if name is None and member is None:
        return web.json_response({"error": "no such device"}, status=404)

    if name:
        state["routes"].pop(name, None)
        state["aliases"].pop(name, None)
        state["selves"].pop(name, None)
        state["muted"] = [s for s in state["muted"] if s != name]
        activity.pop(name, None)
    excluded = False
    if member and member.media_player:
        if member.media_player not in state["excluded"]:
            state["excluded"].append(member.media_player)
        excluded = True
    players.save_players(state)
    log.info("device removed  key=%s  name=%s  registry=%s", key, name,
             bool(member))
    return web.json_response({
        "name": name,
        "device_id": member.device_id if member else None,
        "registry": member is not None,
        "listening": not excluded if member else None,
    })


# A short "is this the right speaker?" sound: the two broadcast chimes.
TEST_GAP_SECONDS = 0.15


async def handle_device_test(request: web.Request) -> web.Response:
    """POST /api/devices/{key}/test — play the chimes on that device's own
    speaker. Same per-speaker result as a broadcast; not a broadcast (no
    last_broadcast, no talkback)."""
    key = request.match_info.get("key", "")
    state = players.load_players()
    members, _ = await registry_members()
    name, member = resolve_device(key, state, members)
    if name is None and member is None:
        return web.json_response({"error": "no such device"}, status=404)
    mp = (channel.self_player(name, state, members) if name else None) or \
        (member.media_player if member else None)
    if not mp:
        return web.json_response(
            {"error": "this device has no known speaker in Home Assistant"},
            status=400)
    gap = b"\x00" * (int(mixer.sample_rate * TEST_GAP_SECONDS)
                     * mixer.sample_width * mixer.channels)
    wav = mixer.build_wav(gap)
    try:
        results = await _play_on_targets(
            wav, "wav", mixer.total_duration_seconds(gap), [mp],
            name=f"test-{uuid.uuid4()}")
    except Exception as e:
        log.error("test sound for %s failed: %s", mp, e)
        return web.json_response({"media_player": mp, "error": str(e)}, status=502)
    counts = delivery_counts(results)
    ok = counts["delivered"] or counts["queued"]
    body = {"media_player": mp, "result": results.get(mp), **counts}
    return web.json_response(body, status=200 if ok else 502)


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
    """Publish the media (see _publish_media) and play it on `targets`.

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
    results: dict = {}
    if not targets:
        log.warning("no targets; skipping play for %s", name)
        return results

    # The name stays valid long enough for a queued delivery (airtime's
    # max_wait); the file goes `linger` after the last delivery starts.
    filepath, media_url, keep_for = await _publish_media(
        wav_bytes, ext, duration, name=name, wait=airtime.max_wait)
    linger = keep_for - airtime.max_wait
    filename = name   # for logs; the served name is a secret
    try:
        states = await _player_states()
    except Exception:
        _spawn(_delete_after(filepath, linger))
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
        _spawn(_deliver_later(later_jobs, results, media_url, duration, filepath,
                              linger))
    else:
        _spawn(_delete_after(filepath, linger))
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
                         duration: float, filepath: Path,
                         linger: float) -> None:
    """Play queued jobs as their slots open; the media file outlives them."""
    async def one(player, slot, use_announce):
        await asyncio.sleep(max(0.0, slot.start - airtime.now()))
        results[player] = await _deliver(player, media_url, duration, slot, use_announce)

    try:
        await asyncio.gather(*(one(*job) for job in jobs))
    finally:
        await _delete_after(filepath, linger)


async def _publish_media(body: bytes, ext: str, duration: float, *,
                         name: str, wait: float = 0.0) -> tuple[Path, str, float]:
    """Make `body` fetchable by the players: (file, URL, seconds to keep it).

    Served by the add-on under a random name; /config/www (public at /local/)
    only if the LAN port is not published. `wait` = longest queue delay."""
    base, ha_url = await lan_address.resolve(ha)
    if base:
        keep_for = duration + wait + MEDIA_GRACE_SECONDS
        path = media_store.put(body, ext, keep_for, label=name)
        log.info("media published  %s  (%.2fs, %d bytes)", name, duration, len(body))
        return path, f"{base}/media/{path.name}", keep_for
    filename = f"{name}.{ext}"
    path = Path(CONFIG_WWW) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    keep_for = duration + wait + WWW_GRACE_SECONDS
    log.warning("LAN port not published — media in %s (public at /local/ "
                "for up to %.0fs)", path, keep_for)
    return path, f"{ha_url}/local/{filename}", keep_for


async def handle_media_get(request: web.Request) -> web.StreamResponse:
    """GET /media/{name} — a broadcast, for the players. No auth: HA's
    ffmpeg proxy and Cast fetch it bare; the random name is the secret."""
    name = request.match_info.get("name", "")
    path = media_store.lookup(name)
    if path is None:
        return web.Response(status=404)
    return web.FileResponse(path, headers={
        "Content-Type": media.content_type(name),
        "Cache-Control": "no-store",
    })


# AppKey needs aiohttp >= 3.9; older Alpine images get a plain key.
LAN_TOKEN_KEY = web.AppKey("lan_token", str) if hasattr(web, "AppKey") else "lan_token"

# Paths on the LAN port that never need lan_token.
_LAN_PUBLIC_PREFIX = "/media/"


@web.middleware
async def lan_auth(request: web.Request, handler):
    """With lan_token set, require `Authorization: Bearer <token>` (or
    ?token=<token>, for firmware that can only change its URL)."""
    token = request.app.get(LAN_TOKEN_KEY) or ""
    if token and not request.path.startswith(_LAN_PUBLIC_PREFIX):
        auth = request.headers.get("Authorization", "")
        given = auth[7:].strip() if auth[:7].lower() == "bearer " else \
            request.query.get("token", "")
        if not hmac.compare_digest(given.encode(), token.encode()):
            log.warning("LAN request to %s from %s rejected: bad or missing token",
                        request.path, request.remote)
            return web.json_response(
                {"error": "unauthorized"}, status=401,
                headers={"WWW-Authenticate": "Bearer"})
    return await handler(request)


# The loop holds tasks weakly; keep them alive until done.
_background_tasks: set = set()


def _spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _delete_after(filepath: Path, delay: float) -> None:
    await asyncio.sleep(delay)
    if filepath.parent == media_store.directory():
        media_store.remove(filepath.name)
        return
    try:
        filepath.unlink()
        log.info("cleaned up %s", filepath.name)
    except OSError as e:
        log.warning("cleanup failed for %s: %s", filepath.name, e)


_LEGACY_WWW_MEDIA = re.compile(
    r"^(intercom|announce)-[A-Za-z0-9_-]{1,128}\.(wav|mp3)$")


def remove_stale_www_media() -> int:
    """Delete broadcasts a previous run left in /config/www (crash or
    restart before the cleanup timer). Only our own name pattern."""
    removed = 0
    try:
        candidates = list(Path(CONFIG_WWW).iterdir())
    except OSError:
        return 0
    for path in candidates:
        if _LEGACY_WWW_MEDIA.match(path.name) and path.is_file():
            try:
                path.unlink()
                removed += 1
            except OSError as e:
                log.warning("could not remove stale %s: %s", path.name, e)
    return removed


def make_lan_app(token: Optional[str] = None) -> web.Application:
    app = web.Application(client_max_size=10 * 1024 * 1024,
                          middlewares=[lan_auth])
    app[LAN_TOKEN_KEY] = lan_token() if token is None else token
    app.router.add_post("/intercom", handle_intercom)
    app.router.add_post("/intercom/reply", handle_intercom)
    app.router.add_post("/announce", handle_announce)
    app.router.add_get(media.ROUTE, handle_media_get)
    return app


def make_ingress_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_picker_index)
    app.router.add_get("/api/players", handle_picker_get)
    app.router.add_post("/api/players", handle_picker_post)
    app.router.add_get("/api/devices", handle_devices_get)
    app.router.add_patch("/api/devices/{key}", handle_device_patch)
    app.router.add_delete("/api/devices/{key}", handle_device_delete)
    app.router.add_post("/api/devices/{key}/test", handle_device_test)
    app.router.add_post("/api/announce", handle_announce)
    app.router.add_get("/api/recordings", handle_recordings_list)
    app.router.add_get("/api/recordings/{name}", handle_recording_get)
    app.router.add_delete("/api/recordings/{name}", handle_recording_delete)
    return app


class PathOnlyAccessLogger(AbstractAccessLogger):
    """Access log without the query string (?token=...) or media names."""

    def log(self, request, response, time):
        path = request.path
        if path.startswith(_LAN_PUBLIC_PREFIX):
            path = _LAN_PUBLIC_PREFIX + "…"
        self.logger.info("%s %s %s %d %.3fs", request.remote, request.method,
                         path, response.status, time)


async def _run() -> None:
    # Removed options (port, sample_rate, bits_per_sample, channels, ha_url)
    # may linger in options.json; they are ignored.
    opts = load_options()
    port = media.LAN_PORT   # the host port is set in the add-on's Network section
    ingress_port = 8099

    media_store.clear()
    stale = remove_stale_www_media()
    if stale:
        log.info("removed %d stale broadcast file(s) from %s", stale, CONFIG_WWW)

    try:
        players.migrate_file()
    except OSError as e:
        log.error("could not migrate players.json: %s", e)

    log.info("starting intercom relay on port %d (LAN)", port)
    log.info("starting picker UI on port %d (ingress)", ingress_port)
    log.info("audio format: 16-bit mono, X-Sample-Rate (default %d Hz)",
             DEFAULT_SAMPLE_RATE)
    log.info("tts engine: %s", opts.get("tts_engine", "tts.piper"))
    keep = keep_recordings()
    log.info("denoise: %s", "on" if denoise_enabled() else "off")
    log.info("mic recordings: %s",
             f"keeping newest {keep} in {recordings.RECORDINGS_DIR}" if keep
             else "off (existing ones kept until deleted in the panel)")
    lan_app = make_lan_app()
    log.info("LAN auth: %s", "lan_token required" if lan_app[LAN_TOKEN_KEY] else
             "off (anyone on the LAN can broadcast; set lan_token)")

    lan_runner = web.AppRunner(lan_app, access_log_class=PathOnlyAccessLogger)
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
