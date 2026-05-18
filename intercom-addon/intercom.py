import asyncio
import json
import logging
import os
import struct
import uuid
from pathlib import Path
from typing import Optional

from aiohttp import web

from ha_client import HAClient

ha = HAClient()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OPTIONS_FILE = "/data/options.json"
CONFIG_WWW = "/config/www"
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
        log.warning("players.json not found; using empty routes")
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
    states = await ha.get_states()
    out = []
    for s in states:
        eid = s.get("entity_id", "")
        if not eid.startswith("media_player."):
            continue
        friendly = (s.get("attributes") or {}).get("friendly_name") or eid
        out.append({"entity_id": eid, "friendly_name": friendly})
    return out


PICKER_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Intercom Picker</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 1.5rem; max-width: 720px; }
  h1 { margin-top: 0; }
  .row { padding: 0.75rem 0; border-bottom: 1px solid #eee; }
  .row:last-child { border-bottom: none; }
  .src { font-family: ui-monospace, monospace; font-weight: 600; margin-bottom: 0.4rem; }
  .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.4rem; min-height: 1.6rem; }
  .chip {
    display: inline-flex; align-items: center; gap: 0.35rem;
    padding: 0.2rem 0.6rem; background: #eef; border-radius: 999px;
    font-size: 0.9rem;
  }
  .chip button {
    border: none; background: transparent; cursor: pointer;
    font-size: 1rem; line-height: 1; padding: 0; color: #557;
  }
  .empty { color: #888; font-style: italic; font-size: 0.9rem; }
  select { padding: 0.35rem 0.5rem; font-size: 0.95rem; }
  .toolbar { margin-top: 1rem; }
  .toast { margin-left: 1rem; color: #2a7; }
  .error { color: #c33; }
  .hint { color: #666; margin: 0.75rem 0; }
  button.save { padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }
</style>
</head>
<body>
<h1>Intercom Routes</h1>
<div id="status"></div>
<div id="content"></div>
<div class="toolbar">
  <button class="save" id="save">Save</button>
  <span id="toast" class="toast"></span>
</div>
<script>
const $ = (id) => document.getElementById(id);
let state = { available: [], routes: {}, default: [] };

async function load() {
  $("status").textContent = "Loading...";
  try {
    const resp = await fetch("./api/players");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    state = await resp.json();
    render();
    $("status").textContent = "";
  } catch (e) {
    $("status").innerHTML = '<span class="error">Could not load: ' + e + '</span> <button onclick="load()">Retry</button>';
    $("content").innerHTML = "";
  }
}

function targetsFor(src) {
  return src === "default" ? state.default : state.routes[src];
}

function friendlyName(eid) {
  const t = state.available.find((x) => x.entity_id === eid);
  return t ? t.friendly_name : eid;
}

function renderRow(src) {
  const selected = targetsFor(src);
  const row = document.createElement("div");
  row.className = "row";

  const label = document.createElement("div");
  label.className = "src";
  label.textContent = src;
  row.appendChild(label);

  const chips = document.createElement("div");
  chips.className = "chips";
  if (selected.length === 0) {
    const e = document.createElement("span");
    e.className = "empty";
    e.textContent = "no targets";
    chips.appendChild(e);
  } else {
    for (const eid of selected) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = friendlyName(eid) + " ";
      const x = document.createElement("button");
      x.textContent = "×";
      x.title = eid;
      x.addEventListener("click", () => {
        const arr = targetsFor(src);
        const i = arr.indexOf(eid);
        if (i >= 0) arr.splice(i, 1);
        render();
      });
      chip.appendChild(x);
      chips.appendChild(chip);
    }
  }
  row.appendChild(chips);

  const sel = document.createElement("select");
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "+ add speaker…";
  sel.appendChild(placeholder);
  for (const tgt of state.available) {
    if (selected.includes(tgt.entity_id)) continue;
    const opt = document.createElement("option");
    opt.value = tgt.entity_id;
    opt.textContent = tgt.friendly_name + "  (" + tgt.entity_id + ")";
    sel.appendChild(opt);
  }
  sel.addEventListener("change", () => {
    if (!sel.value) return;
    targetsFor(src).push(sel.value);
    render();
  });
  row.appendChild(sel);

  return row;
}

function render() {
  const sources = Object.keys(state.routes).sort();
  $("content").innerHTML = "";

  if (sources.length === 0) {
    const hint = document.createElement("div");
    hint.className = "hint";
    hint.textContent = "No sources enrolled yet. Press the PTT on each Atom Echo once to enroll it.";
    $("content").appendChild(hint);
  }

  for (const src of [...sources, "default"]) {
    $("content").appendChild(renderRow(src));
  }
}

async function save() {
  $("toast").textContent = "";
  try {
    const resp = await fetch("./api/players", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ routes: state.routes, default: state.default }),
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    $("toast").textContent = "Saved";
    setTimeout(() => { $("toast").textContent = ""; }, 2000);
  } catch (e) {
    $("toast").innerHTML = '<span class="error">Save failed: ' + e + '</span>';
  }
}

$("save").addEventListener("click", save);
load();
</script>
</body>
</html>
"""


async def handle_picker_index(request: web.Request) -> web.Response:
    return web.Response(text=PICKER_HTML, content_type="text/html")


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

    media_url = f"{ha_url}/local/{filename}"
    log.info("playing on %d player(s): %s", len(targets), targets)
    for player in targets:
        status = await ha.play_media(player, media_url)
        log.info("HA API  player=%s  status=%d", player, status)

    asyncio.create_task(_delete_after(filepath, duration + 10))
    return web.Response(status=204)


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
    return app


def make_ingress_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_picker_index)
    app.router.add_get("/api/players", handle_picker_get)
    app.router.add_post("/api/players", handle_picker_post)
    return app


async def _run() -> None:
    global sample_rate, sample_width, channels

    opts = load_options()
    port = opts.get("port", 9999)
    ingress_port = 8099

    sample_rate = opts.get("sample_rate", 16000)
    bits = opts.get("bits_per_sample", 16)
    sample_width = bits // 8
    channels = opts.get("channels", 1)

    log.info("starting intercom relay on port %d (LAN)", port)
    log.info("starting picker UI on port %d (ingress)", ingress_port)
    log.info("audio format: %d Hz, %d-bit, %d channel(s)",
             sample_rate, bits, channels)

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
