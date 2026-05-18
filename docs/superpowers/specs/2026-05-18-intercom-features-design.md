# Intercom feature batch: chimes, aliases, ducking, talkback, wake-word

Status: design approved 2026-05-18

## Goal

Make the intercom feel like a real intercom rather than a one-shot voicemail.
Add five features as one coordinated change:

1. **Pre/post chimes** on every broadcast
2. **Source aliases** in the picker UI
3. **Pre-broadcast ducking** of media playing on target speakers
4. **Talkback**: 30-second reply window to the most recent sender
5. **Wake-word PTT alternative** alongside the existing button

## Non-goals

- Live audio streaming (still write-then-play; latency reduction is a separate effort).
- Per-target volume control beyond pause/play.
- Custom wake-word training. Prebuilt micro_wake_word model only.
- Persisting talkback state across addon restarts.
- LED reply-mode indicator on receivers (deferred; can be added later via an HA
  automation reacting to a broadcast event).
- Replacing the button — wake word augments PTT, doesn't replace it.

## Architecture

```
┌─────────────────────────────┐         ┌────────────────────────────────────────┐
│      Atom Echo (firmware)   │         │       intercom-addon (Python)          │
│                             │ POST    │                                        │
│  ┌─ PTT button              │ /intercom                                        │
│  │  └─ recorder.start(HOLD) ├────────►│  handle_intercom:                      │
│  │                          │  chunked│   1. resolve route                     │
│  ├─ micro_wake_word         │  PCM    │      ├─ talkback? → reply route        │
│  │  └─ recorder.start(VAD)  │         │      └─ else     → routes[source]      │
│  │                          │         │   2. snapshot+pause each target        │
│  └─ recorder (HOLD or VAD)  │         │   3. mix chimes → WAV file             │
│     └─ RMS detector stops   │         │   4. play_media                        │
│        when silent          │         │   5. schedule restore (+duration)      │
│                             │         │   6. record_broadcast(source,targets)  │
│                             │         │      → set 30s reply-window for each   │
│  mic runs continuously      │         │        receiver that is itself a source│
│  (data callback fan-out:    │         │                                        │
│   wake-word + recorder)     │         │  picker UI (ingress):                  │
│                             │         │   • per-source row: alias field        │
│                             │         │   • aliases stored in players.json     │
└─────────────────────────────┘         └────────────────────────────────────────┘
```

### Python module split

Today the addon is a single 446-line `intercom.py`. To make the new behavior
testable in isolation, split into focused modules:

| Module        | Responsibility                                                   |
|---------------|------------------------------------------------------------------|
| `players.py`  | Load/save/validate `players.json` (incl. `aliases`)              |
| `chimes.py`   | Generate pre/post PCM tones, mix with payload                    |
| `ducking.py`  | Snapshot/pause/restore per target                                |
| `talkback.py` | In-memory reply-window state                                     |
| `ha_client.py`| Shared `aiohttp.ClientSession`, wraps HA API calls               |
| `intercom.py` | aiohttp routes (LAN + ingress), wire everything together         |

`ha_client.py` is the seam that lets unit tests inject a fake.

### Firmware module split

| File              | Change                                                       |
|-------------------|--------------------------------------------------------------|
| `recorder.h`      | Add `REC_HOLD` / `REC_VAD` modes + RMS-based silence detector|
| `uploader.h`      | Unchanged                                                    |
| `atom-echo.yaml`  | Mic always-on; add `micro_wake_word` with `on_wake_word_detected` |

## Server-side details

### Chimes (generated, not files)

Two short sine sweeps:

- `chime_in`  — ~120 ms, 800 → 1200 Hz, 5 ms linear fade-in/out
- `chime_out` — ~120 ms, 1200 → 800 Hz, same envelope

Generated once at startup at the configured `sample_rate` / `bits_per_sample` /
`channels`, cached as `bytes`. Mixed into the WAV as:

```
[WAV header][chime_in PCM][broadcast PCM][chime_out PCM]
```

Header `pcm_len` is the sum. No binary assets to ship; always matches the
configured audio format.

### `players.json` schema (forward-compatible)

```json
{
  "routes":   { "atom-echo-7a3b": ["media_player.sonos_kitchen"] },
  "default":  ["media_player.atom_echo_kitchen_player"],
  "aliases":  { "atom-echo-7a3b": "Kitchen" },
  "selves":   { "atom-echo-7a3b": "media_player.atom_echo_kitchen_player" }
}
```

- `aliases` (display-only, additive): re-flashing keeps existing routes intact.
- `selves`: maps a source name to **its own speaker** (the `media_player.*` on
  the same device). Used by talkback to route a reply back to where the
  original sender was standing. Optional per source.
- `load_players()` returns `aliases: {}` and `selves: {}` if missing — existing
  files keep working.
- `_validate_players_payload`:
  - `aliases` must be `dict[str, str]`, non-empty keys, non-empty values.
    (Empty value treated as "no alias", stripped on save.)
  - `selves` must be `dict[str, str]`, non-empty keys, values starting with
    `media_player.`.

### Picker UI

Each source row gets:
- Editable alias field (label, freeform string)
- "This device's speaker" dropdown (sets `selves[source]`; optional)
- Existing chips + dropdown for outgoing targets

Layout:

```
[alias input]   atom-echo-7a3b  (muted)
this device's speaker: [dropdown — media_player.atom_echo_…_player ▾]
outgoing: <speaker chips>             [+ add speaker]
```

The `default` row has no alias or self-player field.

### Ducking

For each target at broadcast time:

1. `GET /states/{entity_id}` → snapshot `{state, volume_level}`.
2. If `state == "playing"` → `POST /services/media_player/media_pause`.
3. Schedule `restore_after(target, snapshot, total_duration + 1.5s)`.
4. On restore, if snapshot was `playing`, call `media_player/media_play`.

Volume is left alone in v1.

#### Concurrent broadcasts to the same target

Keep an in-memory `dict[entity_id, snapshot]` keyed on the **first** snapshot
taken. Later broadcasts to a target that already has an active snapshot:

- Skip taking a new snapshot.
- Re-extend the existing restore timer to the new `expires_at` (debounce —
  don't stack timers).

The restore fires once, when the last broadcast's timer expires.

### Talkback

In-memory state, no persistence:

```python
# device -> (sender, expires_at_monotonic)
_reply_window: dict[str, tuple[str, float]] = {}
WINDOW_SECONDS = 30
```

**On upload from `source`:**

- If `_reply_window.get(source)` exists, not expired, and `selves[sender]` is
  set → route = `[selves[sender]]` (a media_player entity). Window stays open
  until time expiry — multiple replies within the same window are allowed.
- If window exists but `selves[sender]` is unset → log warning ("can't reply,
  sender has no self_player configured") and fall through to normal routes.
- Else → normal route lookup.

**After broadcast resolves targets:**

A target's media_player can be reverse-mapped to a source via the inverted
`selves` map. For each target that maps back to a source:

```python
target_to_source = {v: k for k, v in selves.items()}
for tgt in resolved_targets:
    receiver = target_to_source.get(tgt)
    if receiver:
        _reply_window[receiver] = (source, monotonic() + WINDOW_SECONDS)
```

Only receivers we know how to reply *from* (i.e., that are themselves sources)
get a window. Sonos / Google speakers without an associated source get none —
correctly, since they have no upload path.

#### Routing precedence

```
upload arrives from `source`
   │
   ├─ talkback window active for source?  ──yes──►
   │     │
   │     ├─ selves[sender] set?  ──yes──►  route = [selves[sender]]
   │     └─ no                 ──fall through, log warning──►
   │
   └─ source in routes?  ──yes──►  route = routes[source]
        │
        no  ──►  enroll source, route = default
```

When talkback wins, the route table is not modified — talkback is transient.
The window is **not** consumed by use; only expiry or being overwritten by a
new incoming broadcast clears it.

#### Edge cases covered

- Multi-recipient broadcast: every receiver mapped back to a source via
  `selves` gets the same 30 s window pointed at `source`.
- A→B, then B→A within 30 s: B's reply is a broadcast targeting
  `selves[A]`; that target maps back to A, so `_reply_window[A] = (B, +30)` —
  natural conversational ping-pong.
- New broadcast to a receiver mid-window: its window resets to the new sender
  (latest wins).
- Receiver that is not a source (no entry in `selves`'s inverse — e.g. a Sonos
  that can't push back): gets no window.
- Sender with no `selves` entry receives broadcasts normally (windows still
  open for them), but those windows are useless until they configure a
  self-player — replies fall through to normal routes with a warning.

### Observability

Log lines made richer so behavior is readable at INFO:

```
received  session=abc12345  source=atom-echo-7a3b (alias=Kitchen)  pcm=128000  duration=4.0s
talkback  source=Kitchen  reply-to=LivingRoom  → media_player.atom_echo_living_player  (window expires 27.3s)
routing   source=Kitchen  targets=[media_player.sonos_living]
ducking   media_player.sonos_living  state=playing  volume=0.45  → paused
playing   target=media_player.sonos_living  status=200
broadcast scheduled-restore=5.5s
restored  media_player.sonos_living  state=playing
```

## Firmware details

### Microphone lifecycle change

Today mic starts/stops on button press/release. For wake-word it must stream
continuously. Switch to always-on:

```yaml
esphome:
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
        - microphone.capture: atom_mic
```

`recorder_on_data` already gates on `_rec_active`, so off-state data is
discarded. Button handlers lose their `atom_mic.start()` / `.stop()` calls
(now no-ops anyway).

### `recorder.h` — modes + RMS VAD

```c
enum rec_mode_t { REC_HOLD, REC_VAD };

// VAD tuning (v1 compile-time constants; promote to config later if needed)
static const uint32_t VAD_MIN_MS        = 1000;   // ignore silence for first 1s
static const uint32_t VAD_SILENCE_MS    = 1200;   // stop after 1.2s quiet
static const uint32_t VAD_MAX_MS        = 15000;  // hard cap
static const uint16_t VAD_RMS_THRESHOLD = 600;    // tune empirically
```

`recorder_on_data` does two things in VAD mode:

1. Forward bytes to the stream buffer (unchanged path).
2. Compute RMS over the chunk; track `_last_loud_ms` and `_recording_start_ms`.

A poll (driven from the existing data callback, no new task) checks:

```
if (mode == VAD &&
    elapsed >= VAD_MIN_MS &&
    silence_for >= VAD_SILENCE_MS) || elapsed >= VAD_MAX_MS
  → _rec_done = true
```

The uploader already drains until `recorder_is_done()`, so the upload
terminates naturally.

Public API:

```c
void recorder_start();        // HOLD mode (existing behavior, button)
void recorder_start_vad();    // VAD mode (wake-word)
```

### `atom-echo.yaml` — wake-word entry point

```yaml
micro_wake_word:
  models:
    - model: <chosen-prebuilt-model>   # phrase chosen before merge
  on_wake_word_detected:
    - if:
        condition:
          lambda: 'return uploader_is_uploading() || recorder_is_active();'
        then:
          - logger.log: "wake word ignored — already recording/uploading"
        else:
          - light.turn_on: { id: status_led, red: 0%, green: 0%, blue: 100% }
          - lambda: |-
              recorder_start_vad();
              uploader_start("http://homeassistant.local:9999/intercom",
                             App.get_name().c_str());
          - wait_until:
              condition: 'lambda: return !uploader_is_uploading();'
              timeout: 20s
          - light.turn_off: status_led
```

Button path (`on_press` / `on_release`) keeps calling `recorder_start()` for
HOLD mode. Both paths feed the same uploader and same `/intercom` endpoint —
the server can't and shouldn't distinguish them.

### Concurrency guards

- `uploader_is_uploading()` is the lock on overlapping uploads — both
  handlers check it.
- Wake-word during an in-progress recording → ignored by the `if` guard.
- Button during a wake-word recording → ignored by existing `if` guard.

## Testing & error handling

### Unit tests (mirror `tests/test_picker.py` style)

| Module | Tests |
|--------|-------|
| `chimes.py` | Generated chime length == expected ms × sample_rate; total mixed length == chime + pcm + chime; regenerates when sample format changes |
| `players.py` | `aliases` + `selves` round-trip through load/save; missing fields load as `{}`; validation rejects non-string keys/values; `selves` values must start with `media_player.`; existing route/default behavior unchanged |
| `talkback.py` | Reply within window routes to `selves[sender]`; reply when `selves[sender]` is unset falls through with warning; window NOT consumed on use, only on expiry; expired window falls back to normal routes; window resets on new broadcast; A→B then B→A both work; non-source receivers don't get windows |
| `ducking.py` | Snapshot captures state+volume; only paused if was playing; restore called once after duration; concurrent broadcasts debounce restore; restore is no-op if snapshot was paused |
| `intercom.py` integration | End-to-end with mocked `HAClient`: upload → mix → play_media → restore. Talkback path overrides routing. Alias-only edit doesn't disturb routes. |

### Firmware manual smoke matrix

- [ ] Button PTT records and plays as before (regression)
- [ ] Wake-word starts a recording; goes silent → recording ends ~1.2 s later → plays
- [ ] Wake-word while uploading → ignored, log line emitted
- [ ] Button while wake-word recording → ignored
- [ ] VAD hard cap (15 s) fires when speaker keeps talking
- [ ] Mic always-on doesn't OOM or drop ("buffer full" warnings stay absent under normal use)

### Error handling boundaries

| Failure | Behavior |
|---------|----------|
| Target offline / `media_pause` errors | Log + skip pause for that target, still attempt `play_media` |
| `play_media` fails on a target | Log + still schedule restore for any successful pauses |
| Target state unknown at snapshot time | Treat as `idle`; no restore needed |
| Chime generation fails (defensive) | Log + serve broadcast without chimes |
| `players.json` has malformed `aliases` | Log error; drop `aliases` field; keep routes intact |
| Talkback dict growth | Bounded by enrolled-source count; entries expire on read or next broadcast. No GC needed in v1. |

## Open items before merge

- Choose wake-word phrase (prebuilt micro_wake_word model).
- Tune `VAD_RMS_THRESHOLD` empirically against the Atom Echo PDM mic gain
  with typical room noise.
- Decide chime tone shape on a real speaker (the sweep frequencies above are
  starting points, not final).
