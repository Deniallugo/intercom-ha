# Terrace VoiceS3R Enclosure

Parametric OpenSCAD wall-mount case for the terrace intercom combo: M5Stack
VoiceS3R + 2× MAX98357A + 2× 2" drivers.

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
Parts: `front`, `rear`, `button`, `spacer`, `coupon` (fit test), `all` (assembled preview).

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
- 4× M3 self-tap screws (rear plate → front bosses)
- 8× M2 self-tap screws for the drivers
- 8× M2 self-tap screws for the amp boards
- 2× foam/EVA gasket rings for the drivers (~45–52 mm)
- 2× wall screws for the keyholes

## Assembly

1. Gasket ring into each baffle groove, drivers in, 4× M2 each. Solder leads to the amps.
2. VoiceS3R into the cradle, button forward (mic behind the holes under the button). Route
   wires through the side window to the amps.
3. Amp boards on their standoffs, 4× M2 each.
4. Button cap into its well from the front, **nub toward the top** (see below).
5. Hang the rear plate on two wall screws via the keyholes.
6. Mate front to rear; drive 4× M3 from the back.

## Optional depth spacer

If it sounds boxy with the rear closed, the drivers lack air (~8 mm behind each cone).
Print `spacer`: a ring between front shell and rear plate that adds `spacer_t` (20 mm)
of sealed volume. Print frame face down. Foam tape on **both** seams (it's a sealed box);
use 4× M3×35 (or ×30) self-tap screws instead of the short ones.

## Button: top-switch nub (orient + fix)

The module's switch is above its centre, so the cap's nub is offset by
`btn_above_center` (tune it by reprinting only the cap). The well is round, so the cap
can spin: fit it nub-up and fix it with a dab of glue.
