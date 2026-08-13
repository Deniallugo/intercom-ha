"""snap-in button cap: a scaled TalkingPetDIY dome, flange + straight body + one fillet.

Port of ``modules/button_cap.scad``. Drawn in PRINTING orientation: the dome APEX is on
the build plate at z = 0 and the part grows +z, which is the same direction as case z, so
case z maps to print z by adding btn_dome_h.

Printed apex-down the whole part is a cup — floor, then walls, then a post standing up
inside it — with no overhang anywhere, and three things make that true: the top fillet
meets the plate tangentially, the step out to the flange is 45 deg because btn_flare_h()
is DERIVED from the flange/body step, and the post is on the axis.

The revolved section is the OpenSCAD polygon with TRUE ARCS where it had a 24-segment
approximation of one — the only place this port is not bit-identical to the STL the SCAD
produced, and it is the direction you want to differ in.
"""

import math

from . import params as P
from .build import box_z, cyl, revolve_profile

NAME = 'button cap'


def _revolve(part):
    """One closed section: out from the apex, down the outside, round the flange, on down
    the body to the lip, then back up the inside and home along the axis."""
    pz = P.btn_dome_h                    # case z + pz = print z
    r_top = P.btn_top_d()/2
    r_wall = P.btn_wall_od/2
    r_in = P.btn_wall_id()/2
    r_flng = P.btn_cap_d/2
    r_lip = P.btn_lip_od()/2
    z_flare = pz + P.btn_flare_top_z()   # body meets the flare
    z_fl0 = pz + P.btn_flange_top_z()    # flange, upper face
    z_fl1 = pz + P.btn_face_bot_z()      # flange, underside — rests over the recess
    z_catch = pz + P.bh_catch_z()        # lip's square shoulder
    z_end = pz + P.btn_wall_z1()         # body's far edge
    dome_c = (r_top, P.btn_dome_r)       # both fillet arcs share this centre

    return revolve_profile(part, (0, 0), [
        ('line', (r_top, 0)),
        ('arc', dome_c, 90),               # outer top fillet, tangent to the plate
        ('line', (r_wall, z_flare)),       # body
        ('line', (r_flng, z_fl0)),         # 45 deg flare out
        ('line', (r_flng, z_fl1)),         # flange
        ('line', (r_wall, z_fl1)),
        ('line', (r_wall, z_catch)),       # body, on down to the lip
        # Retention lip. Tapered, not a square barb: the far end enters the bore first, so
        # it is the narrow end and the body cams inward as you press. The step back at the
        # near end stays square — that face is the catch.
        ('line', (r_lip, z_catch)),
        ('line', (r_wall, z_end)),
        ('line', (r_in, z_end)),
        ('line', (r_in, P.btn_dome_r)),    # back up the inside
        ('arc', dome_c, -90),              # inner fillet, btn_wall_t inside the outer one
        ('line', (0, P.btn_wall_t)),
        ('line', None),                    # close along the axis
    ], name=NAME)


def _slits(part):
    """Radial slits, so the lip can collapse through the shell bore.

    They start below the top face and run off the far edge, which leaves the body solid
    everywhere the shell bore touches it — the journal is not cut where it is most
    accurate, and the only way to see one is to look up under the flange. Each cut runs
    outward from the axis only, so btn_slits is the slit count, not half of it.
    """
    z0 = P.btn_dome_h + P.btn_slit_z0
    z1 = P.btn_dome_h + P.btn_wall_z1() + 0.2
    big = 4*P.btn_cap_d
    out = []
    for i in range(P.btn_slits):
        a = math.radians(i*360.0/P.btn_slits)
        centre = (-big/2*math.sin(a), big/2*math.cos(a))
        out.append(box_z(part, z0, z1 - z0, centre, (P.btn_slit_w, big),
                         angle=i*360.0/P.btn_slits, name='slit'))
    return out


def build(part):
    _revolve(part)
    # Centre post, reaching btn_preload PAST the plunger's free position — so with the lip
    # on the catch the switch is holding the cap up there and it cannot rattle. It carries
    # the whole thumb load until the plunger bottoms in the switch body under it.
    post = cyl(part, 0, P.btn_wall_t + P.btn_post_h(), P.btn_post_d, name='post')
    part.union(NAME, [post])
    return part.cut(NAME, _slits(part))
