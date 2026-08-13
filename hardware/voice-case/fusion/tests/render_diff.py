"""Render the Fusion port offline and diff it against the OpenSCAD original.

    python3 render_diff.py [--png] [part ...]

Fusion has no headless mode, so a change to `vc/*.py` can normally only be checked by
opening Fusion and clicking Run — which means every mistake costs a round trip, and a
mistake that merely MIRRORS something (the button cap came out inside out once) costs
several, because it builds cleanly and looks almost right.

So this runs the port's own geometry code against `scad_emit`, an adsk stand-in that turns
each feature into the equivalent OpenSCAD (extrude -> linear_extrude, revolve ->
rotate_extrude, loft -> hull, combine -> union/difference/intersection), renders that, and
compares volume and bounding box against `../../stl/<part>.stl`.

It also renders each part under DELIBERATELY WRONG sketch-plane conventions. A construction
plane's u/v axes are Fusion's business, not ours — `Part._frame` probes them rather than
assuming — and this is the check that the probe is actually doing its job: the geometry must
come out identical whichever way the planes are laid out. That is the test the inside-out
button cap would have failed.

Volumes differ from the OpenSCAD by a fraction of a percent because this port uses true
arcs where the SCAD used `$fn = 64`, so the tolerance below is 1%, not zero.
"""

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
CASE = os.path.dirname(os.path.dirname(HERE))          # hardware/voice-case
OUT = os.path.join(HERE, 'emitted')
OPENSCAD = os.environ.get('OPENSCAD') or '/opt/homebrew/bin/openscad'
VOLUME_TOL = 1.0          # percent, against the OpenSCAD render
BBOX_TOL = 0.05           # mm

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(CASE, 'fusion/VoiceCase'))

import scad_emit                                                        # noqa: E402
Design = scad_emit.install()

from vc import base_plate, build, button_cap, button_holder             # noqa: E402
from vc import coupons, mic_clamp, parameters, params as P, shell       # noqa: E402

MODULES = {'shell': shell, 'base': base_plate, 'button': button_cap,
           'holder': button_holder, 'clamp': mic_clamp}
PARTS = ('shell', 'base', 'button', 'holder', 'clamp', 'fit', 'fit-front', 'coupon',
         'all')
# `coupon` and `all` are multi-component, and the OpenSCAD lays them out in one object, so
# they are rendered for looking at rather than diffed.
DIFFED = ('shell', 'base', 'button', 'holder', 'clamp', 'fit', 'fit-front')

X, Y, Z = scad_emit.X, scad_emit.Y, scad_emit.Z
NX, NY, NZ = scad_emit.NX, scad_emit.NY, scad_emit.NZ
# The first is what the planes look like they do; the rest are what they might actually do.
PLANE_VARIANTS = {
    'conventional': {'xy': (X, Y), 'yz': (Y, Z), 'xz': (X, Z)},
    'xz v = -Z': {'xy': (X, Y), 'yz': (Y, Z), 'xz': (X, NZ)},
    'yz axes swapped': {'xy': (X, Y), 'yz': (Z, Y), 'xz': (X, NZ)},
    'yz both negated': {'xy': (X, Y), 'yz': (NY, NZ), 'xz': (NX, Z)},
    'xy v = -Y': {'xy': (X, NY), 'yz': (Y, Z), 'xz': (NX, NZ)},
}


def emit(part):
    """the OpenSCAD for one part selector, straight out of the port's own build code"""
    scad_emit.OCCURRENCES.clear()
    d = Design()
    if part == 'coupon':
        coupons.coupon(d)
    elif part == 'fit':
        coupons.fit(d, end=-1)
    elif part == 'fit-front':
        coupons.fit(d, end=+1)
    elif part == 'all':
        t = build.transform
        placed = [(shell, None),
                  (base_plate, t((0, 0, P.top_depth()))),
                  (button_cap, t((P.btn_pos[0], P.btn_pos[1], -P.btn_proud()))),
                  (button_holder, t((P.btn_pos[0], P.btn_pos[1], P.bh_z1()), rot_x_deg=180)),
                  (mic_clamp, t((P.mic_pos[0], P.mic_pos[1], P.wall + P.mic_post_h),
                                rot_x_deg=180))]
        for module, transform in placed:
            module.build(build.Part(d, module.NAME, transform))
    else:
        MODULES[part].build(build.Part(d, part))
    for occ in scad_emit.OCCURRENCES:
        if occ.component.bodies.count != 1:
            raise AssertionError('%s: %s left %d bodies'
                                 % (part, occ.component.name, occ.component.bodies.count))
    return 'union() { %s }' % ' '.join(o.scad() + ';' for o in scad_emit.OCCURRENCES)


def render(part, tag=''):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    stem = os.path.join(OUT, part + tag)
    with open(stem + '.scad', 'w') as fh:
        fh.write('// emitted from the Fusion port by tests/render_diff.py — not source\n')
        fh.write('%s;\n' % emit(part))
    r = subprocess.run([OPENSCAD, '-o', stem + '.stl', stem + '.scad'],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError('%s failed to render:\n%s' % (part, r.stderr[-1500:]))
    return stem + '.stl'


def png(part, camera='0,0,0,60,0,35,260'):
    stem = os.path.join(OUT, part)
    subprocess.run([OPENSCAD, '--camera=' + camera, '--imgsize=1000,780',
                    '--colorscheme=Tomorrow', '-o', stem + '.png', stem + '.scad'],
                   capture_output=True, text=True)
    return stem + '.png'


def read_stl(path):
    with open(path, 'rb') as fh:
        data = fh.read()
    tris = []
    if data[:5] == b'solid' and b'facet' in data[:2000]:
        cur = []
        for line in data.decode('ascii', 'replace').splitlines():
            w = line.split()
            if w[:1] == ['vertex']:
                cur.append(tuple(float(x) for x in w[1:4]))
                if len(cur) == 3:
                    tris.append(tuple(cur))
                    cur = []
    else:
        for i in range(struct.unpack('<I', data[80:84])[0]):
            v = struct.unpack('<12f', data[84 + i*50:84 + i*50 + 48])
            tris.append((v[3:6], v[6:9], v[9:12]))
    return tris


def volume(tris):
    total = 0.0
    for a, b, c in tris:
        total += (a[0]*(b[1]*c[2] - b[2]*c[1])
                  - a[1]*(b[0]*c[2] - b[2]*c[0])
                  + a[2]*(b[0]*c[1] - b[1]*c[0]))/6.0
    return abs(total)


def bbox(tris):
    vs = [v for t in tris for v in t]
    return tuple(f(v[i] for v in vs) for i in range(3) for f in (min, max))


def check_reference_parameters():
    """The ref_* parameters must survive a SECOND run of the script.

    Fusion's `userParameters.add` fails on a duplicate rather than replacing it, so a
    re-run into the same design has to update in place — and re-running after editing
    params.py is the entire workflow.
    """
    design = Design()
    added, updated, failed = parameters.write(design)
    again_added, again_updated, again_failed = parameters.write(design)
    problems = []
    if failed or again_failed:
        problems.append('refused: %s' % ', '.join(failed + again_failed))
    if updated or again_added:
        problems.append('first run should add and second should update, got %d/%d then %d/%d'
                        % (added, updated, again_added, again_updated))
    if design.userParameters.count != added:
        problems.append('%d parameters for %d entries — duplicated'
                        % (design.userParameters.count, added))
    print('  %d reference parameters, re-runnable  %s'
          % (added, 'OK' if not problems else 'BROKEN: ' + '; '.join(problems)))
    return problems


def main(argv):
    want_png = '--png' in argv
    parts = [a for a in argv if not a.startswith('-')] or list(PARTS)
    if not os.path.isfile(OPENSCAD):
        print('SKIP render diff — OpenSCAD not found (set $OPENSCAD)')
        return 0

    failures = []
    print('== reference user parameters ==')
    failures += check_reference_parameters()
    print('== port vs OpenSCAD ==')
    for part in parts:
        try:
            mine = read_stl(render(part))
        except Exception as exc:
            print('  %-8s RENDER FAILED — %s' % (part, exc))
            failures.append(part)
            continue
        line = '  %-8s %8.3f cm3' % (part, volume(mine)/1000.0)
        ref = os.path.join(CASE, 'stl', '%s.stl' % part)
        if part in DIFFED and os.path.exists(ref):
            r = read_stl(ref)
            dv = 100.0*(volume(mine) - volume(r))/volume(r)
            db = max(abs(a - b) for a, b in zip(bbox(mine), bbox(r)))
            ok = abs(dv) < VOLUME_TOL and db < BBOX_TOL
            line += '  %+6.2f%% vs scad  bbox delta %.3f mm  %s' % (
                dv, db, 'OK' if ok else 'DIFFERS')
            if not ok:
                failures.append(part)
        elif part in DIFFED:
            line += '  (no reference — run ../../build.sh)'
        else:
            line += '  (multi-part: rendered, not diffed)'
        print(line)
        if want_png:
            png(part)

    print('== invariance to the sketch planes\' own axes ==')
    baseline = {}
    for label, planes in PLANE_VARIANTS.items():
        scad_emit.PLANES = planes
        marks = []
        for part in ('shell', 'base', 'button', 'holder', 'clamp'):
            if part not in parts:
                continue
            tris = read_stl(render(part, tag='-variant'))
            got = (round(volume(tris), 1), tuple(round(b, 4) for b in bbox(tris)))
            if label == 'conventional':
                baseline[part] = got
                marks.append(part)
            elif got == baseline.get(part):
                marks.append(part)
            else:
                marks.append('%s MOVED' % part)
                failures.append('%s under %s' % (part, label))
        print('  %-18s %s' % (label, ' '.join(marks)))
    scad_emit.PLANES = PLANE_VARIANTS['conventional']

    if failures:
        print('\nFAIL: %s' % ', '.join(sorted(set(failures))))
        return 1
    print('\nOK — the port renders the same solids as the OpenSCAD, and does so whichever '
          'way\n     Fusion happens to orient its sketch planes')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
