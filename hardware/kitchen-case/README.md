# Kitchen Atom Echo Enclosure

Parametric OpenSCAD wall-mount case for the kitchen intercom: classic M5Stack
Atom Echo + 1× MAX98357A + 2× 4 cm drivers (side by side, wired in series off
the one amp). Design spec:
[../../docs/superpowers/specs/2026-06-01-kitchen-case-design.md](../../docs/superpowers/specs/2026-06-01-kitchen-case-design.md).
Forked from `hardware/terrace-case` (two speakers/two amps) — kitchen keeps the
two-driver baffle but drives both from a single amp.

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
Parts: `front`, `rear`, `button`, `coupon` (fit test), `all` (assembled preview). Select with the normal variable flag `-D part="..."` (a `$`-prefixed variable would be ignored by `-D`).

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

The two drivers sit side by side, centered as a pair; the module sits centered
below them with the single amp board to its right. Outer width is derived
(`outer_w()`) from whichever is wider — the driver pair or the module+amp row.

## Print before you commit to the full case

Print the **coupon** first (~10 min) and dry-fit the module, a driver, and the
button cap:
```bash
"$OPENSCAD" -D 'part="coupon"' -o stl/coupon.stl kitchen-case.scad
```
- Cradle too tight/loose → adjust `clr` / `mod_clr`.
- Button binds or has no travel → adjust `btn_well_d` / `btn_travel`.
- Driver doesn't seat → adjust `spk_od` / `spk_seat_depth`.
- Drivers are friction/glue-mounted (`spk_screw_n = 0`); the locating ring + gasket hold them. To screw-mount instead, set `spk_screw_n > 0` and enlarge the shell until `test.sh` passes (the asserts guard against the bolt-circle bosses colliding with the corner lid screws in this tight envelope).

## Print settings

- Front shell: grille face **down** (no supports needed). 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- Rear plate: flat.
- Button cap: face down.
- Material: your choice (indoor location).

## BOM

- 1× M5Stack Atom Echo (classic)
- 1× MAX98357A breakout
- 2× 4 cm full-range drivers (~40 mm locating dia, ~20 mm deep)
- 4× M3 screws (from the back, through the flat rear plate, self-tap into the corner front-shell bosses)
- 4× M2 self-tap screws for the amp board (into the standoffs)
- 2× foam/EVA gasket rings for the drivers (~34–39 mm, seat in the baffle grooves)
- a dab of glue / foam tape to retain each driver in its locating ring (drivers are friction/glue-mounted, not screwed)
- 2× wall screws for the keyhole slots

## Speaker wiring (two drivers, one amp)

Wire the two drivers **in series** across the single amp's `+ / −` output:
`amp +` → driver A `+`, driver A `−` → driver B `+`, driver B `−` → `amp −`.
Series **doubles** the load impedance (e.g. 2× 4 Ω → 8 Ω), which is always safe
for the MAX98357A and splits the power between the two drivers. (Parallel would
halve the impedance — fine for 8 Ω drivers, but 2× 4 Ω → 2 Ω risks overheating
/ clipping the amp, so series is the default here.)

## Assembly

1. Drop a foam/EVA gasket ring into the baffle groove around each driver, then seat the drivers into the front-shell locating rings (compressing the gasket); retain each with a dab of glue or foam tape — the rings + gaskets hold them, there are no driver screws. Wire the two drivers in series (see above) and solder the series pair to the amp `+/−`.
2. Drop the Atom Echo into the cradle top-face-forward (its button + mic end up behind the well and the perforation in the front wall); route header wires through the side window to the amp.
3. Seat the amp board on its standoffs; fasten with 4× M2 into the standoff pilots.
4. Drop the button cap into its well from the front (snaps captive).
5. Hang the rear plate on two wall screws via the keyholes.
6. Mate front to rear; drive 4× M3 from the back.

Wiring (amp taps + internal-speaker handling) is covered by the louder-amp
design: [../../docs/superpowers/specs/2026-06-01-kitchen-atom-echo-louder-amp-design.md](../../docs/superpowers/specs/2026-06-01-kitchen-atom-echo-louder-amp-design.md).
