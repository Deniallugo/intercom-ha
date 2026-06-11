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

## Optional depth spacer

If the assembled case sounds constrained/boxy with the rear closed, the drivers
are starved for air (~8 mm behind each cone). The **spacer** part is a drop-in
picture-frame ring that inserts at the front-shell ↔ rear-plate parting line and
adds `spacer_t` (default **20 mm**) of sealed air volume behind the drivers — no
reprint of the front shell or rear plate.

Render/print it like any other part:

    openscad -o stl/spacer.stl -D 'part="spacer"' terrace-case.scad

Print flat (frame face down), no supports, same settings as the shell (0.2 mm
layers, ≥4 perimeters, 20–30 % infill).

**Assembly (front shell → spacer → rear plate):**

1. Seat the spacer on the front shell — its spigot lip nests into the shell's
   rear opening; the 4 corner pads land on the existing front bosses.
2. Foam/EVA tape on **both** seams (front↔spacer and spacer↔rear). Plastic faces
   are not airtight and this is a sealed box — skipping this re-introduces leaks.
3. Fit the rear plate and fasten with **4× M3×35 self-tapping screws** (replacing
   the short ones) — they span the rear plate + spacer and bite into the front
   bosses. M3×30 also works (~7 mm engagement).

The USB-C exit (front shell bottom wall) and keyhole wall-mount (rear plate) are
unchanged; the case simply stands `spacer_t` further off the wall. Tune
`spacer_t` in `modules/params.scad` and reprint just the spacer to taste.

## Button: top-switch nub (orient + fix)

The module's tactile switch is toward the **top** of the module, not its center,
so the cap's contact nub is offset up by `btn_above_center` (`modules/params.scad`)
while the round face stays centered. The nub stays fully under the skirt (assert
guards this); tune `btn_above_center` and reprint **only the button cap** to dial
it in — no front-shell reprint.

Because the well is a plain round bore, the round cap is free to **spin**, which
would swing the offset nub off the switch. So at assembly, orient the cap **nub
toward the top** and fix that rotation — a dab of glue/CA on the skirt or a snug
press-fit. (A spin-proof captive version would need the well keyed, i.e. a
front-shell reprint.)
