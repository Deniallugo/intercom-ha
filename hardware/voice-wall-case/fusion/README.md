# Voice S3 wall unit: Fusion model

This is the wall unit as a Fusion script. It builds every printed part, and also **every electronic part as its own component**, so you can move any part in Fusion and have the case follow it.

**This is the source of truth.** Python is the parametric engine, and Fusion gets standard sketches, extrudes, lofts and combines, the same approach as [`../../voice-case/fusion`](../../voice-case/fusion). The OpenSCAD in `../` is the old two-box design and is no longer compared against.

```
fusion/
  test.sh                    design checks, every part built offline, sync round-trip
  tests/scad_emit.py         adsk stand-in (emits OpenSCAD text; nothing renders it)
  tests/test_build.py        every printed part through the stand-in: one body each, under
                             every sketch-plane orientation Fusion could hand over
  tests/test_sync.py         drag -> sync -> rebuild, against an emulated document
  VoiceWallCase/
    VoiceWallCase.py         what Fusion runs
    vwc/placement.py         WHERE the movable parts sit; `sync` rewrites this file
    vwc/params.py            every other number, every derived dimension, the frames
    vwc/elec.py              every electronic part, as data (dummies, checks and sync all read it)
    vwc/checks.py            the design's constraints, including the electronics
    vwc/case.py              tray, panel, switch bridge, coupons
    vwc/button.py            the mic clamp
    vwc/electronics.py       builds elec.py as Fusion components
    vwc/assembly.py          what goes where; the browser tree
    vwc/sync.py              Fusion moves -> placement.py
    vwc/build.py  vwc/xf.py  the CSG vocabulary on sketches/features; rigid transforms
```

## Running it

1. In Fusion, open **Utilities → Add-Ins → Scripts and Add-Ins** (Shift+S). Click **+** beside *My Scripts* and pick `hardware/voice-wall-case/fusion/VoiceWallCase`.
2. Select **VoiceWallCase** and click **Run**. It asks what to build:

| Answer | Builds |
|---|---|
| `all` (default) | The whole unit on the wall: tray, panel, bridge, clamp, and every electronic part |
| `electronics` | Only the electronics, in their positions |
| `small` | The bridge and the clamp on one bed, in print orientation |
| `tray` `panel` `bridge` `clamp` | One printed part, in its print orientation |
| `coupon-button` `coupon-top` | A test slice: the panel's button area, the tray's top |
| `sync` | Writes the parts you moved back to `placement.py` (see below) |

Each build goes into a **new document**. The flags at the top of `VoiceWallCase.py` are:

| Flag | Effect |
|---|---|
| `PART`, `ASK` | Pin a part and skip the prompt |
| `GHOST` | Opacity of the tray and panel in the assembly, so the electronics show through |
| `EXPORT_STL` | One STL per **printed** component into `VoiceWallCase/stl/` |
| `USER_PARAMETERS` | Writes the `ref_*` reference parameters |

At the end of a run the script lists anything that went wrong in a build: a printed part that came out as more than one body, a cut that missed, or a part Fusion would not keep in place.

## Frames

One thing will look backwards until you know it. **Box-local +x is the viewer's LEFT.** Box-local is a real, right-handed frame, with y up and z running into the box from the front face, and in such a frame +x has to be on your left as you face the unit. So in `placement.py`:

- the voice column (devkit, DAC, MP1584) at x ≈ +31 is on the left;
- the amp at x = −20 is on the right.

The amp's own numbers (hole positions, connector x, the pots) are kept exactly as they were photographed, where "+ = the VOL end" was read as "right". `params.amp_xf()` maps them into the box with a mirror. That is fine because a mirror is only ever applied to numbers (dummies and standoff positions), never to a Fusion occurrence. As a result VOLUME comes out on the viewer's left, matching the real board turned knobs-up with its parts facing you.

## Moving parts in place

1. Run `all`.
2. Drag a part inside the **electronics** group: the devkit, DAC, MP1584, mic, tactile switch (which carries the whole button) or the amp board. Inspect › Interference shows what it hits.
3. Run `sync` on that document. The move is written to `vwc/placement.py` and the design checks run on the result.
4. Run `all` again. Pockets, standoffs, posts and holes follow the part.

The voice boards move only across the plate (x and y); the mic moves across the bottom (x and depth z). The amp moves across (`amp_x`) and forward (`amp_lift`, which lengthens the standoffs and deepens the box). Knobs, plugs and wiring follow the part they belong to; a rotation or a move along an axis a part doesn't own is reported, not synced.

## Checking it without opening Fusion

```
./test.sh
```

It runs three things, all in pure Python, with no Fusion and no OpenSCAD:

1. **Design checks.** Everything the case depends on:
   - fits: devkit across, amp, faceplate;
   - the amp: knob grip above the top, room for the pot nuts, plug room below the board;
   - knob names: don't overlap, fit the face, clear the mic port;
   - flexure: arm width, disc-to-arm joint, stress, preload;
   - fixings: wall screws vs standoffs, base screws vs the cable notch;
   - board screws: none under a part on the amp;
   - every electronic part against every other one, the cavity, and every printed obstacle.
2. **Build.** Every printed part through the adsk stand-in. Each must close every sketch into one profile and come out as **one body**, under four different sketch-plane orientations.
3. **Sync.** Drag, sync and rewrite against an emulated document, including a drag of the mirrored amp board.

## What has not been checked

- **Not run in Fusion yet.** Two features are new to this port:
  - **The knob names** use sketch text on a construction plane turned half a turn about Y (or about X, whichever reads correctly). If a name comes out mirrored or missing, that is the place to look (`build.text_tools`).
  - **The button slots** are arc sectors drawn with the same arc-closing rules as the rest of the port.
- **The flexure stiffness is an estimate** from straight fixed-guided beams. Curved arms are softer. Print `coupon-button` before the panel.
- **Nothing was rendered.** The OpenSCAD comparison and pictures were dropped along with the two-box design.
