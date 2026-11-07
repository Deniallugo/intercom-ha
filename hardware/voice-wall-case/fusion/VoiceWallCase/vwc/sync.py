"""Drag a part in Fusion, then write the move back into ``placement.py``.

How it works: every electronic part is built at the IDENTITY inside its box's sub-assembly, so
after a drag its occurrence transform IS the move, in box-local mm. Each part declares which
placement number each axis drives (``elec.Comp.moves``); the new value is the value the
document was BUILT with (stamped into the design by ``assembly.remember_placement``) plus the
move. Then ``placement.py`` is rewritten in place — only the number on each `name = value` line
changes, comments and layout stay — and the design checks run on the result.

Not synced, and said so:
  * a part that `follows` another (knobs, plugs, wiring) — move the one it follows;
  * an axis the part does not own (the devkit cannot leave its tray: y is ignored);
  * a rotation — only translations map to numbers.

``plan`` and ``rewrite`` are pure Python, so the logic is tested offline (tests/test_sync.py);
``read`` is the only function that touches Fusion.
"""

import json
import os
import re

from . import elec, xf
from . import params as P

TOL = 0.05      # mm: smaller moves are noise from the drag, not intent
BOXES = ('amp electronics', 'voice electronics')


def read(design):
    """{part name: (translation mm, rotated?)} for every electronic part not at the identity,
    plus the placement the document was built with (or None)."""
    from .build import unmatrix
    comps = elec.by_name()
    names = set(comps)
    moved = {}
    root = design.rootComponent
    for i in range(root.occurrences.count):
        box = root.occurrences.item(i)
        if box.component.name not in BOXES:
            continue
        occs = box.component.occurrences
        for j in range(occs.count):
            occ = occs.item(j)
            if occ.component.name not in names:
                continue
            # The part was drawn in WORLD coordinates at the identity, so its transform (read
            # through the root proxy, relative to its never-moved group) IS the drag, in world
            # axes. Conjugating by the box's quarter turn turns it into box-local x / y / z.
            world = unmatrix(occ.createForAssemblyContext(box).transform2)
            drag = xf.mul(xf.inverse(unmatrix(box.transform2)), world)
            B = elec.box_xf(comps[occ.component.name].where)
            R, t = xf.chain(xf.inverse(B), drag, B)
            rotated = not xf.same_rotation((R, t), xf.IDENTITY, 1e-4)
            if rotated or max(abs(v) for v in t) > TOL:
                moved[occ.component.name] = (t, rotated)
    built = None
    try:
        a = design.attributes.itemByName('voice-wall-case', 'placement')
        built = json.loads(a.value) if a else None
    except Exception:
        pass
    return moved, built


def plan(moved, built=None):
    """-> (updates {name: new value}, notes [str]). Pure."""
    comps = elec.by_name()
    base = dict(built or {})
    for n in P.PLACEMENT:
        base.setdefault(n, list(getattr(P, n)) if isinstance(getattr(P, n), tuple) else getattr(P, n))
    updates, notes = {}, []
    for name in sorted(moved):
        t, rotated = moved[name]
        comp = comps.get(name)
        if comp is None:
            notes.append('%s: not an electronic part this version knows — ignored' % name)
            continue
        if rotated:
            notes.append('%s: rotated — rotations are not synced, only the translation' % name)
        if comp.follows:
            notes.append('%s follows %s — move that instead; this move is ignored'
                         % (name, comp.follows))
            continue
        for k, axis in enumerate('xyz'):
            d = t[k]
            if abs(d) <= TOL:
                continue
            if axis not in comp.moves:
                notes.append('%s: %+.1f mm along %s ignored — it cannot move that way'
                             % (name, d, axis))
                continue
            pname, idx = comp.moves[axis]
            cur = updates.get(pname, base[pname])
            if idx is None:
                new = round(cur + d, 1)
            else:
                new = list(cur)
                new[idx] = round(new[idx] + d, 1)
            updates[pname] = new
            notes.append('%s: %s %+.1f mm -> %s = %s' % (name, axis, d, pname, _lit(new)))
    return updates, notes


def _lit(v):
    if isinstance(v, (list, tuple)):
        return '(%s)' % ', '.join(_num(c) for c in v)
    return _num(v)


def _num(v):
    v = round(float(v), 1)
    return str(int(v)) if v == int(v) else repr(v)


def rewrite(text, updates):
    """Replace the value on each `name = value` line of placement.py, nothing else. Pure."""
    for name, value in updates.items():
        pat = re.compile(r'^(%s\s*=\s*)(.*?)(\s*#.*)?$' % re.escape(name), re.M)
        if not pat.search(text):
            raise KeyError('%s has no line in placement.py' % name)
        text = pat.sub(lambda m: m.group(1) + _lit(value) + (m.group(3) or ''), text, count=1)
    return text


def placement_path():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'placement.py')


def write(updates):
    path = placement_path()
    with open(path) as fh:
        text = fh.read()
    new = rewrite(text, updates)
    with open(path, 'w') as fh:
        fh.write(new)
    return path
