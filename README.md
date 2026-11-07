# Intercom HA

A whole-home push-to-talk intercom and voice satellite on
[Home Assistant](https://www.home-assistant.io/) and [ESPHome](https://esphome.io/).
Hold a device's button to talk; your voice plays on the other devices' speakers.
The same path carries TTS announcements; the devices are also Assist satellites
and music players.

- **Firmware** (`devices/`, `include/`, `packages/`) — ESPHome configs.
- **Add-on** (`intercom-addon/`) — receives uploads, adds chimes, ducks media,
  plays the result on the target media players; renders text announcements.

## Devices

| Device | MCU | Role |
|---|---|---|
| **Kitchen** — M5Stack Atom Echo + 1× MAX98357A | ESP32 (no PSRAM) | Button-PTT intercom, TTS announcements, DMA watchdog auto-reboot |
| **Terrace** — M5Stack VoiceS3R + 2× MAX98357A (dual mono) | ESP32-S3 (8 MB PSRAM) | PTT intercom, wake word (`okay nabu`) + HA Assist, Spotify via Music Assistant, TTS announcements |
| **Voice S3** — bare ESP32-S3 + PCM5102A + ZK-502MT amp + INMP441 + button | ESP32-S3 N16R8 (8 MB PSRAM) | One box on 24 V: stereo Music Assistant player with a built-in 2 × 50 W amp driving two passive speakers, wake word + HA Assist, tap-to-talk / hold-to-intercom. Mic and DAC on separate I²S peripherals, so it keeps listening while playing |

Wiring, GPIO maps and hardware notes: **[docs/DEVICES.md](docs/DEVICES.md)**.

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

The add-on's ingress panel also sends text announcements (Piper TTS) down the
same path.

## Repository layout

```
intercom/
├── devices/              # ESPHome device configs (+ gitignored secrets-*.yaml)
│   ├── atom-echo.yaml         # Kitchen Atom Echo
│   ├── intercom-s3.yaml       # Terrace VoiceS3R
│   ├── intercom-s3-minimal.yaml
│   ├── speaker-s3.yaml        # Bare S3 + PCM5102A, playback only
│   └── voice-s3.yaml          # Bare S3 + PCM5102A + ZK-502MT amp + INMP441 + button
├── include/              # Shared C++ — recorder.h (PCM ring + gain), uploader.h (chunked POST)
├── packages/base.yaml    # Shared logger/api/ota/wifi/captive_portal
├── intercom-addon/       # HA add-on (aiohttp): relay, chimes, ducking, talkback, announce, recordings
├── tests/                # pytest suite for the add-on
├── hardware/             # 3D-printable enclosures (kitchen, terrace, speaker, voice puck)
├── tools/mic-capture.py  # Bench tool — catch a device's mic upload as a WAV + verdict
├── tools/wyoming-macos/  # launchd plists — remote Whisper/Piper on a Mac
├── docs/DEVICES.md       # Full hardware + wiring reference
├── docs/REMOTE-VOICE.md  # Offloading STT/TTS off the Pi onto a LAN machine
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
| `keep_recordings` | `10` | Mic recordings retained for playback in the panel (`0` disables) |
| `denoise` | `true` | Clean up broadcast audio: high-pass, band subtraction, expander, level to −16 dBFS. Off — no noise reduction, but speech is still levelled to −16 dBFS |

### Broadcast cleanup

`denoise.py` processes each upload before broadcast (the stored recording stays raw):

1. high-pass at 80 Hz — removes room rumble (35 % of a capture's RMS was below 80 Hz);
2. 8-band spectral subtraction — the only stage that reduces hiss under speech;
3. downward expander — quiets the gaps between words;
4. level — speech to −16 dBFS, lookahead limiter at −3 dBFS peaks.

`denoise: false` skips 1–3 and keeps 4 (`denoise.level()`). Raw uploads arrive at
−21 to −33 dBFS, too quiet next to music and the chime. The level stage must
stay last, after the noise is down. Measured on voice-s3:

| | speech | floor between words |
|---|---|---|
| raw upload | −31.0 dBFS | −57.8 dBFS |
| `denoise: false` | −16.0 | −42.9 |
| `denoise: true` | −16.2 | −60.2 |

Tuning: `BAND_GAIN_FLOOR` and `MAX_ATTENUATION` in `denoise.py` (raise if gaps
sound abrupt, lower if hiss remains). Preview a capture with
`tools/denoise-preview.py <wav>`. Device-side mic gain: [docs/DEVICES.md](docs/DEVICES.md) → INMP441 mic.

### Mic recordings

Every upload to `/intercom` is also saved as a raw, chime-free WAV in
`/data/recordings` (newest `keep_recordings`; `0` keeps nothing and deletes old
ones). The side-panel lists them with player, download and delete.

The **Mic test recording** button (voice-s3, atom-echo) records 5 s and uploads
to the `mic_test_url` substitution — the add-on by default, so the test is saved
here **and played on the device's target speakers**. For level/SNR statistics,
point `mic_test_url` at `tools/mic-capture.py`; PTT is unaffected.

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

Add-on tests (use a venv — macOS `python3` has no pytest):

```bash
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
.venv/bin/python -m pytest tests -q
```

Voice-case design checks: `cd hardware/voice-case/fusion/VoiceCase && python3 -m vc.checks`.

## License

No license file; all rights reserved.
