# Voice S3 Desk Puck

Parametric OpenSCAD enclosure for [`devices/voice-s3.yaml`](../../devices/voice-s3.yaml)
— a tabletop voice satellite shaped like the Home Assistant Voice PE, **with a 3.5 mm
line-out instead of an internal speaker**.

**96 × 96 × 34 mm**, rounded square, 45° chamfered top edge. One big button and the
mic port on the top face; the devkit's USB-C out the rear wall and the DAC board's own
3.5 mm socket out the `+x` side. Wiring for everything inside is in
[../../docs/DEVICES.md](../../docs/DEVICES.md) → *Voice S3 — bare ESP32-S3*.

## Why this isn't one of the other cases

VPE's whole lower half is a driver and its grille. Voice S3 has neither — it is a
line-out device, so the driver is replaced by the DAC's own 3.5 mm socket used straight
through the wall, and the box becomes a board carrier. Every dimension is set by the two
boards, not by an acoustic volume.

## Why it is 96 × 96 × 34

Neither number is a free choice. Both have derived floors, and the asserts name the
value they need rather than failing as a pile of unrelated collisions further down:

```
plan_min   = 94.8    (width 94.8 | boss/s3 73.2 | boss/dac 88.2 | depth 73.7)
cavity_min = 26.6    (bare 16.1  | mic 23.7     | button holder 26.6)
```

**Width (96).** The devkit is 63 mm deep — nearly the whole case — and the four M3
bosses are full-depth pillars a board may not overlap at *any* height. So wherever the
devkit sits, a rear boss falls inside its span in y and only x clearance can save it.
That forces it to be **centred**, which means the DAC has to begin beyond *half* the
devkit pocket rather than just beside it. VPE manages 86 mm with a purpose-built PCB.

**Height (34).** Set by the devkit's 11 mm component stack — soldered 2.54 headers plus
dressed wire — against the button holder, which reaches 11.5 mm down from the top face
and has to clear it. The devkit alone would need only 16.1 mm of cavity; the button costs
the other 10.5. `cavity_depth = 28` leaves 1.4 mm over the floor.

Both floors exist because both numbers were set by eye and turned out wrong once a real
board got measured. If you change a board dimension, run `./test.sh` — it will tell you
the new minimum.

## Layout

`+y` is the front, `-y` the rear, `z` runs from the top face down into the box.

```
base plate — both boards, looking down (96 x 96)      o = M3 screw

    +--------------------------------------+
    |  o        === vents ===           o  |
    |           === vents ===              |     +y  front
    |           === vents ===              |
    |       +-------------+   +---------+  |
    |       |             |   |   DAC   |  |
    |       |   devkit    |   | 20 x 33 |]--  socket, centred on +x wall
    |       |   30 x 64   |   |         |  |
    |       |             |   +---------+  |
    |       |             |     | | | |    |
    |  o    +--[ USB ]----+     vents   o  |     -y  rear
    +--------------------------------------+
            ^ pocket has NO rear wall

    devkit CENTRED in x (see above) and registered against the rear wall.
    DAC turned sideways: its socket is on a long edge, so the board runs along y.

    the socket sits in the board's REAR CORNER, 3 mm from the end — so the BOARD is
    shifted +9 mm in y to put that socket behind a CENTRED hole. The hole stays in
    the middle of the wall where it looks deliberate; the board is hidden.

top face — mic and button only

    +-----------------------------------------------+
    |                  . mic .                      |
    |               o          o    <-- the two blind M2 pilots
    |              (( BUTTON ))         the holder screws onto
    +-----------------------------------------------+


section — through y = 0                          +x to the right

  z  0  ==============[ cap ]=====================    top face
     3  |           [ holder ]                    |
  11.5  |           [ switch ]                    |
  14.9  |   ---- devkit components ----            |   3.4 mm below the holder
  20.4  |                        +--socket--+   ]--   thinned panel + plug hole
  25.9  |   +---- devkit PCB ---+   +--DAC--+     |
    31  +---+----------------+------+-------+-----+   base plate
    34  ==========================================

  the devkit's 11 mm component stack (headers + dressed wire) is what sets the
  height: the button holder reaches 11.5 mm down and has to clear it
```

| Feature | Where |
|---|---|
| ESP32-S3-DevKitC-1 | base plate pocket, long axis along y, USB end at the rear |
| PCM5102A "LINE" board | base plate pocket, turned sideways — long axis along y, socket edge at the `+x` wall |
| INMP441 | top face, front edge, gasketed port + clamp bar |
| tactile switch | in the `holder`, which screws to two blind pilots inside the top face |
| USB-C window | rear wall, over the devkit's own two ports — power, flashing and logs |
| 3.5 mm socket | the DAC board's own, behind a locally thinned panel in the `+x` wall |

**Both boards sit on the base plate**, not one on each part. The DAC board has no
mounting holes — every gold pad on it is a header position — so it lives in a friction
pocket, and a friction-pocketed board has to sit on a floor with gravity holding it
rather than hang upside down off the lid.

**The button is a separate two-part module**, not shell geometry. The shell keeps only
a bore, a cosmetic recess and two blind M2 pilots; the cap and the `holder` carry the
switch pocket, the plunger aperture and the snap catch between them. That split is the
whole point: the catch is the fussiest fit on the case, and with the seat moulded into
the shell every attempt at it cost a four-hour reprint and the switch had to be pushed
into a blind pocket down a 15 mm hole and glued by feel. Now the mechanism assembles in
the open, you test it by pressing it with a finger, and a revision costs ten minutes.

**Why the socket is on the side and not next to the USB.** Forced, not stylistic. The
devkit is centred and spans nearly the whole depth, so the rear wall is entirely taken by
its USB window and the board behind it. The `+x` wall is where the DAC can reach.

**Why the wall is thinned behind the socket** (`jack_panel_t`, 1.2 mm — the same trick
the speaker case uses for its PTT switch). A 3.5 mm plug has ~14 mm of barrel and needs
nearly all of it inserted to make the ring contact. Spend 3 mm of that on a
full-thickness wall and the plug bottoms out on the case before it seats, which reads
as intermittent or mono output. At 1.2 mm the plug loses 1.7 mm total and seats
properly.

**Why the socket stops behind the skin** instead of poking through: the base plate
carries the board, so it rises straight up into the shell at assembly. A socket
protruding through the wall would have to be threaded in sideways, which a vertical
joint cannot do. The counterbore gives it somewhere to sit.

The board's x position is **derived backwards** from where the socket must end up —
face just behind the panel, minus `dac_jack_overhang` — so a wrong `dac_w` only slides
the far edge inward and the socket stays on the hole.

## Render

```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
./build.sh        # shell.stl, base.stl, button.stl, clamp.stl into stl/
./test.sh         # asserts + clean-render check for every part
```

Render one part manually:
```bash
"$OPENSCAD" -D 'part="shell"' -o stl/shell.stl voice-case.scad
```

| Part | What it is |
|---|---|
| `shell` | top face + four walls: button bore/halo/pilots, mic seat and posts, corner bosses, rear USB window, side socket panel |
| `base` | flat plate: devkit and DAC pockets, register lip, vents, counterbored screw holes |
| `button` | snap-in cap |
| `holder` | switch carrier — the whole button mechanism |
| `clamp` | mic clamp bar |
| `coupon` | fit test — see below |
| `all` | assembled preview |

Select with the normal variable flag `-D part="..."` (a `$`-prefixed variable would be
ignored by `-D`).

## Print the coupon first

The coupon is the button bore, its pilots and the mic seat cut out of the real top face,
plus the three small parts that mate with them. Ten minutes of printing tells you
whether the snap, the travel and the gasket land before you commit four hours to the
shell — and because the mechanism is now in `holder`, most fixes mean reprinting the
coupon and the holder rather than anything large.

```bash
"$OPENSCAD" -D 'part="coupon"' -o stl/coupon.stl voice-case.scad
```

- Cap won't snap in, or snaps in and won't come out → `btn_lip_over`, `btn_slit_w`.
- Cap rattles → `btn_face_gap` (it is the free travel *and* the rattle).
- Cap presses but the switch never clicks → `bh_gap_h` is too tall for the post, or
  `btn_face_gap` is too small and the face is bottoming on the recess floor.
- Switch falls out of the holder → `sw_body` / `clr`; it is a push fit plus a dab of
  glue, and the plunger aperture is what stops it going too far.
- Mic board doesn't seat flat → `mic_seat_depth`, `clr`.

**Measure your DAC board before printing the shell.** These are the numbers that place
the hole, and my defaults are estimates from a product photo, not from calipers:

| Param | What to measure | Default |
|---|---|---|
| `dac_jack_w` | socket body width along its edge | 9.0 |
| `dac_jack_h` | socket body height above the PCB face | 6.5 |
| `dac_jack_axis` | barrel **axis** height above the PCB face | 3.2 |
| `dac_jack_overhang` | how far the socket body sticks past that long edge | 2.5 |
| `dac_jack_inset` | board **end** edge to the near side of the socket body | 3.0 |
| `board_clr` | per-side clearance in both friction pockets | 1.0 |
| `dac_w`, `dac_l` | board size across x, along y | 20 × 33 |

The socket is **not centred on its edge** — it sits in the corner, 3 mm from the end of
the board. That offset has to be absorbed somewhere, and it goes into the **board's
position, not the hole's**:

    dac_jack_off() = dac_jack_end * (dac_l/2 - dac_jack_inset - dac_jack_w/2)   // -7.5
    dac_pos_y()    = jack_hole_y - dac_jack_off()                              // +7.5

So `jack_hole_y = 0` keeps the hole in the middle of the wall, where it looks
deliberate, and the board shifts 7.5 mm to put its corner socket behind it. The board is
hidden; the wall is not.

Two asserts hold this together: one that the socket offset really is out at the board
end (if it collapses toward zero, someone has started typing it in again) and one that
`dac_jack_y()` lands exactly on `jack_hole_y`. The second is the check that would have
caught the hole sitting 10 mm away from its socket.

`dac_w`/`dac_l` matter less — the board is positioned from its socket edge, so a wrong
size mostly slides the far edge inward. But `dac_l` now feeds the derived offset too, so
it is worth getting roughly right. `dac_jack_overhang` and `dac_jack_axis` decide how
deep the plug seats.

## Parameters

All in [modules/params.scad](modules/params.scad). Common edits:

| Param | Meaning |
|---|---|
| `plan`, `cavity_depth` | footprint and interior height. **Both have derived floors** — `plan_min()` and `cavity_min()`; the asserts name the number needed |
| `s3_comp_h` | tallest thing on the devkit's component side. This sets the case height |
| `s3_w`, `s3_l` | devkit footprint (64 × 30, measured). This is what sizes the whole case |
| `s3_pos_x` | devkit x — must stay `0`; its y is derived so it registers on the rear wall |
| `s3_seat_h` | pocket floor under the devkit — this is what sets the rear window's height |
| `jack_hole_y` | where the socket hole sits on the side wall; `0` = centred. The board moves to suit — both DAC coordinates are derived |
| `mic_pos` | INMP441 position on the top face |
| `dac_jack_*` | the DAC's onboard socket — see the measurement table above |
| `jack_panel_t` | local wall thickness behind the socket; the reason a plug seats |
| `jack_hole_d` | plug clearance hole through that panel |
| `btn_bore_d` | shell bore; the whole button diameter chain follows from it |
| `btn_face_gap` | cap float above the recess floor = available travel |
| `bh_*` | the holder — plate size, catch thickness, lip relief, plunger aperture |
| `clr` | global fit clearance (raise if parts are tight) |

Every relationship these can break is asserted. Change one and run `./test.sh` — it
will name the collision rather than let you find it with a printed part.

## Print settings

- **Shell: top face DOWN**, no supports. The top edge is a 45° chamfer rather than a
  fillet precisely so it prints support-free in this orientation, and the button
  recess, halo and mic port come out as crisp first layers. The USB window and jack
  bore are horizontal holes in vertical walls — short bridges, no support needed.
- **Base plate**: flat, pockets up.
- **Button cap**: face down. **Holder**: plate face down (the face that mates the wall),
  block growing up — the one internal overhang is a short annular bridge where the
  plunger aperture closes over the lip relief, which needs no support at 0.2 mm.
- **Mic clamp**: bar face down, pad up.
- 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- **PETG for the button cap** if you have it — the slit skirt is a snap-fit and PLA
  gets brittle at that thickness. The shell and plate are happy in either.

## BOM

- 1× ESP32-S3-DevKitC-1, N16R8 (16 MB flash / 8 MB octal PSRAM)
- 1× PCM5102A DAC breakout **with an onboard 3.5 mm socket** — the case uses that
  socket directly, so there is no panel-mount jack and no analog flying leads
- 1× INMP441 MEMS mic breakout
- 1× 6×6 mm tactile switch (any common height — check `sw_body_h`)
- 4× M3 heat-set inserts + 4× M3×8 screws (M3×10 if your inserts are deep)
- 2× M2×8 self-tap screws for the mic clamp (they reach through the bar into the posts)
- 2× M2×6 self-tap screws for the button holder (into the blind pilots in the top face)
- 1× foam/EVA gasket **ring** for the mic, ⌀12 mm outer with a bore that clears the
  module's port — punch it out of foam tape; a solid disc would seal the port shut
- 4× self-adhesive rubber feet (stuck straight onto the flat plate — no recesses)
- hookup wire — the devkit's 5 V and 3V3 rails feed both breakouts

## Assembly

1. **Heat-set the four M3 inserts** into the shell's corner bosses, from the open
   (base) side.
2. **Build the button module on the bench**, before it goes anywhere near the shell.
   Push the tactile switch into the holder's block, plunger first, until its top face
   lands on the aperture ledge; the legs come out through the side slots. A dab of glue
   holds it. Solder its two leads to **G4** and **GND**, leaving them long.
3. **Bench-test the snap**: press the cap into the holder's bore until the lip catches,
   press the face with a finger — you should feel the switch click and the cap should
   spring back with the lip still held — then work the cap back out. This is the test
   worth doing properly, and none of it needs the shell. Everything about it is tunable
   by reprinting these two parts.
4. **Screw the holder to the shell** — against the wall's inner face, 2× M2 into the
   blind pilots — and only then **snap the cap in from the outside**. The cap has to go
   in that way round: its 18 mm face cannot pass back through the 15 mm bore, so the cap
   is always the last thing fitted, never pre-assembled into the holder.
5. **Mic**: gasket ring into the seat, INMP441 on top of it port-down, then the clamp
   bar across the two posts, pad down onto the middle of the board, 2× M2. The posts
   flank the board rather than sit under it — they have to, since the board lies on
   its own gasket — so the bar is what holds it. Tightening those two screws is what
   compresses the gasket, and that seal is the acoustic design, not a nicety.
6. **Both boards into the base plate**, component sides **up**. The devkit goes in its
   long pocket with its USB end toward the notch; the DAC slides into the short pocket
   from the open `+x` end, socket first. Solder wires directly to the DAC's pads —
   don't fit the header strips it ships with; the pocket is sized for a bare board.
   Strap the DAC as the wiring table says: `SCK→GND`, `FMT→GND`, `XMT→3V3`,
   `FLT/DEMP→GND`. A floating `SCK` is silent or noisy, and a floating `XMT` stays
   soft-muted. Nothing is wired to `LROUT`/`RROUT` — the onboard socket already has
   them.
7. Wire it all (I²S bus 0 → DAC on G5/G6/G7, bus 1 → mic on G10/G11/G12).
8. **Test-fit the plate before you commit**: offer it up to the shell and check that a
   3.5 mm plug pushed through the side hole seats fully in the socket with a click, not
   a stop. If it stops short, the socket is sitting too far back — reduce
   `dac_socket_setback` or re-measure `dac_jack_overhang`.
9. Stick four self-adhesive feet on the outside of the plate (clear of the vents — there
   are no recesses for them, see below), drop the plate on — the register lip finds
   the alignment — and drive 4× M3 from underneath.

## Notes on two decisions

**The button is a cap over a tactile switch, not a panel-mount switch.** The
speaker case uses a 12 mm panel-mount momentary and it is the more robust part, but
its body and terminals need ~30 mm behind the panel; that would have made this puck
~45 mm tall instead of 29 and killed the VPE proportions. The cost is real: tactile
travel is ~0.25 mm, so the button *clicks* rather than moves. That's the same feel as
VPE's own button.

**The mic gets one short gasketed port, not a hole cluster.** Same call, and same
reason, as the speaker case: a cluster of small holes through a 3 mm wall is a
Helmholtz resonator sitting right on top of speech. One short hole with the MEMS port
pressed to a gasket leaves near-zero front volume and moves the resonance well clear.

## Desk only

There is no keyhole wall mount. Voice S3 wants to sit where you talk to it, and the
rear wall is full of cables. Wall-mounted intercom nodes are what
[../kitchen-case](../kitchen-case) and [../terrace-case](../terrace-case) are for.
