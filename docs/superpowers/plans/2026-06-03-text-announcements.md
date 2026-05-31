# Text Announcements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user announce typed text (via the addon panel) or automation-triggered text (via an HTTP endpoint) as Piper TTS speech, chimed and ducked, on HA media players.

**Architecture:** A new announcement flow reuses the intercom addon's chime + duck + play + cleanup machinery. The addon fetches Piper audio from HA, mixes the existing chime at the audio's native sample rate, and plays one WAV through a `_play_on_targets()` helper extracted from `handle_intercom`. Two routes (`POST /announce` on the LAN server for automations, `POST /api/announce` on ingress for the UI) share one handler.

**Tech Stack:** Python 3 / aiohttp addon, stdlib `wave`, pytest (`asyncio_mode = auto`, `AsyncMock` HA stubs), vanilla-JS ingress UI, HA `rest_command`.

**Spec:** `docs/superpowers/specs/2026-06-03-text-announcements-design.md`

---

## File Structure

- `intercom-addon/ha_client.py` — **modify**: add `tts_get_audio()`.
- `intercom-addon/announce.py` — **create**: `parse_tts_wav()`, `build_announcement_wav()` (pure audio logic, no I/O).
- `intercom-addon/intercom.py` — **modify**: extract `_play_on_targets()`; add `handle_announce`; register routes; read `tts_engine`.
- `intercom-addon/config.yaml` — **modify**: add `tts_engine` option + schema; bump version.
- `intercom-addon/picker.html` — **modify**: add an "Announce" section.
- `docs/DEVICES.md` — **modify**: document the announce feature + `rest_command`.
- `tests/test_ha_client.py` — **modify**: tests for `tts_get_audio`.
- `tests/test_announce.py` — **create**: tests for the pure audio functions.
- `tests/test_picker.py` — **modify**: handler tests for `/announce` + intercom-refactor regression.

---

## Task 1: `HAClient.tts_get_audio`

**Files:**
- Modify: `intercom-addon/ha_client.py`
- Test: `tests/test_ha_client.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ha_client.py`:

```python
async def test_tts_get_audio_posts_then_fetches(env_token):
    post_resp = MagicMock(status=200)
    post_resp.json = AsyncMock(return_value={
        "url": "http://ha/api/tts_proxy/x.wav",
        "path": "/api/tts_proxy/x.wav",
    })
    get_resp = MagicMock(status=200)
    get_resp.read = AsyncMock(return_value=b"RIFFfakeaudio")
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=post_resp)
    fake_session.get = AsyncMock(return_value=get_resp)

    client = HAClient(session=fake_session)
    audio = await client.tts_get_audio("tts.piper", "hello there")

    assert audio == b"RIFFfakeaudio"
    post_url = fake_session.post.await_args.args[0]
    post_kwargs = fake_session.post.await_args.kwargs
    assert post_url == "http://supervisor/core/api/tts_get_url"
    assert post_kwargs["json"] == {"engine_id": "tts.piper", "message": "hello there"}
    assert post_kwargs["headers"]["Authorization"] == "Bearer tok"
    get_url = fake_session.get.await_args.args[0]
    assert get_url == "http://supervisor/core/api/tts_proxy/x.wav"


async def test_tts_get_audio_raises_when_get_url_fails(env_token):
    post_resp = MagicMock(status=500)
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=post_resp)
    client = HAClient(session=fake_session)
    with pytest.raises(RuntimeError):
        await client.tts_get_audio("tts.piper", "hi")


async def test_tts_get_audio_raises_on_missing_path(env_token):
    post_resp = MagicMock(status=200)
    post_resp.json = AsyncMock(return_value={"url": "http://ha/x.wav"})
    fake_session = MagicMock()
    fake_session.post = AsyncMock(return_value=post_resp)
    client = HAClient(session=fake_session)
    with pytest.raises(RuntimeError):
        await client.tts_get_audio("tts.piper", "hi")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/danillugovskoy/own/intercom && python -m pytest tests/test_ha_client.py -k tts_get_audio -v`
Expected: FAIL — `AttributeError: 'HAClient' object has no attribute 'tts_get_audio'`.

- [ ] **Step 3: Implement `tts_get_audio`**

Add this method to the `HAClient` class in `intercom-addon/ha_client.py` (e.g. after `play_media`):

```python
    async def tts_get_audio(self, engine_id: str, message: str) -> bytes:
        """Generate TTS via HA and return the raw audio bytes.

        POSTs /api/tts_get_url to make HA render the speech, then GETs the
        returned proxy path (kept on the internal supervisor proxy).
        """
        resp = await self.session.post(
            f"{HA_API}/tts_get_url",
            headers=self._auth_headers(),
            json={"engine_id": engine_id, "message": message},
        )
        if resp.status != 200:
            raise RuntimeError(f"tts_get_url returned {resp.status}")
        data = await resp.json()
        path = data.get("path")
        if not path:
            raise RuntimeError("tts_get_url response missing 'path'")
        audio_resp = await self.session.get(
            f"http://supervisor/core{path}", headers=self._auth_headers()
        )
        if audio_resp.status != 200:
            raise RuntimeError(f"tts audio fetch returned {audio_resp.status}")
        return await audio_resp.read()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ha_client.py -v`
Expected: PASS (all, including the existing ones).

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/ha_client.py tests/test_ha_client.py
git commit -m "feat(announce): HAClient.tts_get_audio fetches Piper speech bytes

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `announce.py` — WAV parse + chime mixing

**Files:**
- Create: `intercom-addon/announce.py`
- Test: `tests/test_announce.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_announce.py`:

```python
import io
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import announce  # noqa: E402


def _make_wav(pcm: bytes, rate: int = 22050, width: int = 2, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def test_parse_tts_wav_extracts_format_and_pcm():
    pcm = b"\x01\x02" * 50
    wav = _make_wav(pcm, rate=22050, width=2, channels=1)
    parsed = announce.parse_tts_wav(wav)
    assert parsed is not None
    out_pcm, rate, width, channels = parsed
    assert out_pcm == pcm
    assert (rate, width, channels) == (22050, 2, 1)


def test_parse_tts_wav_returns_none_for_non_wav():
    assert announce.parse_tts_wav(b"ID3\x03not an mp3 really") is None


def test_build_announcement_wav_mixes_chime_at_native_rate():
    pcm = b"\xAA\xBB" * 100  # 200 bytes
    wav_in = _make_wav(pcm, rate=22050, width=2, channels=1)
    out, ext, duration = announce.build_announcement_wav(wav_in)
    assert ext == "wav"
    # Output is a valid WAV whose PCM is chime + speech + chime (longer than speech).
    with wave.open(io.BytesIO(out), "rb") as w:
        assert w.getframerate() == 22050
        total_frames = w.getnframes()
    speech_frames = len(pcm) // 2
    assert total_frames > speech_frames
    assert duration > speech_frames / 22050


def test_build_announcement_wav_falls_back_for_non_wav():
    raw = b"ID3 this is actually mp3 bytes"
    out, ext, duration = announce.build_announcement_wav(raw)
    assert out == raw
    assert ext == "mp3"
    assert duration == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_announce.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'announce'`.

- [ ] **Step 3: Implement `announce.py`**

Create `intercom-addon/announce.py`:

```python
import io
import logging
import wave

from chimes import ChimeMixer

log = logging.getLogger(__name__)


def parse_tts_wav(audio: bytes):
    """Return (pcm, sample_rate, sample_width, channels), or None if the bytes
    are not a parseable PCM WAV (e.g. the engine returned mp3)."""
    try:
        with wave.open(io.BytesIO(audio), "rb") as w:
            channels = w.getnchannels()
            width = w.getsampwidth()
            rate = w.getframerate()
            pcm = w.readframes(w.getnframes())
    except (wave.Error, EOFError, ValueError):
        return None
    return pcm, rate, width, channels


def build_announcement_wav(audio: bytes):
    """Return (bytes, ext, duration_seconds).

    If the TTS audio is a 16-bit PCM WAV, build a chime+speech+chime WAV at the
    audio's native format (the chime is generated per-rate, so no resampling).
    Otherwise return the raw bytes with no chime (degraded fallback).
    """
    parsed = parse_tts_wav(audio)
    if parsed is None:
        log.warning("TTS audio not a parseable WAV; playing without chime")
        return audio, "mp3", 0.0
    pcm, rate, width, channels = parsed
    if width != 2:
        log.warning("TTS WAV is %d-bit, not 16-bit; playing without chime", width * 8)
        return audio, "wav", 0.0
    mixer = ChimeMixer(sample_rate=rate, sample_width=width, channels=channels)
    wav = mixer.build_wav(pcm)
    duration = mixer.total_duration_seconds(pcm)
    return wav, "wav", duration
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_announce.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/announce.py tests/test_announce.py
git commit -m "feat(announce): WAV parsing + native-rate chime mixing

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Extract `_play_on_targets()` from `handle_intercom`

This is a pure refactor — no behavior change. The existing intercom tests are the safety net.

**Files:**
- Modify: `intercom-addon/intercom.py:129-154`
- Test: `tests/test_picker.py` (existing intercom tests must still pass)

- [ ] **Step 1: Run the existing intercom tests (baseline, green)**

Run: `python -m pytest tests/test_picker.py -v`
Expected: PASS (this is the baseline; it must stay green after the refactor).

- [ ] **Step 2: Add the `_play_on_targets` helper**

In `intercom-addon/intercom.py`, add this function just above `_delete_after`:

```python
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
```

- [ ] **Step 3: Replace the tail of `handle_intercom`**

In `handle_intercom`, replace everything from `opts = load_options()` (currently line 129) through the final `return web.Response(status=204)` (line 154) with:

```python
    wav = mixer.build_wav(pcm)
    total_duration = mixer.total_duration_seconds(pcm)
    log.info("WAV built  %s  (%.2fs incl. chimes)", session_id[:8], total_duration)

    await _play_on_targets(
        wav, "wav", total_duration, targets, name=f"intercom-{session_id}"
    )
    return web.Response(status=204)
```

Leave everything above (session/source parsing, talkback, route resolution, `talkback.record_broadcast`) unchanged.

- [ ] **Step 4: Run the intercom tests to verify no regression**

Run: `python -m pytest tests/test_picker.py -v`
Expected: PASS — same set as the baseline, including `test_intercom_wav_includes_chimes` (still globs `intercom-*.wav`, PCM length 7880) and `test_intercom_known_source_with_empty_route_plays_nowhere` (no `play_media` calls).

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/intercom.py
git commit -m "refactor(intercom): extract _play_on_targets helper

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Announce handler + routes

**Files:**
- Modify: `intercom-addon/intercom.py` (add `handle_announce`; register on both apps)
- Test: `tests/test_picker.py`

- [ ] **Step 1: Write the failing handler tests**

Add to `tests/test_picker.py`. First extend the `fake_ha` fixture so it stubs `tts_get_audio` — change the fixture body (around line 24) to also include:

```python
    monkeypatch.setattr(srv.ha, "tts_get_audio", AsyncMock(return_value=b""))
```

(keep the existing stubs; just add this line before `return srv.ha`).

Then add this fixture and these tests at the end of the file:

```python
import io as _io
import wave as _wave


def _wav_bytes(pcm: bytes, rate: int = 22050) -> bytes:
    buf = _io.BytesIO()
    with _wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


@pytest.fixture
def announce_app():
    app = web.Application()
    app.router.add_post("/announce", srv.handle_announce)
    return app


async def test_announce_explicit_targets_plays_and_chimes(
    aiohttp_client, announce_app, www_dir, fake_options, fake_ha,
):
    fake_ha.tts_get_audio.return_value = _wav_bytes(b"\x01\x02" * 100)
    client = await aiohttp_client(announce_app)
    resp = await client.post("/announce", json={
        "text": "dinner is ready",
        "targets": ["media_player.kitchen", "media_player.bedroom"],
    })
    assert resp.status == 204
    fake_ha.tts_get_audio.assert_awaited_once()
    assert fake_ha.tts_get_audio.await_args.args == ("tts.piper", "dinner is ready")
    played = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert played == ["media_player.kitchen", "media_player.bedroom"]
    wav_files = list(www_dir.glob("announce-*.wav"))
    assert len(wav_files) == 1


async def test_announce_omitted_targets_uses_all_players(
    aiohttp_client, announce_app, www_dir, fake_options, fake_ha,
):
    fake_ha.tts_get_audio.return_value = _wav_bytes(b"\x01\x02" * 100)
    fake_ha.get_states.return_value = [
        {"entity_id": "media_player.kitchen", "attributes": {}},
        {"entity_id": "light.bulb", "attributes": {}},
        {"entity_id": "media_player.bedroom", "attributes": {}},
    ]
    client = await aiohttp_client(announce_app)
    resp = await client.post("/announce", json={"text": "hello house"})
    assert resp.status == 204
    played = [c.args[0] for c in fake_ha.play_media.call_args_list]
    assert played == ["media_player.kitchen", "media_player.bedroom"]


async def test_announce_empty_text_returns_400(
    aiohttp_client, announce_app, www_dir, fake_options, fake_ha,
):
    client = await aiohttp_client(announce_app)
    resp = await client.post("/announce", json={"text": "  "})
    assert resp.status == 400
    assert fake_ha.tts_get_audio.call_args_list == []


async def test_announce_bad_targets_returns_400(
    aiohttp_client, announce_app, www_dir, fake_options, fake_ha,
):
    client = await aiohttp_client(announce_app)
    resp = await client.post("/announce", json={
        "text": "hi", "targets": ["light.bulb"],
    })
    assert resp.status == 400


async def test_announce_tts_failure_returns_502(
    aiohttp_client, announce_app, www_dir, fake_options, fake_ha,
):
    fake_ha.tts_get_audio.side_effect = RuntimeError("piper down")
    client = await aiohttp_client(announce_app)
    resp = await client.post("/announce", json={
        "text": "hi", "targets": ["media_player.kitchen"],
    })
    assert resp.status == 502


async def test_announce_non_wav_tts_plays_without_chime(
    aiohttp_client, announce_app, www_dir, fake_options, fake_ha,
):
    fake_ha.tts_get_audio.return_value = b"ID3 mp3 bytes here"
    client = await aiohttp_client(announce_app)
    resp = await client.post("/announce", json={
        "text": "hi", "targets": ["media_player.kitchen"],
    })
    assert resp.status == 204
    assert list(www_dir.glob("announce-*.mp3")) != []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_picker.py -k announce -v`
Expected: FAIL — `AttributeError: module 'intercom' has no attribute 'handle_announce'`.

- [ ] **Step 3: Implement `handle_announce` and register routes**

In `intercom-addon/intercom.py`, add `import announce` near the other addon imports (after `import players`).

Add the handler (e.g. just below `handle_intercom`):

```python
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
```

Then register it on both apps. In `make_lan_app`, add after the `/intercom` route:

```python
    app.router.add_post("/announce", handle_announce)
```

In `make_ingress_app`, add after the `/api/players` POST route:

```python
    app.router.add_post("/api/announce", handle_announce)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_picker.py -v`
Expected: PASS — all announce tests plus the unchanged intercom/picker tests.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS (all files).

- [ ] **Step 6: Commit**

```bash
git add intercom-addon/intercom.py tests/test_picker.py
git commit -m "feat(announce): /announce + /api/announce handler

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Config — `tts_engine` option

**Files:**
- Modify: `intercom-addon/config.yaml`

- [ ] **Step 1: Add the option, schema entry, and bump version**

In `intercom-addon/config.yaml`:

Under `options:` add a line:

```yaml
  tts_engine: "tts.piper"
```

Under `schema:` add a line:

```yaml
  tts_engine: str
```

Bump `version` from `"3.0.3"` to `"3.1.0"` (new feature).

- [ ] **Step 2: Log the configured engine on startup (optional clarity)**

In `intercom-addon/intercom.py` `_run()`, after the existing `log.info("audio format: ...")` line, add:

```python
    log.info("tts engine: %s", opts.get("tts_engine", "tts.piper"))
```

- [ ] **Step 3: Verify config parses**

Run: `python -c "import yaml; print(yaml.safe_load(open('intercom-addon/config.yaml'))['options']['tts_engine'])"`
Expected: prints `tts.piper`.

- [ ] **Step 4: Commit**

```bash
git add intercom-addon/config.yaml intercom-addon/intercom.py
git commit -m "feat(announce): configurable tts_engine option (default tts.piper)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: UI — Announce section in `picker.html`

There is no JS test harness in this repo; verification is a manual render check. Keep the JS in the same vanilla style as the rest of the file (no frameworks).

**Files:**
- Modify: `intercom-addon/picker.html`

- [ ] **Step 1: Add the Announce markup**

In `picker.html`, just after `<h1>Intercom Routes</h1>` and before `<div id="status"></div>`, insert:

```html
<section id="announce" style="margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 2px solid #eee;">
  <h2 style="margin: 0 0 0.5rem;">Announce</h2>
  <textarea id="ann-text" rows="2" placeholder="Type a message to speak…"
            style="width: 100%; box-sizing: border-box; font-size: 1rem; padding: 0.5rem;"></textarea>
  <div class="chips" id="ann-chips"></div>
  <select id="ann-add"><option value="">+ add speaker…</option></select>
  <span class="hint" id="ann-allhint"> (no speakers = announce on all)</span>
  <div style="margin-top: 0.6rem;">
    <button class="save" id="ann-send">Announce</button>
    <span id="ann-toast" class="toast"></span>
  </div>
</section>
```

- [ ] **Step 2: Add the Announce JS**

In the `<script>` block, just before the final `load();` call, insert:

```javascript
let annTargets = [];

function renderAnnounce() {
  const chips = $("ann-chips");
  chips.innerHTML = "";
  for (const eid of annTargets) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = friendlyName(eid) + " ";
    const x = document.createElement("button");
    x.textContent = "×";
    x.title = eid;
    x.addEventListener("click", () => {
      annTargets = annTargets.filter((e) => e !== eid);
      renderAnnounce();
    });
    chip.appendChild(x);
    chips.appendChild(chip);
  }
  const sel = $("ann-add");
  sel.innerHTML = '<option value="">+ add speaker…</option>';
  for (const tgt of state.available) {
    if (annTargets.includes(tgt.entity_id)) continue;
    const opt = document.createElement("option");
    opt.value = tgt.entity_id;
    opt.textContent = tgt.friendly_name + "  (" + tgt.entity_id + ")";
    sel.appendChild(opt);
  }
}

$("ann-add").addEventListener("change", (e) => {
  if (!e.target.value) return;
  annTargets.push(e.target.value);
  renderAnnounce();
});

$("ann-send").addEventListener("click", async () => {
  const text = $("ann-text").value.trim();
  $("ann-toast").textContent = "";
  if (!text) {
    $("ann-toast").innerHTML = '<span class="error">Enter a message first</span>';
    return;
  }
  try {
    const resp = await fetch("./api/announce", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text, targets: annTargets}),
    });
    if (!resp.ok) {
      const b = await resp.json().catch(() => ({}));
      throw new Error("HTTP " + resp.status + (b.error ? ": " + b.error : ""));
    }
    $("ann-toast").textContent = "Announced";
    $("ann-text").value = "";
    setTimeout(() => { $("ann-toast").textContent = ""; }, 2000);
  } catch (e) {
    $("ann-toast").innerHTML = '<span class="error">Failed: ' + e + '</span>';
  }
});
```

- [ ] **Step 3: Call `renderAnnounce()` once players are loaded**

In the `render()` function, add `renderAnnounce();` as its last line (so the speaker dropdown populates after `load()` fetches `state.available`).

- [ ] **Step 4: Manual verification**

Open the addon's Intercom panel in HA (or load `picker.html` against a running addon). Expected: an "Announce" box at the top with a textarea, a "+ add speaker…" dropdown listing the same players as the routes section, removable chips, and an "Announce" button that POSTs and shows an "Announced" toast. Empty text shows an inline error.

- [ ] **Step 5: Commit**

```bash
git add intercom-addon/picker.html
git commit -m "feat(announce): Announce text box in the picker UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Docs — `DEVICES.md`

**Files:**
- Modify: `docs/DEVICES.md`

- [ ] **Step 1: Add an Announcements section**

Append a new section to `docs/DEVICES.md` (after the Capabilities table or at the end):

````markdown
## Announcements (text-to-speech)

Type a message in the **Intercom** addon panel (the "Announce" box) or trigger
one from a Home Assistant automation. The addon renders the text with Piper TTS,
prefixes/suffixes the intercom chime, ducks any playing media on the targets,
and plays it — the same path the PTT intercom uses.

- TTS engine is configurable via the addon's `tts_engine` option (default
  `tts.piper`).
- From the UI you pick the target players each time. If you trigger via the API
  and omit `targets`, the announcement plays on **every** `media_player` in HA.

### Trigger from an automation

Define a `rest_command` once (in `configuration.yaml`), pointing at the same
host/port the devices already use for the intercom:

```yaml
rest_command:
  intercom_announce:
    url: "http://homeassistant.local:9999/announce"
    method: POST
    content_type: "application/json"
    payload: >
      {"text": "{{ text }}",
       "targets": {{ targets | tojson }}}
```

Then call it from any automation (omit `targets` to hit all players):

```yaml
- action: rest_command.intercom_announce
  data:
    text: "Someone is at the front door"
    targets:
      - media_player.atom_echo_player
      - media_player.intercom_s3_player
```
````

Also add a row to the **Capabilities** table:

```markdown
| Text announcements (UI + automation TTS) | ✓ | ✓ |
```

- [ ] **Step 2: Verify the doc**

Run: `git diff docs/DEVICES.md`
Expected: the new Announcements section + capabilities row; the `rest_command` URL matches `http://homeassistant.local:9999` (the same host the devices POST `/intercom` to).

- [ ] **Step 3: Commit**

```bash
git add docs/DEVICES.md
git commit -m "docs(announce): document text announcements + rest_command

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Acceptance criteria (from spec)

1. ✅ Announce by UI text box AND HTTP API — Tasks 4, 6.
2. ✅ Speech via Piper, configurable engine — Tasks 1, 5.
3. ✅ Manual targets picked each time; API targets optional → all players — Tasks 4, 6.
4. ✅ Chime reused (mixed at native rate) — Task 2.
5. ✅ Ducking reused via shared `_play_on_targets` — Task 3, 4.
6. ✅ Non-WAV TTS degrades to no-chime playback, not a failure — Tasks 2, 4.
7. ✅ Automation trigger documented via `rest_command` — Task 7.
8. ✅ No firmware/ESPHome change (`devices/*.yaml` untouched).
