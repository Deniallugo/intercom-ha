"""The CSG vocabulary this port is written in, on standard Fusion sketches and features.

Taken from hardware/voice-case/fusion (vc/build.py), where it was proven in Fusion, and
extended for this design: prisms, cones and lofts along ANY of the three axes (the wall
unit's boxes are cut through their front face, their side walls and their top), nested
sub-assemblies, and components that are positioned only after they are built.

The rules that make it survive a parameter change are unchanged:

  * NOTHING selects a face or an edge. Every profile is drawn from computed coordinates and
    every boolean names its bodies, so a moved parameter can only move geometry.
  * EVERY SKETCH HAS EXACTLY ONE CLOSED LOOP, so `profiles.item(0)` is unambiguous.
  * NO PLANE'S ORIENTATION IS ASSUMED. Each base plane's u/v axes are PROBED
    (`Part._frame`) — three points into a scratch sketch, read back — and every authored
    coordinate is mapped through the answer.

One addition to those: EVERY COMPONENT IS BUILT AT THE IDENTITY and only then moved into
place (`Part.place`). The probe reads `worldGeometry`, and whether that includes the
occurrence's own transform is exactly the kind of thing not to depend on — at the identity
the question does not arise.

Units: the API is centimetres, this design is millimetres; `mm()` converts, here and nowhere
else. Nothing above this file calls the adsk API directly, apart from the entry script.
"""

import math

import adsk.core
import adsk.fusion

from . import xf

TOL = 1e-9

# Per sketch plane: the two MODEL axes a caller authors in, then the axis the extrude runs
# along. Nothing here says which way the plane's own u/v point — that is probed.
_PLANE_AXES = {
    'xy': ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),   # (x, y), depth along z
    'yz': ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),   # (y, z), depth along x
    'xz': ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),   # (x, z), depth along y
}


def mm(v):
    """mm -> the API's cm."""
    return v * 0.1


def _val(v_mm):
    return adsk.core.ValueInput.createByReal(mm(v_mm))


def _pt(u, v, w=0.0):
    return adsk.core.Point3D.create(mm(u), mm(v), mm(w))


def _dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


class _Mapper:
    """Authored in-plane pair -> the sketch's own (u, v), whatever those turn out to be.

    Also carries `sweep`: if the plane's u/v are a MIRROR of the authored pair (negative
    determinant) then counter-clockwise in authored coordinates is clockwise in the
    sketch, and every arc has to sweep the other way or the rounded corners bulge inward.
    """

    def __init__(self, u, v, a1, a2):
        self.m = ((_dot(a1, u), _dot(a2, u)),
                  (_dot(a1, v), _dot(a2, v)))
        det = self.m[0][0]*self.m[1][1] - self.m[0][1]*self.m[1][0]
        self.sweep = 1.0 if det > 0 else -1.0

    def __call__(self, a, b):
        (m00, m01), (m10, m11) = self.m
        return (m00*a + m01*b, m10*a + m11*b)


class Part:
    """One component, built like an OpenSCAD module: keeper bodies, then tools.

    A keeper is created first and NAMED; `union`/`cut`/`intersect` take that name and
    consume tool bodies into it, re-resolving the target by name after every feature
    rather than holding a proxy across it. That is what keeps long boolean chains stable,
    and it lets a part build a sub-assembly (the plate's board seats) before joining it.
    """

    def __init__(self, design, name, parent=None):
        """`parent` is a Group (sub-assembly) or None for the root component. The occurrence
        starts at the IDENTITY; `place()` moves it once the part is built."""
        host = parent.comp if parent is not None else design.rootComponent
        occ = host.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        self.occ = occ
        self.comp = occ.component
        self.xf = None          # where it goes — applied by place_all(), after every feature
        self.parent = parent
        self.zsign = 1
        self.warnings = []      # cuts whose tool body missed the part entirely
        self._frames = {}

    def place(self, x):
        """Where this component goes, as an xf (R, t) in mm. Only RECORDED here: positions are
        applied together by place_all() after the last feature, because a parametric design
        may revert an uncaptured position change when the next feature recomputes it."""
        self.xf = x
        return self

    def move_bodies(self, x):
        """A Move feature on every body in the component — how a part authored in its use
        frame (the sled, the tray) is turned into its print frame, so the component exports
        print-ready. One timeline feature, no face selection."""
        coll = adsk.core.ObjectCollection.create()
        for i in range(self.comp.bRepBodies.count):
            coll.add(self.comp.bRepBodies.item(i))
        moves = self.comp.features.moveFeatures
        try:
            inp = moves.createInput2(coll)
            inp.defineAsFreeMove(matrix(x))
        except AttributeError:                  # Fusion builds before createInput2
            inp = moves.createInput(coll, matrix(x))
        moves.add(inp)
        return self

    # ---- frame -----------------------------------------------------------------
    def mirrored(self):
        """`mirror([0, 0, 1])`: authored z is negated for the duration of the block."""
        return _Mirrored(self)

    def zv(self, z):
        """one authored z, in the component's frame"""
        return self.zsign * z

    def zrange(self, z0, z1):
        """an authored z range, as (lo, hi) in the component's frame"""
        a, b = self.zsign * z0, self.zsign * z1
        return (a, b) if a <= b else (b, a)

    # ---- plane frames, read from Fusion rather than assumed ---------------------
    def _frame(self, kind):
        """(u, v, n) of a base construction plane, as MODEL unit vectors.

        Probed once per component and cached: a scratch sketch, three points, read back
        through `worldGeometry`, then thrown away. Cheap, and it turns "which way does the
        XZ plane's v axis point" from an assumption into a measurement.
        """
        if kind in self._frames:
            return self._frames[kind]
        plane = {'xy': self.comp.xYConstructionPlane,
                 'yz': self.comp.yZConstructionPlane,
                 'xz': self.comp.xZConstructionPlane}[kind]
        sk = self.comp.sketches.add(plane)
        probe = []
        for c in ((0, 0, 0), (1, 0, 0), (0, 1, 0)):
            w = sk.sketchPoints.add(adsk.core.Point3D.create(*c)).worldGeometry
            probe.append((w.x, w.y, w.z))
        sk.deleteMe()
        o, pu, pv = probe
        u = (pu[0] - o[0], pu[1] - o[1], pu[2] - o[2])
        v = (pv[0] - o[0], pv[1] - o[1], pv[2] - o[2])
        self._frames[kind] = (u, v, _cross(u, v))
        return self._frames[kind]

    def mapper(self, kind):
        u, v, _ = self._frame(kind)
        a1, a2, _ = _PLANE_AXES[kind]
        return _Mapper(u, v, a1, a2)

    def span(self, kind, a0, a1):
        """(start, length) for an extrude between two positions on the plane's own axis.

        Both are measured along the plane's NORMAL, which may point against the authored
        axis — in which case the start flips sign and the length goes negative, and Fusion
        extrudes backwards along the normal to land in the same place.
        """
        s = self._depth_sign(kind)
        return (a0*s, (a1 - a0)*s)

    def _depth_sign(self, kind):
        _, _, n = self._frame(kind)
        return 1.0 if _dot(_PLANE_AXES[kind][2], n) > 0 else -1.0

    # ---- sketches --------------------------------------------------------------
    def sketch(self, kind):
        plane = {'xy': self.comp.xYConstructionPlane,
                 'yz': self.comp.yZConstructionPlane,
                 'xz': self.comp.xZConstructionPlane}[kind]
        return self._sketch(plane)

    def offset_sketch(self, kind, at):
        """a sketch on a plane parallel to `kind`, at authored position `at` on its axis.

        A parallel offset keeps the base plane's u/v axes and its in-plane origin, so the
        same mapper applies — only the offset itself has to follow the normal's sign.
        """
        base = {'xy': self.comp.xYConstructionPlane,
                'yz': self.comp.yZConstructionPlane,
                'xz': self.comp.xZConstructionPlane}[kind]
        pin = self.comp.constructionPlanes.createInput()
        pin.setByOffset(base, _val(at*self._depth_sign(kind)))
        return self._sketch(self.comp.constructionPlanes.add(pin))

    def _sketch(self, plane):
        sk = self.comp.sketches.add(plane)
        sk.isComputeDeferred = True
        return sk

    def _finish(self, sk):
        sk.isComputeDeferred = False
        return sk

    # ---- features --------------------------------------------------------------
    def _extrude(self, sk, start, length):
        """extrude sketch profile 0 from `start` for `length` along the sketch normal"""
        self._finish(sk)
        if sk.profiles.count != 1:
            raise RuntimeError(
                'sketch "%s" made %d profiles, expected 1 closed loop — a chained '
                'profile did not close' % (sk.name, sk.profiles.count))
        exts = self.comp.features.extrudeFeatures
        inp = exts.createInput(sk.profiles.item(0),
                               adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.setDistanceExtent(False, _val(length))
        if abs(start) > TOL:
            inp.startExtent = adsk.fusion.OffsetStartDefinition.create(_val(start))
        return exts.add(inp).bodies.item(0)

    def revolve(self, sk, name=None):
        """revolve sketch profile 0 a full turn about the component's Z axis"""
        self._finish(sk)
        revs = self.comp.features.revolveFeatures
        inp = revs.createInput(sk.profiles.item(0), self.comp.zConstructionAxis,
                               adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.setAngleExtent(False, adsk.core.ValueInput.createByReal(2*math.pi))
        return _named(revs.add(inp).bodies.item(0), name)

    def loft(self, sketches):
        """loft through one profile per sketch — the chamfer and the cones"""
        lofts = self.comp.features.loftFeatures
        inp = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        for sk in sketches:
            self._finish(sk)
            inp.loftSections.add(sk.profiles.item(0))
        inp.isSolid = True
        return lofts.add(inp).bodies.item(0)

    # ---- booleans --------------------------------------------------------------
    # Targets are named, not held: a body proxy taken before a combine may not survive
    # it, and a plain `bRepBodies.item(0)` breaks the moment a part builds a sub-assembly
    # of its own (the plate's two board seats are cut and unioned before they join the
    # plate). Every keeper body gets a name and is re-resolved by it after each feature.

    def body(self, name):
        b = self.comp.bRepBodies.itemByName(name)
        if b is None:
            raise RuntimeError('body "%s" is gone — a combine consumed the wrong one'
                               % name)
        return b

    def _combine(self, target, tools, op):
        tools = [t for t in tools if t is not None]
        if not tools:
            return self.body(target)
        tgt = self.body(target)
        coll = adsk.core.ObjectCollection.create()
        for t in tools:
            coll.add(t)
        combines = self.comp.features.combineFeatures
        inp = combines.createInput(tgt, coll)
        inp.operation = op
        inp.isKeepToolBodies = False
        inp.isNewComponent = False
        feature = combines.add(inp)
        kept = self.comp.bRepBodies.itemByName(target)
        if kept is None:                      # Fusion renamed it — take what came out
            kept = feature.bodies.item(0)
            kept.name = target
        return kept

    def union(self, target, tools):
        return self._combine(target, tools,
                             adsk.fusion.FeatureOperations.JoinFeatureOperation)

    def intersect(self, target, tools):
        return self._combine(target, tools,
                             adsk.fusion.FeatureOperations.IntersectFeatureOperation)

    def cut(self, target, tools):
        """Cut, tolerating a tool that happens to miss.

        OpenSCAD does not care whether a `difference()` tool touches anything; Fusion
        refuses the whole feature if one body in the set does not intersect. So the fast
        path is one combine for the lot, and the fallback cuts them one at a time and
        deletes any that turn out to be misses — a miss is a real finding (a cut that
        was meant to land somewhere), so it is reported rather than swallowed.
        """
        tools = [t for t in tools if t is not None]
        if not tools:
            return self.body(target)
        cut_op = adsk.fusion.FeatureOperations.CutFeatureOperation
        try:
            return self._combine(target, tools, cut_op)
        except Exception:
            missed = []
            for t in tools:
                try:
                    self._combine(target, [t], cut_op)
                except Exception:
                    missed.append(t.name)
                    t.deleteMe()
            if missed:
                self.warnings.extend(missed)
            return self.body(target)


class _Mirrored:
    def __init__(self, part):
        self.part = part

    def __enter__(self):
        self.part.zsign *= -1
        return self.part

    def __exit__(self, *exc):
        self.part.zsign *= -1
        return False


# ===== 2D profiles ==========================================================
# All authored in the plane's MODEL axes and mapped through `mp` on the way in. Chained
# geometry: each curve starts on the previous curve's end POINT object, so the loop is
# topologically closed rather than merely closed to within a tolerance.

def chain_loop(sk, mp, start, segments):
    """`segments` is a list of ('line', (a, b)) and ('arc', (ca, cb), sweep_deg).

    A line's final segment closes onto the first point OBJECT, so it is already joined. An
    arc cannot be given its end point, so a loop ending on one needs a coincident
    constraint to close — added ONCE, at the end, and only if Fusion has not already merged
    the two points itself. Adding it twice, or adding it to points Fusion merged, is a
    "Constraint has already been applied" error rather than a no-op.
    """
    first = sk.sketchPoints.add(_pt(*mp(*start)))
    cur = first
    lines = sk.sketchCurves.sketchLines
    arcs = sk.sketchCurves.sketchArcs
    for i, seg in enumerate(segments):
        last = (i == len(segments) - 1)
        if seg[0] == 'line':
            end = first if last else _pt(*mp(*seg[1]))
            cur = lines.addByTwoPoints(cur, end).endSketchPoint
        else:
            arc = arcs.addByCenterStartSweep(_pt(*mp(*seg[1])), cur,
                                             math.radians(seg[2])*mp.sweep)
            cur = _far_end(arc, cur)
    if cur is not first and cur.geometry.isEqualTo(first.geometry):
        try:
            sk.geometricConstraints.addCoincident(cur, first)
        except RuntimeError:
            pass            # already coincident — the loop is closed either way
    return sk


def _far_end(arc, start):
    """The end of `arc` that is NOT where it started.

    Fusion stores every sketch arc counter-clockwise. An arc drawn with a NEGATIVE sweep — which
    is every arc on a mirrored sketch plane (top, floor and side walls here) — comes back with
    its ends swapped: `endSketchPoint` is the point it was started FROM. Chaining the next curve
    off that leaves the arc dangling and the loop open (0 profiles). So pick by position.
    """
    g = start.geometry
    a, b = arc.startSketchPoint, arc.endSketchPoint
    return b if a.geometry.distanceTo(g) <= b.geometry.distanceTo(g) else a


def rrect_loop(sk, mp, w, d, r, center=(0, 0)):
    """2D rounded rectangle centred on `center` — OpenSCAD's rounded_rect().

    Degenerate straights are dropped rather than drawn zero-length, which is what lets
    the same helper draw the vent SLOTS (r == w/2, so the ends are plain semicircles).
    """
    cx, cy = center
    r = max(0.0, min(r, min(w, d)/2))
    hx, hy = w/2 - r, d/2 - r          # corner arc centres
    if r <= TOL:
        return chain_loop(sk, mp, (cx + w/2, cy - d/2),
                          [('line', (cx + w/2, cy + d/2)),
                           ('line', (cx - w/2, cy + d/2)),
                           ('line', (cx - w/2, cy - d/2)),
                           ('line', None)])
    # (segment, the point it ends on), counter-clockwise from the right edge's bottom
    loop = []
    if hy > TOL:
        loop.append((('line', (cx + hx + r, cy + hy)), (cx + hx + r, cy + hy)))
    loop.append((('arc', (cx + hx, cy + hy), 90), (cx + hx, cy + hy + r)))
    if hx > TOL:
        loop.append((('line', (cx - hx, cy + hy + r)), (cx - hx, cy + hy + r)))
    loop.append((('arc', (cx - hx, cy + hy), 90), (cx - hx - r, cy + hy)))
    if hy > TOL:
        loop.append((('line', (cx - hx - r, cy - hy)), (cx - hx - r, cy - hy)))
    loop.append((('arc', (cx - hx, cy - hy), 90), (cx - hx, cy - hy - r)))
    if hx > TOL:
        loop.append((('line', (cx + hx, cy - hy - r)), (cx + hx, cy - hy - r)))
    loop.append((('arc', (cx + hx, cy - hy), 90), (cx + hx + r, cy - hy)))
    lines = [i for i, (seg, _) in enumerate(loop) if seg[0] == 'line']
    if not lines:                       # all four corners meet: it is a circle
        return circle_loop(sk, mp, center, 2*r)
    # Rotate the loop so it ENDS ON A LINE. A closing line lands on the first point OBJECT,
    # so the loop is closed by topology. A closing arc lands wherever Fusion computes its end,
    # and on a mirrored sketch plane (the top/floor and side walls) that is a hair off the
    # start: no coincident gets added, the loop stays open and the sketch has 0 profiles.
    k = lines[-1]
    order = loop[k + 1:] + loop[:k + 1]
    segs = [seg for seg, _ in order[:-1]] + [('line', None)]
    return chain_loop(sk, mp, loop[k][1], segs)


def poly_loop(sk, mp, pts):
    """closed polygon through `pts`"""
    return chain_loop(sk, mp, pts[0],
                      [('line', p) for p in pts[1:]] + [('line', None)])


def rect_loop(sk, mp, center, size, angle=0):
    """rectangle centred on `center`, optionally rotated in the plane"""
    cu, cv = center
    hu, hv = size[0]/2, size[1]/2
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    pts = [(cu + du*ca - dv*sa, cv + du*sa + dv*ca)
           for du, dv in ((+hu, -hv), (+hu, +hv), (-hu, +hv), (-hu, -hv))]
    return poly_loop(sk, mp, pts)


def circle_loop(sk, mp, center, d):
    sk.sketchCurves.sketchCircles.addByCenterRadius(_pt(*mp(*center)), mm(d/2))
    return sk


# ===== solids ===============================================================
# One function per OpenSCAD primitive, all taking authored mm and an authored z range.

def box(part, center, size, name=None):
    """`translate(center) cube(size, center = true)`"""
    sk = part.sketch('xy')
    rect_loop(sk, part.mapper('xy'), (center[0], center[1]), (size[0], size[1]))
    lo, hi = part.zrange(center[2] - size[2]/2, center[2] + size[2]/2)
    return _named(part._extrude(sk, *part.span('xy', lo, hi)), name)


def box_z(part, z0, h, center, size, angle=0, name=None):
    """a box given as an authored z RANGE instead of a centre — and optionally rotated"""
    sk = part.sketch('xy')
    rect_loop(sk, part.mapper('xy'), center, size, angle)
    lo, hi = part.zrange(z0, z0 + h)
    return _named(part._extrude(sk, *part.span('xy', lo, hi)), name)


def cyl(part, z0, h, d, center=(0, 0), name=None):
    """`translate([x, y, z0]) cylinder(h, d)` — axis along z"""
    sk = part.sketch('xy')
    circle_loop(sk, part.mapper('xy'), center, d)
    lo, hi = part.zrange(z0, z0 + h)
    return _named(part._extrude(sk, *part.span('xy', lo, hi)), name)


def cyl_x(part, x0, h, d, center=(0, 0), name=None):
    """axis along +x — the jack's plug hole. `center` is (y, z)."""
    sk = part.sketch('yz')
    circle_loop(sk, part.mapper('yz'), (center[0], part.zv(center[1])), d)
    return _named(part._extrude(sk, *part.span('yz', x0, x0 + h)), name)


def cone_x(part, x0, h, d1, d2, center=(0, 0), name=None):
    """`cylinder(h, d1 = , d2 = )` along +x, as a loft between two circles.

    A loft rather than a tapered extrude: the taper's SIGN depends on which way Fusion
    thinks the profile faces, and a lead-in chamfer that tapers the wrong way still
    cuts a cone — it just cuts the wrong one, silently. Two explicit circles cannot.
    """
    mp = part.mapper('yz')
    sketches = []
    for x, d in ((x0, d1), (x0 + h, d2)):
        sk = part.offset_sketch('yz', x)
        circle_loop(sk, mp, (center[0], part.zv(center[1])), d)
        sketches.append(sk)
    return _named(part.loft(sketches), name)


def cone_z(part, z0, h, d1, d2, center=(0, 0), name=None):
    """the same along z — the holder's bore mouth"""
    mp = part.mapper('xy')
    sketches = []
    for z, d in ((z0, d1), (z0 + h, d2)):
        sk = part.offset_sketch('xy', part.zv(z))
        circle_loop(sk, mp, center, d)
        sketches.append(sk)
    return _named(part.loft(sketches), name)


def rrect_prism(part, z0, h, w, d, r, center=(0, 0), name=None):
    """`linear_extrude(h) rounded_rect(w, d, r)`"""
    sk = part.sketch('xy')
    rrect_loop(sk, part.mapper('xy'), w, d, r, center)
    lo, hi = part.zrange(z0, z0 + h)
    return _named(part._extrude(sk, *part.span('xy', lo, hi)), name)


def rrect_loft(part, z0, z1, lo_size, hi_size, name=None):
    """the hull of two rounded rects at two heights — the 45 deg top chamfer.

    Each size is (w, d, r). With both profiles' corner arcs sharing a centre (which
    `chamfer` and `radius - chamfer` guarantee), the ruled surface between them IS the
    chamfer, which is what hull() produced.
    """
    mp = part.mapper('xy')
    sketches = []
    for z, (w, d, r) in ((z0, lo_size), (z1, hi_size)):
        sk = part.offset_sketch('xy', part.zv(z))
        rrect_loop(sk, mp, w, d, r)
        sketches.append(sk)
    return _named(part.loft(sketches), name)


def prism_yz(part, pts, x_center, x_len, name=None):
    """a (y, z) polygon extruded along x — the devkit tab's 45 deg wedge"""
    sk = part.sketch('yz')
    poly_loop(sk, part.mapper('yz'), [(y, part.zv(z)) for (y, z) in pts])
    return _named(part._extrude(sk, *part.span('yz', x_center - x_len/2,
                                               x_center + x_len/2)), name)


def revolve_profile(part, start, segments, name=None):
    """a closed section in authored (radius, z), revolved about the component's Z axis.

    Authored in the component's own frame — the one part that uses it, the button cap, is
    never drawn mirrored, so `zv()` deliberately does not apply here.
    """
    sk = part.sketch('xz')
    chain_loop(sk, part.mapper('xz'), start, segments)
    return part.revolve(sk, name)


def _named(body, name):
    """Name a body, uniquely — names are how keepers are re-resolved after a combine, so
    a duplicate would make `body(name)` ambiguous. Repeats get " 2", " 3", ... ."""
    if not name:
        return body
    comp = body.parentComponent
    unique, n = name, 2
    while True:
        clash = comp.bRepBodies.itemByName(unique)
        if clash is None or clash == body:
            break
        unique, n = '%s %d' % (name, n), n + 1
    body.name = unique
    return body


# ===== any-axis solids =====================================================
# `axis` is the direction of extrusion; in-plane coordinates are the other two MODEL axes in
# x, y, z order: axis 'z' -> (x, y), axis 'x' -> (y, z), axis 'y' -> (x, z). `a0..a1` is the
# span along the axis, in either order.
_KIND = {'z': 'xy', 'x': 'yz', 'y': 'xz'}


def _ext(part, axis, draw, a0, a1, name):
    kind = _KIND[axis]
    sk = part.sketch(kind)
    draw(sk, part.mapper(kind))
    lo, hi = min(a0, a1), max(a0, a1)
    return _named(part._extrude(sk, *part.span(kind, lo, hi)), name)


def prism_rect(part, axis, c, size, a0, a1, angle=0, name=None):
    return _ext(part, axis, lambda sk, mp: rect_loop(sk, mp, c, size, angle), a0, a1, name)


def prism_circle(part, axis, c, d, a0, a1, name=None):
    return _ext(part, axis, lambda sk, mp: circle_loop(sk, mp, c, d), a0, a1, name)


def prism_rrect(part, axis, c, w, h, r, a0, a1, name=None):
    """rounded rectangle; with r = min(w, h)/2 it is a stadium (a vent slot)"""
    return _ext(part, axis, lambda sk, mp: rrect_loop(sk, mp, w, h, r, c), a0, a1, name)


def prism_poly(part, axis, pts, a0, a1, name=None):
    return _ext(part, axis, lambda sk, mp: poly_loop(sk, mp, pts), a0, a1, name)


def aabox(part, lo, hi, name=None):
    """axis-aligned box between two corners"""
    return prism_rect(part, 'z', ((lo[0] + hi[0])/2, (lo[1] + hi[1])/2),
                      (hi[0] - lo[0], hi[1] - lo[1]), lo[2], hi[2], name=name)


def cone(part, axis, c, d1, d2, a0, a1, name=None):
    """`cylinder(h, d1, d2)` along `axis`, d1 at a0 and d2 at a1, as a loft of two circles"""
    kind = _KIND[axis]
    mp = part.mapper(kind)
    sketches = []
    for a, d in ((a0, d1), (a1, d2)):
        sk = part.offset_sketch(kind, a)
        circle_loop(sk, mp, c, d)
        sketches.append(sk)
    return _named(part.loft(sketches), name)


def loft_rect_circle(part, axis, rect_c, rect_size, a_rect, circ_c, d, a_circ, name=None):
    """hull of a thin rectangle and a disc at two stations — the lid bosses' 45 deg taper"""
    kind = _KIND[axis]
    mp = part.mapper(kind)
    s1 = part.offset_sketch(kind, a_rect)
    rect_loop(s1, mp, rect_c, rect_size)
    s2 = part.offset_sketch(kind, a_circ)
    circle_loop(s2, mp, circ_c, d)
    return _named(part.loft([s1, s2]), name)


def rrect_loft_ax(part, axis, a0, a1, lo_size, hi_size, c=(0, 0), name=None):
    """hull of two rounded rects (w, h, r) at two stations — the 45 deg front chamfer"""
    kind = _KIND[axis]
    mp = part.mapper(kind)
    sketches = []
    for a, (w, h, r) in ((a0, lo_size), (a1, hi_size)):
        sk = part.offset_sketch(kind, a)
        rrect_loop(sk, mp, w, h, r, c)
        sketches.append(sk)
    return _named(part.loft(sketches), name)


# ===== assemblies ============================================================

class Group:
    """An empty component holding other components — a sub-assembly. Built at the identity
    like everything else, and placed afterwards."""

    def __init__(self, design, name, parent=None):
        host = parent.comp if parent is not None else design.rootComponent
        self.occ = host.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        self.occ.component.name = name
        self.comp = self.occ.component
        self.xf = None
        self.parent = parent

    def place(self, x):
        self.xf = x            # see Part.place
        return self


def matrix(x):
    """xf (R, t) in mm -> a Fusion Matrix3D in cm. Set from the coordinate system — origin and
    the images of the three axes, the COLUMNS of R — so no row/column-major convention is
    involved."""
    R, t = x
    m = adsk.core.Matrix3D.create()
    m.setWithCoordinateSystem(
        adsk.core.Point3D.create(mm(t[0]), mm(t[1]), mm(t[2])),
        adsk.core.Vector3D.create(R[0][0], R[1][0], R[2][0]),
        adsk.core.Vector3D.create(R[0][1], R[1][1], R[2][1]),
        adsk.core.Vector3D.create(R[0][2], R[1][2], R[2][2]))
    return m


def unmatrix(m):
    """the inverse of `matrix`: a Fusion Matrix3D (cm) -> xf (R, t) in mm"""
    o, xa, ya, za = m.getAsCoordinateSystem()
    R = ((xa.x, ya.x, za.x), (xa.y, ya.y, za.y), (xa.z, ya.z, za.z))
    return (R, (o.x*10.0, o.y*10.0, o.z*10.0))


def place(occ, x):
    # Fusion GROUNDS the first component created in a design, and a grounded occurrence ignores
    # a new transform without an error — which is what kept "amp electronics" (created first)
    # pinned at the origin on the first real runs, through every retry.
    try:
        if occ.isGrounded:
            occ.isGrounded = False
    except AttributeError:
        pass
    m = matrix(x)
    try:
        occ.transform2 = m
    except AttributeError:
        occ.transform = m


def _snapshot(design):
    try:
        snaps = design.snapshots
        if snaps.hasPendingSnapshot:
            snaps.add()
    except Exception:
        pass        # a direct-modelling design has no snapshots and needs none


def _is_at(occ, x, tol=1e-3):
    try:
        m = occ.transform2
    except AttributeError:
        m = occ.transform
    got = unmatrix(m)
    return xf.same_rotation(got, x, 1e-6) and all(abs(a - b) < tol for a, b in zip(got[1], x[1]))


def place_all(design, items, passes=4):
    """Apply every recorded position, capture it, then READ EVERY ONE BACK and re-apply what
    did not stick. -> [names still wrong] (empty when all is well).

    The read-back is what found the first real-run bug: the first component created is grounded
    and silently ignores its transform (place() now ungrounds it). Anything that still is not
    where it was put gets another pass, and is reported if it never gets there.

    Every item placed here is TOP-LEVEL (a nested occurrence only accepts a position through
    its root proxy, and Fusion placed those wrongly). The electronics and their groups are not
    placed at all: they are drawn in world coordinates and stay at the identity.
    """
    todo = [it for it in items if it.xf is not None]
    for it in todo:
        if getattr(it, 'parent', None) is not None:
            raise RuntimeError('%s: only top-level components are placed' % it.comp.name)
    for _ in range(passes):
        for it in todo:
            place(it.occ, it.xf)
            _snapshot(design)
        todo = [it for it in todo if not _is_at(it.occ, it.xf)]
        if not todo:
            break
    return [it.comp.name for it in todo]
