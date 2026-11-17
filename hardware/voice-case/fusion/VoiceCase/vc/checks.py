"""Design checks (port of ``tests/asserts.scad``): the constraints a buildable case
must meet. Each failure names the value it needs. Plain Python; ``VoiceCase.py`` runs
them before building and refuses a case that fails.
"""

import math
import sys

try:
    from . import params as P
except ImportError:                        # run directly, not as a package
    import params as P


class Checks:
    def __init__(self):
        self.failures = []

    def ok(self, condition, message):
        if not condition:
            self.failures.append(message)
        return condition

    # ---- collision helpers for plan-mounted features ----
    def clears_bosses(self, c, sz, name):
        for cb in P.boss_centres():
            self.ok(P.aabb_clear(c, sz, cb, (P.boss_od, P.boss_od)),
                    '%s clashes a corner boss' % name)

    def inside_cavity(self, c, sz, name):
        self.ok(abs(c[0]) + sz[0]/2 <= P.inner_half_x(), '%s off the cavity width' % name)
        self.ok(abs(c[1]) + sz[1]/2 <= P.inner_half_y(), '%s off the cavity depth' % name)


def run_checks():
    """Return a list of failure messages — empty means the design is self-consistent."""
    c = Checks()
    ok = c.ok

    # ===== shell / envelope =====
    ok(P.plan_x >= P.plan_x_min(),
       'plan_x too small for the boards side by side — needs at least %s' % P.plan_x_min())
    ok(P.plan_y >= P.plan_y_min(),
       'plan_y too small — needs at least %s (devkit length %s, DAC vs bosses %s)'
       % (P.plan_y_min(), P.plan_y_from_depth(), P.plan_y_from_boss_dac()))
    ok(abs(P.s3_cavity_x1() - (P.dac_cavity_x0() - P.shared_wall)) < 0.001,
       'the two beds no longer share one wall — s3_pos_x has been typed in again')
    ok(P.shared_wall >= P.pocket_wall,
       'the shared wall is thinner than a normal pocket wall, and it is retaining two boards')
    ok(P.s3_boss_margin > 0,
       'devkit pocket touches the corner bosses — s3_boss_margin must be positive')
    ok(P.s3_pos_x() - P.s3_pocket_f()[0]/2
       >= -P.boss_cx() + P.boss_od/2 + P.s3_boss_margin - 0.001,
       'devkit pocket eats the -x corner bosses — plan_x must be at least %s' % P.plan_x_min())
    ok(P.cavity_depth >= P.cavity_min(),
       'cavity_depth too shallow for the devkit — needs at least %s (bare %s, mic %s, '
       'button holder %s), giving outer height %s'
       % (P.cavity_min(), P.cavity_from_bare(), P.cavity_from_mic(),
          P.cavity_from_button(), P.cavity_min() + 2*P.wall))
    ok(P.outer_d() == P.top_depth() + P.wall,
       'base must be a FLAT plate: outer depth = top_depth + wall')
    ok(P.chamfer < P.radius, 'top chamfer must be smaller than the corner radius')
    ok(0 < P.chamfer < P.top_depth(), 'top chamfer out of range')
    ok(P.flat_half_x() > 0 and P.flat_half_y() > 0,
       'top chamfer swallowed the whole top face')
    ok(0 < P.reg_h < P.cavity_depth, 'registration lip out of range')
    ok(0 < P.reg_t < P.wall, 'registration lip must be thinner than the wall')

    # ===== corner bosses =====
    ok(P.boss_od >= P.insert_m3_d + 3, 'corner boss too thin around the heat-set insert')
    ok(P.insert_m3_d > P.screw_clear,
       'heat-set bore must be wider than the screw clearance')
    ok(P.screw_cbore_d > P.screw_clear,
       'counterbore must be wider than the screw clearance')
    ok(P.screw_cbore_h < P.wall, 'counterbore must not cut through the base plate')
    ok(P.boss_cx() + P.boss_od/2 <= P.inner_half_x()
       and P.boss_cy() + P.boss_od/2 <= P.inner_half_y(),
       'corner bosses run into the side walls')
    # Independent of plan: the boss sits (radius - boss_inset)*sqrt(2) off the corner arc centre.
    boss_corner_reach = math.sqrt(2)*(P.radius - P.boss_inset) + P.boss_od/2
    lip_corner_r_in = P.radius - P.wall - P.clr - P.reg_t
    ok(P.boss_inset < P.radius,
       'boss_inset past the corner radius — the diagonal corner checks below stop applying')
    ok(boss_corner_reach <= P.radius - P.wall,
       'corner boss breaks out through the rounded corner — boss_inset must be at least %s'
       % (P.radius - (P.radius - P.wall - P.boss_od/2)/math.sqrt(2)))
    # Also clear the base plate's register lip, or the plate won't close.
    ok(boss_corner_reach <= lip_corner_r_in,
       'corner boss blocks the register lip — the lip cannot slip inside. boss reaches %s '
       'but the lip\'s inner corner is at %s. boss_inset must be at least %s'
       % (boss_corner_reach, lip_corner_r_in,
          P.radius - (lip_corner_r_in - P.boss_od/2)/math.sqrt(2)))

    # ===== plan layout =====
    c.inside_cavity(P.s3_pocket_c(), P.s3_pocket_f(), 'S3 pocket')
    c.inside_cavity(P.dac_pocket_c(), P.dac_pocket_f(), 'DAC pocket')
    c.inside_cavity(P.mic_pos, P.mic_size(), 'mic seat+posts')
    c.clears_bosses(P.s3_pocket_c(), P.s3_pocket_f(), 'S3 pocket')
    c.clears_bosses(P.dac_pocket_c(), P.dac_pocket_f(), 'DAC pocket')
    c.clears_bosses(P.mic_pos, P.mic_size(), 'mic seat+posts')
    # The pocket blocks overlap by design; check the cavities, exactly shared_wall apart.
    gap = P.dac_cavity_x0() - P.s3_cavity_x1()
    ok(gap >= P.shared_wall - 0.001,
       'the two board cavities are closer than the wall between them — only %s mm for a '
       '%s mm wall' % (gap, P.shared_wall))
    ok(gap <= P.shared_wall + 0.001,
       'the two beds are not sharing a wall any more — there is a gap between the pockets')

    ok(abs(P.btn_pos[0]) + P.btn_recess_d()/2 <= P.flat_half_x(),
       'button recess runs onto the chamfer (x)')
    ok(abs(P.btn_pos[1]) + P.btn_recess_d()/2 <= P.flat_half_y(),
       'button recess runs onto the chamfer (y)')
    ok(math.hypot(P.btn_pos[0] - P.mic_pos[0], P.btn_pos[1] - P.mic_pos[1])
       >= P.btn_cap_d/2 + P.mic_hole_d/2 + 2,
       'button flange runs over the mic port on the top face')
    ok(abs(P.mic_pos[0]) + P.mic_size()[0]/2 <= P.flat_half_x(),
       'mic seat runs onto the chamfer (x)')
    ok(abs(P.mic_pos[1]) + P.mic_size()[1]/2 <= P.flat_half_y(),
       'mic seat runs onto the chamfer (y)')

    # ===== plate boards vs top-face parts: z gaps, only where they overlap in plan =====
    if not P.aabb_clear(P.dac_pocket_c(), P.dac_pocket_f(), P.mic_pos, P.mic_size()):
        ok(P.dac_top_z() > P.wall + P.mic_post_h + P.mic_clamp_t + 2,
           'DAC socket collides with the mic clamp')
    ok(P.dac_top_z() > P.wall + 2, 'DAC socket reaches the top face — deepen cavity_depth')
    ok(P.s3_top_z() > P.wall + P.mic_post_h + P.pcb_t + 2,
       'mic board reaches into the devkit — deepen cavity_depth')
    ok(P.s3_pcb_top_z() > 0 and P.s3_top_z() > P.wall,
       'devkit stack does not fit the cavity at all')

    # ===== rear wall: devkit USB-C window =====
    ok(P.s3_usb_z0() >= P.wall, 'USB window runs into the top face — lower the devkit')
    ok(P.s3_usb_z1() <= P.top_depth() - 1.5,
       'USB window breaks the base rim — raise s3_seat_h or trim more off its bottom')
    ok(P.s3_usb_h_eff() >= 2.8,
       'USB window trimmed to %s — a USB-C plug is ~2.6 mm thick and will not pass'
       % P.s3_usb_h_eff())
    ok(P.s3_usb_trim_top >= 0 and P.s3_usb_trim_bottom >= 0,
       'USB window trims must not be negative')
    ok(P.s3_usb_w() >= P.s3_usb_ports*P.s3_usb_port_w
       + (P.s3_usb_ports - 1)*P.s3_usb_gap,
       'USB window narrower than the ports it serves — no plug would fit either one')
    ok(P.s3_usb_w() <= P.s3_l + 2*P.s3_board_clr,
       'USB window wider than the devkit — it would open past the board')
    ok(P.s3_rear_notch() >= P.s3_usb_w(),
       'rear stops narrower apart than the USB window — they would sit across the ports. '
       's3_rear_notch() is %s and the window is %s' % (P.s3_rear_notch(), P.s3_usb_w()))
    ok(P.s3_rear_notch() <= P.s3_l + 2*P.s3_board_clr - 2,
       'rear stops have no width left — the notch is %s in a cavity of %s. s3_usb_slop() '
       'tracks s3_board_clr, so this means the pocket itself is too narrow'
       % (P.s3_rear_notch(), P.s3_l + 2*P.s3_board_clr))
    ok(P.s3_pocket_y1() > P.s3_cy() + P.s3_w/2,
       'devkit pocket has no +y wall to locate the board')
    ok(P.usb_setback() <= 6.5,
       'USB receptacle sits too deep for a plug to reach — setback is %s. Thin '
       'usb_panel_t, or move the board back toward the wall' % P.usb_setback())
    ok(1.5 <= P.usb_panel_t < P.wall,
       'usb_panel_t out of range — it must actually be thinner than the wall, and at '
       'least 1.5 to survive a plug')
    ok(P.s3_usb_cz_eff() + P.s3_usb_h_eff()/2 + P.usb_cb_margin <= P.top_depth() - 1.5,
       'thinned USB panel runs into the base rim — it reaches %s and the rim starts at %s'
       % (P.s3_usb_cz_eff() + P.s3_usb_h_eff()/2 + P.usb_cb_margin, P.top_depth() - 1.5))
    ok(P.s3_usb_cz_eff() - P.s3_usb_h_eff()/2 - P.usb_cb_margin >= P.wall,
       'thinned USB panel runs into the top face')
    ok(abs(P.s3_pos_x()) + P.s3_usb_w()/2 + P.usb_cb_margin <= P.plan_x/2 - P.radius,
       'thinned USB panel runs off the flat part of the rear wall into a rounded corner')
    for cb in P.boss_centres():
        ok(abs(P.s3_pos_x() - cb[0])
           >= (P.s3_usb_w() + 2*P.usb_cb_margin + P.boss_od)/2,
           'thinned USB panel cuts into a corner boss')

    # ===== +x side wall: the DAC's own 3.5 mm socket =====
    ok(P.dac_jack_w > 0 and P.dac_jack_h > 0, 'DAC socket body geometry')
    ok(abs(P.dac_jack_end) == 1, 'dac_jack_end picks an end: -1 or +1')
    ok(P.dac_jack_inset >= 0 and P.dac_jack_inset + P.dac_jack_w <= P.dac_l,
       'DAC socket does not fit along the board edge — check dac_jack_w/dac_jack_inset '
       'vs dac_l')
    ok(abs(P.dac_jack_off()) + P.dac_jack_w/2 <= P.dac_l/2,
       'DAC socket falls off the board edge')
    ok(abs(P.dac_jack_off()) >= P.dac_l/2 - P.dac_jack_w - 1,
       'DAC socket offset is not at the board end any more — is dac_jack_off() still derived?')
    ok(P.dac_jack_end > 0,
       'socket must sit at the board\'s FRONT end for the hole to clear the vents')
    ok(P.dac_jack_y() + P.dac_jack_w/2 <= P.dac_pos_y() + P.dac_l/2,
       'socket runs past the board\'s front edge')
    ok(P.dac_jack_y() - P.dac_jack_w/2 > P.dac_pos_y(),
       'socket is not at the far END of the bed — it has drifted back toward the middle')
    ok(abs(P.dac_jack_off()) + P.dac_jack_w/2 <= P.dac_l/2 + P.board_clr,
       'socket body runs into the DAC pocket\'s end wall')
    ok(0 < P.dac_jack_axis < P.dac_jack_h,
       'the barrel axis must lie inside the socket body')
    ok(0.8 <= P.jack_panel_t <= 1.5,
       'jack_panel_t out of range — thicker and a plug will not seat, thinner and the '
       'panel tears')
    ok(P.jack_panel_t < P.wall, 'the socket panel must actually be THINNER than the wall')
    ok(P.jack_hole_d > 4.5, 'plug hole must clear a 3.5 mm plug and its tolerance')
    ok(P.jack_hole_d + 2*P.jack_lead_in <= P.dac_jack_w + 2*P.clr,
       'plug hole + chamfer is wider than the counterbore behind it — the panel would vanish')
    ok(0 < P.jack_lead_in < P.jack_panel_t, 'socket lead-in chamfer out of range')
    ok(P.dac_socket_setback > 0,
       'socket face must sit behind the thinned panel, not in it')
    ok(P.dac_pcb_edge_x() + P.dac_jack_overhang <= P.outer_w()/2 - P.jack_panel_t,
       'socket protrudes through the outer skin — the base plate could not be assembled')
    ok(P.dac_socket_z0() - P.clr >= P.wall + 1,
       'socket counterbore runs into the top face')
    ok(P.dac_socket_z1() + P.clr <= P.top_depth() - P.jack_cb_rim_margin,
       'socket counterbore runs past the shell\'s bottom rim — dac_seat_h must be at '
       'least %s' % (P.dac_jack_h + P.clr + P.jack_cb_rim_margin))

    # ---- socket recess in the pocket floor (board is component-side DOWN) ----
    under = (P.plate_inner_z() + P.wall) - P.dac_recess_z1()
    ok(under >= 1.5,
       'too little material under the socket — only %s mm of floor + plate' % under)
    ok(0 < P.dac_jack_depth < P.dac_w,
       'socket body reaches further inboard than the board is wide — check dac_jack_depth')
    ok(P.dac_recess_x0() > P.dac_cx() - P.dac_w/2,
       'socket recess undercuts the whole board — nothing left to seat on')
    ok(P.dac_recess_z1() < P.plate_inner_z() + P.wall - 0.8,
       'socket recess breaks through the bottom of the plate — it reaches %s and the '
       'outer face is at %s' % (P.dac_recess_z1(), P.plate_inner_z() + P.wall))
    ok(P.dac_top_z() > P.wall + 2,
       'DAC pin tails reach the top face — deepen cavity_depth')
    for cb in P.boss_centres():
        ok(abs(P.dac_jack_y() - cb[1]) >= (P.dac_jack_w + 2*P.clr + P.boss_od)/2,
           'DAC socket cutout runs into a corner boss')
    ok(abs(P.dac_jack_y()) + P.dac_jack_w/2 + P.clr + P.jack_lead_in <= P.inner_half_y(),
       'DAC socket cutout runs off the side wall')

    # ===== button module: shell bore, cap, holder =====
    ok(P.btn_cap_d > P.btn_bore_d(),
       'cap flange must be wider than the bore or it falls in')
    ok(P.btn_recess_d() >= P.btn_cap_d + 2*P.clr, 'cap recess must clear the flange')
    ok(P.btn_recess_depth < P.wall, 'cap recess must not cut through the top face')
    ok(P.btn_pilot_depth < P.wall - 0.6,
       'holder pilots must stay blind — they would show through the top face')
    ok(P.btn_pilot_depth > 1.5, 'holder pilots too shallow for an M2 to hold')
    ok(P.btn_pilot_pitch/2 - P.board_screw_pilot/2 >= P.btn_recess_d()/2 + 1,
       'holder pilots too close to the recess wall — needs btn_pilot_pitch of at least %s'
       % (P.btn_recess_d() + P.board_screw_pilot + 2))

    # -- cap guide and snap --
    btn_guide_len = (P.wall - P.btn_recess_depth) + P.bh_guide_h
    btn_lean = P.btn_cap_d/2 * (2*P.btn_guide_clr)/btn_guide_len
    ok(btn_guide_len >= 6,
       'cap guide is only %s mm long on a %s mm flange — raise bh_guide_h'
       % (btn_guide_len, P.btn_cap_d))
    ok(btn_lean <= 1.2,
       'cap flange can lean %s mm — tighten btn_guide_clr or lengthen bh_guide_h' % btn_lean)
    ok(P.btn_wall_t >= 1.2, 'cap body too thin to be a bearing surface')
    ok(P.btn_wall_id() > P.btn_post_d + 2,
       'cap body bore is barely wider than its own post')
    ok(P.btn_slits >= 4, 'too few slits for a body this size to collapse through the bore')
    ok(P.btn_slit_w < P.btn_wall_od*math.pi/(2*P.btn_slits),
       'slits eat more than half the body')
    ok(P.btn_slit_z0 > P.wall,
       'cap slits cross the shell bore — raise btn_slit_z0 above `wall`')
    ok(P.btn_slit_z0 < P.bh_catch_z(),
       'cap slits start below the catch — the lip could not collapse')
    ok(P.btn_post_d < P.sw_plunger_d, 'cap post is wider than the plunger it presses')
    ok(P.btn_post_h() > 0, 'cap post has no length — check the z chain')
    ok(P.btn_proud() > 0, 'cap sits below the top surface — nothing to press')

    # -- travel and preload: positive preload pins the cap; negative rattles --
    ok(P.btn_preload > 0,
       'no preload — the cap would rest on the plunger with its lip clear of the catch, '
       'and rattle')
    ok(P.btn_preload <= P.sw_travel/2,
       'preload is %s of only %s mm of switch travel — it would sit close to permanently '
       'pressed. Keep it under %s' % (P.btn_preload, P.sw_travel, P.sw_travel/2))
    ok(P.btn_stroke() >= 0.3,
       'only %s mm of stroke left after the preload — raise sw_travel or lower btn_preload'
       % P.btn_stroke())
    ok(P.btn_face_gap > P.btn_stroke() + 0.5,
       'flange bottoms on the recess floor before the switch closes — btn_face_gap must '
       'exceed the %s mm stroke' % P.btn_stroke())
    ok(P.btn_face_gap <= P.btn_recess_depth,
       'flange stands proud of the top face at rest — raise btn_recess_depth to match '
       'btn_face_gap')
    ok(P.btn_recess_depth < P.wall - 1.0,
       'recess leaves under 1 mm of top face for the flange to land on')
    ok(P.bh_relief_h() >= P.btn_lip_t + P.btn_stroke(),
       'lip relief is shorter than the lip plus its travel — the cap jams before it actuates')
    # Both rooms reduce to btn_lip_slack; at 0.3 a printed cap seized.
    room_body = P.bh_relief_z1() - (P.btn_wall_z1() + P.btn_stroke())
    ok(room_body >= 0.6,
       'cap body bottoms on the collar floor mid-stroke — only %s mm of room. Raise '
       'btn_lip_slack' % room_body)
    room_lip = P.bh_relief_h() - P.btn_lip_t - P.btn_stroke()
    ok(room_lip >= 0.6,
       'lip bottoms in its relief before the stroke finishes — only %s mm of room. Raise '
       'btn_lip_slack' % room_lip)
    # -- the cap's bore must swallow the switch's diagonal --
    ok(P.btn_wall_id() >= P.sw_diag() + 2*P.clr,
       'cap\'s body bore is %s and the switch\'s diagonal is %s — btn_wall_od must be at '
       'least %s' % (P.btn_wall_id(), P.sw_diag(),
                     P.sw_diag() + 2*P.clr + 2*P.btn_wall_t))
    ok(P.bh_relief_d() >= P.sw_diag() + 2*P.clr,
       'switch\'s diagonal does not clear the holder\'s relief bore (%s)' % P.bh_relief_d())

    # -- printability: the cap prints dome-down, so every step is 45 deg or tangent --
    ok(P.btn_flare_h() >= (P.btn_cap_d - P.btn_wall_od)/2 - 0.001,
       'flange flare is steeper than 45 deg — it would print as an overhang')
    ok(P.btn_dome_r > P.btn_wall_t,
       'top fillet is thinner than the wall — no inner radius left')
    ok(P.btn_top_d() > P.btn_post_d + 4,
       'top fillet has eaten the flat the post roots into')
    ok(P.btn_dome_h > P.btn_dome_r + P.btn_flare_h() + P.btn_flange_t,
       'cap is too short for its own fillet, flare and flange')

    # -- the catch --
    ok(P.btn_lip_od() > P.bh_bore_d(), 'retention lip does not catch on the holder')
    ok((P.btn_lip_od() - P.bh_bore_d())/2 >= 0.3,
       'lip catches on only %s mm of shoulder — raise btn_lip_over'
       % ((P.btn_lip_od() - P.bh_bore_d())/2))
    ok(P.btn_lip_od() > P.btn_bore_d(),
       'lip passes the shell bore freely — the cap would only be held by the holder')
    ok(P.bh_relief_d() > P.btn_lip_od(),
       'no radial room for the lip in the holder\'s relief')
    ok(P.bh_relief_h() >= P.btn_lip_t + 0.2, 'lip relief is shorter than the lip')
    # The holder sits on two M2s in clearance holes, so its bore must be looser.
    ok(P.bh_guide_clr > P.btn_guide_clr,
       'holder bore is as tight as the shell\'s — it would pinch the cap off axis')
    ok(P.bh_guide_clr - P.btn_guide_clr >= (P.bh_screw_clear - P.screw_m2_d)/2,
       'holder bore does not allow for its own mounting slop — needs bh_guide_clr of at '
       'least %s' % (P.btn_guide_clr + (P.bh_screw_clear - P.screw_m2_d)/2))

    # -- holder: the switch on the floor, and its four pins through it --
    ok(P.sw_plunger_h > 0 and P.plunger_z() < P.sw_top_z(),
       'plunger does not stand proud of the body — the post could never reach it')
    ok(P.btn_post_tip_z() > P.plunger_z(),
       'cap post stops short of the plunger — the cap would rest on it and rattle at the lip')
    ok(abs((P.btn_post_tip_z() - P.plunger_z()) - P.btn_preload) < 0.001,
       'post over-travel does not match btn_preload — the z chain has been broken')
    ok(P.plunger_z() > P.btn_ceil_z() + P.btn_wall_t,
       'switch stands so tall its plunger reaches the cap\'s own ceiling (%s)'
       % P.plunger_z())
    # Above the straight bore the dome closes to ~the switch diagonal.
    ok(P.sw_top_z() > P.btn_flare_top_z() + P.btn_stroke() + 1,
       'switch body reaches up into the cap\'s dome, where the bore narrows to %s against '
       'a %s mm diagonal — its top is at %s'
       % (P.btn_top_d(), P.sw_diag(), P.sw_top_z()))
    ok(P.sw_body_h() > 0,
       'sw_plunger_h (%s) is larger than the whole switch height (%s)'
       % (P.sw_plunger_h, P.sw_h))
    ok(P.sw_pin_axis in (0, 1),
       'sw_pin_axis picks which pair of sides has the pins')
    ok(P.sw_pin_win > 1.5,
       'pin windows too small to clear a tactile\'s legs and their solder')
    ok(P.sw_pin_out >= 0,
       'sw_pin_out is how far the pins stand OUT from the body — it cannot be negative')
    ok(P.sw_pin_slack > 0.5,
       'pin slots too short to be a range — they are back to guessing a position')
    ok(P.sw_pin_a_lo() <= P.sw_body/2,
       'pin slots start %s mm OUTSIDE the body\'s face — a pin flush with the side would '
       'miss them' % (P.sw_pin_a_lo() - P.sw_body/2))
    ok(P.sw_pin_gap > P.sw_pin_win,
       'the two pins on one side are closer together than their own windows are wide')
    ok(P.sw_seat_area() >= 0.4*P.sw_body*P.sw_body,
       'pin windows have eaten the floor the switch stands on — only %s of %s mm2 left'
       % (P.sw_seat_area(), P.sw_body*P.sw_body))
    for p in P.sw_pin_pos():
        win = P.sw_pin_win_xy()
        ok(math.hypot(abs(p[0]) + win[0]/2, abs(p[1]) + win[1]/2) < P.bh_relief_d()/2,
           'pin slot at %s reaches the collar wall — it would breach the relief bore' % (p,))
        ok(abs(abs(p[0]) - P.btn_pilot_pitch/2) > (win[0] + P.bh_screw_cbore_d)/2,
           'pin slot at %s runs into the holder\'s own screw counterbores' % (p,))
    # ---- locating ribs: must clear the cap and be fused to the floor ----
    if P.sw_locate_t > 0:
        ok(P.sw_locate_max() <= P.btn_wall_id()/2 - P.clr,
           'locating ribs reach %s from the axis and the cap\'s bore is %s — shorten '
           'sw_locate_len or thin sw_locate_t'
           % (P.sw_locate_max(), P.btn_wall_id()/2))
        ok(P.sw_locate_r0() > P.sw_body/2,
           'locating ribs are inside the switch\'s own footprint — it would sit on them')
        ok(0 < P.sw_locate_clr <= 1.0,
           'sw_locate_clr out of range — the ribs either pinch the switch or do not locate it')
        ok(P.sw_locate_len_pin + P.sw_pin_win + 0.5 <= P.sw_pin_gap,
           'rib on a pinned side is %s long and only %s of gap is clear between that '
           'side\'s two pin slots'
           % (P.sw_locate_len_pin, P.sw_pin_gap - P.sw_pin_win))
        ok(P.sw_locate_len_pin > 1.0, 'rib on a pinned side is too short to locate anything')
        ok(P.sw_locate_len/2 <= P.sw_pin_a_lo(),
           'long rib reaches the pin slots on the neighbouring side — keep sw_locate_len '
           'under %s' % (2*P.sw_pin_a_lo()))
        ok(P.sw_locate_h > P.pcb_t,
           'locating ribs too short to catch the switch body\'s side')
        ok(P.bh_rib_embed > P.bh_relief_eps,
           'locating ribs must reach INTO the collar floor — bh_rib_embed %s against a '
           'relief that oversteps it by %s' % (P.bh_rib_embed, P.bh_relief_eps))
        ok(P.bh_rib_embed < P.bh_floor_t - 1.0,
           'locating ribs sunk %s into a %s floor — leave the pins something to pass '
           'through' % (P.bh_rib_embed, P.bh_floor_t))
    ok(P.sw_pin_len > P.bh_floor_t,
       'pins do not reach through the floor — nothing to solder to under the holder')
    ok(P.bh_floor_t >= 1.2, 'collar floor too thin to stand the switch on')
    ok(P.bh_screw_clear > P.board_screw_pilot,
       'holder holes must clear the M2 they pass')
    ok(P.bh_screw_cbore_d > P.bh_screw_clear
       and P.bh_screw_cbore_h < P.bh_z1() - P.bh_relief_z1(),
       'screw counterbore must be wider than the hole and stay inside the floor')
    ok(P.bh_ear_d >= P.bh_screw_cbore_d + 2,
       'screw post too thin around its own counterbore')
    ok(P.btn_pilot_pitch/2 - P.bh_ear_d/2 < P.bh_collar_od()/2 + 2,
       'screw posts stand too far off the collar for the web to reach')
    ok(P.btn_pilot_pitch/2 + P.bh_ear_d/2 > P.bh_collar_od()/2,
       'screw posts are buried in the collar — they would open into the guide bore')
    ok(P.bh_collar_od() >= P.bh_relief_d() + 2*P.bh_wall,
       'collar wall thinner than bh_wall at the relief')

    # -- the assembled module must fit the box and clear what is under it --
    # Measured at the pin tips (bh_deep_z), the deepest point.
    ok(P.bh_deep_z() < P.top_depth() - 2, 'button module reaches the base plate')
    holder_f = (P.bh_plate_w(), P.bh_plate_l())
    if not P.aabb_clear(P.btn_pos, holder_f, P.s3_pocket_c(), P.s3_pocket_f()):
        ok(P.s3_top_z() > P.bh_deep_z() + 2,
           'button module collides with the devkit — its pins reach %s and the devkit\'s '
           'stack starts at %s' % (P.bh_deep_z(), P.s3_top_z()))
    if not P.aabb_clear(P.btn_pos, holder_f, P.dac_pocket_c(), P.dac_pocket_f()):
        ok(P.dac_top_z() > P.bh_deep_z() + 2, 'button module collides with the DAC')
    c.clears_bosses(P.btn_pos, holder_f, 'button holder collar')
    c.inside_cavity(P.btn_pos, holder_f, 'button holder collar')
    ok(P.aabb_clear(P.btn_pos, holder_f, P.mic_pos, P.mic_size()),
       'button holder collar overlaps the mic seat')
    ok(abs(P.mic_pos[1]) - P.mic_size()[1]/2 >= P.btn_bore_d()/2,
       'shell bore breaks into the mic seat on the inner face')

    # ===== microphone =====
    ok(P.mic_seat_depth + P.mic_gasket_depth < P.wall,
       'mic seat + gasket seat cut through the top face')
    ok(P.mic_gasket_d > P.mic_hole_d, 'mic gasket seat must be wider than the port')
    ok(P.mic_gasket_d <= P.mic_board_l,
       'mic gasket seat wider than the board it seals against')
    ok(P.mic_post_pitch/2 - P.mic_post_od/2 >= (P.mic_board_w + 2*P.clr)/2,
       'mic posts intrude into the board recess')
    ok(P.mic_clamp_pad_h() > 0,
       'mic clamp pad has no height — the posts are shorter than the seated board')
    ok(P.mic_clamp_pad < P.mic_board_w and P.mic_clamp_pad <= P.mic_board_l,
       'mic clamp pad overhangs the board it presses')
    ok(P.mic_screw_clear > P.board_screw_pilot,
       'clamp holes must clear the M2 they pass')
    ok(P.mic_clamp_len() >= P.mic_post_pitch + P.mic_post_od,
       'clamp bar does not span both posts')
    ok(P.mic_clamp_w <= P.mic_post_od + 4, 'clamp bar wider than the posts can support')
    ok(P.mic_clamp_w >= P.mic_screw_clear + 1.5,
       'clamp bar too narrow for the M2 holes it carries — needs at least %s'
       % (P.mic_screw_clear + 1.5))
    ok(P.mic_clamp_t >= 1.0, 'clamp bar too thin to press without bowing')
    ok(P.wall + P.mic_post_h + P.mic_clamp_t < P.s3_top_z(),
       'mic clamp collides with the devkit')

    # ===== base plate: pockets, vents, feet, screws =====
    ok(abs(P.s3_pos_x()) + P.s3_pocket_f()[0]/2 <= P.lip_inner_half_x(),
       'devkit pocket fouls the register lip (x)')
    ok(max(abs(P.s3_pocket_y0()), abs(P.s3_pocket_y1())) <= P.lip_outer_half_y(),
       'devkit pocket runs past the register lip\'s outer face — the plate would not drop in')
    front_wall_t = P.s3_front_wall_t()
    ok(front_wall_t >= P.reg_t - 0.001,
       'devkit pocket\'s front wall is thinner than the register lip it stands on — only '
       '%s mm' % front_wall_t)
    ok(P.dac_pocket_x1() <= P.lip_inner_half_x(),
       'DAC pocket crosses the register lip')
    ok(abs(P.dac_pos_y()) + P.dac_pocket_f()[1]/2 <= P.lip_inner_half_y(),
       'DAC pocket fouls the register lip (y)')
    ok(P.dac_pocket_x0() < P.dac_pocket_x1(),
       'DAC pocket has no length — the board is too long for the plate')
    for cb in P.boss_centres():
        ok(P.aabb_clear(P.s3_pocket_c(), P.s3_pocket_f(), cb,
                        (P.screw_cbore_d, P.screw_cbore_d)),
           'devkit pocket clashes a base-plate screw')
        ok(P.aabb_clear(P.dac_pocket_c(), P.dac_pocket_f(), cb,
                        (P.screw_cbore_d, P.screw_cbore_d)),
           'DAC pocket clashes a base-plate screw')
    ok(P.s3_seat_h > 0 and P.s3_lip > 0,
       'devkit pocket needs a floor and a retaining lip')
    # ---- devkit fit and the retention tab ----
    ok(P.s3_board_clr > 0,
       'devkit pocket has no clearance at all — the board would not go in')
    ok(P.s3_board_clr <= P.board_clr,
       'the devkit pocket is looser than the DAC\'s, which has its socket to locate it — '
       'that is backwards')
    ok(P.s3_board_clr <= 2.0,
       's3_board_clr is large enough that the board is not in a pocket so much as a tray')
    ok(P.s3_board_clr > 0.2,
       'no y travel for the devkit — it would be pinched between the stops and the front wall')
    ok(P.s3_front_gap > 0,
       'the cavity ends at the board\'s front edge — no y clearance in front of it at all')
    ok(P.s3_front_wall_t() >= P.reg_t - 0.001,
       'devkit pocket\'s front wall is thinner than the register lip it stands on — only '
       '%s mm' % P.s3_front_wall_t())
    ok(0 < P.s3_relief_front_setback < P.s3_front_gap + P.pin_row_w,
       'devkit relief setback does not leave the front wall a base to stand on')
    if P.s3_tab_cover > 0:
        ok(P.s3_tab_h > 0, 'retention tab has no height above its ramp')
        ok(abs(P.s3_wall_top() - P.s3_tab_top()) < 0.001,
           'retention tab is no longer flush with the top of the pocket wall — wall top %s, '
           'tab top %s' % (P.s3_wall_top(), P.s3_tab_top()))
        ok(P.s3_tab_z0() > P.s3_seat_h + 0.2,
           'retention tab\'s ramp reaches the pocket floor — s3_lip is %s and the ramp '
           'starts at %s against a floor at %s'
           % (P.s3_lip, P.s3_tab_z0(), P.s3_seat_h))
        # Tab is anchored to the wall top; the bite is only bounded so the board still goes under.
        ok(P.s3_tab_bite() < P.pcb_t/2,
           'tab reaches more than half way down the PCB\'s edge (bite %s) — the board would '
           'not go under it' % P.s3_tab_bite())
        ok(0.6 < P.s3_tab_cover < P.s3_w/8,
           'retention tab covers either too little of the board\'s front edge to hold it, '
           'or too much of that end')
        ok(0 < P.s3_tab_w <= P.s3_l - 8,
           'retention tab is wide enough to reach the devkit\'s header rows — keep '
           's3_tab_w under %s' % (P.s3_l - 8))
        ok(not P.s3_rear_stops or P.s3_rear_stop_h <= P.pcb_t,
           'rear stops stand %s mm above the PCB\'s top face — the board is then captured '
           'in z at both ends and cannot be assembled' % (P.s3_rear_stop_h - P.pcb_t))
        ok(not P.s3_rear_stops or P.s3_rear_stop_h >= P.pcb_t/2,
           'rear stops are too short to catch the board\'s edge — it would ride over them')
    ok(P.dac_seat_h > 0 and P.dac_lip > 0,
       'DAC pocket needs a floor and a retaining lip')
    # ---- pocket wall heights ----
    s3_wall_top_z = P.plate_inner_z() - (P.s3_seat_h + P.pcb_t + P.s3_lip)
    dac_wall_top_z = P.plate_inner_z() - (P.dac_seat_h + P.pcb_t + P.dac_lip)
    ok(s3_wall_top_z > P.wall + P.mic_post_h + P.mic_clamp_t + 2,
       'devkit pocket wall is tall enough to hit the mic clamp — reduce s3_lip')
    ok(s3_wall_top_z > P.bh_deep_z() + 2
       or abs(P.s3_pos_x()) + P.s3_pocket_f()[0]/2 - P.pocket_wall > P.bh_plate_w()/2,
       'devkit pocket wall is tall enough to hit the button holder — reduce s3_lip')
    ok(dac_wall_top_z > P.wall + 2,
       'DAC pocket wall reaches the top face — reduce dac_lip')
    ok(P.dac_lip >= P.pcb_t + 1, 'dac_lip does not properly capture the PCB edge')
    ok(P.dac_lip <= P.pcb_t + P.board_pin_h + 3,
       'dac_lip runs far past the pin tails — nothing above %s does work'
       % (P.pcb_t + P.board_pin_h))

    # ---- pin relief ----
    ok(P.board_pin_h > 0,
       'no pin relief: the board would seat on its own pin tails')
    ok(P.pin_relief_setback > 0, 'pin relief undercuts the pocket wall base')
    ok(P.pin_relief_setback + 1 < min(P.board_clr, P.s3_board_clr) + 2.5,
       'pin relief setback pushes the channel out from under the header row')
    ok(P.board_pin_h + P.clr <= P.s3_seat_h - 0.8,
       'pin relief would leave too little devkit pocket floor — raise s3_seat_h to at '
       'least %s' % (P.board_pin_h + P.clr + 0.8))
    ok(P.board_pin_h + P.clr <= P.dac_seat_h - 0.8,
       'pin relief would leave too little DAC pocket floor — raise dac_seat_h to at '
       'least %s' % (P.board_pin_h + P.clr + 0.8))
    ok(2*P.pin_row_w < P.s3_l + 2*P.s3_board_clr - 4,
       'pin relief strips swallow the devkit\'s central land')
    ok(P.pin_land > 1 and 2*P.pin_land < P.s3_w,
       'devkit pin relief leaves no end land')
    ok(2*P.dac_relief_w() < P.dac_l + 2*P.board_clr - 4,
       'DAC relief channel swallows its central land')
    ok(P.dac_recess_w() >= P.dac_jack_w,
       'socket recess is narrower than the socket — the socket would foul the floor '
       'beside it')
    ok(P.pin_land > 1 and 2*P.pin_land < P.dac_w, 'DAC pin relief leaves no end land')
    ok(P.dac_w + 2*P.board_clr - 2*P.pin_land > 0,
       'DAC relief strips have no width left')
    dac_relief_xhi = P.dac_pocket_x1()
    dac_relief_xlo = P.dac_cx() - (P.dac_w/2 + P.board_clr - P.pin_land)
    dac_relief_y_rear = P.dac_pos_y() - ((P.dac_l + 2*P.board_clr)/2
                                         - P.pin_relief_setback - P.dac_relief_w()/2)
    ok(dac_relief_y_rear + P.dac_relief_w()/2
       < P.dac_jack_y() - (P.dac_jack_w/2 + P.clr),
       'rear relief channel runs into the socket recess — the two would nest')
    ok(dac_relief_xhi >= P.dac_pocket_x1() - 0.001,
       'DAC relief stops short of the floor\'s open edge — it would be a dead end')
    ok(dac_relief_xhi <= P.lip_inner_half_x() + 0.001,
       'DAC relief runs past the floor into the register lip')
    ok(dac_relief_xlo > P.dac_pocket_x0() + P.pocket_wall,
       'DAC relief no longer has a land at its left end — it would breach the left wall')

    for v in P.vent_rects:
        vc, vs = (v[0], v[1]), (v[2], v[3])
        ok(P.aabb_clear(vc, vs, P.s3_pocket_c(), P.s3_pocket_f()),
           'vent at %s opens under the devkit pocket' % (vc,))
        ok(P.aabb_clear(vc, vs, P.dac_pocket_c(), P.dac_pocket_f()),
           'vent at %s opens under the DAC pocket' % (vc,))
        for cb in P.boss_centres():
            ok(P.aabb_clear(vc, vs, cb, (P.screw_cbore_d, P.screw_cbore_d)),
               'vent at %s runs into a screw counterbore' % (vc,))
        for f in P.foot_positions:
            ok(P.aabb_clear(vc, vs, f, (P.foot_d, P.foot_d)),
               'vent at %s breaks into a foot recess' % (vc,))
        ok(abs(v[0]) + v[2]/2 <= P.lip_inner_half_x()
           and abs(v[1]) + v[3]/2 <= P.lip_inner_half_y(),
           'vent at %s runs into the register lip' % (vc,))
    # foot_positions is empty by default; these guard re-adding feet.
    for f in P.foot_positions:
        ok(abs(f[0]) + P.foot_d/2 <= P.plan_x/2 - 2
           and abs(f[1]) + P.foot_d/2 <= P.plan_y/2 - 2,
           'foot recess runs off the plate edge')
        ok(P.foot_depth < P.wall - 1, 'foot recess leaves too little plate under it')
        for cb in P.boss_centres():
            ok(math.hypot(f[0] - cb[0], f[1] - cb[1])
               >= (P.foot_d + P.screw_cbore_d)/2,
               'foot recess overlaps a screw counterbore')
        ok(P.foot_depth + P.s3_seat_h < P.wall
           or P.aabb_clear(f, (P.foot_d, P.foot_d), P.s3_pocket_c(), P.s3_pocket_f()),
           'foot recess would break through the devkit pocket floor')
        ok(P.foot_depth + P.dac_seat_h < P.wall
           or P.aabb_clear(f, (P.foot_d, P.foot_d), P.dac_pocket_c(), P.dac_pocket_f()),
           'foot recess would break through the DAC pocket floor')

    return c.failures


def summary():
    """The derived floors, in the form the README quotes them."""
    return '\n'.join([
        'plan_x     = %-6s min %-6s  boss line -> devkit -> shared wall -> DAC -> socket'
        % (P.plan_x, round(P.plan_x_min(), 2)),
        'plan_y     = %-6s min %-6s  (devkit length %s | DAC vs bosses %s)'
        % (P.plan_y, round(P.plan_y_min(), 2), round(P.plan_y_from_depth(), 2),
           round(P.plan_y_from_boss_dac(), 2)),
        'cavity     = %-6s min %-6s  (bare %s | mic %s | button holder %s)'
        % (P.cavity_depth, round(P.cavity_min(), 2), round(P.cavity_from_bare(), 2),
           round(P.cavity_from_mic(), 2), round(P.cavity_from_button(), 2)),
        'outer      = %s x %s x %s mm (%s over the button)'
        % (P.outer_w(), P.outer_h(), P.outer_d(), round(P.outer_d() + P.btn_proud(), 2)),
        'button     = cap dome %s, bore %s, holder reaches %s down'
        % (P.btn_cap_d, round(P.btn_bore_d(), 2), round(P.bh_deep_z(), 2)),
        'devkit     = pocket %s x %s at x %s, USB setback %s of 6.5'
        % (round(P.s3_pocket_f()[0], 2), round(P.s3_pocket_f()[1], 2),
           round(P.s3_pos_x(), 2), round(P.usb_setback(), 2)),
    ])


def main():
    failures = run_checks()
    print(summary())
    print()
    if failures:
        print('FAIL — %d design check(s):' % len(failures))
        for f in failures:
            print('  * %s' % f)
        return 1
    print('OK — all design checks pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
