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
// `bclr` is the pocket clearance for THIS board — the two are no longer the same number,
// so it has to be passed in rather than read off the global. Pass the devkit's and the
// strips land under its header rows; leave it and they land under the DAC's.
module pin_relief(bw, bl, floor_h, along_short = false, x_lo = undef, x_hi = undef,
                 y_len = undef, sides = [-1, 1], row_w = undef, bclr = board_clr) {
    d = board_pin_h + clr;
    rw = is_undef(row_w) ? pin_row_w : row_w;
    if (along_short)
        // Short-edge strips. Each end defaults to a `pin_land` land; pass x_lo / x_hi to
        // override one and run the channel off that end instead, giving wires soldered along
        // these edges a route out of the pocket.
        for (sy = sides) {
            xl = is_undef(x_lo) ? -(bw/2 + bclr - pin_land) : x_lo;
            xr = is_undef(x_hi) ?  (bw/2 + bclr - pin_land) : x_hi;
            translate([(xl + xr)/2,
                       sy*((bl + 2*bclr)/2 - pin_relief_setback - rw/2),
                       floor_h - d/2 + 0.01])
                cube([xr - xl, rw, d + 0.02], center = true);
        }
    else
        // Long-edge strips. `y_len` pins the length instead of deriving it from the board,
        // anchored at the REAR end, so the board can grow without the channels growing.
        for (sx = [-1, 1]) {
            yl = -(bl + 2*bclr)/2 + pin_land;
            yh = is_undef(y_len) ? (bl + 2*bclr)/2 - pin_land : yl + y_len;
            translate([sx*((bw + 2*bclr)/2 - pin_relief_setback - pin_row_w/2),
                       (yl + yh)/2, floor_h - d/2 + 0.01])
                cube([pin_row_w, yh - yl, d + 0.02], center = true);
        }
}

// Registration lip nesting into the shell's cavity. The screws locate the plate
// eventually, but only after you have already lined it up against four inserts; the
// lip does that part, and closes the light gap at the seam.
module register_lip() {
    mirror([0, 0, 1]) linear_extrude(reg_h)
        difference() {
            rounded_rect(2*lip_outer_half_x(), 2*lip_outer_half_y(),
                         max(0.5, radius - wall - clr));
            rounded_rect(2*lip_inner_half_x(), 2*lip_inner_half_y(),
                         max(0.5, radius - wall - clr - reg_t));
        }
}

// Retention tab hanging off the +y pocket wall, over the board's front short edge — the
// thing that turns the pocket from a tray into a slot. Drawn in the seat's own mirrored
// frame, so z here is height ABOVE the plate's inner face, which is also print-up.
//
// The underside is a 45 deg ramp: the plate prints pocket-side up, so a shelf reaching
// inward at this height would be an unsupported overhang. Built as the hull of a sliver at
// the wall face and the finished tab one `s3_tab_over` higher, which makes the 45 deg true
// by construction rather than by a number that can drift.
//
// It hangs off the front wall, which is the register lip grown to pocket height, so the reach
// has to cross s3_front_clr before it is over the board at all — hence both the reach and the
// underside height being derived rather than typed.
module s3_front_tab() {
    yf   = lip_inner_half_y();                      // front wall's inner face
    z0   = s3_tab_z0();
    zt   = s3_tab_z1();
    ztop = s3_wall_top();
    if (s3_tab_cover > 0 && ztop > zt)
        hull() {
            translate([s3_pos_x, yf - 0.005, z0 + 0.005])
                cube([s3_tab_w, 0.01, 0.01], center = true);
            translate([s3_pos_x, yf - s3_tab_over()/2, (zt + ztop)/2])
                cube([s3_tab_w, s3_tab_over(), ztop - zt], center = true);
        }
}

// Two blocks on the register lip's own footprint at the rear, flanking a notch for the USB.
// They are the board's y datum: the front tab's ramp preloads it back against these.
//
// They stop at the PCB's top face and no higher. Full height would capture the board in z at
// both ends, and then it could not be assembled at all — with the tab over the front edge the
// only way in is to tilt the board rear-up and drop it behind these, which needs them low
// enough for the rear corners to clear.
module s3_rear_stop_blocks() {
    y1  = -lip_inner_half_y();                      // inner face — the datum
    y0  = -lip_outer_half_y();
    h   = s3_seat_h + s3_rear_stop_h;
    nx  = s3_rear_notch()/2;
    cav = s3_l/2 + s3_board_clr;                    // board cavity half-width
    if (s3_rear_stops && cav > nx)
        for (sx = [-1, 1]) {
            x0 = sx*nx;
            x1 = sx*cav;
            translate([s3_pos_x + (x0 + x1)/2, (y0 + y1)/2, h/2])
                cube([abs(x1 - x0), y1 - y0, h], center = true);
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
//
// The rear is no longer fully open: two stops now flank the USB notch (s3_rear_stops), which
// is what gives the board a y datum on the plate instead of on the shell wall. The notch is
// still wider than the window, so the ports themselves are as clear as they ever were.
module s3_seat() {
    h  = s3_seat_h + pcb_t + s3_lip;
    y0 = s3_pocket_y0();
    y1 = s3_pocket_y1();
    by = s3_cy() + s3_w/2;              // board's +y edge
    mirror([0, 0, 1]) {
        difference() {
            translate([s3_pos_x, (y0 + y1)/2, h/2])
                cube([s3_pocket_f()[0], y1 - y0, h], center = true);
            // board cavity, running off the -y end so the pocket is open there
            translate([s3_pos_x, (y0 - 1 + by)/2, s3_seat_h + (h - s3_seat_h + 0.1)/2])
                cube([s3_l + 2*s3_board_clr, by - y0 + 1, h - s3_seat_h + 0.1], center = true);
            // Pin-tail relief so the board seats FLAT, not on its own pins. BOTH strips run the
            // board's full length — the header rows do, so the relief has to.
            translate([s3_pos_x, s3_cy(), 0])
                pin_relief(s3_l, s3_w, s3_seat_h, y_len = s3_relief_len, bclr = s3_board_clr);
        }
        // ...and then the tab and the rear stops are put BACK into the cavity that was just
        // cut. The tab has to be a union rather than a smaller cut, or its 45 deg underside
        // would have to be built as a negative — the same wedge upside down, and far easier
        // to get wrong.
        s3_front_tab();
        s3_rear_stop_blocks();
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
        // SOCKET RECESS. The board is component-side DOWN, so the socket hangs below the PCB
        // and drops in here, cradled by the floor. It runs off the +x end so the socket can
        // also reach out into the wall's counterbore.
        // Authored z is DEPTH BELOW the plate's inner face, so the recess sinks from the
        // seating plane DOWN toward the plate: zlo..zhi below. Getting this direction wrong
        // cuts upward into the board and lip zone instead, leaving the floor solid and a
        // sliver of wall standing beside the relief.
        rz_lo = plate_inner_z() - dac_recess_z1();     // nearest the plate
        rz_hi = plate_inner_z() - dac_seat_z();        // the seating plane
        translate([(dac_recess_x0() + x1 + 1)/2, dac_jack_y(), (rz_lo + rz_hi)/2])
            cube([x1 + 1 - dac_recess_x0(), dac_recess_w(), rz_hi - rz_lo + 0.02],
                 center = true);
        // Open at the RIGHT (+x) end, landed at the left: the channels run off the edge of
        // the floor on the socket side, which is already the pocket's open side, so no wall
        // is breached. x_hi stops exactly at the floor's edge so the register lip beyond it
        // stays intact.
        // REAR channel only. The front one would sit inside the socket recess — the recess is
        // deeper, so the two nested into a stepped pocket — and it cannot be moved clear: the
        // relief setback pins its centre to the board edge, which is the same end the socket
        // is in. The recess already relieves that end of the board, so the channel there was
        // doing nothing anyway. (Asserted: dac_relief_y_rear() must stay clear of the recess.)
        //
        // Its +x end stops dac_relief_wall_gap short of the RIGHT wall's inner face rather
        // than running off the floor's edge: it is the jack's access and wants a land there.
        translate([dac_cx(), dac_pos_y(), 0])
            pin_relief(dac_w, dac_l, dac_seat_h, along_short = true,
                       x_hi = inner_half_x() - dac_relief_wall_gap - dac_cx(), sides = [-1],
                       row_w = dac_relief_w());
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
            translate([sx*boss_cx(), sy*boss_cy(), -0.1]) {
                cylinder(h = wall + 0.2, d = screw_clear);
                translate([0, 0, wall - screw_cbore_h + 0.1])
                    cylinder(h = screw_cbore_h + 0.1, d = screw_cbore_d);
            }
        vents();
        foot_recesses();
    }
}
