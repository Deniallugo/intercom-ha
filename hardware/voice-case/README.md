# Voice S3 Desk Puck

Parametric OpenSCAD enclosure for [`devices/voice-s3.yaml`](../../devices/voice-s3.yaml)
— a tabletop voice satellite shaped like the Home Assistant Voice PE, **with a 3.5 mm
line-out instead of an internal speaker**.

**73 × 74 × 35 mm** (41.5 over the button), rounded box, 45° chamfered top edge. One
big button and the mic port on the top face; the devkit's USB-C out the rear wall and the
DAC board's own 3.5 mm socket out the `+x` side. Wiring for everything inside is in
[../../docs/DEVICES.md](../../docs/DEVICES.md) → *Voice S3 — bare ESP32-S3*.

## Why this isn't one of the other cases

VPE's whole lower half is a driver and its grille. Voice S3 has neither — it is a
line-out device, so the driver is replaced by the DAC's own 3.5 mm socket used straight
through the wall, and the box becomes a board carrier. Every dimension is set by the two
boards, not by an acoustic volume.

## Why it is 73 × 74 × 35

Neither number is a free choice. Both have derived floors, and the asserts name the
value they need rather than failing as a pile of unrelated collisions further down:

```
plan_x_min = 72.8    one chain: boss line -> devkit -> shared wall -> DAC -> socket
plan_y_min = 73.4    (devkit length 73.4 | DAC vs bosses 66.2)
cavity_min = 27.25   (bare 16.1 | mic 23.7 | button holder 27.25)
```

**It is not square, because the two axes are not set by the same thing.** Depth is the 63 mm
board plus two walls, two register lips and two pocket clearances — 73.4, and there is nothing
on that axis to save. Width is one chain read inward from the `+x` wall: the socket fixes the
DAC, the DAC fixes the devkit one shared wall inboard of it, and `plan_x` only has to be big
enough that the devkit's outer wall still clears the `-x` corner bosses — 72.8. Getting here
took five steps.

It was **96** until the devkit stopped being centred. The old rule was that a board
spanning nearly the full depth has no y escape from the four full-depth M3 bosses, so it
had to sit at x = 0 — and the y part of that is true, a rear boss falls inside the
devkit's span wherever it sits. The conclusion was too strong, though: what the bosses
demand is *x* clearance, and parking the pocket hard against the `-x` pair gives that
just as well as centring does. Centred, the DAC had to begin beyond **half** the devkit
pocket, so the `-x` half of the plate — 17.6 mm across the whole depth — held nothing at
all. Pushed over, the DAC begins just past the pocket's own edge. That took it to 80.

Then the board got measured properly, which took several goes at both dimensions: **`s3_w`
67 → 65 → 63** walked `plan_y` down with it, and **`s3_l` settled at 28** via 26 and 25 — both of
those *derived* from something rather than measured. See the note on `s3_l` in params: each axis of
this case is one board dimension plus fixed overheads, so both are caliper numbers and nothing
else.

Then the two beds started **sharing one wall** instead of standing two walls back to back with
a 3 mm gap between them: 1.6 + 3 + 1.6 became a single 2.0 mm rib, and `plan_x` lost 4 mm.
Depth lost nothing — depth is the board, and there is no wall to save along it — so this is
what broke the tie and made the case rectangular. Spending those 4 mm on staying square would
have bought nothing but a wider `+x` half than the DAC needs.

Two smaller things moved along the way: `dac_pos_y` went to **0**, because the DAC pocket is
38.2 mm deep and has to pass *between* the `+y` and `-y` bosses, so every millimetre of offset
costs two of `plan_y` and at the old 14.7 the DAC alone demanded 95.6; and the mic came back
from y 28 to **23**, which is where it stops running onto the chamfer.

Net: **−32 % of material** (96.3 → 65.8 cm³ for shell + plate) and **−39 % of desk**.
VPE manages 86 mm with a purpose-built PCB; this undercuts it on two off-the-shelf boards,
at the cost of being 35 mm tall instead of flat.

**Height (35).** Set by the devkit's 11 mm component stack — soldered 2.54 headers plus
dressed wire — against the button module, which reaches **13.25 mm** down from the top face
and has to clear it. The devkit alone would need only 16.1 mm of cavity; the button costs the
other 12.25. `cavity_depth = 29` leaves 0.65 mm over the floor.

Note *what* reaches 13.25: not the holder's floor, which stops at 11.35, but the **switch's
four pins** hanging through it, whose solder joints are the lowest thing on the whole top-face
assembly. Clip them shorter and `cavity_min()` drops with them.

**And 6.5 mm more over the button.** The cap is a dome, not a flat disc — see below — so
the puck stands 41.5 mm at its highest point. That is the cap alone; the box is unchanged.

Both floors exist because both numbers were set by eye and turned out wrong once a real
board got measured. If you change a board dimension, run `./test.sh` — it will tell you
the new minimum.

## Layout

`+y` is the front, `-y` the rear, `z` runs from the top face down into the box.

```
base plate — both boards, looking down (73 x 74)      o = M3 screw

    +-----------------------------------------+
    | | | +--------------------++----------+  |
    | |o| |                    ||          |  |
    | |=| |                    ||          |  |     +y  front
    | |=| |                    ||          |  |
    | |=| |      devkit        ||   DAC    |  |
    | |=| |      28 x 63       ||  20 x 33 |]--- socket, y +10.5
    | |=| |                    ||          |  |
    | |=| |                    ||          |  |
    | |=| |                    ||          |  |
    | |o| |                    ||          |  |
    | | | +-###-[ USB ]--###---++----------+  |
    | | |                                     |     -y  rear
    +-----------------------------------------+
        ^ -x strip: boss clearance, and both long vents
              ^ rear stops, 3.2 mm, flanking a 22.8 mm notch
                                 ^ ONE shared wall, 2.0 mm

    devkit parked against the -x bosses with 0.8 mm of air (s3_pos_x is derived from
    boss_inset, not typed in). The 10 mm strip outboard of it is the boss-clearance strip
    — the one bit of dead plate the layout cannot avoid — so it carries the biggest pair
    of vents.

    in y the board no longer registers against the shell's rear wall: it sits between the
    two REAR STOPS and the front wall, both of which are the register lip grown to pocket
    height, and the front tab's ramp preloads it BACK against the stops. So the stop face
    is the datum and the plug setback is 4.0 mm.
    DAC turned sideways — its socket is on a long edge, so the board runs along y —
    and CENTRED in y, because its 38.2 mm pocket has to pass between the +-y bosses.

    the socket sits in the board's FRONT CORNER, 3 mm from the end, so the hole lands
    at y +10.5 rather than on the wall's centreline. The hole follows the socket now,
    not the other way round: there is no spare plate left to slide the board on.

    the two beds SHARE one 2.0 mm wall — each pocket still draws its own 1.6 mm on that
    side, and they overlap into a single rib. That replaced 1.6 + 3 + 1.6 mm of wall,
    gap, wall, and is what took plan_x from 76 to 72; the 28 mm board put it at 73.

    the vents are down to FOUR: two long ones in the -x strip (dead plate the bosses
    force on us anyway, and it runs right along the devkit) and one in each bay fore and
    aft of the DAC. 428 mm2 of open area against the old eight slots' 564.

    the devkit pocket is a SLOT, not a tray: 0.6 mm per side rather than the DAC's 1.0,
    a tab over the board's front edge that preloads it, and stops behind its rear corners.
    It goes in TILTED — rear up about 2 deg, front edge under the tab first, then push
    until the rear drops behind the stops. It cannot be dropped in flat, and it cannot be
    slid straight in either.

top face — mic and button only

    +-----------------------------------------------+
    |                  . mic .                      |
    |                                               |
    |        o     (( BUTTON ))     o               |
    +-----------------------------------------------+
              ^ the two blind M2 pilots the holder screws onto. On +-x,
                because +y belongs to the mic.


section — through the boards                     +x to the right
                                                 (the jack is at y +10.5, projected in)

 z -6.5        ,--''--.                             cap apex, 6.5 proud
  z  0  ======[==flange==]=======================    top face
     3  |      [ holder  ]                      |    collar top
     8  |      [  catch  ]                      |    cap's lip lands here, and
  3.55  |      [ switch  ]                      |    11x11 x 8 tall, standing ON
  9.75  |      [ ffloorf ]                      |    the collar floor, reaching up
 13.25  |       | |  | |                        |    four pins, soldered under it
  15.9  | ---- devkit components ----           |    2.65 mm below those pins
  20.4  |                       +--socket--+  ]--    thinned panel + plug hole
  25.9  | +---- devkit PCB ----+  +--DAC--+     |
    31  +-+-----------------+----+--------+-----+    base plate
    34  =========================================

  the devkit's 11 mm component stack (headers + dressed wire) is what sets the
  height: the button holder reaches 12.15 mm down and has to clear it
```

| Feature | Where |
|---|---|
| ESP32-S3-DevKitC-1 | base plate pocket, long axis along y, USB end at the rear — slides in from that end, retained by a tab at the other |
| PCM5102A "LINE" board | base plate pocket, turned sideways — long axis along y, socket edge at the `+x` wall |
| INMP441 | top face, front edge, gasketed port + clamp bar |
| 11×11 tactile switch, 4-pin | standing on the `holder`'s floor, pins straight down through it |
| USB-C window | rear wall, over the devkit's own two ports — power, flashing and logs |
| 3.5 mm socket | the DAC board's own, behind a locally thinned panel in the `+x` wall |

**Both boards sit on the base plate**, not one on each part. The DAC board has no
mounting holes — every gold pad on it is a header position — so it lives in a friction
pocket, and a friction-pocketed board has to sit on a floor with gravity holding it
rather than hang upside down off the lid.

### Why the devkit's pocket is tighter than the DAC's

They used to share one `board_clr` of 1.0 mm per side — 2 mm of slack on both axes,
chosen after a pocket built on 0.4 came out *smaller* than the board it was for. The DAC
keeps it, because the slack never shows on that board: its socket drops into a
zero-clearance recess in the floor and then sits inside the shell's counterbore, so the
socket locates the board and the pocket only has to hold it roughly.

Nothing locates the devkit. Its slack is real movement, and it lands on the USB-C
window — the one opening that has to line up with something. So it gets its own
`s3_board_clr`, **0.6**, plus two things the DAC does not need:

- **a retention tab** over the board's far short edge, covering 1.2 mm of it with a 45°
  printable underside. Its height is *derived*, not set: the ramp is aimed to reach
  `s3_tab_preload` = 0.1 mm below the top of the laminate **at the board's own edge**, so
  it keeps holding whatever the front clearance turns out to be. The board is therefore
  *preloaded*, not merely covered — a tab that just covers lets the board lift most of a
  millimetre and knock. The interference is self-limiting because the ramp is 45°, so it
  goes in with a push rather than a press, and the same ramp is what pushes the board back
  against the rear stops.

  It is on the **short** edge deliberately — the long `±x` edges are where the header rows
  are, and a header body starts within a millimetre of the PCB edge, so anything reaching
  in over a long edge fouls it. Set `s3_tab_cover = 0` if your board has something tall at
  that end, and lower `s3_tab_preload` if it will not go in.
- **two rear stops** flanking a 23.8 mm notch, on the register lip's own footprint. This is
  what closes the rear end, and the notch is why it can: it is wider than the 23 mm USB
  window, so the stops sit only where the shell was already solid. They stand exactly
  `pcb_t` above the seating plane and no higher — taller and the board would be captured in
  z at both ends, which is a part you cannot assemble.
- **the front wall is the register lip**, grown to pocket height. It used to be a separate
  1.6 mm wall standing inboard of the lip, which cost 1.6 mm of depth for nothing. Moving it
  onto the lip is what paid for the rear stops without the case growing.
- **the rear wall is locally thinned** to 1.8 mm behind the window (`usb_panel_t`), the same
  trick the `+x` wall uses behind the 3.5 mm socket. The stops hold the board 2.2 mm off that
  wall, which would have put the plug setback at 5.8 against a 6.5 limit; thinning brings it
  to **4.0**.
- **a fit coupon**, `part="fit"` — the **whole bed**, end to end: both long walls, the
  front wall with its tab, and the rear stops. It was a 25 mm slice off the front until the
  rear stops went in, and then a slice stopped being able to answer the question: the board
  no longer slides in, it tilts in between two features 65 mm apart, and you cannot rehearse
  that on one end of it.

  It is shaved to 1.2 mm of plate rather than the real 3 mm — none of that thickness is
  under test, and without the trim the coupon comes out at half the volume of the plate it
  exists to save. As it stands it is **9.8 cm³** against the plate's 28.8.

  0.6 is a deliberate midpoint between the 0.4 that was too tight and the 1.0 that rattled,
  not a measurement. Print the coupon, tilt the board in, and move `s3_board_clr` in 0.1
  steps before committing to the plate:

  | what you feel | what to change |
  |---|---|
  | will not go in at all | `s3_board_clr` up 0.1 |
  | rocks side to side | `s3_board_clr` down 0.1 |
  | front edge will not go under the tab | `s3_tab_preload` down |
  | board lifts at the front | `s3_tab_preload` up, or `s3_tab_cover` up |
  | rear corners will not drop behind the stops | `s3_rear_stop_h` down |
  | slides back out over the stops | `s3_rear_stop_h` up, capped at `pcb_t` |

**The button is a separate two-part module**, not shell geometry. The shell keeps only
a bore, a recess and two blind M2 pilots; the cap and the `holder` carry the switch
pocket, the guide and the snap catch between them. That split is the whole point: the
catch is the fussiest fit on the case, and with the seat moulded into the shell every
attempt at it cost a four-hour reprint and the switch had to be pushed into a blind
pocket down a 15 mm hole and glued by feel. Now the mechanism assembles in the open, you
test it by pressing it with a finger, and a revision costs ten minutes.

**The cap's shape is a scaled TalkingPetDIY button.** The reference is a 61.4 mm two-part
printable pet-communication button; its silhouette — a wide flange, a body stepped in
from it, and a top that is one big *fillet* rather than a spherical dome — was measured
off its meshes and rebuilt parametrically at this button's own **Ø22**. It holds the
reference's ratios for the body (0.891 of the flange against its 0.865) and the fillet, but
not for height: 6.5 mm on a Ø22 flange is flatter than the reference's 0.363 would give, and
that 1.4 mm is deliberate — the ratio is aesthetic and the height is real.

**Why Ø22 and not Ø18.** The switch. An 11 mm square body has a **15.6 mm diagonal**, and the
switch stands up *inside* the cap's own body bore — it has to, because its base sits on the
holder's collar floor and its top is therefore always above the catch, which is inside the
cap. So the bore has to swallow that diagonal: Ø17.2 of bore, Ø19.6 of body, Ø22 of flange.

The alternative was sinking the switch *below* the collar floor, out of the cap's way. That
keeps Ø18 and costs about **5 mm of case height**, because the holder then reaches 17.5 mm
down instead of 11.35 and `cavity_depth` follows. Growing the button costs nothing but
top-face area, of which there is plenty.

**There is no return spring.** There was one — a coil spring in a counterbore on top of a boss
— and it existed because a 4×4 tactile has 0.25 mm of travel and a weak spring, so the cap
rattled and the press was a click rather than a stroke. An 11 mm tactile has a real spring and
~0.7 mm of travel of its own, so both problems solved themselves:

- **no rattle**, because the plunger pushes the cap UP against its retention lip and holds it
  there. `btn_preload` is how far the post over-travels into the plunger to guarantee that —
  0.25 mm. The cap is preloaded against the lip exactly as before; the spring doing the
  preloading is just inside the switch now.
- **a stroke you can feel**: 0.45 mm of press after the preload has spent its share.

The direction of that preload is the whole design. Positive — post slightly long — and the cap
is pinned to the lip with the switch a little pre-depressed, which is harmless. Negative — post
slightly short — and the cap rests on the plunger with its lip floating clear of the catch, and
it rattles by exactly that error. So the post is deliberately made long, and `btn_preload` is
asserted to stay under half of `sw_travel` so print error at either end cannot close the switch
permanently. The switch is still the **stop** as well: the plunger bottoms in its own body and
the body takes the finger load.

Losing the spring also **simplified the holder**. The boss existed only to raise a rim for the
spring to seat on, with the switch pocket sunk inside that rim; with no spring there is nothing
to seat, so the switch stands directly on the floor and the holder is a plain cup. It reaches
11.35 mm down against the sprung version's 12.15.

**Where the pins go: straight down.** Four pins, four windows through the collar floor, soldered
underneath. The 4×4's two legs used to come out *sideways* through the pocket wall and then
along the floor and out through a notch in the collar's rim, because a boss stood in the middle
and there was nowhere else for them to go. With no boss the floor is the direct route.

The pin field is **rectangular, not square**: 2 mm in from the side on one axis (3.5 mm off
centre on an 11 mm body) and 5 mm apart on the other (2.5 mm off centre). `sw_pin_pitch` is
therefore a `[x, y]` vector — it was a single number on the assumption that a 12×12's legs sit
at the corners of a square, which they do not. Windows are 2.8 mm square on each pin: about
0.9 mm of tolerance around a 1 mm leg in every direction, and 1.1 mm of land left between the
two rows on the tight axis. They cannot be much more generous without eating that land. What is
left of the floor is a cross, and the switch seats on it: 90 of its 121 mm².

**Four locating ribs, not a pocket.** The pins do *not* locate the switch — inside windows sized
for tolerance it can slide several millimetres, which is a switch that wanders under your thumb.
The obvious fix, a pocket sunk into the floor, costs case height: every millimetre of pocket is a
millimetre of `cavity_depth`, because the switch's base is what sets where its plunger ends up.

So instead there are four ribs standing *beside* the body at the midpoint of each edge, giving it
`sw_locate_clr` = 0.4 mm of play per side and nothing more. They cost **no depth** — they are
beside the switch, not under it. One per side rather than four at the corners because a corner
rib would have to fit in the 0.82 mm between the switch's corner and the cap's bore, where at the
mid-edge there is 3.1 mm; as drawn they reach 7.91 mm from the axis against the cap's 8.6 mm
bore, which is asserted.

Nothing holds the switch **down** and nothing needs to: pressing the cap loads it straight into
the floor, and the plunger's reaction on release pushes it the same way.

A dome shows lean that a flat disc hides, and a Ø22 flange shows more of it than a Ø18 one, so
the guide matters more than it used to: it is the cap's **body wall** running in a matching bore
— 1.4 mm of it in the shell plus 5 mm inside the holder — rather than a skirt. `btn_lean()` in
the asserts turns that into the number you actually care about: how far the flange edge can
lift, 0.69 mm on the bigger flange against a 1.2 mm limit.

That guide is also why the `holder` is a **cup** and not a flat plate. Stack guide, relief,
aperture and switch body in series under the top face and it reaches ~17.5 mm — into the devkit
at 15.9. Standing the switch *inside* the guide puts the two side by side instead of end to end.

**Which of the `sw_*` numbers actually matter.** The switch's height is given as **one** number,
`sw_h` = 8.0 — total above its seating plane, pins excluded — because that is the one you can
put a caliper across, and because it is the only thing the post's length depends on:

```
plunger_z()  = bh_relief_z1() - sw_h          ->  9.75 - 8.0 = 1.75
btn_post_h() = plunger_z() + btn_preload - btn_ceil_z()
             = 1.75 + 0.25 + 5.3 = 7.30
```

The body/plunger split does not appear there. It only decides where `sw_top_z()` falls, and the
one thing that cares is the body staying clear of the cap's dome — above the cap's straight bore
the inner fillet closes to Ø15.6 against the switch's 15.56 mm diagonal, which is 0.02 mm, i.e.
nothing. So `sw_h` is measured and `sw_body_h()` is derived from it rather than the other way
round: a wrong guess at `sw_plunger_h` cannot quietly change the post.

Two things are genuinely fussy, both asserted: `sw_plunger_d` must exceed `btn_post_d` or the
post overhangs the plunger onto the body and jams, and `sw_travel` must be at least twice
`btn_preload` or the switch sits close to permanently pressed. `sw_pin_len` is the one that
costs case height — it sets `cavity_min()`, so clipping the pins short buys the millimetre
back.

**Why the socket is on the side and not next to the USB.** Forced, not stylistic. The
devkit spans nearly the whole depth, so the rear wall is entirely taken by its USB window
and the board behind it. The `+x` wall is where the DAC can reach.

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
| `shell` | top face + four walls: button bore/recess/pilots, mic seat and posts, corner bosses, rear USB window, side socket panel |
| `base` | flat plate: devkit and DAC pockets, register lip, vents, counterbored screw holes |
| `button` | snap-in cap — the dome you press |
| `holder` | switch carrier and cap guide — the whole button mechanism |
| `clamp` | mic clamp bar |
| `coupon` | button + mic fit test — see below |
| `fit` | devkit bed fit test — the **whole** bed, tab and rear stops included, on a thinned plate |
| `all` | assembled preview |

Select with the normal variable flag `-D part="..."` (a `$`-prefixed variable would be
ignored by `-D`).

### ...or in Fusion 360

The same model, same parameters and same asserts are ported to a Fusion 360 script in
[fusion/](fusion/) — standard sketches, extrudes, revolves, lofts and combines, one
component and one timeline group per part, taking the same part names as `-D part=`. Its
`fusion/test.sh` needs no Fusion at all: it runs the design checks in plain Python, then
renders the port's own geometry through OpenSCAD and diffs it against `stl/`:

```bash
./fusion/test.sh          # design floors, then every part vs the OpenSCAD render
./fusion/test.sh --png    # ...and a picture of each part in fusion/tests/emitted/
```

See [fusion/README.md](fusion/README.md) for how to register the script folder in Fusion
and where the two models deliberately differ (true arcs instead of `$fn = 64`, and no
Fusion user parameters — Python is still the parametric engine).

## Print the coupon first

The coupon is the button bore, its pilots and the mic seat cut out of the real top face,
plus the three small parts that mate with them. Ten minutes of printing tells you
whether the snap, the travel and the gasket land before you commit four hours to the
shell — and because the mechanism is now in `holder`, most fixes mean reprinting the
coupon and the holder rather than anything large.

```bash
"$OPENSCAD" -D 'part="coupon"' -o stl/coupon.stl voice-case.scad
```

- Cap won't snap in, or snaps in and won't come out → `btn_lip_over`, `btn_slit_w`,
  `btn_slits`. The lip has to collapse past *both* bores before it reaches its relief.
- Cap rattles → `btn_face_gap` (it is the free travel *and* the rattle).
- Cap **leans** when you press it off-centre → `btn_guide_clr` first, then `bh_guide_h`.
  `btn_lean()` predicts it; the assert caps it at 1.2 mm.
- Cap binds or feels gritty → the reverse: `bh_guide_clr` is too *tight* for however far
  the holder's two M2s let the collar sit off axis. It must stay looser than the shell's.
- Cap presses but the switch never clicks → the post is short, or the stroke is being
  eaten before it gets there. Check in this order: `btn_face_gap` vs `btn_stroke()` (the
  flange bottoming on the recess floor), then the cap body's far edge vs the collar
  floor, then `sw_plunger_h` — if your switch's plunger is shorter than the default the
  post never reaches it. All three are asserted; `./test.sh` names whichever one it is.
- **Cap goes in and then will not move at all** → it is binding, and there are exactly three
  places it can bind. All three were at 0.2–0.3 mm and all three are now 0.8–1.15:

  | path | what it is | now |
  |---|---|---|
  | radial | body in the shell bore, per side (`btn_guide_clr`) | 0.30 |
  | axial | cap body's far edge vs the collar floor (`btn_lip_slack`) | 0.80 |
  | axial | lip bottoming in its own relief (`btn_lip_slack`) | 0.80 |
  | axial | flange vs the recess floor (`btn_face_gap`) | 1.15 |

  Note the middle two are the **same number**: subtract the chains and both come out as exactly
  `btn_lip_slack`, so raising it fixes both at once. If a print still binds, raise
  `btn_guide_clr` first (it costs lean, which `btn_lean()` reports) and `btn_lip_slack` second
  (it costs holder depth, which `cavity_min()` reports).
- **Cap needs a shove to snap in** → the lip has to collapse 0.5 mm radially past the shell bore,
  and it does that by flexing eight 1.2 mm fingers 5.5 mm long. More `btn_slits` or a wider
  `btn_slit_w` both make it easier; less `btn_lip_over` makes it easier and shallower on the
  catch, which `./test.sh` bounds at 0.3 mm of shoulder.
- **Cap rattles** → the post is short: it is resting on the plunger with its lip floating
  clear of the catch. Raise `btn_preload`. This is the one failure the sign of the preload
  exists to prevent.
- **Switch permanently closed / no click at all** → the post is too long, or `sw_travel` is
  smaller than the default. `btn_preload` is asserted against half of `sw_travel`; measure the
  travel and the assert will tell you.
- Cap will not go down over the switch → the switch's diagonal is wider than the cap's bore.
  Asserted, and the message names the `btn_wall_od` it needs.
- Switch tips or will not sit flat → the pins are not lining up with the four floor windows.
  `sw_pin_pitch` is `[x, y]` — measure both, they are not the same.
- Switch wanders / rocks in the holder → `sw_locate_clr`, the four locating ribs. Lower it to
  0.2. If it will not drop in past them, raise it instead.
- Mic board doesn't seat flat → `mic_seat_depth`, `clr`.

**`s3_w` and `s3_l` set the case size.** Both were first recorded over something that is not
the laminate — 67 × 30 — and both are now measured off the PCB: **63 × 28**. Depth is
`2·wall + 2·clr + 2·reg_t + s3_w + 2·s3_board_clr`, so a millimetre off `s3_w` is still a
millimetre off the puck.

**Measure your DAC board before printing the shell.** These are the numbers that place
the hole, and my defaults are estimates from a product photo, not from calipers:

| Param | What to measure | Default |
|---|---|---|
| `dac_jack_w` | socket body width along its edge | 6.0 |
| `dac_jack_h` | socket body height above the PCB face | 6.5 |
| `dac_jack_axis` | barrel **axis** height above the PCB face | 3.2 |
| `dac_jack_overhang` | how far the socket body sticks past that long edge | 2.5 |
| `dac_jack_inset` | board **end** edge to the near side of the socket body | 3.0 |
| `board_clr` | per-side clearance in both friction pockets | 1.0 |
| `dac_w`, `dac_l` | board size across x, along y | 20 × 33 |

The socket is **not centred on its edge** — it sits in the corner, 3 mm from the end of
the board. That offset has to be absorbed somewhere, and **the hole absorbs it**:

    dac_jack_off() = dac_jack_end * (dac_l/2 - dac_jack_inset - dac_jack_w/2)   // +10.5
    dac_jack_y()   = dac_pos_y() + dac_jack_off()                               // +10.5

This is inverted from how it started. The hole used to be pinned to the middle of the
wall and the board slid in y to put its corner socket behind it, on the grounds that an
off-centre hole reads as a mistake while a hidden board does not. That trade stopped
being available: the board's y is spent on clearing the corner bosses
(`dac_pos_y = 0`, see above), so there is nothing left to slide, and the hole goes where
the socket is.

One assert holds it together: that the socket offset really is out at the board end. If
it collapses toward zero, someone has started typing it in rather than deriving it — and
since the hole now follows the board, that is the failure that would put the hole 10 mm
away from its socket.

`dac_w`/`dac_l` matter less — the board is positioned from its socket edge, so a wrong
size mostly slides the far edge inward. But `dac_l` now feeds the derived offset too, so
it is worth getting roughly right. `dac_jack_overhang` and `dac_jack_axis` decide how
deep the plug seats.

## Parameters

All in [modules/params.scad](modules/params.scad). Common edits:

| Param | Meaning |
|---|---|
| `plan_x`, `plan_y`, `cavity_depth` | footprint and interior height. **All three have derived floors** — `plan_x_min()`, `plan_y_min()`, `cavity_min()`; the asserts name the number needed |
| `shared_wall` | the single wall between the two beds. Each pocket still draws its own `pocket_wall` there and they overlap into exactly this |
| `s3_comp_h` | tallest thing on the devkit's component side. This sets the case height |
| `s3_w`, `s3_l` | devkit PCB footprint (63 × 28, measured off the laminate). One sets `plan_y`, the other `plan_x` — **measure, never infer** |
| `s3_pos_x` | devkit x — **derived**, parked one `shared_wall` inboard of the DAC's cavity. The DAC is the fixed end of the chain because its socket has to reach the `+x` wall |
| `s3_boss_margin` | that air gap. It is in `plan_x_min()` millimetre for millimetre |
| `boss_inset` | how far the corner bosses sit into the corners. It is the `-x` end of the width chain, so it sets `plan_x`; floored at 9.6 by the register lip |
| `s3_seat_h` | pocket floor under the devkit — this is what sets the rear window's height |
| `s3_board_clr` | per-side clearance in the **devkit** pocket. The one number to tune with `part="fit"`; tighter than `board_clr` because nothing else locates that board |
| `s3_tab_cover` | how much of the board's front edge the retention tab sits over. `0` removes the tab and the pocket goes back to being a tray |
| `s3_tab_preload` | how far the tab's ramp reaches below the board's top face **at its edge**. Lower it if the board will not go in |
| `s3_rear_stops`, `s3_rear_stop_h` | the two stops that close the rear end. `false` reopens it; the height is capped at `pcb_t` or the board cannot be assembled |
| `usb_panel_t` | local rear-wall thickness behind the USB window. This is what buys back the plug reach the rear stops cost |
| `board_clr` | per-side clearance in the **DAC** pocket. Stays loose — the socket locates that board |
| `dac_pos_y_set` | DAC board centre in y. `0`, and it wants to stay there — offset costs two of `plan_y` for every one of itself. The hole follows the socket, not the reverse |
| `mic_pos` | INMP441 position on the top face |
| `dac_jack_*` | the DAC's onboard socket — see the measurement table above |
| `jack_panel_t` | local wall thickness behind the socket; the reason a plug seats |
| `jack_hole_d` | plug clearance hole through that panel |
| `btn_wall_od` | cap **body** diameter; the whole button chain — shell bore, guide, catch, lip, collar — follows from it |
| `btn_cap_d` | flange diameter: what you see. `btn_dome_h` is how proud it stands |
| `btn_guide_clr` | body-in-bore clearance, per side. Too tight and the cap **seizes**; too loose and it rocks. 0.2 seized, 0.3 works, `btn_lean()` is the cost |
| `btn_lip_slack` | doubles as the lip's room in its relief *and* the gap from the cap body to the collar floor. 0.3 bottomed out; 0.8 works |
| `btn_preload` | how far the post over-travels into the plunger with the cap's lip on the catch. This is what stops the cap rattling — it must be positive, and under half of `sw_travel` |
| `btn_face_gap` | flange to the recess floor at rest; must clear the whole stroke |
| `sw_body`, `sw_h`, `sw_travel` | the 11×11 tactile: footprint, total height without pins, travel — **measure these**. `sw_h` is what sets the cap's post length, on its own |
| `sw_plunger_d`, `sw_plunger_h` | the pin on top. `sw_plunger_d` must exceed `btn_post_d`; `sw_plunger_h` only splits `sw_h` and never touches the post |
| `sw_pin_pitch` | `[x, y]` pitch of the pin field — **rectangular**, 7 × 5 as measured |
| `sw_pin_win`, `sw_pin_len` | window size per pin, and how far the pins reach below the body. `sw_pin_len` is what sets `cavity_min()` |
| `sw_locate_*` | the four ribs that locate the switch. `sw_locate_clr` is its play per side — the one to tune if it wanders or will not drop in |
| `bh_guide_h` | how much guide the holder adds below the shell's own 1.8 mm |
| `bh_*` | the rest of the holder — relief, floor, collar, screw posts |
| `clr` | global fit clearance (raise if parts are tight) |

Every relationship these can break is asserted. Change one and run `./test.sh` — it
will name the collision rather than let you find it with a printed part.

## Print settings

- **Shell: top face DOWN**, no supports. The top edge is a 45° chamfer rather than a
  fillet precisely so it prints support-free in this orientation, and the button
  recess and mic port come out as crisp first layers. The USB window and jack
  bore are horizontal holes in vertical walls — short bridges, no support needed.
- **Base plate**: flat, pockets up.
- **Button cap: dome DOWN**, no supports. The top fillet meets the plate tangentially
  like any rounded-bottom part, the flange is reached by a 45° flare, and the post
  narrows upward — printed this way the cap is a plain cup with no overhang in it. Do
  *not* print it flange-down: that leaves the whole inner ceiling of the dome in mid-air.
- **Holder: floor DOWN** — the opposite end from the cap, and the opposite of the old
  plate holder. It is a cup, so the floor goes on the plate and the collar, the switch
  block and the two screw posts all grow up off it as vertical walls.
- **Mic clamp**: bar face down, pad up.
- 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- **PETG for the button cap** if you have it — the slit body is a snap-fit and PLA
  gets brittle at that thickness. The shell and plate are happy in either.

## BOM

- 1× ESP32-S3-DevKitC-1, N16R8 (16 MB flash / 8 MB octal PSRAM)
- 1× PCM5102A DAC breakout **with an onboard 3.5 mm socket** — the case uses that
  socket directly, so there is no panel-mount jack and no analog flying leads
- 1× INMP441 MEMS mic breakout
- 1× **11 × 11 mm 4-pin** tactile switch with a pin plunger (the 12×12 family). Measure its
  body height, plunger and travel — see `sw_*` in params. **No return spring**: this switch
  has its own, which is the whole reason the coil spring came out
- 4× M3 heat-set inserts + 4× M3×8 screws for the corners (M3×10 if your inserts are deep)
- 2× M2×10 self-tap screws for the button holder — they run the full height of the collar's
  screw posts before they reach the blind pilots in the top face
- 2× M2×8 self-tap screws for the mic clamp (they reach through the bar into the posts)
- 1× foam/EVA gasket **ring** for the mic, ⌀12 mm outer with a bore that clears the
  module's port — punch it out of foam tape; a solid disc would seal the port shut
- 4× self-adhesive rubber feet (stuck straight onto the flat plate — no recesses)
- hookup wire — the devkit's 5 V and 3V3 rails feed both breakouts

## Assembly

1. **Heat-set the four M3 inserts** into the shell's corner bosses, from the open (base) side.
   Only the corners get inserts — the button holder and the mic clamp are M2 self-tap into
   printed pilots, which a built one has shown is enough.
2. **Build the button module on the bench**, before it goes anywhere near the shell.
   Reaching down the open mouth of the collar: drop the 11 × 11 switch in **plunger up**,
   with its four pins through the four windows in the floor, until the body sits on the cross
   of floor between them and between the four locating ribs, which give it 0.4 mm of play and no
   more. It stands well proud of the collar — that is correct, it reaches up into the cap. Turn the holder over and **solder the leads to the pins from underneath**;
   that is the only side you can reach them from, so do it now. Leads to **G38** and **GND**,
   left long.
3. **Bench-test the whole action**: press the cap into the holder's bore until the lip
   catches. Now press the dome. You should get about half a millimetre of travel and a
   definite click, and the cap should return on its own with the lip still held — the
   switch's own spring is doing that. Check the cap does **not** rock or rattle when you
   waggle it: if it does, the post is short and `btn_preload` wants raising. Press it
   off-centre and check it does not lean noticeably. None of this needs the shell, and all of
   it is tunable by reprinting these two parts.
4. **Screw the holder to the shell** — collar face against the wall's inner face, 2× M2
   up through the screw posts into the blind pilots — and only then **snap the cap in
   from the outside**. The cap has to go in that way round: its 22 mm flange cannot pass
   back through the 16 mm bore, so the cap is always the last thing fitted, never
   pre-assembled into the holder.
5. **Mic**: gasket ring into the seat, INMP441 on top of it port-down, then the clamp
   bar across the two posts, pad down onto the middle of the board, 2× M2. The posts
   flank the board rather than sit under it — they have to, since the board lies on
   its own gasket — so the bar is what holds it. Tightening those two screws is what
   compresses the gasket, and that seal is the acoustic design, not a nicety.
6. **Both boards into the base plate**, component sides **up**. The devkit goes in
   **tilted**: hold it rear-up about 2°, put its front edge under the tab on the front
   wall, then push forward until the rear corners drop behind the two stops either side of
   the USB notch. It will not drop in flat (the tab is over the front edge) and it will not
   slide straight in (the stops are behind the rear edge). Once home it is preloaded back
   against those stops and cannot lift. The DAC slides into the short pocket from the open
   `+x` end, socket first. Solder wires directly to the DAC's pads —
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

**The button is a sprung cap over a tactile switch, not a panel-mount switch.** The
speaker case uses a 12 mm panel-mount momentary and it is the more robust part, but its
body and terminals need ~30 mm behind the panel; that would have made this puck ~60 mm
tall and killed the VPE proportions. What the printed cap used to cost was feel — a bare
tactile gives 0.25 mm of travel, so the old button *clicked* rather than moved. Adding
the reference's return spring buys that back: 1 mm of free stroke before the switch is
touched, a click at the end, and a positive return that does not depend on the switch's
own spring. The switch is still what stops the stroke, which is the part that makes it
tolerant of print error.

**The mic gets one short gasketed port, not a hole cluster.** Same call, and same
reason, as the speaker case: a cluster of small holes through a 3 mm wall is a
Helmholtz resonator sitting right on top of speech. One short hole with the MEMS port
pressed to a gasket leaves near-zero front volume and moves the resonance well clear.

## Desk only

There is no keyhole wall mount. Voice S3 wants to sit where you talk to it, and the
rear wall is full of cables. Wall-mounted intercom nodes are what
[../kitchen-case](../kitchen-case) and [../terrace-case](../terrace-case) are for.
