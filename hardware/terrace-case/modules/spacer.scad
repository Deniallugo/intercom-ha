// ===== depth spacer ring (no top-level geometry) =====
// A picture-frame inserted at the front-shell <-> rear-plate parting line to
// add `spacer_t` of air behind the drivers. No change to the front shell or
// rear plate: 4 corner pads pass the (longer) M3 screws straight through to the
// existing front bosses, and a registration spigot nests in the front shell's
// rear opening. Local coords: frame body z in [0, spacer_t]; spigot in
// [-spigot_h, 0] (points toward the front shell).

// hollow perimeter frame — the added air volume
module spacer_frame() {
    linear_extrude(spacer_t)
        difference() {
            rounded_rect(outer_w(), outer_h(), radius);
            rounded_rect(outer_w() - 2*wall, outer_h() - 2*wall, max(0.5, radius - wall));
        }
}

// solid corner pad merging into the frame, sized to contain the boss XY; the
// screw clearance hole is drilled later. Clamps onto the front boss top.
module spacer_corner_pad(sx, sy) {
    pad = 2*boss_inset + boss_od;   // square pad spanning the corner inward past the boss
    intersection() {
        linear_extrude(spacer_t) rounded_rect(outer_w(), outer_h(), radius);
        translate([sx*(outer_w()/2 - pad/2), sy*(outer_h()/2 - pad/2), 0])
            linear_extrude(spacer_t) square(pad, center = true);
    }
}

// registration lip nesting inside the front shell's rear opening, along all
// four edges; the four corners are relieved so the lip clears the front bosses.
module spacer_spigot() {
    lip_ow = outer_w() - 2*wall - 2*clr;
    lip_oh = outer_h() - 2*wall - 2*clr;
    ir     = max(0.5, radius - wall - clr);
    difference() {
        translate([0, 0, -spigot_h]) linear_extrude(spigot_h)
            difference() {
                rounded_rect(lip_ow, lip_oh, ir);
                rounded_rect(lip_ow - 2*spigot_wall, lip_oh - 2*spigot_wall, max(0.5, ir - spigot_wall));
            }
        // corner relief: clear the front shell's corner bosses
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -spigot_h - 0.1])
                cylinder(h = spigot_h + 0.2, d = boss_od + 2*clr);
    }
}

module spacer() {
    difference() {
        union() {
            spacer_frame();
            for (sx = [-1, 1], sy = [-1, 1]) spacer_corner_pad(sx, sy);
            spacer_spigot();
        }
        // M3 clearance holes through the corner pads (and the full spigot range)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -spigot_h - 0.1])
                cylinder(h = spacer_t + spigot_h + 0.2, d = screw_clear);
    }
}
