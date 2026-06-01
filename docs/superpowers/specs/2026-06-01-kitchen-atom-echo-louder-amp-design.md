# Kitchen Atom Echo — Louder External Amp

**Date:** 2026-06-01
**Status:** Design — pending implementation
**Device:** Kitchen M5Stack Atom Echo (`devices/atom-echo.yaml`)

## Goal

Make the kitchen Atom Echo's playback (PTT intercom + HA TTS announcements)
noticeably louder by adding a single external MAX98357A amplifier driving a
bigger speaker, replacing the tiny internal 0.5 W driver.

Explicitly **out of scope**: no music-streaming media pipeline, no new
`media_player`, no HA-controllable amp switch. The device stays
announcement-only. This is a hardware change with **zero YAML change**.

## Background

The Atom Echo is an ESP32-classic (no PSRAM) with an internal NS4168 class-D
amp driving a 0.5 W speaker over I²S out. Its existing `atom_player` media
player has only an `announcement_pipeline` (no music pipeline), so "no media
player" — in the sense of no music streaming — is already the case.

The terrace VoiceS3R already proves this pattern: MAX98357A boards wired as
passive parallel listeners on an I²S bus, decoding the same stream ESPHome
already sends. We reuse that pattern with a single board on the Atom Echo.

### Verified hardware facts

- The Atom Echo's bottom headers expose: `3V3 / G22 / G19 / G23 / G33` on one
  side and `G21 / G25 / 5V / GND` on the other. The I²S signals we need are at
  the header pads — **no case-opening required to tap them**.
- I²S signal map (internal audio): **BCLK = G19, LRCLK = G33, DOUT/SDATA = G22**,
  mic data in = G23.
- The internal speaker is **0.5 W** (DEVICES.md currently says 1 W — fix to 0.5 W
  during implementation).
- M5Stack marks G19/G22/G23/G33 "reserved for internal audio." This warning is
  about *repurposing* the pins for another function. Adding a high-impedance
  parallel listener (the MAX98357A's I²S inputs) does not repurpose them — it is
  the same technique the terrace uses with two MAX boards on one bus.
- The internal NS4168 has **no software enable/SD pin** broken out. It plays
  whenever the I²S clock runs. The only way to silence it is to physically
  disconnect the internal speaker.
- The Atom Echo I²S stream is 16 kHz / 16-bit mono. The MAX98357A supports
  8–96 kHz, so 16 kHz mono is well within range.

## Design

### Approach: single MAX98357A as a parallel I²S listener

Wire one MAX98357A onto the Atom Echo's existing I²S-out signals at the header
pads. The amp listens to the same stream the NS4168 receives — ESPHome is
unaware of it, so **no configuration changes**.

#### Wiring

| MAX98357A pin | Atom Echo pin | Note |
|---|---|---|
| VIN | 5V | bottom header (`G21 / G25 / 5V / GND` side) |
| GND | GND | bottom header |
| BCLK | G19 | I²S bit clock |
| LRC | G33 | I²S word/LR clock |
| DIN | G22 | I²S data out |
| GAIN | → GND | +12 dB (matches terrace; bare wire to GND) |
| SD | leave default | on-board pull-up keeps the amp enabled / mono-average mode |
| `+ / −` | one driver | bigger 4 Ω driver |

Speaker: a single driver on the MAX's `+ / −` output. 4 Ω gives the MAX its
full ~3.2 W at 5 V (vs. the internal 0.5 W). An 8 Ω driver also works at lower
output — either is far louder than the internal.

#### Silencing the internal speaker

Open the Atom Echo case and disconnect the internal 0.5 W speaker (desolder or
cut its two leads). Required because the NS4168 has no enable pin. This is the
only step that needs the case opened; reversible if leads are cut cleanly /
re-solderable.

**Fallback if the user prefers not to open the case:** leave the internal
speaker connected. At 0.5 W it is negligibly quiet next to the external driver.
The design works either way; disconnecting is the chosen "replace" behavior.

### Why not the alternatives

- **HA soft-mute switch (drive MAX SD from a free GPIO):** adds a `switch:` to
  the YAML and consumes a free pin (G21/G25). Rejected — the request is "just
  louder, no media player," i.e. keep it minimal. The zero-YAML approach is
  preferred.
- **Analog amp tapping the internal speaker line:** rejected. The NS4168 output
  is an amplified bridge-tied class-D signal, not line level, so it can't be
  cleanly re-amplified. Digital I²S (MAX98357A) is the correct tap point.

## Risk / caveats

- **Tapping reserved pins:** electrically safe as a parallel high-Z listener;
  do not also drive these pins from the MAX (it never does — DIN/BCLK/LRC are
  inputs). Keep stub wires short to avoid loading the I²S lines.
- **No DMA/RAM impact:** the MAX adds no load on the ESP32's scarce DMA-capable
  RAM; the existing I²S stream and the DMA watchdog in `atom-echo.yaml` are
  untouched.
- **GAIN to GND must be a bare wire**, not a resistor (15 dB would need a 100 kΩ
  resistor — not what we want here).

## Acceptance criteria

1. MAX98357A wired to G19/G33/G22 + 5V/GND at the header; GAIN bridged to GND.
2. External driver audibly louder than the original internal speaker for both
   PTT intercom playback and HA TTS announcements.
3. Internal speaker silent (disconnected), or — if the case-open is declined —
   inaudible under the external driver.
4. `devices/atom-echo.yaml` unchanged.
5. `docs/DEVICES.md` updated: kitchen row reflects the external MAX98357A +
   driver, the 0.5 W internal-speaker correction, and a wiring table/diagram in
   the kitchen section.

## Work items

- Physical: wire MAX98357A, set GAIN, attach driver, disconnect internal speaker.
- Docs: update `docs/DEVICES.md` (kitchen device row, capabilities table, new
  kitchen wiring table + ASCII diagram, 0.5 W correction).
- No firmware/YAML change.
