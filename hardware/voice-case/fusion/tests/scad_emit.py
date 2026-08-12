"""An adsk stand-in that EMITS OpenSCAD, so the Fusion port can be rendered offline.

Fusion has no headless mode, so the only way to see what `vc/*.py` actually builds without
clicking Run is to implement the slice of the API it uses and have each feature write the
equivalent OpenSCAD. It is a real emulation, not a mock:

  * planes carry a model-space origin and u/v axes, and `worldGeometry` reports them — so
    `Part._frame`'s probe gets the same answer Fusion's conventions would give
  * sketch curves are recorded in SKETCH coordinates and transformed back to model space
    by the plane's own frame at extrude time, exactly as Fusion would
  * extrude -> multmatrix + linear_extrude, revolve -> rotate_extrude, loft -> hull(),
    combine -> union / difference / intersection

So if the port's coordinate math or its plane mapping is wrong, the rendered result is
wrong in the same way it would be in Fusion.
"""

import math
import sys
import types

SEG = 256          # arc segments; only affects how closely the render matches true arcs
S = 10.0           # emit millimetres (the API works in cm)

X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
NX, NY, NZ = (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0)

# The (u, v) axes the three base planes hand a sketch. Fusion's real answer is not
# obvious — the XZ plane's v axis points along model -Z, which is what turned the button
# cap inside out — so render.py overrides this to check the port is INVARIANT to it.
PLANES = {'xy': (X, Y), 'yz': (Y, Z), 'xz': (X, Z)}


def _add(a, b, k=1.0):
    return (a[0] + b[0]*k, a[1] + b[1]*k, a[2] + b[2]*k)


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


class P3:
    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z

    @property
    def geometry(self):
        return self

    def isEqualTo(self, o):
        return (abs(self.x - o.x) < 1e-7 and abs(self.y - o.y) < 1e-7
                and abs(self.z - o.z) < 1e-7)

    def asTuple(self):
        return (self.x, self.y, self.z)


class SketchPoint:
    def __init__(self, sk, pt):
        self.sk = sk
        self.geometry = pt

    @property
    def worldGeometry(self):
        m = self.sk.plane.to_model(self.geometry.x, self.geometry.y)
        return P3(*m)


class Curve:
    def __init__(self, sk, end):
        self.endSketchPoint = SketchPoint(sk, end)


class Lines:
    def __init__(self, sk):
        self.sk = sk

    def addByTwoPoints(self, a, b):
        pa = a.geometry if isinstance(a, SketchPoint) else a
        pb = b.geometry if isinstance(b, SketchPoint) else b
        self.sk.ops.append(('line', (pa.x, pa.y), (pb.x, pb.y)))
        return Curve(self.sk, P3(pb.x, pb.y))


class Arcs:
    def __init__(self, sk):
        self.sk = sk

    def addByCenterStartSweep(self, centre, start, sweep):
        c = centre.geometry if isinstance(centre, SketchPoint) else centre
        s = start.geometry if isinstance(start, SketchPoint) else start
        pts = []
        r = math.hypot(s.x - c.x, s.y - c.y)
        a0 = math.atan2(s.y - c.y, s.x - c.x)
        for i in range(SEG + 1):
            a = a0 + sweep*i/SEG
            pts.append((c.x + r*math.cos(a), c.y + r*math.sin(a)))
        self.sk.ops.append(('arc', pts[0], pts[-1], pts))
        return Curve(self.sk, P3(*pts[-1]))


class Circles:
    def __init__(self, sk):
        self.sk = sk

    def addByCenterRadius(self, centre, r):
        self.sk.circle = ((centre.x, centre.y), r)
        return object()


class Curves:
    def __init__(self, sk):
        self.sketchLines = Lines(sk)
        self.sketchArcs = Arcs(sk)
        self.sketchCircles = Circles(sk)


class Points:
    def __init__(self, sk):
        self.sk = sk

    def add(self, pt):
        return SketchPoint(self.sk, pt)


class Constraints:
    def __init__(self):
        self.pairs = set()

    def addCoincident(self, a, b):
        assert a.geometry.isEqualTo(b.geometry), 'coincident on points that differ'
        key = tuple(sorted((id(a), id(b))))
        if key in self.pairs:
            raise RuntimeError('3 : Constraint has already been applied')
        self.pairs.add(key)


class Profiles:
    def __init__(self, sk):
        self.sk = sk

    @property
    def count(self):
        return 1 if (self.sk.circle or self.sk.ops) else 0

    def item(self, i):
        return self.sk


class Plane:
    def __init__(self, name, o, u, v):
        self.name, self.o, self.u, self.v = name, o, u, v
        self.n = _cross(u, v)

    def to_model(self, pu, pv, pn=0.0):
        p = self.o
        p = _add(p, self.u, pu)
        p = _add(p, self.v, pv)
        return _add(p, self.n, pn)

    def offset(self, d):
        return Plane('%s+%.4f' % (self.name, d), _add(self.o, self.n, d), self.u, self.v)


class Sketch:
    def __init__(self, plane, name):
        self.plane, self.name = plane, name
        self.ops = []
        self.circle = None
        self.isComputeDeferred = False
        self.deleted = False
        self.sketchCurves = Curves(self)
        self.sketchPoints = Points(self)
        self.geometricConstraints = Constraints()
        self.profiles = Profiles(self)

    def deleteMe(self):
        self.deleted = True
        return True

    # ---- what the emitter needs ------------------------------------------------
    def loop(self):
        """the closed loop, as sketch-space points"""
        pts = []
        for op in self.ops:
            if op[0] == 'line':
                pts.append(op[1])
            else:
                pts.extend(op[3][:-1])
        return pts

    def scad2d(self):
        if self.circle:
            (cu, cv), r = self.circle
            return 'translate([%.6f, %.6f]) circle(r = %.6f, $fn = %d)' % (
                cu*S, cv*S, r*S, SEG)
        pts = self.loop()
        assert len(pts) >= 3, 'sketch %s has no loop' % self.name
        return 'polygon([%s])' % ', '.join('[%.6f, %.6f]' % (u*S, v*S) for u, v in pts)

    def matrix(self):
        """sketch (u, v, n) -> model, as an OpenSCAD multmatrix"""
        u, v, n, o = self.plane.u, self.plane.v, self.plane.n, self.plane.o
        rows = []
        for i in range(3):
            rows.append('[%.6f, %.6f, %.6f, %.6f]' % (u[i], v[i], n[i], o[i]*S))
        return 'multmatrix([%s, [0, 0, 0, 1]])' % ', '.join(rows)

    def model_loop_xz(self):
        """the loop in MODEL space, as (x, z) — for rotate_extrude"""
        out = []
        for pu, pv in self.loop():
            m = self.plane.to_model(pu, pv)
            out.append((m[0]*S, m[2]*S))
        return out


class Body:
    def __init__(self, comp, name, scad):
        self.parentComponent = comp
        self.name = name
        self.scad = scad

    def deleteMe(self):
        self.parentComponent.bodies.remove(self)
        return True


class Bodies:
    def __init__(self, comp):
        self.comp = comp
        self._items = []

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        return self._items[i]

    def itemByName(self, name):
        for b in self._items:
            if b.name == name:
                return b
        return None

    def add(self, name, scad):
        b = Body(self.comp, name, scad)
        self._items.append(b)
        return b

    def remove(self, b):
        self._items.remove(b)


class _Coll:
    def __init__(self, items=()):
        self._items = list(items)

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        return self._items[i]

    def add(self, x):
        self._items.append(x)
        return True


class FeatureResult:
    def __init__(self, bodies):
        self.bodies = _Coll(bodies)


class ExtrudeInput:
    def __init__(self, profile, op):
        self.profile, self.operation = profile, op
        self.startExtent = 0.0
        self.distance = 0.0

    def setDistanceExtent(self, sym, d):
        self.distance = d


class RevolveInput:
    def __init__(self, profile, axis, op):
        self.profile, self.axis, self.operation = profile, axis, op

    def setAngleExtent(self, sym, a):
        self.angle = a


class LoftInput:
    def __init__(self, op):
        self.operation = op
        self.loftSections = _Coll()
        self.isSolid = True


class CombineInput:
    def __init__(self, target, tools):
        self.target, self.tools = target, tools
        self.operation = None
        self.isKeepToolBodies = True
        self.isNewComponent = True


class Features:
    def __init__(self, comp):
        self.comp = comp
        self.extrudeFeatures = self
        self.revolveFeatures = self
        self.loftFeatures = self
        self.combineFeatures = self

    def createInput(self, *a):
        if len(a) == 3:
            return RevolveInput(*a)
        if len(a) == 1:
            return LoftInput(a[0])
        if isinstance(a[1], _Coll):
            return CombineInput(a[0], a[1])
        return ExtrudeInput(a[0], a[1])

    def add(self, inp):
        if isinstance(inp, ExtrudeInput):
            sk = inp.profile
            lo = min(inp.startExtent, inp.startExtent + inp.distance)
            h = abs(inp.distance)
            assert h > 0, 'zero-height extrude of %s' % sk.name
            scad = ('%s translate([0, 0, %.6f]) linear_extrude(height = %.6f) %s'
                    % (sk.matrix(), lo*S, h*S, sk.scad2d()))
            return FeatureResult([self.comp.bodies.add(self._auto(), scad)])
        if isinstance(inp, RevolveInput):
            pts = inp.profile.model_loop_xz()
            assert min(p[0] for p in pts) >= -1e-9, \
                'revolve profile crosses the axis: min radius %.4f' % min(p[0] for p in pts)
            scad = ('rotate_extrude($fn = %d) polygon([%s])'
                    % (SEG, ', '.join('[%.6f, %.6f]' % p for p in pts)))
            return FeatureResult([self.comp.bodies.add(self._auto(), scad)])
        if isinstance(inp, LoftInput):
            # hull of the two sections, each given a hair of thickness — which is exactly
            # how the OpenSCAD built its chamfer. The hair is CENTRED on the section plane,
            # so which way the plane's normal points cannot change the result by half of it.
            parts = []
            for i in range(inp.loftSections.count):
                sk = inp.loftSections.item(i)
                parts.append('%s translate([0, 0, -0.0005]) linear_extrude(height = 0.001) %s'
                             % (sk.matrix(), sk.scad2d()))
            return FeatureResult([self.comp.bodies.add(
                self._auto(), 'hull() { %s }' % ' '.join(p + ';' for p in parts))])
        # combine
        op = inp.operation
        tools = [inp.tools.item(i) for i in range(inp.tools.count)]
        if not tools:
            raise RuntimeError('combine with no tools')
        keyword = {'join': 'union', 'cut': 'difference', 'intersect': 'intersection'}[op]
        inp.target.scad = '%s() { %s }' % (
            keyword, ' '.join([inp.target.scad + ';'] + [t.scad + ';' for t in tools]))
        if not inp.isKeepToolBodies:
            for t in tools:
                self.comp.bodies.remove(t)
        return FeatureResult([inp.target])

    def _auto(self):
        return 'Body%d' % (self.comp.bodies.count + 1)


class Planes:
    def __init__(self, comp):
        self.comp = comp

    def createInput(self):
        return types.SimpleNamespace(setByOffset=self._set)

    def _set(self, plane, offset):
        self._pending = plane.offset(offset)
        return True

    def add(self, inp):
        return self._pending


class Sketches:
    def __init__(self, comp):
        self.comp = comp
        self.all = []

    def add(self, plane):
        sk = Sketch(plane, 'sketch %d on %s' % (len(self.all) + 1, plane.name))
        self.all.append(sk)
        return sk


class Component:
    def __init__(self, name):
        self.name = name
        self.bodies = Bodies(self)
        self.sketches = Sketches(self)
        self.features = Features(self)
        self.constructionPlanes = Planes(self)
        # Fusion's own conventions for the three base planes. The port does not rely on
        # these being right — it probes them — but they are what it will meet.
        self.xYConstructionPlane = Plane('XY', (0, 0, 0), *PLANES['xy'])
        self.yZConstructionPlane = Plane('YZ', (0, 0, 0), *PLANES['yz'])
        self.xZConstructionPlane = Plane('XZ', (0, 0, 0), *PLANES['xz'])
        self.zConstructionAxis = types.SimpleNamespace(name='Z')
        self.occurrences = Occurrences()

    @property
    def bRepBodies(self):
        return self.bodies


class Occurrence:
    def __init__(self, transform):
        self.component = Component('unnamed')
        self.transform = transform

    def scad(self):
        """the component's body, placed — `translate(t) rotate(r)`, OpenSCAD's own order"""
        body = self.component.bodies.item(0).scad
        t = getattr(self.transform, 'translation', None)
        r = getattr(self.transform, 'rotation', None)
        if r:
            body = 'rotate(a = %.6f, v = [%.6f, %.6f, %.6f]) %s' % (
                math.degrees(r[0]), r[1][0], r[1][1], r[1][2], body)
        if t:
            body = 'translate([%.6f, %.6f, %.6f]) %s' % (t.x*S, t.y*S, t.z*S, body)
        return body


class Occurrences:
    def addNewComponent(self, transform):
        occ = Occurrence(transform)
        OCCURRENCES.append(occ)
        return occ


OCCURRENCES = []


class UserParameter:
    def __init__(self, name, expression, units, comment):
        self.name, self.expression = name, expression
        self.units, self.comment = units, comment


class UserParameters:
    """Enough of the Parameters dialog to exercise vc/parameters.py offline.

    It also enforces what Fusion enforces and the port has to live with: a name must be a
    valid identifier, and `add` fails on a duplicate rather than replacing it.
    """

    def __init__(self):
        self._items = []

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        return self._items[i]

    def itemByName(self, name):
        for p in self._items:
            if p.name == name:
                return p
        return None

    def add(self, name, value, units, comment):
        if not name.replace('_', 'a').isalnum() or name[0].isdigit():
            raise RuntimeError('3 : invalid parameter name "%s"' % name)
        if self.itemByName(name):
            raise RuntimeError('3 : parameter "%s" already exists' % name)
        p = UserParameter(name, value, units, comment)
        self._items.append(p)
        return p


class Design:
    def __init__(self):
        self.rootComponent = Component('root')
        self.userParameters = UserParameters()


def install():
    core = types.ModuleType('adsk.core')
    fusion = types.ModuleType('adsk.fusion')
    adsk = types.ModuleType('adsk')

    core.Point3D = types.SimpleNamespace(create=lambda x, y, z=0.0: P3(x, y, z))
    core.Vector3D = types.SimpleNamespace(create=lambda x, y, z=0.0: P3(x, y, z))

    def _matrix():
        m = types.SimpleNamespace(translation=None, rotation=None)

        def _rot(angle, axis, origin):
            m.rotation = (angle, (axis.x, axis.y, axis.z))
            return True

        m.setToRotation = _rot
        return m

    core.Matrix3D = types.SimpleNamespace(create=_matrix)
    core.ValueInput = types.SimpleNamespace(createByReal=lambda v: v,
                                            createByString=lambda s: s)
    core.ObjectCollection = types.SimpleNamespace(create=lambda: _Coll())

    fusion.FeatureOperations = types.SimpleNamespace(
        NewBodyFeatureOperation='new', JoinFeatureOperation='join',
        CutFeatureOperation='cut', IntersectFeatureOperation='intersect')

    class _Offset:
        @staticmethod
        def create(v):
            return v
    fusion.DistanceExtentDefinition = _Offset
    fusion.OffsetStartDefinition = _Offset
    fusion.ExtentDirections = types.SimpleNamespace(PositiveExtentDirection=1)

    adsk.core, adsk.fusion = core, fusion
    sys.modules['adsk'] = adsk
    sys.modules['adsk.core'] = core
    sys.modules['adsk.fusion'] = fusion
    return Design
