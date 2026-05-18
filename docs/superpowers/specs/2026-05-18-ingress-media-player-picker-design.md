# Ingress Media Player Picker

## Problem

The intercom add-on currently configures target media players as a free-text list of strings in `options.yaml` (`media_players: [str]`). Home Assistant add-on schemas don't support entity pickers, so users have to type entity IDs exactly. A real picker — selecting from the actual `media_player.*` entities in Home Assistant — is more discoverable and prevents typos.

## Solution

Add a small Home Assistant ingress UI to the add-on. It lists every `media_player.*` entity from HA's state API and lets the user check which ones the intercom should broadcast to. The selection is stored in `/data/players.json` and read by the existing `POST /intercom` handler on every request.

This replaces the `media_players` option entirely. Existing add-on config values for it are dropped (breaking change → version 2.0.0).

## Architecture

Two HTTP listeners in one Python process, started concurrently in `main()`:

- **LAN listener on port 9999** (existing): handles `POST /intercom` only. ESPHome hits this directly. No auth, no UI surface.
- **Ingress listener on port 8099**: handles the picker UI — `GET /`, `GET /api/players`, `POST /api/players`. Reached via Home Assistant's ingress proxy (`ingress: true` in `config.yaml`), so HA gates auth.

Separating listeners ensures the picker API is never exposed to anyone on the LAN — only authenticated HA users via ingress.

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
media_players: []   # removed
media_players: - str   # removed from schema
```

No automatic migration. After upgrade, the picker shows zero selections until the user opens the panel and saves.

## Persistence

- **File**: `/data/players.json`
- **Shape**: `{"selected": ["media_player.kitchen", "media_player.bedroom"]}`
- **Read**: fresh on every `POST /intercom` (matches existing per-request `load_options()` pattern).
- **Write**: atomic — write to `/data/players.json.tmp`, then `os.replace()` to final path. Prevents corruption if the process dies mid-write.
- **Missing/empty file**: log a warning, skip the HA API call, still return 204 to ESPHome so it doesn't retry.
- **Malformed JSON**: log error, treat as empty selection, don't crash.

## UI

Single HTML page served inline by aiohttp as a Python string constant in `intercom.py`. No separate static files — Dockerfile and `map:` block stay unchanged.

Behavior:

- On load, `fetch('./api/players')` → render alphabetically-sorted checklist. Each row: `[checkbox] friendly_name (entity_id)`. Box checked = currently selected.
- "Save" button → `POST ./api/players` with `{"selected": [...]}` → on 204, show "Saved" toast.
- On API failure: show "Could not load media players — Retry" with a retry button.
- Plain CSS, no framework. Native checkboxes; entity IDs in monospace.

## Backend endpoints (ingress port only)

### `GET /api/players`

1. Call `http://supervisor/core/api/states` with `Authorization: Bearer $SUPERVISOR_TOKEN`.
2. Filter response to entries where `entity_id` starts with `media_player.`.
3. Read `/data/players.json` for current selection (empty list if missing).
4. Return:

```json
{
  "available": [
    {"entity_id": "media_player.kitchen", "friendly_name": "Kitchen Sonos"}
  ],
  "selected": ["media_player.kitchen"]
}
```

If the supervisor call fails: return 502 with `{"error": "..."}`.

### `POST /api/players`

1. Parse JSON body: `{"selected": [...]}`.
2. Validate: must be a list of strings, each starting with `media_player.`. Reject with 400 otherwise.
3. Atomic write to `/data/players.json`.
4. Return 204.

## Existing `POST /intercom` changes

Replace `players = opts.get("media_players", [])` with a read of `/data/players.json`. Everything else (WAV writing, HA API call per player, cleanup) stays the same.

If `/data/players.json` is missing/empty/malformed: log a warning, skip the play loop, still return 204.

## Error handling & edge cases

| Case | Behavior |
|------|----------|
| Supervisor API down on `GET /api/players` | 502 with error message; UI shows retry button |
| Empty selection saved | Allowed; intercom is a no-op until repopulated. Warning logged on each `POST /intercom`. |
| Stale entity ID in `players.json` (entity deleted in HA) | `play_media` returns non-200; logged (existing behavior). Other entries still play. |
| Concurrent picker saves | Last writer wins (atomic rename) |
| `players.json` hand-edited and malformed | Logged error, empty selection, no crash |

## Testing

Existing `tests/test_intercom.py` references `srv.sessions` and `X-Chunk-Index` that no longer exist in the code — those tests are pre-existing failures and out of scope for this work.

New tests to add:

- `POST /api/players` writes `/data/players.json` with the expected JSON shape.
- `POST /api/players` rejects entries not starting with `media_player.` with 400.
- `GET /api/players` filters supervisor response to `media_player.*` only.
- `POST /intercom` reads `/data/players.json` and posts to every selected entity.
- `POST /intercom` with missing `/data/players.json` → 204, no HA call, warning logged.

The ingress UI HTML/JS is not unit-tested; verified manually through the HA panel.

## Out of scope

- Grouping players by area or device
- "Test play" buttons per entity
- Search/filter in the picker
- Auto-refresh of the entity list (user reloads the panel to refresh)
- Migrating old `media_players` option values into `players.json`
- Fixing the pre-existing stale tests
