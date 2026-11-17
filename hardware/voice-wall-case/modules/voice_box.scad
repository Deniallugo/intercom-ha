// ===== Voice S3 box: shell, rear lid, board tray, pass-through sleeve (box-local frame) =====
// The front-face features are voice-case's (button bore + recess + blind pilots, gasket mic seat +
// clamp posts), placed on a vertical face instead of a horizontal one. Same z convention, so the
// modules are unchanged apart from where they sit.

module button_cut() {
    translate([btn_pos[0], btn_pos[1], 0]) {
        translate([0, 0, -0.1]) cylinder(h = wall + 0.2, d = btn_bore_d());
        translate([0, 0, -0.1]) cylinder(h = btn_recess_depth + 0.1, d = btn_recess_d());
    }
}

module button_pilots() {
    for (sx = [-1, 1])
        translate([btn_pos[0] + sx*btn_pilot_pitch/2, btn_pos[1], wall - btn_pilot_depth])
            cylinder(h = btn_pilot_depth + 0.1, d = board_screw_pilot);
}

module mic_seat() {
    translate([mic_pos[0], mic_pos[1], 0]) {
        translate([0, 0, wall - mic_seat_depth]) linear_extrude(mic_seat_depth + 0.1)
            square([mic_board_w + 2*clr, mic_board_l + 2*clr], center = true);
        translate([0, 0, wall - mic_seat_depth - mic_gasket_depth])
            cylinder(h = mic_gasket_depth + 0.01, d = mic_gasket_d);
        translate([0, 0, -0.1])
            cylinder(h = wall - mic_seat_depth - mic_gasket_depth + 0.2, d = mic_hole_d);
    }
}

module mic_posts() {
    for (sx = [-1, 1])
        translate([mic_pos[0] + sx*mic_post_pitch/2, mic_pos[1], wall - 0.01])
            screw_boss(mic_post_h + 0.01, mic_post_od, board_screw_pilot);
}

module voice_shell() {
    h = voice_h;
    d = box_d();
    difference() {
        union() {
            box_shell(box_w, h, d, box_r, front_chamfer);
            lid_bosses(h);
            multmatrix(top_face_m(h)) mic_posts();
        }
        button_cut();
        button_pilots();
        multmatrix(top_face_m(h)) mic_seat();   // the mic is on the TOP face
        // floor: the sleeve down into the amp box
        floor_cut() translate([sleeve_x, sleeve_zc()]) circle(d = sleeve_od() + 2*clr);
        // sides: slots alongside the devkit, low (intake) and high (exhaust)
        for (sx = [-1, 1], yy = [tray_top() + 9, h - wall - 6])
            side_cut(sx) translate([s3_zc(), yy]) rotate(90) slot_field(1, s3_pocket()[1] - 4);
    }
}

module voice_lid() { box_lid(voice_h, peg_y_voice); }

// ---- board tray ----
// Both boards lie component-side UP in friction pockets, pushed toward the front by the lid through
// the tray itself. The pocket floors stand tray_seat proud of the tray so the pin-tail relief can be
// sunk into them without going through.
module pocket(cav, c, relief) {
    o = cav + [2*pocket_wall, 2*pocket_wall];
    hgt = tray_seat + pcb_t + tray_lip;
    translate([c[0], tray_top() - 0.01, c[1]])
        difference() {
            translate([-o[0]/2, 0, -o[1]/2]) cube([o[0], hgt, o[1]]);
            translate([-cav[0]/2, tray_seat, -cav[1]/2]) cube([cav[0], hgt, cav[1]]);
            for (r = relief)   // [x, z, w, l] relative to the pocket centre, sunk board_pin_h
                translate([r[0] - r[2]/2, tray_seat - board_pin_h, r[1] - r[3]/2])
                    cube([r[2], board_pin_h + 0.1, r[3]]);
        }
}

module voice_tray() {
    s3c  = [s3_x, s3_zc()];
    dacc = [dac_xc(), dac_zc()];
    difference() {
        union() {
            sled_plate(tray_t);   // same outline + notches as the amp sled
            // devkit: long axis across x, header rows along its two long (front/rear) edges
            pocket(s3_cav(), s3c,
                   [for (s = [-1, 1]) [0, s*(s3_cav()[1]/2 - pin_row_w/2 - 0.5), s3_cav()[0] - 1, pin_row_w]]);
            // DAC: long axis across x, socket on the REAR long edge
            pocket(dac_cav(), dacc,
                   [[0, 0, dac_cav()[0] - 5, dac_cav()[1] - 5]]);
        }
        // notch the DAC pocket's rear wall where the socket overhangs it
        translate([dac_jack_x() - dac_jack_w/2 - clr, tray_top() + tray_seat - 0.5, dac_edge_z() - 0.5])
            cube([dac_jack_w + 2*clr, 20, pocket_wall + board_clr + 2]);
        // sleeve
        translate([sleeve_x, wall - 0.1, sleeve_zc()]) rotate([-90, 0, 0])
            cylinder(h = tray_t + 0.2, d = sleeve_od() + 2*clr);
    }
}

// ---- pass-through sleeve: flange rests on the tray, tube drops through the voice floor, across the
// stack gap and sleeve_engage into the amp top. Printed flange-down.
module sleeve() {
    difference() {
        union() {
            cylinder(h = 1.6, d = sleeve_od() + 2*sleeve_flange);
            cylinder(h = 1.6 + sleeve_len(), d = sleeve_od());
        }
        translate([0, 0, -0.1]) cylinder(h = sleeve_len() + 2, d = sleeve_id);
        // 0.6 chamfer at the entry so a wire jacket cannot catch
        translate([0, 0, -0.1]) cylinder(h = 0.7, d1 = sleeve_id + 1.4, d2 = sleeve_id);
    }
}
