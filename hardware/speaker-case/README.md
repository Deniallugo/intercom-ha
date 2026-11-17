# Speaker case — 53 mm vertical pair, ported, intercom-capable

Wall-mounted enclosure for **two AIYIMA 53 mm (2") full-range drivers stacked
vertically**, dual mono, in a **ported 0.70 L chamber tuned to ~145 Hz**. Speaker
chamber on top, vented electronics bay below, split by a divider with four sealed
terminal bolts. Music first; intercom (mic + PTT) second.

> **Firmware status:** `devices/speaker-s3.yaml` is playback only. The case has the
> ICS-43434 mic pocket and the PTT bore, but neither the mic nor the button is
> implemented in the firmware yet.

External size: **86 × 202 × 88 mm** (W × H × D).
Net chamber volume: **0.7015 L** (asserted ≥ 0.65 L).

## What this box can and cannot do

| | |
|---|---|
| Flat response | ~135 Hz – 15 kHz |
| Max SPL, midrange | ~94 dB @ 1 m (thermal) |
| Max SPL at 150 Hz | **~85 dB @ 1 m (excursion-limited)** |
| Max SPL at 60 Hz | ~69 dB — inaudible under music |

Two cones give Vd ≈ 2.9 cm³: **no enclosure reaches below ~120 Hz.** What helps, best
first: corner placement (+6 to +9 dB below 250 Hz), the port (+3 dB at 140–170 Hz), a
+4 dB low shelf in Music Assistant, a powered sub on the line-out.

## Parts

- `body` — chamber, divider, electronics bay (devkit pocket, PTT bore, mic pocket,
  bottom USB-C / sub jack, +x service slot)
- `rear` — gasketed lid with keyhole bosses and DAC / amp standoffs
- `port` — tuned port tube, separate so Fb can be changed

No grille part: a perforated disc hurts the treble more than it protects. Use open mesh.

## Build

```bash
./build.sh            # -> stl/{body,rear,port}.stl
./test.sh             # asserts + render checks
"$OPENSCAD" -D 'part="body"' -o stl/body.stl speaker-case.scad   # one part
```

`part="all"` (the default) is the assembled preview.

## Tuning the port

Reprint `port` with a different `port_len`:

| `port_len` | Fb |
|---|---|
| 40 mm | ~156 Hz |
| **49 mm (default)** | **~145 Hz** |
| 60 mm | ~134 Hz |
| 75 mm | ~122 Hz |

`Lv = 23562.5·d²/(Fb²·Vb) − 0.732·d` (d in cm, Vb in litres).

**Don't tune below ~130 Hz:** under Fs (145 Hz) the cones can't drive the port and the
box unloads. Peak port air speed at Xmax is ~8.4 m/s, under the ~17 m/s chuffing limit.

## Electronics bay — boards and wiring

PAM8406 on 5 V gives 2 × 3 W and clips before a 3–5 W driver dies. A bigger amp
(e.g. TPA3116 on 15 V, ~40 W) would destroy it on one full-scale sample.

| Board | Mount | Location |
|---|---|---|
| ESP32-S3 DevKitC-1 (N16R8) | friction pocket (no screw holes) | front baffle, bay |
| GY-PCM5102A I²S DAC | 4 M2 standoffs | **rear-lid inner face**, left |
| PAM8406 5 V stereo class-D | 4 M2 standoffs | **rear-lid inner face**, right |
| ICS-43434 I²S MEMS mic | friction pocket + gasket seat | front baffle, left of the PTT |

Front-baffle features (all in the bay):
- **PTT** panel-mount switch: 12.4 mm bore in a 2.5 mm thinned panel, nut counterbore behind.
- **Mic**: one 2 mm port with the mic pressed onto a gasket — resonance ~14 kHz, clear of speech.
- **Bottom wall**, cables straight down: panel-mount USB-C 5 V in (a breakout board would
  collide with a lid boss) and the 3.5 mm sub line-out.
- **+x service slot**: the devkit's own USB-C, for flashing and logs.

### Wiring map

```
USB-C 5 V charger (2 A+)
  └─► panel-mount USB-C ─┬─► PAM8406 VCC
                         └─► ESP32-S3 5V pin

ESP32-S3 ── I²S out ─► PCM5102A ─┬─ L ─┐
                                 └─ R ─┤ 2x 10k passive sum
                                       ├──► attenuator ──► PAM8406 IN (both channels)
                                       └──► 3.5 mm jack ──► powered sub (its own LPF)

PAM8406 OUT A ── 330 uF ──► divider terminals ──► driver 1 (upper)
PAM8406 OUT B ── 330 uF ──► divider terminals ──► driver 2 (lower)
```

**Three things that bite if skipped:**

1. **The 330 µF series caps are required.** One per driver, bipolar/NP, ≈120 Hz corner
   into 4 Ω. TTS and chimes bypass Music Assistant's EQ; these are the only high-pass
   they get, and they also cut LF intermodulation.
2. **Attenuate the DAC before the amp.** PCM5102 full-scale is ~2.1 Vrms; PAM8406's
   fixed ~24 dB gain would ask for 33 V from a 5 V rail and clip continuously. Use the
   module's onboard pot or a 10 kΩ/1.2 kΩ divider (≈ −19 dB).
3. **Do not power the amp through the devkit's USB port.** Peak draw is ~2 A; that path
   goes through the devkit's Schottky and a thin trace. Feed both from the USB-C socket.

Passive L+R summing keeps the firmware at `channel: stereo` and gives drivers and sub a
true mono mix.

Driver wires cross the divider through **four M3 brass terminal bolts** with O-rings, not
a wire hole: a leak in a 0.7 L box ruins the tuning. BTL outputs have no common return,
so all four conductors are separate. Solder each series cap between amp and terminal.

## Print & assembly notes

**Printing:**
- **Back down**, no supports (the 6 mm front chamfer allows it).
- **PETG or ASA** if it ever sees sun (PLA creeps at ~60 °C). PLA-CF damps panels better.
- 0.6 mm nozzle, 0.24 mm layers, **5 perimeters**, "ensure vertical shell thickness",
  25 % gyroid. Perimeters make it airtight; infill leaks.
- Brush a coat of 2-part epoxy or shellac inside the chamber.
- **Pressure-test before assembly:** seal the drivers and the port, blow into a terminal
  bore, and soap the seams. A leak invalidates the whole alignment.

**Drivers:**
- Foam ring under each flange; 4 × M2 self-tap. Don't drill the blind pilots deeper.
- Both drivers **same polarity**.
- Keep them stacked vertically: comb filtering then lands in the vertical plane.

**Rear lid:**
- **M3 heat-set inserts** in the corner bosses (4.0 mm bore): the lid is opened often and
  self-tap would strip.
- Foam strip in the lid gasket groove; foam tape on the divider's back edge.

**Polyfill:** loosely in the speaker chamber only, and keep it clear of the port's inner
mouth.

**EQ (server-side in Music Assistant):**

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | ~130 Hz | 12–24 dB/oct | — |
| Body | Low shelf | ~250 Hz | — | +4 dB |

Always pair the shelf with the high-pass.

## Wall mount

Two recessed keyholes on the lid, 50 mm apart **vertically**. Pass the screw heads
through the round end at the bottom, then let the box drop onto the slots.

Mount **flush to the wall** (a gap notches the response) and leave ≥ 30 mm free on the
**+x port side**.

## Confirm before printing `[confirm vs hardware]`

- **Driver bolt circle (49 mm).** The datasheet figure is self-contradictory; measure yours.
- **Xmax and Vas** — not measured; they set the box volume and every SPL figure above.
- Driver cutout (46 mm), frame OD (53 mm), seated depth (28 mm)
- Board footprints: S3 devkit (69 × 26 in `params.scad`; a real board measured 63 × 28 — check yours), PCM5102 (27 × 27), PAM8406 (24 × 16)
- Panel-mount USB-C socket: cutout (9.5 × 4.5 mm) and screw pitch (20 mm) vary by module
- PTT panel-mount switch thread (12 mm → 12.4 mm bore) and nut across flats (16.5 mm)
- Wall-mount screw head diameter vs the keyhole geometry
