# Voice S3 wall unit: Fusion model

This is the wall unit as a Fusion script. It builds both boxes, the plate and every printed part.
It also builds **every electronic part as its own component**, so you can move any part in Fusion
and have the case follow it.

**This is the source of truth.** The same approach as
[`../../voice-case/fusion`](../../voice-case/fusion) applies. Python is the parametric engine.
Fusion gets standard sketches, extrudes, revolves, lofts and combines. The OpenSCAD in `../` is
kept so that `test.sh` can compare two independent builds of the same numbers. That comparison is
the only way to check this script without opening Fusion.

```
fusion/
  test.sh                    design checks, sync round-trip, geometry diff vs the OpenSCAD
  tests/scad_emit.py         adsk stand-in that emits OpenSCAD (the port renders offline)
  tests/render_diff.py       port vs OpenSCAD, plane-invariance, electronics-vs-case solids
  tests/test_sync.py         drag -> sync -> rebuild, against an emulated document
  VoiceWallCase/
    VoiceWallCase.py         what Fusion runs
    vwc/placement.py         WHERE the movable parts sit; `sync` rewrites this file
    vwc/params.py            every other number, and every derived dimension
    vwc/elec.py              every electronic part, as data (dummies, checks, sync all read it)
    vwc/checks.py            the design's constraints, including the electronics
    vwc/case.py              shells, lids, amp sled, voice tray, sleeve, coupons
    vwc/button.py            plunger, dome, holder, mic clamp
    vwc/plate.py             wall plate, lock bracket
    vwc/electronics.py       builds elec.py as Fusion components
    vwc/assembly.py          what goes where; the browser tree
    vwc/sync.py              Fusion moves -> placement.py
    vwc/build.py  vwc/xf.py  the CSG vocabulary on sketches/features; rigid transforms
```

## Running it

1. In Fusion, open **Utilities → Add-Ins → Scripts and Add-Ins** (Shift+S), click **+** beside
   *My Scripts*, and pick `hardware/voice-wall-case/fusion/VoiceWallCase`.
2. Select **VoiceWallCase** and click **Run**. It asks what to build:

| Answer | Builds |
|---|---|
| `all` (default) | The whole unit on the wall: printed parts, electronics, plate and lock |
| `electronics` | Only the electronics, in their positions |
| `amp-shell` `amp-lid` `amp-sled` `voice-shell` `voice-lid` `voice-tray` `sleeve` `plunger` `dome` `holder` `clamp` `plate` `lock` | One printed part, in its print orientation |
| `coupon-amp` `coupon-voice` | A front-wall fit slice |
| `sync` | Writes the parts you moved back to `placement.py` (see below) |

Each build goes into a **new document**. The flags at the top of `VoiceWallCase.py` are:

| Flag | Effect |
|---|---|
| `PART`, `ASK` | Pin a part and skip the prompt |
| `GHOST` | Opacity of the shells, lids and plate in the assembly, so the electronics show through |
| `EXPORT_STL` | One STL per **printed** component into `VoiceWallCase/stl/`. Electronics are never exported |
| `USER_PARAMETERS` | Writes the `ref_*` reference parameters |

The browser tree after `all`:

```
amp electronics          (sub-assembly, placed where the amp box is)
  ZK-502MT · knobs · MP1584 · power switch · DC plug · AUX plug (amp) · amp wiring
voice electronics        (sub-assembly, placed where the voice box is)
  ESP32-S3 devkit · PCM5102A · AUX plug (DAC) · INMP441 · tactile switch · voice wiring
amp shell, amp lid, amp sled, voice shell, voice lid, voice tray, sleeve,
plunger, dome, button holder, mic clamp, wall plate, lock bracket
```

The printed parts are top-level on purpose. Placed inside a group, Fusion put the amp shell
rotated off its box on the first real run. A top-level placement is the form that came out right
for every part.

## Moving parts in place

Inside its electronics group, every part is built at the **identity**, in its box's local frame:

| Axis | Direction |
|---|---|
| x | Across, + to the right as you face the unit |
| y | Up from the box's bottom face |
| z | Into the box from its front face |

A part you move therefore shows its move as box-local x / y / z. The loop:

1. Run `all`.
2. Move a part inside its group: select it in the browser, then **Modify → Move/Copy**, or drag it.
   **Inspect → Interference** shows what it now hits.
3. Run the script again and answer `sync`. It works on the **active** document (the one you
   moved things in). It reads every moved part, works out the new placement numbers, rewrites
   `vwc/placement.py`, re-runs the design checks and reports them.
4. Run `all` again. Every case feature tied to a moved part follows it:

| You move | Number written | What follows it |
|---|---|---|
| ZK-502MT, x | `amp_x` | Standoffs, faceplate window, heatsink vents, terminal access holes, lid cable window |
| ZK-502MT, y | `amp_lift` | Standoff height, faceplate window, and the box height |
| ZK-502MT, z | `amp_setback` | Box depth. Only valid in `holes` mode; the checks refuse it in `faceplate` mode |
| MP1584, x / z | `mp_x`, `mp_dz` | Its pocket on the sled |
| power switch, z / y | `psw_dz`, `amp_psw_y` | The side-wall cut-out |
| ESP32-S3 devkit, x / z | `s3_x`, `s3_z0` | Its tray pocket, the voice side vents, and the DAC behind it |
| PCM5102A, x / z | `dac_dx`, `dac_dz` | Its pocket and the socket notch |
| INMP441, x / z (it is on the top face) | `mic_pos` | Gasket seat, port, clamp posts and clamp |
| tactile switch, x / y | `btn_pos` | Bore, recess, holder pilots, holder, plunger and dome |

The sleeve has no part of its own to move. Edit `sleeve_x` / `sleeve_dz` in `placement.py`. The
amp top hole, the voice floor hole, the tray hole and both cables follow.

`sync` does **not** sync these, and says so in its report:

- **A part that follows another.** The knobs, the plugs and the wiring follow their board.
  Move the board instead.
- **An axis the part does not own.** A board lying in a tray pocket cannot leave the floor,
  so its y move is ignored.
- **A rotation.** Only translations map to numbers.

`sync` adds your move to the placement the document was **built with**, which every build stamps
into the design. Syncing twice without rebuilding therefore gives the same answer, not a double
move. You can also skip Fusion entirely and edit `placement.py` by hand.

Sizes are not positions: board outlines, connector heights, plug sizes and clearances live in
`vwc/params.py`. **Fusion edits are not read back**, apart from what `sync` reads. A feature edited
in the timeline, or a sketch dragged, stays in that document only. The `ref_*` parameters in the
Parameters dialog are copies for hand-drawn sketches and drive nothing.

## The electronics are dummies

Board outlines and connector positions come from `params.py` and carry its tags
(`[measured]`, `[user]`, `[photo]`, `[assumed]`). The bodies on them are **[assumed] typical
sizes**: pot cans, jack bodies, the WROOM can, dupont housings, plug heads, the rocker's bezel.
They are there to be seen and to collide, not to be trusted to 0.1 mm. When you measure a part,
put the number in `params.py` (electronics block at the end).

Cables are drawn as illustrative routes:

- the patch cable and the 5 V lead, through the sleeve;
- the 24 V tap from the barrel-jack pins to the MP1584;
- the switch leads;
- the speaker leads and the DC cable, out of the lid window and down the channel.

They are never collision-checked, because they bend.

## Checking it without opening Fusion

```
./test.sh                     # design checks + sync + geometry diff of every printed part
./test.sh --quick             # the geometry diff on the small parts only
./test.sh --interference      # + every electronic part vs the printed parts, as solids
./test.sh --picture           # + tests/emitted/picture-{inside,outside}-{iso,side}.png
```

OpenSCAD 2021.01 is enough. Set `$OPENSCAD` if it isn't at `/opt/homebrew/bin/openscad`.

1. **Design checks** (`vwc/checks.py`, plain CPython). These cover every assert from
   `../tests/asserts.scad`, plus three electronics checks:
   - every part against every other part in its box;
   - every part against the box cavity;
   - every part against the printed obstacles (lid bosses, sled or tray, standoffs, button holder,
     mic clamp, sleeve).

   The script runs these before it models anything, and refuses to build on a failure. Move the
   devkit into the button holder and the build names both parts.
2. **Sync** (`tests/test_sync.py`). Builds the real assembly through the stand-in, moves parts,
   and checks that `sync` reads the right numbers. It also checks that `sync` ignores what it
   should, survives a second sync, and rewrites only the lines that changed.
3. **Geometry** (`tests/render_diff.py`). Each printed part is emitted through the port's own
   code, rendered, and compared with `../voice-wall-case.scad`. The OpenSCAD is rendered with the
   **current `placement.py` values passed in with `-D`**, so after a `sync` the two still
   describe the same unit. Tolerances are 1 % volume and 0.05 mm bounding box.
4. **Plane invariance.** Parts are also re-rendered under deliberately wrong sketch-plane
   conventions and must come out identical. That is the check the inside-out button cap of
   voice-case would have failed.
5. **`--interference`.** Intersects each electronic part with everything printed in its box, in
   the assembled position, using the real shells, pockets, windows and holes rather than boxes.

## How it is built

[`../../voice-case/fusion/README.md`](../../voice-case/fusion/README.md) explains the rules this
port inherits:

- No face or edge is ever selected.
- Every sketch has exactly one closed loop.
- Sketch-plane axes are probed rather than assumed.
- Millimetres are converted to the API's centimetres in one place.

What is new here:

- **Any-axis features.** A box is cut through its front face (z), its top and floor (y) and its
  side walls (x). The prisms, cones and lofts in `build.py` therefore take the axis as an
  argument.
- **Components are built at the identity and placed last.** The plane probe reads
  `worldGeometry`. Whether that includes the occurrence's own transform is not something to
  depend on, and at the identity it doesn't matter. Positions are applied together after the
  final feature and captured in one snapshot, because a parametric design can revert an
  uncaptured move when a later feature recomputes.
- **Print frame = component frame.** The sled and tray are authored in the box frame (where the
  board and the lid locate them), then turned flat with one Move feature. Every printed component
  therefore exports print-ready. The assembly undoes that move with the occurrence transform.
- **No mirrors.** Fusion occurrences take rigid transforms only. The OpenSCAD placed the wall
  plate with `mirror()`. Here it is a rotation that also flips x, which gives the same solid
  because the plate is symmetric in x.
- **Lid-boss taper.** It is a loft between a thin rectangle on the wall and the boss's front disc.
  The OpenSCAD was changed to build the same shape (a hull of exactly those two plus the
  cylinder), so both sides compare like with like.

## What has not been checked

- **Fusion itself.** This port has been run against the emulator only. The API calls are the
  ones the voice-case port already makes, plus these, which the emulator stands in for:
  - nested `occurrences.addNewComponent`
  - `Matrix3D.setWithCoordinateSystem`
  - `occurrence.transform2`
  - `moveFeatures.createInput2`
  - `design.snapshots`
  - `design.attributes`
  - `occurrence.opacity` (cosmetic, wrapped)

  On the first Fusion run, check:
  - the tree matches the one above;
  - a moved part shows up in `sync`'s report;
  - the sled and tray STLs come out lying flat.
- **The appearances.** They are looked up by name in Fusion's library, and those names vary
  between versions. A failure leaves the part grey and is never fatal.
