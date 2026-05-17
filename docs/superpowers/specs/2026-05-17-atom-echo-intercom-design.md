# Atom Echo Intercom Design

**Date:** 2026-05-17
**Status:** Approved

## Overview

Push-to-talk intercom using the M5 Atom Echo: hold the button to record, release to broadcast the audio to configured HA media players. A local HA addon handles the relay — no cloud required for Sonos (Alexa is acceptable as an exception given it is inherently cloud-dependent).

## Hardware

Same device as the voice assistant project.

| Component | Details |
|-----------|---------|
| Device | M5 Atom Echo |
| MCU | ESP32-PICO-D4 |
| Microphone | SPM1423 (PDM, GPIO23) |
| Button | GPIO39 (active LOW) |
| LED | SK6812 RGB on GPIO27 |
| I2S bus | LRCLK=GPIO33, BCLK=GPIO19 |
| HA host | Raspberry Pi 5 |

## Architecture

```
[Atom Echo]
  button hold  →  mic capture (PCM, 16kHz 16-bit mono)
  button release →  HTTP POST /intercom  →  [Intercom Addon : 9999]
                                                │
                                   save temp WAV to /homeassistant/www/
                                                │
                                   HA REST API: media_player.play_media
                                                │
                             ┌──────────────────┴──────────────────┐
                      [Sonos speakers]                    [Alexa speakers]
                                                │
                                   asyncio timer → delete temp WAV
```

## ESPHome Configuration (`atom-echo.yaml`)

Replaces the `voice_assistant` block with `http_request`. Speaker component is removed (intercom is one-way).

### Components used

- `i2s_audio` + `microphone` (same pins as voice assistant config)
- `http_request` — sends the recorded buffer to the addon
- `light` (neopixelbus) — status LED
- `binary_sensor` (GPIO39) — push-to-talk button

### Button behavior

| Event | Action |
|-------|--------|
| Press | Start mic capture, LED blue |
| Release | Stop capture, HTTP POST PCM to addon, LED off |

### Recording storage

Mic data is written to **SPIFFS** (ESP32 onboard flash) during the button hold rather than accumulated in RAM. SPIFFS provides ~1.5 MB of usable storage, giving a maximum recording of **~46 seconds** at 16kHz 16-bit mono (32 KB/s).

### Upload (chunked HTTP POST)

After button release, ESPHome reads the SPIFFS file and uploads it in 16 KB chunks. Each request carries:

| Header | Value |
|--------|-------|
| `Content-Type` | `audio/pcm` |
| `X-Session-ID` | random UUID generated at press time |
| `X-Chunk-Index` | 0, 1, 2, … |
| `X-Final` | `1` on the last chunk, absent otherwise |

URL: `http://homeassistant.local:9999/intercom`

Upload happens after recording stops, so there is no concurrent mic capture + HTTP and no risk of dropping mic data.

## HA Addon (`intercom-addon`)

A local addon installed from `/addons/intercom-addon/` on the Pi. Managed by HA supervisor — starts on boot, restartable, configurable via HA UI.

### File structure

```
intercom-addon/
├── config.yaml       # addon metadata, options schema, port declaration
├── Dockerfile        # based on ghcr.io/home-assistant/aarch64-base:latest
├── run.sh            # entry point: python3 /intercom.py
└── intercom.py       # aiohttp relay server
```

### Addon options (HA UI)

| Option | Type | Description |
|--------|------|-------------|
| `ha_token` | string | Long-lived HA access token |
| `port` | int | Port to listen on (default: 9999) |
| `media_players` | list of strings | HA entity IDs to broadcast to |

Example:
```yaml
ha_token: "eyJ..."
port: 9999
media_players:
  - media_player.sonos_living_room
  - media_player.alexa_kitchen
```

### Relay server logic (`intercom.py`)

Each `POST /intercom` request is a chunk identified by `X-Session-ID` and `X-Chunk-Index`.

1. Read `X-Session-ID`, `X-Chunk-Index`, `X-Final` from headers
2. Append raw PCM body to an in-memory buffer keyed by session ID
3. If `X-Final` is absent, return 204 and wait for more chunks
4. On final chunk:
   a. Concatenate all buffered PCM for this session
   b. Generate `intercom-<session-id>.wav` filename
   c. Write WAV to `/homeassistant/www/<filename>` (prepend 44-byte header: 16kHz, 16-bit, mono)
   d. Call HA REST API: `POST /api/services/media_player/play_media` for each configured player
      - `media_content_id`: `http://homeassistant.local:8123/local/<filename>`
      - `media_content_type`: `music`
   e. Schedule deletion: `call_later(duration + 5, delete_file)`
   f. Drop session buffer from dict

### Port exposure

`config.yaml` declares port 9999 as `host` network so ESPHome can reach it directly.

## LED States

| State | Color |
|-------|-------|
| Idle | Off |
| Recording | Blue |
| Sending / done | Off (immediate on release) |

Error states (e.g. HTTP failure) are logged but do not change LED — keeping the UI simple.

## Deliverables

| File | Description |
|------|-------------|
| `atom-echo.yaml` | Updated ESPHome config (intercom mode) |
| `intercom-addon/config.yaml` | Addon metadata |
| `intercom-addon/Dockerfile` | Container definition |
| `intercom-addon/run.sh` | Entry point |
| `intercom-addon/intercom.py` | Relay server |

## Out of Scope

- Two-way communication (ESP32 cannot do simultaneous mic + speaker on one I2S bus)
- Runtime speaker selection (configured once in addon options)
- Wake word or voice command to trigger broadcast
- Audio compression (PCM is sent raw to keep ESPHome side simple)
