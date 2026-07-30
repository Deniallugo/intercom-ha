# Intercom HA

A whole-home **push-to-talk intercom + voice satellite** built on
[Home Assistant](https://www.home-assistant.io/) and [ESPHome](https://esphome.io/).

Press a button on any device to record, and your voice is broadcast through the
speakers of every other device. The same path also carries Home Assistant TTS
announcements, wake-word voice assist, and music streaming — all into custom
external speakers driven by MAX98357A amps.

The project has two halves:

- **Firmware** (`devices/`, `include/`, `packages/`) — ESPHome configs for the
  ESP32 satellites.
- **Add-on** (`intercom-addon/`) — a Home Assistant add-on (Python/aiohttp) that
  receives audio from the devices, mixes in chimes, ducks any playing media, and
  broadcasts to the target media players. It also renders text announcements via
  Piper TTS.

## Devices

| Device | MCU | Role |
|---|---|---|
| **Kitchen** — M5Stack Atom Echo + 1× MAX98357A | ESP32 (no PSRAM) | Button-PTT intercom, TTS announcements, DMA watchdog auto-reboot |
| **Terrace** — M5Stack VoiceS3R + 2× MAX98357A (dual mono) | ESP32-S3 (8 MB PSRAM) | PTT intercom, wake word (`okay nabu`) + HA Assist, Spotify via Music Assistant, TTS announcements |
| **Voice S3** — bare ESP32-S3 + PCM5102A + INMP441 + button | ESP32-S3 N16R8 (8 MB PSRAM) | Stereo Music Assistant player on a 3.5 mm line-out, wake word + HA Assist, tap-to-talk / hold-to-intercom. Mic and DAC on separate I²S peripherals, so it keeps listening while playing |

See **[docs/DEVICES.md](docs/DEVICES.md)** for the full hardware reference:
wiring diagrams, GPIO maps, the audio pipeline, and the key technical decisions
(two-I²S-bus design, dual-mono amps, codec mic gain, DMA fragmentation watchdog).

## How it works

```
   Button press                                      Other device(s)
        │                                                   ▲
        ▼                                                   │
   ESP32 records mic ──HTTP POST──►  intercom-addon  ──media_player.play_media──┘
   (recorder.h /                    (port 9999)
    uploader.h)                      • prepends/appends chime
                                     • ducks media playing on targets
                                     • broadcasts to target players
```

The same add-on serves an **Announce** panel (HA ingress) where you type text
that's rendered with Piper TTS and played on the players you pick — the identical
broadcast path the intercom uses.

## Repository layout

```
intercom/
├── devices/              # ESPHome device configs (+ gitignored secrets-*.yaml)
│   ├── atom-echo.yaml         # Kitchen Atom Echo
│   ├── intercom-s3.yaml       # Terrace VoiceS3R
│   ├── intercom-s3-minimal.yaml
│   ├── speaker-s3.yaml        # Bare S3 + PCM5102A, playback only
│   ├── voice-s3.yaml          # Bare S3 + PCM5102A + INMP441 + button
│   └── listen_and_answer.yaml
├── include/              # Shared C++ — recorder.h (PCM ring + gain), uploader.h (chunked POST)
├── packages/base.yaml    # Shared logger/api/ota/wifi/captive_portal
├── intercom-addon/       # HA add-on (aiohttp): relay, chimes, ducking, talkback, announce
├── tests/                # pytest suite for the add-on
├── hardware/             # 3D-printable enclosures (kitchen, terrace)
├── tools/mic-capture.py  # Bench tool — catch a device's mic upload as a WAV + verdict
├── docs/DEVICES.md       # Full hardware + wiring reference
└── flash.sh              # ./flash.sh <device> — flash helper
```

## Firmware: flashing a device

Requires [ESPHome](https://esphome.io/guides/installing_esphome.html) installed.
Each device needs its own `devices/secrets-<name>.yaml` (gitignored) defining
`wifi_ssid`, `wifi_password`, `ap_password`, and `api_encryption_key` —
consumed by `packages/base.yaml`.

```bash
./flash.sh                     # list available devices
./flash.sh atom-echo           # auto (OTA over mDNS, or USB if plugged in)
./flash.sh intercom-s3 /dev/cu.usbserial-0001   # explicit USB port
./flash.sh atom-echo atom-echo-7a3b.local       # explicit OTA host
```

## Add-on: installation

This repo is a Home Assistant **add-on repository**. In Home Assistant:

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, add:
   `https://github.com/Deniallugo/intercom-ha`
2. Install **Intercom Relay**, then **Start** it.
3. Open the add-on's **Intercom** side-panel (ingress) to pick announcement
   targets and send text announcements.

Pre-built images are published to GHCR for `aarch64` and `amd64` on each version
tag (see `.github/workflows/build.yml`).

### Configuration

| Option | Default | Description |
|---|---|---|
| `ha_url` | `http://homeassistant.local:8123` | Home Assistant base URL |
| `port` | `9999` | TCP port for ESPHome audio uploads |
| `sample_rate` | `16000` | Audio sample rate (Hz) |
| `bits_per_sample` | `16` | Sample width |
| `channels` | `1` | Channel count |
| `tts_engine` | `tts.piper` | HA TTS engine for text announcements |

### HTTP API

The add-on listens on `port` (default `9999`):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/intercom` | Receive a PCM audio upload from a device and broadcast it |
| `POST` | `/announce` | Render text via TTS and play on targets (omit `targets` → all players) |

Trigger an announcement from a Home Assistant automation with a `rest_command`:

```yaml
rest_command:
  intercom_announce:
    url: "http://homeassistant.local:9999/announce"
    method: POST
    content_type: "application/json"
    payload: >
      {"text": "{{ text }}", "targets": {{ targets | tojson }}}
```

```yaml
- action: rest_command.intercom_announce
  data:
    text: "Someone is at the front door"
    targets:
      - media_player.atom_echo_player
      - media_player.intercom_s3_player
```

See [docs/DEVICES.md → Announcements](docs/DEVICES.md) for details.

## Development

The add-on logic is plain Python with a pytest suite:

```bash
pip install -r tests/requirements.txt
pytest
```

## License

No license file is present; treat as all rights reserved unless the maintainer
states otherwise.
