# Kitchen amp upgrade + terrace ESP32-S3 device

Status: design approved 2026-05-18

## Goal

Make the intercom physically usable for terrace ↔ kitchen calls:

1. **Kitchen (Atom Echo)** — keep the device intact but route audio out the Grove
   port into an external I2S amp + larger driver, so HA announcements and
   intercom playback are loud enough to hear over kitchen noise.
2. **Terrace (new build)** — purpose-built ESP32-S3 device with a stereo
   music-capable amp, two 5″ full-range drivers in ported cabinets, better
   mic, and weatherproof enclosure. Triple-role:
   - Outdoor music speaker (HA `media_player` target, 44.1 kHz stereo)
   - Intercom endpoint (PTT button + wake word)
   - Home Assistant voice-assistant satellite

   Mode is selected by which source is active: HA TTS / intercom playback /
   music stream all route through the same speaker; intercom and VA are
   switched by wake word (or button override).

This spec covers only the hardware swap and YAML scaffolding. It builds on top
of (and depends on) the wake-word + recorder-modes work in
[`2026-05-18-intercom-features-design.md`](./2026-05-18-intercom-features-design.md).

## Non-goals

- No firmware logic changes beyond pin remapping and adding the
  `voice_assistant` block. The wake-word + recorder-mode firmware comes from
  the intercom-features spec.
- No new server-side behavior. The addon, `recorder.h`, and `uploader.h`
  changes are owned by the intercom-features spec.
- No disassembly of the M5 Atom Echo. Internal speaker stays in place, just
  receives silence (no I2S data on its DIN pin).
- No far-field / beamforming mic array. INMP441 is sufficient since the user
  is close to the mic at trigger time (PTT or wake word).
- No battery operation. Both devices are mains-powered.
- No subwoofer / dedicated tweeter. Stereo full-range drivers handle the full
  band. A 2-way build is a future option, out of scope for v1.
- Kitchen Atom Echo is **not** a music speaker. NS4168's 3W ceiling + a 3″
  driver caps it at "background TTS / intercom playback" quality. The terrace
  device is the music-capable one.

## Architecture

```
┌─────────────────────────────────┐     ┌────────────────────────────────────┐
│  Kitchen — Atom Echo (kept)     │     │  Terrace — ESP32-S3 (new, stereo)  │
│                                 │     │                                    │
│  ESP32 ── I2S ─┬─ GPIO22 (silent)│     │  ESP32-S3 ── I2S out (stereo) ──►  │
│                │  internal NS4168│     │              │                    │
│                │  + tiny driver  │     │              ▼                    │
│                │  (left in place)│     │       PCM5102 I²S DAC             │
│                └─ GPIO26 ── DIN  │     │              │                    │
│                   (Grove pin)    │     │     L/R analog out (line level)   │
│                        ↓         │     │              ▼                    │
│                  MAX98357A       │     │       TPA3116D2 amp (~30 W × 2)   │
│                        ↓         │     │              │                    │
│                  3″ DMA70-4 in   │     │      ┌───────┴───────┐            │
│                  small box       │     │      ▼               ▼            │
│                                  │     │   Visaton FRS 8   Visaton FRS 8   │
│  PDM mic — kept (internal)      │     │   3.3″ L          3.3″ R           │
│  Button — kept (GPIO39)         │     │   (ported box)    (ported box)     │
│  WS2812 LED — kept (GPIO27)     │     │                                    │
│                                  │     │   ESP32-S3 ── I2S in ── INMP441   │
│                                  │     │   Button + WS2812 status          │
│                                  │     │   12 V PSU → buck → 5 V logic     │
│                                  │     │   IP54 electronics enclosure       │
└─────────────────────────────────┘     └────────────────────────────────────┘
                │                                       │
                └───────── both POST to ────────────────┘
                          http://homeassistant.local:9999/intercom
                          (existing addon — unchanged)

           both expose voice_assistant satellite to HA Assist
           wake-word A → intercom recording (POST to addon)
           wake-word B → voice_assistant flow
           button     → intercom recording (PTT override)
```

## Device 1 — Kitchen Atom Echo upgrade

### Hardware BOM (~$15)

| Part | Notes |
|------|-------|
| Atom Echo (owned) | Not disassembled |
| MAX98357A breakout (Adafruit or AliExpress clone) | I2S Class-D, 3.2 W @ 4 Ω |
| Dayton Audio DMA70-4 (3″) | Or any 3″ full-range 4 Ω driver, ≥ 86 dB sensitivity |
| Small sealed/ported enclosure | 3D-printed or cheap project box, ~0.2 L |
| Grove cable (cut one end) + dupont wires | For the GPIO19 / GPIO33 taps |

### Wiring

| MAX98357A pin | Source |
|---------------|--------|
| VIN           | Grove `5V` |
| GND           | Grove `GND` |
| BCLK          | GPIO19 (side header — shared with existing I2S bus) |
| LRC           | GPIO33 (side header — shared) |
| DIN           | GPIO26 (Grove yellow) |
| GAIN          | Float (default 9 dB) or tie to GND for 12 dB |
| SD            | Leave open (always-on) |

Internal NS4168 keeps receiving BCLK and LRCLK but no data, so it idles silent.
No need to mute it explicitly.

### YAML changes (`atom-echo.yaml`)

Single line — the I2S DOUT pin moves from the internal amp to the Grove pin:

```yaml
speaker:
  - platform: i2s_audio
    id: atom_speaker
    i2s_audio_id: i2s_out
    i2s_dout_pin: GPIO26     # was: GPIO22
    dac_type: external
    bits_per_sample: 16bit
    sample_rate: 16000
```

Everything else (`media_player`, `microphone`, `binary_sensor`, status LED,
recorder/uploader glue) is unchanged.

The wake-word + voice-assistant additions are pulled in from the
intercom-features spec — they touch the same file but are owned by that spec.

## Device 2 — Terrace ESP32-S3 build (stereo music-capable)

### Hardware BOM (~$130)

| Part | Notes |
|------|-------|
| ESP32-S3-DevKitC-1 (N8R8 or N16R8) | Dual I2S, USB-native, ≥ 8 MB PSRAM — needed for 44.1 kHz stereo audio buffering |
| PCM5102 (or PCM5102A) I²S DAC breakout | Stereo 24-bit DAC. Hardware-mode (no I²C config). `SCK` pin tied to GND on-board enables internal PLL — no external MCLK needed. |
| TPA3116D2 stereo amp board (analog input, 12–24 V) | Class-D, ~30 W × 2 at 12 V into 4 Ω. **Avoid Bluetooth / DSP / SD-card variants** — must be plain analog-input. |
| 2× Visaton FRS 8 (3.3″, 87 dB, 4 Ω) | Compact full-range. Good voice-band + usable music bass with port tuning. Roll-off ~120 Hz; punchy mids. |
| 2× ported MDF/3D-printed enclosures | ~0.7 L per side, port tuned ~100 Hz. Compact, fit easily on a terrace shelf or under-eave mount. |
| 12 V 3 A barrel-jack PSU | TPA3116 PVDD rail |
| Buck converter 12 V → 5 V (MP1584 module, ~$2) | Feeds ESP32-S3 + INMP441 + LED |
| Short twisted analog cable (DAC → amp) | A few cm; keep short, twist with ground to reject noise |
| INMP441 I2S MEMS mic breakout | Omni, 24-bit, ~$3 |
| Foam windscreen | Cut from cheap headset cover |
| Momentary tactile button | 12 mm panel-mount |
| WS2812 RGB LED | Single, or short strip |
| IP54 electronics enclosure | ~150 × 100 × 60 mm — holds ESP32 + DAC + amp + buck + connectors. Separate from the speaker cabinets. |
| Outdoor-rated speaker grille cloth + mounting hardware | Glued/clamped behind routed cutout on each cabinet |
| Strain-relieved 12 V mains entry + speaker terminals | Outdoor electrical hygiene |

### Pin assignments (suggested)

| Function                  | Pin    |
|---------------------------|--------|
| I2S out BCLK (to PCM5102) | GPIO5  |
| I2S out LRCLK             | GPIO6  |
| I2S out DOUT (stereo PCM) | GPIO7  |
| I2S in BCLK (from INMP441) | GPIO15 |
| I2S in LRCLK              | GPIO16 |
| I2S in DIN                | GPIO17 |
| Button                    | GPIO9 (boot-safe input with pull-up) |
| WS2812 data               | GPIO8  |

PCM5102 in hardware mode needs no I²C config and no MCLK from the ESP32 (its
`SCK` pin is tied to GND on the breakout, enabling internal PLL). TPA3116D2
is analog-only — no MCU-side wiring beyond the audio cable from the DAC's
L/R outputs.

These are starting points — final pin choice is done at wiring time depending
on the specific S3 board's silkscreen and which strapping pins are exposed.

### YAML scaffolding (`intercom-s3.yaml`)

Reuses the same `recorder.h` / `uploader.h` glue. Structure:

```yaml
esphome:
  name: intercom-terrace
  includes: [recorder.h, uploader.h]
  on_boot: [ ...same callbacks as atom-echo.yaml... ]

esp32:
  board: esp32-s3-devkitc-1
  framework: { type: esp-idf }

i2s_audio:
  - id: i2s_in     # mic
  - id: i2s_out    # amp

microphone:
  - platform: i2s_audio
    id: terrace_mic
    i2s_audio_id: i2s_in
    i2s_din_pin: GPIO17
    i2s_bclk_pin: GPIO15
    i2s_lrclk_pin: GPIO16
    adc_type: external
    pdm: false             # INMP441 is standard I2S, not PDM
    sample_rate: 16000

speaker:
  - platform: i2s_audio
    id: terrace_speaker
    i2s_audio_id: i2s_out
    i2s_dout_pin: GPIO7
    i2s_bclk_pin: GPIO5
    i2s_lrclk_pin: GPIO6
    dac_type: external
    bits_per_sample: 16bit
    sample_rate: 44100        # music-grade; downmixed for 16 kHz TTS/intercom
    channel: stereo           # both L+R channels active

media_player:
  - platform: speaker
    id: terrace_player
    name: "Terrace Player"
    buffer_size: 65536        # bigger buffer for music streams; PSRAM-backed
    media_pipeline:
      speaker: terrace_speaker
      format: FLAC            # for streamed music
    announcement_pipeline:
      speaker: terrace_speaker
      format: WAV

# PCM5102 + TPA3116D2 need no boot config — analog signal path after the DAC.
# Volume control is software-side in ESPHome (the TPA3116's onboard
# potentiometer is set to ~80% once during install and left alone).

light:
  - platform: esp32_rmt_led_strip
    chipset: WS2812
    pin: GPIO8
    num_leds: 1
    name: "Terrace LED"
    id: status_led

binary_sensor:
  - platform: gpio
    pin: { number: GPIO9, inverted: true, mode: { input: true, pullup: true } }
    name: "Terrace Button"
    on_press:   # same PTT flow as atom-echo.yaml
    on_release: # same

voice_assistant:
  microphone: terrace_mic
  speaker: terrace_speaker
  # rest mirrors listen_and_answer.yaml

micro_wake_word:
  models:
    - model: <intercom-phrase>      # → recorder_start_vad() + uploader_start()
    - model: <voice-assistant-phrase>  # → voice_assistant.start()
  on_wake_word_detected:
    # branch on detected phrase id; two if-else clauses
```

The dual-wake-word handler logic is the same on both devices; it just sits in
two YAML files for now. If duplication grows, factor into a shared package
later.

## Wake-word split

Both devices run two `micro_wake_word` models concurrently and dispatch on
which model fired:

```yaml
on_wake_word_detected:
  - if:
      condition: 'lambda: return id(...).wake_word == "<intercom-phrase>";'
      then:
        - if:
            condition: 'lambda: return uploader_is_uploading() || recorder_is_active();'
            then: [logger.log: "ignored — busy"]
            else:
              - light.turn_on: { id: status_led, blue: 100% }
              - lambda: |-
                  recorder_start_vad();
                  uploader_start(...);
      else:
        - voice_assistant.start
```

**RAM caveat for Atom Echo (ESP32-classic):** running two micro_wake_word
models is right at the edge of the original ESP32's RAM. If it doesn't fit,
the fallback is:

- Kitchen Atom Echo: 1 wake word (intercom) + button still works as PTT
  override; voice assistant on this device is triggered from HA only (no local
  wake word). Voice assistant still functions as a satellite — HA can push
  TTS to it; it just can't be locally-wake-worded.
- Terrace S3: 2 wake words (intercom + VA). No RAM constraint.

Decide at flash time after measuring `Free internal heap` on the Atom with
both models loaded.

## Cost summary

| Item | Kitchen | Terrace |
|------|---------|---------|
| MCU | $0 (owned Atom Echo) | $8 (ESP32-S3 DevKit-C) |
| DAC | – | $4 (PCM5102) |
| Amp | $4 (MAX98357A) | $7 (TPA3116D2 stereo) |
| Drivers | $20 (DMA70-4 ×1) | $50 (Visaton FRS 8 ×2) |
| PSU | $0 (USB-C) | $10 (12 V 3 A) + $2 (buck) |
| Speaker enclosures | $5 (small) | $15 (2× 0.7 L ported MDF / printed) |
| Mic | $0 (kept) | $3 (INMP441) |
| Button + LED | $0 (kept) | $2 |
| Electronics enclosure | (combined w/ above) | $20 (IP54) |
| Grille cloth, terminals, strain relief | – | $10 |
| Misc (wires, foam, twisted analog cable) | $3 | $5 |
| **Total** | **~$32** | **~$136** |

## Open items before implementation

- **Wake-word phrases:** pick two compatible prebuilt micro_wake_word models
  (one for intercom, one for VA). Candidates: "okay nabu", "computer",
  "hey jarvis", "alexa". One per role.
- **Atom Echo RAM check:** verify two wake-word models fit; if not, fall back
  to the single-model plan documented above.
- **Enclosure design:** Confirm 0.7 L ported volume, port tuning (~100 Hz),
  and whether the two cabinets are physically separate (better stereo image)
  or combined into one box (easier to mount). FRS 8 is forgiving — even a
  sealed 0.5 L box sounds OK for voice-plus-light-music.
- **PCM5102 board variant check:** confirm the breakout that arrives has its
  `SCK` pin tied to GND on the PCB (look for a solder bridge near the SCK
  pin). If not, either solder one yourself or wire MCLK from a fourth ESP32
  GPIO. 99% of common Aliexpress boards have it pre-bridged.
- **TPA3116D2 board variant check:** must be the **plain analog-input
  stereo** version. Reject Bluetooth, DSP, ADAU, or SD-card variants — their
  input is hijacked by the extra module.
- **TPA3116D2 input gain pot:** set to ~80 % during install and leave it.
  Final volume control happens in ESPHome software via the speaker's
  `volume` parameter.
- **ESPHome stereo I2S config:** verify `channel: stereo` works on
  ESPHome's i2s_audio speaker platform with the chosen ESPHome version, and
  that 44.1 kHz stereo playback is stable end-to-end through `media_pipeline`
  with a real Spotify-via-Music-Assistant or local-file source. Possible
  fallback: stereo via two separate `speaker` entries (one per channel).
- **Pin remap on S3 board:** confirm chosen GPIOs are not strapping pins on
  the specific ESP32-S3 board variant the user buys (N8R8 vs N16R8 vs
  WROOM-1U etc.); the pin table above is a starting point.
- **Terrace power & weather:** 12 V mains via outdoor-rated cable + IP54
  strain relief. Confirm the speaker cabinet itself is rain-protected (under
  an eave or with a downward-firing baffle), as full waterproofing of a
  paper-cone driver is not realistic.

## Dependencies

- This spec's YAML changes assume the **firmware refactor from
  [`2026-05-18-intercom-features-design.md`](./2026-05-18-intercom-features-design.md)
  is already merged** (mic always-on, `recorder_start_vad()`, `REC_HOLD` /
  `REC_VAD` modes, wake-word handler in `atom-echo.yaml`).
- Server-side behavior (chimes, aliases, ducking, talkback) is owned by that
  spec; no changes needed here.

**Plan scope decision:** this work has its own implementation plan, separate
from the intercom-features plan. The implementation plan for this spec gates
on the intercom-features firmware (wake-word handler, `recorder_start_vad`,
mic always-on) being merged first — the hardware swap and S3 YAML
scaffolding here have no useful behavior without it.
