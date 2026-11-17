# Kitchen Atom Echo Enclosure

Parametric OpenSCAD wall-mount case for the kitchen intercom: classic M5Stack
Atom Echo + 1× MAX98357A + 2× 4 cm drivers wired in series. Derived from
[../terrace-case](../terrace-case), with one amp instead of two.

## Render

```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
./build.sh        # front.stl, rear.stl, button.stl into stl/
./test.sh         # asserts + clean-render check for every part
```

Render one part manually:
```bash
"$OPENSCAD" -D 'part="front"' -o stl/front.stl kitchen-case.scad
```
Parts: `front`, `rear`, `button`, `spacer`, `coupon` (fit test), `all` (assembled preview).

## Parameters

All in [modules/params.scad](modules/params.scad). Common edits:

| Param | Meaning |
|---|---|
| `spk_od`, `spk_cut` | driver locating-ring dia / grille field dia |
| `spk_gap` | gap between the two drivers (lower = tighter) |
| `mod_w`, `mod_d` | Atom Echo footprint / depth |
| `amp_gap` | space between the module cradle and the amp board |
| `usb_conn_w`, `usb_conn_t` | USB-C plug body cross-section (10×10 mm) — drives the bottom hole size |
| `usb_clr` | clearance around the connector in every opening |
| `usb_z` | USB-C port depth from the front face — centers the bounded bottom hole |
| `mic_below_btn` | mic perforation offset below the button — tune to the module mic |
| `clr` | global fit clearance (raise if parts are tight) |
| `keyhole_spacing` | wall-screw spacing |

Drivers side by side on top; module below with the amp to its right. Outer width
(`outer_w()`) follows the wider of the two rows.

## Print before you commit to the full case

Print the **coupon** first (~10 min) and dry-fit the module, a driver, and the
button cap:
```bash
"$OPENSCAD" -D 'part="coupon"' -o stl/coupon.stl kitchen-case.scad
```
- Cradle too tight/loose → adjust `clr` / `mod_clr`.
- Button binds or has no travel → adjust `btn_well_d` / `btn_travel`.
- Driver doesn't seat → adjust `spk_od` / `spk_seat_depth`.
- Drivers are glued, not screwed (`spk_screw_n = 0`). To screw them, set `spk_screw_n > 0`
  and grow the shell until `test.sh` passes.

## Print settings

- Front shell: grille face **down** (no supports needed). 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- Rear plate: flat.
- Button cap: face down.
- Material: your choice (indoor location).

## BOM

- 1× M5Stack Atom Echo (classic)
- 1× MAX98357A breakout
- 2× 4 cm full-range drivers (~40 mm locating dia, ~20 mm deep)
- 4× M3 self-tap screws (rear plate → front bosses)
- 4× M2 self-tap screws (amp board)
- 2× foam/EVA gasket rings for the drivers (~34–39 mm)
- glue or foam tape for the drivers
- 2× wall screws for the keyholes

## Speaker wiring (two drivers, one amp)

**In series:** `amp +` → A `+`, A `−` → B `+`, B `−` → `amp −`. 2× 4 Ω in series is
8 Ω; in parallel it would be 2 Ω, too low for the MAX98357A.

## Assembly

1. Gasket ring into each baffle groove, drivers into the locating rings, glue. Wire them
   in series to the amp `+/−`.
2. Atom Echo into the cradle, face forward (button and mic behind the well and mic holes).
   Route wires through the side window to the amp.
3. Amp board on its standoffs, 4× M2.
4. Button cap into its well from the front, **nub toward the top** (see below).
5. Hang the rear plate on two wall screws via the keyholes.
6. Mate front to rear; drive 4× M3 from the back.

Amp wiring: [docs/DEVICES.md](../../docs/DEVICES.md) → *Kitchen*.

## Optional depth spacer

If the wiring behind the Atom Echo doesn't fit, print `spacer`: a ring between front
shell and rear plate that adds `spacer_t` (10 mm) of depth. Print frame face down.
Foam tape on both seams; use 4× M3×20 (or ×25) self-tap screws instead of the short ones.

## Button: top-switch nub (orient + fix)

The Atom Echo's switch is above the module's centre, so the cap's nub is offset by
`btn_above_center` (tune it by reprinting only the cap). The well is round, so the cap
can spin: fit it nub-up and fix it with a dab of glue.
