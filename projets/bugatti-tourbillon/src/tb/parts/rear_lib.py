"""Helpers for the rear-end module (mesh builder, text fitting, small functions)."""
import math
import numpy as np
import bpy
from mathutils import Matrix
from tb import geo


def S(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


class MB:
    """Tiny mesh accumulator with oriented strips."""

    def __init__(self):
        self.v = []
        self.f = []

    def add(self, pts):
        i = len(self.v)
        self.v += [tuple(map(float, p)) for p in pts]
        return list(range(i, i + len(pts)))

    def strip(self, ra, rb, want, closed=True):
        n = len(ra)
        faces = []
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            faces.append([ra[k], ra[k2], rb[k2], rb[k]])
        f = faces[0]
        p = [np.array(self.v[i]) for i in f]
        nrm = np.cross(p[2] - p[0], p[3] - p[1])
        c = sum(p) / 4.0
        if np.dot(nrm, np.array(want(c))) < 0:
            faces = [ff[::-1] for ff in faces]
        self.f += faces

    def cap(self, ring, want):
        f = list(ring)
        p = [np.array(self.v[i]) for i in f]
        nrm = np.zeros(3)
        for k in range(len(p)):
            a, b = p[k], p[(k + 1) % len(p)]
            nrm += np.cross(a, b)
        if np.dot(nrm, np.array(want)) < 0:
            f = f[::-1]
        self.f.append(f)

    def obj(self, name, coll, sharp=35.0):
        return geo.new_object(name, self.v, self.f, coll=coll, smooth=True, sharp_angle=sharp)


def tube(name, secs, coll, sharp=35.0, cap=True):
    """Closed-section loft: secs = [n_sections][k points] (no resampling)."""
    ob = geo.grid_surface(name, np.array(secs, dtype=float), close_v=True, coll=coll, smooth=True,
                          sharp_angle=sharp, uv=False)
    if cap:
        geo.fill_holes(ob)
    geo.recalc_normals(ob)
    return ob


def fit_text(name, body, w, h, extrude, coll, shear=0.0):
    """Text mesh in XY plane scaled to w x h (bounds), centred on origin, sheared."""
    ob = geo.text_mesh(name, body, size=0.1, extrude=extrude, coll=coll)
    lo, hi = geo.bounds([ob])
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    sx = w / max(hi.x - lo.x, 1e-6)
    sy = h / max(hi.y - lo.y, 1e-6)
    m = Matrix(((sx, shear * sy, 0, -cx * sx - shear * sy * cy),
                (0, sy, 0, -cy * sy),
                (0, 0, 1, 0),
                (0, 0, 0, 1)))
    geo.transform_mesh(ob, m)
    return ob


def face_up(ob):
    """Flip normals if the mean polygon normal points down."""
    nz = sum(p.normal.z * p.area for p in ob.data.polygons)
    if nz < 0:
        geo.flip_normals(ob)
    return ob
