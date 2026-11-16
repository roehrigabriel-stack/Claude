"""Helpers shared by chassis.py and engine.py (not a buildable module).

MeshBuilder accumulates many primitives (boxes, cylinders, tubes, sweeps, helices)
in world coordinates and is emitted as ONE mesh object with ONE material.
"""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Vector

from tb import geo, mats


# ---------------------------------------------------------------- vector helpers
def V(p):
    return np.asarray(p, dtype=float)


def unit(v):
    v = V(v)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else np.array([0.0, 0.0, 1.0])


def frame_from_axis(axis, up=(0, 0, 1)):
    """Orthonormal frame (u, v, w) with w along axis."""
    w = unit(axis)
    up = V(up)
    if abs(np.dot(w, unit(up))) > 0.97:
        up = np.array([1.0, 0.0, 0.0]) if abs(w[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = unit(np.cross(up, w))
    v = np.cross(w, u)
    return u, v, w


def rot_x(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def circle(n, r=1.0):
    return np.array([(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)])


def rect_profile(w, h, ch=0.0):
    """Closed rectangle (counter-clockwise), optional corner chamfer."""
    a, b = w / 2.0, h / 2.0
    if ch <= 0:
        return np.array([(a, -b), (a, b), (-a, b), (-a, -b)])
    c = min(ch, a * 0.95, b * 0.95)
    return np.array([(a, -b + c), (a, b - c), (a - c, b), (-a + c, b), (-a, b - c), (-a, -b + c),
                     (-a + c, -b), (a - c, -b)])


def ibeam_profile(w, h, tf, tw):
    a, b = w / 2, h / 2
    t, s = tf, tw / 2
    return np.array([(a, -b), (a, -b + t), (s, -b + t), (s, b - t), (a, b - t), (a, b), (-a, b), (-a, b - t),
                     (-s, b - t), (-s, -b + t), (-a, -b + t), (-a, -b)])


def catmull(points, per=6, closed=False):
    return geo.catmull_rom([V(p) for p in points], per_seg=per, closed=closed)


def smooth_path(points, n=40):
    return geo.bspline([V(p) for p in points], n=n)


def helix_path(p0, p1, radius, turns, per_turn=14, wire_r=0.0, end_flat=0.6):
    """Coil spring centre line from p0 to p1 (end turns closed up)."""
    p0, p1 = V(p0), V(p1)
    u, v, w = frame_from_axis(p1 - p0)
    L = np.linalg.norm(p1 - p0)
    n = int(turns * per_turn)
    pts = []
    for k in range(n + 1):
        t = k / n
        s = t - 0.15 * math.sin(2 * math.pi * t) / (2 * math.pi)   # closed (tighter) end turns
        a = 2 * math.pi * turns * t
        pts.append(p0 + w * (L * s) + u * (radius * math.cos(a)) + v * (radius * math.sin(a)))
    return np.asarray(pts)


# ---------------------------------------------------------------- mesh builder
class MeshBuilder:
    def __init__(self):
        self.v = []      # list of np arrays [k,3]
        self.f = []      # list of face lists (global index)
        self.n = 0

    # raw
    def add(self, verts, faces):
        verts = np.asarray(verts, dtype=float).reshape(-1, 3)
        base = self.n
        self.v.append(verts)
        self.f.extend([[base + i for i in f] for f in faces])
        self.n += len(verts)
        return base

    # --- primitives
    def box(self, c, size, R=None, ch=0.0, seg=1):
        """Box centred on c. R: 3x3 local->world. ch: chamfer/bevel size."""
        sx, sy, sz = (s / 2.0 for s in size)
        if ch <= 0:
            vv = np.array([(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
                           (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)])
            ff = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        else:
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            for v in bm.verts:
                v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
            ch = min(ch, min(size) * 0.48)
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=ch, segments=seg, affect='EDGES', profile=0.5)
            vv = np.array([tuple(v.co) for v in bm.verts])
            idx = {v: i for i, v in enumerate(bm.verts)}
            ff = [[idx[v] for v in f.verts] for f in bm.faces]
            bm.free()
        if R is not None:
            vv = vv @ np.asarray(R).T
        self.add(vv + V(c), ff)

    def box_between(self, p0, p1, w, h, up=(0, 0, 1), ch=0.0):
        """Beam of rectangular section w (side) x h (up) between two points."""
        p0, p1 = V(p0), V(p1)
        u, v, wv = frame_from_axis(p1 - p0, up)
        # local x = u (side), y = v (up'), z = along
        R = np.stack([u, v, wv], axis=1)
        L = np.linalg.norm(p1 - p0)
        self.box((p0 + p1) / 2.0, (w, h, L), R=R, ch=ch)

    def cyl(self, p0, p1, r0, r1=None, seg=16, caps=True, up=(0, 0, 1), cap_inset=0.0):
        p0, p1 = V(p0), V(p1)
        r1 = r0 if r1 is None else r1
        u, v, w = frame_from_axis(p1 - p0, up)
        ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)
        ca, sa = np.cos(ang)[:, None], np.sin(ang)[:, None]
        ring0 = p0 + (u * ca + v * sa) * r0
        ring1 = p1 + (u * ca + v * sa) * r1
        verts = np.vstack([ring0, ring1])
        faces = [(i, (i + 1) % seg, seg + (i + 1) % seg, seg + i) for i in range(seg)]
        if caps:
            faces.append(tuple(range(seg - 1, -1, -1)))
            faces.append(tuple(range(seg, 2 * seg)))
        self.add(verts, faces)

    def disc_stack(self, p0, p1, profile, seg=24, up=(0, 0, 1)):
        """Lathe about the axis p0->p1: profile [(t, r), ...] t in 0..1 along axis, r radius. Closed ends."""
        p0, p1 = V(p0), V(p1)
        u, v, w = frame_from_axis(p1 - p0, up)
        ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)
        ca, sa = np.cos(ang)[:, None], np.sin(ang)[:, None]
        rows = []
        for t, r in profile:
            rows.append(p0 + (p1 - p0) * t + (u * ca + v * sa) * r)
        m = len(profile)
        verts = np.vstack(rows)
        faces = []
        for j in range(m - 1):
            for i in range(seg):
                i2 = (i + 1) % seg
                faces.append((j * seg + i, j * seg + i2, (j + 1) * seg + i2, (j + 1) * seg + i))
        faces.append(tuple(range(seg - 1, -1, -1)))
        faces.append(tuple(range((m - 1) * seg, m * seg)))
        self.add(verts, faces)

    def sweep(self, path, prof, scale=None, closed=True, caps=True, up=None, twist=0.0, loop=False):
        """Sweep 2D profile along path. scale: scalar, [n] or [n,2]. up: fixed up reference or None (parallel transport)."""
        path = np.asarray(path, dtype=float)
        n = len(path)
        prof = np.asarray(prof, dtype=float)
        m = len(prof)
        T = np.zeros_like(path)
        T[1:-1] = path[2:] - path[:-2]
        T[0] = path[1] - path[0]
        T[-1] = path[-1] - path[-2]
        if loop:
            T[0] = path[1] - path[-1]
            T[-1] = path[0] - path[-2]
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
        if scale is None:
            sc = np.ones((n, 2))
        else:
            sc = np.asarray(scale, dtype=float)
            if sc.ndim == 0:
                sc = np.full((n, 2), float(sc))
            elif sc.ndim == 1:
                sc = np.stack([sc, sc], axis=1)
        verts = np.empty((n, m, 3))
        if up is None:
            ref = np.array([0.0, 0.0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0.0, 0.0])
            nrm = unit(np.cross(T[0], np.cross(ref, T[0])))
        for i in range(n):
            t = T[i]
            if up is None:
                nrm = nrm - np.dot(nrm, t) * t
                nrm = nrm / max(np.linalg.norm(nrm), 1e-12)
                b = np.cross(t, nrm)
                side, upv = b, nrm
            else:
                side = np.cross(t, V(up))
                if np.linalg.norm(side) < 1e-6:
                    side = np.cross(t, np.array([1.0, 0, 0]))
                side = unit(side)
                upv = np.cross(side, t)
            if twist:
                a = math.radians(twist * i / max(n - 1, 1))
                ca, sa = math.cos(a), math.sin(a)
                side, upv = side * ca + upv * sa, -side * sa + upv * ca
            verts[i] = path[i] + np.outer(prof[:, 0] * sc[i, 0], side) + np.outer(prof[:, 1] * sc[i, 1], upv)
        faces = []
        mm = m if closed else m - 1
        for i in range(n if loop else n - 1):
            i2 = (i + 1) % n
            for j in range(mm):
                j2 = (j + 1) % m
                faces.append((i * m + j, i * m + j2, i2 * m + j2, i2 * m + j))
        if caps and closed and not loop:
            faces.append(tuple(range(m - 1, -1, -1)))
            faces.append(tuple(range((n - 1) * m, n * m)))
        self.add(verts.reshape(-1, 3), faces)

    def tube(self, path, r, seg=8, radii=None, caps=True):
        """Round tube along a path. r scalar, radii optional per-point multipliers."""
        self.sweep(path, circle(seg), scale=(r if radii is None else r * np.asarray(radii)), caps=caps)

    def lathe(self, p0, p1, profile, seg=24, up=(0, 0, 1), loop=True):
        """Hollow revolve about p0->p1 of a profile [(t, r)...] (t along the axis, 0..1). loop closes the profile."""
        p0, p1 = V(p0), V(p1)
        u, v, w = frame_from_axis(p1 - p0, up)
        ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)
        ca, sa = np.cos(ang)[:, None], np.sin(ang)[:, None]
        rows = [p0 + (p1 - p0) * t + (u * ca + v * sa) * r for t, r in profile]
        self.rings(rows, caps=False, closed=True, loop_n=loop)

    def rings(self, rings, caps=True, closed=True, loop_n=False):
        """Loft through rings (list of [m,3] arrays with same m)."""
        R = [np.asarray(r, dtype=float) for r in rings]
        n, m = len(R), len(R[0])
        faces = []
        for i in range(n if loop_n else n - 1):
            i2 = (i + 1) % n
            for j in range(m if closed else m - 1):
                j2 = (j + 1) % m
                faces.append((i * m + j, i * m + j2, i2 * m + j2, i2 * m + j))
        if caps and closed and not loop_n:
            faces.append(tuple(range(m - 1, -1, -1)))
            faces.append(tuple(range((n - 1) * m, n * m)))
        self.add(np.vstack(R), faces)

    def torus(self, c, axis, major, minor, seg_major=24, seg_minor=8):
        u, v, w = frame_from_axis(axis)
        c = V(c)
        rows = []
        for i in range(seg_major):
            a = 2 * math.pi * i / seg_major
            d = u * math.cos(a) + v * math.sin(a)
            for j in range(seg_minor):
                b = 2 * math.pi * j / seg_minor
                rows.append(c + d * (major + minor * math.cos(b)) + w * (minor * math.sin(b)))
        faces = []
        for i in range(seg_major):
            i2 = (i + 1) % seg_major
            for j in range(seg_minor):
                j2 = (j + 1) % seg_minor
                faces.append((i * seg_minor + j, i * seg_minor + j2, i2 * seg_minor + j2, i2 * seg_minor + j))
        self.add(np.array(rows), faces)

    def sphere(self, c, r, seg=12, rings=8, scale=(1, 1, 1)):
        rows = [(0, 0, 1)]
        for i in range(1, rings):
            th = math.pi * i / rings
            for k in range(seg):
                ph = 2 * math.pi * k / seg
                rows.append((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        rows.append((0, 0, -1))
        P = np.array(rows) * np.array(scale) * r + V(c)
        faces = []
        for k in range(seg):
            faces.append((0, 1 + k, 1 + (k + 1) % seg))
        for i in range(rings - 2):
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((1 + i * seg + k, 1 + (i + 1) * seg + k, 1 + (i + 1) * seg + k2, 1 + i * seg + k2))
        last = len(rows) - 1
        for k in range(seg):
            faces.append((last, 1 + (rings - 2) * seg + (k + 1) % seg, 1 + (rings - 2) * seg + k))
        self.add(P, faces)

    def bolts(self, centres, axis, r=0.005, h=0.004, seg=6, hex_head=True):
        """Bolt heads (short hex cylinders) at the given centres, pointing along `axis`."""
        a = unit(axis)
        for c in centres:
            c = V(c)
            self.cyl(c, c + a * h, r, r * 0.95, seg=seg, caps=True)

    def ring_bolts(self, c, axis, ring_r, n, r=0.005, h=0.004, phase=0.0):
        u, v, w = frame_from_axis(axis)
        cs = [V(c) + (u * math.cos(2 * math.pi * k / n + phase) + v * math.sin(2 * math.pi * k / n + phase)) * ring_r
              for k in range(n)]
        self.bolts(cs, w, r, h)

    def extrude_poly(self, outline_yz, x0, x1, ch=0.0):
        """Prism from a closed (y,z) outline between x0 and x1 (profile in YZ plane)."""
        o = np.asarray(outline_yz, dtype=float)
        n = len(o)
        v0 = np.column_stack([np.full(n, x0), o[:, 0], o[:, 1]])
        v1 = np.column_stack([np.full(n, x1), o[:, 0], o[:, 1]])
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        self.add(np.vstack([v0, v1]), faces)

    def extrude_poly_z(self, outline_xy, z0, z1):
        o = np.asarray(outline_xy, dtype=float)
        n = len(o)
        v0 = np.column_stack([o[:, 0], o[:, 1], np.full(n, z0)])
        v1 = np.column_stack([o[:, 0], o[:, 1], np.full(n, z1)])
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        self.add(np.vstack([v0, v1]), faces)

    def extrude_poly_y(self, outline_xz, y0, y1):
        o = np.asarray(outline_xz, dtype=float)
        n = len(o)
        v0 = np.column_stack([o[:, 0], np.full(n, y0), o[:, 1]])
        v1 = np.column_stack([o[:, 0], np.full(n, y1), o[:, 1]])
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        self.add(np.vstack([v0, v1]), faces)

    def empty(self):
        return self.n == 0

    def arrays(self, mirror=False):
        if not self.v:
            return np.zeros((0, 3)), []
        V_ = np.vstack(self.v)
        F_ = list(self.f)
        if mirror == 'only':
            Vm = V_.copy()
            Vm[:, 0] *= -1.0
            return Vm, [list(reversed(f)) for f in F_]
        if mirror:
            Vm = V_.copy()
            Vm[:, 0] *= -1.0
            base = len(V_)
            F_ = F_ + [[base + i for i in reversed(f)] for f in self.f]
            V_ = np.vstack([V_, Vm])
        return V_, F_


# ---------------------------------------------------------------- emit
def emit(mb, name, mat, coll, parent=None, mirror=False, sharp=38.0, bevel=None, smooth=True, mats_extra=None):
    """Create a mesh object from a MeshBuilder with material `mat` (name or Material).
    bevel: None or (width, segments) live bevel modifier. Returns the object (or None if empty)."""
    if mb.empty():
        return None
    verts, faces = mb.arrays(mirror)
    ob = geo.new_object(name, verts, faces, coll=coll, smooth=smooth, sharp_angle=sharp)
    # consistent outward normals (islands are closed volumes)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    if smooth:
        geo.shade(ob, True, sharp)
    mats.assign(ob, mat)
    if bevel:
        m = geo.mod_bevel(ob, bevel[0], bevel[1], angle=50.0, harden=False)
    if parent is not None:
        geo.parent(ob, parent)
    return ob


class Parts:
    """Dictionary of named MeshBuilders -> emit all with their material."""

    def __init__(self, coll, root, prefix):
        self.coll, self.root, self.prefix = coll, root, prefix
        self.b = {}
        self.meta = {}
        self.objs = []

    def get(self, key, mat, mirror=False, bevel=None, sharp=38.0, parent=None):
        if key not in self.b:
            self.b[key] = MeshBuilder()
            self.meta[key] = dict(mat=mat, mirror=mirror, bevel=bevel, sharp=sharp, parent=parent)
        return self.b[key]

    def flush(self):
        for key, mb in self.b.items():
            m = self.meta[key]
            ob = emit(mb, self.prefix + key, m['mat'], self.coll, parent=m['parent'] or self.root,
                      mirror=m['mirror'], bevel=m['bevel'], sharp=m['sharp'])
            if ob is not None:
                self.objs.append(ob)
        self.b.clear()
        self.meta.clear()
        return self.objs


def bbox_of(objs):
    lo, hi = geo.bounds(objs)
    return lo, hi
