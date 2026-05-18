# Ingress Media Player Picker — Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ingress-served picker UI to the intercom add-on. Replace the global `media_players` option with a per-source routes map (`{"routes": {source_id: [entity_ids]}, "default": [entity_ids]}`) stored in `/data/players.json`. Update `POST /intercom` to enroll unknown sources and route to `routes[X-Device-Name]` (falling back to `default`).

**Architecture:** Two aiohttp listeners run concurrently in one process. Port 9999 (LAN) serves only `POST /intercom`. Port 8099 (ingress) serves the picker UI and JSON API. State lives in `/data/players.json`, read fresh on every intercom request, written atomically by the UI's POST handler and by source-enrollment.

**Tech Stack:** Python 3, aiohttp, pytest + pytest-aiohttp. No new deps.

**Scope:** Only the add-on server (`intercom-addon/*`) and its tests. ESPHome device changes from the spec (`atom-echo.yaml` speaker + media_player) are explicitly out of scope for this plan.

---

## File structure

**Modify:**
- `intercom-addon/intercom.py` — all the Python logic (handlers, helpers, app wiring, inline HTML)
- `intercom-addon/config.yaml` — add ingress fields, remove `media_players`, bump version

**Create:**
- `tests/test_picker.py` — new tests for picker endpoints and routing

**Leave alone:**
- `tests/test_intercom.py` — references `srv.sessions` / `X-Chunk-Index` that no longer exist; pre-existing failures per spec
- `intercom-addon/Dockerfile`, `intercom-addon/run.sh`, `intercom-addon/build.json` — no changes needed
- `atom-echo.yaml`, `uploader.h`, `recorder.h` — ESPHome side, out of scope

`intercom.py` stays a single file: the spec mandates inline HTML and unchanged Dockerfile. New code is organized into clearly-named functions so tests can target each piece.

---

## Notes for the implementer

- **Working directory:** `/Users/danillugovskoy/own/intercom`.
- **Run tests with:** `pytest tests/test_picker.py -v` (don't run the whole `tests/` dir — `test_intercom.py` is stale and will error at collection).
- **Atomic writes:** use `os.replace(tmp, final)` — atomic on POSIX, works on the add-on's Alpine container.
- **Path constants:** the add-on uses `/data/options.json` and `/config/www/...`. New constant: `PLAYERS_FILE = "/data/players.json"`. For tests, monkeypatch `srv.PLAYERS_FILE` to a `tmp_path`.
- **aiohttp two-app pattern:** start each `web.Application` via `AppRunner` + `TCPSite`, then `await asyncio.Event().wait()` to block forever. Replaces the current `web.run_app(...)`.
- **HTML is a triple-quoted string** in `intercom.py`. Use `./api/players` (relative) for fetches so it works through the HA ingress prefix.
- **DRY/YAGNI/TDD:** test → fail → minimal code → pass → commit.

---

## Task 1: Persistence helpers (`load_players`, `save_players`)

**Files:**
- Modify: `intercom-addon/intercom.py` — add constants and two functions near the top (after `load_options`).
- Test: `tests/test_picker.py` (new file).

- [ ] **Step 1: Create the new test file with persistence tests**

Write to `tests/test_picker.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402


@pytest.fixture
def players_file(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    monkeypatch.setattr(srv, "PLAYERS_FILE", str(p))
    return p


def test_load_players_missing_file_returns_empty(players_file):
    data = srv.load_players()
    assert data == {"routes": {}, "default": []}


def test_load_players_malformed_returns_empty(players_file):
    players_file.write_text("not json")
    data = srv.load_players()
    assert data == {"routes": {}, "default": []}


def test_load_players_reads_existing(players_file):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.x"]},
        "default": ["media_player.y"],
    }))
    data = srv.load_players()
    assert data["routes"] == {"src-a": ["media_player.x"]}
    assert data["default"] == ["media_player.y"]


def test_save_players_writes_atomically(players_file):
    srv.save_players({"routes": {"a": ["media_player.x"]}, "default": []})
    assert json.loads(players_file.read_text()) == {
        "routes": {"a": ["media_player.x"]},
        "default": [],
    }
    # No leftover .tmp file
    assert not (players_file.parent / "players.json.tmp").exists()


def test_save_then_load_roundtrip(players_file):
    original = {"routes": {"a": ["media_player.x", "media_player.y"]}, "default": ["media_player.z"]}
    srv.save_players(original)
    assert srv.load_players() == original
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_picker.py -v`
Expected: 5 errors/failures — `PLAYERS_FILE`, `load_players`, `save_players` don't exist yet.

- [ ] **Step 3: Add the constant and functions to intercom.py**

In `intercom-addon/intercom.py`, after the existing module-level constants (`OPTIONS_FILE`, `CONFIG_WWW`, `HA_API`), add:

```python
PLAYERS_FILE = "/data/players.json"
```

After the existing `load_options()` function, add:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_picker.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): add players.json persistence helpers"
```

---

## Task 2: Supervisor entity fetch (`fetch_media_players`)

**Files:**
- Modify: `intercom-addon/intercom.py` — add an async helper.
- Test: `tests/test_picker.py`.

- [ ] **Step 1: Add tests**

Append to `tests/test_picker.py`:

```python
import os
from unittest.mock import patch


class _FakeStatesResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def json(self):
        return self._payload

    async def text(self):
        return json.dumps(self._payload)


class _FakeStatesSession:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status
        self.calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeStatesResponse(self._payload, self._status)


@pytest.fixture
def supervisor_token(monkeypatch):
    monkeypatch.setitem(os.environ, "SUPERVISOR_TOKEN", "tok")


async def test_fetch_media_players_filters_and_maps(supervisor_token):
    states = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "light.bulb", "attributes": {"friendly_name": "Bulb"}},
        {"entity_id": "media_player.bedroom", "attributes": {}},
    ]
    fake = _FakeStatesSession(states)
    with patch("intercom.ClientSession", return_value=fake):
        result = await srv.fetch_media_players()

    assert result == [
        {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen"},
        {"entity_id": "media_player.bedroom", "friendly_name": "media_player.bedroom"},
    ]
    url, kwargs = fake.calls[0]
    assert url == f"{srv.HA_API}/states"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


async def test_fetch_media_players_raises_on_non_200(supervisor_token):
    fake = _FakeStatesSession([], status=503)
    with patch("intercom.ClientSession", return_value=fake):
        with pytest.raises(RuntimeError):
            await srv.fetch_media_players()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_picker.py -v`
Expected: 2 new failures — `fetch_media_players` not defined.

- [ ] **Step 3: Implement `fetch_media_players`**

In `intercom-addon/intercom.py`, add after `save_players`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_picker.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): add supervisor media_player fetch helper"
```

---

## Task 3: Picker GET endpoint (`handle_picker_get`)

**Files:**
- Modify: `intercom-addon/intercom.py` — add handler.
- Test: `tests/test_picker.py`.

- [ ] **Step 1: Add tests**

Append to `tests/test_picker.py`:

```python
from aiohttp import web


@pytest.fixture
def ingress_app():
    app = web.Application()
    app.router.add_get("/api/players", srv.handle_picker_get)
    app.router.add_post("/api/players", srv.handle_picker_post)
    return app


async def test_get_players_merges_available_and_routes(
    aiohttp_client, ingress_app, players_file, supervisor_token,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    states = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "media_player.bedroom", "attributes": {"friendly_name": "Bedroom"}},
    ]
    client = await aiohttp_client(ingress_app)
    with patch("intercom.ClientSession", return_value=_FakeStatesSession(states)):
        resp = await client.get("/api/players")
        body = await resp.json()

    assert resp.status == 200
    assert body["available"] == [
        {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen"},
        {"entity_id": "media_player.bedroom", "friendly_name": "Bedroom"},
    ]
    assert body["routes"] == {"src-a": ["media_player.kitchen"]}
    assert body["default"] == ["media_player.bedroom"]


async def test_get_players_supervisor_failure_returns_502(
    aiohttp_client, ingress_app, players_file, supervisor_token,
):
    client = await aiohttp_client(ingress_app)
    with patch("intercom.ClientSession", return_value=_FakeStatesSession([], status=503)):
        resp = await client.get("/api/players")
        body = await resp.json()

    assert resp.status == 502
    assert "error" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_picker.py -v`
Expected: 2 new failures — `handle_picker_get` and `handle_picker_post` not defined.

- [ ] **Step 3: Implement `handle_picker_get` (and a stub `handle_picker_post` so the fixture imports)**

In `intercom-addon/intercom.py`, add after `fetch_media_players`:

```python
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
    return web.Response(status=501)  # filled in by Task 4
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_picker.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): add GET /api/players endpoint"
```

---

## Task 4: Picker POST endpoint (validation + atomic write)

**Files:**
- Modify: `intercom-addon/intercom.py` — fill in `handle_picker_post`.
- Test: `tests/test_picker.py`.

- [ ] **Step 1: Add tests**

Append to `tests/test_picker.py`:

```python
async def test_post_players_writes_file(aiohttp_client, ingress_app, players_file):
    client = await aiohttp_client(ingress_app)
    payload = {
        "routes": {"src-a": ["media_player.kitchen", "media_player.bedroom"]},
        "default": ["media_player.kitchen"],
    }
    resp = await client.post("/api/players", json=payload)

    assert resp.status == 204
    assert json.loads(players_file.read_text()) == payload


async def test_post_players_rejects_non_media_player_target(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {"src-a": ["light.bulb"]},
        "default": [],
    })
    assert resp.status == 400
    assert not players_file.exists()


async def test_post_players_rejects_non_list_route_value(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {"src-a": "media_player.kitchen"},  # str, not list
        "default": [],
    })
    assert resp.status == 400


async def test_post_players_rejects_empty_source_key(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {"": ["media_player.kitchen"]},
        "default": [],
    })
    assert resp.status == 400


async def test_post_players_rejects_non_media_player_default(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {},
        "default": ["light.bulb"],
    })
    assert resp.status == 400


async def test_post_players_rejects_missing_fields(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={"routes": {}})  # no default
    assert resp.status == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_picker.py -v`
Expected: 6 new failures — handler returns 501 / writes nothing.

- [ ] **Step 3: Implement `handle_picker_post`**

Replace the stub in `intercom-addon/intercom.py`:

```python
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


def _validate_players_payload(body) -> str | None:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_picker.py -v`
Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): add POST /api/players with validation"
```

---

## Task 5: Update `POST /intercom` to use per-source routes

**Files:**
- Modify: `intercom-addon/intercom.py` — change `handle_intercom`.
- Test: `tests/test_picker.py`.

- [ ] **Step 1: Add tests**

Append to `tests/test_picker.py`:

```python
import uuid


class _FakeMediaResponse:
    status = 204


class _FakeMediaSession:
    def __init__(self):
        self.calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeMediaResponse()


@pytest.fixture
def lan_app():
    app = web.Application()
    app.router.add_post("/intercom", srv.handle_intercom)
    return app


@pytest.fixture
def www_dir(monkeypatch, tmp_path):
    d = tmp_path / "www"
    d.mkdir()
    monkeypatch.setattr(srv, "CONFIG_WWW", str(d))
    return d


@pytest.fixture
def fake_options(monkeypatch):
    monkeypatch.setattr(srv, "load_options", lambda: {"ha_url": "http://ha.test:8123"})


async def test_intercom_known_source_uses_route(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        resp = await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
        )

    assert resp.status == 204
    assert [c[1]["json"]["entity_id"] for c in fake.calls] == ["media_player.kitchen"]


async def test_intercom_unknown_source_enrolls_and_uses_default(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "new-src"},
        )

    assert json.loads(players_file.read_text())["routes"] == {"new-src": []}
    assert [c[1]["json"]["entity_id"] for c in fake.calls] == ["media_player.bedroom"]


async def test_intercom_missing_device_header_uses_unknown(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {"unknown": ["media_player.kitchen"]},
        "default": [],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid},
        )

    assert [c[1]["json"]["entity_id"] for c in fake.calls] == ["media_player.kitchen"]


async def test_intercom_known_source_with_empty_route_plays_nowhere(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": []},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        resp = await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
        )

    assert resp.status == 204
    assert fake.calls == []


async def test_intercom_missing_players_file_returns_204_no_call(
    aiohttp_client, lan_app, players_file, supervisor_token, www_dir, fake_options,
):
    # players_file fixture monkeypatches PLAYERS_FILE but never creates it
    client = await aiohttp_client(lan_app)
    fake = _FakeMediaSession()
    sid = str(uuid.uuid4())

    with patch("intercom.ClientSession", return_value=fake):
        resp = await client.post(
            "/intercom", data=b"\x00" * 64,
            headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
        )

    assert resp.status == 204
    # source auto-enrolled, default is empty, so no HA calls
    assert fake.calls == []
    assert json.loads(players_file.read_text())["routes"] == {"src-a": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_picker.py -v`
Expected: 5 new failures — current `handle_intercom` reads `media_players` from options.

- [ ] **Step 3: Rewrite `handle_intercom`**

Replace the existing `handle_intercom` function in `intercom-addon/intercom.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_picker.py -v`
Expected: 20 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): route per-source via players.json"
```

---

## Task 6: Inline HTML picker page

**Files:**
- Modify: `intercom-addon/intercom.py` — add `PICKER_HTML` constant and `handle_picker_index` handler.

(No automated tests — UI is verified manually through the HA panel.)

- [ ] **Step 1: Add the HTML constant**

In `intercom-addon/intercom.py`, just above `handle_picker_get`, add:

```python
PICKER_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Intercom Picker</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 1.5rem; }
  h1 { margin-top: 0; }
  table { border-collapse: collapse; }
  th, td { border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: center; }
  th.src { text-align: left; }
  td.src { text-align: left; font-family: ui-monospace, monospace; }
  .target-id { color: #666; font-family: ui-monospace, monospace; font-size: 0.85em; }
  .toolbar { margin: 1rem 0; }
  .toast { margin-left: 1rem; color: #2a7; }
  .error { color: #c33; }
  .hint { color: #666; margin-top: 0.5rem; }
  button { padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }
</style>
</head>
<body>
<h1>Intercom Routes</h1>
<div id="status"></div>
<div id="content"></div>
<div class="toolbar">
  <button id="save">Save</button>
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

function render() {
  const sources = Object.keys(state.routes).sort();
  if (sources.length === 0) {
    $("content").innerHTML = '<div class="hint">No sources enrolled yet. Press PTT on each Atom Echo once to enroll it.</div>';
  } else {
    $("content").innerHTML = "";
  }

  const table = document.createElement("table");
  const head = table.insertRow();
  const corner = head.insertCell();
  corner.outerHTML = "<th class='src'>source &rarr; target</th>";
  for (const tgt of state.available) {
    const th = document.createElement("th");
    th.innerHTML = tgt.friendly_name + '<br><span class="target-id">' + tgt.entity_id + '</span>';
    head.appendChild(th);
  }

  for (const src of [...sources, "default"]) {
    const row = table.insertRow();
    const label = row.insertCell();
    label.className = "src";
    label.textContent = src;
    const selected = src === "default" ? state.default : state.routes[src];
    for (const tgt of state.available) {
      const td = row.insertCell();
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = selected.includes(tgt.entity_id);
      cb.dataset.src = src;
      cb.dataset.eid = tgt.entity_id;
      td.appendChild(cb);
    }
  }
  $("content").appendChild(table);
}

async function save() {
  const routes = {};
  for (const k of Object.keys(state.routes)) routes[k] = [];
  let def = [];
  for (const cb of document.querySelectorAll("input[type=checkbox]")) {
    if (!cb.checked) continue;
    if (cb.dataset.src === "default") def.push(cb.dataset.eid);
    else routes[cb.dataset.src].push(cb.dataset.eid);
  }
  $("toast").textContent = "";
  try {
    const resp = await fetch("./api/players", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({routes, default: def}),
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    state.routes = routes;
    state.default = def;
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
```

- [ ] **Step 2: Quick smoke check — run all tests**

Run: `pytest tests/test_picker.py -v`
Expected: 20 passed (no regressions; HTML constant doesn't affect tests).

- [ ] **Step 3: Commit**

```bash
git add intercom-addon/intercom.py
git commit -m "feat(intercom): add picker HTML page"
```

---

## Task 7: Wire up two aiohttp listeners in `main()`

**Files:**
- Modify: `intercom-addon/intercom.py` — replace `main()` to start two apps concurrently.

(No automated tests — multi-listener wiring is exercised at runtime in the add-on.)

- [ ] **Step 1: Replace `main()`**

Replace the existing `main()` and `if __name__ == "__main__":` block at the bottom of `intercom-addon/intercom.py` with:

```python
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
```

- [ ] **Step 2: Syntax check (Python parses cleanly)**

Run: `python3 -c "import ast; ast.parse(open('intercom-addon/intercom.py').read())"`
Expected: no output, exit 0.

- [ ] **Step 3: Re-run picker tests as a regression check**

Run: `pytest tests/test_picker.py -v`
Expected: 20 passed.

- [ ] **Step 4: Commit**

```bash
git add intercom-addon/intercom.py
git commit -m "feat(intercom): run LAN and ingress listeners in one process"
```

---

## Task 8: Update `config.yaml` (ingress, remove `media_players`, bump version)

**Files:**
- Modify: `intercom-addon/config.yaml`.

(No automated tests — config is consumed by the HA supervisor.)

- [ ] **Step 1: Edit config.yaml**

Replace the contents of `intercom-addon/config.yaml` with:

```yaml
image: ghcr.io/deniallugo/intercom-ha/intercom-relay
name: Intercom Relay
description: Receives audio from Atom Echo and plays it on HA media players.
version: "2.0.0"
slug: intercom_relay
init: false
hassio_api: true
hassio_role: homeassistant
homeassistant_api: true
ingress: true
ingress_port: 8099
panel_icon: mdi:speaker-multiple
panel_title: Intercom
arch:
  - aarch64
  - amd64
options:
  ha_url: "http://homeassistant.local:8123"
  port: 9999
  sample_rate: 16000
  bits_per_sample: 16
  channels: 1
schema:
  ha_url: str
  port: int
  sample_rate: int
  bits_per_sample: int
  channels: int
map:
  - config:rw
ports:
  9999/tcp: 9999
ports_description:
  9999/tcp: ESPHome audio relay
```

- [ ] **Step 2: YAML syntax check**

Run: `python3 -c "import yaml; yaml.safe_load(open('intercom-addon/config.yaml'))"`
Expected: no output, exit 0. (If `yaml` isn't installed: `pip install pyyaml` first.)

- [ ] **Step 3: Commit**

```bash
git add intercom-addon/config.yaml
git commit -m "feat(addon): enable ingress, drop media_players option, bump 2.0.0"
```

---

## Final verification

- [ ] **Step 1: Run all picker tests one last time**

Run: `pytest tests/test_picker.py -v`
Expected: 20 passed.

- [ ] **Step 2: Confirm `intercom.py` parses and imports cleanly**

Run: `python3 -c "import sys; sys.path.insert(0, 'intercom-addon'); import intercom; print('OK')"`
Expected: `OK`. (Will succeed even though `SUPERVISOR_TOKEN` isn't set — it's only read at request time.)

- [ ] **Step 3: Confirm git log**

Run: `git log --oneline -10`
Expected: 8 new commits in order matching tasks 1–8.

- [ ] **Step 4: Tell the user**

Report: server-side implementation complete, 20 picker tests passing, ready to test in the add-on (requires building the container and installing on a HA host).
