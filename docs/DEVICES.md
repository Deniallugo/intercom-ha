# Intercom System — Current State

A three-device PTT intercom + voice satellite running on Home Assistant.
The kitchen Atom Echo has one MAX98357A amp wired to its exposed I²S header
pads, driving a larger speaker in place of the disconnected internal one. The
terrace VoiceS3R has two MAX98357A amps wired to its free GPIOs, both playing
the same mono mix into a pair of larger drivers (dual mono). Voice S3 is a bare
ESP32-S3 built from discrete parts — PCM5102A line-out, INMP441 mic, one button —
and is the only one whose mic and speaker sit on separate I²S peripherals.

---

## Devices

### Kitchen — M5Stack Atom Echo + external amp

| Item | Detail |
|---|---|
| MCU | ESP32 classic, ~520 KB SRAM, no PSRAM |
| Mic | Internal PDM (SPM1423) on GPIO23 |
| Internal speaker | Internal NS4168 amp → built-in 0.5 W speaker on GPIO22 (disconnected — replaced by external amp) |
| External amp | 1× MAX98357A as a passive parallel I²S listener on G19/G33/G22 (+12 dB) |
| External speaker | One 4 Ω driver on the MAX98357A `+ / −` output |
| Button | Built-in tactile on GPIO39 (active LOW) |
| LED | Built-in SK6812 RGB on GPIO27 |
| Power | USB-C |

### Terrace — M5Stack ATOM Echo S3R / VoiceS3R + two amps (dual mono)

| Item | Detail |
|---|---|
| MCU | ESP32-S3, 8 MB octal PSRAM |
| Codec | ES8311 on internal I²C (SDA G45, SCL G0) |
| Mic | Built-in MEMS via codec ADC (DSDIN G48, ASDOUT G4) |
| Internal speaker | Internal NS4150 amp on G18, 1 W speaker (kept as fallback, mutable via HA switch) |
| External amps | 2× MAX98357A on second I²S bus (G5/G6/G7), both decoding the same mono slot |
| External speakers | Two drivers, one per MAX98357A `+ / −` output, both playing the same mono mix |
| Button | Built-in tactile on G41 (active LOW) |
| Power | USB-C |

> The terrace 3D-printed case accepts an optional **+20 mm depth spacer**
> (`part="spacer"`) at the rear parting line to give the drivers more sealed air
> volume; it needs 4× M3×35 screws and foam tape on the two new seams. See
> `hardware/terrace-case/README.md`.

### Voice S3 — bare ESP32-S3 + PCM5102A line-out + INMP441

| Item | Detail |
|---|---|
| MCU | Bare ESP32-S3 devkit, N16R8 (16 MB flash, 8 MB octal PSRAM @ 40 MHz) |
| DAC | PCM5102A on I²S bus 0 (BCK G5, LCK G6, DIN G7) → 3.5 mm stereo jack |
| Mic | INMP441 MEMS on I²S bus 1 (SCK G10, WS G11, SD G12), left slot |
| Amplification | None on board — the jack feeds a powered speaker or an external amp |
| Button | One momentary switch on G4 to GND (active LOW, internal pull-up) |
| Power | USB-C |

Unlike the other two, capture and playback run on **two separate I²S
peripherals**, so the mic never has to yield the bus to the speaker: the wake
word keeps listening through music and TTS, and barge-in works. That removes the
`on_announcement` / `on_idle` wake-word juggling that intercom-s3 needs.

The button does two jobs, split by hold time — tap (< 1.2 s) starts Assist
without the wake word, hold (≥ 1.2 s) records and broadcasts over the intercom
for as long as you hold it.

> The 3D-printed enclosure is a **desk puck**, 96 × 96 × 34 mm — modelled on the Home
> Assistant Voice PE, slightly broader because a 64 mm-deep devkit has to sit centred
> between four full-depth corner bosses. Driver and grille are replaced by the
> 3.5 mm line-out — button and mic port on top, the devkit's USB-C out the back, and the
> PCM5102A board's **own 3.5 mm socket** used straight through the side wall (so
> `LROUT`/`RROUT` need no wiring and there is no panel-mount jack). The wall is
> locally thinned to 1.2 mm behind that socket, or a plug loses too much of its
> 14 mm barrel to the wall to seat. Both boards sit in friction pockets on the base
> plate — the DAC has no mounting holes.
> See `hardware/voice-case/README.md`.

---

## Capabilities

| Capability | Kitchen | Terrace | Voice S3 |
|---|---|---|---|
| Button-PTT intercom (record → POST to addon → playback elsewhere) | ✓ | ✓ | ✓ (hold) |
| Wake-word + HA Assist (STT, intent, TTS reply) | — | ✓ (`okay nabu`) | ✓ (`okay nabu`, or tap) |
| Music streaming from Spotify via Music Assistant | — | ✓ | ✓ (stereo) |
| HA TTS announcements (`media_player.play_media`) | ✓ | ✓ | ✓ |
| Text announcements (UI + automation TTS) | ✓ | ✓ | ✓ |
| External larger-driver speakers | ✓ (1× MAX98357A) | ✓ (2× MAX98357A, dual mono) | ✓ (line-out to any amp) |
| Listens while playing (no shared-bus stall) | — | — | ✓ |
| Internal speaker fallback | — (disconnected) | ✓ (HA-toggleable switch) |
| Software mic gain | +6 dB (recorder.h) | n/a (codec PGA at 36 dB) |
| DMA watchdog auto-reboot | ✓ | — |

---

## Audio pipeline (VoiceS3R)

```
HA / Music Assistant ──► media_player.intercom_s3_player
                                     │
                          ┌──────────┴───────────┐
                          ▼                      ▼
                  announcement_pipeline    media_pipeline
                          │                      │
                  s3_announcement_src     s3_media_src
                          │                      │
                          └──────► s3_mixer ─────┘
                                     │
                                     ▼
                          s3_speaker_ext (I²S bus 2, G5/G6/G7)
                                     │
                                     ▼
                       2× MAX98357A → 2 drivers (dual mono, same mix)
```

The mic on the separate internal I²S bus (ES8311 codec) feeds:
- `micro_wake_word` for wake-word detection
- `voice_assistant` for HA Assist
- Custom `recorder.h` for PTT intercom upload to the HA addon

---

## Wiring

### Kitchen — Atom Echo + external MAX98357A

One MAX98357A is wired as a passive parallel listener on the Atom Echo's
existing I²S-out signals, exposed on the bottom headers. It decodes the same
stream the internal NS4168 receives — ESPHome is unaware of it, so there is
**no YAML change**. The internal 0.5 W speaker is physically disconnected, so
only the external driver plays. (M5Stack labels G19/G22/G23/G33 "reserved for
internal audio"; tapping them as a high-impedance listener is the same
technique the terrace uses — it does not repurpose the pins.)

| GPIO | Function |
|---|---|
| GPIO33 | I²S LRCLK (mic + amps) — also feeds MAX98357A LRC |
| GPIO19 | I²S BCLK (shared) — also feeds MAX98357A BCLK |
| GPIO23 | PDM mic data in |
| GPIO22 | I²S DOUT → (internal NS4168, disconnected) + MAX98357A DIN |
| GPIO39 | Button (active LOW, internal pull-up) |
| GPIO27 | SK6812 RGB LED data |

#### External MAX98357A wiring

| MAX98357A pin | Atom Echo pin | Header |
|---|---|---|
| VIN | 5V | bottom header (`G21 / G25 / 5V / GND` side) |
| GND | GND | bottom header |
| BCLK | G19 | `3V3 / G22 / G19 / G23 / G33` side |
| LRC | G33 | same side |
| DIN | G22 | same side |
| GAIN | bridged to GND (bare wire) | +12 dB |
| SD | left floating | on-board pull-up = enabled, mono-average |
| `+ / −` | one 4 Ω driver | — |

```
       M5Stack Atom Echo                  MAX98357A (×1)
       ┌─────────────────────┐            ┌──────────────────┐
       │ 3V3 G22 G19 G23 G33 │            │                  │
       │      │   │      │    │            │  GAIN ──┐        │
       │      │   │      │    └───────────►│  LRC    │(GAIN→GND
       │      │   └──────┼────────────────►│  BCLK   │  = +12 dB)
       │      └──────────┼────────────────►│  DIN    │        │
       │                 └────────────────►│  GND ───┘        │
       │ G21 G25  5V  GND│                 │                  │
       │           │   │ │       ┌────────►│  VIN             │
       │           └───┼─┼───────┘         │                  │
       │               └─┼───────────────►│  GND  (power)     │
       │  USB-C in       │                 │   +  ────────────┼── + driver
       └─────────────────┘                 │   −  ────────────┼── − driver
                                            └──────────────────┘
   Internal NS4168 speaker: disconnected (NS4168 has no enable pin).
```

### Terrace — VoiceS3R

#### Internal connections (hard-wired inside the case — not user-accessible)

| GPIO | Function |
|---|---|
| GPIO3 | I²S LRCK to/from ES8311 codec |
| GPIO17 | I²S SCLK to/from ES8311 codec |
| GPIO11 | I²S MCLK to ES8311 codec |
| GPIO48 | DSDIN — codec DAC input (speaker direction) |
| GPIO4 | ASDOUT — codec ADC output (mic direction) |
| GPIO18 | NS4150 amp enable (internal speaker on/off) |
| GPIO45 | I²C SDA — codec config |
| GPIO0 | I²C SCL — codec config |
| GPIO41 | Built-in button |

These signals are not broken out on the side headers. Audio I/O to/from
the codec happens inside the M5Stack module.

#### External MAX98357A wiring (the user-facing side)

Both MAX98357A boards are wired **identically in parallel** to the same
side-header pins (I²S is a broadcast bus). Per board:

| MAX98357A pin | VoiceS3R pin | Header position |
|---|---|---|
| **VIN** | 5V | Top header (4-pin row) |
| **GND** | G (GND) | Top header |
| **BCLK** | G5 | Bottom header (4-pin row, leftmost when label is right-side up) |
| **LRC** | G6 | Bottom header |
| **DIN** | G7 | Bottom header |
| **GAIN** | bridged to GND | (+12 dB. Default floating = 9 dB; a bare wire to GND is +12 dB. NB: 15 dB needs a 100 kΩ resistor to GND, *not* a bare wire.) |
| **SD** | not connected | Left floating — the board's pull-up defaults it to enabled/left. |
| **`+ / −` outputs** | its own driver `+ / −` | one driver per board |

Both boards run in the **left/mono slot** (SD high via the board pull-up) and
`channel: mono` feeds the mono mix, so the two drivers play the same audio
(dual mono).

**SD wiring:** left **unconnected**. These boards have a working SD pull-up
(verified: they run fine with SD unwired), so SD floats to enabled/left and the
amps are always on. There is no software mute — if you want HA on/off later,
wire both SD pins to a spare GPIO and add a `gpio` switch. (Some cheap clones
lack the pull-up and float into shutdown — these aren't those.)

```
       M5Stack ATOM Echo S3R           MAX98357A (×2, wired identically)
       ┌─────────────────────┐         ┌──────────────────┐
       │  Top header:        │         │                  │
       │  [G39][G38][5V][G]  │   ┌────►│  VIN             │
       │               │  │  │   │     │                  │
       │               │  └──┼───┼────►│  GND             │
       │               └─────┼───┘     │                  │
       │                     │         │  GAIN ──┐        │
       │  Bottom header:     │         │         │ (wire GAIN → GND
       │  [G5][G6][G7][G8]   │         │  GND ───┘   = +12 dB)
       │   │   │   │         │         │                  │
       │   │   │   │         │         │  SD   (n/c — board│
       │   │   │   │         │         │        pull-up = on)
       │   └───┼───┼─────────┼────────►│  BCLK            │
       │       └───┼─────────┼────────►│  LRC             │
       │           └─────────┼────────►│  DIN             │
       │                     │         │                  │
       │  Port A (Grove):    │         │   +  ────────────┼── + speaker
       │  [G1][G2][5V][GND]  │         │   −  ────────────┼── − speaker
       │   (G8 now free)     │         └──────────────────┘
       │  USB-C in           │
       └─────────────────────┘         Per-board wiring:
                                          • GAIN → GND = +12 dB (float = 9 dB;
                                                         15 dB needs 100 kΩ)
                                          • SD   = n/c (board pull-up keeps it on)
```

The diagram shows one board; the **second MAX98357A is wired identically** to
the same G5/G6/G7 + 5V/GND, with its own driver on its `+ / −` outputs.

#### Optional: PCM5100 3.5 mm line-out (future add-on)

The MAX98357As above are self-contained — they decode the I²S stream and drive
the in-case speakers with nothing else wired. A **PCM5100** line-level DAC can
be bolted on later purely to add a **3.5 mm jack**, without disturbing them.

I²S is a broadcast bus, so the PCM5100 is wired as a **parallel listener** — tap
the same three signals the MAX already uses (no new bus, no I²C):

| PCM5100 pin | VoiceS3R pin | Note |
|---|---|---|
| BCK | G5 | shared with MAX BCLK |
| LCK (LRCK) | G6 | shared with MAX LRC |
| DIN | G7 | shared with MAX DIN |
| VIN / GND | 5V / G | power |
| **SCK → GND** | — | bus 2 has no MCLK; this makes the PCM5100 derive its clock from BCK (else: silence) |
| **XSMT → 3V3** | — | un-mute (floating/low = silent) |
| FLT / DEMP / FMT | — | leave on board defaults (I²S, 16-bit) |

Analog out is line level, centered on AGND (the chip's charge pump means **no
DC-blocking coupling caps needed**) — wire straight to the jack:

| PCM5100 pin | 3.5 mm jack |
|---|---|
| LOUT | tip (left) |
| ROUT | ring (right) |
| AGND | sleeve (ground) |

The PCM5100 plays the **same stream** as the in-case speakers. To have the jack
live while the speakers are silent:

- You **can't** mute in software — all chips share the G7 data line, and the
  current build leaves the MAX SD pins floating (always on).
- To silence the speakers while keeping the jack live, you'd need to control SD.
  For **dual mono**, wire both MAX SD pins to a spare GPIO (e.g. G8) + a `gpio`
  switch — one 3.3 V line drives both (same left/mono slot). For **L/R stereo**
  (right board biased ~1 V on SD) don't drive SD from a GPIO — SD also selects
  L/R; power-gate the boards with a MOSFET instead.

#### What the silkscreen labels mean

The center sticker on the VoiceS3R has labels like `LRCK: G3`, `SCLK: G17`,
`DSDIN: G48` — these document **internal** wiring (which GPIO controls each
audio function inside the case). The actual physical pins on the side
headers are labeled with G-numbers (`G5`, `G6`, `G7`, `G8`, etc.) and those
are what you wire to.

The audio I²S pins from the legend (G3, G17, G11, G48, G4) are **not** broken
out — they go straight to the internal codec. That's why we use a **second**
I²S peripheral on free GPIOs (G5/G6/G7) for the external amps.

### Voice S3 — bare ESP32-S3

Everything is discrete here, so every wire is yours to run. The two I²S buses
are deliberately kept separate (see *Key technical decisions*).

#### PCM5102A DAC → 3.5 mm jack (I²S bus 0)

| PCM5102A pin | ESP32-S3 | Note |
|---|---|---|
| **VIN** | 5V (or 3V3) | The GY-PCM5102 breakout regulates on board |
| **GND** | GND | |
| **BCK** | G5 | Bit clock |
| **LCK** | G6 | Word/LR clock |
| **DIN** | G7 | Data in |
| **SCK** | **GND** | Forces the internal PLL to make MCLK — this is why no `i2s_mclk_pin` is declared. Left floating, the DAC is silent or noisy. |
| **FMT** | GND | I²S format (not left-justified) |
| **XMT** | 3V3 | Un-mute; tie high or the output stays soft-muted |
| **FLT / DEMP** | GND | Normal filter, de-emphasis off |
| **LROUT / RROUT** | jack tip / ring | Line level, already DC-blocked on the breakout |

The jack is **line level**, not speaker level — it needs a powered speaker or an
amp downstream. Jack sleeve → GND.

#### INMP441 mic (I²S bus 1)

| INMP441 pin | ESP32-S3 | Note |
|---|---|---|
| **VDD** | 3V3 | 3.3 V only — not 5 V tolerant |
| **GND** | GND | |
| **SCK** | G10 | Bit clock |
| **WS** | G11 | Word select |
| **SD** | G12 | Data out → ESP32 data in |
| **L/R** | **GND** | Selects the LEFT slot, matching `channel: left`. Leave it floating and the slot assignment is undefined. |

The INMP441 is 24-bit left-justified in a 32-bit slot, so the mic is configured
`bits_per_sample: 32bit`. Assist and the wake word get 16-bit via their
microphone sources; the intercom's raw data callback converts itself.

**It needs no gain.** Measured from a real capture, speech peaks at 5404/32767
(≈ −15.7 dBFS) with `gain_factor: 1` and a plain `>> 16` on the intercom path.
`use_apll: true` gives the RX a lower-jitter clock.

#### Bring-up notes — how this mic fails

Debugging one of these is mostly about telling four different failures apart,
and the raw sample words distinguish them faster than any level meter:

| Symptom in the raw 32-bit words | Cause |
|---|---|
| Exactly `00000000` forever, no noise floor | Nothing arriving — dead wire, or the mic isn't clocked |
| Peak pinned at `32768` (`0x8000`) while the mean stays near 0 | Floating data line latched at the MSB — the mic goes high-Z outside its slot |
| Long runs of zeros interrupted by full-scale bursts | Intermittent connection; the bursts are contact noise, not audio |
| Smooth ramps of a constant step, ~4 Hz, heavily clipped | Sub-audio wander, usually too much digital gain applied to a DC-ish signal |

A real capture settles it where statistics mislead: **speech produces hundreds
to thousands of zero-crossings per second.** Anything under ~50/s is not sound,
whatever the level looks like.

Getting one takes about a minute — `tools/mic-capture.py` stands in for the
add-on's `/intercom` endpoint, writes a WAV, and prints the verdict:

```bash
python3 tools/mic-capture.py            # on any machine on the LAN
# then set intercom_url: "http://<that-machine>:9999/intercom", flash,
# and press the device's "Mic test recording" button in Home Assistant
```

```
peak 5404  mean 824  dc -7
clipped 0.00%   impossible jumps 0
zero crossings 564/s
noise floor 699  loudest 1074  SNR ~4 dB
--> looks like real audio.
```

It distinguishes SILENT / GLITCHING / NOT AUDIO / CLIPPING / real audio, which
is exactly the set of failures above. The `Mic test recording` button is a
permanent diagnostic entity on the device — no PTT button needs to be wired.

A healthy INMP441 should show **40–60 dB SNR**. If it is closer to 5 dB with
energy piled into 3–8 kHz, that is broadband hiss from the wiring, not the
capsule: add 100 nF across VDD–GND at the module, shorten SD/SCK/WS, run the
mic's ground alongside the data line, and add 10 kΩ from SD to GND so the line
is defined while the mic isn't driving it.

#### Button

| Pin | Wiring |
|---|---|
| **G4** | one leg of a momentary switch; other leg to **GND** (internal pull-up, active LOW) |

#### Pins to avoid on this board

G26–G32 are the SPI flash and **G33–G37 the octal PSRAM** — using any of them
kills the board's memory. G19/G20 are USB, G43/G44 are UART0, and G0/G3/G45/G46
are strapping pins. The G4–G12 block used here is clear of all of that.

---

## Repo layout

```
intercom/
├── devices/
│   ├── atom-echo.yaml              # Kitchen Atom Echo (PTT intercom + DMA watchdog)
│   ├── listen_and_answer.yaml      # Atom Echo VA variant
│   ├── intercom-s3.yaml            # Terrace VoiceS3R (intercom + wake-word + music)
│   ├── intercom-s3-minimal.yaml    # Bare-boot diagnostic config
│   ├── speaker-s3.yaml             # Bare S3 + PCM5102A — playback only, no mic
│   ├── voice-s3.yaml               # Bare S3 + PCM5102A + INMP441 + button
│   ├── secrets-atom.yaml           # Atom Echo's API key (gitignored)
│   ├── secrets-s3.yaml             # VoiceS3R's API key (gitignored)
│   └── secrets-voice.yaml          # Voice S3's API key (gitignored)
├── include/
│   ├── recorder.h                  # Shared C++ — PCM ring buffer + software gain
│   └── uploader.h                  # Shared C++ — chunked HTTP POST to addon
├── packages/
│   └── base.yaml                   # Shared logger/api/ota/wifi/captive_portal
├── intercom-addon/                 # HA addon — receives POSTs, broadcasts to targets
├── flash.sh                        # `./flash.sh <device>` helper
└── docs/superpowers/               # Specs and plans
```

---

## Key technical decisions

- **Per-device secrets** — each device loads its own `secrets-<name>.yaml`
  via packages, so kitchen and terrace have separate HA API keys.
- **Shared C++ glue** — `recorder.h` and `uploader.h` work for both devices
  unchanged; software gain in `recorder.h` boosts Atom Echo's PDM mic +6 dB
  (`recorder_set_gain(2, 1)`).
- **Two I²S buses on the VoiceS3R** — Bus 1 (internal, hard-wired) handles
  the ES8311 codec for mic; Bus 2 (G5/G6/G7) handles the external MAX98357A
  amps. They run independently so wake-word listening doesn't conflict with
  external playback.
- **Two I²S *peripherals* on Voice S3** — the S3 has two I²S controllers, and
  Voice S3 spends both: bus 0 drives the PCM5102A, bus 1 reads the INMP441. Not
  an optimisation — it's what lets the mic stay live during playback. A single
  full-duplex bus (the VoiceS3R's situation) forces mic and DAC onto one clock,
  which is why intercom-s3 has to stop the wake word and wait for the mic to
  release the bus before every announcement.
- **INMP441 read as 32-bit, converted twice over** — the part is 24-bit
  left-justified in a 32-bit slot. `micro_wake_word` and `voice_assistant` each
  take a *microphone source*, which down-converts to the 16 bits they require;
  the intercom's raw `add_data_callback` gets native 32-bit frames and shifts
  them itself. Feeding raw frames to `recorder.h` unshifted yields noise.
- **The mic is reference-counted** — `Microphone::start()` / `stop()` take and
  return listener slots, and the driver only stops when all are returned. So the
  intercom's hold path takes its own slot before `micro_wake_word.stop`, and
  re-arms the wake word *before* returning it — the count never hits zero, so the
  I²S driver never tears down mid-recording.
- **One button, split by hold time** — tap (< 1.2 s) starts Assist, hold
  (≥ 1.2 s) records the intercom. A `restart`-mode script started on press and
  cancelled on release is what distinguishes them; a `bool` global remembers
  which mode the release belongs to.
- **Dual mono on two MAX98357A** — both amps are passive parallel listeners on
  Bus 2 (I²S is a broadcast), both decoding the same left/mono slot, so adding
  the second board is wiring-only (no YAML change). GAIN → GND on both = +12 dB.
- **ES8311 codec mic gain at 36 dB** — compromise between wake-word
  detectability (default 42 dB clipped intercom recordings) and clean PTT
  recordings (18 dB was too quiet for wake word).
- **Mixer speaker** — gives `media_player` two virtual source endpoints
  (`s3_announcement_src`, `s3_media_src`) so TTS announcements and music
  streaming can coexist on one physical speaker.
- **DMA watchdog on Atom Echo** — auto-reboot when DMA-capable heap
  fragments below threshold, preventing the "speaker wedged" failure mode
  on the no-PSRAM ESP32.
- **`flash.sh` helper** — single-command flash across devices:
  `./flash.sh atom-echo`, `./flash.sh intercom-s3`, etc.
- **MAX98357A SD left floating** — these boards have a working SD pull-up
  (verified: they run with SD unwired), so they default to enabled/left and the
  amps are always on. No GPIO, no software mute (G8 stays free). (Bring-up
  lesson: GAIN→GND killing *all* output traced to a faulty board, not the wiring
  — a healthy GAIN pin is per-amp and can't silence the other amp. See
  `docs/superpowers/specs/2026-06-01-terrace-dual-amp-design.md`.)

---

## External integrations

- **HA Voice Assistant** — VoiceS3R registered as a satellite, full
  STT / intent / TTS pipeline. Wake word `okay nabu` triggers HA Assist;
  TTS reply plays back through the external speaker via the mixer's
  announcement pipeline.
- **Music Assistant** — bridge from Spotify Premium to the ESPHome
  `media_player`. Routes through the mixer's media pipeline with a 1 MB
  PSRAM-backed buffer for smooth streaming.
- **HA intercom-addon** — Python service on port 9999 receiving audio
  uploads from either device; broadcasts to configured target media players.

---

## Announcements (text-to-speech)

Type a message in the **Intercom** addon panel (the "Announce" box) or trigger
one from a Home Assistant automation. The addon renders the text with Piper TTS,
prefixes/suffixes the intercom chime, ducks any playing media on the targets,
and plays it — the same path the PTT intercom uses.

- TTS engine is configurable via the addon's `tts_engine` option (default
  `tts.piper`).
- From the UI you pick the target players each time. If you trigger via the API
  and omit `targets`, the announcement plays on **every** `media_player` in HA.

### Trigger from an automation

Define a `rest_command` once (in `configuration.yaml`), pointing at the same
host/port the devices already use for the intercom:

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

Then call it from any automation (omit `targets` to hit all players):

```yaml
- action: rest_command.intercom_announce
  data:
    text: "Someone is at the front door"
    targets:
      - media_player.atom_echo_player
      - media_player.intercom_s3_player
```
