"""fit-test coupons — the two parts that exist to keep you from reprinting a four-hour one.

Ported from the top of ``voice-case.scad``, where they lived because both are an
INTERSECTION of a real part with a slab: whatever the coupon tests, it tests the actual
geometry the shell or the plate will have, not a re-drawn approximation of it.

`coupon`   the button bore + pilots and the mic seat, cut out of the real top face, plus
           the three small parts that mate with them. Ten minutes of printing tells you
           whether the snap, the travel and the mic gasket land before you commit four
           hours to the shell. With the mechanism in the holder, this is also the cheapest
           way to iterate it — reprint the coupon and the holder, never the shell.
`fit`      a slice off the devkit bed's REAR end — pin relief, pocket width, rear stops.
`fit-front` the same slice off its FRONT end — the retention tab, and the width again.

           One coupon became two rather than one long one. It has been all three: a front
           slice, then the WHOLE bed once the rear stops went in (the board goes in TILTED
           between two features 63 mm apart, and a slice cannot rehearse that), then a rear
           slice. The whole bed is 10 cm3 — a third of the plate — and the questions live at
           the two ENDS, not in the 40 mm of plain pocket between them. Two 3.5 cm3 slices
           cover both for less than one bed, and each is a ten-minute print.

           What neither tests is the tilt itself. For that, raise s3_fit_len until they meet,
           or print the plate.
"""

from . import base_plate, button_cap, button_holder, mic_clamp, shell
from . import params as P
from .build import Part, box_z, transform

COUPON = 'coupon'
FIT = 'fit coupon'
FIT_FRONT = 'fit coupon front'


def coupon(design):
    """Top-face slice, plus the three mating parts laid out clear of it.

    The slice is DERIVED from the two features it has to contain, not typed in: it used to
    be a hard-coded 62 x 64 cube sized for a 96 mm plan, which quietly starts hanging off
    the part the moment plan_x changes. It spans the button holder's footprint and reaches
    forward past the mic posts, clamped to the case so it cannot run off the edge.
    """
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
    """A slice off one END of the devkit bed, taken off the real plate.

    ``end`` is -1 for the rear (pin relief, pocket width, rear stops) and +1 for the front
    (the retention tab, and the width again). Same slab, mirrored — writing it once means the
    two coupons cannot drift apart, and neither can drift from the plate they came off.

    The x span is the pocket EXACTLY, with no skirt — not laziness: the vent slots either
    side run within half a millimetre of the pocket walls, so any skirt would slice a
    channel down the coupon's own edges and leave it flexing where it has to be stiff. In
    y it takes a small skirt at the outboard end, where the nearest thing beyond is plate.

    It is shaved to s3_fit_base of plate rather than the real `wall`, because none of that
    plate thickness is under test: the bed is everything above the inner face, and 1.2 mm
    plus the pocket's own 3.5 mm floor is more than stiff enough to push a board into.
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
