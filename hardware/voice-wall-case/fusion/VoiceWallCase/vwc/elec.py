"""Every electronic part in the unit, as data — pure Python, no adsk.

One description, three consumers:
  * ``electronics.py`` builds each entry as its own Fusion component (inside the "electronics"
    group), so it shows up in the browser, can be hidden, measured, or DRAGGED;
  * ``checks.py`` tests every pair of parts for overlap and every part against the box's
    cavity and the printed obstacles in it (standoffs, pockets, posts, the button bridge);
  * ``sync.py`` maps a drag in Fusion back to the placement number that moved it.

Each part is drawn in the frame its numbers are measured in (``params`` docstring):
  where = 'amp'   the ZK-502MT and what plugs into it, in the A frame; ``params.amp_xf()`` puts
                  it in the box;
  where = 'unit'  everything else, already in box-local B (front-wall boards are drawn in their
                  tray frame and put on the plate or the tower here, with ``params.plate_xf()``).
``in_box(comp)`` gives any part's primitives in B; ``box_xf(where)`` takes its frame to the world.

The shapes are DUMMIES. Board outlines, connector positions and heights come from
``params.py`` and carry its tags; the bodies standing on them (pot cans, jack bodies, the
WROOM can, dupont housings, plug heads) are [assumed] typical sizes. They are there to be
seen and to collide, not to be trusted to 0.1 mm.

Kinds of primitive:
  box     axis-aligned, `lo`..`hi`
  cyl     along `axis`, centre `c` in the other two axes in (x, y, z) order, `d`, `a0`..`a1`
Flags:
  outside   deliberately outside the cavity (a knob, a shaft through the top) — skipped by the
            cavity check, still checked against other parts
  soft      a cable: drawn, never checked. Cables bend; the routes are illustrations
"""

try:
    from . import params as P, xf
except ImportError:
    import params as P
    import xf


def box_world():
    """B -> world: the box on the wall, front face box_d out, bottom on z = 0"""
    return xf.mul(xf.T(0, P.box_d, 0), xf.Rx(90))


def frame(where):
    """the part's own frame -> B"""
    return P.amp_xf() if where == 'amp' else xf.IDENTITY


def box_xf(where):
    """the part's own frame -> world"""
    return xf.mul(box_world(), frame(where))


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
# amplifier, A frame
# =====================================================================================
def _amp():
    ax = P.amp_x
    y0, y1 = P.amp_pcb_y(), P.amp_pcb_top()
    zf = P.amp_front_z()                       # faceplate front face
    zp = zf + P.amp_face_t                     # PCB front edge, behind the faceplate
    zr = P.amp_rear_z()                        # PCB rear edge
    pr = [
        box('PCB', (ax - P.amp_w/2, y0, zp), (ax + P.amp_w/2, y1, zr), 'pcb_dark'),
        # the faceplate lies just under the top wall; the pot nuts sit in the face_gap above it
        cbox('faceplate', (ax + P.amp_face_x, P.amp_face_y() + P.amp_face_h/2, zf + P.amp_face_t/2),
             (P.amp_face_w, P.amp_face_h, P.amp_face_t), 'black'),
        cbox('heatsink', (ax + P.amp_hs[0], (y1 + P.amp_env_top())/2, P.amp_bz(P.amp_hs[1])),
             (P.amp_hs[2], P.amp_env_top() - y1, P.amp_hs[3]), 'alu'),
    ]
    axis_y = y0 + P.ctrl_axis
    for i in (-1, 0, 1):
        x = ax + P.ctrl_x0 + i*P.ctrl_pitch
        bw, bd, bh = P.amp_pot_body
        pr.append(box('pot', (x - bw/2, y1, zp), (x + bw/2, y1 + bh, zp + bd), 'metal'))
        # bushing + nut through the faceplate, and the shaft out of the box
        # into the knob hole in the top: through a wall on purpose, so "outside" the cavity
        pr.append(cyl('bushing', 'z', (x, axis_y), P.ctrl_bush_d, zf - 1.5, zp, 'metal', outside=True))
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
    for cx, cr in P.amp_caps:                  # the two big electrolytics: tallest after the heatsink
        pr.append(cyl('470 uF cap', 'y', (ax + cx, P.amp_bz(cr)), P.amp_cap_d, y1, y1 + P.amp_cap_h, 'metal'))
    sx, sz = P.amp_sw_onboard_at
    w, d, h = P.amp_sw_onboard
    pr.append(cbox('onboard switch', (ax + sx, y1 + h/2, P.amp_bz(sz)), (w, h, d), 'yellow'))
    # the four mounting screws' heads, so the standoffs visibly meet the board's holes
    hd, hh = P.amp_screw_head
    for hx, hr in P.amp_holes:
        pr.append(cyl('screw head', 'y', (ax + hx, P.amp_bz(hr)), hd, y1, y1 + hh, 'metal'))
    return Comp('ZK-502MT', 'amp', pr,
                moves={'x': ('amp_x', None), 'y': ('amp_lift', None)},
                note='upright on the back plate, parts facing the front, knobs up through the top')




def _knobs():
    pr = []
    axis_y = P.amp_pcb_y() + P.ctrl_axis
    z_top = P.top_z_a()                          # the top's outer face, as an A-frame z
    for x, _ in P.knob_xs():                     # A x == B x for the amp
        pr.append(cyl('knob', 'z', (x, axis_y), P.knob_d,
                      z_top - P.knob_gap - P.knob_h, z_top - P.knob_gap, 'knob', outside=True))
    return Comp('knobs', 'amp', pr, follows='ZK-502MT', mates=('ZK-502MT',),
                note='on the pot shafts, above the top')


def _amp_plugs():
    """right-angle plugs in the connector edge, which faces DOWN: head along the jack axis, the
    cable turning toward the plate"""
    y1 = P.amp_pcb_top()
    z0 = P.plug_z0()
    dx, dy = P.amp_x + P.amp_dc_x, y1 + P.amp_dc_axis
    # straight in from under the box, through the base: the body passes the bottom wall
    dc = [cyl('plug', 'z', (dx, dy), P.amp_dc_plug_d, z0, z0 + P.amp_dc_plug_len, 'black', outside=True)]
    dc += route('cable', [(dx, dy, z0 + P.amp_dc_plug_len), (dx, dy, z0 + P.amp_dc_plug_len + 25)],
                P.dc_cable_d)
    ax, ay = P.amp_x + P.amp_aux_x, y1 + P.amp_aux_axis
    hd = P.aux_plug_d
    aux = [box('plug head', (ax - hd/2 - 0.5, ay - hd/2, z0), (ax + hd/2 + 0.5, ay + hd/2 + 4,
                                                               z0 + P.aux_plug_barrel), 'black')]
    return [Comp('DC plug', 'amp', dc, follows='ZK-502MT', mates=('ZK-502MT',),
                 note='24 V in, straight up through the bottom of the base'),
            Comp('AUX plug (amp)', 'amp', aux, follows='ZK-502MT', mates=('ZK-502MT',),
                 note='right-angle; the patch cable from the DAC')]


def _amp_leads():
    y1 = P.amp_pcb_top()
    xc = P.amp_x + (P.amp_term_x[0] + P.amp_term_x[1])/2
    ys = y1 + P.amp_term_h/2
    zr, zo = P.amp_rear_z(), P.plug_z0() + P.plug_room + P.wall + 15
    spk = []
    for s in (-1, 1):                          # one cable per speaker, straight down and out
        spk += route('speaker leads', [(xc + s*P.spk_hole_dx, ys, zr), (xc + s*P.spk_hole_dx, ys, zo)],
                     P.spk_cable_d)
    return [Comp('amp wiring', 'amp', spk, follows='(routes)',
                 note='speaker leads straight down out of the bottom — illustrative')]


# =====================================================================================
# front wall: drawn in the tray frame, put on the wall
# =====================================================================================
def _placed(prims, x):
    return [to_world(p, x) for p in prims]


def _devkit():
    yb = P.tray_seat
    yt = yb + P.pcb_t
    pr = [cbox('PCB', (0, (yb + yt)/2, 0), (P.s3_w, P.pcb_t, P.s3_l), 'pcb_dark')]
    mx, mz, mh = P.s3_module
    pr.append(box('ESP32-S3 module', (P.s3_w/2 - mx, yt, -mz/2), (P.s3_w/2, yt + mh, mz/2), 'metal'))
    ux, uz, uh = P.s3_usb
    for s in (-1, 1):
        pr.append(box('USB-C', (-P.s3_w/2, yt, s*P.s3_usb_pitch/2 - uz/2),
                      (-P.s3_w/2 + ux, yt + uh, s*P.s3_usb_pitch/2 + uz/2), 'metal'))
    hw, _ = P.s3_hdr
    for s in (-1, 1):
        zr = s*(P.s3_l/2 - 1.27 - 0.6)
        pr.append(box('header + duponts', (-28, yt, zr - hw/2), (28, yt + P.s3_dupont_h, zr + hw/2),
                      'black'))
        pr.append(box('pin tails', (-28, yb - P.board_pin_h, zr - 0.8), (28, yb, zr + 0.8), 'metal'))
    return Comp('ESP32-S3 devkit', 'unit', _placed(pr, P.s3_xf()),
                moves={'x': ('s3_pos', 0), 'y': ('s3_pos', 1)},
                note='DevKitC-1 standing on the back plate, USB-C down through the bottom')


def dac_prims():
    """component side down on its seat, socket edge at tray +z (see params)"""
    yb, yt = P.dac_seat_y(), P.dac_pcb_top_y()
    pr = [cbox('PCB', (0, (yb + yt)/2, 0), (P.dac_l, P.pcb_t, P.dac_w), 'pcb_purple')]
    jw, jx = P.dac_jack_w, P.dac_jack_off()
    pr.append(box('3.5 mm socket', (jx - jw/2, yb - P.dac_jack_h, P.dac_edge_z() - P.dac_jack_depth),
                  (jx + jw/2, yb, P.dac_socket_z()), 'black', outside=True))   # into its recess in the plate
    xh, zh = P.dac_relief_x(), (P.dac_relief_z0() + P.dac_relief_z1())/2
    pr.append(box('header + duponts', (xh - 1.25, yt, zh - P.dac_hdr_len/2),
                  (xh + 1.25, yt + P.s3_dupont_h, zh + P.dac_hdr_len/2), 'black'))
    tl = 5*2.54 + 0.64
    pr.append(box('pin tails', (xh - 0.32, yb - P.board_pin_h, zh - tl/2), (xh + 0.32, yb, zh + tl/2),
                  'metal'))
    return pr


def _dac():
    return Comp('PCM5102A', 'unit', _placed(dac_prims(), P.dac_xf()),
                moves={'x': ('dac_pos', 0), 'y': ('dac_pos', 1)},
                note='I2S DAC, top of the right column, socket facing down')


def _dac_plug():
    ay, hd, x = P.dac_axis_y(), P.aux_plug_d, P.dac_jack_off()
    pr = [box('plug head', (x - hd/2 - 0.5, ay - hd/2, P.dac_socket_z()),
              (x + hd/2 + 0.5, ay + hd/2, P.dac_socket_z() + P.dac_aux_plug), 'black', outside=True)]  # in its groove
    return Comp('AUX plug (DAC)', 'unit', _placed(pr, P.dac_xf()), follows='PCM5102A',
                mates=('PCM5102A',), note='right-angle; the cable runs down beside the devkit')


def _mp1584():
    yb, yt = 0.0, 1.2
    pr = [cbox('PCB', (0, (yb + yt)/2, 0), (P.mp_w, yt - yb, P.mp_l), 'pcb_blue')]
    w, d, h = P.mp_inductor
    pr.append(cbox('inductor', (-4, yt + h/2, 0), (w, h, d), 'black'))
    w, d, h = P.mp_trim
    pr.append(cbox('trim pot', (6, yt + h/2, 4), (w, h, d), 'blue'))
    return Comp('MP1584', 'unit', _placed(pr, P.mp_xf()),
                moves={'x': ('mp_pos', 0), 'y': ('mp_pos', 1)},
                note='24 V -> 5 V buck, bottom of the right column. Set to 5.0 V BEFORE connecting')


def _mic():
    """lying in the top wall's seat, port facing UP through the grille"""
    x, z = P.mic_pos
    yt = P.box_h() - (P.wall - P.mic_seat_depth)    # board's outer face, on the gasket
    pr = [cbox('PCB', (x, yt - P.pcb_t/2, z), (P.mic_board_w, P.pcb_t, P.mic_board_l), 'pcb_dark',
               outside=True)]
    hw, hh, hl = P.mic_hdr
    zh = z - P.mic_board_l/2 + 1.5
    pr.append(box('header + duponts', (x - hw/2, yt - P.pcb_t - P.s3_dupont_h, zh - hh/2),
                  (x + hw/2, yt - P.pcb_t, zh + hh/2), 'black'))
    return Comp('INMP441', 'unit', pr, moves={'x': ('mic_pos', 0), 'z': ('mic_pos', 1)},
                note='in the gasket seat in the top beside the knobs, port up; the clamp presses it')


def _tactile():
    x, y = P.btn_pos
    s = P.sw_body
    pr = [box('body', (x - s/2, y - s/2, P.sw_front_z()), (x + s/2, y + s/2, P.sw_back_z()), 'black'),
          cyl('plunger', 'z', (x, y), P.sw_plunger_d, P.sw_tip_z(), P.sw_front_z(), 'metal')]
    for px, py in P.sw_pin_pos():
        a = xf.apply(xf.Rz(P.bridge_angle), (px, py, 0))     # pins turn with the bridge
        pr.append(cbox('pin', (x + a[0], y + a[1], P.sw_back_z() + P.sw_pin_len/2),
                       (0.8, 0.8, P.sw_pin_len), 'metal'))
    return Comp('tactile switch', 'unit', pr, moves={'x': ('btn_pos', 0), 'y': ('btn_pos', 1)},
                note='on the bridge behind the panel\'s flexure disc; the panel\'s only wires')


def _voice_leads():
    """Every board-to-board run, along the WIRE CHANNEL: the bottom front strip under the amp's
    connector edge, behind the panel. Illustrative routes — but they are what the channel is
    kept clear for."""
    yc = P.wall + 9                              # channel height, above the panel bosses
    zc = P.wall + P.lip_d + 6                    # channel depth, behind the panel's lip
    amp = P.amp_xf()
    aux = xf.apply(amp, (P.amp_x + P.amp_aux_x, P.amp_pcb_top() + P.amp_aux_axis,
                         P.plug_z0() + P.aux_plug_barrel - 1))
    plug = xf.apply(P.dac_xf(), (P.dac_jack_off(), P.dac_axis_y(), P.dac_socket_z() + P.dac_aux_plug - 1))
    patch = route('patch cable', [plug, (plug[0], yc, plug[2]), (plug[0], yc, zc), (aux[0], yc, zc),
                                  (aux[0], yc, aux[2]), (aux[0], aux[1] - 2, aux[2])], P.patch_cable_d)
    # devkit header (bottom end, left) -> along the channel -> DAC header / MP1584 OUT (right)
    s3 = xf.apply(P.s3_xf(), (-P.s3_w/2 + 6, P.tray_seat + P.pcb_t + P.s3_dupont_h, 0))
    dac = xf.apply(P.dac_xf(), (P.dac_relief_x(), P.dac_pcb_top_y() + P.s3_dupont_h, 0))
    i2s = route('I2S lead', [s3, (s3[0], yc + 2, s3[2]), (s3[0], yc + 2, zc), (dac[0], yc + 2, zc),
                             (dac[0], dac[1], zc), (dac[0], dac[1], dac[2])], P.lead_d)
    mp = xf.apply(P.mp_xf(), (P.mp_w/2 - 1, P.mp_lip, 0))
    v5 = route('5 V lead', [mp, (mp[0], mp[1], zc + 3), (mp[0], yc + 4, zc + 3), (s3[0] - 3, yc + 4, zc + 3),
                            (s3[0] - 3, s3[1], zc + 3)], P.lead_d)
    return [Comp('voice wiring', 'unit', patch + i2s + v5, follows='(routes)',
                 note='patch cable, I2S and 5 V along the bottom wire channel — illustrative')]


def components():
    """Every part, freshly derived from the current parameters."""
    return ([_amp(), _knobs()] + _amp_plugs() + _amp_leads()
            + [_devkit(), _dac(), _dac_plug(), _mp1584(), _mic(), _tactile()] + _voice_leads())


def by_name():
    return {c.name: c for c in components()}


def in_box(comp):
    """the part's primitives in box-local B"""
    if comp.where == 'unit':
        return list(comp.prims)
    x = P.amp_xf()
    return [to_world(p, x) for p in comp.prims]


# =====================================================================================
# printed obstacles — what a dragged part can run into that is not another part
# =====================================================================================
def obstacles():
    """[(name, lo, hi)] in B. Conservative boxes, not the exact shapes."""
    out = []
    pz = P.plate_z()
    for x, y in P.standoff_pts():
        r = P.amp_standoff_od/2
        out.append(('standoff', (x - r, y - r, pz - P.amp_standoff_len()), (x + r, y + r, pz)))
    for name, (lo, hi) in seat_boxes().items():
        out.append((name, lo, hi))
    x, z = P.mic_pos
    w, h = P.mic_size()
    top = P.box_h() - P.wall
    out.append(('mic posts + clamp', (x - w/2, top - P.mic_post_h - P.mic_clamp_t, z - h/2), (x + w/2, top, z + h/2)))
    # the panel: the disc's travel and the nub, the bridge and its feet, the lip, hooks, bosses
    bx, by = P.btn_pos
    r = P.btn_r_out()
    out.append(('button travel', (bx - r, by - r, P.wall), (bx + r, by + r, P.wall + P.btn_travel)))
    rn = P.btn_nub_d/2
    out.append(('button nub', (bx - rn, by - rn, P.wall), (bx + rn, by + rn, P.btn_nub_end())))
    for fx, fy in P.bridge_feet():
        rp = max(P.bridge_post_od, P.bridge_w)/2
        out.append(('bridge foot', (fx - rp, fy - rp, P.wall), (fx + rp, fy + rp, P.bridge_back_z())))
    hp = P.bridge_pad/2
    out.append(('bridge pad', (bx - hp, by - hp, P.bridge_z()), (bx + hp, by + hp, P.bridge_back_z())))
    ih, h = P.ih(), P.box_h()
    lip = P.lip_t + P.clr
    zl = (P.wall, P.wall + P.lip_d)
    for lo, hi in (((-ih, P.wall, zl[0]), (ih, P.wall + lip, zl[1])),
                   ((-ih, h - P.wall - lip, zl[0]), (ih, h - P.wall, zl[1])),
                   ((-ih, P.wall, zl[0]), (-ih + lip, h - P.wall, zl[1])),
                   ((ih - lip, P.wall, zl[0]), (ih, h - P.wall, zl[1]))):
        out.append(('panel lip', lo, hi))
    for x in P.hook_xs:
        out.append(('panel hook', (x - P.hook_w/2, h - P.wall - lip - 1, P.wall),
                    (x + P.hook_w/2, h - P.wall, P.wall + P.hook_len + 3)))
    z0, z1 = P.pboss_z()
    for x in P.pboss_xs:
        r = P.pboss_od/2
        out.append(('panel boss', (x - r, P.wall, z0), (x + r, P.wall + P.pboss_od, z1)))
    return out


def seat_boxes():
    """the devkit pocket, the MP1584 pocket and the DAC seat, as B boxes"""
    def bx(lo, hi, x):
        p = to_world(box('x', lo, hi, ''), x)
        return (p.lo, p.hi)
    sp = P.s3_pocket()
    rx, rz = P.mp_ring()
    return {
        'devkit pocket': bx((-sp[0]/2, -0.01, -sp[1]/2), (sp[0]/2, P.s3_pocket_h(), sp[1]/2), P.s3_xf()),
        'DAC seat': bx((-P.dac_block_x(), -0.01, P.dac_block_z0()),
                       (P.dac_block_x(), P.dac_block_top(), P.dac_block_z1()), P.dac_xf()),
        'MP1584 pocket': bx((-rx/2, -0.01, -rz/2), (rx/2, P.mp_lip, rz/2), P.mp_xf()),
    }


# which printed obstacle each part is ALLOWED to sit in or on
OBSTACLE_MATES = {
    'ZK-502MT': {'standoff'},
    'ESP32-S3 devkit': {'devkit pocket'},
    'PCM5102A': {'DAC seat'},
    'AUX plug (DAC)': {'DAC seat'},
    'MP1584': {'MP1584 pocket'},
    'INMP441': {'mic posts + clamp'},
    'tactile switch': {'bridge pad', 'button nub'},
}
