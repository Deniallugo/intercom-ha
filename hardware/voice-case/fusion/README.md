# Voice S3 desk puck — Fusion 360 port

The desk puck as a Fusion 360 script: same parameters, checks and parts as
[`../voice-case.scad`](../voice-case.scad). **This is the source of truth**; the OpenSCAD
is kept in step and serves as an independent reference for `test.sh`.

```
fusion/
  test.sh                  design checks + geometry diff against the OpenSCAD STLs
  tests/scad_emit.py       adsk stand-in that emits OpenSCAD (no Fusion needed)
  tests/render_diff.py     renders that and compares against ../stl/*.stl
  VoiceCase/
    VoiceCase.py           entry point: pick a part, check, build, export
    vc/params.py           every number and derived dimension
    vc/checks.py           design constraints
    vc/build.py            CSG helpers on sketches + features
    vc/shell.py  base_plate.py  button_cap.py  button_holder.py  mic_clamp.py  coupons.py
```

## Running it

1. Fusion → **Utilities → Scripts and Add-Ins** (Shift+S) → **+** next to *My Scripts* →
   `hardware/voice-case/fusion/VoiceCase`.
2. Select **VoiceCase** → **Run**, pick a part (default `all`). It builds into a new document.

Parts: `all` · `shell` · `base` · `button` · `holder` · `clamp` · `coupon` · `fit` · `fit-front`.

Flags at the top of `VoiceCase.py`: `PART`, `ASK`, `NEW_DOCUMENT`, `USER_PARAMETERS`,
`EXPORT_STL`. `EXPORT_STL` is on by default and writes one STL per part, in print
orientation, to `VoiceCase/stl/`.

The script is one-way: edits made in the Fusion timeline are not read back. Change
`vc/params.py` and re-run. The `ref_*` user parameters are read-only copies for
dimensioning hand-drawn sketches; editing them changes nothing.

## Checking without Fusion

```
./test.sh                 # design checks, then every part vs the OpenSCAD render
./test.sh --png button    # also writes tests/emitted/button.{scad,stl,png}
```

The design checks run in plain Python (`python3 -m vc.checks` from `VoiceCase/`), and
`VoiceCase.py` refuses to build if one fails:

```
plan_x     = 73     min 72.6    boss line -> devkit -> shared wall -> DAC -> socket
plan_y     = 74     min 73.7    (devkit length 73.7 | DAC vs bosses 66.2)
cavity     = 29     min 28.85   (bare 16.1 | mic 23.7 | button holder 28.85)
outer      = 73 x 74 x 35 mm (41.5 over the button)
OK — all design checks pass
```

The geometry diff needs OpenSCAD. Volumes must match within 1 % (true arcs vs `$fn = 64`)
and bounding boxes within 0.05 mm. Every part is also rebuilt under deliberately wrong
sketch-plane conventions and must come out identical.

## Conventions

- Every solid is a sketch + extrude/revolve/loft; every boolean is a Combine. Each part is
  one component with one timeline group.
- **Nothing selects faces or edges.** Profiles come from computed coordinates, so a
  parameter change cannot re-target a feature. The top chamfer is a loft, not a
  `ChamferFeature`, for that reason.
- **Sketch-plane axes are probed, not assumed.** Fusion's XZ plane has v along −Z; assuming
  otherwise mirrors the cap. `Part._frame` measures each plane.
- One closed loop per sketch, so `profiles.item(0)` is unambiguous.
- Millimetres everywhere; conversion to cm only in `vc/build.py`.
- Frames match the OpenSCAD: z runs from the top face down.
- A `cut()` tool that misses its target is reported, not ignored.

## Check the export

`test.sh` does not see what Fusion writes to STL/3MF. Two failures seen there:

- The cap's outer dome fillet exported as a straight cone, leaving a 0.15 mm wall.
  Re-run and re-export.
- The holder's locating ribs exported as separate bodies (fixed via `bh_rib_embed`).

On every export check that each part is **one body** and that a section through the cap
dome shows 1.2 mm of wall all round.
