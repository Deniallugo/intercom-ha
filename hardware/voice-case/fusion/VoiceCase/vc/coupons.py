"""Fit-test coupons: real parts intersected with a slab, so they test the actual geometry.

`coupon`    button bore + pilots and mic seat from the real top face, plus their mating
            parts. ~10 min print; iterate the button here, not on the shell.
`fit`       rear end of the devkit bed: pin relief, width, rear stops.
`fit-front` front end of the devkit bed: retention tab, width.

Neither tests the tilt-in itself; raise s3_fit_len until they meet, or print the plate.
"""

from . import base_plate, button_cap, button_holder, mic_clamp, shell
from . import params as P
from .build import Part, box_z, transform

COUPON = 'coupon'
FIT = 'fit coupon'
FIT_FRONT = 'fit coupon front'


def coupon(design):
    """Top-face slice sized from the button holder and mic posts, plus the mating parts
    laid out beside it."""
    part = Part(design, COUPON)
    shell.build(part)
    w, y0, y1 = P.coupon_w(), P.coupon_y0(), P.coupon_y1()
    slab = box_z(part, -6, P.wall + 8, (0, (y0 + y1)/2), (w, y1 - y0), name='slice')
    part.intersect(shell.NAME, [slab])
    part.body(shell.NAME).name = COUPON

    parts = [part]
    for module, xy in ((button_cap, (0, y0 - 20)),
                       (button_holder, (w/2 + 24, y0 - 6)),
                       (mic_clamp, (-w/2 - 16, y0 - 14))):
        mate = Part(design, module.NAME, transform((xy[0], xy[1], 0)))
        module.build(mate)
        parts.append(mate)
    return parts


def fit(design, end=-1):
    """One end of the devkit bed off the real plate: ``end`` -1 rear, +1 front.

    x spans the pocket exactly (a skirt would cut into the adjacent vents); y gets a small
    skirt at the outboard end. Plate shaved to s3_fit_base.
    """
    name = FIT if end < 0 else FIT_FRONT
    part = Part(design, name)
    base_plate.build(part)
    zlo = -4*P.outer_d()
    outboard = end*(P.lip_outer_half_y() + P.s3_fit_skirt)
    inboard = outboard - end*P.s3_fit_len
    y0, y1 = min(outboard, inboard), max(outboard, inboard)
    slab = box_z(part, zlo, P.s3_fit_base - zlo, (P.s3_pos_x(), (y0 + y1)/2),
                 (P.s3_pocket_f()[0], y1 - y0),
                 name='slice')
    part.intersect(base_plate.NAME, [slab])
    part.body(base_plate.NAME).name = name
    return [part]
