# Speaker case — 53 mm vertical pair, ported, intercom-capable

Wall-mounted enclosure for **two AIYIMA 53 mm (2") full-range drivers stacked
vertically** on the front baffle, dual mono (one amp channel each), in a **ported
0.70 L chamber tuned to ~145 Hz**. A vertical stack: the sealed/ported speaker chamber
on top, a vented electronics bay below, split by a divider crossed by four sealed
terminal bolts. Intercom (mic + PTT) is a secondary role; music playback is primary.

External size: **86 × 194 × 88 mm** (W × H × D).
Net chamber volume: **0.7015 L** (≥ the 0.65 L `vol_target` floor in the asserts).

Design rationale, the acoustic arithmetic, and the honest performance limits:
`docs/superpowers/specs/2026-07-29-speaker-case-53mm-review.md`

## What this box can and cannot do

| | |
|---|---|
| Flat response | ~135 Hz – 15 kHz |
| Max SPL, midrange | ~94 dB @ 1 m (thermal) |
| Max SPL at 150 Hz | **~85 dB @ 1 m (excursion-limited)** |
| Max SPL at 60 Hz | ~69 dB — inaudible under music |

Bass is displacement, and two cones at Xmax give Vd ≈ 2.9 cm³. **No enclosure choice
reaches below ~120 Hz.** The levers that do work, best value first: corner or
wall-junction placement (+6 to +9 dB below 250 Hz, free), the port (+3 dB at 140–170 Hz),
a +4 dB low shelf in Music Assistant (free at sane listening levels), and a powered
subwoofer on the line-out for anything below 120 Hz.

---

## Parts

- `body` — shell with the ported chamber (two drivers on the front baffle with local
  stiffening pads, tuned port on the +x side wall), the sealing divider + four sealed
  terminal bolts, and the electronics bay (S3 friction pocket, PTT bore, bottom-wall
  mic seat / USB-C breakout / sub jack, +x service slot)
- `rear` — flat gasketed lid with recessed keyhole wall-mount bosses + inner DAC and
  amp standoffs
- `port` — the tuned port tube, printed separately **so Fb is tunable**

There is no `grille` part. A 22 %-open perforated disc 4 mm off a cone that runs to
15 kHz costs more than it protects. Use open metal mesh if you need protection.

## Build

```bash
# render all three parts
./build.sh            # -> stl/{body,rear,port}.stl

# or render one at a time
/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD \
  -D 'part="body"' -o stl/body.stl speaker-case.scad

# run the assert harness + render smoke checks
./test.sh
```

Assembled preview: open `speaker-case.scad` in the OpenSCAD GUI with the default
`part="all"`.

---

## Tuning the port

Print a different `port` — that is the whole point of it being a separate part.

| `port_len` | Fb |
|---|---|
| 40 mm | ~156 Hz |
| **49 mm (default)** | **~145 Hz** |
| 60 mm | ~134 Hz |
| 75 mm | ~122 Hz |

`Lv = 23562.5·d²/(Fb²·Vb) − 0.732·d` (d in cm, Vb in litres).

**Do not tune lower than ~130 Hz.** Below Fs (145 Hz) the cones cannot drive the port
and the box unloads — that is exactly the mistake the superseded 75 Hz passive radiator
made. Port area is 3.14 cm² (≥ 10 % of total cone area); peak air velocity at Xmax is
~8.4 m/s, well under the ~17 m/s chuffing threshold.

---

## Electronics bay — boards and wiring

The 15 V PD tree is gone. A 4 Ω 53 mm driver wants 3–5 W; TPA3116 on 15 V into 4 Ω
delivers ~40 W and would destroy it on one full-scale sample. PAM8406 on plain 5 V gives
2 × 3 W and **clips before the driver dies** — the amp's ceiling is free protection.
That deletes the CH224K, the MP1584 and the TPA3116: five boards down to three.

| Board | Mount | Location |
|---|---|---|
| ESP32-S3 DevKitC-1 (N16R8) | friction pocket (no screw holes) | front baffle, bay |
| GY-PCM5102A I²S DAC | 4 M2 standoffs | **rear-lid inner face**, left |
| PAM8406 5 V stereo class-D | 4 M2 standoffs | **rear-lid inner face**, right |
| USB-C 5 V breakout (5.1 kΩ CC) | 4 M2 standoffs | bay **bottom wall** |

Bottom-wall features (all in the bay):
- **ICS-43434 I²S MEMS mic** — board-locating recess + gasket seat + **one 2 mm port**.
  Press the mic's port onto the gasket: near-zero front volume puts the port resonance
  at ~15 kHz. (The superseded 7 × 1.5 mm cluster was a ~5.7 kHz resonator sitting on
  top of speech.) Two M2 posts flank the seat; gasket compression makes the seal.
- **USB-C 5 V power IN** — breakout lies flat, connector facing −x, cable exits a slot
  in the −x side wall.
- **3.5 mm sub line-out** — see below.

Other breaches:
- **PTT panel-mount momentary switch** — 12.4 mm bore through a locally thinned
  (2.5 mm) panel, bottom-center of the front baffle, with a nut counterbore behind and
  a tactile halo ring on the outer face.
- **+x side-wall service slot** — exposes the devkit's own USB-C ports for the first
  flash and serial logs.

### Wiring map

```
USB-C 5 V charger (2 A+)
  └─► USB-C breakout ─┬─► PAM8406 VCC
                      └─► ESP32-S3 5V pin

ESP32-S3 ── I²S out ─► PCM5102A ─┬─ L ─┐
                                 └─ R ─┤ 2x 10k passive sum
                                       ├──► attenuator ──► PAM8406 IN (both channels)
                                       └──► 3.5 mm jack ──► powered sub (its own LPF)

PAM8406 OUT A ── 330 uF ──► divider terminals ──► driver 1 (upper)
PAM8406 OUT B ── 330 uF ──► divider terminals ──► driver 2 (lower)
```

**Three things that bite if skipped:**

1. **The 330 µF series caps are not optional.** One per driver leg, bipolar/NP,
   ≈120 Hz corner into 4 Ω. Both design docs called a high-pass "mandatory" because TTS
   and wake-word bypass Music Assistant's DSP, and then shipped no hardware backstop.
   This is it. Its bigger payoff is cutting intermodulation distortion — unchecked LF
   excursion modulates the midrange the same cone is reproducing.
2. **Attenuate the DAC before the amp.** PCM5102 full-scale is ~2.1 Vrms; PAM8406's
   fixed ~24 dB gain would ask for 33 V from a 5 V rail and clip continuously. Use the
   module's onboard pot or a 10 kΩ/1.2 kΩ divider (≈ −19 dB).
3. **Do not power the amp through the devkit's USB port.** Peak draw is ~2 A; that path
   goes through the devkit's Schottky and a thin trace. Feed both from the breakout.

Passive L+R summing means **`devices/speaker-s3.yaml` needs no change** — it stays
`channel: stereo`, and both drivers and the sub get a true mono mix instead of one
arbitrary channel.

Driver wires cross the divider through **four M3 brass terminal bolts** with an O-ring
under each washer — not a wire pass. Dual mono on a BTL amp has no common return, so
all four conductors are independent, and in a 0.7 L box a silicone-smeared hole is the
leak that ruins Qtc. Solder each series cap between the amp output and its bay-side
terminal.

---

## Print & assembly notes

**Printing:**
- Orient **back-down**: flat baffle up, open back on the plate, no supports. The front
  edge is a 6 mm **chamfer** rather than a fillet precisely so it prints support-free in
  this orientation (a tangent fillet would start as a 90° overhang).
- **PETG or ASA**, not PLA, if the wall ever sees sun — PLA's Tg ≈ 60 °C creeps under
  sustained load. PLA-CF is a good compromise: higher internal damping than plain PLA,
  which lowers panel Q.
- 0.6 mm nozzle, 0.24 mm layers, **5 perimeters**, "ensure vertical shell thickness:
  all", 25 % gyroid. Airtightness comes from perimeters, not infill — with normal
  infill, air migrates through the infill matrix from the chamber into the bay and out
  the PTT/USB breaches.
- Brush a coat of 2-part epoxy or shellac inside the chamber.
- **Pressure-test before assembly:** seal the drivers and the port, blow into a terminal
  bore, and soap the seams. A leak invalidates the whole alignment.

**Drivers:**
- Punched foam ring in the baffle recess under each flange; 4 × M2 self-tap into the
  blind pilots. The pilots leave 1.5 mm of solid floor — do not chase them deeper.
- Both drivers **same polarity**. They are a coherent vertical pair, not stereo.
- The vertical stack is deliberate: comb filtering lands in the vertical plane, where
  nobody moves, and the horizontal polar response stays clean. Never mount them
  side by side.

**Rear lid:**
- **M3 heat-set inserts** in the four body corner bosses (4.0 mm bore). This is the
  joint opened repeatedly for wiring and polyfill; self-tap would strip. The drivers
  keep self-tap pilots because the *port*, not the driver, is the tuning element here.
- Foam strip in the lid perimeter gasket groove; foam tape on the divider's back edge.

**Polyfill:** loosely in the speaker chamber only, and keep it clear of the port's inner
mouth.

**EQ (server-side in Music Assistant):**

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | ~130 Hz | 12–24 dB/oct | — |
| Body | Low shelf | ~250 Hz | — | +4 dB |

The shelf is free at normal listening levels (at 75 dB you have ~10 dB of excursion
headroom at 150 Hz) and must be paired with the high-pass. The 330 µF caps are the
hardware backstop for everything that bypasses this DSP.

---

## Wall mount

Two recessed keyhole bosses on the lid's outer face, **stacked vertically** 50 mm apart
over the chamber. 120 mm side-by-side spacing cannot fit an 86 mm lid, and on a 194 mm
tall box two vertically-spaced screws resist the tip-out moment far better than two at
the same height. Each boss has a wall-side retaining plate with the keyhole cut through
it, backing onto a head-clearance cavity floored by the solid lid panel — so the head is
captured while the panel stays solid and the chamber sealed. The head-circle sits at the
bottom: pass the heads through, then let the box settle so the shanks ride up the slots.

Mount it **flush to the wall** (a 100 mm standoff puts a cancellation notch at ~857 Hz)
and keep ≥ 30 mm clear on the **+x port side**.

---

## Confirm before printing `[confirm vs hardware]`

- **Driver bolt circle (49 mm).** The published "4 × on a 43 mm square (60 mm diagonal)"
  is self-contradictory for a 53 mm frame: a 43 mm *square* puts screws at r = 30.4
  (outside the frame), a 43 mm bolt *circle* puts them at r = 21.5 (inside the 46 mm
  cutout). Measure yours. The asserts enforce that it lands between the two.
- **Xmax and Vas** — never measured. Vas picks the box volume; Xmax sets every max-SPL
  number above. Measure both (added-mass or closed-box delta-Fs) before trusting them.
- Driver cutout (46 mm), frame OD (53 mm), seated depth (28 mm)
- Board footprints: S3 devkit (69 × 26), PCM5102 (27 × 27), PAM8406 (24 × 16),
  USB-C breakout (15 × 13)
- PTT panel-mount switch thread (12 mm → 12.4 mm bore) and nut across flats (16.5 mm)
- Wall-mount screw head diameter vs the keyhole geometry
