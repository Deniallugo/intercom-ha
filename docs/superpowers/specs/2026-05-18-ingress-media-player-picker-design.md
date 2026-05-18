# Ingress Media Player Picker

## Problem

The intercom add-on currently configures target media players as a free-text list of strings in `options.yaml` (`media_players: [str]`). Home Assistant add-on schemas don't support entity pickers, so users have to type entity IDs exactly. A real picker — selecting from the actual `media_player.*` entities in Home Assistant — is more discoverable and prevents typos.

In addition, the Atom Echo M5 devices are mic-only today: they send audio but cannot receive it, so a true two-way intercom mesh isn't possible. The routing is also a single global broadcast list — every sender plays to the same set of targets — which doesn't let users build asymmetric routes (kitchen → bedroom only).

## Solution

Three coordinated changes:

1. **Atom Echo speaker + media_player** — extend `atom-echo.yaml` so each M5 also exposes a speaker and a `media_player` entity in HA. Each M5 becomes both a source and a valid target.
2. **Per-source routing** — replace the single global `media_players` list with a routes map keyed by the sender's source ID. Each source has its own list of target entity IDs.
3. **Ingress UI for picking** — add a small Home Assistant ingress UI to the add-on. It lists every `media_player.*` entity from HA's state API and lets the user check, per source, which targets that source broadcasts to. The selection is stored in `/data/players.json` and read by `POST /intercom` on every request.

This replaces the `media_players` option entirely. Existing add-on config values for it are dropped (breaking change → version 2.0.0).

## Architecture

Two HTTP listeners in one Python process, started concurrently in `main()`:

- **LAN listener on port 9999** (existing): handles `POST /intercom` only. ESPHome hits this directly. No auth, no UI surface.
- **Ingress listener on port 8099**: handles the picker UI — `GET /`, `GET /api/players`, `POST /api/players`. Reached via Home Assistant's ingress proxy (`ingress: true` in `config.yaml`), so HA gates auth.

Separating listeners ensures the picker API is never exposed to anyone on the LAN — only authenticated HA users via ingress.

## ESPHome device changes (`atom-echo.yaml`)

### Speaker + media_player component

The Atom Echo wires its mic (PDM, GPIO23) and speaker (PCM, GPIO22) onto the same shared I2S BCLK (GPIO19) and LRCLK (GPIO33) pins. ESPHome's I2S driver reconfigures the peripheral between PDM-RX and PCM-TX as needed — half-duplex, which is fine for a PTT intercom (mic is only active while PTT is held; speaker is only active when receiving).

Add to `atom-echo.yaml` under the existing `i2s_audio:` block:

```yaml
speaker:
  - platform: i2s_audio
    id: atom_speaker
    i2s_dout_pin: GPIO22
    dac_type: external
    mode: mono

media_player:
  - platform: speaker
    id: atom_player
    name: "${friendly_name} Player"
    announcement_pipeline:
      speaker: atom_speaker
      format: WAV
```

The resulting HA entity ID is `media_player.<name>_player` (slugified). This entity shows up automatically once the device joins HA — no manual config in the add-on.

### Per-device naming

`atom-echo.yaml` sets `name_add_mac_suffix: true` so each flashed unit's device name is `${name}-<6 hex>` automatically — no per-device YAML editing required. The resulting source IDs are stable across reboots and unique per board.

### `X-Device-Name` header on upload

`uploader.h` and `atom-echo.yaml` already pass the device name through to the upload as the `X-Device-Name` header (`App.get_name().c_str()` in the lambda call to `uploader_start`). No further firmware changes are required. The add-on uses this header value as the route key — so source IDs in `players.json` look like `atom-echo-aabbcc`.

## `config.yaml` changes

```yaml
version: "2.0.0"
ingress: true
ingress_port: 8099
panel_icon: mdi:speaker-multiple
panel_title: Intercom
```

Remove from `options` and `schema`:

```yaml
media_players: []      # removed
media_players: - str   # removed from schema
```

No automatic migration. After upgrade, the routes map is empty until the user opens the panel and saves selections.

## Persistence

- **File**: `/data/players.json`
- **Shape**:

```json
{
  "routes": {
    "atom-echo-aabbcc": ["media_player.atom_echo_ddeeff_player"],
    "atom-echo-ddeeff": ["media_player.atom_echo_aabbcc_player"]
  },
  "default": []
}
```

- **`routes`**: map from source ID (the `X-Device-Name` header value sent by the M5) → list of target entity IDs.
- **`default`**: fallback target list used when an incoming source isn't in `routes` (e.g. a newly-flashed M5 before its routes are configured, or any other client).
- **Read**: fresh on every `POST /intercom` (matches existing per-request `load_options()` pattern).
- **Write**: atomic — write to `/data/players.json.tmp`, then `os.replace()` to final path. Prevents corruption if the process dies mid-write.
- **Missing/empty file**: log a warning, skip the HA API call, still return 204 to ESPHome so it doesn't retry.
- **Malformed JSON**: log error, treat as empty routes + empty default, don't crash.

## Source discovery (implicit)

Sources are recorded as M5s upload for the first time. On every `POST /intercom`:

1. Read `X-Device-Name` header. If absent or empty, source = `"unknown"`.
2. If `source` isn't in `routes` yet, add it with an empty target list and write back atomically.
3. Use `routes[source]` (or `default` if the entry was just freshly created and is empty) as the play list.

This means a newly-flashed M5 enrolls itself the first time its PTT is pressed; the user then opens the picker UI to assign targets. No separate registration endpoint, no per-device YAML editing on the server side.

## UI

Single HTML page served inline by aiohttp as a Python string constant in `intercom.py`. No separate static files — Dockerfile and `map:` block stay unchanged.

Layout: a **matrix**.

- **Columns**: every `media_player.*` discovered from HA's states API, sorted alphabetically by friendly name. Header row shows `friendly_name (entity_id)`.
- **Rows**: every source ID currently in `routes` (sorted alphabetically), plus a fixed `default` row at the bottom.
- **Cells**: checkboxes. Checking row R, column C means "when source R sends audio, play it on target C".

Behavior:

- On load, `fetch('./api/players')` → render the matrix.
- "Save" button → `POST ./api/players` with the full new routes map → on 204, show "Saved" toast.
- On API failure: show "Could not load — Retry" with a retry button.
- If no sources are known yet, show only the `default` row and a help line: "Press the PTT on each Atom Echo once to enroll it as a source."
- Plain CSS, no framework. Native checkboxes; entity IDs in monospace.

## Backend endpoints (ingress port only)

### `GET /api/players`

1. Call `http://supervisor/core/api/states` with `Authorization: Bearer $SUPERVISOR_TOKEN`.
2. Filter to entries where `entity_id` starts with `media_player.`.
3. Read `/data/players.json` for current routes (empty map if missing).
4. Return:

```json
{
  "available": [
    {"entity_id": "media_player.atom_echo_aabbcc_player", "friendly_name": "Atom Echo aabbcc Player"},
    {"entity_id": "media_player.sonos_lounge", "friendly_name": "Sonos Lounge"}
  ],
  "routes": {
    "atom-echo-aabbcc": ["media_player.atom_echo_ddeeff_player"]
  },
  "default": []
}
```

If the supervisor call fails: return 502 with `{"error": "..."}`.

### `POST /api/players`

1. Parse JSON body: `{"routes": {...}, "default": [...]}`.
2. Validate:
   - `routes` is an object whose values are lists of strings each starting with `media_player.`
   - `default` is a list of strings each starting with `media_player.`
   - Source keys in `routes` are non-empty strings.
   - Reject with 400 otherwise.
3. Atomic write to `/data/players.json`.
4. Return 204.

## Existing `POST /intercom` changes

Replace `players = opts.get("media_players", [])` with:

1. Read `X-Device-Name` header (fall back to `"unknown"` if missing or empty).
2. Read `/data/players.json`.
3. If `source` not in `routes`: add it with empty list, atomic-write back, then use `default` as the play list for this request.
4. Otherwise use `routes[source]`.
5. Everything else (WAV writing, HA API call per player, cleanup) stays the same.

An empty target list (in either `routes[source]` or `default`) means "no play" — by design. This lets a user explicitly silence a source by saving an empty row. After first enrollment a source has an empty list, so the second PTT will not play anywhere until the user assigns targets in the UI. The first PTT plays on `default` so the user gets an immediate signal that the device is connected.

If `/data/players.json` is missing/empty/malformed: log a warning, skip the play loop, still return 204.

## Error handling & edge cases

| Case | Behavior |
|------|----------|
| Supervisor API down on `GET /api/players` | 502 with error message; UI shows retry button |
| Empty routes saved | Allowed; intercom is a no-op for unmapped sources until repopulated. Warning logged on each `POST /intercom`. |
| Stale entity ID in `routes` (entity deleted in HA) | `play_media` returns non-200; logged. Other entries still play. |
| Concurrent saves | Last writer wins (atomic rename) |
| `players.json` hand-edited and malformed | Logged error, empty routes + default, no crash |
| `X-Device-Name` header missing | Source = `"unknown"`; uses `default` route. |
| New source uploads while user is editing UI | Source gets added to the on-disk file. The next UI reload picks it up; in-flight edits are not preserved across the reload. |

## Testing

Existing `tests/test_intercom.py` references `srv.sessions` and `X-Chunk-Index` that no longer exist in the code — those tests are pre-existing failures and out of scope for this work.

New tests to add:

- `POST /api/players` writes `/data/players.json` with the expected JSON shape.
- `POST /api/players` rejects target entries not starting with `media_player.` with 400.
- `POST /api/players` rejects non-list values in `routes` with 400.
- `GET /api/players` filters supervisor response to `media_player.*` only.
- `POST /intercom` with a known `X-Device-Name` posts to that source's route targets only.
- `POST /intercom` with an unknown `X-Device-Name` adds the source to `routes`, posts to `default`.
- `POST /intercom` with missing `X-Device-Name` uses source `"unknown"` and `default`.
- `POST /intercom` with missing `/data/players.json` → 204, no HA call, warning logged.

The ingress UI HTML/JS is not unit-tested; verified manually through the HA panel.

## Out of scope

- Grouping players by area or device
- "Test play" buttons per entity
- Search/filter in the picker
- Auto-refresh of the entity list (user reloads the panel to refresh)
- Migrating old `media_players` option values into `players.json`
- Fixing the pre-existing stale tests
- Full-duplex audio on Atom Echo (we rely on half-duplex PTT semantics)
- Volume control on the M5 media_player (HA's default speaker volume slider is enough)
