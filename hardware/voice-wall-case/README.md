# Voice S3 Wall Unit

A 3D-printable enclosure for [`devices/voice-s3.yaml`](../../devices/voice-s3.yaml), mounted on a wall.

It is **flat**: one layer of boards against the wall, under a removable front panel.

- **Tray:** screwed to the wall, carrying **every board**:
  - the ZK-502MT in the middle on standoffs, parts facing the front, knobs up through the top, exactly centred;
  - on your left, the ESP32-S3 devkit standing on the plate;
  - on your right, the PCM5102A at the top and the MP1584 at the bottom, next to the DC jack, both flat on the plate.
- **Mic:** the INMP441 sits in the top wall, beside the knobs, listening up through a grille.
- **Wire channel:** the board-to-board runs (I2S, 5 V, the DAC's patch cable) go along a clear channel at the bottom front, under the amp's connectors and behind the panel.
- **Panel:** just a flat front with the flexure button and the knob names. **Its only wires are the button switch's two, on a small plug.** Unplug it and the panel comes away, leaving every board and terminal in front of you.

| | |
|---|---|
| Outside | **143 × 101 × 37 mm** (W × H × D), 34 mm walls behind a 3 mm panel, 0.54 L |
| Printed parts | 4: tray, panel, switch bridge, mic clamp |

**The Fusion model in [`fusion/`](fusion/) is the source of truth.** It builds every printed part and also every electronic part as its own component. You can drag a part in Fusion, run `sync`, and the case follows it ([fusion/README.md](fusion/README.md)).

- Positions are in [`vwc/placement.py`](fusion/VoiceWallCase/vwc/placement.py).
- Every other number is in [`vwc/params.py`](fusion/VoiceWallCase/vwc/params.py).

```
fusion/test.sh   # design checks + every part built offline + sync round-trip — no Fusion needed
```

The OpenSCAD files in this folder (`voice-wall-case.scad`, `modules/`) are the **old two-box design**. They are kept for reference and are not maintained.

> **Status: not printed yet.** The layout has only been checked offline. Several amp dimensions come from photos; each is tagged `[photo]` or `[assumed]` in `params.py`. Print the two coupons first. See [Measurements still needed](#measurements-still-needed).

---

## Layout

Front view with the panel off. +x in the model is the viewer's **left**: box-local is right-handed with z running into the box.

```
          knobs on top:  VOLUME · BASS · TREBLE        mic grille
 ┌──────────────────────────────────────────────────────────────────┐
 │ ┌────────────┐ ┌───────────────────────────────┐ ┌─────────────┐ │
 │ │ DAC        │ │                               │ │             │ │
 │ └──socket────┘ │      ZK-502MT, upright,       │ │  ESP32-S3   │ │
 │                │      parts facing you         │ │  devkit     │ │
 │ ┌────────────┐ │                               │ │ (standing)  │ │
 │ │ MP1584     │ └───────────────────────────────┘ │             │ │
 │ └────────────┘   DC jack ·· speaker block ·· AUX jack └─────────┘ │
 │ ═══════════════ wire channel (I2S, 5 V, patch) ═════════════════ │
 └──DC plug── speaker holes ───────────────────────────── USB-C ────┘  ← bottom
     (your right)                                         (your left)
```

**Front panel:** the knob names along the top edge over each knob, engraved 0.6 mm deep to fill with paint; the flexure button below them, above the amp's heatsink (its switch sits behind it); nothing else.

**Heat.** The heatsink stands vertical, so the box works as a chimney: air comes in through slots in the bottom and leaves through two rows of slots in the top, one in front of the faceplate and one behind it.

---

## Parts

| Part | Prints | What it carries |
|---|---|---|
| `tray` | back face down | back plate + top, bottom, sides. Amp standoffs; devkit pocket (left); DAC seat over the MP1584 pocket (right). **Top:** knob holes, mic seat + 7-hole grille, vents, the windows the panel's hooks click into. **Bottom:** DC plug hole, 2 speaker-cable holes, devkit USB-C window, vents, 2 panel screws. **Plate:** 2 keyholes behind the amp, 1 locking screw under it, 2 cable knock-outs |
| `panel` | front face down | flat front: flexure button, bridge feet, knob names, a locating lip, 2 snap hooks at the top, 2 screw bosses at the bottom |
| `bridge` | flat | the bar behind the button that holds the tactile switch; 2 × M2 into the feet |
| `clamp` | flat | presses the mic board onto its gasket; 2 × M2 |
| `coupon-button` | front face down | the middle of the panel: button, nub, feet. **Print first** to check the feel |
| `coupon-top` | — | the strip of the tray's top with the knob holes and hook windows |

**Material:** PETG for the panel, because the flexure arms are 1.2 mm thick. PLA works but creeps under a constant press.

**Hardware:**
- M3 screws:
  - 4 × M3 self-tapping, about 6 mm, for the amp board;
  - 2 × M3×8 countersunk self-tapping, up through the bottom into the panel.
- M2 screws:
  - 2 × M2 for the switch bridge;
  - 2 × M2 for the mic clamp.
- Wall: 2 × 4 mm wood screws with heads up to 8.5 mm across, for the keyholes; 1 × 4 mm countersunk screw for locking; 3 wall plugs.
- Parts:
  - 12 × 12 mm 4-pin tactile switch, with a 2-pin JST lead;
  - MP1584;
  - right-angle 3.5 mm patch cable, about 15 cm;
  - Ø12 mic gasket **with its centre cut to at least 9 mm**, so all 7 grille holes open onto the port.

---

## The button

The disc on the panel is 24 mm across. It is cut free by **three stepped-spiral slots**, which leave three arms about 22 mm long. The ring around it is thinned from the inside to 1.2 mm.

- **How it moves.** Pressing anywhere moves the disc straight in. A 3 mm nub on its back presses an ordinary tactile switch on a small bridge screwed to two feet behind it.
- **Click.** The click comes from the switch. The arms add about 2 N/mm.
- **Strength.** At 1 mm of travel the arms see about 14 MPa, under the 20 MPa allowed for PETG fatigue.

To tune it, change these in `params.py`:
- **Softer or stiffer:** `btn_flex_t` (arm thickness), `btn_step` (arm width), `btn_arc_in` / `btn_arc_out` (arm length).
- **Bigger or smaller disc:** `btn_disc_d`.
- **Switch contact:** `btn_preload`, if the switch fires too early or never.

## The mic

The INMP441 lies in a gasket seat in the top wall, beside the knobs, port facing up. It hears through a **grille of 7 × 1.5 mm holes** within a 7.5 mm circle, about four times the open area of the single 2 mm port it replaces, which muffled the sound. It sits at the front edge of the top, as close to the room as the box allows.

---

## How it goes together

**Hanging it.** The tray hangs on two screws through keyholes and is held down by one locking screw. It comes off the wall by taking off the panel and that one screw. **The amp never has to come off.**

1. **Mark the wall:** hold the empty tray level against the wall, where it will hang. Mark the **top end of each keyhole slot** (the slots run up from the round entry holes, behind where the amp goes), because that is where the screw ends up once the box drops. Also mark the locking-screw hole low in the middle. Drill and plug all three.
2. **Wall screws:** drive the two keyhole screws in, leaving their heads **2.5 mm proud** of the wall.
3. **Boards on the tray, on the bench:**
   - **amp:** screw the ZK-502MT onto its standoffs, then feed the two speaker cables up through their holes under the barrier block and screw them in;
   - **devkit:** press it into its pocket;
   - **MP1584:** into its pocket, set to 5.0 V **first**;
   - **DAC:** onto its seat;
   - **mic:** onto its gasket in the top, with the clamp.
4. **Wire everything on the tray** (see [Wiring](#wiring)). Run the I2S, 5 V and patch leads along the bottom wire channel, so they stay clear of the button's switch.
5. **Hang it:** put the tray against the wall with the screw heads in the keyhole entries and push it down 9 mm. Drive the locking screw through the bottom middle of the back plate, under the amp's connectors.
6. **Panel:** screw the tactile switch's bridge to the feet and plug its lead into the devkit. Push the panel home: the hooks click into the top. Then drive 2 × M3 up through the bottom into its bosses.
7. **Power:** plug the charger **straight up into the bottom**. The barrel jack faces down, right above its hole.

**To take it down:** take out the 2 bottom panel screws, press the two hooks down through their windows in the top, pull the panel forward and unplug the switch. Undo the locking screw, lift the tray 9 mm and pull it off the screws.

---

## Wiring

All of it is on the tray except the button switch.

```
24 V adapter ── [your switch, wherever you want it] ── plug, straight up into the amp barrel jack
                                                          │ (tap at the jack's solder pins)
                                                          └── MP1584 IN ── 5.0 V ──► devkit 5V / GND
DAC 3.5 mm socket ──(right-angle plug, along the wire channel)──► amp AUX jack
Devkit ──(I2S: 5 leads, along the wire channel)──► DAC
Amp L± R± terminals ──(straight down, out of the two holes under the block)──► speakers
Tactile switch on the panel ──(2-pin JST, ~15 cm)──► devkit GPIO / GND
```

- **Set the MP1584 to 5.0–5.1 V on the bench before connecting the devkit.** The modules often ship set above 5 V. Its input limit is 28 V, so check the adapter's unloaded voltage too.
- **Power switch.** There is no switch in the box. Put one in the 24 V line wherever suits you. Placed before the barrel jack it turns the ESP32 off too; to keep the voice device online, switch only the amp's feed and take the MP1584's 24 V from the unswitched side.
- **Speaker terminals.** Confirm L+/L−/R+/R− on the barrier block from the silkscreen before connecting both speakers. The amp is bridge-tied, so never join a minus to ground.
- **Interference.** Keep the 5 V pair twisted and away from the AUX cable.

---

## Measurements still needed

Measured or fit-checked so far: the board (73 to the faceplate front face, holes 52 × 43), the tallest part (20 mm above the PCB underside, the board included), the faceplate thickness (1.6), the pot shafts (13 past the faceplate), the AUX plug (17 past the board edge), the rear-edge connectors and the charger plug, the parts behind the button, the new devkit (70 × 26, two USB-C as before), the knobs (they sit fully down on 8.7 mm of shaft above the top).

Still open, in order of how much they move the design:

1. **The pot axis height** above the PCB underside (`ctrl_axis`, 9 from photos). It sets where the knob holes sit across the top's depth. Print `coupon-top` to check it.
2. **The faceplate's width and height** (`amp_face_w`, `amp_face_h`, 60 × 18 assumed) and where its bottom edge sits against the PCB (`amp_face_y0`).
3. **Board width** (60, from the listing).
4. **The DAC's socket** height (`dac_jack_h`, 6.5 from the old case).
5. **MP1584** tallest part (`mp_h`, 5 assumed).

**Print order:** `coupon-button` (button feel) → `coupon-top` (knob holes, hook windows) → `tray` (boards on it) → `panel`.
