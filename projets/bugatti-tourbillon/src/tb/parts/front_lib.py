"""Helpers for the front module: ruled panels between an opening's outline edges, oriented boxes, snapping."""
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector
from tb import geo


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class Opening:
    """A closed 3D outline (an opening in the body). Surface points are interpolated between the lower and the
    upper outline edge at each x, so panels follow the opening boundary exactly (flush)."""

    def __init__(self, pts, const_out=None):
        self.P = np.asarray(pts, float)
        self.xmin = float(self.P[:, 0].min())
        self.xmax = float(self.P[:, 0].max())
        self.const_out = None if const_out is None else _unit(const_out)

    def col(self, x):
        P = self.P
        hits = []
        n = len(P)
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            if (a[0] - x) * (b[0] - x) <= 0 and abs(b[0] - a[0]) > 1e-12:
                t = (x - a[0]) / (b[0] - a[0])
                hits.append(a + (b - a) * t)
        if len(hits) < 2:
            return None
        hits.sort(key=lambda h: h[2])
        return hits[0], hits[-1]

    def _cl(self, x):
        e = 1e-4 * (self.xmax - self.xmin)
        return min(max(x, self.xmin + e), self.xmax - e)

    def out_at(self, x):
        if self.const_out is not None:
            return self.const_out
        h = 0.01 * (self.xmax - self.xmin)
        a = self.col(self._cl(x - h))
        b = self.col(self._cl(x + h))
        ma, mb = (a[0] + a[1]) / 2, (b[0] + b[1]) / 2
        t = mb - ma
        o = np.array([t[1], -t[0], 0.0])
        o = _unit(o)
        if o[1] > 0:
            o = -o
        return o

    def pos(self, u, v, off=0.0):
        """u along x (0..1), v from the lower to the upper edge (0..1). Returns point, tu, tv, out."""
        x = self._cl(self.xmin + u * (self.xmax - self.xmin))
        b, t = self.col(x)
        out = self.out_at(x)
        p = b + (t - b) * v + out * off
        h = 0.02 * (self.xmax - self.xmin)
        x2 = self._cl(x + h)
        x1 = self._cl(x - h)
        c2, c1 = self.col(x2), self.col(x1)
        q2 = c2[0] + (c2[1] - c2[0]) * v
        q1 = c1[0] + (c1[1] - c1[0]) * v
        tu = _unit(q2 - q1)
        tv = _unit(np.cross(out, tu))
        out = _unit(np.cross(tu, tv))
        return p, tu, tv, out

    def grid(self, nu, nv, inset=0.0, dome=0.0, v0=0.0, v1=1.0):
        us = 0.5 + 0.5 * np.sin(np.linspace(-math.pi / 2, math.pi / 2, nu)) * 0.9999
        vs = np.linspace(v0, v1, nv)
        G = []
        for u in us:
            row = []
            for v in vs:
                d = dome * max(0.0, 1 - (2 * u - 1) ** 2) * max(0.0, 1 - (2 * ((v - v0) / (v1 - v0)) - 1) ** 2)
                p, tu, tv, out = self.pos(u, v, d - inset)
                row.append(tuple(p))
            G.append(row)
        return G

    def panel(self, name, nu, nv, inset=0.0, dome=0.0, coll=None, v0=0.0, v1=1.0):
        G = self.grid(nu, nv, inset, dome, v0, v1)
        ob = geo.grid_surface(name, G, coll=coll, smooth=True)
        geo.merge_by_distance(ob, 1e-5)
        out = self.out_at(0.5 * (self.xmin + self.xmax))
        me = ob.data
        if me.polygons:
            tot = sum((np.array(p.normal) @ out) for p in me.polygons)
            if tot < 0:
                geo.flip_normals(ob)
        return ob

    def outline_pts(self, off=0.0):
        return [tuple(p + self.out_at(p[0]) * off) for p in self.P]


def oriented_box(name, c, tu, tv, n, size, coll=None):
    c = np.asarray(c, float)
    hu, hv, hn = size[0] / 2, size[1] / 2, size[2] / 2
    V = []
    for sz in (-1, 1):
        for sv in (-1, 1):
            for su in (-1, 1):
                V.append(tuple(c + tu * hu * su + tv * hv * sv + n * hn * sz))
    F = [(3, 2, 0, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]
    ob = geo.new_object(name, V, F, coll=coll, smooth=False)
    geo.recalc_normals(ob)
    return ob


def ellipse(cx, cy, rx, ry, n=32):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def basis_matrix(normal, pos, up='Y'):
    q = Vector(normal).to_track_quat('Z', up)
    M = q.to_matrix().to_4x4()
    M.translation = Vector(pos)
    return M


def snap(rc, p, d, lift=0.0, back=0.4):
    """Cast from p - d*back along d onto the surface; return the hit raised by `lift` against d. Falls back to p."""
    d = Vector(d).normalized()
    h = rc.cast(Vector(p) - d * back, d, distance=back * 3)
    if h is None:
        return np.array(p, float), None
    return np.array(h[0] - d * lift), h[1]


def strip_grid(rc, path2d_fn, d, n_u, n_v, width, lift, up=None):
    """Grid strip: centre line path2d_fn(t) -> 3D point (t in 0..1), widened in the direction perpendicular to
    both the path and d, every vertex projected along d onto the surface and raised by `lift`."""
    d = np.asarray(d, float)
    G = []
    for i in range(n_u):
        t = i / (n_u - 1)
        p = np.asarray(path2d_fn(t), float)
        pa = np.asarray(path2d_fn(min(1, t + 0.01)), float)
        pb = np.asarray(path2d_fn(max(0, t - 0.01)), float)
        tg = _unit(pa - pb)
        side = _unit(np.cross(tg, d))
        row = []
        for j in range(n_v):
            w = (j / (n_v - 1) - 0.5) * width
            q, _ = snap(rc, p + side * w, d, lift)
            row.append(tuple(q))
        G.append(row)
    return G


def convex_hull_2d(pts):
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def offset_polygon(poly, d):
    """Naive outward offset of a convex CCW polygon."""
    P = np.asarray(poly, float)
    n = len(P)
    out = []
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        e1 = _unit(b - a)
        e2 = _unit(c - b)
        n1 = np.array([e1[1], -e1[0]])
        n2 = np.array([e2[1], -e2[0]])
        m = _unit(n1 + n2)
        k = d / max(0.3, float(m @ n1))
        out.append(tuple(b + m * k))
    return out


def fit_text(ob, width, height=None):
    """Scale a flat text mesh (in XY) so its width is `width` (and height <= height), centred at the origin."""
    me = ob.data
    co = np.array([v.co[:] for v in me.vertices])
    mn, mx = co.min(0), co.max(0)
    w, h = mx[0] - mn[0], mx[1] - mn[1]
    s = width / w
    if height and h * s > height:
        s = height / h
    c = (mn + mx) / 2
    for v in me.vertices:
        v.co = Vector(((v.co.x - c[0]) * s, (v.co.y - c[1]) * s, v.co.z * (s if False else 1.0)))
    me.update()
