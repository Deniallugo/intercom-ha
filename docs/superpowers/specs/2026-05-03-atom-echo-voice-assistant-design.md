# M5 Atom Echo — Local Voice Assistant Design

**Date:** 2026-05-03
**Status:** Approved

## Overview

A fully local, push-to-talk voice assistant using an M5 Atom Echo (ESP32-PICO-D4) connected to Home Assistant via the ESPHome native API. Speech-to-text runs via Faster-Whisper, text-to-speech via Piper, and intent handling via HA Assist — all on-device with no cloud services.

## Hardware

| Component | Details |
|-----------|---------|
| Device | M5 Atom Echo |
| MCU | ESP32-PICO-D4 |
| Microphone | SPM1423 (PDM) |
| Speaker | NS4168 (I2S, 1W) |
| Button | GPIO39 |
| LED | SK6812 RGB on GPIO27 |
| HA host | Raspberry Pi 5 |

## Architecture

```
[Atom Echo] ──ESPHome native API──► [Home Assistant]
                                         │
                          ┌──────────────┼──────────────┐
                     [Faster-Whisper]  [Assist]       [Piper]
                       (STT, local)  (intent)    (TTS, local)
```

Audio flows:
- **TX (mic → HA):** Button held → SPM1423 PDM mic → ESPHome streams PCM to HA → Faster-Whisper transcribes
- **RX (HA → speaker):** Piper synthesizes TTS audio → ESPHome streams to NS4168 speaker

## Home Assistant Setup

### Addons to install

1. **Faster-Whisper** (community addon, Wyoming protocol)
   - Model: `small` (good accuracy, ~1-2s on Pi 5)
   - Language: user's language (e.g. `en`)

2. **Piper** (official HA addon, Wyoming protocol)
   - Voice: user's choice (e.g. `en_US-lessac-medium`)

### Pipeline configuration

Settings → Voice Assistants → Add pipeline:
- Name: `Local`
- STT: Faster-Whisper (`small`)
- TTS: Piper (chosen voice)
- Conversation agent: Home Assistant

## ESPHome Configuration

Single YAML file for the Atom Echo with these sections:

### I2S audio bus

```yaml
i2s_audio:
  i2s_lrclk_pin: GPIO26
  i2s_bclk_pin: GPIO0
```

### Microphone (SPM1423, PDM)

```yaml
microphone:
  platform: i2s_audio
  i2s_din_pin: GPIO34
  adc_type: external
  pdm: true
```

### Speaker (NS4168)

```yaml
speaker:
  platform: i2s_audio
  i2s_dout_pin: GPIO25
  dac_type: external
  mode: mono
```

### Voice assistant

```yaml
voice_assistant:
  microphone: mic_id
  speaker: spk_id
  noise_suppression_level: 2
  auto_gain: 31dBFS
  volume_multiplier: 2.0
  on_listening: # LED blue
  on_stt_end:   # LED yellow (thinking)
  on_tts_start: # LED green (speaking)
  on_end:       # LED off (idle)
  on_error:     # LED red briefly
```

### Button (GPIO39) — push-to-talk

```yaml
binary_sensor:
  platform: gpio
  pin: GPIO39
  on_press:
    voice_assistant.start
  on_release:
    voice_assistant.stop
```

### LED states

| State | Color |
|-------|-------|
| Idle | Off |
| Listening | Blue |
| Thinking (STT done, waiting for Assist) | Yellow |
| Speaking (TTS playing) | Green |
| Error | Red (2s then off) |

## Behavior

1. User presses and holds the button
2. LED turns blue; device streams mic audio to HA
3. User releases button; streaming stops
4. Faster-Whisper transcribes; HA Assist handles the intent
5. Piper synthesizes a response; Atom Echo plays it, LED turns green
6. Playback ends; LED turns off (idle)
7. On any error: LED turns red for 2 seconds, returns to idle

## Deliverables

- `atom-echo.yaml` — ready-to-flash ESPHome config
- Step-by-step HA addon setup instructions (in implementation plan)

## Out of Scope

- Wake word detection (can be added later)
- Multi-device relay / intercom (requires ESP32-S3)
- Cloud STT/TTS
