"""Wall plate and lock bracket.

Port of ``modules/wall_plate.scad``. Plate frame: x across, y up (= world z, 0 at the bottom of
the amp box), z out of the wall (z = 0 is the wall side). Printed BACK DOWN: the keyhole
cavities open onto the bed and the lip over them is an ~8.4 mm bridge.

The OpenSCAD placed this with a mirror. Fusion takes rigid transforms only, so the assembly
uses a rotation that also flips x — the same solid, because everything here is symmetric in x.
"""

from . import params as P
from .build import aabox, cone, prism_circle, prism_rrect

PLATE = 'wall plate'
LOCK = 'lock bracket'


def plate(part):
    w, h, t = P.plate_w(), P.plate_h(), P.plate_t
    aabox(part, (-w/2, 0, 0), (w/2, h, t), name=PLATE)
    hw = P.header_w()
    part.union(PLATE, [aabox(part, (-hw/2, h - P.header_h, t - 0.01), (hw/2, h, P.header_d()),
                             name='header')])
    cuts = []
    slot_w, head_d, drop = P.kh_slot_w(), P.kh_head_d(), P.peg_drop
    for x, y in P.peg_pts():
        # lip: the keyhole proper — a slot the neck slides down, the head's entry at its top
        z0, z1 = t - P.kh_lip - 0.1, t + 0.1
        cuts.append(prism_rrect(part, 'z', (x, y + drop/2), slot_w, drop + slot_w, slot_w/2, z0, z1,
                                name='keyhole slot'))
        cuts.append(prism_circle(part, 'z', (x, y + drop), head_d, z0, z1, name='keyhole entry'))
        # cavity behind it, head-wide over the whole travel, open to the wall
        cuts.append(prism_rrect(part, 'z', (x, y + drop/2), head_d, drop + head_d, head_d/2,
                                -0.1, t - P.kh_lip, name='keyhole cavity'))
    sink = (P.ws_head_d - P.ws_d)/2
    for x, y in P.ws_pts():
        cuts.append(prism_circle(part, 'z', (x, y), P.ws_d, -0.1, t + 0.1, name='wall screw'))
        cuts.append(cone(part, 'z', (x, y), P.ws_d, P.ws_head_d, t - sink, t + 0.01, name='countersink'))
    for sx in (-1, 1):
        cuts.append(prism_circle(part, 'y', (sx*P.lock_screw_x, P.lock_screw_y()), P.insert_m3_d,
                                 h + 0.1 - (P.insert_m3_h + 1.1), h + 0.1, name='lock insert'))
    return part.cut(PLATE, cuts)


def lock(part):
    """World-aligned, printed flat: x across, y = distance from the wall, z up from the plate
    top. It lies on the header block over its whole depth — a cap, not a shelf — and its two
    outer ends span the voice legs' tops lock_gap below it."""
    y1 = P.lid_back_y() - 0.5
    aabox(part, (-P.box_w/2, 0.5, 0), (P.box_w/2, y1, P.lock_t), name=LOCK)
    cuts = []
    for sx in (-1, 1):
        c = (sx*P.lock_screw_x, P.lock_screw_y())
        cuts.append(prism_circle(part, 'z', c, P.screw_clear, -0.1, P.lock_t + 0.1, name='lock screw'))
        cuts.append(prism_circle(part, 'z', c, 6.2, P.lock_t - 1.8, P.lock_t + 0.2, name='counterbore'))
    return part.cut(LOCK, cuts)
