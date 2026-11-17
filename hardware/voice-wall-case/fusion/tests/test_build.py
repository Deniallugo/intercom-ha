"""Build every part through the adsk stand-in — no Fusion, no OpenSCAD.

    python3 test_build.py

Runs the real build code (``vwc.case``, ``vwc.assembly``, ``vwc.build``) against the emulator in
``scad_emit.py``, which enforces the Fusion behaviours that have bitten this port before:
sketches that must close into exactly one profile, arcs whose ends swap on mirrored planes,
nested-occurrence transforms, grounded first components. A printed part must come out as ONE
body. It also tries the whole build with the sketch planes' axes laid out every other way
Fusion could hand them over, so nothing depends on a guess about plane orientation.
"""

import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'VoiceWallCase'))

import scad_emit                                                        # noqa: E402
Design = scad_emit.install()

from vwc import assembly, build, xf                                     # noqa: E402

FAIL = []
X, Y, Z = scad_emit.X, scad_emit.Y, scad_emit.Z
NX, NY, NZ = scad_emit.NX, scad_emit.NY, scad_emit.NZ
VARIANTS = {
    'conventional': {'xy': (X, Y), 'yz': (Y, Z), 'xz': (X, Z)},
    'xz v = -Z': {'xy': (X, Y), 'yz': (Y, Z), 'xz': (X, NZ)},
    'yz axes swapped': {'xy': (X, Y), 'yz': (Z, Y), 'xz': (X, Z)},
    'xy v = -Y': {'xy': (X, NY), 'yz': (Y, Z), 'xz': (X, Z)},
}


def check(cond, msg):
    print('  %s %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        FAIL.append(msg)


def build_one(which):
    scad_emit.OCCURRENCES.clear()
    d = Design()
    printed, items = assembly.build(d, which)
    stuck = build.place_all(d, items)
    return d, printed, items, stuck


def main():
    for name, planes in VARIANTS.items():
        scad_emit.PLANES.update(planes)
        print('== sketch planes: %s ==' % name)
        # `small` is left out: its bed layout reads Fusion bounding boxes the stand-in cannot give
        for which in assembly.SINGLE:
            try:
                _, printed, items, _ = build_one(which)
                counts = [p.comp.bodies.count for p in printed]
                warn = [w for p in items for w in getattr(p, 'warnings', [])]
                check(all(n == 1 for n in counts) and not warn,
                      '%-13s %s body%s%s' % (which, counts, '' if counts == [1] else 'ies',
                                             (' — cuts missed: %s' % warn) if warn else ''))
            except Exception as e:                               # noqa: BLE001
                check(False, '%-13s raised %s: %s' % (which, type(e).__name__, e))
    scad_emit.PLANES.update(VARIANTS['conventional'])

    print('== the whole unit ==')
    _, printed, items, stuck = build_one('all')
    check(stuck == [], 'every part kept its position (%s)' % (stuck or 'none stuck'))
    check(sorted(p.comp.name for p in printed) == sorted(n for n, _, _ in assembly.placements()),
          'all four printed parts built: %s' % ', '.join(p.comp.name for p in printed))
    check(all(p.comp.bodies.count == 1 for p in printed), 'each printed part is one body')
    for p in printed:
        check(abs(xf.det(p.xf) - 1) < 1e-9, '%s is placed by a rotation, not a mirror' % p.comp.name)

    print('\n%s' % ('OK — every part builds as one body' if not FAIL else 'FAIL: %d' % len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
