# Speaker case — design review against the 53 mm driver constraint

Date: 2026-07-29
Status: **implemented** — Option 2 (one box, vertical pair) built in
`hardware/speaker-case/`. Supersedes the acoustic half of
`2026-06-13-speaker-case-hardware-design.md`.

**Trigger:** the build must reuse the **53 mm AIYIMA 2″ driver already in hand**, not the
Dayton PS95-8 3.5″ the current `hardware/speaker-case/` package was rebuilt around.
That single substitution invalidates most of the current enclosure's acoustic reasoning,
so this doc re-derives the physics first and then lists what is actually wrong in the
package as committed.

---

## 1. Verdict up front

The committed enclosure (158 × 159 × 118 mm, ~1.6 L sealed chamber, side-mounted passive
radiator, 15 V PD → TPA3116) is **the wrong box for this driver in every dimension**:
about **3× too large**, carries a **passive radiator that cannot work**, and is driven by
an amp with roughly **8× more power than the driver can survive**. Meanwhile the things
that would actually make it sound good — panel resonance, internal modes, baffle
diffraction, an excursion backstop, mic acoustics — are either unaddressed or actively
wrong.

The good news: with the correct box the result is a genuinely *decent-sounding*
speaker — clean, uncoloured, wide-dispersion, articulate from ~160 Hz to 15 kHz at up to
~88 dB. It will not have bass, and no enclosure can give it bass. Section 2 proves why.

---

## 2. The driver sets every limit (do this arithmetic before choosing a box)

Measured values already in the repo (`2026-06-13-speaker-case-design.md`):
Fs ≈ 145 Hz, Re ≈ 3.4 Ω, Qms ≈ 4.4, Qes ≈ 0.71, **Qts ≈ 0.61**, sensitivity ≈ 83–84 dB,
frame OD 53 mm, cutout 46 mm, 4 screws on a **43 mm square**, seated depth 28 mm.

**Never measured, and it is the parameter that picks the box: Vas.** Estimated from
Sd ≈ 14.5 cm² (≈ 43 mm effective piston) and Mms ≈ 1.5–3 g:

> Vas = ρ₀c²·Sd²·Cms, with Cms = 1/((2πFs)²·Mms) → **Vas ≈ 0.12–0.24 L, call it 0.2 L.**

### 2.1 Box volume is nearly irrelevant — the current 1.6 L is wasted

Sealed: Fc = Fs·√(1 + Vas/Vb), Qtc = Qts·√(1 + Vas/Vb).

| Vb (net) | Fc | Qtc | F3 |
|---|---|---|---|
| 0.3 L | 187 Hz | 0.78 | ~180 Hz |
| **0.4 L** | 178 Hz | 0.74 | ~175 Hz |
| **0.5 L** | 172 Hz | 0.71 | ~172 Hz |
| 0.7 L | 164 Hz | 0.68 | ~170 Hz |
| 1.0 L | 159 Hz | 0.66 | ~167 Hz |
| **1.6 L (as built)** | 154 Hz | 0.64 | ~164 Hz |
| ∞ | 145 Hz | 0.61 | — |

Tripling the box from 0.5 L to 1.6 L buys **18 Hz (0.16 octave) and ΔQtc 0.07.** That is
inaudible. The knee of the curve is **0.4–0.5 L**; everything past it is plastic, print
time, wall load, and — per §4 — *worse* sound.

### 2.2 The passive radiator cannot work and must be deleted

A PR tuned to 75 Hz below a driver with Fs = 145 Hz fails on four counts:

1. A PR only radiates where the driver excites it, and the driver is already 15–20 dB
   down and mechanically unloaded at 75 Hz. There is nothing to radiate.
2. Tuning a Sd ≥ 35 cm² diaphragm to 75 Hz in 0.5 L needs an absurd mass, and the
   resulting Qms would dominate the alignment.
3. The PR's own suspension adds compliance to a box whose total compliance is only
   ~0.2 L equivalent — a floppy 3–4″ PR would swamp Vb and make Fc/Qtc unpredictable.
4. Below the PR's tuning the box unloads and cone excursion runs away — the failure mode
   the design doc itself flags as "mandatory to prevent", while shipping no hardware
   protection (§3.3).

The old doc's own conclusion was right ("Fs = 145 Hz — can't manufacture sub-bass"); the
rebuild imported a PR from an *8 Ω / Fs 87 Hz / Vas 1.1 L* driver's design and never
re-derived it. **Delete the PR entirely** (`pr_*` params, `pr_seat`, `pr_cut_hole`,
`pr_gasket_groove`, `pr_screw_bosses`, and their asserts).

### 2.3 Max SPL — the number no doc states, and it caps the whole design

Piston in half-space, far field: p_rms = ρ₀·ω²·Sd·x_rms / (2πr).
With Sd = 14.5 cm², r = 1 m, and Xmax ≈ 1 mm (typical 2″; **measure it**):

| Band | Limit | Max SPL @ 1 m |
|---|---|---|
| 150 Hz | excursion (Xmax 1 mm) | **≈ 79 dB** (≈ 73 dB if Xmax is 0.5 mm) |
| 300 Hz | excursion | ≈ 91 dB |
| ≥ 500 Hz | thermal (5 W real, 83 dB/W) | **≈ 90 dB** |

Excursion demand falls as 1/f², so above ~300 Hz the driver is thermally limited and
comfortable; at 150 Hz it is hard-stopped near 79 dB. Wall/corner boundary gain adds
+3 to +9 dB in the 100–300 Hz region — which is *more low-end benefit than any box
choice in §2.1*. Mount it flush to the wall and pick the placement deliberately.

**Consequence:** the driver can use about **3–5 W**. Every watt beyond that is risk, not
loudness.

---

## 3. Holes — electrical

### 3.1 The amp is ~8× oversized and will kill the driver

TPA3116 on a 15 V rail into **4 Ω** delivers ≈ 40 W. The driver wants 3–5 W. One
full-scale sample — a TTS clip start transient, an ESPHome buffer underrun, a Music
Assistant volume slip — puts 40 W into a 12 W voice coil. The BOM chose TPA3116 to fix
"MAX98357A is too weak" — but that critique was measured against an **8 Ω** PS95-8
(≈ 2 W). Into **4 Ω**, MAX98357A delivers **3.2 W ≈ 88 dB**, which is exactly matched to
§2.3 and, crucially, **clips before the driver dies**. The amp's own ceiling becomes free
protection.

Recommended chain, which also **collapses the power tree from five boards to two**:

```
USB-C 5 V (plain charger)  ──►  ESP32-S3  ──I²S──►  PCM5102A  ──analog──►  small 5 V amp  ──►  330 µF  ──► 53 mm driver
```

- Drop **CH224K PD trigger** and **MP1584 buck** — no 15 V rail, no 15 V-PD-capable
  charger dependency, no star-ground hum risk, ~$5 and 3 boards saved.
- Keep **PCM5102A**: `devices/speaker-s3.yaml` is *already written for it* (GPIO5/6/7,
  `dac_type: external`, SCK→GND), so the firmware needs no change, and it keeps the
  3.5 mm line-out option open.
- Amp: **PAM8403/PAM8406 or TPA3110 at 5 V** (~2.5–3 W into 4 Ω) fed from the PCM5102
  L-out. If you want the MAX98357A instead, it replaces *both* DAC and amp — but then
  `speaker-s3.yaml` becomes mono and you lose the line-out.
- If you insist on headroom: TPA3116 on **12 V**, lowest gain jumper, plus §3.3's cap and
  a firmware volume ceiling. ~93 dB mid. Not recommended for a 2″ driver.

### 3.2 The 4 Ω / 8 Ω mismatch is never reconciled anywhere

Every power figure in the hardware spec assumes 8 Ω (PS95-8). The driver in hand is
**4 Ω** (Re 3.4 Ω). Amp output doubles, thermal margin halves. Any amp choice must be
re-checked at 4 Ω, and the amp must be 4 Ω-stable.

### 3.3 "Mandatory HPF" is specified and then not implemented — biggest real hole

Both docs state that the high-pass at Fb is **mandatory** because TTS and wake-word
bypass Music Assistant's DSP, and then provide **zero hardware backstop**. Fix it with
one part:

> **Series 330 µF bipolar/NP electrolytic in one driver leg.**
> f = 1/(2πRC) = 1/(2π·4·330 µF) ≈ **120 Hz.**

This is unusually well-matched to this driver: at Fs the impedance peaks near
Re·(1 + Qms/Qes) ≈ 24 Ω, so the cap is nearly transparent at 145 Hz, while below Fs the
impedance falls back toward 3.4 Ω and the roll-off bites hard — exactly where you want
it. Two further benefits worth as much as the protection:

- It removes any amp DC offset from the coil.
- It cuts **intermodulation distortion**, which is the dominant audible flaw of a small
  full-range driver: unchecked LF excursion amplitude- and Doppler-modulates the
  midrange the same cone is reproducing. Keeping sub-120 Hz energy off the cone is the
  single cheapest audible improvement in this whole document.

Note a correction to the docs' reasoning: in a *sealed* box excursion asymptotes to a
constant below Fc rather than running away (that runaway is the vented/PR failure mode).
It still commonly exceeds Xmax on full-scale LF content, so the cap stays justified —
but the "excursion runs away" wording only applies to the PR design being deleted.

### 3.4 `usb_z` is a magic number that should be derived

`usb_z = wall + 8` places the USB-C slot centre 12 mm behind the front face, but the
CH224K sits on 3 mm standoffs, so its receptacle centre is really at
`wall + board_standoff_h + pcb_t + conn_h/2` ≈ 9.4 mm. The 13 mm slot is tall enough to
hide the 2.6 mm error, so nothing fails — but the value should be a function of the
standoff stack, not a constant. Moot if the CH224K goes away per §3.1.

---

## 4. Holes — enclosure physics (where the big box actively hurts)

### 4.1 Panel resonance: the 150 mm flat wall rings at ~530 Hz

Clamped-plate fundamental f ≈ (36/2π)·(t/a²)·√(E/(12ρ(1−ν²))). For 4 mm PLA
(E ≈ 3.5 GPa, ρ = 1240, ν = 0.35) the bracket collapses to **f ≈ 11.9/a² Hz** (a in m):

| Panel span | f₁₁ |
|---|---|
| 150 mm (as built) | **≈ 530 Hz** |
| 110 mm | ≈ 980 Hz |
| **90 mm (proposed)** | **≈ 1.5 kHz** |

530 Hz is the middle of the vocal fundamental range, on a panel with PLA's very low
internal damping. It will radiate and colour every voice announcement. Shrinking the box
per §2.1 raises it by ~9 dB-equivalent of stiffness for free — **the small box is
acoustically better, not merely smaller.**

### 4.2 Internal standing waves land in the vocal band

Half-wave modes at c/2L:

| Internal dimension | Mode |
|---|---|
| 150 mm width (as built) | 1143 Hz |
| 110 mm depth (as built) | 1560 Hz |
| 103 mm height (as built) | 1665 Hz |
| 90 mm (proposed) | 1906 Hz |
| 75 mm (proposed) | 2287 Hz |

The current box puts **three strong modes in 1.1–1.7 kHz** — the presence region — and
they re-radiate straight back through a thin 2″ cone. Fixes, all of which printing makes
free: a smaller box, **non-parallel / curved walls**, and polyfill (already specified).

### 4.3 The "rounded vertical edges (baffle diffraction)" comment is wishful

`radius = 8` on a 158 mm baffle does nothing for diffraction — the baffle step sits near
λ ≈ W (≈ 2.2 kHz here) and you need r ≳ 15–20 mm to smear it. A *small* baffle with a
*large* front-edge transition gets this nearly free, and printing makes the transition
cost nothing. Recommend a **12–15 mm 45° chamfer plus 3 mm fillets** on the front edge
(see §6 for why a chamfer rather than a true fillet).

### 4.4 Do **not** add a waveguide

Tempting with printing, but wrong here. A 43 mm piston has ka = 1 at ≈ 2.5 kHz and stays
wide to ~8 kHz — excellent dispersion is this driver's main *advantage*. A waveguide
would trade that away for on-axis sensitivity the driver doesn't need. Large roundover,
no horn.

### 4.5 The grille is worse than no grille — and doesn't attach

Two separate problems in `modules/grille.scad`:

- **Acoustic:** `grille()` puts 142 × 3 mm holes on a 6 mm ring pitch over the opening =
  **≈ 22 % open area**, 1.6 mm thick, sitting a few mm off the cone. For a driver whose
  useful output runs to 15 kHz that is a measurable obstruction plus a field of little
  resonators. Want ≥ 50–60 % open and as thin as possible.
- **Mechanical bug:** the skirt bores to `spk_od + 2*seat_wall + 2*clr` to "snap over the
  driver seat ring" — but `speaker_seat()` is built on the **inner** baffle face at
  `z = wall`, growing into the box. There is **no external boss for the skirt to grip**;
  as committed the grille is a loose disc held on by nothing.

Recommend: drop the printed grille, or print a thin ring that captures fine metal mesh.

### 4.6 The 6 mm divider wire pass is the leak that ruins Qtc

A 0.5 L sealed box has very little compliance; a few mm² of leak behaves as an untuned
vent and shifts Qtc unpredictably. "Seal with silicone after wiring" is a hand-fit
process on a joint you cannot inspect. Better: **no hole at all** — two M3 brass bolts as
feedthrough terminals with an O-ring under each washer, or a proper spring terminal
through a wall. This becomes free if you adopt §5.4 (split pods).

Related, and specific to printing: with normal infill, air migrates *through the infill
matrix* from the chamber into the bay and out the USB/PTT breaches. The chamber must be
bounded by solid-walled regions (≥ 4–5 perimeters and "ensure vertical shell thickness"),
which is exactly what a monolithic body with an internal divider makes hard to guarantee.

### 4.7 Mic acoustics: a ~5.7 kHz Helmholtz resonator right where speech lives

The committed 7-hole cluster (1 centre + 6 on a 2.6 mm ring, 1.5 mm dia) through the
4 mm wall *plus* the 1.6 mm pocket floor is a Helmholtz resonator:

> f = (c/2π)·√(A/(V·L)); A = 7 × 1.77 = 12.4 mm², L = 5.6 mm, front cavity V ≈ 200 mm³
> → **f ≈ 5.7 kHz**, with the matching dip below it.

That colours every recording and degrades wake-word/STT. Standard MEMS practice is the
opposite of what's here: **one hole (~1.5–2 mm), the shortest possible path, and
essentially zero front volume** — press the mic's port against a die-cut silicone or foam
gasket sealing port-to-hole. Shrinking V to ~10 mm³ with a single 2 mm hole moves the
resonance to **≈ 15 kHz**, out of band.

The uncommitted `body.scad` change (piercing the pocket floor as well as the wall) is
*correct and necessary* — without it the bottom-ported ICS-43434 is sealed off entirely.
Keep it, but the 7-hole geometry it fixes should be replaced outright.

### 4.8 The mic is bolted to the panel the driver is shaking

Rigidly mounting the mic in a friction pocket on the same baffle as the driver, 50 mm
away, maximises structure-borne coupling. Tolerable for PTT (you're not playing music
while talking); bad for wake-word during playback, where there is no AEC. Mount the mic
on a compliant grommet/foam island, and as far from the driver as the box allows — ideally
on a different face, and ideally on the electronics pod rather than the acoustic one.

### 4.9 Wall mount: two keyholes in a 4 mm printed lid will creep

Hanging a heavy box off two screws bearing on 4 mm of printed plastic is a long-term
creep failure, PLA especially. And a flat 158 × 159 mm lid is itself a drum (§4.1) while
also being the chamber's pressure boundary. Recommend a **separate wall bracket** (French
cleat or plate) that the box hooks over, with metal washers or inserts at the load
points — and a much smaller, stiffer lid.

---

## 5. What to build instead

> **Superseded in part by §7a/§7b:** these three options assume ONE driver. Both units
> are in hand, so the build is a vertical pair in ~0.70 L with a tuned port (§7a
> Option 2). Option C below is explicitly withdrawn in §7b. The electronics (§3.1) and
> the series cap (§3.3) carry over unchanged.

Three options. All share the §3.1 electronics and the §3.3 series cap.

### Option A — recommended: small sealed pod, ~0.5 L

- Net Vb **0.45–0.5 L** → Fc ≈ 172 Hz, Qtc ≈ 0.71 (maximally flat, no hump).
- Internal ≈ **95 × 75 × 70 mm**; external ≈ **105 × 85 × 80 mm** with a chamfered face.
- Front-edge 45° chamfer 12 mm + 3 mm fillets (§4.3). Baffle **6–8 mm**, walls 4 mm.
- Cone cutout 46 mm with the inner edge chamfered ~45° so the cone breathes.
- Driver screws: **4 on a 43 mm square** — i.e. a 60.8 mm bolt circle at 45° (§7.1).
- Honest result: flat ≈ 170 Hz – 15 kHz, ~88 dB max, low colouration, wide dispersion.
  Exactly the right character for an intercom, and pleasant for music minus bass.

### Option B — aperiodic / resistive vent, ~0.4 L

Same shell, plus a **20 mm × 20 mm duct with a foam plug** retained by a printed ring.
Drops Qtc to ≈ 0.6, softening the 170–200 Hz hump; **no unloading below tuning and no
chuffing**, unlike a tuned port. Its real advantage here: it is **tolerant of Vas being
unmeasured** — you tune by swapping plug density rather than by trusting a number nobody
measured. Cheap insurance; a good default if you don't want to measure Vas.

### Option C — maximum: printed folded tapered quarter-wave line

The one enclosure type that actually adds LF output from a small driver, and the one that
**only printing makes practical** (arbitrary curved, tapered internal ducts; no
woodworking).

- λ/4 at 145 Hz → path length **≈ 590 mm**, tapering from ≈ 3·Sd (43 cm²) at the closed
  end to ≈ 1·Sd (15 cm²) at the terminus.
- Duct ≈ 65 × 65 mm → 40 × 38 mm, folded 3× into roughly **160 × 160 × 90 mm**.
- Expected gain: **+3 to +4 dB across 130–200 Hz, F3 from ~172 Hz down to ~135 Hz.**
  About a third of an octave, and noticeably more body on voice.
- Cost: bigger box, and stuffing density must be iterated by ear/measurement.

**Do not expect more than that from any option.** Vd = Sd·Xmax ≈ 1.45 cm³ is the hard
wall (§2.3). If you want real bass, the answer is a second player/subwoofer in Music
Assistant, not this box. If you own **two** of these drivers, the right move is **two
Option-A pods as real stereo**, not two drivers in one box (the dual-2″ comb-filtering
critique in the existing doc is correct) — and that also buys +6 dB.

---

## 6. Best-possible print recipe

**Geometry choices that only make sense because it's printed:**

- **Curved or non-parallel walls.** A curved shell resists bending in-plane instead of
  out-of-plane, so it is far stiffer per gram than a flat panel, *and* it removes the
  parallel-wall modes of §4.2. Free in CAD, impossible in plywood.
- **Ribbed or sandwich walls** instead of thicker solid ones: two 1.6 mm skins with a
  ~5 mm gyroid core beats 4 mm solid on stiffness-per-gram and on damping. Alternatively
  design **sealed pour cavities with a fill plug** and fill them with fine sand or plaster
  after printing — mass plus lossy damping, and it is the single biggest audible upgrade
  available to a printed enclosure.
- **Filled filament** (PLA-CF, PLA-wood) has meaningfully higher internal damping — lower
  panel Q — than plain PLA. Worth it for the shell.
- **Heat-set brass inserts everywhere**, not self-tapping screws. M2 → 3.2 mm bore ×
  4 mm; M3 → 4.0 mm × 5.7 mm. Four M2 self-taps in 4 mm PLA holding a driver that gets
  removed a few times during PR/EQ tuning *will* strip, and they pull between layers —
  the weakest direction.

**Split the box into two printed parts (§4.6):** an **acoustic pod** and an
**electronics pod**, gasketed and bolted. Wins: each prints in its own optimal
orientation; no large flat divider drumhead; no wire pass through infill (sealed
terminals instead); electronics serviceable without breaking the acoustic seal; the
acoustic pod can be sand-filled; the mic moves off the driver's panel (§4.8).

**Slicer / material:**

| Setting | Value | Why |
|---|---|---|
| Material | **PETG or ASA** (PLA-CF acceptable indoors) | PLA's Tg ≈ 60 °C creeps on a sun-facing wall; ASA can be vapour-smoothed gas-tight |
| Nozzle / layer | 0.6 mm / 0.24 mm | fewer, fatter perimeters seal better than many thin ones |
| Perimeters | **5**, "ensure vertical shell thickness: all" | airtightness comes from perimeters, not infill |
| Infill | 25 % gyroid (or the sandwich core above) | isotropic, damping |
| Orientation | **open back down on the plate**, baffle up | no supports; §6 note below |
| Post-process | brush 2-part epoxy or shellac inside the chamber | closes any inter-layer porosity |
| Verify | pressure-test: seal the driver, blow into the terminal hole, soap the seams | a leak invalidates §2.1 entirely |

**Why a chamfer, not a fillet, on the front edge:** printing back-down puts the baffle on
top. A true tangent fillet starts horizontal at the baffle plane — a local 90° overhang.
A 45° chamfer with small fillets is support-free, prints clean, and captures most of the
diffraction benefit.

---

## 7. Code / assert holes in `hardware/speaker-case/`

1. **The published driver screw pattern is self-contradictory, and neither reading
   works.** `2026-06-13-speaker-case-design.md` says "4 × on a 43 mm square (60 mm
   diagonal)". For a **53 mm frame with a 46 mm cutout**:
   - as a 43 mm **square**, screws sit at r = 21.5·√2 = **30.4 mm** — outside the 26.5 mm
     frame radius entirely;
   - as a 43 mm bolt **circle**, screws sit at r = **21.5 mm** — inside the 23 mm cutout
     radius, i.e. through the cone.

   The pattern must land on the flange land, 23 < r < 26.5, so the real value is a bolt
   circle of ~**49 mm**, and it is a hard `[confirm vs hardware]`. Asserted both ways
   (`> spk_cut`, `< spk_od`) rather than trusting either published number.

   Consequence: **no raised screw bosses.** At r = 24.5 a 5 mm boss spans r ∈ [22, 27],
   overlapping both the cutout and the frame edge. The drivers get blind pilots straight
   into the baffle instead — which also retires the gasket-groove-severs-bosses problem,
   since a 53 mm frame has no room for an annular groove either (only a 3.5 mm annulus,
   shared with the screws). A shallow full-circle recess locates the frame and lands a
   punched foam ring.
2. **`vol_target = 1400000` is now an actively harmful assert** — it forces the box to
   stay ~3× oversized for this driver. Retarget to ~450 000 mm³.
3. **`net_vol()` overstates the real volume.** It computes `inner_w × spk_zone_h ×
   cavity_depth` as a rectangular prism minus two constants, ignoring the rounded corners
   (~5 600 mm³), the seat ring, the screw bosses, and the corner lid bosses. Small
   (~0.5 %) against 1.6 L, but the README quotes "1.5995 L" — precision the model does not
   have. At 0.45 L the boss volume is a larger fraction and should be subtracted.
4. **`driver_disp = 60000` / `pr_disp = 40000`** are PS95-8/PR figures. A 53 mm basket
   displaces ≈ 10 000 mm³; `pr_disp` → 0.
5. **Grille skirt grips a boss that doesn't exist** (§4.5) — a real geometry bug, not just
   an acoustic one.
6. **All `pr_*` params, modules, and asserts become dead code** and should be removed
   rather than left with unused values (they will silently pass their own asserts forever).
7. `assert(cavity_depth >= spk_depth)` etc. stay valid but the values collapse:
   `spk_depth` 45 → 28, `cavity_depth` 110 → ~70.
8. The uncommitted `mic_perf()` fix (piercing wall + pocket floor) is **correct — keep
   it**, even though §4.7 replaces the surrounding geometry.

---

## 7a. Two drivers (both units in hand) — what the second one buys

The limit in §2.3 is **excursion, not power**. Two coherent cones double Vd:

| | 1 driver | 2 drivers |
|---|---|---|
| Cone area | 14.5 cm² | 29 cm² |
| Max SPL @ 150 Hz (excursion) | ~79 dB | **~85 dB** |
| Midrange max | ~88–90 dB | **~94 dB** |
| Effective sensitivity below ~1.5 kHz | 83 dB/W | ~86 dB/W (+3 power, +3 mutual coupling) |
| Excursion per cone at a given SPL | x | **x/2** → much lower IMD |

That last row is what you hear. Halving excursion halves the intermodulation that
dominates a small full-range driver. **What it does not do:** Fc and Qtc are unchanged
if the box scales with driver count (0.5 L each → 1.0 L shared). Two drivers are louder
and cleaner, never deeper.

**Arrangement — vertical, never side by side.** The old spec rejected a dual-2″ pair
over comb filtering, which is right for the arrangement it assumed (70 mm *horizontal*
spacing → first null ~29° at 5 kHz) but missed the fix. Stacked vertically the combing
lands in the vertical plane, where listeners do not move, and the horizontal polar
response stays clean — the reason line arrays and MTM designs stack vertically. At
57 mm centres the first null is ~3.0 kHz at 90° off-axis and only walks inward above
that. A vertical pair also forces a narrow ~86 mm baffle, which fixes §4.3 for free.

Options considered:

- **Option 1 — two small pods, real stereo.** L/R from the PCM5102, one stereo amp, a
  cable to the second pod. No comb filtering at all; stereo imaging is the biggest
  subjective music gain available — and worthless for the intercom.
- **Option 2 — one box, vertical pair, dual mono. CHOSEN.** Both amp channels fed the
  same mono mix, one driver each: sidesteps both the 2 Ω parallel and 8 Ω series
  problems. One mount, one mic, one print, full +6 dB, all of the IMD benefit.
- Rejected: isobaric clamshell (halves required volume, gives no SPL — the box is
  already small) and opposed push-push (cancels cabinet vibration, throws away half the
  direct output).

## 7b. Adding bass — every lever, ranked

The ceiling first. Two cones at Xmax, Vd ≈ 2.9 cm³:

| Freq | Max SPL @ 1 m, both cones at Xmax |
|---|---|
| 150 Hz | 85 dB |
| 120 Hz | 80 dB |
| 100 Hz | 78 dB |
| 80 Hz | 74 dB |
| 60 Hz | **69 dB** |
| 50 Hz | **66 dB** |

Music at a comfortable level is 75–85 dB, so 50 Hz maxes out *below the music* — at zero
distortion allowance. Nothing reaches down there. Everything below is about 120–200 Hz,
which is where "sounds thin" actually lives.

1. **Placement — free, and bigger than everything else combined.** +3 dB on an open
   wall, **+6 dB at a wall/ceiling or wall/wall junction, +9 dB in a corner**,
   concentrated below ~250 Hz. Mount flush: 100 mm of standoff puts a cancellation notch
   at ~857 Hz.
2. **A tuned port at ~145 Hz — and this withdraws the folded TL of §5 Option C.**
   20 mm × 49 mm in 0.70 L: +3 dB at 140–170 Hz, F3 from 172 → ~135 Hz. A quarter-wave
   line gets the same third of an octave with better-damped roll-off, but for a *pair* it
   needs a 590 mm tapered path at 87 cm² starting cross-section, folding into a
   ~200 × 200 × 110 mm cabinet. A 49 mm printed tube wins on every practical axis, and
   printing it as a separate part makes Fb tunable by reprinting 5 g.
3. **EQ — the one you notice most.** The excursion ceiling only bites when loud. At 75 dB
   there is ~10 dB of headroom at 150 Hz, so a **+4 to +6 dB shelf below 250 Hz is
   effectively free**, paired with the high-pass. TTS bypasses MA DSP, so announcements
   stay un-boosted — which is what you want anyway.
4. **A subwoofer — the only real fix below 120 Hz, and nearly free here.** The passively
   summed L+R node also feeds a 3.5 mm jack; a powered sub's own low-pass does the
   crossover. No firmware change, one jack.

Rejected: doubling the box again (1.0 → 2.0 L moves Fc 172 → 159 Hz), and cone
mass-loading — it works (double Mms drops Fs 145 → 103 Hz) but costs 6 dB of sensitivity
everywhere and pushes Qtc to 0.86. A bad trade at 83 dB/W.

**Stacked result: full, musical output to ~120 Hz.** Male voice fundamentals, kick-drum
body, bass-guitar second harmonics. It sounds *full* rather than thin. Below 120 Hz it is
the sub or nothing.

## 8. Measure these three things before cutting any geometry

1. **Vas** (added-mass or closed-box delta-Fs method) — picks the box volume. Everything
   in §2.1 rests on an estimate.
2. **Xmax** — sets max SPL (§2.3) and whether the 330 µF cap corner should move.
3. **Driver frame dims in hand** — cutout 46, 43 mm screw square, seated depth 28. The
   asserts enforce fit, not truth.

Then: build Option A (or B), measure the near-field response, and only chase Option C if
the missing 130–200 Hz band genuinely bothers you.
