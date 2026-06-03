# Text Announcements — Design

**Date:** 2026-06-03
**Status:** Approved (design)

## Goal

Let the user announce arbitrary text on their HA media players — either by
typing it into the addon's panel, or by triggering it from a Home Assistant
automation. The text is spoken by HA's Piper TTS, prefixed/suffixed with the
existing intercom chime, and played with the same duck-and-restore behavior the
intercom already uses.

## Background

The intercom addon (`intercom-addon/`) is an aiohttp server with two faces:

- A **LAN server** on port 9999 (`/intercom`) that ESPHome devices POST recorded
  PCM to. The handler builds a WAV (`ChimeMixer.build_wav`), writes it to
  `/config/www`, ducks the targets (`Ducker`), plays it via
  `media_player.play_media` at `{ha_url}/local/<file>`, then deletes the file.
- An **ingress UI** on port 8099 (`picker.html` + `/api/players`) for editing
  routes/aliases.

Announcements reuse this machinery: same chime, same ducker, same play/cleanup
path — only the audio source changes (Piper TTS instead of a mic recording).

## Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Trigger surface | Both: UI text box **and** HTTP API for automations |
| TTS engine | Piper (local); configurable via a `tts_engine` option |
| Manual target selection | Pick targets each time in the UI |
| Chime | Yes — reuse the existing intercom chime |
| Ducking | Yes — reuse the existing `Ducker` |
| API `targets` | Optional; if omitted/empty, fall back to **all** media players |
| Automation ergonomics | Documented `rest_command` only (no extra addon code) |

## Architecture

A new announcement flow mirrors the intercom flow but sources audio from Piper.
The play/duck/cleanup tail of `handle_intercom` is extracted into a shared
`_play_on_targets()` helper so both features stay byte-for-byte consistent.

```
UI textarea ──POST /api/announce (ingress)──┐
HA automation ─POST /announce (LAN :9999)───┤
                                            │
                                            ▼
                       resolve targets (explicit list, else all players)
                                            │
                                            ▼
                    HAClient.tts_get_audio(tts_engine, text)   ← Piper via supervisor proxy
                                            │
                                            ▼
                    build_announcement_wav(audio)              ← chime mixed at native rate
                                            │
                                            ▼
                    _play_on_targets(wav, ext, duration, targets)
                       = write /config/www → duck → play_media → schedule restore → delete
```

## Components

### 1. `HAClient.tts_get_audio(engine_id, message) -> bytes`
New method in `intercom-addon/ha_client.py`.

- `POST {HA_API}/tts_get_url` with `{"engine_id": engine_id, "message": message}`.
- Read `path` (e.g. `/api/tts_proxy/<token>.wav`) from the JSON response.
- `GET http://supervisor/core{path}` with the auth header to fetch the audio
  bytes.
- Raises `RuntimeError` on any non-200 (consistent with the other `HAClient`
  methods).

Stays entirely on the supervisor proxy — no dependency on the external
`ha_url`.

### 2. `announce.py` (new module)
Pure-logic audio assembly, no I/O, so it's unit-testable in isolation.

- `parse_tts_wav(audio: bytes) -> tuple[bytes, int, int, int] | None`
  Uses stdlib `wave` over a `BytesIO` to extract `(pcm, sample_rate,
  sample_width, channels)`. Returns `None` if the bytes aren't a parseable PCM
  WAV (e.g. the engine returned mp3).

- `build_announcement_wav(audio: bytes) -> tuple[bytes, str, float]`
  Returns `(wav_or_raw_bytes, extension, duration_seconds)`.
  - If `parse_tts_wav` succeeds: construct a `ChimeMixer` **at the audio's own
    sample rate / width / channels** and return
    `build_wav(pcm)` (chime + speech + chime), `"wav"`, and
    `total_duration_seconds(pcm)`. The chime sweep is generated per-rate, so no
    resampling is ever needed. (`ChimeMixer` requires 16-bit; Piper is 16-bit.)
  - If parsing fails: return the raw bytes unchanged, the guessed extension
    (default `"mp3"`), and a best-effort duration of `0` (cleanup uses a fixed
    grace window). Logged as a degraded "no chime" fallback — not an error.

### 3. `_play_on_targets(wav_bytes, ext, duration, targets)` — extracted in `intercom.py`
The existing tail of `handle_intercom` becomes a shared coroutine:

1. `filepath = /config/www/<name>.<ext>`; write bytes.
2. `await ducker.snapshot_and_pause(targets)`.
3. For each target: `await ha.play_media(player, f"{ha_url}/local/<name>.<ext>")`.
4. `ducker.schedule_restore(targets, duration + 1.5)`.
5. `asyncio.create_task(_delete_after(filepath, duration + 10))`.

`handle_intercom` is refactored to call this with its chime-mixed WAV; behavior
is unchanged (existing intercom tests must still pass).

### 4. Handlers
Both validate and share one core coroutine `_announce(text, targets)`:

- `handle_announce` — LAN router, `POST /announce` (for automations).
- `handle_announce_ingress` — ingress router, `POST /api/announce` (for the UI;
  the browser can't reach port 9999).

`_announce`:
1. Parse JSON `{text, targets?}`.
2. Validate: `text` is a non-empty string (else 400). If `targets` present, it
   must be a list of `media_player.*` ids (reuse `players._is_entity_list`, else
   400).
3. Resolve targets: explicit non-empty list as-is; otherwise
   `fetch_media_players()` → all `media_player.*` ids.
4. If still empty (no media players exist), 204 no-op with a warning.
5. `audio = await ha.tts_get_audio(tts_engine, text)` (502 on failure).
6. `wav, ext, duration = build_announcement_wav(audio)`.
7. `await _play_on_targets(wav, ext, duration, targets)`.
8. Return 204.

### 5. UI — `picker.html`
A new "Announce" section above the routes list:

- A `<textarea>` for the message.
- A target picker reusing the existing chip + `<select>` pattern, populated from
  the already-loaded `available` players (no new fetch).
- An "Announce" button → `POST ./api/announce` with `{text, targets}`.
- Toast on success; inline error on failure. Empty text disables the button.

### 6. Config — `config.yaml`
- `options`: add `tts_engine: "tts.piper"`.
- `schema`: add `tts_engine: str`.
- `_run()` reads it; handlers read it from `load_options()` per request (same as
  `ha_url`).
- Bump `version`.

## HA automation usage (documented, no addon code)

`rest_command` pointing at the same host/port the devices already use:

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

Call from an automation (explicit targets) or omit `targets` to hit all players:

```yaml
- action: rest_command.intercom_announce
  data:
    text: "Someone is at the front door"
    targets:
      - media_player.atom_echo_player
      - media_player.intercom_s3_player
```

This is documented in `docs/DEVICES.md` (or the addon README).

## Error handling

| Condition | Response |
|---|---|
| Empty/missing `text` | 400, message |
| `targets` present but not a `media_player.*` list | 400, message |
| `targets` omitted | resolve to all media players |
| No media players exist at all | 204 no-op, logged warning |
| `tts_get_url` / audio fetch fails | 502, logged |
| TTS output not parseable as WAV | play raw bytes, no chime; logged (not an error) |
| Invalid JSON body | 400 |

## Testing

Following the existing pytest patterns (`asyncio_mode = auto`, `AsyncMock` HA
stubs, module-level `monkeypatch`, `tmp_path` for `/config/www`):

- **`tests/test_announce.py`** (new):
  - `parse_tts_wav` round-trips a known WAV (rate/width/channels/pcm).
  - `parse_tts_wav` returns `None` for non-WAV bytes.
  - `build_announcement_wav` mixes the chime at the source's native rate and
    reports a duration longer than the bare speech.
  - `build_announcement_wav` falls back to raw bytes (no chime) on non-WAV
    input.
- **`tests/test_ha_client.py`** (additions):
  - `tts_get_audio` POSTs the correct `tts_get_url` body, then GETs the returned
    `path` and returns the bytes.
  - raises on non-200 at either step.
- **`tests/test_picker.py`** (additions, handler-level with `fake_ha`):
  - `/api/announce` with explicit targets → calls `tts_get_audio`,
    `play_media` per target, ducks, returns 204.
  - omitted targets → resolves to all `media_player.*` from `get_states`.
  - empty text → 400; non-WAV TTS → still plays (no chime).
  - existing intercom handler tests still pass after the `_play_on_targets`
    refactor.

## Out of scope (YAGNI)

- Per-announcement chime toggle (chime is always on).
- Per-announcement volume / TTS voice selection.
- Scheduling / queueing announcements (fire-and-forget, like the intercom).
- Webhook trigger path (rest_command is sufficient).
- Any ESPHome/firmware change (`devices/*.yaml` untouched).
