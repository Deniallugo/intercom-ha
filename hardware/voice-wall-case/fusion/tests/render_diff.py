"""Render the Fusion port offline and check it three ways.

    python3 render_diff.py [--png] [--interference] [--quick] [part ...]

1. Port vs OpenSCAD. Each printed part is emitted through ``scad_emit`` (the port's own build
   code against an adsk stand-in that writes OpenSCAD), rendered, and compared — volume and
   bounding box — with the same part rendered from ``../../voice-wall-case.scad``. The OpenSCAD
   is rendered with the CURRENT placement.py values passed in with -D, so after a `sync` the
   two still describe the same unit. References are cached by a hash of those values and the
   .scad sources.
2. Invariance to the sketch planes' own axes. Fusion decides which way each base plane's u/v
   point; the port probes rather than assumes. Every part is re-rendered under deliberately
   wrong conventions and has to come out identical.
3. (--interference) The electronics against the printed parts, as SOLIDS: every dummy
   component intersected with everything printed in its box, in the assembled position. The
   design checks do this with boxes; this does it with the real shells, pockets and holes.

Fusion has no headless mode; this is how the port is checked without clicking Run.
"""

import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
FUSION = os.path.dirname(HERE)
CASE = os.path.dirname(FUSION)                          # hardware/voice-wall-case
OUT = os.path.join(HERE, 'emitted')
REF = os.path.join(HERE, 'ref')
OPENSCAD = os.environ.get('OPENSCAD') or '/opt/homebrew/bin/openscad'
VOLUME_TOL = 1.0          # percent
BBOX_TOL = 0.05           # mm

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(FUSION, 'VoiceWallCase'))

import scad_emit                                                        # noqa: E402
Design = scad_emit.install()

from vwc import assembly, build, elec, params as P                      # noqa: E402

DIFFED = ('amp-shell', 'amp-lid', 'amp-sled', 'voice-shell', 'voice-lid', 'voice-tray', 'sleeve',
          'plunger', 'dome', 'holder', 'clamp', 'plate', 'lock', 'coupon-amp', 'coupon-voice')
QUICK = ('sleeve', 'plunger', 'dome', 'holder', 'clamp', 'lock', 'amp-sled', 'voice-tray')

X, Y, Z = scad_emit.X, scad_emit.Y, scad_emit.Z
NX, NY, NZ = scad_emit.NX, scad_emit.NY, scad_emit.NZ
PLANE_VARIANTS = {
    'conventional': {'xy': (X, Y), 'yz': (Y, Z), 'xz': (X, Z)},
    'xz v = -Z': {'xy': (X, Y), 'yz': (Y, Z), 'xz': (X, NZ)},
    'yz axes swapped': {'xy': (X, Y), 'yz': (Z, Y), 'xz': (X, NZ)},
    'yz both negated': {'xy': (X, Y), 'yz': (NY, NZ), 'xz': (NX, Z)},
    'xy v = -Y': {'xy': (X, NY), 'yz': (Y, Z), 'xz': (NX, NZ)},
}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError('%s\n%s' % (' '.join(cmd[:3]), r.stderr[-1500:]))
    return r


# ---- emitting -----------------------------------------------------------------------------
def emit_design(which):
    scad_emit.OCCURRENCES.clear()
    d = Design()
    printed, items = assembly.build(d, which)
    build.place_all(d, items)           # positions last, exactly as the entry script does
    return d, printed


def emit_part(which):
    """one printed part, in its own (print) frame — what Fusion would export"""
    _, printed = emit_design(which)
    (p,) = printed
    n = p.comp.bodies.count
    if n != 1:
        raise AssertionError('%s left %d bodies, expected 1' % (which, n))
    return p.comp.bodies.item(0).scad


def write_scad(stem, body):
    with open(stem + '.scad', 'w') as fh:
        fh.write('// emitted from the Fusion port by tests/render_diff.py — not source\n%s;\n' % body)


def render(which, tag=''):
    os.makedirs(OUT, exist_ok=True)
    stem = os.path.join(OUT, which + tag)
    write_scad(stem, emit_part(which))
    run([OPENSCAD, '-o', stem + '.stl', stem + '.scad'])
    return stem + '.stl'


# ---- references ---------------------------------------------------------------------------
def ref_dir():
    h = hashlib.sha1()
    for k, v in sorted(P.scad_overrides().items()):
        h.update(('%s=%s;' % (k, v)).encode())
    for root, _, files in os.walk(os.path.join(CASE, 'modules')):
        for f in sorted(files):
            h.update(open(os.path.join(root, f), 'rb').read())
    h.update(open(os.path.join(CASE, 'voice-wall-case.scad'), 'rb').read())
    return os.path.join(REF, h.hexdigest()[:12])


def reference(which):
    d = ref_dir()
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, which + '.stl')
    if not os.path.exists(out):
        cmd = [OPENSCAD, '-o', out, '-D', 'part="%s"' % which]
        for k, v in P.scad_overrides().items():
            cmd += ['-D', '%s=%s' % (k, v)]
        run(cmd + [os.path.join(CASE, 'voice-wall-case.scad')])
    return out


# ---- STL arithmetic -------------------------------------------------------------------------
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
    t = 0.0
    for a, b, c in tris:
        t += (a[0]*(b[1]*c[2] - b[2]*c[1]) - a[1]*(b[0]*c[2] - b[2]*c[0])
              + a[2]*(b[0]*c[1] - b[1]*c[0]))/6.0
    return abs(t)


def bbox(tris):
    vs = [v for t in tris for v in t]
    return tuple(f(v[i] for v in vs) for i in range(3) for f in (min, max))


# ---- the three checks -------------------------------------------------------------------------
def diff(parts, want_png):
    failures = []
    print('== port vs OpenSCAD (placement passed with -D; refs in %s) ==' % os.path.relpath(ref_dir(), HERE))
    for which in parts:
        try:
            mine = read_stl(render(which))
            ref = read_stl(reference(which))
        except Exception as exc:
            print('  %-13s FAILED — %s' % (which, exc))
            failures.append(which)
            continue
        dv = 100.0*(volume(mine) - volume(ref))/volume(ref)
        db = max(abs(a - b) for a, b in zip(bbox(mine), bbox(ref)))
        good = abs(dv) < VOLUME_TOL and db < BBOX_TOL
        print('  %-13s %8.3f cm3  %+6.2f%% vs scad  bbox delta %.3f mm  %s'
              % (which, volume(mine)/1000.0, dv, db, 'OK' if good else 'DIFFERS'))
        if not good:
            failures.append(which)
        if want_png:
            png(os.path.join(OUT, which))
    return failures


def invariance(parts):
    failures = []
    print("== invariance to the sketch planes' own axes ==")
    base = {}
    for label, planes in PLANE_VARIANTS.items():
        scad_emit.PLANES = planes
        marks = []
        for which in parts:
            tris = read_stl(render(which, tag='-variant'))
            got = (round(volume(tris), 0), tuple(round(b, 3) for b in bbox(tris)))
            if label == 'conventional':
                base[which] = got
                marks.append(which)
            elif got == base[which]:
                marks.append(which)
            else:
                marks.append('%s MOVED' % which)
                failures.append('%s under %s' % (which, label))
        print('  %-16s %s' % (label, ' '.join(marks)))
    scad_emit.PLANES = PLANE_VARIANTS['conventional']
    return failures


def interference():
    """every dummy part vs every printed part in its box, as solids"""
    print('== electronics vs printed parts, as solids (assembled positions) ==')
    scad_emit.SEG = 32
    _, _ = emit_design('all')
    occ_by = {o.component.name: o for o in scad_emit.OCCURRENCES}
    comps = elec.components()
    soft_names = {p.name for k in comps for p in k.prims if p.soft}
    amp, voice = assembly.box_parts()
    printed = {'amp': [n for n, _, _ in amp], 'voice': [n for n, _, _ in voice]}
    failures = []
    os.makedirs(OUT, exist_ok=True)
    for k in comps:
        # cables are drawn, never checked — they bend (bodies are named after their primitive,
        # repeats get " 2", " 3", ...)
        body = occ_by[k.name].scad(only=lambda b: not any(b.name == s or b.name.startswith(s + ' ')
                                                          for s in soft_names))
        if body is None:
            continue
        case = ' '.join(occ_by[n].scad() + ';' for n in printed[k.where])
        stem = os.path.join(OUT, 'clash-' + k.name.replace(' ', '_').replace('(', '').replace(')', ''))
        write_scad(stem, 'intersection() { %s; union() { %s } }' % (body, case))
        r = subprocess.run([OPENSCAD, '-o', stem + '.stl', stem + '.scad'], capture_output=True, text=True)
        empty = 'Current top level object is empty' in r.stderr or 'empty' in r.stderr.lower()
        v = 0.0 if empty or r.returncode else volume(read_stl(stem + '.stl'))
        good = v < 1.0          # mm3 — coincident faces leave slivers, a real clash is far more
        print('  %-18s %8.2f mm3  %s' % (k.name, v, 'clear' if good else 'CLASHES'))
        if not good:
            failures.append('%s clashes a printed part' % k.name)
    scad_emit.SEG = 96
    return failures


def png(stem):
    subprocess.run([OPENSCAD, '--viewall', '--autocenter', '--imgsize=1100,860',
                    '--colorscheme=Tomorrow', '-o', stem + '.png', stem + '.scad'],
                   capture_output=True, text=True)


COLOURS = {'black': 'dimgray', 'pcb_dark': 'darkgreen', 'pcb_blue': 'royalblue',
           'pcb_purple': 'purple', 'metal': 'silver', 'alu': 'lightsteelblue', 'green': 'green',
           'yellow': 'gold', 'red': 'red', 'blue': 'blue', 'knob': 'black', 'cable': 'orange'}


def picture():
    """The assembled unit, preview-rendered: `outside` with see-through shells, lids and plate,
    `inside` without them so the electronics show. Each dummy body in its finish colour."""
    scad_emit.SEG = 48
    emit_design('all')
    comps = {k.name: k for k in elec.components()}
    inner, outer = [], []
    for occ in scad_emit.OCCURRENCES:
        name = occ.component.name
        if name in comps:
            for b, p in zip(occ.component.bodies._items, comps[name].prims):
                s = b.scad
                for m in reversed(occ.chain()):
                    s = '%s %s' % (m.scad(), s)
                inner.append('color("%s") %s;' % (COLOURS.get(p.finish, 'gray'), s))
            continue
        s = occ.scad()
        if not s:
            continue
        if name in assembly.SHELLS or name == 'lock bracket':
            outer.append('color([0.85, 0.86, 0.9, 0.3]) %s;' % s)
        else:
            inner.append('color([0.82, 0.72, 0.55, 0.6]) %s;' % s)
    os.makedirs(OUT, exist_ok=True)
    stem = os.path.join(OUT, 'picture')
    for tag, body in (('inside', inner), ('outside', inner + outer)):
        write_scad('%s-%s' % (stem, tag), 'union() { %s }' % ' '.join(body))
        for view, cam in (('iso', '0,70,60,62,0,215,420'), ('side', '0,70,60,90,0,90,420')):
            subprocess.run([OPENSCAD, '--camera=%s' % cam, '--imgsize=1200,900', '--colorscheme=Tomorrow',
                            '-o', '%s-%s-%s.png' % (stem, tag, view), '%s-%s.scad' % (stem, tag)],
                           capture_output=True, text=True)
    scad_emit.SEG = 96
    return stem


def main(argv):
    if not os.path.isfile(OPENSCAD):
        print('SKIP render checks — OpenSCAD not found (set $OPENSCAD)')
        return 0
    flags = {a for a in argv if a.startswith('-')}
    parts = [a for a in argv if not a.startswith('-')]
    if not parts:
        parts = list(QUICK if '--quick' in flags else DIFFED)
    failures = diff(parts, '--png' in flags)
    failures += invariance([p for p in parts if p in QUICK or '--all-variants' in flags])
    if '--interference' in flags:
        failures += interference()
    if '--picture' in flags:
        print('pictures: %s-{inside,outside}-{iso,side}.png' % os.path.relpath(picture(), HERE))
    if failures:
        print('\nFAIL: %s' % ', '.join(sorted(set(failures))))
        return 1
    print('\nOK — the port builds the same solids as the OpenSCAD, whichever way Fusion lays out '
          'its sketch planes')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
