"""Puck shell (port of ``modules/shell.scad``): top face + four walls, open at the base.

Top face: button bore, mic port. Rear wall: devkit USB-C window. +x wall: DAC socket.
Additive shapes are unioned first, then every opening is cut; no cut depends on a face
created by another feature.
"""

from . import params as P
from .build import (box, box_z, cone_x, cyl, cyl_x, rrect_loft, rrect_prism)

NAME = 'shell'


# ---- envelope ------------------------------------------------------------------
def shell_body(part, depth):
    """Outer rounded box with a 45 deg chamfered top edge, hollowed, open at +z. A chamfer,
    not a fillet, so it prints top-down without support (lofted, like the SCAD's hull)."""
    rrect_loft(part, 0, P.chamfer,
               (2*P.flat_half_x(), 2*P.flat_half_y(), max(0.5, P.radius - P.chamfer)),
               (P.outer_w(), P.outer_h(), P.radius),
               name=NAME)
    walls = rrect_prism(part, P.chamfer, depth - P.chamfer,
                        P.outer_w(), P.outer_h(), P.radius, name='walls')
    part.union(NAME, [walls])
    cavity = rrect_prism(part, P.wall, depth,
                         P.outer_w() - 2*P.wall, P.outer_h() - 2*P.wall,
                         max(0.5, P.radius - P.wall), name='cavity')
    return part.cut(NAME, [cavity])


# ---- top face: button ----------------------------------------------------------
def button_cut(part):
    """Bore and flange recess. The bore is the accurate half of the cap's guide (the holder
    floats on clearance holes), hence btn_bore_d()."""
    return [
        cyl(part, -0.1, P.wall + 0.2, P.btn_bore_d(), P.btn_pos, name='button bore'),
        cyl(part, -0.1, P.btn_recess_depth + 0.1, P.btn_recess_d(), P.btn_pos,
            name='flange recess'),
    ]


def button_pilots(part):
    """Two blind M2 pilots on ±x, drilled from inside so nothing shows on the top face."""
    return [cyl(part, P.wall - P.btn_pilot_depth, P.btn_pilot_depth + 0.1,
                P.board_screw_pilot,
                (P.btn_pos[0] + sx*P.btn_pilot_pitch/2, P.btn_pos[1]),
                name='holder pilot')
            for sx in (-1, 1)]


# ---- top face: microphone ------------------------------------------------------
def mic_seat(part):
    """Board recess, gasket seat, one short port (keeps the resonance above speech)."""
    z_gasket = P.wall - P.mic_seat_depth - P.mic_gasket_depth
    return [
        box_z(part, P.wall - P.mic_seat_depth, P.mic_seat_depth + 0.1, P.mic_pos,
              (P.mic_board_w + 2*P.clr, P.mic_board_l + 2*P.clr),
              name='mic board recess'),
        cyl(part, z_gasket, P.mic_gasket_depth + 0.01, P.mic_gasket_d, P.mic_pos,
            name='gasket seat'),
        cyl(part, -0.1, z_gasket + 0.2, P.mic_hole_d, P.mic_pos, name='mic port'),
    ]


def mic_posts(part):
    """Two M2 posts flanking the seat (the board lies on its gasket); the clamp screws to them."""
    add, cut = [], []
    for sx in (-1, 1):
        c = (P.mic_pos[0] + sx*P.mic_post_pitch/2, P.mic_pos[1])
        add.append(cyl(part, P.wall, P.mic_post_h, P.mic_post_od, c, name='mic post'))
        cut.append(cyl(part, P.wall - 0.1, P.mic_post_h + 0.2, P.board_screw_pilot, c,
                       name='mic post pilot'))
    return add, cut


# ---- rear wall -----------------------------------------------------------------
def usb_window(part):
    """One window over the devkit's two USB-C ports, with rim left below it for the plate."""
    return box(part, (P.s3_pos_x(), -P.outer_h()/2, P.s3_usb_cz_eff()),
               (P.s3_usb_w(), P.wall*3, P.s3_usb_h_eff()), name='USB window')


def usb_panel(part):
    """Wall thinned from inside to usb_panel_t around the window, so a plug reaches."""
    y_hi = -P.inner_half_y() + 0.05
    y_lo = -(P.outer_h()/2 - P.usb_panel_t)
    return box(part, (P.s3_pos_x(), (y_hi + y_lo)/2, P.s3_usb_cz_eff()),
               (P.s3_usb_w() + 2*P.usb_cb_margin, y_hi - y_lo,
                P.s3_usb_h_eff() + 2*P.usb_cb_margin), name='USB panel thinning')


# ---- +x side wall --------------------------------------------------------------
def dac_jack_cut(part):
    """The DAC's own socket: inner counterbore, plug hole, outer lead-in. The thinned panel
    lets a plug seat fully; the socket stays inside the counterbore so the plate can rise
    straight into the shell."""
    cy = P.dac_jack_w + 2*P.clr
    cz = P.dac_jack_h + 2*P.clr
    panel_x = P.outer_w()/2 - P.jack_panel_t
    return [
        box(part, ((P.inner_half_x() - 0.1 + panel_x)/2, P.dac_jack_y(), P.dac_jack_cz()),
            (panel_x - P.inner_half_x() + 0.1, cy, cz), name='socket counterbore'),
        cyl_x(part, panel_x - 0.1, P.jack_panel_t + 0.2, P.jack_hole_d,
              (P.dac_jack_y(), P.dac_axis_z()), name='plug hole'),
        cone_x(part, P.outer_w()/2 - P.jack_lead_in, P.jack_lead_in + 0.1,
               P.jack_hole_d, P.jack_hole_d + 2*P.jack_lead_in,
               (P.dac_jack_y(), P.dac_axis_z()), name='plug lead-in'),
    ]


# ---- corners -------------------------------------------------------------------
def corner_bosses(part):
    """Full-depth corner pillars for M3 heat-set inserts."""
    add, cut = [], []
    for cx, cy in P.boss_centres():
        add.append(cyl(part, P.wall, P.cavity_depth, P.boss_od, (cx, cy), name='boss'))
        cut.append(cyl(part, P.wall - 0.1, P.cavity_depth + 0.2, P.insert_m3_d, (cx, cy),
                       name='insert bore'))
    return add, cut


def build(part):
    shell_body(part, P.top_depth())
    posts_add, posts_cut = mic_posts(part)
    boss_add, boss_cut = corner_bosses(part)
    part.union(NAME, posts_add + boss_add)
    return part.cut(NAME, button_cut(part) + button_pilots(part) + mic_seat(part)
                    + [usb_window(part), usb_panel(part)] + dac_jack_cut(part)
                    + posts_cut + boss_cut)
