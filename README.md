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
| `denoise` | `true` | Clean up broadcast audio: high-pass, expander, normalise |

### Broadcast cleanup

The INMP441 has no gain control, and measurement showed device-side digital gain
buys nothing: SNR was 13-15 dB at unity, at +18 dB and at +36 dB alike, because
gain lifts the noise floor with the signal. So the device takes only a small
fixed +6 dB that cannot clip, and the real work happens in the add-on, where
there is CPU to spare and float headroom.

`denoise.py` runs four stages over each upload before it is broadcast:

1. **high-pass** at 80 Hz — the single biggest win. Measured on a real capture,
   **35% of the total RMS sits below 80 Hz**: room rumble carrying no speech at
   all. The filter is −3 dB at the corner and flat above 200 Hz, so the voice is
   untouched.
2. **multiband spectral subtraction** — 8 bands, each attenuated by the noise
   estimated for that band. This is the stage that matters, because it is the
   only one that reduces noise *while speech is present*. An expander alone was
   inaudible: measurement showed 67% of frames carry speech, and no gate can
   touch the hiss underneath them.
3. **downward expander** — cleans the remaining gaps. Its threshold is the
   *geometric mean* of the measured floor and the measured speech level (their
   midpoint in dB); a fixed multiple of the floor landed above the speech on
   real captures and attenuated everything equally, achieving nothing.
4. **level restore** — puts speech back at exactly the level it arrived at.

Stage 3 is deliberately **not** a normaliser. Raising the level lifts the
suppressed noise with it, which sounds like "louder, including the noise" — the
one thing this must not do. Set `MAKEUP_DB` if a broadcast genuinely needs more
level; it is in dB so the cost is explicit.

The band split is complementary — each band is a one-pole low-pass of what is
left, subtracted from the residual — so with all gains at 1 the bands sum back
to the input to within 2e-13. A conventional filter bank would leave crossover
ripple that colours the voice even when nothing is being attenuated.

Measured against a high-passed reference across eight real captures: **audible
hiss (1-8 kHz median) 7-12 dB down, voice level within ±0.5 dB, and the gaps
between words 11-14 dB quieter** without going dead. ~0.22 s of CPU per 5 s
upload. Set `denoise: false` to broadcast raw.

Both `BAND_GAIN_FLOOR` and `MAX_ATTENUATION` are taste calls, swept and
documented in the module: raise them if the gaps sound abrupt, lower them if
there is still too much hiss.

The retained recordings stay **raw** either way — that copy exists to expose mic
faults, and cleaning it would hide them. To hear what the cleanup does to a
capture, run `tools/denoise-preview.py <wav>`; it writes a `-clean` sibling and
prints the before/after statistics.

### Mic recordings

Every upload to `/intercom` — a PTT broadcast or a device's **Mic test
recording** button — is also kept as a chime-free WAV of the raw mic audio in
the add-on's `/data/recordings`, newest `keep_recordings` retained. The
**Intercom** side-panel lists them with an inline player, a download link and a
delete button, so a mic can be judged without repointing `mic_test_url` at
`tools/mic-capture.py` and reflashing.

Set `keep_recordings: 0` if you'd rather nothing spoken over the intercom is
retained on disk.

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
