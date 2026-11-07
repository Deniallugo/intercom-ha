"""Dome button — plunger, dome, holder — and the mic clamp.

Port of ``modules/button.scad``. The mechanism is hardware/voice-case's, proven in print: an
11 mm tactile standing in a printed holder cup, a snap-lip plunger in a 19.6 mm journal. What
changes is the visible top — a SEPARATE Ø40 dome glued onto the plunger's flange, because a
dome and a snap plunger cannot both print well in one piece — and the holder's longer guide.

Each part is drawn in its PRINT orientation; the assembly turns them into place:
  plunger   flange top on the bed (z = 0), body growing +z
  dome      flat underside on the bed, crown up
  holder    floor on the bed (voice-case's builder, unchanged)
  clamp     bar on the bed, pad up (voice-case's builder, unchanged)
"""

import math

from . import params as P
from .build import box_z, cone_z, cyl, revolve_profile

PLUNGER = 'plunger'
DOME = 'dome'
HOLDER = 'button holder'
CLAMP = 'mic clamp'


def plunger(part):
    pz = -P.btn_flange_top_z()             # case z + pz = print z (flange top on the bed)
    r_fl = P.btn_flange_d/2
    r_wall = P.btn_wall_od/2
    r_in = P.btn_wall_id()/2
    r_lip = P.btn_lip_od()/2
    z_fl1 = pz + P.btn_face_bot_z()        # flange underside = the plunger's inner ceiling
    z_catch = pz + P.bh_catch_z()
    z_end = pz + P.btn_wall_z1()
    revolve_profile(part, (0, 0), [
        ('line', (r_fl, 0)), ('line', (r_fl, z_fl1)), ('line', (r_wall, z_fl1)),
        ('line', (r_wall, z_catch)),
        # retention lip: square shoulder at the catch, tapering back to the wall at the far end
        ('line', (r_lip, z_catch)), ('line', (r_wall, z_end)),
        ('line', (r_in, z_end)), ('line', (r_in, z_fl1)), ('line', (0, z_fl1)),
        ('line', None)], name=PLUNGER)
    # centre post: reaches btn_preload past the switch plunger's free position
    part.union(PLUNGER, [cyl(part, 0, z_fl1 + P.btn_post_h(), P.btn_post_d, name='post')])
    z0 = pz + P.btn_slit_z0
    z1 = z_end + 0.2
    big = 4*P.btn_flange_d
    slits = []
    for i in range(P.btn_slits):
        a = i*360.0/P.btn_slits
        r = math.radians(a)
        slits.append(box_z(part, z0, z1 - z0, (-big/2*math.sin(r), big/2*math.cos(r)),
                           (P.btn_slit_w, big), angle=a, name='slit'))
    return part.cut(PLUNGER, slits)


def dome(part):
    """Spherical cap on a flat underside; a 45 deg chamfer lifts the rim btn_rim_lift, which is
    what lets it print unsupported and is the rim's clearance when it rocks. A shallow pocket
    takes the plunger flange and centres the dome for gluing."""
    R0, h = P.btn_dome_d/2, P.btn_dome_h
    Rs = (R0*R0 + h*h)/(2*h)
    cz = P.btn_rim_lift + h - Rs                       # sphere centre
    a0 = math.degrees(math.atan2(P.btn_rim_lift - cz, R0))
    rs = P.btn_flange_d/2 + 0.15
    return revolve_profile(part, (0, P.btn_dome_seat), [
        ('line', (rs, P.btn_dome_seat)), ('line', (rs, 0)), ('line', (P.btn_dome_flat_r(), 0)),
        ('line', (R0, P.btn_rim_lift)),
        ('arc', (0, cz), 90 - a0),                     # the cap, up to the crown on the axis
        ('line', None)], name=DOME)


# ---- holder: voice-case vc/button_holder.py, verbatim apart from the names ----------------
def pin_windows(part, z_floor):
    w = P.sw_pin_win_xy()
    return [box_z(part, -0.1, z_floor + 0.2, (p[0], p[1]), (w[0], w[1]), name='pin window')
            for p in P.sw_pin_pos()]


def switch_ribs(part, z_floor):
    """Locating ribs, sunk bh_rib_embed below the plane the relief cut actually left, so the
    Join fuses them — built on the nominal plane they export as four loose bodies."""
    if not (P.sw_locate_t > 0 and P.sw_locate_h > 0):
        return []
    r_mid = (P.sw_locate_r0() + P.sw_locate_r1())/2
    z_seat = z_floor - P.bh_relief_eps
    out = []
    for i in range(4):
        pinned = (i % 2) == P.sw_pin_axis
        length = P.sw_locate_len_pin if pinned else P.sw_locate_len
        centre = (r_mid, 0) if i % 2 == 0 else (0, r_mid)
        if i >= 2:
            centre = (-centre[0], -centre[1])
        out.append(box_z(part, z_seat - P.bh_rib_embed, P.sw_locate_h + P.bh_rib_embed,
                         centre, (P.sw_locate_t, length), angle=i*90, name='locating rib'))
    return out


def holder(part):
    h = P.bh_z1() - P.bh_z0()
    z_floor = P.bh_floor_t
    z_catch = P.bh_z1() - P.bh_catch_z()
    ear_x = P.btn_pilot_pitch/2
    lead_in = 0.6
    cyl(part, 0, h, P.bh_collar_od(), name=HOLDER)
    adds = []
    for sx in (-1, 1):
        adds.append(cyl(part, 0, h, P.bh_ear_d, (sx*ear_x, 0), name='screw post'))
        adds.append(box_z(part, 0, h, (sx*(P.bh_collar_od()/2 + ear_x)/2, 0),
                          (ear_x - P.bh_collar_od()/2 + 2, P.bh_fin_t), name='web'))
    part.union(HOLDER, adds)
    cuts = [cyl(part, z_catch, h - z_catch + 0.1, P.bh_bore_d(), name='guide bore'),
            cone_z(part, h - lead_in, lead_in + 0.1, P.bh_bore_d(), P.bh_bore_d() + 2*lead_in,
                   name='bore lead-in'),
            cyl(part, z_floor - P.bh_relief_eps, z_catch - z_floor + 2*P.bh_relief_eps,
                P.bh_relief_d(), name='lip relief')]
    for sx in (-1, 1):
        cuts.append(cyl(part, -0.1, h + 0.2, P.bh_screw_clear, (sx*ear_x, 0), name='screw clearance'))
        cuts.append(cyl(part, -0.1, P.bh_screw_cbore_h + 0.1, P.bh_screw_cbore_d, (sx*ear_x, 0),
                        name='screw counterbore'))
    cuts += pin_windows(part, z_floor)
    part.cut(HOLDER, cuts)
    return part.union(HOLDER, switch_ribs(part, z_floor))


def clamp(part):
    box_z(part, 0, P.mic_clamp_t, (0, 0), (P.mic_clamp_len(), P.mic_clamp_w), name=CLAMP)
    pad = box_z(part, P.mic_clamp_t, P.mic_clamp_pad_h(), (0, 0),
                (P.mic_clamp_pad, min(P.mic_clamp_pad, P.mic_clamp_w)), name='pad')
    part.union(CLAMP, [pad])
    return part.cut(CLAMP, [cyl(part, -0.1, P.mic_clamp_t + 0.2, P.mic_screw_clear,
                                (sx*P.mic_post_pitch/2, 0), name='clamp screw') for sx in (-1, 1)])
