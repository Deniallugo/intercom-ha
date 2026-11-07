"""Button holder (port of ``modules/button_holder.scad``): a cup on two blind M2 pilots
inside the top face. Provides the lower guide, the catch and the switch floor, so they
can be tuned without reprinting the shell.

Internal profile (case z):
  bh_z0        .. bh_catch_z    guide bore
  bh_catch_z                    catch: where the cap's lip lands
  bh_catch_z   .. bh_relief_z1  relief: lip plus its full stroke
  bh_relief_z1                  collar floor, the switch stands here
  bh_relief_z1 .. bh_z1         floor, with four pin windows

Drawn in print orientation, floor down (print z = bh_z1() - case z), so nothing needs
support; the screw posts are full-height walls for the same reason.
"""

from . import params as P
from .build import box_z, cone_z, cyl

NAME = 'button holder'


def pin_windows(part, z_floor):
    """Four radial pin slots through the floor; each accepts a pin from flush with the
    switch's side to 2.5 mm out."""
    w = P.sw_pin_win_xy()
    return [box_z(part, -0.1, z_floor + 0.2, (p[0], p[1]), (w[0], w[1]), name='pin window')
            for p in P.sw_pin_pos()]


def switch_ribs(part, z_floor):
    """Four ribs at the edge midpoints that locate the switch (no depth cost).

    Shorter on the pinned sides, to fit between each pin pair. Sunk bh_rib_embed below the
    real seating plane (z_floor - bh_relief_eps): a rib on the nominal plane floats and
    exports as a separate body.
    """
    if not (P.sw_locate_t > 0 and P.sw_locate_h > 0):
        return []
    r_mid = (P.sw_locate_r0() + P.sw_locate_r1())/2
    z_seat = z_floor - P.bh_relief_eps        # what the relief cut actually left
    out = []
    for i in range(4):
        pinned = (i % 2) == P.sw_pin_axis     # i even -> +-x pair, i odd -> +-y pair
        length = P.sw_locate_len_pin if pinned else P.sw_locate_len
        centre = (r_mid, 0) if i % 2 == 0 else (0, r_mid)
        if i >= 2:
            centre = (-centre[0], -centre[1])
        out.append(box_z(part, z_seat - P.bh_rib_embed, P.sw_locate_h + P.bh_rib_embed,
                         centre, (P.sw_locate_t, length), angle=i*90, name='locating rib'))
    return out


def build(part):
    h = P.bh_z1() - P.bh_z0()               # overall
    z_floor = P.bh_floor_t                  # collar floor top — the switch stands here
    z_catch = P.bh_z1() - P.bh_catch_z()    # relief top = the catch shoulder
    ear_x = P.btn_pilot_pitch/2
    lead_in = 0.6

    cyl(part, 0, h, P.bh_collar_od(), name=NAME)
    adds = []
    for sx in (-1, 1):
        adds.append(cyl(part, 0, h, P.bh_ear_d, (sx*ear_x, 0), name='screw post'))
        # web tying each post to the collar
        adds.append(box_z(part, 0, h,
                          (sx*(P.bh_collar_od()/2 + ear_x)/2, 0),
                          (ear_x - P.bh_collar_od()/2 + 2, P.bh_fin_t), name='web'))
    part.union(NAME, adds)

    cuts = [
        # guide bore, chamfered at the mouth
        cyl(part, z_catch, h - z_catch + 0.1, P.bh_bore_d(), name='guide bore'),
        cone_z(part, h - lead_in, lead_in + 0.1,
               P.bh_bore_d(), P.bh_bore_d() + 2*lead_in, name='bore lead-in'),
        # lip relief; its upper face is the catch. Oversteps the floor by bh_relief_eps
        # (see switch_ribs).
        cyl(part, z_floor - P.bh_relief_eps, z_catch - z_floor + 2*P.bh_relief_eps,
            P.bh_relief_d(), name='lip relief'),
    ]
    # M2 clearance up the posts, counterbored: the devkit is close below
    for sx in (-1, 1):
        cuts.append(cyl(part, -0.1, h + 0.2, P.bh_screw_clear, (sx*ear_x, 0),
                        name='screw clearance'))
        cuts.append(cyl(part, -0.1, P.bh_screw_cbore_h + 0.1, P.bh_screw_cbore_d,
                        (sx*ear_x, 0), name='screw counterbore'))
    cuts += pin_windows(part, z_floor)
    part.cut(NAME, cuts)
    return part.union(NAME, switch_ribs(part, z_floor))
