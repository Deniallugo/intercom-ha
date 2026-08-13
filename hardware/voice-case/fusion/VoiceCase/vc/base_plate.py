"""base plate: a flat lid that closes the bottom of the puck and carries both boards.

Port of ``modules/base_plate.scad``. The four M3 bosses live on the SHELL at full depth
and hold the inserts; screws drop through these clearance holes into them, counterbored
so no head stands proud to scratch a desk.

Drawn in the plate's OWN frame: z = 0 is the INNER face (toward the cavity) and +z is
outward (toward the desk). Anything reaching into the box is therefore drawn inside
``with part.mirrored():`` — the port's stand-in for ``mirror([0, 0, 1])`` — so its
numbers still read as "depth below the inner face".

The two board seats are built as sub-assemblies: each is a block, cut by its cavity and
its pin-relief channels, and (for the devkit) unioned with its tab and rear stops BEFORE
it joins the plate. That ordering is load-bearing for the tab — as a union it is a wedge,
whereas cutting the cavity around it would mean authoring the same wedge inverted.
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
    """Relief for solder-side pin tails, sunk into a pocket floor.

    Two strips under the header rows, stopping short of each end so the board still seats
    on a land at both short ends as well as the central strip between them. Called from
    inside a mirrored block, so `floor_h` is depth below the plate's inner face.

    `along_short` puts the strips on the board's SHORT edges instead of its long ones.
    The devkit wants them on the long edges, where its header rows run; the DAC wants them
    on the short edges, because its long +x edge is where the 3.5 mm socket lives and that
    edge needs floor under it rather than a channel. `bclr` is per-board — the two pocket
    clearances are no longer the same number, so it cannot be read off the global.
    """
    bclr = P.board_clr if bclr is None else bclr
    d = P.board_pin_h + P.clr
    rw = P.pin_row_w if row_w is None else row_w
    ox, oy = origin
    out = []
    if along_short:
        # Short-edge strips. Each end defaults to a `pin_land` land; pass x_lo / x_hi to
        # run the channel off that end instead, giving wires a route out of the pocket.
        for sy in sides:
            xl = -(bw/2 + bclr - P.pin_land) if x_lo is None else x_lo
            xr = (bw/2 + bclr - P.pin_land) if x_hi is None else x_hi
            out.append(box(part, (ox + (xl + xr)/2,
                                  oy + sy*((bl + 2*bclr)/2 - P.pin_relief_setback - rw/2),
                                  floor_h - d/2 + 0.01),
                           (xr - xl, rw, d + 0.02), name='pin relief'))
    else:
        # Long-edge strips. y_lo / y_hi override each end; without them each is inset by a
        # `pin_land`. The devkit passes both, because its channels have to run the board's whole
        # length — a land at either end is somewhere its tails can come down on solid floor.
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
    """Lip nesting into the shell's cavity.

    The screws locate the plate eventually, but only after you have lined it up against
    four inserts; the lip does that part, and closes the light gap at the seam. Built as
    outer-minus-inner rather than as a two-loop sketch, so the profile stays unambiguous.
    """
    with part.mirrored():
        rrect_prism(part, 0, P.reg_h,
                    2*P.lip_outer_half_x(), 2*P.lip_outer_half_y(),
                    max(0.5, P.radius - P.wall - P.clr), name=LIP)
        bore = rrect_prism(part, -0.1, P.reg_h + 0.2,
                           2*P.lip_inner_half_x(), 2*P.lip_inner_half_y(),
                           max(0.5, P.radius - P.wall - P.clr - P.reg_t), name='lip bore')
    return part.cut(LIP, [bore])


def s3_front_tab(part):
    """Retention tab over the devkit's front short edge — what makes the pocket a SLOT.

    The underside is a 45 deg ramp, because the plate prints pocket-side up and a shelf
    reaching inward at this height would be an unsupported overhang. The ramp is true by
    construction: s3_tab_z1() is s3_tab_z0() plus the same reach the tab spans in y, so
    the diagonal is 1:1.

    It hangs off the cavity's front face — which is the board's nominal front edge, since the
    cavity is cut to exactly there — and both the reach and the underside height come off the
    board's own TRAVEL toward the rear stops. Taking them off the front WALL was a bug: the
    wall's thickness absorbs plan_y's spare depth, so the ramp sank a millimetre for every
    millimetre of it and eventually met the pocket floor.
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
    """Two blocks on the register lip's footprint, flanking a notch for the USB.

    They are the board's y datum — the front tab's ramp preloads it back against these.
    They stop at the PCB's top face and no higher: full height would capture the board in
    z at both ends, and then it could not be assembled at all.
    """
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
    """Friction pocket for the devkit, long axis along y, component side facing UP.

    Walls on +y and +-x only — there is NO rear wall. That is the fix for "none of the
    USB ports fit": a rear wall with a notch in it leaves a stub either side of the notch,
    and those stubs sit directly in front of the two receptacles. The rear is not fully
    open any more — two stops flank the notch, giving the board a y datum on the plate
    instead of on the shell wall — but the notch is still wider than the window.
    """
    h = P.s3_seat_h + P.pcb_t + P.s3_lip
    y0, y1 = P.s3_pocket_y0(), P.s3_pocket_y1()
    cy1 = P.s3_cavity_y1()              # cavity's front face, s3_front_gap past the board
    with part.mirrored():
        box(part, (P.s3_pos_x(), (y0 + y1)/2, h/2),
            (P.s3_pocket_f()[0], y1 - y0, h), name=S3_SEAT)
        # board cavity, running off the -y end so the pocket is open there
        cavity = box(part, (P.s3_pos_x(), (y0 - 1 + cy1)/2,
                            P.s3_seat_h + (h - P.s3_seat_h + 0.1)/2),
                     (P.s3_l + 2*P.s3_board_clr, cy1 - y0 + 1, h - P.s3_seat_h + 0.1),
                     name='devkit cavity')
        # Pin-tail relief so the board seats FLAT, not on its own pins. Both strips run the
        # board's WHOLE length: off the open rear end, and up to a setback short of the front
        # wall so they do not undercut its base. No end lands — the board seats on the 16 mm
        # central land between the strips, which runs the full length anyway.
        relief = pin_relief(part, P.s3_l, P.s3_w, P.s3_seat_h,
                            origin=(P.s3_pos_x(), P.s3_cy()),
                            y_lo=-(P.s3_w/2 + P.s3_board_clr) - 1,
                            y_hi=P.s3_w/2 + P.s3_front_gap - P.s3_relief_front_setback,
                            bclr=P.s3_board_clr)
        part.cut(S3_SEAT, [cavity] + relief)
        # ...and then the tab and the rear stops go BACK into the cavity just cut.
        part.union(S3_SEAT, s3_front_tab(part) + s3_rear_stop_blocks(part))
    return part.body(S3_SEAT)


def dac_seat(part):
    """Friction pocket for the DAC, socket end toward the +x wall.

    OPEN at +x: the socket overhangs the PCB, so a wall there would foul it — and the
    board needs no +x stop anyway, since the socket meeting its counterbore IS the stop.
    Component side faces DOWN, so the socket hangs below the PCB into a recess in this
    floor, which is the only way to get the jack hole near the base plate.
    """
    h = P.dac_seat_h + P.pcb_t + P.dac_lip
    x0, x1 = P.dac_pocket_x0(), P.dac_pocket_x1()   # x1 is the lip, not the shell wall
    bx = P.dac_cx() - P.dac_w/2                     # board's -x edge
    with part.mirrored():
        box(part, ((x0 + x1)/2, P.dac_pos_y(), h/2),
            (x1 - x0, P.dac_pocket_f()[1], h), name=DAC_SEAT)
        # Board cavity, running off the +x end only, so the pocket is open on that side
        # and walled on the other three.
        cavity = box(part, ((bx + x1 + 1)/2, P.dac_pos_y(),
                            P.dac_seat_h + (h - P.dac_seat_h + 0.1)/2),
                     (x1 + 1 - bx, P.dac_l + 2*P.board_clr, h - P.dac_seat_h + 0.1),
                     name='DAC cavity')
        # SOCKET RECESS. Authored z is DEPTH BELOW the inner face, so the recess sinks
        # from the seating plane DOWN toward the plate. Getting this direction wrong cuts
        # upward into the board and lip zone instead, leaving the floor solid and a sliver
        # of wall standing beside the relief.
        rz_lo = P.plate_inner_z() - P.dac_recess_z1()   # nearest the plate
        rz_hi = P.plate_inner_z() - P.dac_seat_z()      # the seating plane
        recess = box(part, ((P.dac_recess_x0() + x1 + 1)/2, P.dac_jack_y(),
                            (rz_lo + rz_hi)/2),
                     (x1 + 1 - P.dac_recess_x0(), P.dac_recess_w(),
                      rz_hi - rz_lo + 0.02), name='socket recess')
        # REAR channel only. The front one would sit inside the socket recess — the recess
        # is deeper, so the two nest into a stepped pocket — and it cannot be moved clear:
        # the relief setback pins its centre to the board edge, which is the same end the
        # socket is in. Its +x end stops dac_relief_wall_gap short of the wall's inner
        # face rather than running off the floor's edge: it is the jack's access and wants
        # a land there.
        relief = pin_relief(part, P.dac_w, P.dac_l, P.dac_seat_h,
                            origin=(P.dac_cx(), P.dac_pos_y()), along_short=True,
                            x_hi=P.inner_half_x() - P.dac_relief_wall_gap - P.dac_cx(),
                            sides=(-1,), row_w=P.dac_relief_w())
        part.cut(DAC_SEAT, [cavity, recess] + relief)
    return part.body(DAC_SEAT)


def vents(part):
    """Slots facing the desk, so they are invisible in use.

    Both banks sit in space the layout already had to leave empty: the -x strip beside the
    devkit — the only part in here that gets warm — and two bays fore and aft of the DAC
    pocket. Every slot's clearance to the pockets and the counterbores is checked, so if
    you move a plan dimension, run ./test.sh before assuming this list still fits.
    """
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
    """Empty by default — see params. A 0.6 recess on the outer face under a 2.5 pocket
    floor on the inner one does not fit in a 3 mm plate, and there is no clean set of four
    positions left. Populate foot_positions to bring them back."""
    return [cyl(part, P.wall - P.foot_depth, P.foot_depth + 0.1, P.foot_d, (fx, fy),
                name='foot recess')
            for fx, fy in P.foot_positions]


def build(part):
    rrect_prism(part, 0, P.wall, P.outer_w(), P.outer_h(), P.radius, name=NAME)
    part.union(NAME, [register_lip(part), s3_seat(part), dac_seat(part)])
    return part.cut(NAME, corner_screws(part) + vents(part) + foot_recesses(part))
