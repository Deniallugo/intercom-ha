# Devices — hardware reference

Three intercom devices plus a playback-only speaker. Repo layout: [README](../README.md#repository-layout).

| | Kitchen | Terrace | Voice S3 |
|---|---|---|---|
| Config | `atom-echo.yaml` | `intercom-s3.yaml` | `voice-s3.yaml` |
| Board | M5Stack Atom Echo (ESP32, no PSRAM) | M5Stack VoiceS3R (ESP32-S3, 8 MB PSRAM) | Bare ESP32-S3 N16R8 devkit |
| Mic | internal PDM (SPM1423) | ES8311 codec, `mic_gain: 36DB` | INMP441 |
| Output | 1× MAX98357A → 2× 4 cm drivers in series | 2× MAX98357A, dual mono | PCM5102A → ZK-502MT 2 × 50 W → two passive speakers |
| Talk button | hold = talk, tap+hold = reply | same, tap = Assist | same, tap = Assist |
| Talker feedback | status LED | tones | tones |
| Wake word + Assist | — | ✓ `okay nabu` | ✓ `okay nabu` |
| Music Assistant | — | ✓ | ✓ stereo |
| Mic gain | ×8 (+18 dB) in `recorder.h` | codec PGA | +12 dB on every path |
| Extra | DMA watchdog reboot | — | timers |

On Terrace and Voice S3, mic and playback are on separate I²S buses, so the wake
word keeps listening during playback.

---

## Talk button — every intercom device

One package, `packages/intercom.yaml`, drives the button on Kitchen, Terrace,
Terrace minimal and Voice S3. The device file sets its pins, mic, tail and
hooks (wake word, Assist, alarms); `packages/feedback-led.yaml` (Kitchen) or
`packages/feedback-sound.yaml` (the S3s) turns the outcome into light or tones.

### Gestures

| Gesture | Does |
|---|---|
| hold ≥ 0.45 s | talk to the channel, until release (limit 30 s) |
| tap, then press and hold | reply to whoever last spoke to this device (`X-Intercom-Reply`; the add-on falls back to the channel) |
| tap | Assist on Terrace and Voice S3; nothing on Kitchen and Terrace minimal |
| tap while a message, or an alarm, plays | silence it, at once |
| hold while a message plays, or while the last message is still being sent | "busy" |

Recording starts at the press and the upload connects meanwhile, so the first
word isn't lost and nothing reaches the add-on for a tap (the idle connection
is just closed). A single tap acts 0.3 s after its release: that is how long a
second press has to turn it into a reply. A tap that silences something acts
at once. A plain double tap does nothing.

After release the device waits for the add-on's answer (it answers once
playback has started; up to 25 s), then signals the outcome. A press during
that wait is "busy".

### Feedback

Kitchen (status LED; colours changed from the old blue/yellow scheme):

| LED | Meaning |
|---|---|
| off | normal |
| red | on air |
| dim red | sending, waiting for the add-on |
| blue pulse | incoming message |
| green flash | delivered |
| red blinking | not delivered: add-on down, refused (502), or no answer |
| white double flash | busy |
| white flicker | 30 s limit reached |
| yellow slow pulse | no Wi-Fi, or the add-on unreachable |
| purple | mic test |

The Kitchen has no tones: mic and speaker share the I²S clock pins, so it
can't beep while recording, and playback costs DMA memory it is short of.

Terrace, Terrace minimal, Voice S3 (tones on their own mixer input, so they
play over music and over a message instead of cutting it; generated on the
device, `include/feedback.h`):

| Tone | Meaning |
|---|---|
| short high tick (2.6 kHz, 25 ms) | on air |
| rising blip-blip (G6, C7) | delivered |
| low descending buzz (B3, G3) | not delivered; also once at boot if the add-on is unreachable |
| busy tone (480 + 620 Hz, × 3) | busy |
| triple high beep | 30 s limit reached |

The add-on's chime is a 120 ms 800↔1200 Hz sweep and the wake chime an A5→E6
bell, so none of these can be taken for an incoming message. The mic hears
the tick, so it is in the recording, ~0.45 s in.

"Delivered" = HTTP 200 and at least one speaker played or queued it. A 200
with nobody to reach (no other intercom device) counts as not delivered.

### Entities

| Entity | |
|---|---|
| **Talk button** (was *Button*) | the button state. Renaming changed its entity ID: `binary_sensor.<device>_button` → `binary_sensor.<device>_talk_button`. HA keeps the old one as unavailable; delete it, and update automations that used it |
| **Talk** (event) | `talk` / `reply` when a hold goes on air, then `delivered` / `failed` |
| **Do not disturb** | incoming messages are stopped as they start (the first ~0.1 s of the chime still plays) |
| **Intercom volume** (S3s) | level of incoming messages only, 5–100 %. The mixer attenuates the announcement input while a message plays; Assist replies, alarms and music keep the player volume. Not on the Kitchen: no mixer there, and its player plays nothing but announcements, so its volume already is the intercom volume |
| **Intercom URL** | the add-on address, stored on the device. Default: the `intercom_url` substitution. With a `lan_token`, append `?token=<t>`. Changing the substitution later doesn't override a stored value: press **Reset intercom URL** |
| **Intercom add-on** (diagnostic) | add-on reachable: a TCP connect every 60 s, and every upload |
| Free DMA heap, Largest DMA block (Kitchen) | now diagnostic |

An incoming message is any announcement on the device's player that it didn't
start itself (Assist chime and reply, alarm). Music uses the media pipeline,
so it never counts. Text announcements from the add-on count as messages.

### Add-on changes that would help (not implemented)

- **Do not disturb on the add-on side:** skip a target whose device has
  `switch.<device>_do_not_disturb` on, with `{"outcome": "skipped", "reason": "dnd"}`.
  Then not even the start of the chime plays, and the sender learns it.
- **`POST /intercom/replay`** (`X-Device-Name`): play again the last message
  that reached this device. A Kitchen tap could call it; today a Kitchen tap
  does nothing.
- **mDNS:** advertise `_intercom._tcp` (port 9999, TXT `path=/intercom`). A
  device with an empty Intercom URL would find it with `mdns_query_ptr()` in
  the uploader task. The token isn't advertised; it still goes into the URL.

### Kitchen memory

The 32 KB ring buffer (1 s) and the uploader task are allocated at boot. The
0.45 s held before the hold is confirmed (14 KB) lives in that ring buffer, so
a press allocates nothing new and the DMA watchdog sees no change; DNS +
connect overlap the hold, so the remaining 0.55 s is slack for a slow connect.

---

## Kitchen — Atom Echo + MAX98357A

The MAX98357A taps the Atom's own I²S-out pins as a passive listener — no YAML
change. The internal NS4168 speaker is disconnected (it has no enable pin).

| GPIO | Function |
|---|---|
| GPIO33 | I²S LRCLK (mic + amps) — also feeds MAX98357A LRC |
| GPIO19 | I²S BCLK (shared) — also feeds MAX98357A BCLK |
| GPIO23 | PDM mic data in |
| GPIO22 | I²S DOUT → (internal NS4168, disconnected) + MAX98357A DIN |
| GPIO39 | Button (active LOW, internal pull-up) |
| GPIO27 | SK6812 RGB LED data |

### External MAX98357A wiring

| MAX98357A pin | Atom Echo pin | Header |
|---|---|---|
| VIN | 5V | bottom header (`G21 / G25 / 5V / GND` side) |
| GND | GND | bottom header |
| BCLK | G19 | `3V3 / G22 / G19 / G23 / G33` side |
| LRC | G33 | same side |
| DIN | G22 | same side |
| GAIN | bridged to GND (bare wire) | +12 dB |
| SD | left floating | on-board pull-up = enabled, mono-average |
| `+ / −` | 2× 4 cm drivers in series | see `hardware/kitchen-case/README.md` |

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

## Terrace — VoiceS3R

### Internal connections (not broken out)

| GPIO | Function |
|---|---|
| GPIO3 | I²S LRCK to/from ES8311 codec |
| GPIO17 | I²S SCLK to/from ES8311 codec |
| GPIO11 | I²S MCLK to ES8311 codec |
| GPIO48 | DSDIN — codec DAC input (speaker direction) |
| GPIO4 | ASDOUT — codec ADC output (mic direction) |
| GPIO18 | NS4150 internal amp enable — unused, the internal speaker is not connected in `intercom-s3.yaml` |
| GPIO45 | I²C SDA — codec config |
| GPIO0 | I²C SCL — codec config |
| GPIO41 | Built-in button |

The silkscreen labels (`LRCK: G3`, `DSDIN: G48`…) describe these internal
pins. External amps go on a second I²S bus on the free header pins G5/G6/G7.

### External MAX98357A × 2

Both boards wired identically, in parallel (I²S is a broadcast bus):

| MAX98357A pin | VoiceS3R pin | Header position |
|---|---|---|
| **VIN** | 5V | Top header (4-pin row) |
| **GND** | G (GND) | Top header |
| **BCLK** | G5 | Bottom header (4-pin row, leftmost when label is right-side up) |
| **LRC** | G6 | Bottom header |
| **DIN** | G7 | Bottom header |
| **GAIN** | bridged to GND | +12 dB (floating = 9 dB; 15 dB needs 100 kΩ to GND) |
| **SD** | not connected | board pull-up = enabled, left slot |
| **`+ / −` outputs** | its own driver `+ / −` | one driver per board |

Both decode the left/mono slot, so the drivers play the same mix. SD floats
high via the board pull-up: amps always on, no software mute (to add one, wire
both SD pins to a spare GPIO such as G8).

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

### Optional: PCM5100 3.5 mm line-out

Wire as a third parallel listener on G5/G6/G7:

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

It plays the same stream as the speakers; muting the speakers needs SD control
(dual mono: both SD pins to one GPIO; L/R stereo: power-gate with a MOSFET,
since SD also selects the channel).

The case takes an optional +20 mm depth spacer — see `hardware/terrace-case/README.md`.

---

## Voice S3 — bare ESP32-S3

24 V box: voice satellite + stereo amp driving two external passive speakers.
Enclosure: `hardware/voice-case/` (holds devkit + DAC only; a case for the amp
is in progress).

| Part | Detail |
|---|---|
| MCU | ESP32-S3 N16R8, octal PSRAM at 40 MHz (80 MHz boot-loops) |
| DAC | PCM5102A, I²S bus 0 → its own 3.5 mm socket → patch cable → amp AUX |
| Amp | ZK-502MT (BT 5.0 + AUX), 2 × 50 W into 4 Ω at 24 V |
| Mic | INMP441, I²S bus 1, left slot |
| Button | G18 → GND, internal pull-up |
| Power | 24 V / 3 A barrel → amp; MP1584 buck → 5 V → devkit. USB-C only for flashing/logs |

### PCM5102A DAC (I²S bus 0)

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
| **LROUT / RROUT** | *nothing* | The breakout's **onboard 3.5 mm socket** already carries them; a short patch cable runs from it to the ZK-502MT's AUX-IN. Wire these only on a board with no socket. |

Floating SCK = silent or noisy, floating XMT = soft-muted. Output is line level.

### ZK-502MT amplifier

| ZK-502MT | Connects to | Note |
|---|---|---|
| **AUX-IN** (3.5 mm) | PCM5102A socket, via a short TRS–TRS patch cable | The amp switches to AUX on its own when a plug is detected, so the patch cable keeps it on AUX permanently |
| **DC-IN** | 24 V rail (see *Power*) | 9–24 V / 3 A+. 24 V is the top of its range, not headroom |
| **L+ / L−** | left passive speaker | 4–8 Ω. Mind polarity, or the two speakers cancel in the bass |
| **R+ / R−** | right passive speaker | Assume bridge-tied (neither terminal at ground): never join L− to R−, or either to chassis/GND |
| **Volume / Treble / Bass** | panel | Shafts brought out through the wall |
| Heatsink | on the amp chip | Fit it if supplied, and leave the case ventilated around it |

- The chip varies (manual says TPA3116D2, listings don't). Check the marking;
  treat 24 V as a hard ceiling and use a regulated supply.
- Two volumes in series: set the amp knob once so HA at 100 % doesn't clip it
  (PCM5102A outputs ~2.1 V RMS), then use HA.
- Bluetooth stays on and can take over from AUX; it can only be disabled in hardware.

### Power

```
24 V / 3 A barrel ──► panel power switch ──┬──► ZK-502MT DC-IN
                                           │
                                           └──► MP1584 IN+ / IN−
                                                  OUT 5.0 V ──► devkit 5V pin
                                                  OUT GND   ──► devkit GND
```

| From | To | Note |
|---|---|---|
| Barrel jack + | power switch → ZK-502MT DC-IN + and MP1584 IN+ | One switch cuts both boards. The switch must carry 3 A |
| Barrel jack − | ZK-502MT DC-IN − and MP1584 IN− | Run both returns **back to the jack separately**, not daisy-chained through the amp |
| MP1584 OUT+ | devkit **5V** pin | **Set to 5.0 V with a meter BEFORE connecting the devkit.** The adjustable module ships at an arbitrary voltage, and its trimmer can put 20 V on the 5V pin |
| MP1584 OUT− | devkit GND | |
| Devkit 5V / 3V3 | PCM5102A, INMP441 | Unchanged: wired as in their own tables, from the devkit's rails |

| From | To | Note |
|---|---|---|
| Barrel + | power switch → amp DC-IN + and MP1584 IN+ | one 3 A switch cuts both |
| Barrel − | amp DC-IN − and MP1584 IN− | separate returns to the jack |
| MP1584 OUT+ | devkit 5V | **set 5.0 V with a meter before connecting** — it ships at an arbitrary voltage |
| MP1584 OUT− | devkit GND | |

- MP1584 is rated 28 V: put ≥ 47 µF / 35 V (and optionally an SMBJ26A TVS) across its input.
- Use the 24 V-side switch; the amp's own switch (if on the volume pot) leaves the devkit running.
- **USB-C with 24 V on:** devkit 5V and VBUS are one net, so the buck back-feeds
  the laptop. Either power off before plugging USB, or put an SS34 Schottky in
  MP1584 OUT+ → 5V and trim the buck to ~5.3 V.

### Noise and Wi-Fi clicks

- Keep the MP1584 at the far end from the mic and the patch cable; twist its 5 V leads.
- Route the patch cable next to the power wiring (its sleeve makes a small ground loop).
- Wi-Fi transmit bursts reach the INMP441 as clicks via the 3.3 V rail.
  `wifi: output_power: 8.5dB` cuts them: −44.2 dBFS / 39 clicks/s at 20 dBm →
  −57.7 dBFS / 1.3 clicks/s (−59.9 / none with no transmit). If the device drops
  off Wi-Fi, raise it first.
- PTT records from the press into a 30 s PSRAM buffer; the upload connects at
  the press, starts sending when the hold is confirmed (0.45 s), drains the
  buffer, then streams until release + 500 ms. A tap sends nothing. The mic
  test records 5 s, then uploads.
- If clicks remain, filter the mic's VDD: 100 Ω series from 3V3, 10 µF + 100 nF
  to GND at the mic; keep its wires away from the antenna.

### INMP441 mic (I²S bus 1)

| INMP441 pin | ESP32-S3 | Note |
|---|---|---|
| **VDD** | 3V3 | 3.3 V only — not 5 V tolerant |
| **GND** | GND | |
| **SCK** | G10 | Bit clock |
| **WS** | G11 | Word select |
| **SD** | G12 | Data out → ESP32 data in |
| **L/R** | **GND** | left slot (`channel: left`); floating = undefined |

24-bit left-justified in a 32-bit slot (`bits_per_sample: 32bit`). Don't set
`use_apll`: the APLL is shared with the DAC's bus.

The mic is quiet (speech peaks ≈ −15.7 dBFS at unity) and has no PGA, so all
gain is digital and doesn't improve SNR (12–15 dB at +0, +18 and +36 dB).
+12 dB is the clipping-free ceiling (worst peak −5.1 dBFS; +18 dB starts clipping):

| Path | Gain |
|---|---|
| Intercom | `>> 14` in the data callback (uses bits `>> 16` would discard), then 180 Hz high-pass in `recorder.h` |
| Wake word | `gain_factor: 4` |
| Assist | `gain_factor: 2` × `volume_multiplier: 2.0` |

The add-on then levels and cleans every broadcast — see
[README → Broadcast cleanup](../README.md#broadcast-cleanup).

#### Bring-up notes — how this mic fails

| Symptom in the raw 32-bit words | Cause |
|---|---|
| Exactly `00000000` forever, no noise floor | Nothing arriving — dead wire, or the mic isn't clocked |
| Peak pinned at `32768` (`0x8000`) while the mean stays near 0 | Floating data line latched at the MSB — the mic goes high-Z outside its slot |
| Long runs of zeros interrupted by full-scale bursts | Intermittent connection; the bursts are contact noise, not audio |
| Smooth ramps of a constant step, ~4 Hz, heavily clipped | Sub-audio wander, usually too much digital gain applied to a DC-ish signal |
| Isolated single-sample spikes at power-of-two magnitudes (512, 1024, 16384) on a few % of samples | Bit errors — `SD`/`SCK`/`WS` wiring or floating `L/R`. Looks like "+18 dB of gain"; it is not a gain problem |

Speech produces hundreds to thousands of zero-crossings per second; under
~50/s is not sound. A healthy INMP441 shows 40–60 dB SNR; ~5 dB with energy at
3–8 kHz is wiring hiss: add 100 nF across VDD–GND, shorten SD/SCK/WS, run ground
next to the data line, add 10 kΩ SD→GND.

The diagnostic **Mic test recording** button records 5 s and uploads to the
`mic_test_url` substitution — the add-on by default (saved in the panel, and
played on the target speakers). For statistics, run the capture tool and point
`mic_test_url` at it:

```bash
python3 tools/mic-capture.py   # then mic_test_url: "http://<this-machine>:9999/intercom", flash, press the button
```

```
peak 5404  mean 824  dc -7
clipped 0.00%   isolated spikes 0.00% (2 of 3 on a power of two)
zero crossings 564/s
noise floor 699  loudest 1074  SNR ~4 dB
--> looks like real audio.
```

### Button

G18 to GND, internal pull-up, 25 ms debounce. Pins to avoid:

- G26–G32 flash, **G33–G37 octal PSRAM**, G19/G20 USB, G43/G44 UART0, G0/G3/G45/G46 strapping.
- **Not G38/G39:** measured floating at 20–30 edges/s next to the 40 MHz MSPI
  bus. Use an RTC pad: G1, G2, G4, G8, G9, G13–G18, G21.

### Assist details

- Ducking: −15 dB while listening, **full** while HA thinks (a near-silent line
  lets powered speakers with auto-standby sleep and eat the reply's first
  0.5 s), −15 dB during the reply, full after.
- The wake chime must use `announcement: true`; raw `speaker.play` fails with
  "Incompatible audio streams". Regenerate with `tools/make-chime.py`.
- Tap = Assist (wake chime first). The tap acts 0.3 s after release, the
  double-tap window.
- The mic is reference-counted: PTT takes its own listener slot and re-arms the
  wake word before releasing it, so the I²S driver never tears down mid-recording.

---

## Announcements (text-to-speech)

Type text in the add-on's **Intercom** panel or call `POST /announce`
([README → HTTP API](../README.md#http-api)). The add-on renders it with
`tts_engine` (default `tts.piper`), adds the chime, ducks media and plays it on
the targets. Omitting `targets` plays on every `media_player`.
