import asyncio
import json
import logging
import uuid
from pathlib import Path

from aiohttp import web

from ha_client import HAClient
from chimes import ChimeMixer
import players

ha = HAClient()

# Initialized at import with the addon's default audio format. _run()
# rebuilds it if options.json overrides any of the format fields. Module-level
# so tests can call handlers directly without going through _run().
mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OPTIONS_FILE = "/data/options.json"
CONFIG_WWW = "/config/www"


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
  .src-line { display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.4rem; }
  .src-id { font-family: ui-monospace, monospace; color: #888; font-size: 0.85rem; }
  .alias-input { padding: 0.25rem 0.5rem; font-size: 0.95rem; flex: 0 0 14rem; }
  .self-line { margin-bottom: 0.4rem; font-size: 0.9rem; color: #444; }
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
let state = { available: [], routes: {}, default: [], aliases: {}, selves: {} };

async function load() {
  $("status").textContent = "Loading...";
  try {
    const resp = await fetch("./api/players");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    state = await resp.json();
    state.aliases = state.aliases || {};
    state.selves  = state.selves  || {};
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

  const head = document.createElement("div");
  head.className = "src-line";
  if (src === "default") {
    const label = document.createElement("div");
    label.style.fontWeight = "600";
    label.textContent = "default";
    head.appendChild(label);
  } else {
    const aliasInput = document.createElement("input");
    aliasInput.className = "alias-input";
    aliasInput.placeholder = "alias (e.g. Kitchen)";
    aliasInput.value = state.aliases[src] || "";
    aliasInput.addEventListener("input", () => {
      const v = aliasInput.value.trim();
      if (v) state.aliases[src] = v;
      else delete state.aliases[src];
    });
    head.appendChild(aliasInput);

    const sid = document.createElement("span");
    sid.className = "src-id";
    sid.textContent = src;
    head.appendChild(sid);
  }
  row.appendChild(head);

  if (src !== "default") {
    const selfLine = document.createElement("div");
    selfLine.className = "self-line";
    const lbl = document.createElement("span");
    lbl.textContent = "this device's speaker: ";
    selfLine.appendChild(lbl);

    const selfSel = document.createElement("select");
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "(none — talkback disabled)";
    selfSel.appendChild(none);
    for (const tgt of state.available) {
      const opt = document.createElement("option");
      opt.value = tgt.entity_id;
      opt.textContent = tgt.friendly_name + " (" + tgt.entity_id + ")";
      if (state.selves[src] === tgt.entity_id) opt.selected = true;
      selfSel.appendChild(opt);
    }
    selfSel.addEventListener("change", () => {
      if (selfSel.value) state.selves[src] = selfSel.value;
      else delete state.selves[src];
    });
    selfLine.appendChild(selfSel);
    row.appendChild(selfLine);
  }

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
      body: JSON.stringify({
        routes:  state.routes,
        default: state.default,
        aliases: state.aliases,
        selves:  state.selves,
      }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error("HTTP " + resp.status + (body.error ? ": " + body.error : ""));
    }
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
    session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
    source = (request.headers.get("X-Device-Name") or "unknown").strip() or "unknown"

    pcm = await request.read()
    if not pcm:
        log.warning("empty body from session=%s, ignoring", session_id[:8])
        return web.Response(status=400)

    duration = mixer.pcm_duration_seconds(pcm)
    log.info("received  session=%s  source=%s  pcm=%d bytes  duration=%.1fs",
             session_id[:8], source, len(pcm), duration)

    state = players.load_players()
    if source in state["routes"]:
        targets = state["routes"][source]
    else:
        state["routes"][source] = []
        players.save_players(state)
        log.info("enrolled new source=%s; using default targets", source)
        targets = state["default"]

    opts = load_options()
    ha_url = opts.get("ha_url", "http://homeassistant.local:8123")
    filename = f"intercom-{session_id}.wav"
    filepath = Path(CONFIG_WWW) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    filepath.write_bytes(mixer.build_wav(pcm))
    total_duration = mixer.total_duration_seconds(pcm)
    log.info("WAV written  %s  (%.2fs incl. chimes)", filepath, total_duration)

    if not targets:
        log.warning("source=%s has no targets; skipping play", source)
        asyncio.create_task(_delete_after(filepath, total_duration + 10))
        return web.Response(status=204)

    media_url = f"{ha_url}/local/{filename}"
    log.info("playing on %d player(s): %s", len(targets), targets)
    for player in targets:
        status = await ha.play_media(player, media_url)
        log.info("HA API  player=%s  status=%d", player, status)

    asyncio.create_task(_delete_after(filepath, total_duration + 10))
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
