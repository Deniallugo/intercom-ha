"""Every electronic part in the unit, as data — pure Python, no adsk.

One description, three consumers:
  * ``electronics.py`` builds each entry as its own Fusion component (inside its box's
    sub-assembly), so it shows up in the browser, can be hidden, measured, or DRAGGED;
  * ``checks.py`` tests every pair of parts for overlap and every part against the box's
    cavity and the printed obstacles in it (lid bosses, floor, button holder, mic clamp);
  * ``sync.py`` maps a drag in Fusion back to the placement number that moved it.

A part is a list of primitives in its box's LOCAL frame (x across, y up from the box bottom,
z into the box from the front face) — the same frame every case feature is authored in, so a
dummy and the pocket made for it are drawn from the same numbers.

The shapes are DUMMIES. Board outlines, connector positions and heights come from
``params.py`` and carry its tags; the bodies standing on them (pot cans, jack bodies, the
WROOM can, dupont housings, plug heads) are [assumed] typical sizes. They are there to be
seen and to collide, not to be trusted to 0.1 mm.

Kinds of primitive:
  box     axis-aligned, `lo`..`hi`
  cyl     along `axis`, centre `c` in the other two axes in (x, y, z) order, `d`, `a0`..`a1`
Flags:
  outside   deliberately outside the cavity (a knob, a flange, a part in a wall rebate) —
            skipped by the cavity check, still checked against other parts
  soft      a cable: drawn, never checked. Cables bend; the routes are illustrations
"""

try:
    from . import params as P, xf
except ImportError:
    import params as P
    import xf


def box_xf(where):
    """box-local -> world for 'amp' / 'voice': OpenSCAD's translate([0, front_y, z0])
    rotate([90, 0, 0]). A quarter turn, so axis-aligned stays axis-aligned."""
    z0 = 0 if where == 'amp' else P.voice_z0()
    return xf.mul(xf.T(0, P.front_y(), z0), xf.Rx(90))


def to_world(p, x):
    """the same primitive, in world coordinates, under the quarter-turn transform `x`"""
    if p.kind == 'box':
        a, b = xf.apply(x, p.lo), xf.apply(x, p.hi)
        return Prim('box', p.name, p.finish, p.outside, p.soft,
                    lo=tuple(min(a[k], b[k]) for k in range(3)),
                    hi=tuple(max(a[k], b[k]) for k in range(3)))
    k = 'xyz'.index(p.axis)
    others = [j for j in range(3) if j != k]

    def point(a):
        q = [0.0]*3
        q[k] = a
        for j, c in zip(others, p.c):
            q[j] = c
        return xf.apply(x, q)
    p0, p1 = point(p.a0), point(p.a1)
    v = xf.apply_vec(x, [1.0 if j == k else 0.0 for j in range(3)])
    kw = max(range(3), key=lambda j: abs(v[j]))
    return Prim('cyl', p.name, p.finish, p.outside, p.soft, axis='xyz'[kw],
                c=tuple(p0[j] for j in range(3) if j != kw), d=p.d, a0=p0[kw], a1=p1[kw])


class Prim:
    def __init__(self, kind, name, finish, outside=False, soft=False, **geo):  # noqa
        self.kind, self.name, self.finish = kind, name, finish
        self.outside, self.soft = outside, soft
        self.__dict__.update(geo)

    def aabb(self):
        if self.kind == 'box':
            return tuple(self.lo), tuple(self.hi)
        i = 'xyz'.index(self.axis)
        others = [k for k in range(3) if k != i]
        lo, hi = [0.0]*3, [0.0]*3
        lo[i], hi[i] = min(self.a0, self.a1), max(self.a0, self.a1)
        for k, c in zip(others, self.c):
            lo[k], hi[k] = c - self.d/2, c + self.d/2
        return tuple(lo), tuple(hi)


def box(name, lo, hi, finish, **kw):
    lo, hi = list(lo), list(hi)
    for k in range(3):
        lo[k], hi[k] = min(lo[k], hi[k]), max(lo[k], hi[k])
    return Prim('box', name, finish, lo=tuple(lo), hi=tuple(hi), **kw)


def cbox(name, c, size, finish, **kw):
    """box from a centre and a size"""
    return box(name, [c[k] - size[k]/2 for k in range(3)],
               [c[k] + size[k]/2 for k in range(3)], finish, **kw)


def cyl(name, axis, c, d, a0, a1, finish, **kw):
    return Prim('cyl', name, finish, axis=axis, c=tuple(c), d=d, a0=a0, a1=a1, **kw)


def route(name, pts, d, finish='cable'):
    """A cable as an axis-aligned polyline: one cylinder per leg, ends overlapped by d/2 so the
    corners close. Every leg must change exactly one coordinate."""
    out = []
    for a, b in zip(pts, pts[1:]):
        moved = [k for k in range(3) if abs(a[k] - b[k]) > 1e-9]
        if len(moved) != 1:
            raise ValueError('%s: leg %s -> %s is not axis-aligned' % (name, a, b))
        k = moved[0]
        lo, hi = min(a[k], b[k]) - d/2, max(a[k], b[k]) + d/2
        c = [a[j] for j in range(3) if j != k]
        out.append(cyl(name, 'xyz'[k], c, d, lo, hi, finish, soft=True))
    return out


class Comp:
    """One Fusion component.

    `moves` maps a box-local axis to the placement number a drag along it changes:
    {'x': ('amp_x', None), 'y': ('btn_pos', 1)} — the index is for tuple values. An axis not
    listed cannot be moved (a board lying in a pocket cannot leave the floor); a part with no
    moves at all `follows` another and is moved by moving that one.
    """

    def __init__(self, name, where, prims, moves=None, follows=None, mates=(), note=''):
        self.name, self.where, self.prims = name, where, prims
        self.moves, self.follows = moves or {}, follows
        self.mates = set(mates)
        self.note = note


# =====================================================================================
# amplifier box
# =====================================================================================
def _amp():
    ax = P.amp_x
    y0, y1 = P.amp_pcb_y(), P.amp_pcb_top()
    zf = P.amp_front_z()                       # faceplate front face
    zp = zf + P.amp_face_t                     # PCB front edge, behind the faceplate
    zr = P.amp_rear_z()                        # PCB rear edge
    pr = [
        box('PCB', (ax - P.amp_w/2, y0, zp), (ax + P.amp_w/2, y1, zr), 'pcb_dark'),
        # The faceplate sits in the front wall's rebate by design, so it is "outside".
        cbox('faceplate', (ax + P.amp_face_x, P.amp_face_y() + P.amp_face_h/2, zf + P.amp_face_t/2),
             (P.amp_face_w, P.amp_face_h, P.amp_face_t), 'black', outside=True),
        cbox('heatsink', (ax + P.amp_hs[0], (y1 + P.amp_env_top())/2, P.amp_bz(P.amp_hs[1])),
             (P.amp_hs[2], P.amp_env_top() - y1, P.amp_hs[3]), 'alu'),
    ]
    axis_y = y0 + P.ctrl_axis
    for i in (-1, 0, 1):
        x = ax + P.ctrl_x0 + i*P.ctrl_pitch
        bw, bd, bh = P.amp_pot_body
        pr.append(box('pot', (x - bw/2, y1, zp), (x + bw/2, y1 + bh, zp + bd), 'metal'))
        # bushing + nut through the faceplate, and the shaft out of the box
        pr.append(cyl('bushing', 'z', (x, axis_y), P.ctrl_bush_d, zf - 1.5, zp, 'metal',
                      outside=True))
        pr.append(cyl('shaft', 'z', (x, axis_y), P.amp_pot_shaft_d, zf - P.ctrl_shaft_proj,
                      zf - 1.5, 'metal', outside=True))
    pr.append(cyl('LED', 'z', (ax + P.ctrl_led[0], y0 + P.ctrl_led[1]), P.amp_led_d,
                  zp, zp + 4, 'red'))
    # rear edge
    z0 = P.plug_z0()                           # connector faces
    w, d, h = P.amp_dc_body
    pr.append(box('DC jack', (ax + P.amp_dc_x - w/2, y1, z0 - d), (ax + P.amp_dc_x + w/2, y1 + h, z0),
                  'black'))
    w, d, h = P.amp_aux_body
    pr.append(box('AUX jack', (ax + P.amp_aux_x - w/2, y1, z0 - d),
                  (ax + P.amp_aux_x + w/2, y1 + h, z0), 'black'))
    pr.append(box('barrier block', (ax + P.amp_term_x[0], y1, zr - P.amp_term_depth),
                  (ax + P.amp_term_x[1], y1 + P.amp_term_h, zr), 'green'))
    sx, sz = P.amp_sw_onboard_at
    w, d, h = P.amp_sw_onboard
    pr.append(cbox('onboard switch', (ax + sx, y1 + h/2, P.amp_bz(sz)), (w, h, d), 'yellow'))
    # the four mounting screws' heads, so the standoffs visibly meet the board's holes
    hd, hh = P.amp_screw_head
    for hx, hr in P.amp_holes:
        pr.append(cyl('screw head', 'y', (ax + hx, P.amp_bz(hr)), hd, y1, y1 + hh, 'metal'))
    return Comp('ZK-502MT', 'amp', pr,
                moves={'x': ('amp_x', None), 'y': ('amp_lift', None), 'z': ('amp_setback', None)},
                note='board + faceplate + heatsink + pots + rear connectors')


def _knobs():
    pr = []
    axis_y = P.amp_pcb_y() + P.ctrl_axis
    for i in (-1, 0, 1):
        x = P.amp_x + P.ctrl_x0 + i*P.ctrl_pitch
        pr.append(cyl('knob', 'z', (x, axis_y), P.knob_d, -P.knob_gap - P.knob_h, -P.knob_gap,
                      'knob', outside=True))
    return Comp('knobs', 'amp', pr, follows='ZK-502MT', mates=('ZK-502MT',),
                note='on the pot shafts, outside the front face')


def _mp1584():
    yb = P.wall + P.sled_t                     # sits on the sled, inside its pocket
    yt = yb + 1.2
    zc = P.mp_zc()
    pr = [cbox('PCB', (P.mp_x, (yb + yt)/2, zc), (P.mp_w, yt - yb, P.mp_l), 'pcb_blue')]
    w, d, h = P.mp_inductor
    pr.append(cbox('inductor', (P.mp_x - 4, yt + h/2, zc), (w, h, d), 'black'))
    w, d, h = P.mp_trim
    pr.append(cbox('trim pot', (P.mp_x + 6, yt + h/2, zc + 4), (w, h, d), 'blue'))
    return Comp('MP1584', 'amp', pr, moves={'x': ('mp_x', None), 'z': ('mp_dz', None)},
                note='24 V -> 5 V buck, in the sled pocket. Set to 5.0 V BEFORE connecting')


def _psw():
    xo = P.box_w/2                             # outer face of the +x wall
    xi = xo - P.wall
    zc, yc = P.psw_zc(), P.amp_psw_y
    fz, fy, fx = P.psw_flange
    bx, bz, by = P.amp_psw_body
    pr = [cbox('bezel', (xo + fx/2, yc, zc), (fx, fy, fz), 'black', outside=True),
          cbox('through wall', (xo - P.wall/2, yc, zc), (P.wall, P.amp_psw_cut[1] - 0.4,
                                                          P.amp_psw_cut[0] - 0.4),
               'black', outside=True),
          box('body', (xi - bx, yc - by/2, zc - bz/2), (xi, yc + by/2, zc + bz/2), 'black')]
    return Comp('power switch', 'amp', pr,
                moves={'z': ('psw_dz', None), 'y': ('amp_psw_y', None)},
                note='panel rocker on the +x wall, replaces the unreachable onboard switch')


def _amp_plugs():
    y1 = P.amp_pcb_top()
    z0 = P.plug_z0()
    # straight barrel plug, out through the lid's cable window, then down the channel
    dc_c = (P.amp_x + P.amp_dc_x, y1 + P.amp_dc_axis)
    zl = P.box_d() + P.lid_t
    dc = [cyl('plug', 'z', dc_c, P.amp_dc_plug_d, z0, z0 + P.dc_plug_len, 'black', outside=True)]
    dc += route('cable', [(dc_c[0], dc_c[1], z0 + P.dc_plug_len), (dc_c[0], dc_c[1], zl + 8),
                          (dc_c[0], -25, zl + 8)], P.dc_cable_d)
    # right-angle AUX plug in the amp's jack; head along z, cable up out of its top
    ax, ay = P.amp_x + P.amp_aux_x, y1 + P.amp_aux_axis
    hd = P.aux_plug_d
    aux = [box('plug head', (ax - hd/2 - 0.5, ay - hd/2, z0), (ax + hd/2 + 0.5, ay + hd/2 + 4,
                                                               z0 + P.aux_plug_barrel), 'black')]
    return [Comp('DC plug', 'amp', dc, follows='ZK-502MT', mates=('ZK-502MT',),
                 note='24 V in; out through the lid window and down the channel'),
            Comp('AUX plug (amp)', 'amp', aux, follows='ZK-502MT', mates=('ZK-502MT',),
                 note='right-angle; the patch cable leaves its top')]


def _amp_leads():
    y1 = P.amp_pcb_top()
    zl = P.box_d() + P.lid_t
    # speaker leads off the barrier block, out of the lid window and down the channel
    xs = P.amp_x + (P.amp_term_x[0] + P.amp_term_x[1])/2
    ys = y1 + P.amp_term_h/2
    spk = route('speaker leads', [(xs, ys, P.amp_rear_z()), (xs, ys, zl + 4), (xs, -25, zl + 4)],
                P.spk_cable_d)
    # 24 V tap: barrel-jack solder pins (under the PCB) to the MP1584's IN end
    yt = P.wall + P.sled_t + 1.5
    xdc = P.amp_x + P.amp_dc_x
    zdc = P.plug_z0() - P.amp_dc_body[1]/2
    xin = P.mp_x - P.mp_w/2 + 1
    tap = route('24 V tap', [(xdc, P.amp_pcb_y(), zdc), (xdc, yt, zdc), (xdc, yt, P.mp_zc()),
                             (xin, yt, P.mp_zc())], P.lead_d)
    # panel switch leads, to the onboard switch's pads
    sx, sz = P.amp_sw_onboard_at
    xo = P.amp_x + sx
    xsw = P.box_w/2 - P.wall - P.amp_psw_body[0]
    sw = route('switch leads', [(xsw, P.amp_psw_y, P.psw_zc()), (xo, P.amp_psw_y, P.psw_zc()),
                                (xo, P.amp_psw_y, P.amp_bz(sz)), (xo, y1 + P.amp_sw_onboard[2],
                                                                  P.amp_bz(sz))], P.lead_d)
    return [Comp('amp wiring', 'amp', spk + tap + sw, follows='(routes)',
                 note='speaker leads, 24 V tap, switch leads — illustrative routes')]


# =====================================================================================
# voice box
# =====================================================================================
def _devkit():
    yb = P.board_seat_y()
    yt = yb + P.pcb_t
    xc, zc = P.s3_x, P.s3_zc()
    pr = [cbox('PCB', (xc, (yb + yt)/2, zc), (P.s3_w, P.pcb_t, P.s3_l), 'pcb_dark')]
    mx, mz, mh = P.s3_module
    pr.append(box('ESP32-S3 module', (xc + P.s3_w/2 - mx, yt, zc - mz/2),
                  (xc + P.s3_w/2, yt + mh, zc + mz/2), 'metal'))
    ux, uz, uh = P.s3_usb
    # flush with the board end: s3_w (63) is the measured end-to-end length, connectors included
    for s in (-1, 1):
        pr.append(box('USB-C', (xc - P.s3_w/2, yt, zc + s*P.s3_usb_pitch/2 - uz/2),
                      (xc - P.s3_w/2 + ux, yt + uh, zc + s*P.s3_usb_pitch/2 + uz/2), 'metal'))
    # header rows on both long edges: plastic + pins + dressed dupont housings above, tails below
    hw, _ = P.s3_hdr
    for s in (-1, 1):
        zr = zc + s*(P.s3_l/2 - 1.27 - 0.6)
        pr.append(box('header + duponts', (xc - 28, yt, zr - hw/2), (xc + 28, yt + P.s3_dupont_h,
                                                                       zr + hw/2), 'black'))
        pr.append(box('pin tails', (xc - 28, yb - P.board_pin_h, zr - 0.8),
                      (xc + 28, yb, zr + 0.8), 'metal'))
    return Comp('ESP32-S3 devkit', 'voice', pr, moves={'x': ('s3_x', None), 'z': ('s3_z0', None)},
                note='DevKitC-1 N16R8, long axis across x, module at +x, USB-C at -x')


def _dac():
    yb = P.board_seat_y()
    yt = yb + P.pcb_t
    xc, zc = P.dac_xc(), P.dac_zc()
    pr = [cbox('PCB', (xc, (yb + yt)/2, zc), (P.dac_l, P.pcb_t, P.dac_w), 'pcb_purple')]
    jw = P.dac_jack_w
    pr.append(box('3.5 mm socket', (P.dac_jack_x() - jw/2, yt, P.dac_socket_z() - 12),
                  (P.dac_jack_x() + jw/2, yt + P.dac_jack_h, P.dac_socket_z()), 'black'))
    zh = zc - P.dac_w/2 + 1.5
    pr.append(box('header + duponts', (xc - P.dac_hdr_len/2, yt, zh - 1.25),
                  (xc + P.dac_hdr_len/2, yt + P.s3_dupont_h, zh + 1.25), 'black'))
    return Comp('PCM5102A', 'voice', pr, moves={'x': ('dac_dx', None), 'z': ('dac_dz', None)},
                note='I2S DAC, socket facing the rear, over the sleeve')


def _dac_plug():
    ay = P.board_seat_y() + P.pcb_t + P.dac_jack_h/2
    hd = P.aux_plug_d
    x = P.dac_jack_x()
    pr = [box('plug head', (x - hd/2 - 0.5, ay - hd/2, P.dac_socket_z()),
              (x + hd/2 + 0.5, ay + hd/2, P.dac_socket_z() + P.dac_aux_plug), 'black')]
    return Comp('AUX plug (DAC)', 'voice', pr, follows='PCM5102A', mates=('PCM5102A',),
                note='right-angle; the cable leaves downward into the sleeve')


def _mic():
    x, y = P.mic_pos
    zb = P.wall - P.mic_seat_depth             # board's front face, on the gasket
    pr = [cbox('PCB', (x, y, zb + P.pcb_t/2), (P.mic_board_w, P.mic_board_l, P.pcb_t), 'pcb_dark',
               outside=True)]
    # No MEMS package drawn: the board lies flat on its gasket and the port is a hole through
    # the PCB (voice-case's printed, working seat), so nothing stands on the gasket side. Where
    # the package sits on the back is not known, and the clamp pad presses the back's centre.
    hw, hh, hl = P.mic_hdr
    yh = y - P.mic_board_l/2 + 1.5
    pr.append(box('header + duponts', (x - hw/2, yh - hh/2, zb + P.pcb_t),
                  (x + hw/2, yh + hh/2, zb + P.pcb_t + P.s3_dupont_h), 'black'))
    top = P.top_face(P.voice_h)
    return Comp('INMP441', 'voice', [to_world(p, top) for p in pr],
                moves={'x': ('mic_pos', 0), 'z': ('mic_pos', 1)},
                note='in the gasket seat on the TOP face, port up; the clamp presses it')


def _tactile():
    x, y = P.btn_pos
    s = P.sw_body
    pr = [box('body', (x - s/2, y - s/2, P.sw_top_z()), (x + s/2, y + s/2, P.bh_relief_z1()), 'black'),
          cyl('plunger', 'z', (x, y), P.sw_plunger_d, P.plunger_z(), P.sw_top_z(), 'metal')]
    for px, py in P.sw_pin_pos():
        pr.append(cbox('pin', (x + px, y + py, (P.bh_relief_z1() + P.sw_pin_z1())/2),
                       (0.8, 0.8, P.sw_pin_z1() - P.bh_relief_z1()), 'metal'))
    return Comp('tactile switch', 'voice', pr,
                moves={'x': ('btn_pos', 0), 'y': ('btn_pos', 1)},
                note='11 mm tactile in the button holder; moving it moves the whole button')


def _voice_leads():
    """Both cables that cross the box interface, in VOICE-box coordinates (the amp box is
    voice_z0() lower, so an amp-local y becomes y - voice_z0())."""
    dz = P.voice_z0()
    ya = lambda y: y - dz
    zc = P.sleeve_zc()
    # patch: DAC plug's underside -> down the sleeve -> along the amp's top -> AUX plug's top
    xp, zp = P.sleeve_x - 2, zc - 2
    xd = P.dac_jack_x()
    zd = P.dac_socket_z() + P.dac_aux_plug - P.aux_plug_d/2
    yd = P.board_seat_y() + P.pcb_t + P.dac_jack_h/2 - P.aux_plug_d/2
    y_hi = ya(P.amp_h() - P.wall - 3)
    ax = P.amp_x + P.amp_aux_x
    az = P.plug_z0() + P.aux_plug_barrel/2
    atop = ya(P.amp_pcb_top() + P.amp_aux_axis + P.aux_plug_d/2 + 4)
    patch = route('patch cable', [(xd, yd, zd), (xd, P.tray_top() + 2, zd), (xp, P.tray_top() + 2, zd),
                                  (xp, P.tray_top() + 2, zp), (xp, y_hi, zp), (ax, y_hi, zp),
                                  (ax, y_hi, az), (ax, atop, az)], P.patch_cable_d)
    # 5 V: MP1584's OUT end -> up -> sleeve -> devkit's rear header row (5V pin end, -x)
    xl, zl = P.sleeve_x + 3, zc + 2
    xo = P.mp_x + P.mp_w/2 - 1
    ym = ya(P.wall + P.sled_t + 1.5)
    yh = P.board_seat_y() + P.pcb_t + P.s3_dupont_h
    x5 = P.s3_x - 26
    z5 = P.s3_zc() + P.s3_l/2 - 1.87
    lead = route('5 V lead', [(xo, ym, P.mp_zc()), (xo, ym, zl), (xo, y_hi - 2, zl), (xl, y_hi - 2, zl),
                              (xl, yh + 2, zl), (x5, yh + 2, zl), (x5, yh + 2, z5), (x5, yh, z5)],
                  P.lead_d)
    return [Comp('voice wiring', 'voice', patch + lead, follows='(routes)',
                 note='patch cable and 5 V lead through the sleeve — illustrative routes')]


def components():
    """Every part, freshly derived from the current parameters."""
    return ([_amp(), _knobs(), _mp1584(), _psw()] + _amp_plugs() + _amp_leads()
            + [_devkit(), _dac(), _dac_plug(), _mic(), _tactile()] + _voice_leads())


def by_name():
    return {c.name: c for c in components()}


# =====================================================================================
# printed obstacles — what a dragged part can run into that is not another part
# =====================================================================================
def obstacles(where):
    """[(name, lo, hi)] in the box's local frame. Conservative boxes, not the exact shapes."""
    h = P.amp_h() if where == 'amp' else P.voice_h
    d = P.box_d()
    ih = P.inner_w()/2
    out = []
    for i, (x, y) in enumerate(P.lid_boss_pts(h)):
        up = y > h/2
        ylo, yhi = (y - P.lid_boss_od/2, h - P.wall) if up else (P.wall, y + P.lid_boss_od/2)
        out.append(('lid boss', (x - P.lid_boss_od/2, ylo, d - P.lid_boss_len),
                    (x + P.lid_boss_od/2, yhi, d)))
    floor = P.wall + (P.sled_t if where == 'amp' else P.tray_t)
    out.append(('sled' if where == 'amp' else 'tray', (-ih, P.wall, P.wall), (ih, floor, d)))
    if where == 'amp':
        # sleeve end, reaching sleeve_engage down through the top
        r = P.sleeve_od()/2
        out.append(('sleeve', (P.sleeve_x - r, h - P.wall - P.sleeve_engage, P.sleeve_zc() - r),
                    (P.sleeve_x + r, h, P.sleeve_zc() + r)))
        r = P.sled_boss_od/2
        for x, z in P.sled_screw_pts():
            out.append(('hold-down boss', (x - r, floor, z - r), (x + r, floor + P.sled_boss_h, z + r)))
        for hx, hr in P.amp_holes:
            r = P.amp_standoff_od/2
            out.append(('standoff', (P.amp_x + hx - r, floor, P.amp_bz(hr) - r),
                        (P.amp_x + hx + r, P.amp_pcb_y(), P.amp_bz(hr) + r)))
    else:
        x, y = P.btn_pos
        out.append(('button holder', (x - (P.btn_pilot_pitch + P.bh_ear_d)/2, y - P.bh_collar_od()/2,
                                      P.wall), (x + (P.btn_pilot_pitch + P.bh_ear_d)/2,
                                                y + P.bh_collar_od()/2, P.bh_z1())))
        x, z = P.mic_pos
        w, _ = P.mic_size()
        h = P.voice_h
        out.append(('mic posts + clamp', (x - w/2, h - P.wall - P.mic_post_h - P.mic_clamp_t,
                                          z - P.mic_clamp_w/2), (x + w/2, h - P.wall, z + P.mic_clamp_w/2)))
        r = P.sleeve_od()/2 + P.sleeve_flange
        out.append(('sleeve flange', (P.sleeve_x - r, P.tray_top(), P.sleeve_zc() - r),
                    (P.sleeve_x + r, P.tray_top() + 1.6, P.sleeve_zc() + r)))
    return out


# which printed obstacle each part is ALLOWED to sit in or on
OBSTACLE_MATES = {
    'tactile switch': {'button holder'},
    'INMP441': {'mic posts + clamp'},
    'ZK-502MT': {'standoff'},
}
