"""Design checks — the port of ``tests/asserts.scad``, plus the electronics.

The first half is every assert from the OpenSCAD, one for one. The second half is new: every
electronic part (``elec.py``) against every other one in its box, against the box's cavity,
and against the printed obstacles in it. That half is what makes dragging a part around in
Fusion safe — move the devkit into the button holder, run `sync`, and the build refuses with
the two names, instead of a case that quietly does not close.

Pure CPython, no adsk: ``python3 vwc/checks.py`` (or ``../test.sh``) runs it anywhere, and
the Fusion script runs it BEFORE modelling and builds nothing on a design that fails.
"""

import sys

try:
    from . import elec, params as P
except ImportError:                        # run directly, not as a package
    import elec
    import params as P


class Checks:
    def __init__(self):
        self.failures = []

    def ok(self, cond, msg):
        if not cond:
            self.failures.append(msg)
        return cond


def within(v, lo, hi):
    return lo <= v <= hi


def _overlap(a, b, eps=0.05):
    """two AABBs share volume (touching faces do not count)"""
    (alo, ahi), (blo, bhi) = a, b
    return all(alo[k] < bhi[k] - eps and blo[k] < ahi[k] - eps for k in range(3))


def run_checks():
    c = Checks()
    ok = c.ok
    ih = P.inner_w()/2

    # ===================== shared envelope =====================
    ok(P.inner_w() >= P.s3_pocket()[0], 'box_w too narrow for the devkit across x — needs %s'
       % (P.s3_pocket()[0] + 2*P.wall))
    ok(P.inner_w() >= P.amp_w + 2*P.clr, 'box_w too narrow for the amp board')
    ok(P.inner_w() >= P.amp_face_w + 2*P.face_fit, 'faceplate rebate wider than the box inside')
    ok(P.box_d() > P.lid_boss_len + P.lid_boss_taper() + 10, 'box too shallow for the lid bosses')

    # ===================== amplifier =====================
    ok(P.amp_standoff_len() >= P.amp_tail_h + 2.5,
       'standoffs leave no room for the 24 V tap wires under the PCB')
    ok(P.amp_hs_clr >= 6, 'less than 6 mm of air over the heatsink')
    ok(P.amp_face_y() - P.face_fit >= P.wall + 0.5, 'faceplate rebate cuts into the floor')
    ok(P.amp_face_y() + P.amp_face_h + P.face_fit <= P.amp_h() - P.wall - 0.5,
       'faceplate rebate cuts into the top')
    ok(P.amp_face_y() > P.wall + P.sled_t, 'faceplate bottom is below the sled top')
    ok(0.8 < P.face_lip < P.amp_face_h/4, 'faceplate lip out of range')
    ok(P.face_rebate < P.wall - 1, 'faceplate rebate leaves under 1 mm of front wall')
    ok(P.ctrl_mode in ('faceplate', 'holes'), "ctrl_mode must be 'faceplate' or 'holes'")
    ok(P.ctrl_mode != 'faceplate' or P.amp_setback == 0,
       'amp_setback must be 0 in faceplate mode — the faceplate IS the front skin')
    ok(abs(P.amp_x + P.amp_face_x) + P.amp_face_w/2 + P.face_fit <= ih,
       'amp_x pushes the faceplate rebate into a side wall')
    ok(abs(P.amp_x) + P.amp_w/2 <= ih - P.clr, 'amp_x pushes the board into a side wall')
    ok(P.amp_knob_proj() >= P.knob_min_grip,
       'only %s mm of shaft outside the box — knobs will not grip' % P.amp_knob_proj())
    if P.ctrl_mode == 'holes':
        ok(abs(P.amp_x) + P.ctrl_x0 + P.ctrl_pitch + P.ctrl_bush_d/2 + P.clr + P.ctrl_slack < ih - 1,
           'outer shaft hole hits the side wall')
    for x, y in P.lid_boss_pts(P.amp_h()):
        ok(abs(x) + P.lid_boss_od/2 < ih, 'lid boss runs into a side wall')
    ok(P.lid_boss_x_bot - P.lid_boss_od/2 - 0.6 > P.mp_x + P.mp_w/2 + P.clr + P.mp_wall,
       'MP1584 pocket runs into the bottom-right lid boss notch')
    ok(-P.lid_boss_x_bot + P.lid_boss_od/2 + 0.6 < P.mp_x - P.mp_w/2 - P.clr - P.mp_wall,
       'MP1584 pocket runs into the bottom-left lid boss notch')
    ok(P.plug_zone >= P.mp_l + 2*P.clr + 2*P.mp_wall + 1, 'plug zone shallower than the MP1584 pocket')
    notch_x0 = P.lid_boss_x_bot - P.lid_boss_od/2 - 0.6
    for x, z in P.sled_screw_pts():
        r = P.sled_boss_od/2
        ok(abs(x - P.mp_x) - r >= P.mp_half_w() + 0.5, 'a sled hold-down boss runs into the MP1584 pocket')
        ok(abs(x) + r <= notch_x0 - 0.5 or z + r < P.lid_boss_z0() - 0.6 - 0.5,
           'a sled hold-down boss runs into a lid boss notch')
        ok(P.plug_z0() + r <= z <= P.box_d() - 0.2 - r - 1, 'a sled hold-down boss is off the plug zone')
        ok(P.sled_screw_pilot + 2*1.6 <= P.sled_boss_od, 'sled hold-down boss wall under 1.6 mm')
    mp_half = P.mp_l/2 + P.clr + P.mp_wall
    ok(P.mp_zc() - mp_half >= P.amp_rear_z() and P.mp_zc() + mp_half <= P.box_d() - 0.2,
       'MP1584 pocket leaves the plug zone (mp_dz)')
    ok(abs(abs(P.sleeve_x) - P.lid_boss_x_top) > P.sleeve_od()/2 + P.clr + P.lid_boss_od/2 + 0.5,
       'sleeve hole runs into a top lid boss')
    if P.amp_psw:
        sw_x0 = ih - P.amp_psw_body[0]
        ok(P.amp_psw_cut[0]/2 + P.psw_zc() < P.box_d() - 1
           and P.psw_zc() - P.amp_psw_body[1]/2 > P.plug_z0(),
           'panel switch body leaves the plug zone')
        ok(sw_x0 > P.lid_boss_x_top + P.lid_boss_od/2 + 0.5
           or P.amp_psw_y + P.amp_psw_body[2]/2 < P.lid_boss_pts(P.amp_h())[2][1] - P.lid_boss_od/2,
           'panel switch body hits the top-right lid boss')
        ok(P.amp_psw_y - P.amp_psw_body[2]/2 > P.wall + P.sled_t + P.mp_lip + 1,
           'panel switch body hits the sled')
        ok(sw_x0 > P.amp_x + P.amp_aux_x + P.dac_aux_plug/2 + 0.5
           or P.amp_psw_y - P.amp_psw_body[2]/2 > P.amp_pcb_top() + P.amp_aux_axis + P.dac_aux_plug/2,
           'panel switch body hits the AUX plug')
        ok(P.amp_psw_y + P.amp_psw_cut[1]/2 < P.amp_h() - P.wall - 1
           and P.amp_psw_y - P.amp_psw_cut[1]/2 > P.wall + 1,
           'panel switch cut-out does not fit the side wall')
    ok(P.amp_win_x0() > -(P.peg_x() - P.leg_w/2), 'cable window runs under the left leg')
    ok(P.amp_win_x1() < (P.peg_x() - P.leg_w/2), 'cable window runs under the right leg')
    ok(P.amp_win_y0() > P.lid_boss_pts(P.amp_h())[0][1] + P.screw_clear/2 + 1.5,
       'cable window cuts the bottom lid screws')
    ok(P.amp_win_y1() < P.lid_boss_pts(P.amp_h())[2][1] - P.screw_clear/2 - 1.5,
       'cable window cuts the top lid screws')
    ok(abs(P.amp_x + P.amp_dc_x) + P.amp_dc_plug_d/2 < P.peg_x() - P.leg_w/2,
       'barrel plug body hits a lid leg in the channel')
    for hx, hr in P.amp_holes:
        ok(abs(hx) + P.amp_standoff_od/2 < P.amp_w/2 + 0.01, 'a standoff sits outside the board')
        ok(within(P.amp_bz(hr), P.amp_front_z() + P.amp_face_t + P.amp_standoff_od/2,
                  P.amp_rear_z() - P.amp_standoff_od/2 + 0.01),
           "a standoff sits outside the board's length")

    # ===================== voice box =====================
    ok(P.voice_h >= P.voice_h_min(), 'voice_h too small for the dome — needs %s' % P.voice_h_min())
    ok(P.btn_pos[1] + P.btn_dome_d/2 < P.voice_h - P.front_chamfer - 1, 'dome overhangs the top edge of the face')
    ok(P.btn_pos[1] - P.btn_dome_d/2 > P.front_chamfer + 2, 'dome overhangs the bottom edge of the face')
    ok(abs(P.btn_pos[0]) + P.btn_dome_d/2 < P.box_w/2 - P.front_chamfer - 1,
       'dome overhangs a side edge of the face')
    ok(P.btn_pos[1] - P.bh_collar_od()/2 > P.tray_top() + P.tray_seat + P.pcb_t + P.tray_lip
       or P.bh_deep_z() < P.s3_z0 - 1, 'button holder collides with the devkit pocket')
    ok(P.bh_deep_z() < P.s3_z0 - 1,
       "devkit pocket starts inside the button holder's depth (%s)" % P.bh_deep_z())
    # mic on the TOP face: mic_pos = (x, z)
    ok(P.mic_pos[1] - P.mic_size()[1]/2 > P.bh_deep_z() + 1
       or P.voice_h - P.wall - P.mic_post_h - P.mic_clamp_t > P.btn_pos[1] + P.bh_collar_od()/2 + 1,
       'mic block runs into the button holder')
    ok(P.mic_pos[1] - P.mic_size()[1]/2 > P.front_chamfer + P.wall, 'mic seat runs into the front edge')
    ok(P.mic_pos[1] + P.mic_size()[1]/2 < P.lid_boss_z0() - 1, 'mic block runs into the top lid bosses')
    ok(abs(P.mic_pos[0]) + P.mic_size()[0]/2 < ih, 'mic posts run into a side wall')
    ok(abs(P.btn_pos[0]) + P.btn_pilot_pitch/2 + P.bh_ear_d/2 < ih, 'button holder ears run into a side wall')
    ok(abs(P.s3_x) + P.s3_pocket()[0]/2 < ih - P.clr, 'devkit pocket wider than the tray')
    ok(abs(P.dac_xc()) + P.dac_cav()[0]/2 + P.pocket_wall < ih - P.clr, 'DAC pocket runs off the tray')
    ok(P.dac_dz >= 0, 'dac_dz < 0 pushes the DAC pocket into the devkit pocket')
    ok(abs(P.dac_jack_x() - P.sleeve_x) + P.aux_plug_d/2 <= P.sleeve_id/2 + 2,
       "the DAC's socket is not over the sleeve — the plug's cable cannot drop into it")
    ok(P.dac_socket_z() + P.dac_aux_plug < P.sleeve_zc() + P.sleeve_od()/2,
       'the AUX plug head reaches past the sleeve — move the DAC forward or deepen plug_zone')
    ok(P.dac_z0() + P.dac_cav()[1] + 2*P.pocket_wall < P.lid_boss_z0() - 1
       or abs(P.dac_xc()) + P.dac_cav()[0]/2 + P.pocket_wall < P.lid_boss_x_bot - P.lid_boss_od/2 - 0.6,
       'DAC pocket runs into a lid boss notch')
    ok(abs(P.sleeve_x) + P.sleeve_od()/2 + P.sleeve_flange < P.lid_boss_x_bot - P.lid_boss_od/2 - 0.6,
       'sleeve flange sits over a lid boss notch')
    ok(P.sleeve_zc() - P.sleeve_od()/2 - P.sleeve_flange > P.dac_edge_z(), 'sleeve flange runs under the DAC')
    ok(P.sleeve_zc() + P.sleeve_od()/2 + P.sleeve_flange < P.box_d() - 0.5, 'sleeve flange hits the lid')
    ok(P.tray_seat >= P.board_pin_h + 0.5, 'pin relief would cut through the pocket floor')
    ok(P.sleeve_engage < P.peg_drop - 1, 'sleeve still engaged in the amp top when the pegs are free')

    # ===================== button =====================
    ok(P.btn_wall_id() > P.sw_diag() + 2*P.clr, 'plunger bore does not swallow the switch diagonal')
    ok(P.btn_post_d < P.sw_plunger_d, 'post overhangs the switch plunger')
    ok(P.btn_preload < P.sw_travel - 0.3, 'preload eats the switch travel')
    ok(P.btn_post_h() > 0, 'post has no length — check the switch height')
    ok(P.btn_flange_d < P.btn_dome_d - 2*P.btn_rim_lift, "flange is wider than the dome's flat underside")
    ok(P.btn_recess_d() > P.btn_flange_d, 'recess smaller than the flange')
    ok(P.btn_edge_drop() < P.btn_rim_gap(),
       "a press at the dome's edge can ground it on the face before the switch closes (%.2f vs %.2f)"
       " — raise btn_flange_t or bh_guide_h" % (P.btn_edge_drop(), P.btn_rim_gap()))
    ok(P.btn_wall_z1() + P.btn_stroke() < P.bh_relief_z1() - 0.2, 'plunger end bottoms on the collar floor')
    ok(P.sw_top_z() > P.btn_ceil_z() + P.btn_stroke() + 0.2, 'switch body hits the plunger ceiling at full press')

    # ===================== wall plate / hanging =====================
    ok(P.stack_gap < P.peg_drop, 'amp box can lift off its pegs with the voice box in place')
    ok(P.lock_gap < P.peg_drop, 'voice box can lift off its pegs under the lock bracket')
    ok(P.stack_gap > P.sleeve_engage, 'sleeve longer than the gap it crosses')
    ok(P.plate_t - P.kh_lip >= P.peg_len() - P.kh_lip - P.kh_clr + 0.5, 'peg head deeper than the keyhole cavity')
    ok(P.kh_head_d() < P.leg_w + 2*P.plate_margin - 2, 'keyhole wider than the plate edge allows')
    ok(P.peg_x() + P.kh_head_d()/2 < P.plate_w()/2 - 1, 'keyhole breaks out of the plate edge')
    for ys in (P.peg_y_amp, P.peg_y_voice):
        ok(ys[1] - ys[0] > P.peg_drop + P.kh_head_d() + 2, 'keyholes overlap')
    ok(max(P.peg_y_amp) + P.peg_drop + P.kh_head_d()/2 < P.amp_h() + P.stack_gap,
       'amp keyhole runs into the voice box zone')
    ok(P.voice_z0() + max(P.peg_y_voice) + P.peg_drop + P.kh_head_d()/2 < P.plate_h() - 1,
       'voice keyhole runs off the plate top')
    ok(P.header_w()/2 < P.peg_x() - P.leg_w/2, 'lock header collides with the legs')
    ok(P.header_d() - P.plate_t >= P.insert_m3_d + 3, 'header too thin for the lock inserts')
    ok(P.header_d() <= P.lid_back_y() - 0.3, 'header reaches the voice lid')
    ok(P.lid_back_y() - 0.5 - P.header_d() <= 0.5, 'lock bracket overhangs the header — it should rest on it')
    for x, _ in P.ws_pts():
        ok(abs(x) + P.ws_head_d/2 < P.peg_x() - P.leg_w/2, 'wall screw under a leg')
    ok(P.plate_h() <= 250 and P.plate_w() <= 250, 'wall plate exceeds the A1 bed (256 x 256)')
    ok(P.box_d() + P.lid_t <= 250, 'box exceeds the A1 bed')

    board_screws(c)
    electronics(c)
    return c.failures


def board_screws(c):
    """a mounting screw's head must sit on bare board, not under a part on the same board"""
    hd = P.amp_screw_head[0]/2 + 0.5
    zk = elec.by_name()['ZK-502MT']
    for hx, hr in P.amp_holes:
        x, z = P.amp_x + hx, P.amp_bz(hr)
        for p in zk.prims:
            if p.name in ('PCB', 'screw head', 'faceplate') or p.outside:
                continue
            lo, hi = p.aabb()
            if lo[1] > P.amp_pcb_top() + 0.5:
                continue
            c.ok(not (lo[0] < x + hd and hi[0] > x - hd and lo[2] < z + hd and hi[2] > z - hd),
                 'amp board screw at (%g, %g) lands under the %s' % (x, z, p.name))


def electronics(c):
    """Parts vs parts, parts vs cavity, parts vs printed obstacles."""
    comps = elec.components()
    ih = P.inner_w()/2
    for where in ('amp', 'voice'):
        h = P.amp_h() if where == 'amp' else P.voice_h
        mine = [k for k in comps if k.where == where]
        cavity = ((-ih, P.wall, P.wall), (ih, h - P.wall, P.box_d()))
        obst = elec.obstacles(where)
        for k in mine:
            for p in k.prims:
                if p.soft:
                    continue
                bb = p.aabb()
                if not p.outside:
                    lo, hi = bb
                    inside = all(cavity[0][i] - 0.01 <= lo[i] and hi[i] <= cavity[1][i] + 0.01
                                 for i in range(3))
                    c.ok(inside, '%s / %s leaves the %s box cavity' % (k.name, p.name, where))
                allowed = elec.OBSTACLE_MATES.get(k.name, set())
                for oname, olo, ohi in obst:
                    if oname not in allowed:
                        c.ok(not _overlap(bb, (olo, ohi)),
                             '%s / %s runs into the %s' % (k.name, p.name, oname))
        for i, a in enumerate(mine):
            for b in mine[i + 1:]:
                if b.name in a.mates or a.name in b.mates:
                    continue
                hit = _first_clash(a, b)
                if hit:
                    c.ok(False, '%s / %s overlaps %s / %s' % (a.name, hit[0], b.name, hit[1]))


def _first_clash(a, b):
    for p in a.prims:
        if p.soft:
            continue
        for q in b.prims:
            if not q.soft and _overlap(p.aabb(), q.aabb()):
                return (p.name, q.name)
    return None


def report():
    """the ECHO lines asserts.scad printed"""
    return [
        'ENVELOPE  amp %g x %g x %g  voice %g x %g x %g  plate %g x %g x %g  front face %g mm off '
        'the wall, total height %g' % (P.box_w, P.amp_h(), P.box_d() + P.lid_t, P.box_w, P.voice_h,
                                       P.box_d() + P.lid_t, P.plate_w(), P.plate_h(), P.plate_t,
                                       P.front_y(), P.plate_h() + P.lock_t),
        'BUTTON    crown %g proud, rim gap %g, edge drop %.3f, post %g, holder reaches %g'
        % (P.btn_proud(), P.btn_rim_gap(), P.btn_edge_drop(), P.btn_post_h(), P.bh_deep_z()),
        'AMP       PCB underside at y %g, envelope top %g, faceplate y %g..%g, knob shaft outside %g,'
        ' plug zone z %g..%g' % (P.amp_pcb_y(), P.amp_env_top(), P.amp_face_y(),
                                  P.amp_face_y() + P.amp_face_h, P.amp_knob_proj(), P.plug_z0(),
                                  P.box_d()),
        'PARTS     %d electronic components, %d primitives'
        % (len(elec.components()), sum(len(k.prims) for k in elec.components())),
    ]


def main():
    failures = run_checks()
    for line in report():
        print('  ' + line)
    if failures:
        print('\nFAIL — %d design check(s):' % len(failures))
        for f in failures:
            print('  - ' + f)
        return 1
    print('\nOK — all design checks pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
