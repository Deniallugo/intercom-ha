// ===== Voice S3 wall unit — design checks =====
// Every fit the layout depends on, named, so that changing a [photo]/[assumed] number to its measured
// value tells you WHICH clearance it broke instead of producing a box that quietly doesn't close.
include <../modules/params.scad>
include <../modules/lib.scad>
include <../modules/amp_box.scad>
include <../modules/voice_box.scad>
include <../modules/button.scad>
include <../modules/wall_plate.scad>

function within(v, lo, hi) = v >= lo && v <= hi;
ih = inner_w()/2;

// ===================== shared envelope =====================
assert(inner_w() >= s3_pocket()[0], str("box_w too narrow for the devkit across x — needs ",
       s3_pocket()[0] + 2*wall));
assert(inner_w() >= amp_w + 2*clr, "box_w too narrow for the amp board");
assert(inner_w() >= amp_face_w + 2*face_fit, "faceplate rebate wider than the box inside");
assert(box_d() > lid_boss_len + lid_boss_taper() + 10, "box too shallow for the lid bosses");

// ===================== amplifier =====================
// vertical stack: floor, sled, standoffs, envelope, air, top
assert(amp_standoff_h >= amp_tail_h + 2.5, "standoffs leave no room for the 24 V tap wires under the PCB");
assert(amp_hs_clr >= 6, "less than 6 mm of air over the heatsink");
// faceplate window
assert(amp_face_y() - face_fit >= wall + 0.5, "faceplate rebate cuts into the floor");
assert(amp_face_y() + amp_face_h + face_fit <= amp_h() - wall - 0.5, "faceplate rebate cuts into the top");
assert(amp_face_y() > wall + sled_t, "faceplate bottom is below the sled top — the sled would block it");
assert(face_lip > 0.8 && face_lip < amp_face_h/4, "faceplate lip out of range");
assert(face_rebate < wall - 1, "faceplate rebate leaves under 1 mm of front wall");
assert(ctrl_mode == "faceplate" || ctrl_mode == "holes", "ctrl_mode must be faceplate|holes");
assert(amp_knob_proj() >= knob_min_grip,
       str("only ", amp_knob_proj(), " mm of shaft outside the box — knobs will not grip"));
if (ctrl_mode == "holes")
    assert(ctrl_x0 + ctrl_pitch + ctrl_bush_d/2 + clr + ctrl_slack < ih - 1, "outer shaft hole hits the side wall");
// rear lid bosses vs things on the floor and in the plug zone
for (p = lid_boss_pts(amp_h()))
    assert(abs(p[0]) + lid_boss_od/2 < ih, "lid boss runs into a side wall");
assert(lid_boss_x_bot - lid_boss_od/2 - 0.6 > mp_x + mp_w/2 + clr + mp_wall,
       "MP1584 pocket runs into the bottom-right lid boss notch");
assert(-lid_boss_x_bot + lid_boss_od/2 + 0.6 < mp_x - mp_w/2 - clr - mp_wall,
       "MP1584 pocket runs into the bottom-left lid boss notch");
assert(plug_zone >= mp_l + 2*clr + 2*mp_wall + 1, "plug zone shallower than the MP1584 pocket");
// sleeve hole in the amp top: clear of the top lid bosses
assert(abs(abs(sleeve_x) - lid_boss_x_top) > sleeve_od()/2 + clr + lid_boss_od/2 + 0.5,
       "sleeve hole runs into a top lid boss");
// panel switch body: inside the plug zone, clear of the top boss and the floor stack
if (amp_psw) {
    sw_x0 = ih - amp_psw_body[0];
    assert(amp_psw_cut[0]/2 + psw_zc() < box_d() - 1 && psw_zc() - amp_psw_body[1]/2 > plug_z0(),
           "panel switch body leaves the plug zone");
    assert(sw_x0 > lid_boss_x_top + lid_boss_od/2 + 0.5
           || amp_psw_y + amp_psw_body[2]/2 < lid_boss_pts(amp_h())[2][1] - lid_boss_od/2,
           "panel switch body hits the top-right lid boss");
    assert(amp_psw_y - amp_psw_body[2]/2 > wall + sled_t + mp_lip + 1, "panel switch body hits the sled");
    assert(sw_x0 > amp_aux_x + dac_aux_plug/2 + 0.5
           || amp_psw_y - amp_psw_body[2]/2 > amp_pcb_top() + amp_aux_axis + dac_aux_plug/2,
           "panel switch body hits the AUX plug");
    assert(amp_psw_y + amp_psw_cut[1]/2 < amp_h() - wall - 1 && amp_psw_y - amp_psw_cut[1]/2 > wall + 1,
           "panel switch cut-out does not fit the side wall");
}
// lid cable window: inside the legs, clear of the lid screws
assert(amp_win_x0() > -(peg_x() - leg_w/2), "cable window runs under the left leg");
assert(amp_win_x1() <  (peg_x() - leg_w/2), "cable window runs under the right leg");
assert(amp_win_y0() > lid_boss_pts(amp_h())[0][1] + screw_clear/2 + 1.5, "cable window cuts the bottom lid screws");
assert(amp_win_y1() < lid_boss_pts(amp_h())[2][1] - screw_clear/2 - 1.5, "cable window cuts the top lid screws");
// barrel plug body must clear the legs in the channel
assert(abs(amp_x + amp_dc_x) + amp_dc_plug_d/2 < peg_x() - leg_w/2, "barrel plug body hits a lid leg in the channel");
// sled standoffs: on the sled, clear of the faceplate and the plug zone
for (p = amp_holes) {
    assert(abs(p[0]) + amp_standoff_od/2 < amp_w/2 + 0.01, "a standoff sits outside the board");
    assert(within(amp_bz(p[1]), amp_front_z() + amp_face_t + amp_standoff_od/2,
                  amp_rear_z() - amp_standoff_od/2 + 0.01), "a standoff sits outside the board's length");
}

// ===================== voice box =====================
assert(voice_h >= voice_h_min(), str("voice_h too small for the dome — needs ", voice_h_min()));
assert(btn_pos[1] - btn_dome_d/2 > front_chamfer + 2, "dome overhangs the bottom edge of the face");
assert(btn_pos[1] + btn_dome_d/2 < voice_h - front_chamfer - 1, "dome overhangs the top edge of the face");
assert(btn_pos[1] - bh_collar_od()/2 > tray_top() + tray_seat + pcb_t + tray_lip
       || bh_deep_z() < s3_z0 - 1, "button holder collides with the devkit pocket");
assert(bh_deep_z() < s3_z0 - 1, str("devkit pocket starts inside the button holder's depth (",
       bh_deep_z(), ")"));
// mic block above the button holder, inside the face
// mic on the TOP face: mic_pos = [x, z]
assert(mic_pos[1] - mic_size()[1]/2 > bh_deep_z() + 1
       || voice_h - wall - mic_post_h - mic_clamp_t > btn_pos[1] + bh_collar_od()/2 + 1, "mic block runs into the button holder");
assert(mic_pos[1] - mic_size()[1]/2 > front_chamfer + wall, "mic seat runs into the front edge");
assert(mic_pos[1] + mic_size()[1]/2 < lid_boss_z0() - 1, "mic block runs into the top lid bosses");
assert(abs(mic_pos[0]) + mic_size()[0]/2 < ih, "mic posts run into a side wall");
assert(btn_pilot_pitch/2 + bh_ear_d/2 < ih, "button holder ears run into a side wall");
// tray: pockets fit, DAC behind the devkit, socket + plug land over the sleeve, notches clear
assert(abs(s3_x) + s3_pocket()[0]/2 < ih - clr, "devkit pocket wider than the tray");
assert(abs(dac_xc()) + dac_cav()[0]/2 + pocket_wall < ih - clr, "DAC pocket runs off the tray");
assert(dac_socket_z() + dac_aux_plug < sleeve_zc() + sleeve_od()/2,
       "the AUX plug head reaches past the sleeve — move the DAC forward or deepen plug_zone");
assert(dac_z0() + dac_cav()[1] + 2*pocket_wall < lid_boss_z0() - 1
       || abs(dac_xc()) + dac_cav()[0]/2 + pocket_wall < lid_boss_x_bot - lid_boss_od/2 - 0.6,
       "DAC pocket runs into a lid boss notch");
assert(abs(sleeve_x) + sleeve_od()/2 + sleeve_flange < lid_boss_x_bot - lid_boss_od/2 - 0.6,
       "sleeve flange sits over a lid boss notch");
assert(sleeve_zc() - sleeve_od()/2 - sleeve_flange > dac_edge_z(), "sleeve flange runs under the DAC");
assert(sleeve_zc() + sleeve_od()/2 + sleeve_flange < box_d() - 0.5, "sleeve flange hits the lid");
assert(tray_seat >= board_pin_h + 0.5, "pin relief would cut through the pocket floor");
// sleeve vs the peg drop: the voice box must lift off its pegs without the sleeve still engaged
assert(sleeve_engage < peg_drop - 1, "sleeve still engaged in the amp top when the pegs are free");

// ===================== button =====================
assert(btn_wall_id() > sw_diag() + 2*clr, "plunger bore does not swallow the switch diagonal");
assert(btn_post_d < sw_plunger_d, "post overhangs the switch plunger");
assert(btn_preload < sw_travel - 0.3, "preload eats the switch travel");
assert(btn_post_h() > 0, "post has no length — check the switch height");
assert(btn_flange_d < btn_dome_d - 2*btn_rim_lift, "flange is wider than the dome's flat underside");
assert(btn_recess_d() > btn_flange_d, "recess smaller than the flange");
assert(btn_edge_drop() < btn_rim_gap(),
       str("a press at the dome's edge can ground it on the face before the switch closes (",
           btn_edge_drop(), " vs ", btn_rim_gap(), ") — raise btn_flange_t or bh_guide_h"));
assert(btn_wall_z1() + btn_stroke() < bh_relief_z1() - 0.2, "plunger end bottoms on the collar floor");
assert(sw_top_z() > btn_ceil_z() + btn_stroke() + 0.2, "switch body hits the plunger ceiling at full press");

// ===================== wall plate / hanging =====================
assert(stack_gap < peg_drop, "amp box can lift off its pegs with the voice box in place");
assert(lock_gap  < peg_drop, "voice box can lift off its pegs under the lock bracket");
assert(stack_gap > sleeve_engage, "sleeve longer than the gap it crosses");
assert(plate_t - kh_lip >= peg_len() - kh_lip - kh_clr + 0.5, "peg head deeper than the keyhole cavity");
assert(kh_head_d() < leg_w + 2*plate_margin - 2, "keyhole wider than the plate edge allows");
assert(peg_x() + kh_head_d()/2 < plate_w()/2 - 1, "keyhole breaks out of the plate edge");
for (ys = [peg_y_amp, peg_y_voice]) assert(ys[1] - ys[0] > peg_drop + kh_head_d() + 2, "keyholes overlap");
assert(max(peg_y_amp) + peg_drop + kh_head_d()/2 < amp_h() + stack_gap, "amp keyhole runs into the voice box zone");
assert(voice_z0() + max(peg_y_voice) + peg_drop + kh_head_d()/2 < plate_h() - 1, "voice keyhole runs off the plate top");
assert(header_w()/2 < peg_x() - leg_w/2, "lock header collides with the legs");
assert(header_d - plate_t >= insert_m3_d + 3, "header too thin for the lock inserts");
assert(header_d < lid_back_y(), "header reaches the voice lid");
for (p = ws_pts()) assert(abs(p[0]) + ws_head_d/2 < peg_x() - leg_w/2, "wall screw under a leg");
assert(plate_h() <= 250 && plate_w() <= 250, "wall plate exceeds the A1 bed (256 x 256)");
assert(box_d() + lid_t <= 250, "box exceeds the A1 bed");

echo(str("ENVELOPE  amp ", box_w, " x ", amp_h(), " x ", box_d() + lid_t,
         "  voice ", box_w, " x ", voice_h, " x ", box_d() + lid_t,
         "  plate ", plate_w(), " x ", plate_h(), " x ", plate_t,
         "  front face ", front_y(), " mm off the wall, total height ", plate_h() + lock_t));
echo(str("BUTTON    crown ", btn_proud(), " proud, rim gap ", btn_rim_gap(), ", edge drop ", btn_edge_drop(),
         ", post ", btn_post_h(), ", holder reaches ", bh_deep_z()));
echo(str("AMP       PCB underside at y ", amp_pcb_y(), ", envelope top ", amp_env_top(),
         ", faceplate y ", amp_face_y(), "..", amp_face_y() + amp_face_h,
         ", knob shaft outside ", amp_knob_proj(), ", plug zone z ", plug_z0(), "..", box_d()));
cube(1);
