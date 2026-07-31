// ===== mic clamp bar (no top-level geometry) =====
// The two M2 posts flank the INMP441 board rather than sit under it — they have to,
// because the board lies directly on its own gasket and nothing can be underneath it.
// So this bar spans both posts and its central pad reaches back down to the board and
// presses it, opposite the MEMS port. Tightening the two M2 screws is what compresses
// the gasket, and the gasket is what makes the seal that keeps the port volume near
// zero.
//
// Drawn in PRINTING orientation: bar flat on the plate at z = 0, pad growing +z. No
// supports.
module mic_clamp() {
    difference() {
        union() {
            translate([0, 0, mic_clamp_t/2])
                cube([mic_clamp_len(), mic_clamp_w, mic_clamp_t], center = true);
            translate([0, 0, mic_clamp_t + mic_clamp_pad_h()/2])
                cube([mic_clamp_pad, min(mic_clamp_pad, mic_clamp_w), mic_clamp_pad_h()],
                     center = true);
        }
        for (sx = [-1, 1])
            translate([sx*mic_post_pitch/2, 0, -0.1])
                cylinder(h = mic_clamp_t + 0.2, d = mic_screw_clear);
    }
}
