"""tb.geo: geometry helpers for Blender 4.2, safe in background mode.

Conventions
  * Mesh data is authored directly in WORLD coordinates and objects are left
    at identity. Pivots are provided by parenting to Empties (see tb.rig),
    not by moving object origins.
  * Every creator takes an optional `coll` (collection) and links the object.
"""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree


# =====================================================================
# scalar helpers and 1D interpolation
# =====================================================================
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0)) if e1 != e0 else float(x >= e1)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0)) if e1 != e0 else float(x >= e1)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


class Pchip:
    """Monotone (shape preserving, no overshoot) C1 cubic through knots.

    f = Pchip([x0, x1, ...], [y0, y1, ...]);  f(x) accepts floats or numpy arrays.
    Outside the knot range the end values are held (clamped).
    """

    def __init__(self, xs, ys):
        x = np.asarray(xs, dtype=float)
        y = np.asarray(ys, dtype=float)
        if len(x) < 2 or np.any(np.diff(x) <= 0):
            raise ValueError('Pchip needs >= 2 strictly increasing x knots')
        h = np.diff(x)
        d = np.diff(y) / h
        m = np.zeros_like(y)
        n = len(x)
        if n == 2:
            m[:] = d[0]
        else:
            for i in range(1, n - 1):
                if d[i - 1] * d[i] > 0.0:
                    w1 = 2.0 * h[i] + h[i - 1]
                    w2 = h[i] + 2.0 * h[i - 1]
                    m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
            m[0] = self._end(h[0], h[1], d[0], d[1])
            m[-1] = self._end(h[-1], h[-2], d[-1], d[-2])
        self.x, self.y, self.m, self.h = x, y, m, h

    @staticmethod
    def _end(h0, h1, d0, d1):
        m = ((2.0 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if m * d0 <= 0.0:
            return 0.0
        if d0 * d1 <= 0.0 and abs(m) > 3.0 * abs(d0):
            return 3.0 * d0
        return m

    def __call__(self, t):
        scalar = np.isscalar(t)
        t = np.clip(np.atleast_1d(np.asarray(t, dtype=float)), self.x[0], self.x[-1])
        i = np.clip(np.searchsorted(self.x, t, side='right') - 1, 0, len(self.x) - 2)
        h = self.h[i]
        s = (t - self.x[i]) / h
        s2, s3 = s * s, s * s * s
        out = ((2 * s3 - 3 * s2 + 1) * self.y[i] + (s3 - 2 * s2 + s) * h * self.m[i]
               + (-2 * s3 + 3 * s2) * self.y[i + 1] + (s3 - s2) * h * self.m[i + 1])
        return float(out[0]) if scalar else out


class CSpline:
    """Natural cubic spline (C2, very smooth, may overshoot) through knots.
    Same call convention as Pchip. Good for long flowing profile curves."""

    def __init__(self, xs, ys):
        x = np.asarray(xs, dtype=float)
        y = np.asarray(ys, dtype=float)
        n = len(x)
        if n < 3:
            raise ValueError('CSpline needs >= 3 knots')
        h = np.diff(x)
        A = np.zeros((n, n))
        r = np.zeros(n)
        A[0, 0] = A[-1, -1] = 1.0
        for i in range(1, n - 1):
            A[i, i - 1] = h[i - 1]
            A[i, i] = 2.0 * (h[i - 1] + h[i])
            A[i, i + 1] = h[i]
            r[i] = 3.0 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
        c = np.linalg.solve(A, r)
        self.x, self.y, self.c, self.h = x, y, c, h
        self.b = (y[1:] - y[:-1]) / h - h * (2.0 * c[:-1] + c[1:]) / 3.0
        self.d = (c[1:] - c[:-1]) / (3.0 * h)

    def __call__(self, t):
        scalar = np.isscalar(t)
        t = np.clip(np.atleast_1d(np.asarray(t, dtype=float)), self.x[0], self.x[-1])
        i = np.clip(np.searchsorted(self.x, t, side='right') - 1, 0, len(self.x) - 2)
        dx = t - self.x[i]
        out = self.y[i] + self.b[i] * dx + self.c[i] * dx * dx + self.d[i] * dx ** 3
        return float(out[0]) if scalar else out


# =====================================================================
# polylines / space curves (numpy arrays of shape [n, 2] or [n, 3])
# =====================================================================
def polyline_length(pts, closed=False):
    p = np.asarray(pts, dtype=float)
    if closed:
        p = np.vstack([p, p[:1]])
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


def resample(pts, n, closed=False):
    """Resample a polyline to n points evenly spaced by arc length."""
    p = np.asarray(pts, dtype=float)
    if closed:
        p = np.vstack([p, p[:1]])
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = s[-1]
    if total <= 0:
        return np.repeat(p[:1], n, axis=0)
    t = np.linspace(0.0, total, n + 1)[:-1] if closed else np.linspace(0.0, total, n)
    out = np.empty((n, p.shape[1]))
    for k in range(p.shape[1]):
        out[:, k] = np.interp(t, s, p[:, k])
    return out


def catmull_rom(points, per_seg=8, closed=False, alpha=0.5):
    """Centripetal Catmull-Rom spline THROUGH the given points."""
    P = [np.asarray(p, dtype=float) for p in points]
    n = len(P)
    if n < 2:
        return np.asarray(P)
    if closed:
        ext = [P[-1]] + P + [P[0], P[1]]
        segs = n
    else:
        ext = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
        segs = n - 1
    out = []
    for i in range(segs):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-9) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-9) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-9) ** alpha
        for j in range(per_seg):
            t = t1 + (t2 - t1) * j / per_seg
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    if not closed:
        out.append(P[-1])
    return np.asarray(out)


def bezier(p0, p1, p2, p3, n=16):
    t = np.linspace(0.0, 1.0, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, dtype=float) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + (t ** 3) * p3


def bspline(ctrl, n=64, closed=False):
    """Uniform cubic B-spline (C2). Open curves are clamped to the end points."""
    C = [np.asarray(p, dtype=float) for p in ctrl]
    if closed:
        C = C + C[:3]
    else:
        C = [C[0], C[0]] + C + [C[-1], C[-1]]
    segs = len(C) - 3
    out = []
    ts = np.linspace(0.0, segs, n, endpoint=not closed)
    for t in ts:
        i = min(int(t), segs - 1)
        u = t - i
        b0 = (1 - u) ** 3 / 6.0
        b1 = (3 * u ** 3 - 6 * u ** 2 + 4) / 6.0
        b2 = (-3 * u ** 3 + 3 * u ** 2 + 3 * u + 1) / 6.0
        b3 = u ** 3 / 6.0
        out.append(b0 * C[i] + b1 * C[i + 1] + b2 * C[i + 2] + b3 * C[i + 3])
    return np.asarray(out)


def superellipse(a, b, n=4.0, count=48):
    """Closed 2D outline |x/a|^n + |y/b|^n = 1 (n=2 ellipse, n>2 squircle)."""
    out = []
    for k in range(count):
        t = 2.0 * math.pi * k / count
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2.0 / n), c), b * math.copysign(abs(s) ** (2.0 / n), s)))
    return np.asarray(out)


def arc(center, radius, a0, a1, count=24, plane='YZ', offset=0.0):
    """Arc points in a world plane. Angles in degrees.
    plane 'YZ' -> points (offset, cy + r cos, cz + r sin); 'XZ' and 'XY' likewise."""
    out = []
    for k in range(count):
        t = math.radians(lerp(a0, a1, k / (count - 1)))
        u, v = center[0] + radius * math.cos(t), center[1] + radius * math.sin(t)
        out.append({'YZ': (offset, u, v), 'XZ': (u, offset, v), 'XY': (u, v, offset)}[plane])
    return np.asarray(out)


# =====================================================================
# collections / linking / parenting
# =====================================================================
def collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def link(obj, coll=None):
    coll = coll or bpy.context.scene.collection
    if obj.name not in coll.objects:
        coll.objects.link(obj)
    return obj


def world_matrix(ob):
    """World matrix from the parent chain without needing a depsgraph update."""
    m = ob.matrix_basis.copy()
    if ob.parent is not None:
        m = world_matrix(ob.parent) @ ob.matrix_parent_inverse @ m
    return m


def parent(child, parent_obj):
    """Parent while keeping the child's current world transform."""
    wm = world_matrix(child)
    child.parent = parent_obj
    child.matrix_parent_inverse = world_matrix(parent_obj).inverted()
    child.matrix_basis = wm
    return child


def empty(name, location=(0, 0, 0), coll=None, size=0.1, display='PLAIN_AXES'):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = display
    ob.empty_display_size = size
    ob.location = location
    return link(ob, coll)


# =====================================================================
# mesh creation
# =====================================================================
def shade(obj, smooth=True, sharp_angle=None):
    """Smooth shade a mesh object; edges sharper than sharp_angle (deg) stay hard."""
    me = obj.data
    if not smooth:
        me.shade_flat()
        return obj
    me.shade_smooth()
    if sharp_angle is not None:
        me.set_sharp_from_angle(angle=math.radians(sharp_angle))
    return obj


def new_object(name, verts, faces, edges=(), coll=None, smooth=True, sharp_angle=40.0):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [tuple(e) for e in edges], [tuple(f) for f in faces])
    me.update(calc_edges=True)
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    if faces:
        shade(ob, smooth, sharp_angle)
    return ob


def grid_surface(name, P, close_u=False, close_v=False, flip=False, coll=None,
                 smooth=True, sharp_angle=None, uv=True):
    """Quad grid mesh from a point array P[nu][nv] (list of rows or numpy [nu, nv, 3]).

    Row index = u, column index = v. `close_u` joins the last row to the first,
    `close_v` joins the last column to the first. `flip` reverses the normals.
    A UV map 'UVMap' with u->V and v->U in [0, 1] is created.
    """
    P = np.asarray(P, dtype=float)
    nu, nv = P.shape[0], P.shape[1]
    verts = P.reshape(-1, 3)
    faces = []
    uvs = []
    for i in range(nu if close_u else nu - 1):
        i2 = (i + 1) % nu
        for j in range(nv if close_v else nv - 1):
            j2 = (j + 1) % nv
            quad = [i * nv + j, i * nv + j2, i2 * nv + j2, i2 * nv + j]
            fu = [(j / max(nv - 1, 1), i / max(nu - 1, 1)), ((j + 1) / max(nv - 1, 1), i / max(nu - 1, 1)),
                  ((j + 1) / max(nv - 1, 1), (i + 1) / max(nu - 1, 1)), (j / max(nv - 1, 1), (i + 1) / max(nu - 1, 1))]
            if flip:
                quad.reverse()
                fu.reverse()
            faces.append(quad)
            uvs.append(fu)
    ob = new_object(name, verts, faces, coll=coll, smooth=smooth, sharp_angle=sharp_angle)
    if uv:
        layer = ob.data.uv_layers.new(name='UVMap')
        k = 0
        for fu in uvs:
            for co in fu:
                layer.data[k].uv = co
                k += 1
    return ob


def loft(name, sections, count=None, closed_sections=False, close_loop=False, flip=False, coll=None, **kw):
    """Loft through a list of section polylines (each [n, 3]). Sections are resampled
    by arc length to `count` points so they may have different point counts."""
    count = count or max(len(s) for s in sections)
    rows = [resample(s, count, closed=closed_sections) for s in sections]
    return grid_surface(name, rows, close_u=close_loop, close_v=closed_sections, flip=flip, coll=coll, **kw)


def revolve(name, profile, segments=64, axis='X', origin=(0.0, 0.0, 0.0), angle=360.0,
            coll=None, smooth=True, sharp_angle=35.0, flip=False):
    """Lathe a 2D profile [(r, a), ...] around a world axis through `origin`.
    r = radius, a = position along the axis. A full turn closes the surface.
    The profile itself may be closed by repeating its first point at the end."""
    prof = np.asarray(profile, dtype=float)
    full = abs(angle - 360.0) < 1e-6
    steps = segments if full else segments + 1
    rows = []
    for k in range(steps):
        t = math.radians(angle) * k / segments
        c, s = math.cos(t), math.sin(t)
        row = []
        for r, a in prof:
            if axis == 'X':
                p = (a, r * c, r * s)
            elif axis == 'Y':
                p = (r * s, a, r * c)
            else:
                p = (r * c, r * s, a)
            row.append((p[0] + origin[0], p[1] + origin[1], p[2] + origin[2]))
        rows.append(row)
    return grid_surface(name, rows, close_u=full, flip=flip, coll=coll, smooth=smooth, sharp_angle=sharp_angle)


def extrude_polygon(name, outline, depth, plane='YZ', offset=0.0, both_sides=False, coll=None,
                    smooth=False, sharp_angle=30.0):
    """Prism from a closed 2D outline (counter-clockwise list of (u, v)).
    plane 'YZ': (u, v) = (y, z), extruded along +X from x = offset (or centred if both_sides).
    plane 'XZ': (u, v) = (x, z), extruded along +Y.  plane 'XY': (u, v) = (x, y), extruded along +Z."""
    o = np.asarray(outline, dtype=float)
    n = len(o)
    a0 = offset - (depth / 2.0 if both_sides else 0.0)
    a1 = a0 + depth

    def P(u, v, a):
        return {'YZ': (a, u, v), 'XZ': (u, a, v), 'XY': (u, v, a)}[plane]

    verts = [P(u, v, a0) for u, v in o] + [P(u, v, a1) for u, v in o]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    ob = new_object(name, verts, faces, coll=coll, smooth=smooth, sharp_angle=sharp_angle)
    recalc_normals(ob)
    return ob


def box(name, size, location=(0, 0, 0), coll=None):
    sx, sy, sz = (s / 2.0 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    v = [(p[0] + location[0], p[1] + location[1], p[2] + location[2]) for p in v]
    f = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return new_object(name, v, f, coll=coll, smooth=False)


def cylinder(name, radius, depth, axis='X', location=(0, 0, 0), segments=48, cap=True, coll=None,
             radius2=None):
    """Cylinder / cone frustum centred on `location`, axis along a world axis."""
    r2 = radius if radius2 is None else radius2
    prof = [(radius, -depth / 2.0), (r2, depth / 2.0)]
    if cap:
        prof = [(0.0, -depth / 2.0)] + prof + [(0.0, depth / 2.0)]
    ob = revolve(name, prof, segments=segments, axis=axis, origin=location, coll=coll, sharp_angle=40.0)
    merge_by_distance(ob, 1e-6)
    return ob


def uv_sphere(name, radius, location=(0, 0, 0), segments=32, rings=16, coll=None, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0] + location[0], v.co.y * scale[1] + location[1], v.co.z * scale[2] + location[2]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    return shade(ob, True)


def torus(name, major, minor, axis='X', location=(0, 0, 0), major_seg=64, minor_seg=16, coll=None):
    prof = [(major + minor * math.cos(2 * math.pi * k / minor_seg), minor * math.sin(2 * math.pi * k / minor_seg))
            for k in range(minor_seg)]
    prof.append(prof[0])
    ob = revolve(name, prof, segments=major_seg, axis=axis, origin=location, coll=coll, sharp_angle=None)
    merge_by_distance(ob, 1e-6)
    return ob


def curve_tube(name, points, radius, resolution=4, cyclic=False, spline='NURBS', cap=True,
               as_mesh=True, coll=None, order=4, radii=None):
    """Round tube along a path (wires, hoses, pipes, trims, seams, roll bars).
    spline: 'POLY' (through points, angular), 'NURBS' (smooth, clamped at the ends).
    radii: optional per-point radius multipliers. Returns a mesh object by default."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = resolution
    cu.use_fill_caps = cap
    cu.resolution_u = 8
    sp = cu.splines.new('NURBS' if spline == 'NURBS' else 'POLY')
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (float(p[0]), float(p[1]), float(p[2]), 1.0)
        if radii is not None:
            sp.points[i].radius = float(radii[i])
    sp.use_cyclic_u = cyclic
    if spline == 'NURBS':
        sp.order_u = min(order, len(points))
        sp.use_endpoint_u = not cyclic
    ob = bpy.data.objects.new(name, cu)
    link(ob, coll)
    if as_mesh:
        ob = convert_to_mesh(ob)
        shade(ob, True, 50.0)
    return ob


def sweep(name, path, profile, closed_profile=True, closed_path=False, up=(0, 0, 1), scales=None,
          coll=None, cap=False, flip=False, smooth=True, sharp_angle=40.0):
    """Sweep a 2D profile [(a, b), ...] along a 3D path.
    At each path point the profile is placed in the plane normal to the path tangent:
    a along `side` (= tangent x up), b along the corrected up vector.
    scales: optional per-path-point (sa, sb) or scalar multipliers."""
    path = np.asarray(path, dtype=float)
    prof = np.asarray(profile, dtype=float)
    n = len(path)
    upv = Vector(up).normalized()
    rows = []
    for i in range(n):
        if closed_path:
            t = Vector(path[(i + 1) % n] - path[i - 1])
        else:
            t = Vector(path[min(i + 1, n - 1)] - path[max(i - 1, 0)])
        t.normalize()
        side = t.cross(upv)
        if side.length < 1e-6:
            side = t.cross(Vector((1, 0, 0)))
        side.normalize()
        u2 = side.cross(t).normalized()
        sc = (1.0, 1.0)
        if scales is not None:
            s = scales[i]
            sc = (s, s) if np.isscalar(s) else s
        c = Vector(path[i])
        rows.append([tuple(c + side * (a * sc[0]) + u2 * (b * sc[1])) for a, b in prof])
    ob = grid_surface(name, rows, close_u=closed_path, close_v=closed_profile, flip=flip, coll=coll,
                      smooth=smooth, sharp_angle=sharp_angle)
    if cap and not closed_path and closed_profile:
        fill_holes(ob)
    return ob


def text_mesh(name, body, size=0.1, extrude=0.002, bevel=0.0, align='CENTER', coll=None, spacing=1.0):
    """Extruded text as a mesh, lying in the XY plane (facing +Z), centred at the origin.
    Transform the returned object (or its mesh via transform_mesh) to place it."""
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.space_character = spacing
    ob = bpy.data.objects.new(name, cu)
    link(ob, coll)
    ob = convert_to_mesh(ob)
    shade(ob, True, 30.0)
    return ob


# =====================================================================
# mesh editing
# =====================================================================
def _bm_edit(obj, fn):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    fn(bm)
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def merge_by_distance(obj, dist=1e-5):
    return _bm_edit(obj, lambda bm: bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist))


def recalc_normals(obj, inside=False):
    def fn(bm):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if inside:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return _bm_edit(obj, fn)


def flip_normals(obj):
    return _bm_edit(obj, lambda bm: bmesh.ops.reverse_faces(bm, faces=bm.faces))


def fill_holes(obj, sides=0):
    return _bm_edit(obj, lambda bm: bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=sides))


def transform_mesh(obj, matrix):
    """Bake a 4x4 matrix into the mesh data (object stays at identity)."""
    obj.data.transform(Matrix(matrix))
    obj.data.update()
    return obj


def place(obj, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
    """Bake a translate / XYZ-euler rotate (degrees) / scale into the mesh data."""
    from mathutils import Euler
    m = Matrix.LocRotScale(Vector(location), Euler([math.radians(a) for a in rotation], 'XYZ'), Vector(scale))
    return transform_mesh(obj, m)


def delete_faces(obj, predicate):
    """Delete faces whose centre (Vector, world = local) satisfies predicate(center, face)."""
    def fn(bm):
        doomed = [f for f in bm.faces if predicate(f.calc_center_median(), f)]
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
    return _bm_edit(obj, fn)


def separate_faces(obj, predicate, name, coll=None):
    """Move faces satisfying predicate(center, face) into a new object (materials kept)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    keep = [f for f in bm.faces if not predicate(f.calc_center_median(), f)]
    bm2 = bm.copy()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in set(keep)], context='FACES')
    bm2.faces.ensure_lookup_table()
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if not predicate(f.calc_center_median(), f)], context='FACES')
    bm.to_mesh(obj.data)
    obj.data.update()
    me = bpy.data.meshes.new(name)
    bm2.to_mesh(me)
    for m in obj.data.materials:
        me.materials.append(m)
    bm.free()
    bm2.free()
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    return ob


def convert_to_mesh(obj):
    """Replace a curve / text object by an equivalent mesh object (same name)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    name = obj.name
    colls = list(obj.users_collection)
    wm = obj.matrix_world.copy()
    old_data = obj.data
    bpy.data.objects.remove(obj)
    if old_data.users == 0:
        (bpy.data.curves if isinstance(old_data, bpy.types.Curve) else bpy.data.meshes).remove(old_data)
    me.name = name
    ob = bpy.data.objects.new(name, me)
    for c in colls:
        c.objects.link(ob)
    ob.matrix_world = wm
    return ob


def apply_modifiers(obj):
    """Apply the whole modifier stack (object must be linked to the scene)."""
    if not obj.modifiers:
        return obj
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    name = old.name
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    me.name = name
    return obj


def duplicate(obj, name, coll=None, linked=False):
    ob = obj.copy()
    if not linked and obj.data is not None:
        ob.data = obj.data.copy()
    ob.name = name
    link(ob, coll or (obj.users_collection[0] if obj.users_collection else None))
    return ob


def mirror_copy(obj, name, coll=None):
    """Real mirrored duplicate across the world YZ plane (x -> -x), normals fixed.
    Modifiers are applied first; the copy is authored in world space at identity."""
    src = duplicate(obj, name + '_tmp', coll)
    apply_modifiers(src)
    wm = world_matrix(obj)
    me = src.data
    me.transform(Matrix.Scale(-1.0, 4, Vector((1, 0, 0))) @ wm)
    me.flip_normals()
    me.update()
    src.parent = None
    src.matrix_parent_inverse = Matrix.Identity(4)
    src.matrix_basis = Matrix.Identity(4)
    src.name = name
    me.name = name
    return src


def join(objs, name=None):
    """Join mesh objects into the first one (modifiers of the others are applied)."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    target = objs[0]
    for o in objs[1:]:
        apply_modifiers(o)
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=target, object=target,
                                       selected_objects=objs, selected_editable_objects=objs):
            bpy.ops.object.join()
    if name:
        target.name = name
        target.data.name = name
    return target


def boolean(obj, cutter, operation='DIFFERENCE', solver='EXACT', apply=True, remove_cutter=True):
    """Boolean modifier; operation in DIFFERENCE / UNION / INTERSECT."""
    mod = obj.modifiers.new('bool', 'BOOLEAN')
    mod.operation = operation
    mod.solver = solver
    mod.object = cutter
    if apply:
        apply_modifiers(obj)
        if remove_cutter:
            data = cutter.data
            bpy.data.objects.remove(cutter)
            if data and data.users == 0:
                bpy.data.meshes.remove(data)
    else:
        cutter.hide_render = True
        cutter.hide_viewport = True
        cutter.display_type = 'WIRE'
    return obj


# =====================================================================
# modifiers (left live unless you call apply_modifiers)
# =====================================================================
def mod_subsurf(obj, levels=2, render_levels=None, boundary_smooth='ALL', quality=3):
    m = obj.modifiers.new('subsurf', 'SUBSURF')
    m.levels = levels
    m.render_levels = levels if render_levels is None else render_levels
    m.boundary_smooth = boundary_smooth      # 'ALL' or 'PRESERVE_CORNERS'
    m.quality = quality
    return m


def mod_solidify(obj, thickness, offset=-1.0, even=True, rim=True):
    m = obj.modifiers.new('solidify', 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    m.use_even_offset = even
    m.use_rim = rim
    return m


def mod_bevel(obj, width=0.002, segments=2, angle=35.0, profile=0.5, harden=True):
    m = obj.modifiers.new('bevel', 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.profile = profile
    m.harden_normals = harden
    return m


def mod_mirror(obj, axis='X', merge=True, merge_threshold=1e-4, clip=True):
    """Mirror across the object's local plane (objects sit at identity so this is
    the world YZ plane for axis 'X')."""
    m = obj.modifiers.new('mirror', 'MIRROR')
    m.use_axis = (axis == 'X', axis == 'Y', axis == 'Z')
    m.use_mirror_merge = merge
    m.merge_threshold = merge_threshold
    m.use_clip = clip
    return m


def mod_weighted_normal(obj, weight=50, keep_sharp=True):
    m = obj.modifiers.new('wnormal', 'WEIGHTED_NORMAL')
    m.weight = weight
    m.keep_sharp = keep_sharp
    return m


def mod_array_circular(obj, count, axis='X', pivot=(0, 0, 0), coll=None):
    """Radial array around a world axis through `pivot` (spokes, bolts, fins)."""
    e = empty(obj.name + '_array_pivot', pivot, coll or (obj.users_collection[0] if obj.users_collection else None), size=0.02)
    ang = 2.0 * math.pi / count
    e.rotation_euler = {'X': (ang, 0, 0), 'Y': (0, ang, 0), 'Z': (0, 0, ang)}[axis]
    bpy.context.view_layer.update()
    m = obj.modifiers.new('radial', 'ARRAY')
    m.count = count
    m.use_relative_offset = False
    m.use_object_offset = True
    m.offset_object = e
    return m, e


def radial_copies(obj, count, axis='X', pivot=(0, 0, 0)):
    """Bake `count` rotated copies of the mesh around a world axis into the same mesh."""
    me = obj.data
    base = me.copy()
    bm = bmesh.new()
    piv = Matrix.Translation(Vector(pivot))
    for k in range(count):
        rot = Matrix.Rotation(2.0 * math.pi * k / count, 4, axis)
        tmp = base.copy()
        tmp.transform(piv @ rot @ piv.inverted())
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    bm.to_mesh(me)
    bm.free()
    bpy.data.meshes.remove(base)
    me.update()
    return obj


# =====================================================================
# queries
# =====================================================================
def bounds(objs):
    """World-space bounding box (min Vector, max Vector) of mesh objects (base meshes)."""
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        if ob.type != 'MESH':
            continue
        wm = world_matrix(ob)
        for corner in ob.bound_box:
            p = wm @ Vector(corner)
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    return lo, hi


class Raycaster:
    """Ray casting against the evaluated (modifiers applied) surface of objects.

    rc = Raycaster([obj1, obj2]);  hit = rc.cast(origin, direction)
    -> (location Vector, normal Vector, distance) or None.
    Use it to snap details (lights, badges, trims, cut lines) onto the body."""

    def __init__(self, objs):
        dg = bpy.context.evaluated_depsgraph_get()
        verts, polys = [], []
        for ob in objs:
            if ob.type != 'MESH':
                continue
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            wm = ob.matrix_world
            base = len(verts)
            verts.extend([wm @ v.co for v in me.vertices])
            polys.extend([[base + i for i in p.vertices] for p in me.polygons])
            ev.to_mesh_clear()
        self.tree = BVHTree.FromPolygons(verts, polys, all_triangles=False)

    def cast(self, origin, direction, distance=100.0):
        loc, nor, _idx, dist = self.tree.ray_cast(Vector(origin), Vector(direction).normalized(), distance)
        return None if loc is None else (loc, nor, dist)

    def nearest(self, point):
        loc, nor, _idx, dist = self.tree.find_nearest(Vector(point))
        return None if loc is None else (loc, nor, dist)
