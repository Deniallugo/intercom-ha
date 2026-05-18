# Intercom features implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pre/post chimes, source aliases, pre-broadcast ducking, 30s talkback, and micro_wake_word PTT alternative to the HA intercom addon and Atom Echo firmware.

**Architecture:** Refactor the 446-line `intercom-addon/intercom.py` into focused modules (`players`, `chimes`, `ducking`, `talkback`, `ha_client`), then add each feature behind its module. Firmware gets a VAD-capable recorder and an always-on mic that micro_wake_word can listen to.

**Tech Stack:** Python 3 + aiohttp on the addon side; ESPHome esp-idf framework on the device side; pytest + pytest-aiohttp for tests.

**Spec:** [docs/superpowers/specs/2026-05-18-intercom-features-design.md](../specs/2026-05-18-intercom-features-design.md)

---

## File map

### New files (server)
- `intercom-addon/ha_client.py` — `HAClient` wrapping aiohttp.ClientSession for HA REST API calls
- `intercom-addon/players.py` — load/save/validate `players.json` (routes, default, aliases, selves)
- `intercom-addon/chimes.py` — generate pre/post chime PCM and build the WAV
- `intercom-addon/ducking.py` — `Ducker` class: snapshot/pause/restore with concurrency debounce
- `intercom-addon/talkback.py` — `TalkbackWindows` class: 30s reply-window state

### New tests
- `tests/test_ha_client.py`
- `tests/test_players.py`
- `tests/test_chimes.py`
- `tests/test_ducking.py`
- `tests/test_talkback.py`

### Modified files
- `intercom-addon/intercom.py` — becomes thin orchestration: handlers + wiring
- `tests/test_picker.py` — extend for aliases + selves fields
- `recorder.h` — add `REC_HOLD`/`REC_VAD` modes + RMS silence detector
- `atom-echo.yaml` — always-on mic, `micro_wake_word` component

### Deleted
- `tests/test_intercom.py` — stale (references removed `sessions` chunked-upload model; all 11 cases error before any change)

---

## Task 1: Delete stale tests

**Files:**
- Delete: `tests/test_intercom.py`

- [ ] **Step 1: Confirm the file is broken**

Run: `python3 -m pytest tests/test_intercom.py -v 2>&1 | tail -5`
Expected: 11 errors about `module 'intercom' has no attribute 'sessions'`.

- [ ] **Step 2: Delete the file**

```bash
rm tests/test_intercom.py
```

- [ ] **Step 3: Run remaining tests to confirm baseline**

Run: `python3 -m pytest tests/ -v`
Expected: 20 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_intercom.py
git commit -m "test: remove stale chunked-upload tests"
```

---

## Task 2: Extract HAClient

**Files:**
- Create: `intercom-addon/ha_client.py`
- Create: `tests/test_ha_client.py`
- Modify: `intercom-addon/intercom.py`
- Modify: `tests/test_picker.py` (patch path)

- [ ] **Step 1: Write the failing test**

Create `tests/test_ha_client.py`:

```python
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
from ha_client import HAClient  # noqa: E402


@pytest.fixture
def env_token(monkeypatch):
    monkeypatch.setitem(os.environ, "SUPERVISOR_TOKEN", "tok")


async def test_get_states_calls_supervisor(env_token):
    fake_resp = MagicMock(status=200)
    fake_resp.json = AsyncMock(return_value=[{"entity_id": "media_player.x"}])
    fake_session = MagicMock()
    fake_session.get = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    states = await client.get_states()

    assert states == [{"entity_id": "media_player.x"}]
    fake_session.get.assert_awaited_once()
    url, kwargs = fake_session.get.await_args.args[0], fake_session.get.await_args.kwargs
    assert url == "http://supervisor/core/api/states"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


async def test_get_states_raises_on_non_200(env_token):
    fake_resp = MagicMock(status=503)
    fake_session = MagicMock()
    fake_session.get = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    with pytest.raises(RuntimeError):
        await client.get_states()


async def test_play_media_posts_correct_body(env_token):
    fake_resp = MagicMock(status=200)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    await client.play_media("media_player.kitchen", "http://ha/local/x.wav")

    url = fake_session.post.await_args.args[0]
    body = fake_session.post.await_args.kwargs["json"]
    assert url == "http://supervisor/core/api/services/media_player/play_media"
    assert body == {
        "entity_id": "media_player.kitchen",
        "media_content_id": "http://ha/local/x.wav",
        "media_content_type": "music",
    }


async def test_pause_posts_pause_service(env_token):
    fake_resp = MagicMock(status=200)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    await client.pause("media_player.kitchen")

    url = fake_session.post.await_args.args[0]
    body = fake_session.post.await_args.kwargs["json"]
    assert url == "http://supervisor/core/api/services/media_player/media_pause"
    assert body == {"entity_id": "media_player.kitchen"}


async def test_play_posts_play_service(env_token):
    fake_resp = MagicMock(status=200)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=fake_resp)

    client = HAClient(session=fake_session)
    await client.play("media_player.kitchen")

    url = fake_session.post.await_args.args[0]
    body = fake_session.post.await_args.kwargs["json"]
    assert url == "http://supervisor/core/api/services/media_player/media_play"
    assert body == {"entity_id": "media_player.kitchen"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_ha_client.py -v`
Expected: ImportError on `from ha_client import HAClient`.

- [ ] **Step 3: Write the minimal implementation**

Create `intercom-addon/ha_client.py`:

```python
import os
from typing import Optional

from aiohttp import ClientSession

HA_API = "http://supervisor/core/api"


class HAClient:
    """Thin wrapper over the HA Supervisor REST API.

    Holds a single aiohttp.ClientSession across the addon's lifetime so we
    don't open a new TCP connection per request.
    """

    def __init__(self, session: Optional[ClientSession] = None):
        self._session = session

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            self._session = ClientSession()
        return self._session

    def _auth_headers(self) -> dict:
        token = os.environ["SUPERVISOR_TOKEN"]
        return {"Authorization": f"Bearer {token}"}

    async def get_states(self) -> list[dict]:
        resp = await self.session.get(
            f"{HA_API}/states", headers=self._auth_headers()
        )
        if resp.status != 200:
            raise RuntimeError(f"supervisor /states returned {resp.status}")
        return await resp.json()

    async def get_state(self, entity_id: str) -> dict:
        resp = await self.session.get(
            f"{HA_API}/states/{entity_id}", headers=self._auth_headers()
        )
        if resp.status != 200:
            raise RuntimeError(
                f"supervisor /states/{entity_id} returned {resp.status}"
            )
        return await resp.json()

    async def play_media(self, entity_id: str, media_url: str) -> int:
        resp = await self.session.post(
            f"{HA_API}/services/media_player/play_media",
            headers=self._auth_headers(),
            json={
                "entity_id": entity_id,
                "media_content_id": media_url,
                "media_content_type": "music",
            },
        )
        return resp.status

    async def pause(self, entity_id: str) -> int:
        resp = await self.session.post(
            f"{HA_API}/services/media_player/media_pause",
            headers=self._auth_headers(),
            json={"entity_id": entity_id},
        )
        return resp.status

    async def play(self, entity_id: str) -> int:
        resp = await self.session.post(
            f"{HA_API}/services/media_player/media_play",
            headers=self._auth_headers(),
            json={"entity_id": entity_id},
        )
        return resp.status

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_ha_client.py -v`
Expected: 5 passed.

- [ ] **Step 5: Refactor intercom.py to use HAClient**

In `intercom-addon/intercom.py`:

Add near the top of the file (after `from aiohttp import web, ClientSession`):

```python
from ha_client import HAClient

ha = HAClient()
```

Replace the body of `fetch_media_players` with:

```python
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
```

In `handle_intercom`, replace the play_media loop block:

```python
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
```

with:

```python
    media_url = f"{ha_url}/local/{filename}"
    log.info("playing on %d player(s): %s", len(targets), targets)
    for player in targets:
        status = await ha.play_media(player, media_url)
        log.info("HA API  player=%s  status=%d", player, status)
```

Remove the now-unused `HA_API` constant from intercom.py (it lives in ha_client.py now).

- [ ] **Step 6: Update test_picker.py patch path**

The existing tests in `tests/test_picker.py` patch `intercom.ClientSession`. They need to patch the new seam instead. Update every line that contains `patch("intercom.ClientSession"...)` to patch the HA client method directly. Easier: replace the entire `_FakeStatesSession` and `_FakeMediaSession` plumbing with monkey-patching `ha.get_states` and `ha.play_media`.

In `tests/test_picker.py`, add at the top of the existing fixtures section:

```python
@pytest.fixture
def fake_ha(monkeypatch):
    """Replace srv.ha methods with AsyncMock stubs; tests configure them as needed."""
    from unittest.mock import AsyncMock
    monkeypatch.setattr(srv.ha, "get_states", AsyncMock(return_value=[]))
    monkeypatch.setattr(srv.ha, "play_media", AsyncMock(return_value=204))
    return srv.ha
```

Rewrite `test_fetch_media_players_filters_and_maps`:

```python
async def test_fetch_media_players_filters_and_maps(fake_ha):
    fake_ha.get_states.return_value = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "light.bulb", "attributes": {"friendly_name": "Bulb"}},
        {"entity_id": "media_player.bedroom", "attributes": {}},
    ]
    result = await srv.fetch_media_players()
    assert result == [
        {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen"},
        {"entity_id": "media_player.bedroom", "friendly_name": "media_player.bedroom"},
    ]
```

Rewrite `test_fetch_media_players_raises_on_non_200`:

```python
async def test_fetch_media_players_raises_on_non_200(fake_ha):
    fake_ha.get_states.side_effect = RuntimeError("503")
    with pytest.raises(RuntimeError):
        await srv.fetch_media_players()
```

Rewrite `test_get_players_merges_available_and_routes` (drop the `supervisor_token` and `ClientSession` patch; use `fake_ha`):

```python
async def test_get_players_merges_available_and_routes(
    aiohttp_client, ingress_app, players_file, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    fake_ha.get_states.return_value = [
        {"entity_id": "media_player.kitchen", "attributes": {"friendly_name": "Kitchen"}},
        {"entity_id": "media_player.bedroom", "attributes": {"friendly_name": "Bedroom"}},
    ]
    client = await aiohttp_client(ingress_app)
    resp = await client.get("/api/players")
    body = await resp.json()

    assert resp.status == 200
    assert body["available"] == [
        {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen"},
        {"entity_id": "media_player.bedroom", "friendly_name": "Bedroom"},
    ]
    assert body["routes"] == {"src-a": ["media_player.kitchen"]}
    assert body["default"] == ["media_player.bedroom"]
```

Rewrite `test_get_players_supervisor_failure_returns_502`:

```python
async def test_get_players_supervisor_failure_returns_502(
    aiohttp_client, ingress_app, players_file, fake_ha,
):
    fake_ha.get_states.side_effect = RuntimeError("boom")
    client = await aiohttp_client(ingress_app)
    resp = await client.get("/api/players")
    body = await resp.json()
    assert resp.status == 502
    assert "error" in body
```

For the four `test_intercom_*` cases at the bottom, replace the `_FakeMediaSession` / `patch("intercom.ClientSession"...)` machinery with `fake_ha`. Rewrite `test_intercom_known_source_uses_route`:

```python
async def test_intercom_known_source_uses_route(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": ["media_player.bedroom"],
    }))
    client = await aiohttp_client(lan_app)
    sid = str(uuid.uuid4())
    resp = await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
    )
    assert resp.status == 204
    called_entities = [
        call.args[0] for call in fake_ha.play_media.call_args_list
    ]
    assert called_entities == ["media_player.kitchen"]
```

Apply the same `fake_ha` pattern to the other three `test_intercom_*` cases, replacing each `_FakeMediaSession` usage with `fake_ha.play_media.call_args_list`. Delete `_FakeMediaSession`, `_FakeMediaResponse`, `_FakeStatesSession`, `_FakeStatesResponse`, and the `supervisor_token` fixture (no longer needed since `fake_ha` short-circuits HA calls entirely).

- [ ] **Step 7: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass (test_picker.py rewrites + new test_ha_client.py).

- [ ] **Step 8: Commit**

```bash
git add intercom-addon/ha_client.py intercom-addon/intercom.py tests/test_ha_client.py tests/test_picker.py
git commit -m "refactor: extract HAClient, share single aiohttp session"
```

---

## Task 3: Extract players module

**Files:**
- Create: `intercom-addon/players.py`
- Create: `tests/test_players.py`
- Modify: `intercom-addon/intercom.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_players.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import players as p  # noqa: E402


@pytest.fixture
def players_file(monkeypatch, tmp_path):
    f = tmp_path / "players.json"
    monkeypatch.setattr(p, "PLAYERS_FILE", str(f))
    return f


def test_load_missing_returns_empty(players_file):
    assert p.load_players() == {"routes": {}, "default": []}


def test_load_malformed_returns_empty(players_file):
    players_file.write_text("not json")
    assert p.load_players() == {"routes": {}, "default": []}


def test_save_then_load_roundtrip(players_file):
    original = {"routes": {"a": ["media_player.x"]}, "default": ["media_player.y"]}
    p.save_players(original)
    assert p.load_players() == original


def test_save_writes_atomically(players_file):
    p.save_players({"routes": {}, "default": []})
    assert players_file.exists()
    assert not (players_file.parent / "players.json.tmp").exists()


def test_validate_accepts_minimal_payload():
    assert p.validate({"routes": {}, "default": []}) is None


def test_validate_rejects_non_dict():
    assert p.validate("nope") is not None


def test_validate_rejects_missing_fields():
    assert p.validate({"routes": {}}) is not None


def test_validate_rejects_non_media_player_target():
    err = p.validate({"routes": {"a": ["light.bulb"]}, "default": []})
    assert err is not None


def test_validate_rejects_empty_source_key():
    err = p.validate({"routes": {"": ["media_player.x"]}, "default": []})
    assert err is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_players.py -v`
Expected: ImportError on `import players`.

- [ ] **Step 3: Write the minimal implementation**

Create `intercom-addon/players.py`:

```python
import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

PLAYERS_FILE = "/data/players.json"


def load_players() -> dict:
    """Read PLAYERS_FILE. Returns {"routes": {}, "default": []} if missing
    or malformed."""
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
    return None


def _is_entity_list(value) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(v, str) and v.startswith("media_player.") for v in value)
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_players.py -v`
Expected: 9 passed.

- [ ] **Step 5: Update intercom.py to import from new module**

In `intercom-addon/intercom.py`:

Replace the top imports:

```python
import asyncio
import json
import logging
import os
import struct
import uuid
from pathlib import Path
from typing import Optional

from aiohttp import web, ClientSession
```

with:

```python
import asyncio
import json
import logging
import os
import struct
import uuid
from pathlib import Path

from aiohttp import web

from ha_client import HAClient
import players
```

Delete these functions/constants from `intercom.py` (they now live in `players.py`):
- `PLAYERS_FILE`
- `load_players()`
- `save_players()`
- `_validate_players_payload()`
- `_is_entity_list()`

Update callers. **Important:** the existing handler uses `players` as a local variable name — that would shadow the imported module. Rename the local var to `state`.

In `handle_intercom`:

```python
    state = players.load_players()
    if source in state["routes"]:
        targets = state["routes"][source]
    else:
        state["routes"][source] = []
        players.save_players(state)
        log.info("enrolled new source=%s; using default targets", source)
        targets = state["default"]
```

In `handle_picker_get`:

```python
    state = players.load_players()
    return web.json_response({
        "available": available,
        "routes":    state["routes"],
        "default":   state["default"],
    })
```

In `handle_picker_post`:

```python
    err = players.validate(body)
    if err:
        return web.json_response({"error": err}, status=400)
    players.save_players({"routes": body["routes"], "default": body["default"]})
    return web.Response(status=204)
```

- [ ] **Step 6: Update test_picker.py for the move**

`tests/test_picker.py` monkeypatches `srv.PLAYERS_FILE`. That no longer exists on `srv`. Change the `players_file` fixture to patch the new location:

```python
import players as players_mod

@pytest.fixture
def players_file(monkeypatch, tmp_path):
    p = tmp_path / "players.json"
    monkeypatch.setattr(players_mod, "PLAYERS_FILE", str(p))
    return p
```

Delete the duplicated load/save tests at the top of test_picker.py — they live in test_players.py now. Keep only the picker-handler integration tests.

- [ ] **Step 7: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All pass.

- [ ] **Step 8: Commit**

```bash
git add intercom-addon/players.py intercom-addon/intercom.py tests/test_players.py tests/test_picker.py
git commit -m "refactor: extract players module"
```

---

## Task 4: Add aliases and selves to players

**Files:**
- Modify: `intercom-addon/players.py`
- Modify: `tests/test_players.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_players.py`:

```python
def test_load_returns_empty_aliases_and_selves_by_default(players_file):
    players_file.write_text(json.dumps({"routes": {}, "default": []}))
    data = p.load_players()
    assert data["aliases"] == {}
    assert data["selves"] == {}


def test_aliases_and_selves_roundtrip(players_file):
    original = {
        "routes": {"a": []},
        "default": [],
        "aliases": {"a": "Kitchen"},
        "selves": {"a": "media_player.atom_echo_kitchen_player"},
    }
    p.save_players(original)
    loaded = p.load_players()
    assert loaded == original


def test_validate_accepts_aliases_and_selves():
    body = {
        "routes": {},
        "default": [],
        "aliases": {"a": "Kitchen"},
        "selves": {"a": "media_player.kitchen"},
    }
    assert p.validate(body) is None


def test_validate_aliases_must_be_dict():
    body = {"routes": {}, "default": [], "aliases": ["nope"]}
    assert p.validate(body) is not None


def test_validate_aliases_rejects_non_string_value():
    body = {"routes": {}, "default": [], "aliases": {"a": 123}}
    assert p.validate(body) is not None


def test_validate_aliases_rejects_empty_value():
    body = {"routes": {}, "default": [], "aliases": {"a": ""}}
    assert p.validate(body) is not None


def test_validate_selves_must_be_dict():
    body = {"routes": {}, "default": [], "selves": "nope"}
    assert p.validate(body) is not None


def test_validate_selves_value_must_start_with_media_player():
    body = {"routes": {}, "default": [], "selves": {"a": "light.kitchen"}}
    assert p.validate(body) is not None


def test_validate_selves_rejects_empty_key():
    body = {"routes": {}, "default": [], "selves": {"": "media_player.x"}}
    assert p.validate(body) is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_players.py -v`
Expected: 9 new tests fail.

- [ ] **Step 3: Update players.py**

In `intercom-addon/players.py`, change `load_players()`:

```python
def load_players() -> dict:
    try:
        with open(PLAYERS_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        log.warning("players.json not found; using empty routes")
        return {"routes": {}, "default": [], "aliases": {}, "selves": {}}
    except (json.JSONDecodeError, OSError) as e:
        log.error("players.json unreadable (%s); using empty routes", e)
        return {"routes": {}, "default": [], "aliases": {}, "selves": {}}

    if not isinstance(data, dict):
        data = {}
    routes = data.get("routes")
    default = data.get("default")
    aliases = data.get("aliases")
    selves = data.get("selves")
    return {
        "routes":  routes  if isinstance(routes,  dict) else {},
        "default": default if isinstance(default, list) else [],
        "aliases": aliases if isinstance(aliases, dict) else {},
        "selves":  selves  if isinstance(selves,  dict) else {},
    }
```

Add to `validate()` after the existing checks (just before `return None`):

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_players.py -v`
Expected: all pass.

- [ ] **Step 5: Update existing test_picker.py expectations**

The picker GET handler will return aliases + selves. Don't change handler yet — just verify existing tests still pass. Run: `python3 -m pytest tests/test_picker.py -v`. Expected: still passing (load_players now returns extra keys, but the GET response shape hasn't been touched yet — see Task 5).

- [ ] **Step 6: Commit**

```bash
git add intercom-addon/players.py tests/test_players.py
git commit -m "feat(players): add aliases and selves to schema"
```

---

## Task 5: Picker UI for aliases and self-players

**Files:**
- Modify: `intercom-addon/intercom.py` (PICKER_HTML + handle_picker_get + handle_picker_post)
- Modify: `tests/test_picker.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_picker.py`:

```python
async def test_get_players_includes_aliases_and_selves(
    aiohttp_client, ingress_app, players_file, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"a": []},
        "default": [],
        "aliases": {"a": "Kitchen"},
        "selves": {"a": "media_player.kitchen_player"},
    }))
    fake_ha.get_states.return_value = []
    client = await aiohttp_client(ingress_app)
    resp = await client.get("/api/players")
    body = await resp.json()

    assert resp.status == 200
    assert body["aliases"] == {"a": "Kitchen"}
    assert body["selves"] == {"a": "media_player.kitchen_player"}


async def test_post_players_persists_aliases_and_selves(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    payload = {
        "routes": {"a": []},
        "default": [],
        "aliases": {"a": "Kitchen"},
        "selves": {"a": "media_player.kitchen_player"},
    }
    resp = await client.post("/api/players", json=payload)
    assert resp.status == 204
    assert json.loads(players_file.read_text()) == payload


async def test_post_players_rejects_invalid_selves(
    aiohttp_client, ingress_app, players_file,
):
    client = await aiohttp_client(ingress_app)
    resp = await client.post("/api/players", json={
        "routes": {},
        "default": [],
        "selves": {"a": "light.bulb"},  # not a media_player.*
    })
    assert resp.status == 400


async def test_post_players_empty_alias_dropped(
    aiohttp_client, ingress_app, players_file,
):
    # Empty alias values are stripped on save (per spec).
    client = await aiohttp_client(ingress_app)
    payload = {
        "routes": {"a": []},
        "default": [],
        "aliases": {"a": ""},
        "selves": {},
    }
    resp = await client.post("/api/players", json=payload)
    # Validator rejects empty values, so this 400s. Confirm.
    assert resp.status == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_picker.py::test_get_players_includes_aliases_and_selves tests/test_picker.py::test_post_players_persists_aliases_and_selves -v`
Expected: failures (handler doesn't return aliases/selves or accept them yet).

- [ ] **Step 3: Update handle_picker_get and handle_picker_post**

In `intercom-addon/intercom.py`, replace `handle_picker_get`:

```python
async def handle_picker_get(request: web.Request) -> web.Response:
    try:
        available = await fetch_media_players()
    except Exception as e:
        log.error("failed to fetch media players: %s", e)
        return web.json_response({"error": str(e)}, status=502)

    p = players.load_players()
    return web.json_response({
        "available": available,
        "routes":    p["routes"],
        "default":   p["default"],
        "aliases":   p["aliases"],
        "selves":    p["selves"],
    })
```

Replace `handle_picker_post`:

```python
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
```

- [ ] **Step 4: Update PICKER_HTML**

Replace `PICKER_HTML` in `intercom-addon/intercom.py` with the updated version. The key changes:

1. `state` now includes `aliases` and `selves`.
2. `renderRow(src)` includes an alias `<input>` and a self-player `<select>` for non-default rows.
3. `save()` sends `aliases` and `selves` in the POST body.

Full replacement HTML (keep the same surrounding triple-quoted string):

```python
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

  // Source header: alias input + raw id (or just "default")
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

  // Self-player row (only for non-default)
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

  // Existing outgoing-targets chip + dropdown
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
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_picker.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(picker): UI for source aliases and self-players"
```

---

## Task 6: Chimes module

**Files:**
- Create: `intercom-addon/chimes.py`
- Create: `tests/test_chimes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_chimes.py`:

```python
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
from chimes import ChimeMixer, wav_header  # noqa: E402


def test_wav_header_is_44_bytes():
    assert len(wav_header(0, sample_rate=16000, channels=1, sample_width=2)) == 44


def test_wav_header_riff_tag():
    h = wav_header(100, sample_rate=16000, channels=1, sample_width=2)
    assert h[:4] == b"RIFF"


def test_wav_header_data_size_field():
    h = wav_header(200, sample_rate=16000, channels=1, sample_width=2)
    assert struct.unpack_from("<I", h, 40)[0] == 200


def test_chime_length_matches_duration():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    # 120ms chime at 16000 Hz mono 16-bit = 16000 * 0.120 * 2 = 3840 bytes
    assert len(mixer.chime_in) == 3840
    assert len(mixer.chime_out) == 3840


def test_chime_changes_with_sample_rate():
    a = ChimeMixer(sample_rate=8000, sample_width=2, channels=1).chime_in
    b = ChimeMixer(sample_rate=16000, sample_width=2, channels=1).chime_in
    assert len(b) == len(a) * 2


def test_build_wav_total_length():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x10\x20" * 100
    wav = mixer.build_wav(payload)
    expected_pcm_len = len(mixer.chime_in) + len(payload) + len(mixer.chime_out)
    assert len(wav) == 44 + expected_pcm_len


def test_build_wav_header_data_size_matches_pcm():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x10\x20" * 100
    wav = mixer.build_wav(payload)
    pcm_len = struct.unpack_from("<I", wav, 40)[0]
    assert pcm_len == len(mixer.chime_in) + len(payload) + len(mixer.chime_out)


def test_build_wav_payload_position():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\xAA\xBB" * 50
    wav = mixer.build_wav(payload)
    start = 44 + len(mixer.chime_in)
    end = start + len(payload)
    assert wav[start:end] == payload


def test_pcm_duration_seconds():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x00" * (16000 * 2)  # exactly 1s at 16k/16/1
    assert mixer.pcm_duration_seconds(payload) == pytest.approx(1.0)


def test_total_duration_includes_chimes():
    mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
    payload = b"\x00" * (16000 * 2)  # 1s
    total = mixer.total_duration_seconds(payload)
    # 1s payload + 0.120s + 0.120s = 1.240s
    assert total == pytest.approx(1.240, abs=0.001)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_chimes.py -v`
Expected: ImportError on `from chimes import ...`.

- [ ] **Step 3: Write the minimal implementation**

Create `intercom-addon/chimes.py`:

```python
import math
import struct
from typing import Optional

CHIME_MS = 120
FADE_MS = 5


def wav_header(pcm_len: int, *, sample_rate: int, channels: int, sample_width: int) -> bytes:
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + pcm_len,
        b"WAVE",
        b"fmt ",
        16,
        1,                                        # PCM
        channels,
        sample_rate,
        sample_rate * channels * sample_width,    # byte rate
        channels * sample_width,                  # block align
        sample_width * 8,                         # bits per sample
        b"data",
        pcm_len,
    )


class ChimeMixer:
    """Pre-generates pre/post chimes at the configured audio format and
    builds full WAVs by concatenating chime_in + payload + chime_out."""

    def __init__(self, sample_rate: int, sample_width: int, channels: int):
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.chime_in = self._generate_chime(800, 1200)
        self.chime_out = self._generate_chime(1200, 800)

    def _generate_chime(self, freq_start: float, freq_end: float) -> bytes:
        """Generate a CHIME_MS sine sweep from freq_start to freq_end with
        FADE_MS linear fade-in/out, encoded at the configured format."""
        if self.sample_width != 2:
            raise ValueError("chimes only support 16-bit PCM in v1")
        n_samples = int(self.sample_rate * CHIME_MS / 1000)
        n_fade = max(1, int(self.sample_rate * FADE_MS / 1000))
        amplitude = 16000  # ~half-scale for int16, well below clipping
        samples = bytearray()
        for i in range(n_samples):
            t = i / self.sample_rate
            # Linear frequency sweep
            freq = freq_start + (freq_end - freq_start) * (i / n_samples)
            value = math.sin(2 * math.pi * freq * t)
            # Fade envelope
            if i < n_fade:
                env = i / n_fade
            elif i > n_samples - n_fade:
                env = (n_samples - i) / n_fade
            else:
                env = 1.0
            v_int = int(value * env * amplitude)
            for _ in range(self.channels):
                samples.extend(struct.pack("<h", v_int))
        return bytes(samples)

    def build_wav(self, pcm: bytes) -> bytes:
        """Return a full WAV byte string: header + chime_in + pcm + chime_out."""
        body = self.chime_in + pcm + self.chime_out
        return wav_header(
            len(body),
            sample_rate=self.sample_rate,
            channels=self.channels,
            sample_width=self.sample_width,
        ) + body

    def pcm_duration_seconds(self, pcm: bytes) -> float:
        return len(pcm) / (self.sample_rate * self.sample_width * self.channels)

    def total_duration_seconds(self, pcm: bytes) -> float:
        return self.pcm_duration_seconds(self.chime_in + pcm + self.chime_out)
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_chimes.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/chimes.py tests/test_chimes.py
git commit -m "feat(chimes): generate pre/post chimes and build WAV"
```

---

## Task 7: Wire chimes into handle_intercom

**Files:**
- Modify: `intercom-addon/intercom.py`
- Modify: `tests/test_picker.py` (integration assertions)

- [ ] **Step 1: Write failing test**

Append to `tests/test_picker.py`:

```python
async def test_intercom_wav_includes_chimes(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    import struct
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": [],
    }))
    client = await aiohttp_client(lan_app)
    pcm = b"\xAA\xBB" * 100  # 200 bytes
    sid = str(uuid.uuid4())
    await client.post(
        "/intercom", data=pcm,
        headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
    )

    wav_files = list(www_dir.glob("intercom-*.wav"))
    assert len(wav_files) == 1
    wav = wav_files[0].read_bytes()
    pcm_len = struct.unpack_from("<I", wav, 40)[0]
    # Chime is 120ms at 16k/16/1 = 3840 bytes each side.
    # Total PCM = 3840 + 200 + 3840 = 7880.
    assert pcm_len == 7880
    assert wav[44 + 3840:44 + 3840 + 200] == pcm
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_picker.py::test_intercom_wav_includes_chimes -v`
Expected: fail (current handler writes header + raw pcm, no chimes).

- [ ] **Step 3: Update intercom.py**

In `intercom-addon/intercom.py`:

Remove the existing top-level `wav_header()` function and the globals `sample_rate`, `sample_width`, `channels` — they live in `chimes.ChimeMixer` now.

Add near the top of the file (after `import players`):

```python
from chimes import ChimeMixer

# Initialized at module load with the addon's default audio format
# (16 kHz, 16-bit mono). _run() reconstructs this if options.json overrides
# any of the format fields. Module-level instance so tests can call handlers
# without going through _run().
mixer = ChimeMixer(sample_rate=16000, sample_width=2, channels=1)
```

In `handle_intercom`, replace the WAV-writing block:

```python
    duration = len(pcm) / (sample_rate * sample_width * channels)
    log.info("received  session=%s  source=%s  pcm=%d bytes  duration=%.1fs",
             session_id[:8], source, len(pcm), duration)
```

through:

```python
    with open(filepath, "wb") as f:
        f.write(wav_header(len(pcm)))
        f.write(pcm)
    log.info("WAV written  %s  (%d Hz, %d-bit, %dch, %.2fs)",
             filepath, sample_rate, sample_width * 8, channels, duration)
```

with:

```python
    duration = mixer.pcm_duration_seconds(pcm)
    log.info("received  session=%s  source=%s  pcm=%d bytes  duration=%.1fs",
             session_id[:8], source, len(pcm), duration)
```

(routing logic stays put, then later:)

```python
    filename = f"intercom-{session_id}.wav"
    filepath = Path(CONFIG_WWW) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(mixer.build_wav(pcm))
    log.info("WAV written  %s  (%.2fs incl. chimes)",
             filepath, mixer.total_duration_seconds(pcm))
```

Update the cleanup scheduling at the bottom of `handle_intercom`:

```python
    asyncio.create_task(_delete_after(filepath, mixer.total_duration_seconds(pcm) + 10))
```

In `_run()`, after reading options, rebuild the mixer if config differs from defaults:

```python
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

    # ... (rest unchanged)
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/ -v`
Expected: all pass, including the new chime-integration test.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): prepend/append chimes to every broadcast"
```

---

## Task 8: Ducker module

**Files:**
- Create: `intercom-addon/ducking.py`
- Create: `tests/test_ducking.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ducking.py`:

```python
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
from ducking import Ducker  # noqa: E402


@pytest.fixture
def fake_ha():
    ha = AsyncMock()
    ha.get_state = AsyncMock()
    ha.pause = AsyncMock()
    ha.play = AsyncMock()
    return ha


async def test_pauses_playing_target(fake_ha):
    fake_ha.get_state.return_value = {
        "state": "playing",
        "attributes": {"volume_level": 0.5},
    }
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    fake_ha.pause.assert_awaited_once_with("media_player.x")


async def test_does_not_pause_idle_target(fake_ha):
    fake_ha.get_state.return_value = {"state": "idle", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    fake_ha.pause.assert_not_called()


async def test_restore_resumes_playing(fake_ha):
    fake_ha.get_state.return_value = {
        "state": "playing",
        "attributes": {"volume_level": 0.5},
    }
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    await d.restore("media_player.x")
    fake_ha.play.assert_awaited_once_with("media_player.x")


async def test_restore_idle_is_noop(fake_ha):
    fake_ha.get_state.return_value = {"state": "idle", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    await d.restore("media_player.x")
    fake_ha.play.assert_not_called()


async def test_concurrent_snapshot_skips_second(fake_ha):
    fake_ha.get_state.return_value = {"state": "playing", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    await d.snapshot_and_pause(["media_player.x"])
    # get_state called once, pause called once
    assert fake_ha.get_state.await_count == 1
    assert fake_ha.pause.await_count == 1


async def test_restore_only_fires_after_last_extend(fake_ha):
    fake_ha.get_state.return_value = {"state": "playing", "attributes": {}}
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.x"])
    # Second broadcast extends — restore should still happen exactly once.
    await d.snapshot_and_pause(["media_player.x"])
    await d.restore("media_player.x")
    # After one restore, the snapshot is cleared
    assert fake_ha.play.await_count == 1
    # A second restore call (orphan) is a no-op
    await d.restore("media_player.x")
    assert fake_ha.play.await_count == 1


async def test_get_state_error_is_treated_as_idle(fake_ha):
    fake_ha.get_state.side_effect = RuntimeError("404")
    d = Ducker(fake_ha)
    # Should not raise; logs + treats as idle
    await d.snapshot_and_pause(["media_player.x"])
    fake_ha.pause.assert_not_called()
    await d.restore("media_player.x")
    fake_ha.play.assert_not_called()


async def test_pause_error_does_not_block_other_targets(fake_ha):
    fake_ha.get_state.return_value = {"state": "playing", "attributes": {}}
    fake_ha.pause.side_effect = [RuntimeError("offline"), None]
    d = Ducker(fake_ha)
    await d.snapshot_and_pause(["media_player.broken", "media_player.ok"])
    assert fake_ha.pause.await_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ducking.py -v`
Expected: ImportError.

- [ ] **Step 3: Write the minimal implementation**

Create `intercom-addon/ducking.py`:

```python
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class Snapshot:
    state: str
    volume_level: Optional[float]


class Ducker:
    """Snapshots target media_player state, pauses playing ones for the
    duration of a broadcast, and restores them.

    Concurrent broadcasts to the same target: keep the FIRST snapshot;
    later calls are no-ops. restore() consumes the snapshot, so an
    overlap-then-restore cycle still fires exactly once.
    """

    def __init__(self, ha):
        self._ha = ha
        self._snapshots: dict[str, Snapshot] = {}

    async def snapshot_and_pause(self, targets: list[str]) -> None:
        for target in targets:
            if target in self._snapshots:
                continue  # debounce — earlier broadcast still active
            snap = await self._snapshot(target)
            self._snapshots[target] = snap
            if snap.state == "playing":
                try:
                    await self._ha.pause(target)
                    log.info("ducking   %s  state=%s  → paused",
                             target, snap.state)
                except Exception as e:
                    log.warning("ducking pause failed for %s: %s", target, e)
            else:
                log.info("ducking   %s  state=%s  → no-op", target, snap.state)

    async def _snapshot(self, target: str) -> Snapshot:
        try:
            data = await self._ha.get_state(target)
        except Exception as e:
            log.warning("ducking snapshot failed for %s: %s", target, e)
            return Snapshot(state="idle", volume_level=None)
        return Snapshot(
            state=data.get("state", "idle"),
            volume_level=(data.get("attributes") or {}).get("volume_level"),
        )

    async def restore(self, target: str) -> None:
        snap = self._snapshots.pop(target, None)
        if snap is None:
            return  # already restored or never snapshotted
        if snap.state == "playing":
            try:
                await self._ha.play(target)
                log.info("restored  %s  state=playing", target)
            except Exception as e:
                log.warning("ducking restore failed for %s: %s", target, e)
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_ducking.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/ducking.py tests/test_ducking.py
git commit -m "feat(ducking): snapshot/pause/restore with concurrency debounce"
```

---

## Task 9: Wire ducking into handle_intercom

**Files:**
- Modify: `intercom-addon/intercom.py`
- Modify: `tests/test_picker.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_picker.py`:

```python
Make sure `tests/test_picker.py` imports `AsyncMock` at the top:

```python
from unittest.mock import AsyncMock, patch
```

Then append:

```python
async def test_intercom_pauses_playing_target_then_resumes(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.kitchen"]},
        "default": [],
    }))
    # Configure the target as playing (overrides the fake_ha default of idle).
    fake_ha.get_state.return_value = {
        "state": "playing", "attributes": {"volume_level": 0.4},
    }

    client = await aiohttp_client(lan_app)
    pcm = b"\xAA\xBB" * 100
    sid = str(uuid.uuid4())
    await client.post(
        "/intercom", data=pcm,
        headers={"X-Session-ID": sid, "X-Device-Name": "src-a"},
    )

    # Pause should have fired
    fake_ha.pause.assert_awaited_once_with("media_player.kitchen")

    # Restore is scheduled — wait long enough for it.
    # Total duration = 200B PCM + 7680B chimes = 7880B at 16k/16/1 = 0.246s
    # Plus the 1.5s slack — so wait ~2s.
    import asyncio as _asyncio
    await _asyncio.sleep(2.0)
    fake_ha.play.assert_awaited_once_with("media_player.kitchen")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_picker.py::test_intercom_pauses_playing_target_then_resumes -v`
Expected: fail (no pause/play calls in current handler).

- [ ] **Step 3: Update intercom.py**

In `intercom-addon/intercom.py`:

Add to top imports:

```python
from ducking import Ducker
```

Add a module-level instance (after `ha = HAClient()` and `mixer:`):

```python
ducker = Ducker(ha)
```

Update `fake_ha` fixture in `tests/test_picker.py` to also expose the ducker's HA client (it's the same `ha` instance, so adding `monkeypatch.setattr(srv.ha, ...)` to stub `get_state`, `pause`, `play` already works). But since the test patches via `monkeypatch.setattr(srv.ha, ...)` and `ducker` was constructed with that same `srv.ha`, the patched methods are picked up automatically. **No change needed** to the existing fixture.

In `handle_intercom`, between `filepath.write_bytes(...)` and the play_media loop:

```python
    if targets:
        await ducker.snapshot_and_pause(targets)
```

After the play_media loop, schedule the restore:

```python
    total_duration = mixer.total_duration_seconds(pcm)
    asyncio.create_task(_restore_after(targets, total_duration + 1.5))
    asyncio.create_task(_delete_after(filepath, total_duration + 10))
    return web.Response(status=204)
```

Add a helper near `_delete_after`:

```python
async def _restore_after(targets: list[str], delay: float) -> None:
    await asyncio.sleep(delay)
    for target in targets:
        await ducker.restore(target)
```

- [ ] **Step 4: Extend fake_ha fixture in test_picker.py**

The existing `fake_ha` fixture stubs `get_states` and `play_media`. Add `get_state`, `pause`, `play` so all the new integration tests work without each one configuring them:

```python
@pytest.fixture
def fake_ha(monkeypatch):
    from unittest.mock import AsyncMock
    monkeypatch.setattr(srv.ha, "get_states", AsyncMock(return_value=[]))
    monkeypatch.setattr(srv.ha, "play_media", AsyncMock(return_value=204))
    monkeypatch.setattr(srv.ha, "get_state", AsyncMock(return_value={"state": "idle", "attributes": {}}))
    monkeypatch.setattr(srv.ha, "pause", AsyncMock(return_value=200))
    monkeypatch.setattr(srv.ha, "play", AsyncMock(return_value=200))
    return srv.ha
```

- [ ] **Step 5: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): duck targets before broadcast, restore after"
```

---

## Task 10: Talkback module

**Files:**
- Create: `intercom-addon/talkback.py`
- Create: `tests/test_talkback.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_talkback.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
from talkback import TalkbackWindows  # noqa: E402


def make(now=0.0):
    """Build a TalkbackWindows with a controllable clock."""
    tw = TalkbackWindows(now_func=lambda: tw.t)
    tw.t = now
    return tw


def test_no_window_active_initially():
    tw = make()
    assert tw.reply_target("A") is None


def test_record_then_reply_within_window():
    tw = make(now=0)
    # A broadcasts; B is a target whose selves[B] is its own player
    selves = {"A": "media_player.a", "B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    # B now has a window pointing back to A
    assert tw.reply_target("B") == "media_player.a"


def test_no_window_when_target_has_no_selves_entry():
    tw = make(now=0)
    selves = {"A": "media_player.a"}  # no B
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") is None


def test_window_not_consumed_on_use():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") == "media_player.a"
    assert tw.reply_target("B") == "media_player.a"  # still there


def test_window_expires_after_30s():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    tw.t = 31
    assert tw.reply_target("B") is None


def test_new_broadcast_resets_window_to_latest_sender():
    tw = make(now=0)
    selves = {
        "A": "media_player.a",
        "B": "media_player.b",
        "C": "media_player.c",
    }
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    tw.t = 10
    tw.record_broadcast(source="C", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") == "media_player.c"


def test_reply_target_unknown_sender_returns_none():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    # Sender has no selves entry — window points to a nonexistent self_player
    selves_no_a = {"B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves_no_a)
    assert tw.reply_target("B") is None


def test_pingpong_A_to_B_then_B_to_A():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    # A → B
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") == "media_player.a"
    # B replies → A (via media_player.a)
    tw.t = 5
    tw.record_broadcast(source="B", targets=["media_player.a"], selves=selves)
    # Now A has a window back to B
    assert tw.reply_target("A") == "media_player.b"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_talkback.py -v`
Expected: ImportError.

- [ ] **Step 3: Write the minimal implementation**

Create `intercom-addon/talkback.py`:

```python
import logging
import time
from typing import Callable, Optional

log = logging.getLogger(__name__)

WINDOW_SECONDS = 30


class TalkbackWindows:
    """Per-receiver short-lived state pointing back at the last sender's
    self-player.

    record_broadcast() opens windows for every target whose entity_id appears
    in the inverted `selves` map (i.e., the target IS a known source).
    reply_target() returns the sender's self-player if the receiver's window
    is still active. Windows are NOT consumed on use — only expire by time
    or are overwritten by a newer broadcast.
    """

    def __init__(self, now_func: Callable[[], float] = time.monotonic):
        self._now = now_func
        # device_name -> (sender_self_player_entity, expires_at_monotonic)
        self._windows: dict[str, tuple[str, float]] = {}

    def record_broadcast(
        self,
        source: str,
        targets: list[str],
        selves: dict[str, str],
    ) -> None:
        """For each target media_player that maps back to a known source,
        open a 30s reply window pointing at `selves[source]`."""
        sender_self = selves.get(source)
        if not sender_self:
            return  # sender has no self-player; replies impossible
        target_to_source = {v: k for k, v in selves.items()}
        expires = self._now() + WINDOW_SECONDS
        for tgt in targets:
            receiver = target_to_source.get(tgt)
            if receiver is None:
                continue  # not a source; no upload path
            self._windows[receiver] = (sender_self, expires)
            log.info(
                "talkback  %s reply-window → %s  (expires in %.0fs)",
                receiver, sender_self, WINDOW_SECONDS,
            )

    def reply_target(self, device: str) -> Optional[str]:
        """Return the sender's self-player entity_id if `device` has an
        active reply window; None otherwise."""
        entry = self._windows.get(device)
        if entry is None:
            return None
        target, expires_at = entry
        if self._now() >= expires_at:
            self._windows.pop(device, None)
            return None
        return target
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_talkback.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/talkback.py tests/test_talkback.py
git commit -m "feat(talkback): 30s reply windows pointing at sender self-player"
```

---

## Task 11: Wire talkback into handle_intercom

**Files:**
- Modify: `intercom-addon/intercom.py`
- Modify: `tests/test_picker.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_picker.py`:

```python
async def test_talkback_routes_to_sender_self_not_normal_route(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    # Setup: kitchen-echo's broadcast targets living-echo's self_player,
    # so a reply window opens for living-echo. living-echo's normal route
    # is something different (media_player.bedroom). Talkback should win.
    players_file.write_text(json.dumps({
        "routes": {
            "kitchen-echo": ["media_player.living_speaker"],
            "living-echo":  ["media_player.bedroom"],
        },
        "default": [],
        "aliases": {},
        "selves": {
            "kitchen-echo": "media_player.kitchen_speaker",
            "living-echo":  "media_player.living_speaker",
        },
    }))
    client = await aiohttp_client(lan_app)

    # kitchen-echo broadcasts → living-echo's self_player plays
    # AND living-echo's reply window opens pointing back at kitchen's self
    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": str(uuid.uuid4()), "X-Device-Name": "kitchen-echo"},
    )

    fake_ha.play_media.reset_mock()
    # living-echo replies within 30 s → reply route, NOT routes["living-echo"]
    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": str(uuid.uuid4()), "X-Device-Name": "living-echo"},
    )
    called_entities = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert called_entities == ["media_player.kitchen_speaker"]


async def test_no_talkback_window_uses_normal_route(
    aiohttp_client, lan_app, players_file, www_dir, fake_options, fake_ha,
):
    players_file.write_text(json.dumps({
        "routes": {"src-a": ["media_player.normal"]},
        "default": [],
        "aliases": {},
        "selves": {},
    }))
    client = await aiohttp_client(lan_app)
    await client.post(
        "/intercom", data=b"\x00" * 64,
        headers={"X-Session-ID": str(uuid.uuid4()), "X-Device-Name": "src-a"},
    )
    called_entities = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert called_entities == ["media_player.normal"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_picker.py::test_talkback_routes_to_sender_self_not_normal_route -v`
Expected: fail (talkback not wired yet).

- [ ] **Step 3: Update intercom.py**

In `intercom-addon/intercom.py`:

Add to top imports:

```python
from talkback import TalkbackWindows
```

Add a module-level instance:

```python
talkback = TalkbackWindows()
```

Add a reset fixture to `tests/test_picker.py` so window state doesn't leak between tests (place near the top, near `fake_ha`):

```python
@pytest.fixture(autouse=True)
def _reset_talkback():
    srv.talkback._windows.clear()
    yield
    srv.talkback._windows.clear()
```

Also reset ducker snapshots so concurrent-broadcast debounce state doesn't leak:

```python
@pytest.fixture(autouse=True)
def _reset_ducker():
    srv.ducker._snapshots.clear()
    yield
    srv.ducker._snapshots.clear()
```

Replace the routing block in `handle_intercom`:

```python
    players = load_players()
    if source in players["routes"]:
        targets = players["routes"][source]
    else:
        players["routes"][source] = []
        save_players(players)
        log.info("enrolled new source=%s; using default targets", source)
        targets = players["default"]
```

with:

```python
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
```

After resolving targets and BEFORE play_media (or anywhere before the function returns 204 with no targets), open windows for receivers:

```python
    # Open reply windows for any receiver that is itself a known source.
    talkback.record_broadcast(
        source=source,
        targets=targets,
        selves=state["selves"],
    )
```

(Place this right before the `if not targets:` early-return block, so it runs even when the broadcast had a real target list.)

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(intercom): wire 30s talkback windows into routing"
```

---

## Task 12: Firmware — recorder.h with HOLD and VAD modes

**Files:**
- Modify: `recorder.h`

- [ ] **Step 1: Replace recorder.h**

Replace the entire file `recorder.h` with:

```cpp
#pragma once
#include <cstdint>
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/stream_buffer.h"

static const char*  REC_TAG   = "recorder";
static const size_t RBUF_SIZE = 32 * 1024;  // ~1 s at 16 kHz 16-bit

// VAD tuning (compile-time constants in v1)
static const uint32_t VAD_MIN_MS         = 1000;
static const uint32_t VAD_SILENCE_MS     = 1200;
static const uint32_t VAD_MAX_MS         = 15000;
static const uint32_t VAD_RMS_THRESHOLD  = 600;

enum rec_mode_t { REC_HOLD, REC_VAD };

static StreamBufferHandle_t _sbuf       = nullptr;
static volatile bool        _rec_active = false;
static volatile bool        _rec_done   = false;
static rec_mode_t           _mode       = REC_HOLD;
static uint64_t             _start_us   = 0;
static uint64_t             _last_loud_us = 0;

static inline uint64_t _now_us() { return esp_timer_get_time(); }

void recorder_init() {
  _sbuf = xStreamBufferCreate(RBUF_SIZE, 1);
  if (!_sbuf) ESP_LOGE(REC_TAG, "stream buffer alloc failed");
  else        ESP_LOGI(REC_TAG, "ready (%u KB ring buffer)", (unsigned)(RBUF_SIZE / 1024));
}

static void _start_common(rec_mode_t mode) {
  if (!_sbuf) return;
  xStreamBufferReset(_sbuf);
  _mode = mode;
  _start_us = _now_us();
  _last_loud_us = _start_us;
  _rec_done   = false;
  _rec_active = true;
  ESP_LOGI(REC_TAG, "recording started (mode=%s)",
           mode == REC_HOLD ? "HOLD" : "VAD");
}

void recorder_start() {
  _start_common(REC_HOLD);
}

void recorder_start_vad() {
  _start_common(REC_VAD);
}

static uint16_t _rms_int16(const uint8_t* data, size_t len) {
  if (len < 2) return 0;
  uint64_t sumsq = 0;
  size_t   n     = len / 2;
  const int16_t* s = reinterpret_cast<const int16_t*>(data);
  for (size_t i = 0; i < n; i++) {
    int32_t v = s[i];
    sumsq += static_cast<uint64_t>(v * v);
  }
  // sqrt of mean
  uint64_t mean = sumsq / n;
  // Integer sqrt (Newton)
  uint64_t r = mean;
  for (int j = 0; j < 8 && r > 0; j++) r = (r + mean / r) / 2;
  return static_cast<uint16_t>(r > 0xFFFF ? 0xFFFF : r);
}

void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_sbuf) return;
  size_t sent = xStreamBufferSend(_sbuf, data, len, 0);
  if (sent < len)
    ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(len - sent));

  if (_mode == REC_VAD) {
    uint64_t now = _now_us();
    uint64_t elapsed_ms = (now - _start_us) / 1000;
    if (_rms_int16(data, len) >= VAD_RMS_THRESHOLD) {
      _last_loud_us = now;
    }
    uint64_t silence_ms = (now - _last_loud_us) / 1000;
    if (elapsed_ms >= VAD_MIN_MS && silence_ms >= VAD_SILENCE_MS) {
      _rec_active = false;
      _rec_done   = true;
      ESP_LOGI(REC_TAG, "VAD stop (silence %llums)", (unsigned long long)silence_ms);
    } else if (elapsed_ms >= VAD_MAX_MS) {
      _rec_active = false;
      _rec_done   = true;
      ESP_LOGI(REC_TAG, "VAD hard cap (%llums)", (unsigned long long)elapsed_ms);
    }
  }
}

void recorder_stop() {
  _rec_active = false;
  _rec_done   = true;
  ESP_LOGI(REC_TAG, "recording stopped");
}

size_t recorder_drain(uint8_t* dst, size_t max_len, uint32_t wait_ms) {
  return xStreamBufferReceive(_sbuf, dst, max_len, pdMS_TO_TICKS(wait_ms));
}

bool recorder_is_active() { return _rec_active; }
bool recorder_is_done()   { return _rec_done && xStreamBufferIsEmpty(_sbuf); }
```

- [ ] **Step 2: Compile check**

Run: `esphome compile atom-echo.yaml`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add recorder.h
git commit -m "feat(recorder): add VAD mode with RMS silence detector"
```

---

## Task 13: Firmware — always-on mic

**Files:**
- Modify: `atom-echo.yaml`

- [ ] **Step 1: Update on_boot to capture the mic immediately**

In `atom-echo.yaml`, change the `esphome:` section. Find:

```yaml
esphome:
  name: ${name}
  friendly_name: ${friendly_name}
  name_add_mac_suffix: true
  includes:
    - recorder.h
    - uploader.h
  on_boot:
    - priority: 600.0
      then:
        - lambda: recorder_init();
    - priority: 200.0
      then:
        - lambda: |-
            id(atom_mic).add_data_callback([](const std::vector<uint8_t>& data) {
              recorder_on_data(data.data(), data.size());
            });
```

Replace the `priority: 200.0` block with:

```yaml
    - priority: 200.0
      then:
        - lambda: |-
            id(atom_mic).add_data_callback([](const std::vector<uint8_t>& data) {
              recorder_on_data(data.data(), data.size());
            });
        - microphone.capture: atom_mic
```

- [ ] **Step 2: Drop mic start/stop from button handlers**

In the same file, find `binary_sensor:`. In the `on_press` block, the existing code is:

```yaml
            - lambda: |-
                recorder_start();
                id(atom_mic).start();
                uploader_start("http://homeassistant.local:9999/intercom", App.get_name().c_str());
```

Remove the `id(atom_mic).start();` line:

```yaml
            - lambda: |-
                recorder_start();
                uploader_start("http://homeassistant.local:9999/intercom", App.get_name().c_str());
```

In `on_release`, the existing block is:

```yaml
    on_release:
      - delay: 2s
      - lambda: |-
          id(atom_mic).stop();
          recorder_stop();
```

Remove the mic stop (keep the delay — it was added intentionally to let the trailing audio drain before stopping the mic; since the mic is now always-on, the delay still serves the recorder's drain):

```yaml
    on_release:
      - delay: 2s
      - lambda: recorder_stop();
```

- [ ] **Step 3: Compile check**

Run: `esphome compile atom-echo.yaml`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add atom-echo.yaml
git commit -m "feat(atom-echo): keep mic always-on for wake-word listening"
```

---

## Task 14: Firmware — micro_wake_word

**Files:**
- Modify: `atom-echo.yaml`

- [ ] **Step 1: Add micro_wake_word component**

In `atom-echo.yaml`, append after the existing `media_player:` block (and before `light:`):

```yaml
# ── Wake-word PTT alternative (always listening on atom_mic) ────────────────

micro_wake_word:
  models:
    - model: okay_nabu
  on_wake_word_detected:
    - if:
        condition:
          lambda: 'return uploader_is_uploading() || recorder_is_active();'
        then:
          - logger.log: "wake word ignored — already recording/uploading"
        else:
          - light.turn_on:
              id: status_led
              red: 0%
              green: 0%
              blue: 100%
          - lambda: |-
              recorder_start_vad();
              uploader_start("http://homeassistant.local:9999/intercom",
                             App.get_name().c_str());
          - wait_until:
              condition:
                lambda: 'return !uploader_is_uploading();'
              timeout: 20s
          - light.turn_off: status_led
```

- [ ] **Step 2: Compile check**

Run: `esphome compile atom-echo.yaml`
Expected: build succeeds. If the model name isn't recognized, swap to `hey_jarvis` or another prebuilt model from the ESPHome `micro_wake_word` docs.

- [ ] **Step 3: Commit**

```bash
git add atom-echo.yaml
git commit -m "feat(atom-echo): add micro_wake_word as PTT alternative"
```

---

## Final verification

- [ ] **Step 1: Full test sweep**

Run: `python3 -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 2: Firmware compile**

Run: `esphome compile atom-echo.yaml`
Expected: build succeeds.

- [ ] **Step 3: Manual smoke test matrix (firmware on real device)**

- [ ] Button PTT records and plays as before (regression)
- [ ] Wake-word starts a recording; goes silent → recording ends ~1.2 s later → plays
- [ ] Wake-word while uploading → ignored, log line emitted
- [ ] Button while wake-word recording → ignored
- [ ] VAD hard cap (15 s) fires when speaker keeps talking
- [ ] Mic always-on doesn't OOM or drop ("buffer full" warnings stay absent under normal use)
- [ ] Two-Echo scenario: kitchen-echo broadcasts → living-echo speaker plays with chimes. Within 30 s, press living-echo PTT → audio plays back on the kitchen speaker (not the living's normal routes).
- [ ] Picker UI: alias edit persists; self-player dropdown persists; default row has no alias/self field.
- [ ] Music playing on a target Sonos pauses for the broadcast, resumes after.
