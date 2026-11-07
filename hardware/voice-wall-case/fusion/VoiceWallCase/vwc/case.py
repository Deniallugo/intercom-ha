"""The two boxes: shells, rear lids, the amp's board sled, the voice tray, the sleeve.

Port of ``modules/lib.scad``, ``modules/amp_box.scad`` and ``modules/voice_box.scad``. All of it
is authored in BOX-LOCAL coordinates — x across, y up from the box's bottom outer face, z into
the box from its front outer face — which is also the shells' print orientation (front face
down). Each cut runs along one axis:
  'z'  through the front face          (button, mic, the amp's faceplate window)
  'y'  through the top or the floor    (vents, terminal access, the sleeve)
  'x'  through a side wall             (vents, the panel switch)

Feature order is the OpenSCAD one: union every additive shape, then cut every opening, so no
cut depends on a face an earlier feature made.
"""

from . import params as P
from . import xf
from .build import (aabox, cone, loft_rect_circle, prism_circle, prism_poly, prism_rect,
                    prism_rrect, rrect_loft_ax)

# a part authored in box-local that prints lying flat (the sled, the tray):
# OpenSCAD's flat() = rotate([90, 0, 0]) translate([0, -wall, 0])
FLAT = xf.mul(xf.Rx(90), xf.T(0, -P.wall, 0))


# ---- shared -----------------------------------------------------------------------------
def box_shell(part, h, name):
    """Open-backed shell: front face z 0..wall, walls to box_d(), open at the rear. The front
    edge is a 45 deg chamfer — a loft between the inset front outline and the full one — because
    the shell prints front-face-down and a fillet would start horizontal on the bed."""
    w, r, c, d = P.box_w, P.box_r, P.front_chamfer, P.box_d()
    mid = (0, h/2)
    rrect_loft_ax(part, 'z', 0, c, (w - 2*c, h - 2*c, max(0.5, r - c)), (w, h, r), c=mid, name=name)
    walls = prism_rrect(part, 'z', mid, w, h, r, c, d, name='walls')
    part.union(name, [walls])
    cav = prism_rrect(part, 'z', mid, w - 2*P.wall, h - 2*P.wall, max(0.5, r - P.wall),
                      P.wall, d + 1, name='cavity')
    return part.cut(name, [cav])


def lid_bosses(part, h):
    """M3 insert bosses on the top and bottom walls at the rear rim. Each one tapers at 45 deg
    toward the front into its wall, so it prints unsupported front-face-down."""
    d = P.box_d()
    adds, cuts = [], []
    for x, y in P.lid_boss_pts(h):
        up = y > h/2
        wall_y = y + P.lid_boss_od/2 + 0.5 if up else y - P.lid_boss_od/2 - 0.5
        z_disc = d - P.lid_boss_len
        adds.append(loft_rect_circle(part, 'z', (x, wall_y), (P.lid_boss_od, 0.5),
                                     z_disc - P.lid_boss_taper(), (x, y), P.lid_boss_od, z_disc,
                                     name='boss taper'))
        adds.append(prism_circle(part, 'z', (x, y), P.lid_boss_od, z_disc, d, name='lid boss'))
        # Web from the wall to the boss axis, full boss width and length: on its own the
        # boss meets the wall along a 1 mm sliver, and an M3 torqued into the insert would
        # snap it off. The web's front edge is the same 45 deg as the taper, so it still
        # prints front-face-down without support.
        face = P.wall if not up else h - P.wall
        f0 = face - 0.5 if not up else face + 0.5       # sunk into the wall so the Join fuses
        dy = abs(y - f0)
        adds.append(prism_poly(part, 'x', [(f0, z_disc - dy), (f0, d), (y, d), (y, z_disc)],
                               x - P.lid_boss_od/2, x + P.lid_boss_od/2, name='boss web'))
        cuts.append(prism_circle(part, 'z', (x, y), P.insert_m3_d, d - P.insert_m3_h - 1, d + 0.1,
                                 name='insert bore'))
    return adds, cuts


def slot(part, axis, c, length, along, a0, a1, name='vent'):
    """one vent slot (a stadium), `length` long along the in-plane axis named by `along`"""
    w = P.vent_w
    size = (length, w) if along == 0 else (w, length)
    return prism_rrect(part, axis, c, size[0], size[1], w/2, a0, a1, name=name)


def top_span(h):    return (h - P.wall - 0.1, h + 0.1)
def floor_span():   return (-0.1, P.wall + 0.1)


def side_span(sx):
    x0 = P.box_w/2 - P.wall - 0.1 if sx > 0 else -P.box_w/2 - 0.1
    return (x0, x0 + P.wall + 0.2)


# ---- amplifier box ----------------------------------------------------------------------
AMP_SHELL = 'amp shell'


def amp_front_cuts(part):
    if P.ctrl_mode == 'faceplate':
        c = P.face_c()
        return [
            # the window — smaller than the faceplate by the lip on every side
            prism_rect(part, 'z', c, (P.amp_face_w - 2*P.face_lip, P.amp_face_h - 2*P.face_lip),
                       -0.1, P.wall + 0.1, name='faceplate window'),
            # the rebate the faceplate nests in, from inside
            prism_rect(part, 'z', c, (P.amp_face_w + 2*P.face_fit, P.amp_face_h + 2*P.face_fit),
                       P.wall - P.face_rebate, P.wall + 0.1, name='faceplate rebate'),
        ]
    out = [prism_circle(part, 'z', (P.amp_x + P.ctrl_x0 + i*P.ctrl_pitch, P.amp_pcb_y() + P.ctrl_axis),
                        P.ctrl_bush_d + 2*P.clr + 2*P.ctrl_slack, -0.1, P.wall + 0.1, name='shaft hole')
           for i in (-1, 0, 1)]
    out.append(prism_circle(part, 'z', (P.amp_x + P.ctrl_led[0], P.amp_pcb_y() + P.ctrl_led[1]),
                            P.ctrl_led_d, -0.1, P.wall + 0.1, name='LED hole'))
    return out


def amp_shell(part):
    h = P.amp_h()
    box_shell(part, h, AMP_SHELL)
    b_add, b_cut = lid_bosses(part, h)
    part.union(AMP_SHELL, b_add)
    t0, t1 = top_span(h)
    cuts = amp_front_cuts(part) + b_cut
    # top: pass-through for the sleeve, over the plug zone
    cuts.append(prism_circle(part, 'y', (P.sleeve_x, P.sleeve_zc()), P.sleeve_od() + 2*P.clr, t0, t1,
                             name='sleeve hole'))
    # top: exhaust over the heatsink
    hx, hz, n, ln = P.amp_x + P.amp_hs[0], P.amp_bz(P.amp_hs[1]), 5, P.amp_hs[3] + 12
    for i in range(n):
        cuts.append(slot(part, 'y', (hx + (i - (n - 1)/2)*P.vent_pitch, hz), ln, 1, t0, t1,
                         name='top vent'))
    # top: screwdriver access to the barrier-block screws
    if P.term_access:
        for x in P.term_xs():
            cuts.append(prism_circle(part, 'y', (x, P.amp_bz(P.amp_term_screw_from_rear)),
                                     P.term_access_d, t0, t1, name='terminal access'))
    # floor: the sled hold-down screws, countersunk from underneath
    f0, f1 = floor_span()
    sink = (P.sled_screw_cs_d - P.screw_clear)/2
    for c in P.sled_screw_pts():
        cuts.append(prism_circle(part, 'y', c, P.screw_clear, f0, f1, name='hold-down hole'))
        cuts.append(cone(part, 'y', c, P.sled_screw_cs_d + 0.2, P.screw_clear, -0.1, sink,
                         name='hold-down countersink'))
    # sides: two rows of slots high on both walls
    for sx in (-1, 1):
        for r in (0, 1):
            cuts.append(slot(part, 'x', (h - P.wall - 4 - r*P.vent_pitch, P.amp_front_z() + 40), 50, 1,
                             *side_span(sx), name='side vent'))
    # +x side: the panel power switch, in the plug zone
    if P.amp_psw:
        c = (P.amp_psw_y, P.psw_zc())
        if P.amp_psw_shape == 'rect':
            cuts.append(prism_rect(part, 'x', c, (P.amp_psw_cut[1], P.amp_psw_cut[0]), *side_span(1),
                                   name='power switch cut-out'))
        else:
            cuts.append(prism_circle(part, 'x', c, P.amp_psw_round_d, *side_span(1),
                                     name='power switch hole'))
    return part.cut(AMP_SHELL, cuts)


# ---- rear lids ----------------------------------------------------------------------------
def peg(part, x, y, z0):
    """Neck, 45 deg cone out to the head, short head — prints upward off the leg's end."""
    neck = P.kh_lip + P.kh_clr
    cone_h = (P.peg_head_d - P.peg_neck_d)/2
    return [prism_circle(part, 'z', (x, y), P.peg_neck_d, z0, z0 + neck + 0.01, name='peg neck'),
            cone(part, 'z', (x, y), P.peg_neck_d, P.peg_head_d, z0 + neck, z0 + neck + cone_h,
                 name='peg cone'),
            # sunk 0.01 into the cone so the Join fuses solid rather than face-to-face
            prism_circle(part, 'z', (x, y), P.peg_head_d, z0 + neck + cone_h - 0.01,
                         z0 + neck + cone_h + P.peg_head_h, name='peg head')]


def box_lid(part, h, peg_ys, name, extra_cuts=None):
    """Lid plate + two legs (the cable channel) + four pegs. Lid frame = box-local shifted back
    by box_d(): inner face on z = 0, legs growing +z, which is also how it prints."""
    mid = (0, h/2)
    prism_rrect(part, 'z', mid, P.box_w, h, P.box_r, 0, P.lid_t, name=name)
    z0, z1 = P.lid_t - 0.01, P.lid_t + P.chan_d
    adds = []
    for sx, leg in ((-1, 'leg left'), (1, 'leg right')):
        # One leg at a time: the two never touch, and a Join of bodies that do not touch leaves
        # them separate in Fusion, so intersecting "both" would round only one. Each is cut to
        # the lid's outline so its outer edges follow the rounded corners.
        aabox(part, (sx*P.peg_x() - P.leg_w/2, 0, z0), (sx*P.peg_x() + P.leg_w/2, h, z1), name=leg)
        part.intersect(leg, [prism_rrect(part, 'z', mid, P.box_w, h, P.box_r, z0, z1, name='outline')])
        adds.append(part.body(leg))
    for sx in (-1, 1):
        for py in peg_ys:
            adds += peg(part, sx*P.peg_x(), py, z1 - 0.01)
    part.union(name, adds)
    cuts = [prism_circle(part, 'z', (x, y), P.screw_clear, -0.1, P.lid_t + 0.1, name='lid screw')
            for x, y in P.lid_boss_pts(h)]
    return part.cut(name, cuts + (extra_cuts(part) if extra_cuts else []))


AMP_LID = 'amp lid'


def amp_lid(part):
    """...with the cable window: barrel plug and speaker leads out into the channel."""
    def window(p):
        return [aabox(p, (P.amp_win_x0(), P.amp_win_y0(), -0.1),
                      (P.amp_win_x1(), P.amp_win_y1(), P.lid_t + 0.1), name='cable window')]
    return box_lid(part, P.amp_h(), P.peg_y_amp, AMP_LID, window)


# ---- amp sled -----------------------------------------------------------------------------
AMP_SLED = 'amp sled'


def sled_plate(part, t, name):
    """Full inside depth, front wall to lid, so the lid holds it in z. Notched round the
    bottom lid bosses and their tapers."""
    z0, z1 = P.wall + 0.2, P.box_d() - 0.2
    w = P.inner_w() - 2*P.clr
    aabox(part, (-w/2, P.wall, z0), (w/2, P.wall + t, z1), name=name)
    notches = []
    for sx in (-1, 1):
        x0 = sx*P.lid_boss_x_bot - P.lid_boss_od/2 - 0.6
        zn = P.lid_boss_z0() - 0.6
        notches.append(aabox(part, (x0, P.wall - 0.1, zn), (x0 + P.lid_boss_od + 1.2, P.wall + t + 0.1,
                                                            zn + P.box_d()), name='boss notch'))
    return part.cut(name, notches)


def mp_pocket(part):
    """MP1584 pocket on the sled's rear, open at both short ends for the IN and OUT wires.

    Returns (ring, cuts): the solid ring is joined to the sled FIRST and the cavity and wire
    exits are cut from the sled afterwards. Cutting them from the ring on its own splits it in
    two (the exits run right across it), and Fusion makes each lump its own body — the second
    half was left floating beside the sled instead of joined to it."""
    cav = (P.mp_w + 2*P.clr, P.mp_l + 2*P.clr)
    o = (cav[0] + 2*P.mp_wall, cav[1] + 2*P.mp_wall)
    top = P.wall + P.sled_t
    y0 = top - 0.01                       # sunk 0.01 into the sled, so the Join fuses it
    y1 = y0 + P.mp_lip
    x, z = P.mp_x, P.mp_zc()
    ring = aabox(part, (x - o[0]/2, y0, z - o[1]/2), (x + o[0]/2, y1, z + o[1]/2), name='mp pocket')
    # from the sled's top face up, so the sled under the board is not touched
    cuts = [aabox(part, (x - cav[0]/2, top, z - cav[1]/2), (x + cav[0]/2, y1 + 0.1, z + cav[1]/2),
                  name='mp cavity'),
            aabox(part, (x - o[0]/2 - 0.1, top, z - 3), (x + o[0]/2 + 0.1, y1 + 0.1, z + 3),
                  name='mp wire exits')]
    return ring, cuts


def amp_sled(part):
    """Board sled: standoffs on the (photo-estimated) holes, the MP1584 pocket at the rear.
    Authored in box-local, then turned flat for printing. Everything solid is joined before
    anything is cut, so the sled stays one body."""
    sled_plate(part, P.sled_t, AMP_SLED)
    y0 = P.wall + P.sled_t - 0.01
    adds, cuts = [], []
    for hx, hr in P.amp_holes:
        c = (P.amp_x + hx, P.amp_bz(hr))
        adds.append(prism_circle(part, 'y', c, P.amp_standoff_od, y0, y0 + P.amp_standoff_len() + 0.01,
                                 name='standoff'))
        # from the sled's top face up: the OpenSCAD drilled the standoff only, never the sled
        cuts.append(prism_circle(part, 'y', c, P.amp_hole_pilot, P.wall + P.sled_t,
                                 y0 + P.amp_standoff_len() + 0.11, name='standoff pilot'))
    for c in P.sled_screw_pts():
        adds.append(prism_circle(part, 'y', c, P.sled_boss_od, y0, y0 + P.sled_boss_h + 0.01,
                                 name='hold-down boss'))
        # blind from the sled's underside (on the bed when printed), stops 1 mm under the top
        cuts.append(prism_circle(part, 'y', c, P.sled_screw_pilot, P.wall - 0.1,
                                 P.wall + P.sled_t + P.sled_boss_h - 1, name='hold-down pilot'))
    ring, mp_cuts = mp_pocket(part)
    part.union(AMP_SLED, adds + [ring])
    part.cut(AMP_SLED, cuts + mp_cuts)
    return part.move_bodies(FLAT)


# ---- voice box ----------------------------------------------------------------------------
VOICE_SHELL = 'voice shell'


def button_cut(part):
    x, y = P.btn_pos
    return [prism_circle(part, 'z', (x, y), P.btn_bore_d(), -0.1, P.wall + 0.1, name='button bore'),
            prism_circle(part, 'z', (x, y), P.btn_recess_d(), -0.1, P.btn_recess_depth,
                         name='flange recess')]


def button_pilots(part):
    """blind M2 pilots from the inner face — a through hole would be two dots beside the dome"""
    x, y = P.btn_pos
    return [prism_circle(part, 'z', (x + sx*P.btn_pilot_pitch/2, y), P.board_screw_pilot,
                         P.wall - P.btn_pilot_depth, P.wall + 0.1, name='holder pilot') for sx in (-1, 1)]


def mic_seat(part):
    """Board recess, gasket seat and one short port — on the TOP face. Depth d below the top
    outer face is y = h - d; (x, z) on the face is mic_pos."""
    x, z = P.mic_pos
    h = P.voice_h
    zg = P.wall - P.mic_seat_depth - P.mic_gasket_depth        # gasket seat floor, as a depth
    return [prism_rect(part, 'y', (x, z), (P.mic_board_w + 2*P.clr, P.mic_board_l + 2*P.clr),
                       h - P.wall - 0.1, h - (P.wall - P.mic_seat_depth), name='mic board recess'),
            prism_circle(part, 'y', (x, z), P.mic_gasket_d, h - zg - P.mic_gasket_depth - 0.01, h - zg,
                         name='gasket seat'),
            prism_circle(part, 'y', (x, z), P.mic_hole_d, h - zg - 0.1, h + 0.1, name='mic port')]


def mic_posts(part):
    """two M2 posts hanging from the top's inner face, flanking the seat along x"""
    x, z = P.mic_pos
    h = P.voice_h
    adds, cuts = [], []
    for sx in (-1, 1):
        c = (x + sx*P.mic_post_pitch/2, z)
        adds.append(prism_circle(part, 'y', c, P.mic_post_od, h - P.wall - P.mic_post_h, h - P.wall + 0.01,
                                 name='mic post'))
        cuts.append(prism_circle(part, 'y', c, P.board_screw_pilot, h - P.wall - P.mic_post_h - 0.1,
                                 h - P.wall, name='mic post pilot'))
    return adds, cuts


def voice_shell(part):
    h = P.voice_h
    box_shell(part, h, VOICE_SHELL)
    b_add, b_cut = lid_bosses(part, h)
    m_add, m_cut = mic_posts(part)
    part.union(VOICE_SHELL, b_add + m_add)
    cuts = button_cut(part) + button_pilots(part) + mic_seat(part) + b_cut + m_cut
    # floor: the sleeve down into the amp box
    cuts.append(prism_circle(part, 'y', (P.sleeve_x, P.sleeve_zc()), P.sleeve_od() + 2*P.clr,
                             *floor_span(), name='sleeve hole'))
    # sides: slots alongside the devkit, low (intake) and high (exhaust)
    for sx in (-1, 1):
        for yy in (P.tray_top() + 9, h - P.wall - 6):
            cuts.append(slot(part, 'x', (yy, P.s3_zc()), P.s3_pocket()[1] - 4, 1, *side_span(sx),
                             name='side vent'))
    return part.cut(VOICE_SHELL, cuts)


VOICE_LID = 'voice lid'


def voice_lid(part):
    return box_lid(part, P.voice_h, P.peg_y_voice, VOICE_LID)


# ---- voice tray -----------------------------------------------------------------------------
VOICE_TRAY = 'voice tray'


def pocket(part, cav, c, relief, name):
    """Friction pocket standing on the tray; its floor tray_seat proud so pin-tail reliefs can
    sink into it. `relief` is [(x, z, w, l)] relative to the pocket centre."""
    o = (cav[0] + 2*P.pocket_wall, cav[1] + 2*P.pocket_wall)
    hgt = P.tray_seat + P.pcb_t + P.tray_lip
    y0 = P.tray_top() - 0.01
    aabox(part, (c[0] - o[0]/2, y0, c[1] - o[1]/2), (c[0] + o[0]/2, y0 + hgt, c[1] + o[1]/2), name=name)
    cuts = [aabox(part, (c[0] - cav[0]/2, y0 + P.tray_seat, c[1] - cav[1]/2),
                  (c[0] + cav[0]/2, y0 + 2*hgt, c[1] + cav[1]/2), name='board cavity')]
    for rx, rz, rw, rl in relief:
        cuts.append(aabox(part, (c[0] + rx - rw/2, y0 + P.tray_seat - P.board_pin_h, c[1] + rz - rl/2),
                          (c[0] + rx + rw/2, y0 + P.tray_seat + 0.1, c[1] + rz + rl/2), name='pin relief'))
    return part.cut(name, cuts)


def voice_tray(part):
    """Devkit across x, the DAC behind it with its socket facing the rear over the sleeve."""
    sled_plate(part, P.tray_t, VOICE_TRAY)
    cav = P.s3_cav()
    s3 = pocket(part, cav, (P.s3_x, P.s3_zc()),
                [(0, s*(cav[1]/2 - P.pin_row_w/2 - 0.5), cav[0] - 1, P.pin_row_w) for s in (-1, 1)],
                'devkit pocket')
    dcav = P.dac_cav()
    dac = pocket(part, dcav, (P.dac_xc(), P.dac_zc()), [(0, 0, dcav[0] - 5, dcav[1] - 5)], 'DAC pocket')
    part.union(VOICE_TRAY, [s3, dac])
    jx = P.dac_jack_x()
    y0 = P.tray_top() + P.tray_seat - 0.5
    z0 = P.dac_edge_z() - 0.5
    part.cut(VOICE_TRAY, [
        # the DAC pocket's rear wall, notched where the socket overhangs it
        aabox(part, (jx - P.dac_jack_w/2 - P.clr, y0, z0),
              (jx + P.dac_jack_w/2 + P.clr, y0 + 20, z0 + P.pocket_wall + P.board_clr + 2),
              name='socket notch'),
        prism_circle(part, 'y', (P.sleeve_x, P.sleeve_zc()), P.sleeve_od() + 2*P.clr, P.wall - 0.1,
                     P.wall + P.tray_t + 0.1, name='sleeve hole')])
    return part.move_bodies(FLAT)


# ---- pass-through sleeve -------------------------------------------------------------------
SLEEVE = 'sleeve'


def sleeve(part):
    """Flange rests on the tray, tube drops through the voice floor, across the stack gap and
    sleeve_engage into the amp top. Own frame: flange on z = 0, tube growing +z."""
    prism_circle(part, 'z', (0, 0), P.sleeve_od() + 2*P.sleeve_flange, 0, 1.6, name=SLEEVE)
    part.union(SLEEVE, [prism_circle(part, 'z', (0, 0), P.sleeve_od(), 0, 1.6 + P.sleeve_len(), name='tube')])
    return part.cut(SLEEVE, [
        prism_circle(part, 'z', (0, 0), P.sleeve_id, -0.1, P.sleeve_len() + 2, name='bore'),
        # 0.6 entry chamfer so a wire jacket cannot catch
        cone(part, 'z', (0, 0), P.sleeve_id + 1.4, P.sleeve_id, -0.1, 0.6, name='entry chamfer')])


# ---- coupons --------------------------------------------------------------------------------
def coupon(part, which):
    """The real shell, sliced: whatever it tests, it tests the actual geometry.
    amp:   the front wall (faceplate window and rebate).
    voice: the front wall (button bore, recess, pilots) AND the strip of top wall over the mic
           seat and posts — one L-shaped print."""
    if which == 'amp':
        amp_shell(part)
        name, h = AMP_SHELL, P.amp_h()
        slab = aabox(part, (-P.box_w, -1, -1), (P.box_w, h + 1, P.wall + 3), name='slice')
    else:
        voice_shell(part)
        name, h = VOICE_SHELL, P.voice_h
        slab = aabox(part, (-P.box_w, -1, -1), (P.box_w, h + 1, P.wall + 3), name='slice')
        top = aabox(part, (-P.box_w, h - P.wall - P.mic_post_h - 1, -1),
                    (P.box_w, h + 1, P.mic_pos[1] + P.mic_size()[1]/2 + 2), name='top slice')
        part.union('slice', [top])
    part.intersect(name, [slab])
    part.body(name).name = 'coupon ' + which
    return part
