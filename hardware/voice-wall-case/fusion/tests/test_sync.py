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
    world = xf.apply(assembly.place_box(0), (0, 10, 0))
    check(abs(world[1] - P.front_y()) < 1e-9 and abs(world[2] - 10) < 1e-9,
          'box-local front face lands at y = front_y() in the world, local y -> world z')
    check(abs(xf.det(assembly.PLATE_XF) - 1) < 1e-12, 'the plate placement is a rotation, not a mirror')
    check(abs(xf.det(assembly.place_box(0)) - 1) < 1e-12, 'the box placement is a rotation')

    print('== nothing that Fusion has to move is a group ==')
    scad_emit.OCCURRENCES.clear()
    d = Design()
    _, items = assembly.build(d, 'all')
    stuck = build.place_all(d, items)
    groups = [o for o in scad_emit.OCCURRENCES if o.component.name in (assembly.AMP_GROUP, assembly.VOICE_GROUP)]
    check(stuck == [] and all(xf.same_rotation(build.unmatrix(g.transform2), xf.IDENTITY)
                              and max(map(abs, build.unmatrix(g.transform2)[1])) < 1e-9 for g in groups),
          'both electronics groups stay at the identity, everything else is placed')

    print('== a fresh build has nothing to sync ==')
    d = built_document()
    moved, built = sync.read(d)
    check(moved == {}, 'no electronic part is off the identity after a build')
    check(built is not None and built['s3_z0'] == P.s3_z0, 'the build stamped its placement into the design')

    print('== drag, then sync ==')
    drag(d, 'ESP32-S3 devkit', (3, 1.5, -2))
    drag(d, 'INMP441', (0, 0, 4))
    drag(d, 'knobs', (5, 0, 0))
    drag(d, 'MP1584', (-1, 0, 0), rot=xf.Rz(10))
    moved, built = sync.read(d)
    check(set(moved) == {'ESP32-S3 devkit', 'INMP441', 'knobs', 'MP1584'}, 'read() sees exactly the four dragged parts')
    updates, notes = sync.plan(moved, built)
    check(updates.get('s3_x') == round(P.s3_x + 3, 1), 'devkit x drag -> s3_x')
    check(updates.get('s3_z0') == round(P.s3_z0 - 2, 1), 'devkit z drag -> s3_z0')
    check(list(updates.get('mic_pos') or []) == [P.mic_pos[0], P.mic_pos[1] + 4], 'mic z drag (along the top face) -> mic_pos[1]')
    check(updates.get('mp_x') == round(P.mp_x - 1, 1), 'MP1584 x drag -> mp_x, despite the rotation')
    check(any('ignored' in n and 'ESP32' in n and ' y' in n for n in notes), "devkit's y drag is reported as ignored")
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
    check(ns['s3_x'] == updates['s3_x'] and tuple(ns['mic_pos']) == tuple(updates['mic_pos']),
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
    saved = P.s3_z0
    P.s3_z0 = 10                                 # devkit dragged into the button holder
    f = checks.run_checks()
    P.s3_z0 = saved
    check(any('button holder' in x for x in f), 'devkit dragged into the button holder is refused')

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
