"""Snap-in button cap (port of ``modules/button_cap.scad``): flange, straight body, one
top fillet.

Drawn in print orientation: apex on the plate at z = 0, print z = case z + btn_dome_h.
Prints dome-down with no overhang (tangent fillet, 45 deg flare, post on axis). Uses true
arcs, so its STL differs slightly from the SCAD's.
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
        # Retention lip: tapered on the leading end so the body cams inward; the square
        # trailing face is the catch.
        ('line', (r_lip, z_catch)),
        ('line', (r_wall, z_end)),
        ('line', (r_in, z_end)),
        ('line', (r_in, P.btn_dome_r)),    # back up the inside
        ('arc', dome_c, -90),              # inner fillet, btn_wall_t inside the outer one
        ('line', (0, P.btn_wall_t)),
        ('line', None),                    # close along the axis
    ], name=NAME)


def _slits(part):
    """Radial slits so the lip can collapse through the shell bore. They start below the
    top face, leaving the body solid where the bore guides it."""
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
    # Centre post, reaching btn_preload past the plunger's free position: the switch holds
    # the cap up against its lip, so it can't rattle.
    post = cyl(part, 0, P.btn_wall_t + P.btn_post_h(), P.btn_post_d, name='post')
    part.union(NAME, [post])
    return part.cut(NAME, _slits(part))
