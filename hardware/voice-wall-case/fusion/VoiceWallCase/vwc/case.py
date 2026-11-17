"""The printed case: tray, panel, the button's switch bridge, and test coupons.

  tray    back plate + top, bottom and sides; screwed to the wall, every board on it. The amp's
          standoffs in the middle; the devkit pocket on one side; on the other the DAC seat (top)
          and the MP1584 pocket (bottom); in
          the top the knob holes, vents and the windows the panel's hooks snap into; in the
          bottom the DC plug hole, the speaker holes, the mic seat and grille, the devkit's USB-C
          window, intake vents and the panel's two screws; in the plate two keyholes behind the amp,
          one locking screw under it, and the cable knock-outs. Authored in box-local B, turned to print back face down.
  panel   the flat front: flexure button and bridge feet, knob names, the locating lip, two snap
          hooks and two screw bosses on its back. Authored in B, which is its print frame.
  bridge  the bar behind the button that carries the tactile switch, screwed to two feet.

Board seats are drawn in their tray frame (params docstring), then MOVED into place and joined.
Anything a seat's own cut would split in two (the MP1584 ring and its wire exits) is joined whole
first and cut from the tray afterwards — Fusion makes each lump of a split body a body of its
own, and only one of them would join.
"""

import math

from . import params as P
from . import xf
from .build import (aabox, cone, prism_circle, prism_poly, prism_rect, prism_rrect, prism_sector,
                    rrect_loft_ax, text_tools)

TRAY = 'tray'
PANEL = 'panel'
BRIDGE = 'switch bridge'


def slot(part, axis, c, length, along, a0, a1, name='vent'):
    """one vent slot (a stadium), `length` long along in-plane axis `along` (0 or 1)"""
    w = P.vent_w
    size = (length, w) if along == 0 else (w, length)
    return prism_rrect(part, axis, c, size[0], size[1], w/2, a0, a1, name=name)


# ---- board seats, tray frame ----------------------------------------------------------
def devkit_pocket(part):
    """voice-case's friction pocket: walls round the board, its floor tray_seat proud so the
    header pin tails sink into reliefs; the -x end wall notched for a USB-C plug"""
    cav, o, hgt = P.s3_cav(), P.s3_pocket(), P.s3_pocket_h()
    name = 'devkit pocket'
    aabox(part, (-o[0]/2, -0.01, -o[1]/2), (o[0]/2, hgt, o[1]/2), name=name)
    cuts = [aabox(part, (-cav[0]/2, P.tray_seat, -cav[1]/2), (cav[0]/2, hgt + 1, cav[1]/2),
                  name='board cavity')]
    for s in (-1, 1):
        rz = s*(cav[1]/2 - P.pin_row_w/2 - 0.5)
        cuts.append(aabox(part, (-cav[0]/2 + 0.5, P.tray_seat - P.board_pin_h, rz - P.pin_row_w/2),
                          (cav[0]/2 - 0.5, P.tray_seat + 0.1, rz + P.pin_row_w/2), name='pin relief'))
    n = P.s3_usb_notch()
    cuts.append(aabox(part, (-o[0]/2 - 0.1, P.tray_seat, -n/2), (-cav[0]/2 + 0.01, hgt + 1, n/2),
                      name='USB notch'))
    return part.cut(name, cuts)


def dac_seat(part):
    """voice-case's DAC seat: a block the board lies on COMPONENT SIDE DOWN, its socket hanging
    into a zero-clearance recess open at the socket edge (+z), a pin-tail channel at the far end"""
    name = 'DAC seat'
    bx, z0, z1 = P.dac_block_x(), P.dac_block_z0(), P.dac_block_z1()
    aabox(part, (-bx, -0.01, z0), (bx, P.dac_block_top(), z1), name=name)
    cx = P.dac_l/2 + P.board_clr
    jx, rw = P.dac_jack_off(), P.dac_recess_w()
    rx, cw = P.dac_relief_x(), P.dac_cut_w
    zf = -P.dac_w/2
    return part.cut(name, [
        aabox(part, (-cx, P.dac_seat_y(), zf), (cx, P.dac_block_top() + 0.1, z1 + 1), name='DAC cavity'),
        aabox(part, (jx - rw/2, P.dac_recess_y0(), P.dac_recess_z0()),
              (jx + rw/2, P.dac_seat_y() + 0.01, z1 + 1), name='socket recess'),
        aabox(part, (rx - cw/2, P.dac_seat_y() - P.board_pin_h - P.clr, P.dac_relief_z0()),
              (rx + cw/2, P.dac_seat_y() + 0.01, P.dac_relief_z1()), name='pin relief')])


def mp_pocket(part):
    """(ring, cuts): the MP1584's walled pocket, open at both short ends for IN and OUT. The
    ring is joined whole and the cavity and exits cut from the tray, never from the ring."""
    cav, o = P.mp_cav(), P.mp_ring()
    ring = aabox(part, (-o[0]/2, -0.01, -o[1]/2), (o[0]/2, P.mp_lip, o[1]/2), name='MP1584 pocket')
    cuts = [aabox(part, (-cav[0]/2, 0, -cav[1]/2), (cav[0]/2, P.mp_lip + 0.1, cav[1]/2), name='MP cavity'),
            aabox(part, (-o[0]/2 - 0.1, 0, -3), (o[0]/2 + 0.1, P.mp_lip + 0.1, 3), name='MP wire exits')]
    return ring, cuts


# ---- flexure button ------------------------------------------------------------------------
def button_slots(part):
    """three stepped spirals: an arc at r_a, a radial step, an arc at r_b"""
    c, w = P.btn_pos, P.btn_slot_w
    ra, rb = P.btn_r_a(), P.btn_r_b()
    z0, z1 = -0.1, P.wall + 0.1
    out = []
    for k in range(3):
        t0 = 90 + 120*k
        t1 = t0 + P.btn_arc_in
        t2 = t1 + P.btn_arc_out
        out.append(prism_sector(part, 'z', c, ra - w/2, ra + w/2, t0, t1, z0, z1, name='button slot'))
        rm = (ra + rb)/2
        cx, cy = c[0] + rm*math.cos(math.radians(t1)), c[1] + rm*math.sin(math.radians(t1))
        out.append(prism_rect(part, 'z', (cx, cy), (rb - ra + w, w), z0, z1, angle=t1, name='button step'))
        out.append(prism_sector(part, 'z', c, rb - w/2, rb + w/2, t1, t2, z0, z1, name='button slot'))
    return out


def button_restore(part):
    """the disc back to full thickness after the ring is thinned, and the nub on it"""
    c = P.btn_pos
    return [prism_circle(part, 'z', c, P.btn_disc_d, P.btn_flex_t - 0.01, P.wall, name='button disc'),
            prism_circle(part, 'z', c, P.btn_nub_d, P.wall - 0.01, P.btn_nub_end(), name='button nub')]


def bridge_feet(part):
    adds, cuts = [], []
    top = P.bridge_z()
    for f in P.bridge_feet():
        adds.append(prism_circle(part, 'z', f, P.bridge_post_od, P.wall - 0.01, top, name='bridge foot'))
        cuts.append(prism_circle(part, 'z', f, P.board_screw_pilot, top - 6, top + 0.1, name='foot pilot'))
    return adds, cuts


def mic_seat(part):
    """board recess, gasket seat and the grille, from the inside of the TOP wall"""
    x, z = P.mic_pos
    h = P.box_h()
    dg = P.wall - P.mic_seat_depth - P.mic_gasket_depth            # gasket seat floor, depth
    cuts = [prism_rect(part, 'y', (x, z), (P.mic_board_w + 2*P.clr, P.mic_board_l + 2*P.clr),
                       h - P.wall - 0.1, h - (P.wall - P.mic_seat_depth), name='mic board recess'),
            prism_circle(part, 'y', (x, z), P.mic_gasket_d, h - (P.wall - P.mic_seat_depth) - 0.01, h - dg,
                         name='gasket seat')]
    for c in P.mic_holes():
        cuts.append(prism_circle(part, 'y', c, P.mic_hole_d, h - dg - 0.01, h + 0.1, name='mic grille'))
    return cuts


def mic_posts(part):
    """two posts hanging from the top's inside, flanking the seat along x"""
    x, z = P.mic_pos
    h = P.box_h()
    adds, cuts = [], []
    for sx in (-1, 1):
        c = (x + sx*P.mic_post_pitch/2, z)
        adds.append(prism_circle(part, 'y', c, P.mic_post_od, h - P.wall - P.mic_post_h, h - P.wall + 0.01,
                                 name='mic post'))
        cuts.append(prism_circle(part, 'y', c, P.board_screw_pilot, h - P.wall - P.mic_post_h - 0.1, h - P.wall,
                                 name='mic post pilot'))
    return adds, cuts


def usb_window(part):
    """voice-case's devkit USB-C window, now through the bottom, the wall thinned round it"""
    xc, w = P.s3_pos[0], P.s3_usb_w()
    zc, hz = P.s3_usb_z(), P.s3_usb_h/2 - P.s3_usb_trim
    m = P.usb_cb_margin
    return [aabox(part, (xc - w/2, -0.1, zc - hz), (xc + w/2, P.wall + 0.1, zc + hz), name='USB window'),
            aabox(part, (xc - w/2 - m, P.usb_panel_t, zc - hz - m), (xc + w/2 + m, P.wall + 0.1, zc + hz + m),
                  name='USB panel thinning')]


def top_cuts(part):
    h = P.box_h()
    t0, t1 = h - P.wall - 0.1, h + 0.1
    cuts = [prism_circle(part, 'y', (x, P.knob_z()), P.ctrl_bush_d + 2*P.ctrl_slack, t0, t1, name='knob hole')
            for x, _ in P.knob_xs()]
    # recesses inside the top for the pot nuts, which stand proud of the faceplate
    cuts += [prism_circle(part, 'y', (x, P.knob_z()), P.nut_recess_d, t0, h - P.wall + P.nut_recess_depth,
                          name='nut recess') for x, _ in P.knob_xs()]
    for x, z, ln in P.top_vents():
        cuts.append(slot(part, 'y', (x, z), ln, 0, t0, t1, name='top vent'))
    z0, z1 = P.hook_window()
    for x in P.hook_xs:
        cuts.append(aabox(part, (x - P.hook_w/2 - 0.5, t0, z0), (x + P.hook_w/2 + 0.5, t1, z1), name='hook window'))
    return cuts + mic_seat(part)


def bottom_cuts(part):
    cuts = [prism_circle(part, 'y', P.dc_hole_pt(), P.dc_hole_d(), -0.1, P.wall + 0.1, name='DC plug hole')]
    for c in P.spk_hole_pts():
        cuts.append(prism_circle(part, 'y', c, P.spk_hole_d, -0.1, P.wall + 0.1, name='speaker hole'))
    for x in P.bottom_vent_xs:
        cuts.append(slot(part, 'y', (x, P.vent_zc()), P.vent_len, 1, -0.1, P.wall + 0.1, name='bottom vent'))
    csink = (P.m3_cs_d - P.screw_clear)/2
    for c in P.pboss_screw_pts():
        cuts.append(prism_circle(part, 'y', c, P.screw_clear, -0.1, P.wall + 0.1, name='panel screw'))
        cuts.append(cone(part, 'y', c, P.m3_cs_d + 0.2, P.screw_clear, -0.1, csink, name='panel screw countersink'))
    return cuts + usb_window(part)


def keyholes(part):
    """Entry hole for the head, a slot up from it for the shank, and a head-wide pocket from the
    wall side over the whole travel: the head drops in, the box slides down, the head sits behind
    a kh_lip of plastic. The pocket opens onto the bed when printing, so nothing overhangs."""
    pz, d = P.plate_z(), P.box_d
    cuts = []
    for x, y in P.kh_pts:
        yc = y + P.kh_drop/2
        cuts.append(prism_circle(part, 'z', (x, y), P.kh_head, pz - 0.1, d + 0.1, name='keyhole entry'))
        cuts.append(prism_rrect(part, 'z', (x, yc), P.kh_shank, P.kh_drop + P.kh_shank, P.kh_shank/2,
                                pz - 0.1, d + 0.1, name='keyhole slot'))
        cuts.append(prism_rrect(part, 'z', (x, yc), P.kh_head, P.kh_drop + P.kh_head, P.kh_head/2,
                                pz + P.kh_lip, d + 0.1, name='keyhole pocket'))
    return cuts


def tray_print():
    """B -> the tray's print frame: back face on the bed"""
    return xf.mul(xf.T(0, 0, P.box_d), xf.Rx(180))


def tray(part):
    w, h, d, r = P.box_w, P.box_h(), P.box_d, P.box_r
    pz = P.plate_z()
    mid = (0, h/2)
    prism_rrect(part, 'z', mid, w, h, r, P.wall, d, name=TRAY)
    part.cut(TRAY, [prism_rrect(part, 'z', mid, w - 2*P.wall, h - 2*P.wall, max(0.5, r - P.wall),
                                P.wall - 0.1, pz, name='cavity')])
    adds, cuts = [], []
    sl = P.amp_standoff_len()
    for c in P.standoff_pts():
        adds.append(prism_circle(part, 'z', c, P.amp_standoff_od, pz - sl, pz + 0.01, name='standoff'))
        cuts.append(prism_circle(part, 'z', c, P.amp_hole_pilot, pz - sl - 0.1, pz + 2, name='standoff pilot'))
    adds += part.move_tools([devkit_pocket(part)], P.s3_xf())
    adds += part.move_tools([dac_seat(part)], P.dac_xf())
    # a groove in the plate under the DAC's plug head: with the seat lowered it would touch
    jx, r = P.dac_jack_off(), P.aux_plug_d/2 + 1
    cuts += part.move_tools([aabox(part, (jx - r, -P.dac_plug_groove, P.dac_edge_z()),
                                   (jx + r, 0.01, P.dac_socket_z() + P.dac_aux_plug + 1), name='plug groove')],
                            P.dac_xf())
    ring, mp_cuts = mp_pocket(part)
    moved = part.move_tools([ring] + mp_cuts, P.mp_xf())
    adds.append(moved[0])
    m_add, m_cut = mic_posts(part)
    part.union(TRAY, adds + m_add)
    cuts += keyholes(part)
    sink = (P.ws_head_d - P.ws_d)/2
    c = P.lock_pt
    cuts.append(prism_circle(part, 'z', c, P.ws_d, pz - 0.1, d + 0.1, name='locking screw'))
    cuts.append(cone(part, 'z', c, P.ws_head_d + 0.02, P.ws_d, pz - 0.01, pz + sink, name='locking countersink'))
    for c in P.knockout_pts():
        cuts.append(prism_circle(part, 'z', c, P.knockout_d, pz - 0.1, d - P.knockout_skin, name='knock-out'))
    part.cut(TRAY, cuts + moved[1:] + m_cut + top_cuts(part) + bottom_cuts(part))
    return part.move_bodies(tray_print())


# ---- panel ----------------------------------------------------------------------------------
def button_slots(part):
    """three stepped spirals: an arc at r_a, a radial step, an arc at r_b"""
    c, w = P.btn_pos, P.btn_slot_w
    ra, rb = P.btn_r_a(), P.btn_r_b()
    z0, z1 = -0.1, P.wall + 0.1
    out = []
    for k in range(3):
        t0 = 90 + 120*k
        t1 = t0 + P.btn_arc_in
        t2 = t1 + P.btn_arc_out
        out.append(prism_sector(part, 'z', c, ra - w/2, ra + w/2, t0, t1, z0, z1, name='button slot'))
        rm = (ra + rb)/2
        cx, cy = c[0] + rm*math.cos(math.radians(t1)), c[1] + rm*math.sin(math.radians(t1))
        out.append(prism_rect(part, 'z', (cx, cy), (rb - ra + w, w), z0, z1, angle=t1, name='button step'))
        out.append(prism_sector(part, 'z', c, rb - w/2, rb + w/2, t1, t2, z0, z1, name='button slot'))
    return out


def button_restore(part):
    """the disc back to full thickness after the ring is thinned, and the nub on it"""
    c = P.btn_pos
    return [prism_circle(part, 'z', c, P.btn_disc_d, P.btn_flex_t - 0.01, P.wall, name='button disc'),
            prism_circle(part, 'z', c, P.btn_nub_d, P.wall - 0.01, P.btn_nub_end(), name='button nub')]


def bridge_feet(part):
    adds, cuts = [], []
    top = P.bridge_z()
    for f in P.bridge_feet():
        adds.append(prism_circle(part, 'z', f, P.bridge_post_od, P.wall - 0.01, top, name='bridge foot'))
        cuts.append(prism_circle(part, 'z', f, P.board_screw_pilot, top - 6, top + 0.1, name='foot pilot'))
    return adds, cuts


def hooks(part):
    """two snap hooks along the top: a spring tab against the top wall, a barb into its window.
    The barb's catch face is square to the pull, its back a ramp, so it clicks in when the panel
    is pushed home and holds until pressed down through the window."""
    yo = P.box_h() - P.wall - P.clr
    zc = P.wall + P.hook_len
    out = []
    for x in P.hook_xs:
        x0, x1 = x - P.hook_w/2, x + P.hook_w/2
        out.append(aabox(part, (x0, yo - P.hook_t, P.wall - 0.01), (x1, yo, zc + 2.5), name='hook tab'))
        out.append(prism_poly(part, 'x', [(yo - 0.01, zc), (yo + P.hook_barb, zc), (yo - 0.01, zc + 2.5)],
                              x0, x1, name='hook barb'))
    return out


def panel_bosses(part):
    adds, cuts = [], []
    z0, z1 = P.pboss_z()
    for x, z in P.pboss_screw_pts():
        yc = P.wall + P.clr + P.pboss_od/2
        adds.append(prism_circle(part, 'z', (x, yc), P.pboss_od, z0 - 0.01, z1, name='panel boss'))
        cuts.append(prism_circle(part, 'y', (x, z), P.m3_pilot, P.wall, P.wall + P.clr + P.pboss_od - 1,
                                 name='panel boss pilot'))
    return adds, cuts


def panel(part):
    w, h, r, c = P.box_w, P.box_h(), P.box_r, P.front_chamfer
    mid = (0, h/2)
    rrect_loft_ax(part, 'z', 0, c, (w - 2*c, h - 2*c, max(0.5, r - c)), (w, h, r), c=mid, name=PANEL)
    part.union(PANEL, [prism_rrect(part, 'z', mid, w, h, r, c, P.wall, name='plate')])
    lw, lh = w - 2*(P.wall + P.clr), h - 2*(P.wall + P.clr)
    lip = prism_rrect(part, 'z', mid, lw, lh, max(0.5, r - P.wall), P.wall - 0.01, P.wall + P.lip_d, name='lip')
    part.cut(lip.name, [prism_rrect(part, 'z', mid, lw - 2*P.lip_t, lh - 2*P.lip_t, 0.5, P.wall - 0.1,
                                    P.wall + P.lip_d + 0.1, name='lip inside')])
    f_add, f_cut = bridge_feet(part)
    b_add, b_cut = panel_bosses(part)
    part.union(PANEL, [part.body(lip.name)] + f_add + b_add + hooks(part))
    flex = prism_circle(part, 'z', P.btn_pos, 2*P.btn_r_out(), P.btn_flex_t, P.wall + 0.01, name='flexure ring')
    part.cut(PANEL, [flex] + f_cut + b_cut + labels(part))
    part.union(PANEL, button_restore(part))
    return part.cut(PANEL, button_slots(part))


def labels(part):
    out = []
    for x, name in P.label_xs():
        out += text_tools(part, (x, P.label_y()), name, P.label_h, -0.1, P.label_depth,
                          right=(-1.0, 0.0, 0.0), up=(0.0, 1.0, 0.0), font=P.label_font, name='label')
    return out


# ---- switch bridge --------------------------------------------------------------------------
def bridge(part):
    """Print frame: bar along x, feet at x = +-bridge_foot_r, the pad face on top (z = bridge_t)
    — that face goes against the feet, the switch sunk into it facing the disc."""
    t, rf, bw = P.bridge_t, P.bridge_foot_r, P.bridge_w
    prism_rrect(part, 'z', (0, 0), 2*rf + bw, bw, bw/2, 0, t, name=BRIDGE)
    part.union(BRIDGE, [prism_rect(part, 'z', (0, 0), (P.bridge_pad, P.bridge_pad), 0, t, name='pad')])
    s = P.sw_body + 2*P.clr
    cuts = [prism_rect(part, 'z', (0, 0), (s, s), t - P.bridge_recess, t + 0.1, name='switch recess')]
    for sx in (-1, 1):
        cuts.append(prism_circle(part, 'z', (sx*rf, 0), P.bh_screw_clear, -0.1, t + 0.1, name='screw clearance'))
        cuts.append(prism_circle(part, 'z', (sx*rf, 0), P.bh_screw_cbore_d, -0.1, P.bh_screw_cbore_h,
                                 name='screw counterbore'))
    wx, wy = P.sw_pin_win_xy()
    for px, py in P.sw_pin_pos():
        cuts.append(prism_rect(part, 'z', (px, py), (wx, wy), -0.1, t + 0.1, name='pin window'))
    return part.cut(BRIDGE, cuts)


# ---- coupons --------------------------------------------------------------------------------
def coupon(part, which):
    """Real parts, sliced, so a test print tests the actual geometry.
    button: the middle of the panel — flexure, nub and bridge feet (fit the bridge and switch).
    top:    the strip of the tray's top with the knob holes, vents and hook windows."""
    h = P.box_h()
    if which == 'button':
        panel(part)
        name = PANEL
        x, y = P.btn_pos
        r = P.bridge_foot_r + 6
        lo, hi = (x - r, y - r, -1), (x + r, y + r, P.bridge_z() + 0.5)
    else:
        tray(part)
        name = TRAY
        part.move_bodies(xf.inverse(tray_print()))
        lo, hi = (-P.box_w, h - P.wall - 1, P.wall - 1), (P.box_w, h + 1, P.plate_z())
    part.intersect(name, [aabox(part, lo, hi, name='slice')])
    part.body(name).name = 'coupon ' + which
    return part
