# Kitchen Atom Echo — Louder External Amp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note:** This plan is mostly physical hardware assembly (done by the human at the bench) plus one docs change in the repo. There is **no firmware/YAML change** and **no automated test code** — by design (`devices/atom-echo.yaml` must stay byte-identical). "Verify" steps are bench measurements and `git` checks, not unit tests.

**Goal:** Add one MAX98357A amplifier + bigger driver to the kitchen Atom Echo as a passive parallel I²S listener, replacing the internal 0.5 W speaker, with zero firmware change.

**Architecture:** The MAX98357A taps the Atom Echo's existing I²S-out signals (BCLK G19 / LRC G33 / DIN G22) at the exposed header pads and decodes the same stream the internal NS4168 already receives. ESPHome is unaware of it. The internal speaker is physically disconnected (NS4168 has no enable pin). Same pattern the terrace VoiceS3R uses with its dual MAX98357A boards.

**Tech Stack:** M5Stack Atom Echo (ESP32-classic), MAX98357A I²S class-D amp, one 4 Ω driver. Repo: ESPHome YAML (unchanged) + Markdown docs.

**Spec:** `docs/superpowers/specs/2026-06-01-kitchen-atom-echo-louder-amp-design.md`

---

## File Structure

- `devices/atom-echo.yaml` — **unchanged** (verified in Task 4; the amp is a passive listener, no config needed).
- `docs/DEVICES.md` — **modified**: kitchen device row, capabilities table, new kitchen wiring table + ASCII diagram, 0.5 W internal-speaker correction.

Physical artifacts (no repo footprint): one MAX98357A board, one 4 Ω driver, hookup wire.

---

## Task 1: Bench-wire the MAX98357A (no power)

**Files:** none (physical).

**Pin map (target):**

| MAX98357A pin | Atom Echo pin | Header side |
|---|---|---|
| VIN | 5V | `G21 / G25 / 5V / GND` side |
| GND | GND | `G21 / G25 / 5V / GND` side |
| BCLK | G19 | `3V3 / G22 / G19 / G23 / G33` side |
| LRC | G33 | `3V3 / G22 / G19 / G23 / G33` side |
| DIN | G22 | `3V3 / G22 / G19 / G23 / G33` side |
| GAIN | GND (bare wire) | sets +12 dB |
| SD | leave unconnected | on-board pull-up keeps amp enabled |
| `+ / −` | one 4 Ω driver | — |

- [ ] **Step 1: Solder the five signal/power wires**

Wire VIN→5V, GND→GND, BCLK→G19, LRC→G33, DIN→G22. Keep the BCLK/LRC/DIN stub wires short (parallel I²S listener — long stubs load the bus). Do **not** connect anything to G23 (mic data) or 3V3.

- [ ] **Step 2: Bridge GAIN to GND with a bare wire**

GAIN → GND directly (no resistor). This is +12 dB. A resistor would change the gain (100 kΩ = 15 dB) — not wanted here.

- [ ] **Step 3: Attach the driver and leave SD unconnected**

Connect the 4 Ω driver to the MAX `+ / −`. Leave SD floating (on-board pull-up enables the amp in mono-average mode).

- [ ] **Step 4: Verify continuity with a multimeter (power OFF)**

Run: continuity probe across each wired pair (VIN↔5V, GND↔GND, BCLK↔G19, LRC↔G33, DIN↔G22, GAIN↔GND).
Expected: continuity beeps on each intended pair; **no** continuity between DIN/BCLK/LRC and each other or to 5V/GND (no shorts).

---

## Task 2: Power-on smoke test (internal speaker still connected)

**Files:** none (physical).

Test the external amp works *before* disconnecting the internal speaker, so a failure is easy to localize. At this stage both speakers will play.

- [ ] **Step 1: Power the Atom Echo over USB-C**

Expected: device boots normally, status LED behaves as usual, connects to Wi-Fi/HA (no behavior change — firmware untouched).

- [ ] **Step 2: Trigger an HA TTS announcement to the kitchen player**

Run (Home Assistant Developer Tools → Services, or `media_player.play_media`): play any TTS/notification sound to `media_player.atom_echo_player` (the kitchen `atom_player`).
Expected: audio plays out of **both** the new external driver (loud) and the internal speaker (faint). External is clearly louder.

- [ ] **Step 3: Trigger a PTT intercom playback**

Run: press the PTT button on another intercom device so the kitchen plays the received clip (existing intercom flow).
Expected: clip plays through the external driver, audibly louder than the internal ever was. No distortion at normal volume.

- [ ] **Step 4: If silent or distorted, stop and diagnose**

- Silent on external only → recheck BCLK/LRC/DIN mapping (G19/G33/G22) and that SD is enabled (floating, pull-up intact).
- Distortion → driver impedance too low or GAIN too high; confirm a 4 Ω (or 8 Ω) driver and GAIN→GND (not a resistor).
- Nothing plays at all → firmware/HA issue unrelated to this change; confirm the device still works with the external amp disconnected.

---

## Task 3: Disconnect the internal speaker

**Files:** none (physical).

The NS4168 has no enable pin, so silencing the internal 0.5 W driver means physically disconnecting it.

- [ ] **Step 1: Power off and open the Atom Echo case**

Remove USB-C. Open the case to expose the internal speaker and its two leads.

- [ ] **Step 2: Disconnect the internal speaker**

Desolder or cleanly cut the internal speaker's two leads. Insulate cut ends if leaving them in place (avoid shorting). Keep the cut clean so it's reversible if desired.

- [ ] **Step 3: Reassemble and power on**

Close the case, reconnect USB-C. Expected: device boots normally.

- [ ] **Step 4: Re-run the announcement + intercom checks**

Run: repeat Task 2 Step 2 (TTS) and Step 3 (PTT intercom).
Expected: audio now plays **only** through the external driver; the internal speaker is silent. Loudness clearly exceeds the original internal-only setup. (Acceptance criteria 2 + 3.)

---

## Task 4: Confirm firmware is unchanged

**Files:** `devices/atom-echo.yaml` (must be unmodified).

- [ ] **Step 1: Verify no change to atom-echo.yaml**

Run: `git status --porcelain devices/atom-echo.yaml`
Expected: **empty output** (no modification). Acceptance criterion 4.

---

## Task 5: Update DEVICES.md

**Files:**
- Modify: `docs/DEVICES.md` — kitchen device row, capabilities table, kitchen wiring section, 0.5 W correction.

- [ ] **Step 1: Correct the internal speaker wattage and note the external amp in the kitchen device row**

In the "Kitchen — M5Stack Atom Echo" device table, change the Speaker row from the internal-only 1 W description to reflect 0.5 W internal and the new external amp. Replace:

```markdown
### Kitchen — M5Stack Atom Echo (unmodified)
```

with:

```markdown
### Kitchen — M5Stack Atom Echo + external amp
```

and update the Speaker row to:

```markdown
| Internal speaker | Internal NS4168 amp → built-in 0.5 W speaker (disconnected — replaced by external amp) |
| External amp | 1× MAX98357A as a passive parallel I²S listener on G19/G33/G22 (+12 dB) |
| External speaker | One 4 Ω driver on the MAX98357A `+ / −` output |
```

- [ ] **Step 2: Update the capabilities table**

In the Capabilities table, change the "External larger-driver speakers" row so Kitchen is now ✓:

```markdown
| External larger-driver speakers | ✓ (1× MAX98357A) | ✓ (2× MAX98357A, dual mono) |
```

And update the "Internal speaker fallback" row — Kitchen no longer has one:

```markdown
| Internal speaker fallback | — (disconnected) | ✓ (HA-toggleable switch) |
```

- [ ] **Step 3: Replace the kitchen wiring section**

The kitchen section currently reads "No external wiring. Everything lives inside the M5Stack case." Replace that paragraph and its GPIO table's intro so it documents the external amp. Replace:

```markdown
### Kitchen — Atom Echo

No external wiring. Everything lives inside the M5Stack case.

| GPIO | Function |
|---|---|
| GPIO33 | I²S LRCLK (mic + internal amp) |
| GPIO19 | I²S BCLK (shared) |
| GPIO23 | PDM mic data in |
| GPIO22 | I²S DOUT → internal NS4168 amp |
| GPIO39 | Button (active LOW, internal pull-up) |
| GPIO27 | SK6812 RGB LED data |
```

with:

```markdown
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
```

- [ ] **Step 4: Verify the doc renders and is internally consistent**

Run: `git diff docs/DEVICES.md`
Expected: the kitchen device row, capabilities table, and kitchen wiring section all reflect the external MAX98357A + 0.5 W correction; no leftover "unmodified" / "No external wiring" / "1 W" text in the kitchen sections.

- [ ] **Step 5: Commit**

```bash
git add docs/DEVICES.md
git commit -m "docs(atom): document external MAX98357A amp on kitchen Atom Echo

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Acceptance criteria (from spec)

1. ✅ MAX98357A wired to G19/G33/G22 + 5V/GND; GAIN→GND — Tasks 1–2.
2. ✅ External driver audibly louder for PTT + TTS — Task 2/3 checks.
3. ✅ Internal speaker silent (disconnected) — Task 3.
4. ✅ `devices/atom-echo.yaml` unchanged — Task 4.
5. ✅ `docs/DEVICES.md` updated — Task 5.
