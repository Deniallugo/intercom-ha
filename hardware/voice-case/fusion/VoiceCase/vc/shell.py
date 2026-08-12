"""puck shell: top face + four walls, open at the base (+z).

Port of ``modules/shell.scad``. The top face carries the button bore, the mic port and
the DAC's nothing-at-all (both boards are on the plate); the rear (-y) wall carries the
devkit's USB-C window and the +x wall the DAC's own 3.5 mm socket.

Feature order is the OpenSCAD one — union the additive shapes, then cut every opening —
because that is what makes each cut independent: nothing here depends on a face that an
earlier feature created, so moving a parameter can only move geometry, never re-target it.
"""

from . import params as P
from .build import (box, box_z, cone_x, cyl, cyl_x, rrect_loft, rrect_prism)

NAME = 'shell'


# ---- envelope ------------------------------------------------------------------
def shell_body(part, depth):
    """Outer rounded box with a 45 deg CHAMFERED top edge, hollowed, open at +z.

    Chamfer rather than fillet: the shell prints top-face-down, so the top edge is on the
    build plate and a tangent fillet would start horizontal there — a local 90 deg
    overhang. The chamfer is a loft between the flat top face and the full plan at
    z = chamfer, which is the hull() the OpenSCAD took.
    """
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
    """A plain bore, a shallow flange recess, nothing mechanical.

    Below the recess the bore is 1.4 mm of the journal the cap body runs in, and it is
    the ACCURATE half of it — the holder only gets on axis via two M2s in clearance
    holes — which is why it is cut at btn_bore_d() rather than at the global `clr`.
    """
    return [
        cyl(part, -0.1, P.wall + 0.2, P.btn_bore_d(), P.btn_pos, name='button bore'),
        cyl(part, -0.1, P.btn_recess_depth + 0.1, P.btn_recess_d(), P.btn_pos,
            name='flange recess'),
    ]


def button_pilots(part):
    """Two BLIND M2 pilots, drilled from the inner face, on +-x.

    Blind is the point: a through-hole here would be two visible dots either side of the
    button. They are on +-x because +y belongs to the mic and the bore between them is
    20 mm across.
    """
    return [cyl(part, P.wall - P.btn_pilot_depth, P.btn_pilot_depth + 0.1,
                P.board_screw_pilot,
                (P.btn_pos[0] + sx*P.btn_pilot_pitch/2, P.btn_pos[1]),
                name='holder pilot')
            for sx in (-1, 1)]


# ---- top face: microphone ------------------------------------------------------
def mic_seat(part):
    """Board recess, gasket seat, one short port.

    Pressing the INMP441's port onto the gasket leaves near-zero front volume, which puts
    the port resonance well above speech instead of in the middle of it.
    """
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
    """Two M2 posts FLANKING the seat, on full-thickness wall.

    They flank rather than sit under the board because the board lies directly on its own
    gasket. Screwing the clamp down onto them is what compresses that gasket.
    """
    add, cut = [], []
    for sx in (-1, 1):
        c = (P.mic_pos[0] + sx*P.mic_post_pitch/2, P.mic_pos[1])
        add.append(cyl(part, P.wall, P.mic_post_h, P.mic_post_od, c, name='mic post'))
        cut.append(cyl(part, P.wall - 0.1, P.mic_post_h + 0.2, P.board_screw_pilot, c,
                       name='mic post pilot'))
    return add, cut


# ---- rear wall -----------------------------------------------------------------
def usb_window(part):
    """One window over the devkit's own two USB-C receptacles.

    Power, first flash and the serial log all come through here, which is why there is no
    panel-mount USB socket. A BOUNDED hole: material is left below it so the rim the base
    plate seats on stays continuous.
    """
    return box(part, (P.s3_pos_x(), -P.outer_h()/2, P.s3_usb_cz_eff()),
               (P.s3_usb_w(), P.wall*3, P.s3_usb_h_eff()), name='USB window')


def usb_panel(part):
    """...and the wall around it thinned from the INSIDE, to usb_panel_t.

    Same trick and the same reason as the jack's panel: a plug has a fixed amount of
    shell before its overmold. Cut on the inner face only, so the outside stays a plain
    flat wall, and stopped short of the bottom rim.
    """
    y_hi = -P.inner_half_y() + 0.05
    y_lo = -(P.outer_h()/2 - P.usb_panel_t)
    return box(part, (P.s3_pos_x(), (y_hi + y_lo)/2, P.s3_usb_cz_eff()),
               (P.s3_usb_w() + 2*P.usb_cb_margin, y_hi - y_lo,
                P.s3_usb_h_eff() + 2*P.usb_cb_margin), name='USB panel thinning')


# ---- +x side wall --------------------------------------------------------------
def dac_jack_cut(part):
    """The DAC board's OWN 3.5 mm socket, through a locally THINNED panel.

    Three cuts: a counterbore on the inner face the socket body nests into, the plug hole
    through what is left, and a lead-in on the outer face. The thinning is what makes the
    socket usable — a 3.5 mm plug needs nearly all of ~14 mm of barrel in to make the
    ring contact — and the socket stops INSIDE the counterbore rather than poking
    through, which is what lets the plate carrying the board rise straight up into the
    shell at assembly.
    """
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
    """Full-depth pillars from the top face to the base plate rim, M3 heat-set inserts.

    Being full-depth is what makes them obstacles on every plane in the box, which is why
    the two boards sit side by side in x rather than anywhere convenient.
    """
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
