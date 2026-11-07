# Voice S3 Wall Unit

Parametric enclosure for [`devices/voice-s3.yaml`](../../devices/voice-s3.yaml) mounted on a
wall. It uses two boxes stacked on one wall plate. The **Voice S3 box** on top holds the
ESP32-S3 devkit, PCM5102A, INMP441 and a dome button. The **amplifier box** underneath holds the
ZK-502MT and the MP1584 buck.

The reference parts carry over from [`../voice-case`](../voice-case) unchanged: devkit 63 × 28,
DAC 33 × 20 with its 6 mm socket, INMP441 17 × 15 with its gasket seat, and the 11 mm tactile with
its holder cup. The desk-puck *layout* does not carry over (see [Voice box](#voice-box)).

**The Fusion model in [`fusion/`](fusion/) is the source of truth.** It builds every printed part
and also every electronic part as its own component:

- the ZK-502MT with its pots, jacks and heatsink, plus the knobs;
- the MP1584 and the panel switch;
- the ESP32-S3 devkit, the PCM5102A and the INMP441;
- the tactile switch;
- both 3.5 mm plugs, the DC plug, and the cable routes.

You can move a part in Fusion, run `sync`, and the case follows it. See
[fusion/README.md](fusion/README.md). The positions live in
[`fusion/VoiceWallCase/vwc/placement.py`](fusion/VoiceWallCase/vwc/placement.py), and every other
number in [`vwc/params.py`](fusion/VoiceWallCase/vwc/params.py).

The OpenSCAD here is kept as an independent second build of the same numbers. `fusion/test.sh`
renders the Fusion port offline and diffs it against this OpenSCAD, passing in the current
placement with `-D`.

```
fusion/test.sh   # design checks + sync round-trip + port-vs-OpenSCAD geometry diff
./test.sh        # OpenSCAD asserts + render every part (set $OPENSCAD if not on PATH)
./build.sh       # STLs -> stl/ from the OpenSCAD
openscad -D 'part="section"' voice-wall-case.scad   # cut-away on the pass-through axis
```

> **Status: first fit-check iteration.** Several amplifier dimensions are estimated from photos
> and have not been measured. Every such number is tagged `[photo]` or `[assumed]` in
> [`vwc/params.py`](fusion/VoiceWallCase/vwc/params.py) (and in
> [`modules/params.scad`](modules/params.scad)). Print the coupons and the sled before the shells. See
> [Measurements still needed](#measurements-still-needed).

---

## Layout

All dimensions are in mm. World axes: **x** is across (+x is to your right as you face the
unit), **y** is out from the wall and **z** is up from the bottom of the amp box.

### Side view (wall on the left)

```
 y:   0  6               36 40                                              141
      │  │                │  │                                                │
 z101 ┌──────────────────────┐  lock bracket, 4 thick, on the plate's header block
 z 97 │  ├┐    3 ▲ lift     │                                 ● mic port, top face, 111 off the wall
 z 94 │  ││  ┌──┬─────────────────────────────────────────────────────────────┐
      │ P││  │L │  sleeve     DAC + plug        devkit         holder        │ VOICE BOX 76 W × 48 H
      │ L││  │E │    ▼                                                       ◖ dome Ø40, z70,
 z 46 │ A││  └──┴─────■───────────────────────────────────────────────────────┘   12 proud
      │ T││    6 gap  ■ sleeve, Ø15.2, 52 off the wall
 z 40 │ E││  ┌──┬─────■───────────────────────────────────────────────────────┐
      │  ││  │L │                AMP BOX     76 W × 40 H × 105 D             │ ← knobs: faceplate
      │  ││  │E │  plug zone    rear edge ◄──────── ZK-502MT 73 ────────►    │   window, 13 mm of
 z  0 └──┴┘  └──┴─────────────────────────────────────────────────────────────┘   shaft outside
          ◄ 30 ►  ↓ power and speaker cables leave the channel at the bottom
         channel
```

| | |
|---|---|
| Overall | 84 W × 101 H (plate + lock) × 141 D (wall to box fronts) |
| Wall plate | 84 × 97 × 6, A1-printable flat |
| Each box | 76 W × 105 D (101 shell + 4 lid), with a 30 mm channel behind it |
| Stack gap | 6 mm. It is smaller than the 8 mm peg drop, so the voice box locks the amp box in place |

### Front view

```
            ◄────────────── 84 plate ──────────────►
              ◄──────────── 76 boxes ────────────►
 z 94  ┌─────────────────────────────────┐  (mic port is on the TOP face, 30 back from the front)
       │            ╭───────────╮
       │           │   dome Ø40  │          centre z70 (24 above the voice box bottom)
       │            ╰───────────╯
 z 46  └─────────────────────────────────┘
 z 40  ┌─────────────────────────────────┐
       │ ┌─────────────────────────────┐ │  window 57 × 15, z11.5–26.5. The board's own
       │ │  TREBLE    BASS     VOL  ● │ │  faceplate sits behind it in a 60.6 × 18.6 × 1
       │ └─────────────────────────────┘ │  rebate. LED at the VOL end
 z  0  └─────────────────────────────────┘
       panel power switch: on the RIGHT side wall, 28 up, 89 back from the front face
```

### Depth zones (z measured into the box from its front face)

```
AMP     0─3 front wall │ 2 faceplate front face │ 2→75 board │ 75→77 connector bodies │ 77→101 PLUG ZONE │ 101→105 lid
                         (in its 1 mm rebate)                                            MP1584, AUX plug,
                                                                                         switch body, wire loop
VOICE   0─3 front wall │ →16.8 button holder + pins │ 19.5→51.7 devkit pocket │ 50.1→75.3 DAC pocket │ 75.2 socket face
        → ~87 right-angle AUX plug │ 89 sleeve axis (flange 78.4–99.6) │ 101→105 lid
```

Vertical stack inside the amp box: floor 3, sled 2, standoffs 6, PCB underside at **11**, 18 mm
envelope up to **29**, 8 mm of air over the heatsink, inner top at 37.

---

## Parts

| `part=` | Print orientation | Notes |
|---|---|---|
| `amp-shell` | front face down | faceplate window, heatsink vents, terminal access holes, sleeve hole, panel switch cut-out |
| `amp-lid` | inner face down, legs up | cable window for the barrel plug and speaker wires; 4 pegs |
| `amp-sled` | flat | standoffs on the board's holes, MP1584 pocket. **Reprint this when the holes are wrong, not the shell** |
| `voice-shell` | front face down | button bore + recess + blind M2 pilots; mic gasket seat + clamp posts on the TOP face; sleeve hole |
| `voice-lid` | inner face down, legs up | 4 pegs |
| `voice-tray` | flat | devkit and DAC friction pockets with pin relief, sleeve hole |
| `sleeve` | flange down | 12 ID pass-through, voice floor → amp top |
| `plunger` | flange down | voice-case snap-lip cap with the dome removed |
| `dome` | flat side down | Ø40 visible cap, glued onto the plunger flange. Can be any colour |
| `holder` | floor down | voice-case cup with an 8 mm guide (it was 5) |
| `clamp` | flat | voice-case mic clamp |
| `plate` | **back face down** | keyholes, 4 countersunk wall screws, header block for the lock |
| `lock` | flat | L-bracket over the voice legs |
| `coupon-amp` | front face down | front wall slice. Test-fits the faceplate window (~20 min) |
| `coupon-voice` | front face down | front wall + the strip of top wall over the mic, one L. Test-fits the button, holder and mic |

**Hardware:** 10× M3 heat-set inserts (5 mm) · 8× M3×8 for the lids · 2× M3×8 for the lock ·
4× M3 self-tap (~6 mm) for the amp board (confirm the hole size) · 2× M3×8 countersunk
self-tap to hold the sled down · 2× M2×12 self-tap for the
holder · 2× M2×6 self-tap for the mic clamp · 4× 4 mm countersunk wall screws and plugs ·
11 × 11 mm 4-pin tactile · panel switch (≥ 3 A at ≥ 24 V DC) · MP1584 · 3.5 mm stereo patch
cable, **right-angle at the DAC end**, ~25 cm · 2-pin connector for the 5 V lead · Ø12 mic
gasket (as in voice-case) · CA or epoxy glue for the dome.

---

## How it goes together

### Hanging and removal

Each lid has two **legs** (8 × 30 mm) with a peg on each end, 4 pegs per box. The legs form the
cable channel's sides. The plate is a flat 6 mm part with a keyhole for each peg. The peg's 45°
cone head catches behind the 2 mm keyhole lip, so the box's weight pulls it tight to the plate.

- **Hang:** amp box first. Put its pegs in the keyhole entries and drop it 8 mm. Then hang the voice
  box the same way, with its sleeve dropping 3 mm into the amp top. Then screw the lock bracket
  onto the header (2× M3, driven vertically from above).
- **Why nothing lifts off:** the voice box can only rise 3 mm before it hits the bracket, and the
  amp box can only rise 6 mm before it hits the voice box. Both pegs need an 8 mm lift to come out.
- **Service:** remove the lock (2 screws) → lift the voice box 8 mm → pull it forward. Then lift the
  amp box 8 mm → pull it forward. Unplug the 5 V connector and the AUX plug through the open
  lids, using the slack in the plug zone.

Wall plate: keyholes at x = ±34. Amp pegs hang at z = 10 / 30 and voice pegs at z = 60 / 102.
Wall screws are at (±16, 12) and (±16, 97).

### Amplifier box

1. Screw the board to the **sled** on the bench, through its 4 holes.
2. Slide the sled and board in from the rear. The sled runs the full inside depth, so the front
   wall stops it at one end and the lid at the other. The faceplate drops into its rebate behind
   the window lip. The pot nuts stay on the faceplate as shipped.
   Then fix it from underneath: 2× M3×8 countersunk self-tappers up through the floor into the
   two bosses beside the MP1584 pocket.
3. Put the MP1584 in its pocket (dab of hot glue). Wire it, fit the panel switch and dress a
   service loop in the plug zone.
4. Close the lid (4× M3 into inserts). The barrel plug and speaker wires go out through the
   lid's window into the channel and down.

**Heat:** the heatsink has 8 mm of air above it and a 5-slot field directly over it (z ≈ 43).
There are two rows of side slots high on both walls. The 6 mm stack gap is open at the front and
sides, so the top vents are not capped by the voice box. The exhaust still heats the voice box
floor. Measure the box temperature at high volume before closing anything up.

**Terminal screws:** four Ø6 holes in the amp top at 70 mm depth line up with the barrier-block
screws. They sit under the voice box, so they are for service with the box off the wall.

### Voice box

The puck put both boards side by side and ran the DAC socket out of a side wall. On a wall the
socket is an internal connection, so the layout runs **front to back** instead, and nothing
stacks. From the front: the button holder (to 16.8 deep), the devkit across x, the DAC with its
socket facing the rear, then the AUX plug, which loops down into the sleeve. That ordering is
why the boxes are 76 wide: 63 + clearance + pocket walls = 67.2 inside. USB-C faces a side wall
and is not reachable (OTA only).

1. Snap the plunger through the face from the front, as in voice-case.
2. Fit the switch in the holder and screw the holder on from inside (2× M2×12).
3. Seat the mic on its gasket and clamp it.
4. Glue the dome onto the plunger flange **last**. Until then the plunger can still come out for a
   holder change.
5. Put the boards in the tray, the tray on the floor and the sleeve through both. Close the lid,
   which pushes the tray forward against the front wall.

**Button:** The mechanism is voice-case's, which printed and works. The visible cap is a Ø40
spherical dome standing 12 mm proud, on a 45° chamfered rim that clears the face by 4 mm. Its
flat underside clears the face by 2 mm at rest. A press at the edge of that flat can rock the
plunger in its two journals by up to 1.68 mm, including stroke (`btn_edge_drop()`), so it closes
the switch before the dome touches the face. The longer 8 mm holder guide keeps that number
under 2.

**Mic:** single Ø2 port on the voice box's **top face**, 30 mm back from the front and
centred. It uses the voice-case gasket seat and clamp, upside down: the posts hang from the top's
inner face. It used to sit above the dome on the front face, and that stack is what made the box
70 tall. The boards only reach 20 mm up, so with the mic on top the box is 48 tall, set by the
dome. The port faces the ceiling, which is the voice-case desk-puck arrangement.

---

## Wiring

```
24 V adapter ──► amp barrel jack ──┬──► [amp power switch] ──► amp
                                   │
                  (solder to the jack's pins, PCB underside)
                                   └──► MP1584 IN ── 5.0 V ──► 2-pin plug ──(sleeve)──► devkit 5V / GND
DAC 3.5 mm socket ──(right-angle plug, through the sleeve)──► amp AUX jack
Amp L± R± terminals ──(lid window → channel → bottom)──► speakers
```

- **Set the MP1584 to 5.0–5.1 V on the bench before connecting the devkit.** These modules are
  often shipped set well above 5 V. The MP1584's input limit is 28 V, so check that the adapter's
  unloaded voltage is under that.
- **Preferred (ESP32 stays on):** tap 24 V at the barrel jack's own solder pins. That is upstream
  of every switch on the board, so the panel switch cuts only the amp and Home Assistant keeps
  the device online.
- **The board's switch is unreachable in this layout.** It is on the rear edge, inside the box,
  facing the wall. A **panel switch on the right side wall** replaces it. Before wiring it,
  confirm which part is the board's power switch: with power off, check with a meter which pads
  lose continuity to the barrel centre pin when it is toggled. In the photos the candidate is the
  small yellow part next to the AUX jack, not next to the barrel. Then remove that switch, or
  leave it ON, and run two wires from its switched pads to the panel switch.
- **Alternative (switch both together):** if the board has no separable power switch, or the
  upstream tap is impractical, feed the MP1584 from the switched side instead. One switch then
  powers everything, and the voice device goes offline when the amp is off. No geometry changes.
- If the yellow part turns out to be a **mode switch** (BT/AUX), leave it in AUX. The panel switch
  then has to break the amp's own feed, which means cutting a trace. Do that only after reading
  the board, not from a photo.
- **Speaker terminals:** the 4-way barrier block appears to be the speaker outputs. The photos
  show a speaker on two of its positions, but no label is readable. Confirm L+/L−/R+/R− from the
  silkscreen or by tracing to the TPA3116 outputs before connecting both speakers. The amp is
  bridge-tied, so never join a minus to ground.
- Keep the 5 V pair twisted and away from the AUX cable. If the buck's switching is audible,
  route it further from the AUX cable or add a ferrite on the 5 V pair.
- Don't power the devkit over USB while the 5 V rail is live unless you have checked the board
  for back-feed protection. That is moot once it is closed up, since USB is not reachable.

---

## What to adjust after a fit check

Any component **position** (the amp board, MP1584, panel switch, devkit, DAC, mic, button, sleeve)
is easiest to change by moving the part in Fusion and running `sync`. Everything below is a
**size**, set in `vwc/params.py`.

| Symptom | Parameter |
|---|---|
| Faceplate won't seat / rattles in the window | `amp_face_w/h/t`, `amp_face_y0`, `face_fit` |
| Faceplate is fine but you want a closed front | `ctrl_mode = "holes"`, then `ctrl_pitch`, `ctrl_axis`, `ctrl_bush_d`, `ctrl_led` |
| Board holes don't line up | `amp_holes`, then reprint `amp-sled` only |
| Knobs sit too close to the face | `face_rebate` (moves the faceplate forward) |
| Barrel plug body hits a leg / plug won't fit through the lid | `amp_dc_x`, `amp_dc_plug_d`, `chan_d`, or use a right-angle plug |
| AUX plug won't pass the sleeve | `sleeve_id` |
| Switch cut-out wrong | `amp_psw_shape`, `amp_psw_cut` / `amp_psw_round_d`, `amp_psw_body` |
| Box too deep | `plug_zone` (MP1584 + right-angle AUX plug set the floor, ~22), `chan_d` |
| Button too prominent / not enough | `btn_dome_d`, `btn_dome_h`. The edge-drop assert says if it gets unsafe |

`./test.sh` re-checks every clearance above by name, including the knob shaft length, the plug
body against the legs, the switch body against the bosses and AUX plug, the keyhole spacing and
the A1 bed size.

---

## Evidence: what each number rests on

| Source | Values |
|---|---|
| **voice-case, printed and fitted** | devkit 63 × 28 and its 0.5 clearance; DAC 33 × 20 and its socket 6 wide, 3 in from the end; INMP441 17 × 15, gasket seat, clamp; the whole button mechanism and 11 mm switch |
| **User, nominal** | amp 73 × 60 × 18 (what it includes is unconfirmed, see below); MP1584 22 × 17 |
| **Photos (estimates, not measurements)** | rear-edge order (AUX at the VOL end, block in the middle, barrel at the TREBLE end) and their x positions; 4 mounting holes (irregular); shafts ~18–22 apart, ~15 proud; heatsink mid-board; LED at the VOL end; the faceplate is a separate panel held by the pot nuts |
| **Assumed** | faceplate 60 × 18 × 1.6, hanging 1 mm below the PCB; barrel/AUX axis heights; plug sizes; switch cut-out; MP1584 height |

One photo estimate was already overruled. The front-right hole reads about 70 mm from the rear
edge, but at 70 its standoff would sit inside the faceplate, so it is set to 66 as a placeholder.

**Assumptions that affect fit or wiring:**
- *73 is the rear edge to the faceplate's front face.* If it excludes the faceplate, the box
  needs `amp_l` + ~1.6.
- *18 is the PCB underside to the highest point.* If it is measured from the PCB top, add 1.6
  to `amp_env_h`; the heatsink air drops to 6.4.
- *The faceplate is as wide as the board.* A wider plate needs `amp_face_w`, and the asserts
  check it against the box.
- *The board can be tapped upstream of its switch at the barrel pins.* This is true by
  construction for the barrel jack itself. Which part is the switch is not confirmed.

---

## Measurements still needed

In order of how much they move the design:

1. **Faceplate:** width × height × thickness, and how far its bottom edge sits below the PCB
   underside. This one reading sets the front window.
2. **What 73 / 60 / 18 include:** confirm 73 runs from the PCB rear edge to the faceplate front
   face, and 18 from the PCB underside to the tallest part. Also note which part is tallest
   (heatsink or caps).
3. **Mounting holes:** 4 centres, measured from the rear edge and from the VOL-side edge, plus
   the hole Ø.
4. **Rear connectors:** barrel and AUX centre x and axis height above the PCB top; terminal block
   span and height; how far the barrel and AUX bodies overhang the rear edge.
5. **The yellow part / power switch:** what it switches. Also check whether any pot has a
   built-in switch.
6. **Terminal block labels** (L±/R±).
7. **Pin tails under the amp PCB.**
8. **Your plugs:** barrel plug type, length and Ø; right-angle 3.5 mm plug head size (sets
   `sleeve_id`).
9. **Your panel switch:** cut-out and body depth.
10. **MP1584 height** (inductor).
11. *(holes mode only)* shaft axis height above the PCB, bushing Ø and LED position.

Suggested print order: `coupon-amp` + `coupon-voice` → `amp-sled` (board on it) → `voice-tray`
→ the shells and lids → `plate` → `lock`.

---

## Not done here

- The Fusion port has only been run against the offline emulator, not in Fusion. See
  [fusion/README.md](fusion/README.md#what-has-not-been-checked) for what to check on the first
  run.
- The devkit pocket is a plain friction pocket with pin relief. voice-case's rear stops and front
  tab can be ported if the board moves in it.
- [`docs/DEVICES.md`](../../docs/DEVICES.md) still describes the enclosure as "being redesigned".
  It should point here once the fit check is done.
