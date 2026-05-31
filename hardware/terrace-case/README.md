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
| `mic_x()`, `mic_y()` | mic port position — set after measuring the module |
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

## Print settings

- Front shell: grille face **down** (no supports needed). 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- Rear plate: flat.
- Button cap: face down.
- Material: your choice; location is sheltered.

## BOM

- 1× M5Stack ATOM Echo S3R (VoiceS3R)
- 2× MAX98357A breakout
- 2× 2" full-range driver (~53 mm OD)
- 4× M3 screws (self-tap into front bosses)
- Thin EVA/foam ring for the mic boss gasket
- 2× wall screws for the keyhole slots

## Assembly

1. Press the EVA ring onto the mic boss.
2. Seat the two drivers into the front-shell rings; secure with M2 screws or printed tabs; solder driver leads to the amp `+/−`.
3. Drop the VoiceS3R into the cradle button-forward; route header wires through the side window to the amps.
4. Seat the amp boards on their standoffs.
5. Drop the button cap into its well from the front (snaps captive).
6. Hang the rear plate on two wall screws via the keyholes.
7. Mate front to rear; drive 4× M3 from the back.

Then run the full suite + build and confirm STLs are produced:
```bash
hardware/terrace-case/test.sh && hardware/terrace-case/build.sh && ls -l hardware/terrace-case/stl
```
