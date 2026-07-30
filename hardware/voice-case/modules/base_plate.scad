// ===== base plate (no top-level geometry) =====
// A flat lid `wall` thick that closes the bottom of the puck and carries the ESP32-S3
// devkit. The four M3 bosses live on the SHELL at full depth and hold the heat-set
// inserts; screws drop through these clearance holes into them, counterbored so no
// head stands proud to scratch a desk.
//
// Drawn in the plate's own frame: z = 0 is the INNER face (toward the cavity), +z is
// outward (toward the desk). Everything mounted into the box is therefore mirrored to
// -z, and authored via plate_d() — depth below the inner face.

// Registration lip nesting into the shell's cavity. The screws locate the plate
// eventually, but only after you have already lined it up against four inserts; the
// lip does that part, and closes the light gap at the seam.
module register_lip() {
    mirror([0, 0, 1]) linear_extrude(reg_h)
        difference() {
            rounded_rect(plan - 2*wall - 2*clr, plan - 2*wall - 2*clr,
                         max(0.5, radius - wall - clr));
            rounded_rect(plan - 2*wall - 2*clr - 2*reg_t, plan - 2*wall - 2*clr - 2*reg_t,
                         max(0.5, radius - wall - clr - reg_t));
        }
}

// Friction pocket for the devkit, long axis along y, component side facing UP into
// the box. The -y wall is notched away over the USB window: without that notch the
// pocket wall sits between the cable and the receptacle and no plug reaches it.
module s3_seat() {
    h = s3_seat_h + pcb_t + s3_lip;
    translate([s3_pos[0], s3_pos[1], 0]) mirror([0, 0, 1]) difference() {
        translate([0, 0, h/2])
            cube([s3_pocket_sz()[0], s3_pocket_sz()[1], h], center = true);
        // board cavity, open at the top of the pocket
        translate([0, 0, s3_seat_h + (h - s3_seat_h + 0.1)/2])
            cube([s3_l + 2*clr, s3_w + 2*clr, h - s3_seat_h + 0.1], center = true);
        // USB notch through the -y wall, lined up with the shell's rear window
        translate([0, -(s3_w/2 + clr + pocket_wall/2), s3_seat_h + (h - s3_seat_h + 0.2)/2])
            cube([s3_usb_w, pocket_wall*3, h - s3_seat_h + 0.2], center = true);
    }
}

// Vent slots in the two x-bands the devkit pocket leaves free. They face the desk, so
// they are invisible in use; an S3 at 240 MHz with PSRAM in a closed box is not cold.
module vents() {
    for (vx = vent_xs)
        translate([vx, 0, -0.1]) linear_extrude(wall + 0.2) slot(vent_w, vent_l);
}

// Shallow recesses at the mid-edges for self-adhesive feet — mid-edges rather than
// corners because the corners are where the screw counterbores are.
module foot_recesses() {
    for (p = foot_positions)
        translate([p[0], p[1], wall - foot_depth]) cylinder(h = foot_depth + 0.1, d = foot_d);
}

module base_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);
            register_lip();
            s3_seat();
        }
        // corner screws: clearance through, counterbored from the OUTER face
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*boss_c(), sy*boss_c(), -0.1]) {
                cylinder(h = wall + 0.2, d = screw_clear);
                translate([0, 0, wall - screw_cbore_h + 0.1])
                    cylinder(h = screw_cbore_h + 0.1, d = screw_cbore_d);
            }
        vents();
        foot_recesses();
    }
}
