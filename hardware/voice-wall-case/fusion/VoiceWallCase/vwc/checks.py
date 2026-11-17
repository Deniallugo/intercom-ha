"""Design checks: the layout's own constraints, then the electronics.

The first half is geometry the case depends on (does the devkit fit across, do the knobs grip,
does the flexure button stay inside its stress budget, do the knob names fit...). The second is
every electronic part (``elec.py``) against every other one, against the box's cavity, and
against the printed obstacles in it. That half is what makes dragging a part in Fusion safe —
move the DAC into the button bridge, run `sync`, and the build refuses with the two names
instead of a case that quietly does not close.

Pure CPython, no adsk: ``python3 vwc/checks.py`` (or ``../test.sh``) runs it anywhere, and the
Fusion script runs it BEFORE modelling and builds nothing on a design that fails.
"""

import math
import sys

try:
    from . import elec, params as P, xf
except ImportError:                        # run directly, not as a package
    import elec
    import params as P
    import xf


class Checks:
    def __init__(self):
        self.failures = []

    def ok(self, cond, msg):
        if not cond:
            self.failures.append(msg)
        return cond


def within(v, lo, hi):
    return lo <= v <= hi


def _overlap(a, b, eps=0.05):
    """two AABBs share volume (touching faces do not count)"""
    (alo, ahi), (blo, bhi) = a, b
    return all(alo[k] < bhi[k] - eps and blo[k] < ahi[k] - eps for k in range(3))


def run_checks():
    c = Checks()
    ok = c.ok
    ih = P.ih()
    (clo, chi) = P.cavity()

    # ===================== envelope =====================
    x0, x1 = P.col_x()
    ok(x1 - x0 >= P.s3_pocket()[1] + 0.5, 'devkit column (%.1f) too narrow' % (x1 - x0))
    x0, x1 = P.col_r_x()
    ok(x1 - x0 >= max(2*P.dac_block_x(), P.mp_ring()[0]) + 0.5,
       'DAC / MP1584 column (%.1f) too narrow' % (x1 - x0))
    ok(abs(P.amp_x) <= 0.05, 'knobs %.1f mm off the middle — keep amp_x at 0' % P.amp_x)
    ok(P.box_h() <= 250 and P.box_w <= 250 and P.box_d <= 250, 'a part exceeds the A1 bed')

    # ===================== amp =====================
    ok(P.amp_standoff_len() >= P.amp_tail_h + 2.5, 'standoffs leave no room for wires behind the board')
    ok(P.knob_proj() >= P.knob_min_grip,
       'only %.1f mm of shaft above the top — knobs will not grip' % P.knob_proj())
    ok(P.face_gap + P.nut_recess_depth >= 2.0, 'no room for the pot nuts between the faceplate and the top')
    ok(P.wall - P.nut_recess_depth >= 2.0, 'nut recesses leave the top wall too thin')
    ok(P.amp_dc_plug_len > P.connector_y() + 5, 'DC plug too short to reach the jack from under the box')
    ok(P.connector_y() - P.aux_plug_barrel >= P.wall + 4, 'right-angle AUX plug within 4 mm of the bottom: it will push the amp off its mounts')
    f0, f1 = P.face_span_z()
    ok(f0 > P.wall + P.lip_d and f1 < P.plate_z(), 'faceplate runs out of the box')
    ok(P.plate_z() - P.amp_standoff_len() - P.amp_env_h >= P.wall + 1,
       'the amp\'s tallest parts reach the panel')

    # ===================== devkit =====================
    usb = xf.apply(P.s3_xf(), (-P.s3_w/2, 0, 0))            # the USB end of the board, in B
    ok(abs(usb[1] - (P.s3_pos[1] - P.s3_w/2)) < 0.01,
       'the devkit\'s USB end does not face its window in the bottom — check s3_orient')
    ok(P.usb_setback() <= 7, 'USB-C receptacles %.1f mm in from the bottom — a plug will not reach'
       % P.usb_setback())

    # ===================== DAC =====================
    ok(P.plate_z() - P.dac_pcb_top_y() - P.s3_dupont_h >= P.wall + P.lip_d + 0.5,
       'DAC duponts reach the panel')
    ok(P.dac_axis_y() - P.aux_plug_d/2 >= -P.dac_plug_groove + 0.3, 'DAC plug head digs into the plate past its groove')
    ok(P.dac_recess_y0() >= -(P.plate_t - 1.5), 'DAC socket recess leaves the plate too thin')

    # ===================== knob names =====================
    names = P.label_xs()
    for (xa, na), (xb, nb) in zip(names, names[1:]):
        ok(abs(xa - xb) - (P.label_w(na) + P.label_w(nb))/2 >= 2,
           'knob names "%s" and "%s" run into each other — shorten them or drop label_h' % (na, nb))
    for x, n in names:
        ok(abs(x) + P.label_w(n)/2 < P.box_w/2 - P.front_chamfer - 2, 'knob name "%s" runs off the face' % n)
    ok(P.label_y() + P.label_h/2 <= P.box_h() - P.front_chamfer - 0.5, 'knob names run into the top chamfer')
    ok(P.btn_pos[1] + P.btn_r_out() + 2 <= P.label_y() - P.label_h/2, 'knob names run into the button')
    ok(P.wall - P.label_depth >= 2, 'labels leave the panel too thin')

    # ===================== flexure button =====================
    ok(P.btn_arm_w() >= 1.6, 'flexure arms narrower than 1.6 mm')
    ok(P.btn_arm_len() >= 15, 'flexure arms too short to bend (%.1f mm)' % P.btn_arm_len())
    ok(P.btn_junction() >= 1.5, 'disc-to-arm junction thinner than 1.5 mm — shorten btn_arc_in')
    ok(P.btn_arc_in < 120 and P.btn_arc_in + P.btn_arc_out < 120 + P.btn_arc_in,
       'flexure slots run into each other')
    ok(P.btn_stress() <= P.petg_allow,
       'flexure arms stressed %.1f MPa at %.1f mm travel — over %g' % (P.btn_stress(), P.btn_travel, P.petg_allow))
    ok(P.btn_preload < P.sw_travel - 0.3, 'preload eats the switch travel')
    ok(P.sw_tip_z() > P.wall + 0.5, 'switch plunger reaches the disc')
    ok(P.bridge_foot_r - P.bridge_post_od/2 > P.btn_r_out() + 0.2, 'bridge feet stand on the flexure ring')

    # ===================== mic =====================
    mw, mh = P.mic_size()
    ok(P.mic_pos[1] - mh/2 >= P.wall + P.lip_d + 0.3, 'mic seat runs into the panel lip')
    ok(abs(P.mic_pos[0]) + mw/2 < ih - 0.5, 'mic seat runs into a side wall')
    ok(P.mic_grille_d() <= P.mic_gasket_d - 2, 'mic grille wider than the gasket seat')
    ok(P.mic_hole_d >= 1.2, 'mic grille holes under 1.2 mm print shut')

    # ===================== holes in the bottom and the top, pairwise =====================
    def apart(feats, where):
        for i, (na, (xa, za), ra, la) in enumerate(feats):
            ok(abs(xa) + ra < ih - 1, '%s off the %s' % (na, where))
            for nb, (xb, zb), rb, lb in feats[i + 1:]:
                ok(abs(xa - xb) >= ra + rb + 1.5 or abs(za - zb) >= la + lb + 1.5,
                   '%s and %s run into each other in the %s' % (na, nb, where))
    mx, mz = P.mic_pos
    feats = [('DC plug hole', P.dc_hole_pt(), P.dc_hole_d()/2, P.dc_hole_d()/2),
             ('USB window', (P.s3_pos[0], P.s3_usb_z()), P.s3_usb_w()/2 + P.usb_cb_margin,
              P.s3_usb_h/2 - P.s3_usb_trim + P.usb_cb_margin)]
    feats += [('speaker hole', c, P.spk_hole_d/2, P.spk_hole_d/2) for c in P.spk_hole_pts()]
    feats += [('panel screw', c, P.m3_cs_d/2, P.m3_cs_d/2) for c in P.pboss_screw_pts()]
    feats += [('bottom vent', (x, P.vent_zc()), P.vent_w/2, P.vent_len/2) for x in P.bottom_vent_xs]
    apart(feats, 'bottom')
    hz0, hz1 = P.hook_window()
    tops = [('knob hole', (x, P.knob_z()), P.nut_recess_d/2, P.nut_recess_d/2) for x, _ in P.knob_xs()]
    tops += [('top vent', (x, z), ln/2, P.vent_w/2) for x, z, ln in P.top_vents()]
    vx = sorted(round(x, 6) for x, _, _ in P.top_vents())
    ok(all(abs(a + b) < 1e-6 for a, b in zip(vx, reversed(vx))), 'top vents are not mirrored left to right')
    ok(all(abs(a + b) < 1e-6 for a, b in zip(sorted(P.hook_xs), sorted(P.hook_xs)[::-1])), 'hooks are not mirrored')
    tops += [('hook window', (x, (hz0 + hz1)/2), P.hook_w/2 + 0.5, (hz1 - hz0)/2) for x in P.hook_xs]
    tops += [('mic seat', P.mic_pos, mw/2, mh/2)]
    apart(tops, 'top')

    # ===================== wall mounting =====================
    ok(P.plate_t - P.kh_lip >= 2.5, 'keyhole pocket too shallow for a screw head')
    ok(P.kh_lip >= 1.8, 'keyhole lip too thin to hang the box from')
    ok(len(P.kh_pts) >= 2 and abs(P.kh_pts[0][0] - P.kh_pts[1][0]) >= 25, 'keyholes too close together to hang level')
    for x, y in P.kh_pts:
        # the whole keyhole (entry + slot + pocket) and the standoff pilots that reach into the plate
        y0, y1 = y - P.kh_head/2, y + P.kh_drop + P.kh_head/2
        ok(P.amp_x0() + P.kh_head/2 + 1 < x < P.amp_x1() - P.kh_head/2 - 1, 'keyhole outside the amp\'s footprint')
        for sx, sy in P.standoff_pts():
            dy = max(y0 - sy, sy - y1, 0)
            ok(math.hypot(x - sx, dy) > P.kh_head/2 + P.amp_standoff_od/2 + 1, 'keyhole runs into a standoff')
    lx, ly = P.lock_pt
    ok(ly + P.ws_head_d/2 < P.connector_y() - 1, 'locking screw is behind the amp — it must be reachable')
    for kx, ky in P.knockout_pts():
        ok(math.hypot(lx - kx, ly - ky) > (P.ws_head_d + P.knockout_d)/2 + 1, 'locking screw in a knock-out')

    board_screws(c)
    electronics(c)
    return c.failures


def board_screws(c):
    """a mounting screw's head must sit on bare board, not under a part on the same board"""
    hd = P.amp_screw_head[0]/2 + 0.5
    zk = elec.by_name()['ZK-502MT']
    for hx, hr in P.amp_holes:
        x, z = P.amp_x + hx, P.amp_bz(hr)
        for p in zk.prims:
            if p.name in ('PCB', 'screw head', 'faceplate') or p.outside:
                continue
            lo, hi = p.aabb()
            if lo[1] > P.amp_pcb_top() + 0.5:
                continue
            c.ok(not (lo[0] < x + hd and hi[0] > x - hd and lo[2] < z + hd and hi[2] > z - hd),
                 'amp board screw at (%g, %g) lands under the %s' % (x, z, p.name))


def electronics(c):
    """Parts vs parts, parts vs the cavity, parts vs the printed obstacles — all in box-local B."""
    comps = elec.components()
    cavity = P.cavity()
    obst = elec.obstacles()
    placed = [(k, elec.in_box(k)) for k in comps]
    for k, prims in placed:
        for p in prims:
            if p.soft:
                continue
            bb = p.aabb()
            if not p.outside:
                lo, hi = bb
                inside = all(cavity[0][i] - 0.01 <= lo[i] and hi[i] <= cavity[1][i] + 0.01 for i in range(3))
                c.ok(inside, '%s / %s leaves the box cavity' % (k.name, p.name))
            allowed = elec.OBSTACLE_MATES.get(k.name, set())
            for oname, olo, ohi in obst:
                if oname not in allowed:
                    c.ok(not _overlap(bb, (olo, ohi)), '%s / %s runs into the %s' % (k.name, p.name, oname))
    for i, (a, pa) in enumerate(placed):
        for b, pb in placed[i + 1:]:
            if b.name in a.mates or a.name in b.mates:
                continue
            hit = _first_clash(pa, pb)
            if hit:
                c.ok(False, '%s / %s overlaps %s / %s' % (a.name, hit[0], b.name, hit[1]))
    names = list(obst)
    for i, (na, la, ha) in enumerate(names):
        for nb, lb, hb in names[i + 1:]:
            if any({na, nb} <= g for g in _SAME_PART):
                continue
            c.ok(not _overlap((la, ha), (lb, hb)), 'printed %s runs into the %s' % (na, nb))


# printed obstacles that are one printed part, and are allowed to touch
_SAME_PART = ({'button travel', 'button nub', 'bridge pad', 'bridge foot'},
              {'DAC seat', 'MP1584 pocket'},
              {'panel lip', 'panel hook', 'panel boss'})


def _first_clash(pa, pb):
    for p in pa:
        if p.soft:
            continue
        for q in pb:
            if not q.soft and _overlap(p.aabb(), q.aabb()):
                return (p.name, q.name)
    return None


def report():
    return [
        'ENVELOPE  %g x %g x %g (W x H x D), %.2f L — sticks out %g mm from the wall'
        % (P.box_w, P.box_h(), P.box_d, P.box_w*P.box_h()*P.box_d/1e6, P.box_d),
        'AMP       plate front at z %g, faceplate under the top at y %g, knob shafts %.1f above the top,'
        ' connector faces at y %g' % (P.plate_z(), P.face_top_y(), P.knob_proj(), P.connector_y()),
        'BUTTON    disc %g, arms %.1f x %.1f x %g, %.1f N/mm, %.1f MPa at %g mm, junction %.1f'
        % (P.btn_disc_d, P.btn_arm_len(), P.btn_arm_w(), P.btn_flex_t, P.btn_stiffness(), P.btn_stress(),
           P.btn_travel, P.btn_junction()),
        'PARTS     %d electronic components, %d primitives'
        % (len(elec.components()), sum(len(k.prims) for k in elec.components())),
    ]


def main():
    failures = run_checks()
    for line in report():
        print('  ' + line)
    if failures:
        print('\nFAIL — %d design check(s):' % len(failures))
        for f in failures:
            print('  - ' + f)
        return 1
    print('\nOK — all design checks pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
