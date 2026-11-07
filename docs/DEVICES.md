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

### Voice S3 — bare ESP32-S3 + PCM5102A + ZK-502MT amp + INMP441

One box: voice satellite and stereo amplifier together, driving **two external
passive speakers**. No drivers inside.

| Item | Detail |
|---|---|
| MCU | Bare ESP32-S3 devkit, N16R8 (16 MB flash, 8 MB octal PSRAM @ 40 MHz) |
| DAC | PCM5102A on I²S bus 0 (BCK G5, LCK G6, DIN G7) → its own 3.5 mm socket |
| Amplifier | ZK-502MT ("502MT"; Bluetooth 5.0 + AUX), fed from the DAC by a short internal 3.5 mm patch cable. 2 × 50 W into 4 Ω / 2 × 40 W into 8 Ω at 24 V |
| Speakers | Two external passive speakers, 4–8 Ω, 15–100 W, on the amp's L± / R± terminals |
| Mic | INMP441 MEMS on I²S bus 1 (SCK G10, WS G11, SD G12), left slot |
| Button | One momentary switch on G18 to GND (active LOW, internal pull-up) |
| Panel controls | Amp's volume, treble and bass knobs, plus power switch, all reachable from outside |
| Power | 24 V / 3 A barrel → ZK-502MT direct; MP1584 buck → 5 V → devkit `5V` pin. USB-C is for flashing and logs only |

Unlike the other two, capture and playback run on **two separate I²S
peripherals**, so the mic never has to yield the bus to the speaker: the wake
word keeps listening through music and TTS, and barge-in works. That removes the
`on_announcement` / `on_idle` wake-word juggling that intercom-s3 needs.

The button does two jobs, split by hold time — tap (< 1.2 s) starts Assist
without the wake word, hold (≥ 1.2 s) records and broadcasts over the intercom
for as long as you hold it.

> **The enclosure is being redesigned for the amp.** The puck below holds the
> devkit and the DAC only; the ZK-502MT (74 × 60 mm board, 89 × 60 × 21 mm with
> connectors and knobs, plus heatsink), the MP1584, the barrel jack and the
> speaker-wire exit do not fit in it. The new layout comes after the boards are
> measured; the puck notes stay until then as the reference for the parts that carry over.
>
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
| External larger-driver speakers | ✓ (1× MAX98357A) | ✓ (2× MAX98357A, dual mono) | ✓ (built-in 2 × 50 W amp → two passive speakers) |
| Listens while playing (no shared-bus stall) | — | — | ✓ |
| Internal speaker fallback | — (disconnected) | ✓ (HA-toggleable switch) |
| Software mic gain | +12 dB (recorder.h) | n/a (codec PGA at 36 dB) | +12 dB (shift + `gain_factor`) |
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
| **LROUT / RROUT** | *nothing* | The breakout's **onboard 3.5 mm socket** already carries them; a short patch cable runs from it to the ZK-502MT's AUX-IN. Wire these only on a board with no socket. |

Everything above is a **strap**, not a signal — only BCK, LCK and DIN carry data.
Four of the five straps have a failure mode that looks like a broken device:
floating `SCK` is silent or noisy, floating `XMT` stays soft-muted, and `FMT`
selects left-justified instead of I²S.

The output is **line level**, not speaker level. The ZK-502MT inside the box is
the amp downstream of it.

#### ZK-502MT amplifier — DAC in, speakers out

| ZK-502MT | Connects to | Note |
|---|---|---|
| **AUX-IN** (3.5 mm) | PCM5102A socket, via a short TRS–TRS patch cable | The amp switches to AUX on its own when a plug is detected, so the patch cable keeps it on AUX permanently |
| **DC-IN** | 24 V rail (see *Power*) | 9–24 V / 3 A+. 24 V is the top of its range, not headroom |
| **L+ / L−** | left passive speaker | 4–8 Ω. Mind polarity, or the two speakers cancel in the bass |
| **R+ / R−** | right passive speaker | Assume bridge-tied (neither terminal at ground): never join L− to R−, or either to chassis/GND |
| **Volume / Treble / Bass** | panel | Shafts brought out through the wall |
| Heatsink | on the amp chip | Fit it if supplied, and leave the case ventilated around it |

**Which chip is on the board varies.** The EC Buying manual describes a
TPA3116D2, but sellers' listings give the chip only as "domestic amplifier
chip", which usually means a Chinese clone or equivalent. Read the marking on
the chip on your board. Until that's done, treat the three chip-dependent claims
in this section as unverified: the terminals are bridge-tied, there is no
standby, and over-voltage is protected. The listing names only over-temperature,
over-current and short-circuit protection, so treat 24 V as a hard ceiling and use
a regulated supply.

**Two volume controls are in series:** Home Assistant's player volume (digital, in
the DAC path) and the amp's knob (analog, after it). Set the knob once so that
Home Assistant at 100 % on loud music does not clip the amp, then leave volume to
Home Assistant. The PCM5102A puts out about 2.1 V RMS at full scale, which is a hot
signal for an AUX input. With the knob near the top, the amp clips before
Home Assistant reaches 100 %.

**The Bluetooth radio stays on.** The board advertises as `ZK-502MT`, and on these
boards a paired Bluetooth source usually takes over from AUX. Anyone in range
can pair with it and play through the speakers, interrupting Assist and the
intercom. If that matters where it is installed, the module's Bluetooth chip can
be disabled in hardware; there is no setting for it.

**Expected: no auto-standby.** Neither the manual nor the listing mentions a
standby or auto-off feature, and a bare TPA3116-class amp stays live on a silent
input. If that holds for your board, the "lost first half-second" problem below,
which a powered speaker caused, does not happen with this amp. To check, ask
Assist something from a silent house and listen for the first word of the reply.

#### Power — 24 V in, 5 V for the devkit

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

Two of these rules exist because the 24 V input is near the MP1584's limit:

- **Input voltage margin.** The MP1584 is rated to 28 V. A 24 V supply leaves
  4 V of margin, and hot-plugging the barrel can spike past that. Put a
  ≥ 47 µF / 35 V electrolytic across MP1584 IN at the module. A 26 V TVS diode
  (e.g. SMBJ26A) there as well makes the input robust. The ZK-502MT has its own bulk capacitance.
- **The switch is on the 24 V side, ahead of both boards.** If the amp's own switch
  is used instead (on some revisions it is on the volume pot), it cuts only the
  amp: the devkit stays up and keeps reporting as a player with nothing behind it.
  Check which kind your board has. Use the amp's switch only if that behaviour is
  what you want.

**USB-C while 24 V is on.** The devkit's 5V pin and its USB VBUS are the same
net on most S3 devkits, so with both connected the buck and the laptop drive one
rail. The buck at 5.0 V pushes current back into the laptop's port. Either:

1. **Never plug USB in with 24 V on.** Flash over OTA, and for USB flashing or
   serial logs, power the box off first. Simplest rule, nothing to add.
2. **Or add a Schottky diode** (SS34 or similar) in series in MP1584 OUT+ → 5V,
   with the buck trimmed to ~5.3 V to make up the drop. Then USB and the buck can be
   connected together: whichever is higher feeds the rail, and neither feeds the other.

**Noise.** The buck switches at about 1 MHz, and the ESP32's Wi-Fi bursts draw
current pulses of several hundred mA. Both can show up as hiss or ticking on the speakers, or as
the 3–8 kHz hiss signature in the INMP441 (see *how this mic fails* below):

- Keep the MP1584 at the **far end of the box from the INMP441** and away from
  the patch cable.
- Keep the 5 V leads short and twisted (OUT+ with OUT−).
- The patch cable's sleeve joins devkit ground to amp ground a second time, which makes
  a small ground loop. That is expected inside one box. Keep the loop small by routing the
  patch cable next to the power wiring, not around the far side of the box.
- If ticking follows Wi-Fi traffic, add 100 µF across the devkit's 5V–GND.

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

**It is a quiet mic.** Measured from a real capture, speech peaks at 5404/32767
(≈ −15.7 dBFS) with `gain_factor: 1` and a plain `>> 16` on the intercom path,
and a normal room capture sits lower still: peak −16.9 dBFS, speech −26.9 dBFS
at the +6 dB this used to run. Against a music master near −12 dBFS that is
inaudible, so **every path now takes +12 dB.**

The INMP441 has no PGA and no GAIN pin (the GAIN references elsewhere in this
file are the amplifier's, not the mic's), so every dB is digital — and digital
gain lifts the noise floor with the signal. Measured SNR was 12-15 dB at unity,
at `>> 13` (+18 dB) and at `>> 10` (+36 dB) alike. **This is level, not clarity;**
expect a louder broadcast, not a cleaner one.

+12 dB is the measured ceiling. Re-scaling the five unclipped captures in
`tools/` by x2 from the old +6 dB gives 0.00% clipped and a worst-case peak of
−5.1 dBFS on the loudest close-range one; x4 (+18 dB) pins that capture at
0.0 dBFS and begins to clip, and `>> 10` (+36 dB) clipped 12.3% outright.

| Path | Gain | Note |
|---|---|---|
| Intercom | +12 dB (`>> 14`) | 5.1 dB of headroom worst case; the add-on takes it on to −16 dBFS |
| Wake word | +12 dB (`gain_factor: 4`) | detection is on-device, so this is its only lever |
| Assist | +12 dB (`gain_factor: 2` × `volume_multiplier: 2.0`) | feeds `auto_gain`/VAD a signal already up |

The intercom figure is the level the device *uploads* at, not what a broadcast
goes out at: the add-on levels every broadcast, cleanup on or off
(`denoise.level()`, speech to −16 dBFS behind a −3 dBFS peak limiter). Measured
on later captures the upload is −27 to −31 dBFS of speech, ~18 dB under the
chime — fine through voice-s3's own amplifier, inaudible on the Atom Echo's
speaker unless the talker was right on the mic.

Since then `recorder.h` also high-passes this path at 180 Hz
(`recorder_set_highpass`): captures carried 1–10 Hz drift up to 12 dB LOUDER
than the speech, which `correct_dc_offset` leaves in. The Atom Echo gets 100 Hz,
drops its first 100 ms (`recorder_set_skip_ms`, a full-scale PDM start-up
burst), and runs at ×8 behind the filter.

`>> 14` rather than `recorder_set_gain(4, 1)` because the shift spends bits a
plain `>> 16` discards, so it costs no resolution — the 24-bit sample occupies
bits 31..8, and anything down to `>> 8` still reads real bits. The multiply
would amplify already-truncated samples for the same level.

The add-on's `denoise.py` then high-passes, subtracts each of 8 bands' own
estimated noise, expands the gaps, and brings speech to −16 dBFS — which is
the thing device-side gain cannot do, because the level is spent *after* the
noise is down rather than on top of it. Measured: hiss 7-12 dB down, and speech
11-15 dB LOUDER than the raw original with the floor between words 1-4 dB below
it (voice-s3 in its case: −60.2 dBFS against −57.8 raw).

The absolute level target matters because the broadcast shares a media player
with music: raw uploads land at −26 to −29 dBFS RMS against music masters near
−12 dBFS, so at one volume setting the chime is audible and the speech is not.

The band subtraction is what makes it audible. This mic delivers only 10-13 dB
of in-band SNR with the noise present continuously, and 67% of frames carry
speech — so a gate or expander, which can only act in the gaps, changed the
audible 1-8 kHz level by 0.2 dB. Reducing noise *underneath* speech needs
per-band subtraction.

Worth knowing for mic placement: **35% of the total RMS in a real capture sits
below 80 Hz.** That is structure-borne rumble reaching the MEMS element, not
speech, and it is why the high-pass alone removes ~10 dB of measured energy
without touching the voice. Decoupling the mic from the case would attack it at
the source. Preview any capture with `tools/denoise-preview.py`.

Do **not** set `use_apll` on this bus. The APLL is shared silicon between the
two I²S peripherals, so requesting it for the mic can disturb the DAC on the
other one. It was tried against the hiss below and gave no measured benefit.

#### Bring-up notes — how this mic fails

Debugging one of these is mostly about telling four different failures apart,
and the raw sample words distinguish them faster than any level meter:

| Symptom in the raw 32-bit words | Cause |
|---|---|
| Exactly `00000000` forever, no noise floor | Nothing arriving — dead wire, or the mic isn't clocked |
| Peak pinned at `32768` (`0x8000`) while the mean stays near 0 | Floating data line latched at the MSB — the mic goes high-Z outside its slot |
| Long runs of zeros interrupted by full-scale bursts | Intermittent connection; the bursts are contact noise, not audio |
| Smooth ramps of a constant step, ~4 Hz, heavily clipped | Sub-audio wander, usually too much digital gain applied to a DC-ish signal |
| Isolated single-sample spikes at power-of-two magnitudes (512, 1024, 16384) on a few % of samples | Bit errors in the I²S word — `SD`/`SCK`/`WS` wiring, or `L/R` left floating. They inflate RMS **and** the noise floor together, so it reads as "suddenly +18 dB of gain"; it is not a gain problem |

A real capture settles it where statistics mislead: **speech produces hundreds
to thousands of zero-crossings per second.** Anything under ~50/s is not sound,
whatever the level looks like.

There are two ways to get one, chosen by the `mic_test_url` substitution — the
address the **Mic test recording** button uploads to. It is deliberately
separate from `intercom_url`, so aiming a mic test at a laptop never diverts PTT
broadcasts away from the add-on.

To simply *hear* the mic, point `mic_test_url` at the add-on and press the
button: the add-on keeps the raw mic audio of the last `keep_recordings` uploads
and lists them under **Mic recordings** in its side-panel, with an inline player
and a download link.

For the statistics — which is what settles the failures in the table above —
`tools/mic-capture.py` stands in for the add-on's `/intercom` endpoint, writes a
WAV next to itself, and prints the verdict:

```bash
python3 tools/mic-capture.py            # on any machine on the LAN
# then set mic_test_url: "http://<that-machine>:9999/intercom", flash,
# and press the device's "Mic test recording" button in Home Assistant
```

Either way the file is the same bytes the device streamed; only where it lands
differs. Flashing is only needed to change `mic_test_url`, not to listen.

```
peak 5404  mean 824  dc -7
clipped 0.00%   isolated spikes 0.00% (2 of 3 on a power of two)
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

#### The lost first half-second — it was the powered speaker

> This happened on the earlier line-out build, which fed a JBL powered speaker. The
> built-in ZK-502MT is expected to have no standby, so the current build should
> not show it (to verify, see *ZK-502MT amplifier* above). The
> ducking schedule below stays because it is harmless and still protects any
> line-out build.

Symptom: every Assist reply arrived with roughly its first 0.5 s missing, so
"02:05" was heard as "05". **The cause was outside the device**: JBL powered
speakers auto-standby on a silent input, and the ~10 s Home Assistant spends
between the microphone releasing and the reply arriving was enough for them to
drop out. They then ate the first half-second waking back up.

Everything inside the device measured clean, and chasing it there cost hours:

| Checked | Result |
|---|---|
| HA's TTS audio | complete, speech from frame 0, **no leading silence** |
| I²S driver start-up | ~300 ms, real, but eliminated by keeping the chain warm |
| Codec (FLAC vs WAV) | identical clipping. WAV is 5x the bytes and starved the pipeline |
| Mixer / buffer timeouts | `timeout: never` on `announcement_src` **silenced replies entirely** |
| Player volume | fine |

The tell was in the *sequence*, not the logs: the chime was audible and the
reply was not, and the chime always arrived moments after full-volume music
while the reply always arrived after a long quiet stretch.

**The fix is the ducking schedule.** Music is only ducked when it needs to be,
so the line is never quiet for long:

| Moment | Music | Why |
|---|---|---|
| Wake word → listening (`on_start`) | −15 dB | Not talking over you into the mic |
| Mic released → waiting (`on_stt_vad_end`) | **full** | Keeps the speaker awake through the wait |
| Reply starts (`on_tts_start`) | −15 dB | So the answer is clear |
| Reply ends (`on_end`) | full | Normal |

This only helps **while music is playing**. Asked from a silent house, the
speaker still sleeps. The permanent fixes are to disable auto-off on the
speaker, drive a bare PAM8406 / TPA3116 (no standby logic at all — which is why
the speaker case never showed this), or pad the response text in HA so the lost
moment is a throwaway word.

#### The on-device chime

It confirms the wake word registered, and it warms the output chain — I²S driver
running, DAC settled — before the reply arrives. It does **not** fix the problem
above; that was the theory it was built for, and the ten-second gap is far longer
than any warm-up it can bridge.

Two details still matter. It must go through the **announcement pipeline**
(`announcement: true` on `media_player.speaker.play_on_device_media_file`) — raw
`speaker.play` bypasses the mixer and fails with "Incompatible audio streams".
And it opens with 60 ms of silence and a 12 ms fade-in, so start-up latency
lands on silence rather than on the sound. Regenerate with `tools/make-chime.py`.

#### Button

| Pin | Wiring |
|---|---|
| **G18** | one leg of a momentary switch; other leg to **GND** (internal pull-up, active LOW) |

#### Pins to avoid on this board

G26–G32 are the SPI flash and **G33–G37 the octal PSRAM** — using any of them
kills the board's memory. G19/G20 are USB, G43/G44 are UART0, and G0/G3/G45/G46
are strapping pins. The G5–G12 block and G18 used here are clear of all of that.

**Do not put the button on G38 or G39.** Measured: with the switch open both
flicker at 20–30 edges/s, continuously, sub-2 ms glitches included — a floating
input, not contact bounce. They are the first pads past the MSPI block (G26–G37,
per `soc/esp32s3/spi_pins.h`), and this module's octal PSRAM keeps that bus
switching at 40 MHz, which a pin held only by the ~45 kΩ internal pull-up is too
high-impedance to sit beside. **G18** is an RTC-domain pad — `SOC_RTCIO_PIN_COUNT
22` covers G0–G21 — well away from MSPI. Any free RTC pad behaves the same:
G1, G2, G4, G8, G9, G13–G18, G21 (G5–G12 are the I²S buses, G0/G3 strapping,
G19/G20 USB, and G22–G25 do not exist on the S3). Caveat: G38–G42 *and* G21 are
the external USB PHY signals (`soc/esp32s3/usb_pins.h`) — irrelevant with the
internal PHY, which is what `USB_SERIAL_JTAG` logging uses.

---

## Repo layout

```
intercom/
├── devices/
│   ├── atom-echo.yaml              # Kitchen Atom Echo (PTT intercom + DMA watchdog)
│   ├── intercom-s3.yaml            # Terrace VoiceS3R (intercom + wake-word + music)
│   ├── intercom-s3-minimal.yaml    # Bare-boot diagnostic config
│   ├── speaker-s3.yaml             # Bare S3 + PCM5102A — playback only, no mic
│   ├── voice-s3.yaml               # Bare S3 + PCM5102A + ZK-502MT amp + INMP441 + button
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
  unchanged; software gain in `recorder.h` boosts Atom Echo's PDM mic +12 dB
  (`recorder_set_gain(4, 1)`) — matching Voice S3's `>> 14`, though unmeasured
  on this mic: it saturates rather than wraps, so drop back to `(2, 1)` if a
  close talker comes through distorted.
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
  (≥ 1.2 s) records the intercom. A `restart`-mode script started on press
  distinguishes them: if it is *still running* at release, the press was a tap.
  Asking the script rather than a flag also means a hold that could not record
  (an upload still in flight) does nothing, instead of falling through to Assist.
- **Ducking follows the interaction, not the session** — music is quiet only
  while the mic listens and while the reply plays, and returns to full during the
  wait in between. A permanently ducked line lets a powered speaker with
  auto-standby drop out; see "The lost first half-second" above.
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
