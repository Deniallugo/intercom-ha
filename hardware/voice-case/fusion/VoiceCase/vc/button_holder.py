"""button holder — the switch carrier and the cap's guide.

Port of ``modules/button_holder.scad``. A cup that screws to the inside of the top face on
two blind M2 pilots. It provides the three things the shell deliberately does not: the
lower half of the journal the cap slides in, the shoulder its lip snaps onto, and a floor
for the 11 mm tactile switch to stand on — so tuning any of that never costs a shell
reprint.

Internal profile, from the wall inward (all case z):
  bh_z0        .. bh_catch_z    guide bore — the far half of what stops the cap rocking
  bh_catch_z                    the catch: the guide's own end face, where the lip lands
  bh_catch_z   .. bh_relief_z1  relief. Not just room for the lip — the lip TRAVELS down
                                it, so it is the lip plus the whole stroke
  bh_relief_z1                  collar floor. The switch stands on this, reaching back UP
                                past the catch into the cap's body bore
  bh_relief_z1 .. bh_z1         floor thickness, with four windows through it for the pins

Drawn in PRINTING orientation, and print z is bh_z1() - case z, i.e. the REVERSE of the
case — unlike every other part here, and that is the point. A cup printed mouth-down has
to bridge its own floor; printed floor-down there is nothing to support. The screw tabs
follow from the same choice: full-height posts rather than a flange, because a flange
standing 8 mm off the collar is an overhang and a post is just another vertical wall.
"""

from . import params as P
from .build import box_z, cone_z, cyl

NAME = 'button holder'


def pin_windows(part, z_floor):
    """The four pins go straight DOWN through the floor and are soldered below it.

    Four radial SLOTS, not four squares, and that is the point: how far the legs stand out
    from the body's side faces is the one dimension this design kept getting wrong, so the
    slot covers a RANGE of it rather than a position. As drawn each accepts a pin anywhere
    from flush with the side face to 2.5 mm outboard.
    """
    w = P.sw_pin_win_xy()
    return [box_z(part, -0.1, z_floor + 0.2, (p[0], p[1]), (w[0], w[1]), name='pin window')
            for p in P.sw_pin_pos()]


def switch_ribs(part, z_floor):
    """Four ribs that locate the switch, at the midpoint of each edge.

    The pins alone let it slide several millimetres inside their own windows; a pocket
    would cost depth 1:1. These stand BESIDE the body where there is 3.1 mm rather than
    the 0.8 at the corners, are plain vertical walls in this print orientation, and reach
    no further from the axis than sw_locate_max() — checked against the cap's bore, which
    comes down over them.

    Two lengths: the switch's pins stand OUT from two opposite sides, so on those the rib
    has to fit in the gap between that side's pair. Get it wrong and a rib sits over a pin
    window, printing in mid-air over a hole.

    They are joined on AFTER the lip relief has been cut, and that cut takes the floor down
    to z_floor - bh_relief_eps. So the seating plane is z_seat, not z_floor, and each rib is
    sunk bh_rib_embed below it. Built on the nominal plane they clear the real one by
    bh_relief_eps, and a Join across a gap joins nothing: they survive as four separate
    bodies, export as four separate objects, and slice as four islands hanging in mid-air
    over the floor. sw_locate_h stays the height above the plane the switch sits on.
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
        # web tying each post back into the collar. A plain vertical wall, so it costs
        # nothing to print in this orientation.
        adds.append(box_z(part, 0, h,
                          (sx*(P.bh_collar_od()/2 + ear_x)/2, 0),
                          (ear_x - P.bh_collar_od()/2 + 2, P.bh_fin_t), name='web'))
    part.union(NAME, adds)

    cuts = [
        # guide bore, with a lead-in at the mouth so the cap's lip meets a chamfer and not
        # a cut edge
        cyl(part, z_catch, h - z_catch + 0.1, P.bh_bore_d(), name='guide bore'),
        cone_z(part, h - lead_in, lead_in + 0.1,
               P.bh_bore_d(), P.bh_bore_d() + 2*lead_in, name='bore lead-in'),
        # lip relief. Its upper face is the guide's end, and that IS the catch. It
        # oversteps the floor by bh_relief_eps at the bottom, so the plane the switch and
        # the ribs stand on is that much below z_floor — switch_ribs() is what has to know.
        cyl(part, z_floor - P.bh_relief_eps, z_catch - z_floor + 2*P.bh_relief_eps,
            P.bh_relief_d(), name='lip relief'),
    ]
    # M2 clearance up the posts, counterbored so no head stands proud of the floor — the
    # devkit is only 2.8 mm below it
    for sx in (-1, 1):
        cuts.append(cyl(part, -0.1, h + 0.2, P.bh_screw_clear, (sx*ear_x, 0),
                        name='screw clearance'))
        cuts.append(cyl(part, -0.1, P.bh_screw_cbore_h + 0.1, P.bh_screw_cbore_d,
                        (sx*ear_x, 0), name='screw counterbore'))
    cuts += pin_windows(part, z_floor)
    part.cut(NAME, cuts)
    return part.union(NAME, switch_ribs(part, z_floor))
