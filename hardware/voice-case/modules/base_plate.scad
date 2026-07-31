// ===== base plate (no top-level geometry) =====
// A flat lid `wall` thick that closes the bottom of the puck and carries the ESP32-S3
// devkit. The four M3 bosses live on the SHELL at full depth and hold the heat-set
// inserts; screws drop through these clearance holes into them, counterbored so no
// head stands proud to scratch a desk.
//
// Drawn in the plate's own frame: z = 0 is the INNER face (toward the cavity), +z is
// outward (toward the desk). Anything that reaches into the box is therefore drawn in
// +z and mirrored, so its numbers read as "depth below the inner face".

// Relief for solder-side pin tails, cut into a pocket floor. Two strips under the header
// rows along the board's long (+-x) edges, stopping short of each end so the board still
// seats on a land at both short ends as well as the central strip between them.
//
// Called from inside a seat's mirror([0,0,1]) block, so z here is depth below the plate's
// inner face: the floor spans 0..floor_h and the strips are sunk from floor_h downward.
// `along_short` puts the strips on the board's SHORT edges instead of its long ones. The
// devkit wants them on the long edges, where its header rows run. The DAC wants them on
// the short edges instead: its long +x edge is where the 3.5 mm socket lives, and that
// edge needs floor under it rather than a channel.
module pin_relief(bw, bl, floor_h, along_short = false, x_lo = undef, x_hi = undef) {
    d = board_pin_h + clr;
    if (along_short)
        // Short-edge strips. Each end defaults to a `pin_land` land; pass x_lo / x_hi to
        // override one and run the channel off that end instead, giving wires soldered along
        // these edges a route out of the pocket.
        for (sy = [-1, 1]) {
            xl = is_undef(x_lo) ? -(bw/2 + board_clr - pin_land) : x_lo;
            xr = is_undef(x_hi) ?  (bw/2 + board_clr - pin_land) : x_hi;
            translate([(xl + xr)/2,
                       sy*((bl + 2*board_clr)/2 - pin_relief_setback - pin_row_w/2),
                       floor_h - d/2 + 0.01])
                cube([xr - xl, pin_row_w, d + 0.02], center = true);
        }
    else
        for (sx = [-1, 1])
            translate([sx*((bw + 2*board_clr)/2 - pin_relief_setback - pin_row_w/2), 0,
                       floor_h - d/2 + 0.01])
                cube([pin_row_w, bl + 2*board_clr - 2*pin_land, d + 0.02], center = true);
}

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

// Friction pocket for the devkit, long axis along y, component side facing UP into the
// box. Walls on +y and +-x only — there is NO wall at the rear.
//
// That is the fix for "none of the USB ports fit". A rear wall with a notch in it leaves
// a stub either side of the notch, and those stubs sit directly in front of the two
// USB-C receptacles; nothing about widening the notch removes them entirely. With the
// end open, the board also slides back until it meets the shell's rear wall, so the
// receptacles end up as close to the window as the geometry allows and the plug setback
// stops depending on where the board drifted to inside an oversize pocket.
module s3_seat() {
    h  = s3_seat_h + pcb_t + s3_lip;
    y0 = s3_pocket_y0();
    y1 = s3_pocket_y1();
    by = s3_cy() + s3_w/2;              // board's +y edge
    mirror([0, 0, 1]) difference() {
        translate([s3_pos_x, (y0 + y1)/2, h/2])
            cube([s3_pocket_f()[0], y1 - y0, h], center = true);
        // board cavity, running off the -y end so the pocket is open there
        translate([s3_pos_x, (y0 - 1 + by)/2, s3_seat_h + (h - s3_seat_h + 0.1)/2])
            cube([s3_l + 2*board_clr, by - y0 + 1, h - s3_seat_h + 0.1], center = true);
        // Pin-tail relief so the board seats FLAT, not on its own pins. BOTH strips run the
        // board's full length — the header rows do, so the relief has to.
        translate([s3_pos_x, s3_cy(), 0]) pin_relief(s3_l, s3_w, s3_seat_h);
    }
}

// Friction pocket for the DAC, long axis along x, socket end toward the +x wall.
// OPEN at +x: the socket overhangs the PCB and stands above it, so a wall there would
// foul it — and the board needs no +x stop anyway, since the socket meeting its
// counterbore is the stop. Component side faces UP into the box, which puts the socket
// between the board and the top face, at the height the wall cutout is cut for.
module dac_seat() {
    h  = dac_seat_h + pcb_t + dac_lip;
    x0 = dac_pocket_x0();
    x1 = dac_pocket_x1();               // stops at the register lip, not the shell wall
    bx = dac_cx() - dac_w/2;            // board's -x edge
    mirror([0, 0, 1]) difference() {
        translate([(x0 + x1)/2, dac_pos_y(), h/2])
            cube([x1 - x0, dac_pocket_f()[1], h], center = true);
        // Board cavity, running off the +x end only, so the pocket is open on that side and
        // walled on the other three.
        translate([(bx + x1 + 1)/2, dac_pos_y(), dac_seat_h + (h - dac_seat_h + 0.1)/2])
            cube([x1 + 1 - bx, dac_l + 2*board_clr, h - dac_seat_h + 0.1], center = true);
        // Pin-tail relief on the SHORT edges here, not the long ones: the long +x edge is
        // the socket's, and it needs floor rather than a channel.
        // Open at the RIGHT (+x) end, landed at the left: the channels run off the edge of
        // the floor on the socket side, which is already the pocket's open side, so no wall
        // is breached. x_hi stops exactly at the floor's edge so the register lip beyond it
        // stays intact.
        translate([dac_cx(), dac_pos_y(), 0])
            pin_relief(dac_w, dac_l, dac_seat_h, along_short = true,
                       x_hi = dac_pocket_x1() - dac_cx());
    }
}

// Vent slots, all on the -x side: that is where the devkit is, and the devkit is what
// actually gets warm. They face the desk, so they are invisible in use. The two on the
// +x side are token — the DAC pocket and the feet leave almost no room there.
module vents() {
    for (v = vent_rects)
        translate([v[0], v[1], -0.1]) linear_extrude(wall + 0.2)
            rounded_rect(v[2], v[3], min(v[2], v[3])/2);
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
            dac_seat();
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
