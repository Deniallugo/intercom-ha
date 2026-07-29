// ===== sound-first PR-loaded shell body (no top-level geometry) =====
// Open-back box. A horizontal divider seals the upper SPEAKER CHAMBER (one
// PS95-8 on the front baffle, a passive radiator on the +x side wall) off from
// the lower vented ELECTRONICS BAY. Driver wires run up through one sealed pass
// in the divider. PR/bay geometry is added in later tasks.

// ---- speaker zone (upper, sealed) -----------------------------------------

module speaker_seat() {
    translate([spk_cx(), spk_cy(), wall])
        difference() {
            cylinder(h = spk_seat_depth, d = spk_od + 2*seat_wall);
            translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
        }
}

module cone_cut() {
    translate([spk_cx(), spk_cy(), -0.1]) linear_extrude(wall + 0.2) circle(d = spk_cut);
}

// The gasket ring straddles the screw bolt circle, so the groove would slice the
// speaker screw bosses free of the baffle. Notch it at each boss (screw clearance
// in the gasket) so a baffle pillar stays under each boss.
module gasket_groove() {
    translate([spk_cx(), spk_cy(), wall - gasket_depth])
        difference() {
            difference() {
                cylinder(h = gasket_depth + 0.1, d = gasket_od);
                translate([0, 0, -0.1]) cylinder(h = gasket_depth + 0.3, d = gasket_id);
            }
            for (i = [0 : spk_screw_n - 1])
                rotate([0, 0, i*360/spk_screw_n + 45])
                    translate([spk_bolt_circle/2, 0, -0.2])
                        cylinder(h = gasket_depth + 0.5, d = spk_boss_od + 2*clr);
        }
}

module speaker_screw_bosses() {
    translate([spk_cx(), spk_cy(), wall])
        screw_circle(spk_screw_n, spk_bolt_circle, spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// ---- passive radiator (mounted on the +x side wall, fires sideways) --------

// locating ring on the INNER side-wall face
module pr_seat() {
    translate([side_x(), spk_cy(), pr_cz()]) rotate([0, -90, 0])
        difference() {
            cylinder(h = pr_seat_depth, d = pr_od + 2*pr_seat_wall);
            translate([0, 0, -0.1]) cylinder(h = pr_seat_depth + 0.2, d = pr_od + 2*clr);
        }
}

// open cutout through the +x side wall
module pr_cut_hole() {
    translate([outer_w()/2 - wall - 0.1, spk_cy(), pr_cz()]) rotate([0, 90, 0])
        linear_extrude(wall + 0.2) circle(d = pr_cut);
}

// annular gasket groove recessed into the inner side-wall face. Same as the
// driver: the ring straddles the PR bolt circle, so notch it at each boss to keep
// a wall pillar under the PR screw bosses.
module pr_gasket_groove() {
    translate([side_x() + pr_gasket_depth, spk_cy(), pr_cz()]) rotate([0, -90, 0])
        difference() {
            difference() {
                cylinder(h = pr_gasket_depth + 0.1, d = pr_gasket_od);
                translate([0, 0, -0.1]) cylinder(h = pr_gasket_depth + 0.3, d = pr_gasket_id);
            }
            for (i = [0 : pr_screw_n - 1])
                rotate([0, 0, i*360/pr_screw_n + 45])
                    translate([pr_bolt_circle/2, 0, -0.2])
                        cylinder(h = pr_gasket_depth + 0.5, d = pr_boss_od + 2*clr);
        }
}

// 4 mounting bosses on the bolt circle, side-wall plane
module pr_screw_bosses() {
    translate([side_x(), spk_cy(), pr_cz()]) rotate([0, -90, 0])
        screw_circle(pr_screw_n, pr_bolt_circle, pr_boss_h, pr_boss_od, pr_screw_pilot);
}

// ---- divider (sealing floor) -----------------------------------------------

// single sealed wire pass, centered under the driver
module divider_wire_cut() {
    translate([spk_cx(), divider_cy(), divider_wire_z])
        rotate([90, 0, 0])
            cylinder(h = divider_t*3, d = divider_wire_d, center = true);
}

module divider() {
    difference() {
        translate([0, divider_cy(), wall + cavity_depth/2])
            cube([outer_w() - 2*wall, divider_t, cavity_depth], center = true);
        divider_wire_cut();
    }
}

// ---- electronics bay (front-baffle board mounts) ---------------------------
module bay_boards() {
    // S3 devkit: friction pocket (no reliable mount holes)
    translate([s3_pos[0], board_cy()+s3_pos[1], wall]) board_pocket(s3_w, s3_l, board_standoff_h+2, pocket_wall);
    // boards with holes: corner standoffs
    translate([dac_pos[0],  board_cy()+dac_pos[1],  wall]) board_standoffs(dac_w, dac_l, board_standoff_h, board_standoff_od, board_screw_pilot);
    translate([buck_pos[0], board_cy()+buck_pos[1], wall]) board_standoffs(buck_w, buck_l, board_standoff_h, board_standoff_od, board_screw_pilot);
    translate([trig_pos[0], board_cy()+trig_pos[1], wall]) board_standoffs(trig_w, trig_l, board_standoff_h, board_standoff_od, board_screw_pilot);
    mic_mount();   // ICS-43434 friction pocket
}

// ---- front-panel breaches --------------------------------------------------

// PTT panel-mount momentary switch, bottom-center of the front baffle.
// The bore runs through a LOCALLY THINNED panel (btn_panel_t) so a switch rated
// for a 1-3 mm panel still gets enough thread for its nut; behind it a flat
// counterbore takes the nut (bezel-in-front switch) or the body shoulder
// (nut-in-front switch). Flat land on both faces = the switch clamps solid and
// the actuator can't rock, which is the whole point of the thinning.
module button_bore() {
    translate([btn_pos[0], board_cy()+btn_pos[1], 0]) {
        translate([0, 0, -0.1]) cylinder(h = btn_panel_t + 0.1, d = btn_bore_d);
        cylinder(h = btn_lead_in, d1 = btn_bore_d + 2*btn_lead_in, d2 = btn_bore_d);
        translate([0, 0, btn_panel_t])
            cylinder(h = wall - btn_panel_t + 0.1, d = btn_pocket_d);
        translate([0, 0, -0.1]) difference() {                  // tactile halo, outer face
            cylinder(h = btn_halo_depth + 0.1, d = btn_halo_od);
            translate([0, 0, -0.1]) cylinder(h = btn_halo_depth + 0.3, d = btn_halo_id);
        }
    }
}

// ICS-43434 mic board: friction pocket + a front perforation cluster over its port
module mic_mount() {
    translate([mic_pos[0], board_cy()+mic_pos[1], wall])
        board_pocket(mic_board_w, mic_board_l, board_standoff_h+1, pocket_wall);
}
// perforation must pierce the front wall AND the friction-pocket floor behind
// it (pocket sits at z=wall with a pocket_wall-thick floor), or the bottom-
// ported ICS-43434 resting on that floor is sealed off from the outside.
module mic_perf() {
    translate([mic_pos[0], board_cy()+mic_pos[1], -0.1]) linear_extrude(wall + pocket_wall + 0.2) {
        circle(d = mic_hole_d);
        for (i = [0 : mic_ring_n - 1])
            rotate(i*360/mic_ring_n) translate([mic_ring_r, 0]) circle(d = mic_hole_d);
    }
}

// USB-C power IN: bounded hole through the bottom (-y) wall at usb_z
module usb_floor_cut() {
    // x follows trig_pos[0]: the USB-C receptacle is on the CH224K board. wall*3 = oversized to punch cleanly through the bottom wall.
    translate([trig_pos[0], -outer_h()/2, usb_z])
        cube([usb_conn_w + usb_clr, wall*3, usb_conn_t + usb_clr], center = true);
}

// ---- corners --------------------------------------------------------------

module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}

module body() {
    difference() {
        union() {
            shell_body(front_depth);
            divider();
            speaker_seat();
            speaker_screw_bosses();
            pr_seat();
            pr_screw_bosses();
            corner_bosses();
            bay_boards();
        }
        cone_cut();
        gasket_groove();
        pr_cut_hole();
        pr_gasket_groove();
        button_bore();
        mic_perf();
        usb_floor_cut();
    }
}
