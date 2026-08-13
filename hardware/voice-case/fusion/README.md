# Voice S3 desk puck — Fusion 360 port

The Voice S3 desk puck as a Fusion 360 script. Same parameters, same derived chains, same
design checks, same seven parts as [`../voice-case.scad`](../voice-case.scad).

**This is the source of truth now.** It began as a port of the OpenSCAD and the relationship
has inverted: changes are made here first, and the OpenSCAD is brought alongside afterwards.
It is still worth keeping, because `test.sh` diffs this port's geometry against `../stl/*.stl`
— two independent implementations of the same numbers is a stronger check than either alone,
and it is the only way to verify this script without opening Fusion.

```
fusion/
  test.sh                  design checks + a geometry diff against the OpenSCAD
  tests/scad_emit.py       an adsk stand-in that emits OpenSCAD, so the port can be
  tests/render_diff.py     rendered and compared without opening Fusion
  VoiceCase/
    VoiceCase.py           what Fusion runs: pick a part, check, build, optionally export
    VoiceCase.manifest
    vc/params.py           every number, and every derived dimension  (was modules/params.scad)
    vc/checks.py           the design's own constraints                (was tests/asserts.scad)
    vc/build.py            the CSG vocabulary on sketches + features   (was modules/lib.scad)
    vc/shell.py  vc/base_plate.py  vc/button_cap.py
    vc/button_holder.py    vc/mic_clamp.py  vc/coupons.py
```

## Running it

1. Fusion → **Utilities → Add-Ins → Scripts and Add-Ins** (Shift+S) → the **+** beside
   *My Scripts* → pick `hardware/voice-case/fusion/VoiceCase`.
2. Select **VoiceCase** → **Run**. It asks which part; the default is `all`.
3. It builds into a **new document**, so re-running never disturbs anything you have open.

Parts: `all` (assembled preview) · `shell` · `base` · `button` · `holder` · `clamp` ·
`coupon` · `fit` — the same names `-D part=` took.

To pin a part and skip the prompt, or to export STLs, edit the flags at the top of
`VoiceCase.py` (`PART`, `ASK`, `NEW_DOCUMENT`, `USER_PARAMETERS`, `EXPORT_STL`).
`EXPORT_STL` writes one file per component into `VoiceCase/stl/`, in each part's own print
orientation — the equivalent of `../build.sh`.

**Hand edits do not come back as code.** The script is one-way: Python generates the model,
and nothing reads the document back. A feature you edit in the timeline lives in that
document only, and because the next run builds into a *new* document it is not destroyed —
just ignored. Sketches carry no dimensional constraints either, so dragging a point deforms
that one profile and nothing follows it. Use Fusion to try something, then move the number
you liked into `params.py`. The `ref_*` parameters below are there to make that easier, and
they drive nothing.

Editing `vc/params.py` and re-running is the whole workflow. The script purges its own
modules from `sys.modules` first, because otherwise Fusion holds the first import for the
rest of the session and your edit appears to do nothing.

## Checking it without opening Fusion

```
./test.sh
```

Two halves. First the **design checks** — `tests/asserts.scad` ported to Python, needing
neither CAD package:

```
plan_x     = 74     min 73.6    boss line -> devkit -> shared wall -> DAC -> socket
plan_y     = 75     min 74.2    (devkit length 74.2 | DAC vs bosses 66.2)
cavity     = 29     min 28.85   (bare 16.1 | mic 23.7 | button holder 28.85)
outer      = 74 x 75 x 35 mm (41.5 over the button)
...
OK — all design checks pass
```

`VoiceCase.py` runs these **before** it models anything and refuses to build a design that
fails one, which is the contract `assert()` had in OpenSCAD. All 111 derived values were
diffed against the OpenSCAD ones and agree exactly.

Then the **geometry itself**. Fusion has no headless mode, so a change to `vc/*.py` would
otherwise only be checkable by clicking Run — which means every mistake costs a round trip,
and a mistake that merely MIRRORS something costs several, because it builds cleanly and
looks almost right. So `tests/scad_emit.py` implements the slice of the adsk API the port
uses and turns each feature into the equivalent OpenSCAD (extrude → `linear_extrude`,
revolve → `rotate_extrude`, loft → `hull`, combine → `union`/`difference`/`intersection`),
and `render_diff.py` renders that and compares against `../stl/*.stl`:

```
  shell      38.593 cm3   +0.03% vs scad  bbox delta 0.001 mm  OK
  base       28.930 cm3   +0.01% vs scad  bbox delta 0.000 mm  OK
  button      1.468 cm3   +0.16% vs scad  bbox delta 0.000 mm  OK
  ...
```

Volumes differ by a fraction of a percent because this port uses true arcs where the SCAD
used `$fn = 64`; the tolerance is 1 %, and bounding boxes have to match to 0.05 mm.
`--png` also writes a picture of each part, which is how you look at one without Fusion:

```
./test.sh --png button          # tests/emitted/button.{scad,stl,png}
```

The second block of that output re-renders every part under **deliberately wrong sketch
plane conventions** — see below for why that is the test that matters.

## How the port is built, and why that way

**Standard sketches and features throughout.** Every solid is a sketch plus an extrude,
revolve or loft; every boolean is a Combine. No temporary-BRep tricks, so each shape lands
in the timeline where it can be inspected, edited or rolled back like hand-drawn geometry.
Each part is one component, and its features are folded into a named timeline group.

**Nothing selects a face or an edge.** That is the discipline that makes a script this size
survive a parameter change. Fusion's fragile move is topological selection — "the top
face", "these four edges" — because it silently re-targets when a dimension moves. Here
every profile is drawn from computed coordinates and every boolean names its bodies, so a
changed parameter can only move geometry, never re-point a feature. The one place this
costs something is the 45° top chamfer: it is a **loft between two computed profiles**
rather than a `ChamferFeature`, which is also exactly what OpenSCAD's `hull()` did.

**No plane's orientation is assumed.** This is the one that bit: a construction plane's u/v
axes are its own business, and Fusion's XZ plane does *not* lay out the way it reads — its
v axis runs along model **−Z**. Authoring "(radius, z)" on it mirrored the button cap in z,
which built cleanly, looked plausible and was inside out; the devkit pocket's retention tab
is the one other profile drawn on a non-XY plane and went the same way. So `Part._frame`
**probes** each plane instead: three points into a scratch sketch, read back through
`worldGeometry`, and every authored coordinate is mapped through the answer — including the
sweep direction of arcs, which flips when the plane's frame is a mirror of the authored one.
`render_diff.py` then re-renders every part under four wrong conventions and requires the
solids to come out identical, so this cannot regress silently.

**Every sketch is one closed loop**, so `profiles.item(0)` is never ambiguous — rings like
the register lip are built as outer-minus-inner solids instead of two loops in one sketch.
Loops are chained point-to-point (each curve starts on the previous curve's end *point*),
so they are topologically closed rather than merely closed to a tolerance.

**Millimetres in, centimetres at the boundary.** The Fusion API is cm and every dimension
here is mm; the conversion happens in `vc/build.py` and nowhere else.

**Frames are the OpenSCAD ones, unchanged.** Case z runs from the top OUTER face *down*
into the box, and the base plate is drawn in its own frame with its seats inside
`with part.mirrored():` — the stand-in for `mirror([0, 0, 1])`. Keeping both means every
number in `params.py` reads exactly as it did, which is the difference between a port you
can review against the original and a rewrite you have to re-derive.

## Where it differs from the OpenSCAD

* **True arcs, not polygons.** `$fn = 64` is gone: the cap's dome fillets and every bore
  are exact geometry. The button cap is the only part whose STL is therefore not
  bit-identical to the OpenSCAD one, and it is better, not different.
* **Bodies are named, not positional.** Booleans re-resolve their target body by name after
  each feature rather than holding a proxy across it, because a proxy may not survive a
  combine.
* **A cut whose tool misses is reported.** OpenSCAD does not care whether a `difference()`
  tool touches anything; Fusion refuses the whole feature if one body in the set does not
  intersect. So `cut()` falls back to cutting one at a time and tells you which tool
  missed — a cut that was meant to land somewhere is a real finding.
* **Fusion's user parameters are reference copies, not the source.** The parametric engine
  is Python, as it was OpenSCAD: `params.py` computes coordinates and the sketches are drawn
  to them. But the script does deposit the headline numbers in the Parameters dialog as
  `ref_*` (see `vc/parameters.py`), so a sketch you draw by hand can be dimensioned against
  the case — `ref_plan_x/2`, `ref_boss_cx`, `ref_dac_axis_z` — instead of you looking each
  one up in the Python. **Editing one changes nothing**: no feature has a dimensional
  constraint tied to it, so the model will not move. Change the value in `params.py` and
  re-run. The `ref_` prefix keeps them clear of any parameter you create yourself (the
  script would otherwise overwrite a same-named one of yours) and sorts them together.
  Turn the whole thing off with `USER_PARAMETERS = False`.
* **The helper "render smoke" asserts are gone.** They existed so `--hardwarnings` would
  fail on a module that produced no geometry. Building the parts is that check now, and an
  empty profile raises.

## What is still in the OpenSCAD

The full design archaeology — why every number is what it is, what it used to be, and which
failure made it move — is in [`../modules/params.scad`](../modules/params.scad) and
[`../README.md`](../README.md). The Python keeps the operative constraint for each
parameter (what breaks if you move it) and points at those for the rest, so the reasoning
lives in one place rather than drifting between two.
