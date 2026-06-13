# Speaker case — sound-first, PR-loaded, intercom-capable

Wall-mounted enclosure for **one Dayton Audio PS95-8 3.5" full-range driver** on the
front baffle plus a **side-mounted passive radiator** (tuned ~75 Hz). A vertical
stack: a **sealed speaker chamber** on top (~1.5 L net), a **vented electronics bay**
below, split by an internal divider with a single sealed wire pass. Intercom (mic +
PTT) is a secondary role; the primary purpose is good music playback.

External size: **~158 × 159 × 118 mm** (W × H × D).  
Net chamber volume: **1.5995 L** (~1.6 L; ≥ the 1.4 L `vol_target` floor in the
asserts).

Design rationale, BOM, EQ, and wiring:
`docs/superpowers/specs/2026-06-13-speaker-case-hardware-design.md`

---

## Parts

- `body` — shell with the sealed speaker chamber (PS95-8 on the front baffle, PR on
  the +x side wall), the sealing horizontal divider + single wire pass, and the
  electronics bay (S3 friction pocket, DAC/buck/trigger standoffs, mic mount + front
  perforation, PTT bore, USB-C bottom exit)
- `rear` — flat gasketed lid with blind keyhole wall-mount bosses + inner TPA3116 amp
  standoffs
- `grille` — optional snap-on protective cover over the driver

There is no `button` part — the PTT switch is a panel-mount momentary through a front
bore; it is not printed.

## Build

```bash
# render all three parts
./build.sh            # -> stl/{body,rear,grille}.stl

# or render one at a time
/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD \
  -D 'part="body"' -o stl/body.stl speaker-case.scad

# run the assert harness + render smoke checks
./test.sh
```

Assembled preview: open `speaker-case.scad` in the OpenSCAD GUI with the default
`part="all"`.

---

## Electronics bay — boards and wiring

Five boards fit the vented bay beneath the divider:

| Board | Mount | Location |
|---|---|---|
| ESP32-S3 DevKitC-1 (N16R8) | friction pocket (no screw holes) | front baffle, center |
| GY-PCM5102A I²S DAC | 4 M2 standoffs | front baffle, left |
| MP1584 buck (15 V → 5 V) | 4 M2 standoffs | front baffle, right |
| CH224K PD trigger (15 V) | 4 M2 standoffs | front baffle, lower-right |
| TPA3116 mono class-D amp | 4 M2 standoffs | **rear-lid inner face**, centered |

Front-panel features in the bay:
- **ICS-43434 I²S MEMS mic** — friction pocket on the front baffle + a 7-hole
  perforation cluster through the baffle face (1 center + 6 on a ring)
- **PTT panel-mount momentary switch** — 12.2 mm bore through the front wall, lower
  section; nut/flat relief behind the panel
- **USB-C power IN** — bottom-edge cutout aligned to the CH224K USB-C receptacle

### Wiring map

```
USB-C PD charger (15 V, 30 W+)
  └─► CH224K (set 15 V) ─┬─► TPA3116 (VCC 15 V) ─► PS95-8 (8 Ω, front baffle)
                         │        ▲ IN+ ◄── PCM5102 L-out              ║ side panel
                         └─► MP1584 → 5 V ─► ESP32-S3               ╚═► PR (~75 Hz)

ESP32-S3 ── I²S out ─► PCM5102A DAC ── analog L ─► TPA3116
          ── I²S in  ◄─ ICS-43434 mic                 (intercom — secondary)
          ── GPIO ────► PTT switch → GND               (intercom — secondary)

COMMON STAR GROUND: CH224K / TPA3116 / MP1584 / S3 / PCM5102 / mic grounds all tied.
```

Driver wires (TPA3116 out) run up through the **single sealed divider wire pass**
into the speaker chamber, then to the PS95-8 terminals. Seal the pass with silicone
after wiring. All inter-board jumpers in the bay are free-air.

---

## Print & assembly notes

**Printing:**
- Orient back-down: flat front baffle + open back; no supports needed.
- Print the **speaker chamber airtight** (≥ 4 perimeters; optionally a thin interior
  coat of epoxy or shellac on the chamber walls).
- The electronics bay does not need to be airtight.

**Driver and passive radiator:**
- Foam gasket ring under the PS95-8 flange (groove provided on the baffle); 4 × M2
  self-tap into the boss circle.
- Foam gasket ring under the PR flange (groove on the +x side wall); 4 × M2
  self-tap into the side-panel boss circle.
- **PR tuning is empirical:** adjust the PR mass, measure Fb, target ~75 Hz. The PR's
  excursion limit often sets the max clean SPL — check both driver and PR excursion at
  high volume.

**Rear lid:**
- Foam strip in the lid perimeter gasket groove.
- Foam tape on the divider's back edge (chamber-to-lid seam).
- 4 × M3 self-tap the lid to the corner bosses.
- The TPA3116 mounts on the lid's inner face; its standoffs point into the bay when
  the lid is installed.

**Polyfill:** add loosely in the **speaker chamber only** (not the bay).

**EQ and driver protection (server-side in Music Assistant):**

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | ~75–80 Hz (Fb) | 12–24 dB/oct | — |
| Gentle shape (if needed) | Peaking | ~110–120 Hz | Q ≈ 1 | −1 to −2 dB |

The HPF at Fb and a conservative volume ceiling are **mandatory** — below Fb a PR lets
cone excursion run away, and TTS/wake bypasses MA DSP so there is no software
backstop.

---

## Wall mount

Two blind keyhole bosses on the lid's outer face (upper, over the chamber zone, 120 mm
apart) hang the box on two wall screws. The bosses are cut through the boss only — the
lid panel behind stays solid, keeping the chamber sealed.

---

## Confirm before printing `[confirm vs hardware]`

The following defaults must be verified against parts in hand before the first print;
the asserts enforce fit, not the absolute numbers:

- PS95-8 cutout (76 mm), bolt-circle diameter (83 mm, 4 screws), seated depth (45 mm)
- PR frame OD (80 mm), cutout (66 mm), bolt-circle (72 mm), intrusion depth (25 mm);
  confirm tuning mass for Fb ~75 Hz
- Board footprints: S3 devkit (69 × 26 mm), PCM5102 (27 × 27 mm), MP1584 (22 × 17 mm),
  CH224K (25 × 15 mm), TPA3116 mono (50 × 30 mm)
- USB-C receptacle depth (usb_z = 8 mm from front face) and slot width (10 mm)
- PTT panel-mount switch thread (12 mm thread body → 12.2 mm bore)
- Wall-mount screw spacing and head diameter vs your keyhole geometry
