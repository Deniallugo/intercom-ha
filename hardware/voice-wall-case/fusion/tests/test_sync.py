"""The adjust-in-place loop, offline: drag a part in an (emulated) document, sync, rebuild.

    python3 test_sync.py

Runs the real ``vwc.sync`` against a document built by the real ``vwc.assembly`` through the
adsk stand-in, so the occurrence tree, the identity placement of every electronic part, the
box transforms and the stamped build placement are all the ones Fusion would see. Nothing here
writes the real placement.py — the rewrite is tested on a copy.
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'VoiceWallCase'))

import scad_emit                                                        # noqa: E402
Design = scad_emit.install()

from vwc import assembly, build, checks, elec, params as P, sync, xf    # noqa: E402

FAIL = []


def check(cond, msg):
    print('  %s %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        FAIL.append(msg)


def built_document():
    scad_emit.OCCURRENCES.clear()
    d = Design()
    _, items = assembly.build(d, 'all')
    build.place_all(d, items)
    return d


def occurrence(d, name):
    root = d.rootComponent
    for i in range(root.occurrences.count):
        box = root.occurrences.item(i)
        for j in range(box.component.occurrences.count):
            o = box.component.occurrences.item(j)
            if o.component.name == name:
                return o
    raise KeyError(name)


def drag(d, name, t, rot=None):
    """What a drag in Fusion does: the part (drawn in world coordinates, at the identity, in a
    group that never moves) gets a WORLD transform, set through its root proxy. `t` / `rot`
    are given in box-local terms, so they are turned into the world move first."""
    local = xf.T(*t) if rot is None else xf.mul(xf.T(*t), rot)
    o = occurrence(d, name)
    B = elec.box_xf(elec.by_name()[name].where)
    o.createForAssemblyContext(o.parent).transform2 = build.matrix(xf.chain(B, local, xf.inverse(B)))


def main():
    print('== transforms ==')
    m = build.unmatrix(build.matrix(xf.mul(xf.T(3, -4, 5), xf.Rx(90))))
    check(xf.same_rotation(m, xf.Rx(90)) and all(abs(a - b) < 1e-9 for a, b in zip(m[1], (3, -4, 5))),
          'matrix() / unmatrix() round-trip')
    world = xf.apply(elec.box_world(), (0, 10, 0))
    check(abs(world[1] - P.box_d) < 1e-9 and abs(world[2] - 10) < 1e-9,
          'box-local front face lands at y = box_d in the world, local y -> world z')
    check(abs(xf.det(elec.box_world()) - 1) < 1e-12, 'the box placement is a rotation')
    knob = xf.apply(P.amp_xf(), (P.ctrl_pitch, P.amp_pcb_y() + P.ctrl_axis, P.top_z_a()))
    check(abs(knob[1] - P.box_h()) < 1e-9 and knob[0] > 0,
          'the VOL pot comes out of the top on +x (the viewer\'s left)')

    print('== nothing that Fusion has to move is a group ==')
    scad_emit.OCCURRENCES.clear()
    d = Design()
    _, items = assembly.build(d, 'all')
    stuck = build.place_all(d, items)
    groups = [o for o in scad_emit.OCCURRENCES if o.component.name == assembly.ELEC_GROUP]
    check(stuck == [] and all(xf.same_rotation(build.unmatrix(g.transform2), xf.IDENTITY)
                              and max(map(abs, build.unmatrix(g.transform2)[1])) < 1e-9 for g in groups),
          'the electronics group stays at the identity, everything else is placed')

    print('== a fresh build has nothing to sync ==')
    d = built_document()
    moved, built = sync.read(d)
    check(moved == {}, 'no electronic part is off the identity after a build')
    check(built is not None and tuple(built['s3_pos']) == P.s3_pos, 'the build stamped its placement into the design')

    print('== drag, then sync ==')
    drag(d, 'ESP32-S3 devkit', (3, 1.5, -2))
    drag(d, 'INMP441', (0, 0, 2))
    drag(d, 'knobs', (5, 0, 0))
    drag(d, 'MP1584', (-1, 0, 0), rot=xf.Rz(10))
    drag(d, 'ZK-502MT', (2, 0, 0))
    moved, built = sync.read(d)
    check(set(moved) == {'ESP32-S3 devkit', 'INMP441', 'knobs', 'MP1584', 'ZK-502MT'},
          'read() sees exactly the five dragged parts')
    updates, notes = sync.plan(moved, built)
    check(list(updates.get('s3_pos') or []) == [round(P.s3_pos[0] + 3, 1), round(P.s3_pos[1] + 1.5, 1)],
          'devkit x / y drag -> s3_pos')
    check(list(updates.get('mic_pos') or []) == [P.mic_pos[0], P.mic_pos[1] + 2], 'mic z drag (along the bottom) -> mic_pos[1]')
    check(list(updates.get('mp_pos') or [])[0] == round(P.mp_pos[0] - 1, 1), 'MP1584 x drag -> mp_pos, despite the rotation')
    check(updates.get('amp_x') == round(P.amp_x + 2, 1), 'amp drag along its own x -> amp_x')
    check(any('ignored' in n and 'ESP32' in n and ' z' in n for n in notes), "devkit's z drag is reported as ignored")
    check(any(n.startswith('knobs follows') for n in notes), 'a following part is reported, not synced')
    check(any('rotated' in n and 'MP1584' in n for n in notes), 'a rotation is reported, not synced')
    check('btn_pos' not in updates, 'nothing else changes')

    print('== a second sync without a rebuild does not double count ==')
    again, _ = sync.plan(*sync.read(d))
    check(again == updates, 'same document, same answer — moves are added to the BUILT placement')

    print('== placement.py rewrite ==')
    src = open(sync.placement_path()).read()
    new = sync.rewrite(src, updates)
    ns = {}
    exec(compile(new, 'placement.py', 'exec'), ns)
    check(tuple(ns['s3_pos']) == tuple(updates['s3_pos']) and tuple(ns['mic_pos']) == tuple(updates['mic_pos']),
          'the rewritten file reads back the new values')
    old_lines, new_lines = src.splitlines(), new.splitlines()
    changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
    check(len(old_lines) == len(new_lines) and len(changed) == len(updates),
          'exactly one line per updated name changed (%d)' % len(changed))
    check(all('#' in new_lines[i] for i in changed), 'their comments survived')
    tmp = os.path.join(tempfile.mkdtemp(), 'placement.py')
    with open(tmp, 'w') as fh:
        fh.write(new)

    print('== the checks catch a bad drag ==')
    saved = P.dac_pos
    P.dac_pos = (5, P.dac_pos[1])               # DAC dragged over the amp
    f = checks.run_checks()
    P.dac_pos = saved
    check(any('PCM5102A' in x and 'ZK-502MT' in x for x in f), 'DAC dragged onto the amp is refused')

    print('== every movable axis maps to a real placement number ==')
    for k in elec.components():
        for axis, (name, idx) in k.moves.items():
            v = getattr(P, name, None)
            check(v is not None and (idx is None) == (not isinstance(v, tuple)),
                  '%s.%s -> %s%s' % (k.name, axis, name, '' if idx is None else '[%d]' % idx))

    print('\n%s' % ('OK — sync round-trips' if not FAIL else 'FAIL: %d' % len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
