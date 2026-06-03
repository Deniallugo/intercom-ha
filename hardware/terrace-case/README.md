# Terrace VoiceS3R Enclosure

Parametric OpenSCAD wall-mount case for the terrace intercom combo: M5Stack
VoiceS3R + 2× MAX98357A + 2× 2" drivers. Design spec:
[../../docs/superpowers/specs/2026-05-31-terrace-case-design.md](../../docs/superpowers/specs/2026-05-31-terrace-case-design.md).

## Render

```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
./build.sh        # front.stl, rear.stl, button.stl into stl/
./test.sh         # asserts + clean-render check for every part
```

Render one part manually:
```bash
"$OPENSCAD" -D 'part="front"' -o stl/front.stl terrace-case.scad
```
Parts: `front`, `rear`, `button`, `coupon` (fit test), `all` (assembled preview). Select with the normal variable flag `-D part="..."` (a `$`-prefixed variable would be ignored by `-D`).

## Parameters

All in [modules/params.scad](modules/params.scad). Common edits:

| Param | Meaning |
|---|---|
| `spk_od`, `spk_cut` | driver outer dia / grille field dia |
| `spk_gap` | gap between the two drivers (lower = tighter) |
| `mod_w`, `mod_d` | VoiceS3R footprint / depth |
| `mic_below_btn` | mic perforation offset below the button — tune to the module mic |
| `clr` | global fit clearance (raise if parts are tight) |
| `keyhole_spacing` | wall-screw spacing |

## Print before you commit to the full case

Print the **coupon** first (~10 min) and dry-fit the module, a driver, and the
button cap:
```bash
"$OPENSCAD" -D 'part="coupon"' -o stl/coupon.stl terrace-case.scad
```
- Cradle too tight/loose → adjust `clr` / `mod_clr`.
- Button binds or has no travel → adjust `btn_well_d` / `btn_travel`.
- Driver doesn't seat → adjust `spk_od` / `spk_seat_depth`.
- Driver screw holes don't line up → adjust `spk_bolt_circle` / `spk_screw_n` / `spk_screw_a0` to match your driver's flange.

## Print settings

- Front shell: grille face **down** (no supports needed). 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- Rear plate: flat.
- Button cap: face down.
- Material: your choice; location is sheltered.

## BOM

- 1× M5Stack ATOM Echo S3R (VoiceS3R)
- 2× MAX98357A breakout
- 2× 2" full-range driver (~53 mm OD)
- 4× M3 screws (from the back, through the flat rear plate, self-tap into the corner front-shell bosses)
- 8× M2 self-tap screws for the drivers (4 per driver, into the bolt-circle bosses)
- 8× M2 self-tap screws for the amp boards (4 per board, into the standoffs)
- 2× foam/EVA gasket rings for the drivers (~45–52 mm, seat in the baffle groove)
- 2× wall screws for the keyhole slots

## Assembly

1. Drop a foam/EVA gasket ring into the baffle groove around each driver, then seat the drivers into the front-shell rings; fasten each with 4× M2 through the flange into the bolt-circle bosses (compressing the gasket); solder driver leads to the amp `+/−`.
2. Drop the VoiceS3R into the cradle button-forward (its mic ends up behind the perforation under the button); route header wires through the side window to the amps.
3. Seat the amp boards on their standoffs; fasten each with 4× M2 into the standoff pilots.
4. Drop the button cap into its well from the front (snaps captive).
5. Hang the rear plate on two wall screws via the keyholes.
6. Mate front to rear; drive 4× M3 from the back.

Then run the full suite + build and confirm STLs are produced:
```bash
hardware/terrace-case/test.sh && hardware/terrace-case/build.sh && ls -l hardware/terrace-case/stl
```
