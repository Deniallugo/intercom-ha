"""Base plate: closes the bottom and carries both boards (port of ``modules/base_plate.scad``).

Own frame: z = 0 is the inner face, +z toward the desk. Features reaching into the box are
drawn inside ``with part.mirrored():`` so their numbers read as depth below the inner face.
Each board seat is built as a sub-assembly (block - cavity - relief, + tab and stops) before
joining the plate.
"""

from . import params as P
from .build import box, cyl, prism_yz, rrect_prism

NAME = 'base plate'
S3_SEAT = 'devkit seat'
DAC_SEAT = 'DAC seat'
LIP = 'register lip'


def pin_relief(part, bw, bl, floor_h, origin=(0, 0), along_short=False,
               x_lo=None, x_hi=None, y_lo=None, y_hi=None, y_len=None, sides=(-1, 1),
               row_w=None, bclr=None):
    """Pin-tail relief strips sunk into a pocket floor (called inside a mirrored block).

    Default: strips along the long edges (devkit headers). `along_short` puts them on the
    short edges (the DAC's long +x edge carries the socket and needs floor). `bclr` is the
    board's own pocket clearance.
    """
    bclr = P.board_clr if bclr is None else bclr
    d = P.board_pin_h + P.clr
    rw = P.pin_row_w if row_w is None else row_w
    ox, oy = origin
    out = []
    if along_short:
        # Short-edge strips; x_lo / x_hi run a channel off that end instead of a land.
        for sy in sides:
            xl = -(bw/2 + bclr - P.pin_land) if x_lo is None else x_lo
            xr = (bw/2 + bclr - P.pin_land) if x_hi is None else x_hi
            out.append(box(part, (ox + (xl + xr)/2,
                                  oy + sy*((bl + 2*bclr)/2 - P.pin_relief_setback - rw/2),
                                  floor_h - d/2 + 0.01),
                           (xr - xl, rw, d + 0.02), name='pin relief'))
    else:
        # Long-edge strips; y_lo / y_hi override the default `pin_land` inset at each end.
        for sx in (-1, 1):
            yl = (-(bl + 2*bclr)/2 + P.pin_land) if y_lo is None else y_lo
            yh = (((bl + 2*bclr)/2 - P.pin_land) if y_len is None else yl + y_len) \
                if y_hi is None else y_hi
            out.append(box(part, (ox + sx*((bw + 2*bclr)/2 - P.pin_relief_setback
                                           - P.pin_row_w/2),
                                  oy + (yl + yh)/2, floor_h - d/2 + 0.01),
                           (P.pin_row_w, yh - yl, d + 0.02), name='pin relief'))
    return out


def register_lip(part):
    """Register lip nesting into the shell cavity: aligns the plate and closes the seam gap."""
    with part.mirrored():
        rrect_prism(part, 0, P.reg_h,
                    2*P.lip_outer_half_x(), 2*P.lip_outer_half_y(),
                    max(0.5, P.radius - P.wall - P.clr), name=LIP)
        bore = rrect_prism(part, -0.1, P.reg_h + 0.2,
                           2*P.lip_inner_half_x(), 2*P.lip_inner_half_y(),
                           max(0.5, P.radius - P.wall - P.clr - P.reg_t), name='lip bore')
    return part.cut(LIP, [bore])


def s3_front_tab(part):
    """Retention tab over the devkit's front edge.

    45 deg underside so it prints without support. Positioned from the cavity's front face
    and the board's travel, not from the front wall (which absorbs spare plan_y).
    """
    if not (P.s3_tab_cover > 0):
        return []
    yf = P.s3_cavity_y1()              # cavity's front face
    z0, zt, ztop = P.s3_tab_z0(), P.s3_tab_z1(), P.s3_tab_top()
    if ztop <= zt:
        return []
    over = P.s3_tab_over()
    return [prism_yz(part, [(yf, z0), (yf, ztop), (yf - over, ztop), (yf - over, zt)],
                     P.s3_pos_x(), P.s3_tab_w, name='retention tab')]


def s3_rear_stop_blocks(part):
    """Two rear stops flanking the USB notch: the board's y datum. No taller than the PCB,
    or the board is captured at both ends and can't be assembled."""
    y1 = -P.lip_inner_half_y()         # inner face — the datum
    y0 = -P.lip_outer_half_y()
    h = P.s3_seat_h + P.s3_rear_stop_h
    nx = P.s3_rear_notch()/2
    cav = P.s3_l/2 + P.s3_board_clr    # board cavity half-width
    if not (P.s3_rear_stops and cav > nx):
        return []
    out = []
    for sx in (-1, 1):
        x0, x1 = sx*nx, sx*cav
        out.append(box(part, (P.s3_pos_x() + (x0 + x1)/2, (y0 + y1)/2, h/2),
                       (abs(x1 - x0), y1 - y0, h), name='rear stop'))
    return out


def s3_seat(part):
    """Devkit friction slot, long axis along y, components up.

    Walls on +y and ±x, no rear wall: the rear has two stops either side of a notch wider
    than the USB window, so nothing sits in front of the ports.
    """
    h = P.s3_seat_h + P.pcb_t + P.s3_lip
    y0, y1 = P.s3_pocket_y0(), P.s3_pocket_y1()
    cy1 = P.s3_cavity_y1()              # cavity's front face, s3_front_gap past the board
    with part.mirrored():
        box(part, (P.s3_pos_x(), (y0 + y1)/2, h/2),
            (P.s3_pocket_f()[0], y1 - y0, h), name=S3_SEAT)
        # board cavity, open at -y
        cavity = box(part, (P.s3_pos_x(), (y0 - 1 + cy1)/2,
                            P.s3_seat_h + (h - P.s3_seat_h + 0.1)/2),
                     (P.s3_l + 2*P.s3_board_clr, cy1 - y0 + 1, h - P.s3_seat_h + 0.1),
                     name='devkit cavity')
        # Pin relief along both long edges, full length (open rear, setback at the front).
        relief = pin_relief(part, P.s3_l, P.s3_w, P.s3_seat_h,
                            origin=(P.s3_pos_x(), P.s3_cy()),
                            y_lo=-(P.s3_w/2 + P.s3_board_clr) - 1,
                            y_hi=P.s3_w/2 + P.s3_front_gap - P.s3_relief_front_setback,
                            bclr=P.s3_board_clr)
        part.cut(S3_SEAT, [cavity] + relief)
        # tab and rear stops go back into the cavity
        part.union(S3_SEAT, s3_front_tab(part) + s3_rear_stop_blocks(part))
    return part.body(S3_SEAT)


def dac_seat(part):
    """DAC friction pocket, open at +x (the socket overhanging there is the stop).

    Component side down: the socket hangs into a floor recess so the jack hole sits low.
    """
    h = P.dac_seat_h + P.pcb_t + P.dac_lip
    x0, x1 = P.dac_pocket_x0(), P.dac_pocket_x1()   # x1 is the lip, not the shell wall
    bx = P.dac_cx() - P.dac_w/2                     # board's -x edge
    with part.mirrored():
        box(part, ((x0 + x1)/2, P.dac_pos_y(), h/2),
            (x1 - x0, P.dac_pocket_f()[1], h), name=DAC_SEAT)
        # board cavity, open at +x
        cavity = box(part, ((bx + x1 + 1)/2, P.dac_pos_y(),
                            P.dac_seat_h + (h - P.dac_seat_h + 0.1)/2),
                     (x1 + 1 - bx, P.dac_l + 2*P.board_clr, h - P.dac_seat_h + 0.1),
                     name='DAC cavity')
        # Socket recess, sinking from the seating plane toward the plate (z = depth below
        # the inner face).
        rz_lo = P.plate_inner_z() - P.dac_recess_z1()   # nearest the plate
        rz_hi = P.plate_inner_z() - P.dac_seat_z()      # the seating plane
        recess = box(part, ((P.dac_recess_x0() + x1 + 1)/2, P.dac_jack_y(),
                            (rz_lo + rz_hi)/2),
                     (x1 + 1 - P.dac_recess_x0(), P.dac_recess_w(),
                      rz_hi - rz_lo + 0.02), name='socket recess')
        # Rear relief channel only (a front one would nest in the socket recess). Stops
        # dac_relief_wall_gap short of the +x wall to leave a land at the jack.
        relief = pin_relief(part, P.dac_w, P.dac_l, P.dac_seat_h,
                            origin=(P.dac_cx(), P.dac_pos_y()), along_short=True,
                            x_hi=P.inner_half_x() - P.dac_relief_wall_gap - P.dac_cx(),
                            sides=(-1,), row_w=P.dac_relief_w())
        part.cut(DAC_SEAT, [cavity, recess] + relief)
    return part.body(DAC_SEAT)


def vents(part):
    """Vent slots facing the desk, in otherwise-empty plate. Positions are checked."""
    return [rrect_prism(part, -0.1, P.wall + 0.2, v[2], v[3], min(v[2], v[3])/2,
                        center=(v[0], v[1]), name='vent')
            for v in P.vent_rects]


def corner_screws(part):
    """M3 clearance through, counterbored from the OUTER face."""
    out = []
    for cx, cy in P.boss_centres():
        out.append(cyl(part, -0.1, P.wall + 0.2, P.screw_clear, (cx, cy), name='screw'))
        out.append(cyl(part, P.wall - P.screw_cbore_h, P.screw_cbore_h + 0.1,
                       P.screw_cbore_d, (cx, cy), name='screw counterbore'))
    return out


def foot_recesses(part):
    """Foot recesses; none by default (no room in a 3 mm plate). See params.foot_positions."""
    return [cyl(part, P.wall - P.foot_depth, P.foot_depth + 0.1, P.foot_d, (fx, fy),
                name='foot recess')
            for fx, fy in P.foot_positions]


def build(part):
    rrect_prism(part, 0, P.wall, P.outer_w(), P.outer_h(), P.radius, name=NAME)
    part.union(NAME, [register_lip(part), s3_seat(part), dac_seat(part)])
    return part.cut(NAME, corner_screws(part) + vents(part) + foot_recesses(part))
