"""Builds every entry of ``elec.py`` as its own Fusion component.

One component per part — "ZK-502MT", "MP1584", "ESP32-S3 devkit", "AUX plug (DAC)", ... —
each built at the identity inside its box's sub-assembly, from the same box-local numbers the
case features use. So in Fusion each one is a separate item in the browser that can be hidden,
isolated, measured, checked with Inspect > Interference, or DRAGGED; `sync` then reads the drag
back into ``placement.py``.

Bodies are left separate (one per primitive, each named and coloured) rather than combined: they
are dummies to look at, never printed and never exported.
"""

from . import appearance, elec
from .build import Part, aabox, prism_circle


def _prim(part, p):
    if p.kind == 'box':
        return aabox(part, p.lo, p.hi, name=p.name)
    return prism_circle(part, p.axis, p.c, p.d, p.a0, p.a1, name=p.name)


def build(design, groups):
    """`groups` maps 'amp' / 'voice' to the group each part goes in.

    Every part is drawn directly in WORLD coordinates — its box's quarter turn applied to the
    numbers, not to an occurrence — and neither the parts nor their groups are ever moved.
    Fusion would not hold a transform on the amp group (grounded or not, it read back as set and
    displayed at the origin), so nothing here depends on one. `sync` undoes the quarter turn."""
    parts = []
    for comp in elec.components():
        part = Part(design, comp.name, parent=groups[comp.where])
        x = elec.box_xf(comp.where)
        for p in comp.prims:
            appearance.paint(design, _prim(part, elec.to_world(p, x)), p.finish)
        part.elec = comp
        parts.append(part)
    return parts
