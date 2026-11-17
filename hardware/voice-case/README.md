# Voice S3 Desk Puck

Parametric OpenSCAD enclosure for [`devices/voice-s3.yaml`](../../devices/voice-s3.yaml):
a desk voice satellite shaped like the Home Assistant Voice PE, with a 3.5 mm line-out
instead of a speaker.

**73 × 74 × 35 mm** (41.5 over the button). Button and mic port on the top face, devkit
USB-C out the rear wall, the DAC board's own 3.5 mm socket out the `+x` side. Wiring:
[docs/DEVICES.md](../../docs/DEVICES.md) → *Voice S3*.

## Size

Each dimension has a derived floor; `./test.sh` prints them:

```
plan_x_min = 72.6    boss line -> devkit -> shared wall -> DAC -> socket
plan_y_min = 73.7    (devkit length 73.7 | DAC vs bosses 66.2)
cavity_min = 28.85   (bare 16.1 | mic 23.7 | button holder 28.85)
```

- **Depth** is the 63 mm devkit plus walls, register lips and clearances.
- **Width** is a chain from the `+x` wall: socket → DAC → one shared 2 mm wall → devkit
  → clearance to the `-x` corner bosses.
- **Height** is the devkit's 11 mm component stack (headers + wire) under the button
  module, whose switch pins reach 13.75 mm down. Clipping the pins shorter lowers
  `cavity_min()`.

Change a board dimension and `./test.sh` reports the new minimum.

## Layout

`+y` front, `-y` rear, `z` from the top face down.

```
base plate, looking down (73 x 74)                  o = M3 screw

    +-----------------------------------------+
    | | | +--------------------++----------+  |
    | |o| |                    ||          |  |
    | |=| |      devkit        ||   DAC    |  |     +y  front
    | |=| |      28 x 63       ||  20 x 33 |]--- socket, y +10.5
    | |o| |                    ||          |  |
    | | | +-###-[ USB ]--###---++----------+  |     -y  rear
    +-----------------------------------------+
        ^ -x strip: boss clearance + two long vents
              ^ rear stops either side of the USB notch
                                 ^ shared 2.0 mm wall

section, through the boards

 z -6.5        ,--''--.                             cap apex
  z  0  ======[==flange==]=======================    top face
     8  |      [  catch  ]                      |    cap lip lands here
 10.25  |      [ switch  ]                      |    switch on the collar floor
 13.75  |       | |  | |                        |    switch pins, soldered underneath
  15.9  | ---- devkit components ----           |
  20.4  |                       +--socket--+  ]--    thinned panel + plug hole
  25.9  | +---- devkit PCB ----+  +--DAC--+     |
    31  +-+-----------------+----+--------+-----+    base plate
```

| Feature | Where |
|---|---|
| ESP32-S3-DevKitC-1 | base plate slot, USB at the rear |
| PCM5102A board with socket | base plate pocket, socket edge at the `+x` wall |
| INMP441 | top face, front; gasketed port + clamp bar |
| 11×11 tactile switch | in the button holder, pins down through its floor |
| USB-C window | rear wall |
| 3.5 mm socket | DAC's own, behind a 1.2 mm thinned panel |

Design decisions worth knowing:

- **Both boards sit on the base plate.** The DAC has no mounting holes, so it needs a
  friction pocket with gravity on its side.
- **The socket stays behind the wall** in a counterbore: the plate rises vertically into
  the shell, so a protruding socket could not be assembled.
- **The wall behind the socket is thinned to 1.2 mm** (`jack_panel_t`) so the plug inserts
  far enough to reach the ring contact. A full 3 mm wall gives mono or intermittent sound.
- **The DAC pocket is loose (`board_clr` 1.0)** because its socket locates it. **The devkit
  slot is tight (`s3_board_clr` 0.5)** because nothing else does, and slack moves the USB
  port off its window. The devkit is held by a front tab that preloads it back against
  two rear stops.
- **The button is a separate module** (cap + holder), so its fit can be tuned by
  reprinting two small parts instead of the shell.
- **No return spring:** the 11 mm tactile's own spring holds the cap up against its lip.
  `btn_preload` (post slightly long) prevents rattle; it must stay under half of
  `sw_travel`, or the switch stays pressed.
- **Ø22 cap:** the switch's 15.6 mm diagonal stands inside the cap's bore.
- **One gasketed mic port**, not a hole cluster: a cluster in a 3 mm wall resonates in
  the speech band.
- **Desk only.** Wall nodes are [../kitchen-case](../kitchen-case) and
  [../terrace-case](../terrace-case).

## Render

```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
./build.sh        # every part into stl/
./test.sh         # asserts + clean render of every part
"$OPENSCAD" -D 'part="shell"' -o stl/shell.stl voice-case.scad   # one part
```

| Part | What it is |
|---|---|
| `shell` | top face + walls: button bore, mic seat, bosses, USB window, socket panel |
| `base` | plate: board pockets, register lip, vents, screw holes |
| `button` | snap-in cap |
| `holder` | switch carrier and cap guide |
| `clamp` | mic clamp bar |
| `coupon` | button + mic fit test |
| `fit`, `fit-front` | devkit bed fit tests: rear end (relief, width, stops) and front end (tab) |
| `all` | assembled preview |

A Fusion 360 port of the same model lives in [fusion/](fusion/).

## Fit tests — print these first

**`coupon`** (~10 min): button bore, pilots and mic seat, plus the parts that mate with them.

| Symptom | Change |
|---|---|
| Cap won't snap in / won't come out | `btn_lip_over`, `btn_slit_w`, `btn_slits` |
| Cap leans when pressed off-centre | `btn_guide_clr` down, or `bh_guide_h` up |
| Cap binds or feels gritty | `bh_guide_clr` up (must stay looser than `btn_guide_clr`) |
| Cap goes in and won't move | `btn_guide_clr` up first, then `btn_lip_slack` |
| Cap rattles | `btn_preload` up |
| Switch always closed / no click | `btn_preload` down; measure `sw_travel` |
| Switch won't sit flat | measure `sw_pin_pitch` — it is `[x, y]`, not square |
| Switch wanders | `sw_locate_clr` down |
| Mic board doesn't seat flat | `mic_seat_depth`, `clr` |

**`fit` / `fit-front`**: try the devkit in each end of the bed and tune in 0.1 mm steps.

| Symptom | Change |
|---|---|
| Won't go in | `s3_board_clr` up |
| Rocks side to side | `s3_board_clr` down |
| Front edge won't go under the tab | `s3_tab_preload` down |
| Front lifts | `s3_tab_preload` or `s3_tab_cover` up |
| Rear won't drop behind the stops | `s3_rear_stop_h` down |
| Slides back out over the stops | `s3_rear_stop_h` up (max `pcb_t`) |

## Measure before printing the shell

`s3_w` × `s3_l` (63 × 28, measured) set the case size. The DAC socket numbers are
estimated from a photo. Measure yours:

| Param | Measure | Default |
|---|---|---|
| `dac_jack_w` | socket body width along the edge | 6.0 |
| `dac_jack_h` | socket body height above the PCB | 6.5 |
| `dac_jack_axis` | barrel axis height above the PCB | 3.2 |
| `dac_jack_overhang` | socket overhang past the board edge | 2.5 |
| `dac_jack_inset` | board end to the socket body | 3.0 |
| `dac_w`, `dac_l` | board size | 20 × 33 |
| `sw_body`, `sw_h`, `sw_travel`, `sw_pin_pitch`, `sw_pin_len` | the tactile switch | |

The socket sits in the board's corner, so the side hole is at y +10.5, not centred.

## Parameters

All in [modules/params.scad](modules/params.scad). Every relationship is asserted; change
one and run `./test.sh`.

| Param | Meaning |
|---|---|
| `plan_x`, `plan_y`, `cavity_depth` | footprint and interior height (floors above) |
| `s3_w`, `s3_l`, `s3_comp_h` | devkit PCB and its tallest component |
| `s3_board_clr` | devkit slot clearance per side — tune with `fit` |
| `s3_tab_cover`, `s3_tab_preload` | front retention tab; `s3_tab_cover = 0` removes it |
| `s3_rear_stops`, `s3_rear_stop_h` | rear stops; height capped at `pcb_t` |
| `board_clr` | DAC pocket clearance per side |
| `boss_inset` | corner boss position; sets `plan_x` |
| `dac_pos_y_set` | DAC centre in y; keep 0 (each mm costs 2 mm of `plan_y`) |
| `usb_panel_t`, `jack_panel_t` | thinned wall behind the USB window / socket |
| `mic_pos` | mic position on the top face |
| `btn_wall_od`, `btn_cap_d`, `btn_dome_h` | cap body, flange, dome height |
| `btn_guide_clr`, `btn_lip_slack`, `btn_preload`, `btn_face_gap` | button fits (see fit tests) |
| `sw_*`, `sw_locate_clr` | tactile switch and its locating ribs |
| `bh_*` | holder: guide, relief, floor, collar, screw posts |
| `clr` | global fit clearance |

## Print settings

- **Shell:** top face down, no supports (the 45° chamfer is what allows this).
- **Base plate:** flat, pockets up.
- **Button cap:** dome down, no supports. Not flange-down.
- **Holder:** floor down. If the slicer shows four small floating blocks, the locating
  ribs aren't fused to the floor — check `bh_rib_embed` against `bh_relief_eps`.
- **Mic clamp:** bar face down.
- 0.2 mm layers, ≥4 perimeters, 20–30 % infill. PETG for the cap if you have it (the
  snap fingers crack in PLA).

## BOM

- 1× ESP32-S3-DevKitC-1 N16R8
- 1× PCM5102A breakout with an onboard 3.5 mm socket
- 1× INMP441 breakout
- 1× 11 × 11 mm 4-pin tactile switch (12×12 family, pin plunger)
- 4× M3 heat-set inserts + 4× M3×8 (M3×10 for deep inserts)
- 2× M2×10 self-tap (holder), 2× M2×8 self-tap (mic clamp)
- 1× foam gasket **ring** for the mic, Ø12 outer, bore clear of the port (a solid disc seals it)
- 4× stick-on rubber feet, hookup wire

## Assembly

1. Heat-set the four M3 inserts into the corner bosses.
2. **Button module, on the bench:** drop the switch into the holder plunger-up, pins through
   the floor windows. Solder leads to the pins from underneath — **G18** and **GND**, long.
3. Press the cap into the holder until the lip catches. Check: ~0.5 mm travel, a click, no
   rattle, no noticeable lean. Fix with the coupon table.
4. Screw the holder to the shell (2× M2 into the blind pilots), **then** snap the cap in
   from outside. The flange can't pass the bore, so the cap always goes in last.
5. **Mic:** gasket into the seat, INMP441 port-down on it, clamp bar across the posts, 2× M2.
   The clamp compresses the gasket; the seal matters acoustically.
6. **Boards into the plate**, components up. Devkit: rear up ~2°, front edge under the tab,
   push until the rear drops behind the stops. DAC: slide in socket first; solder wires to
   its pads (no header strips). Strap `SCK→GND`, `FMT→GND`, `XMT→3V3`, `FLT/DEMP→GND` —
   floating `SCK` is silent or noisy, floating `XMT` stays muted.
7. Wire: DAC on G5/G6/G7, mic on G10/G11/G12.
8. Offer the plate up and push a plug through the side hole: it must click home. If it stops
   short, lower `dac_socket_setback` or re-measure `dac_jack_overhang`.
9. Feet on the plate (clear of the vents), plate on, 4× M3 from below.
