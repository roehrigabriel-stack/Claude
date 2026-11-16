"""Helpers for the body shell (tb.parts.body).

Core idea
---------
The half body (+X side) is ONE smooth parametric skin S(s, t):
  * s  = station parameter along the car (mostly equal to y; near the nose and the
         tail the rails have their own y so that the first column is the outline of
         the horseshoe opening and the last column the outline of the tail),
  * t  = rail parameter around the half section (t = k exactly on rail k).
Rails are space curves (x(s), y(s), z(s)) given by knots and natural cubic splines.
Between rails the section is a cubic Hermite curve with geometric (G1) tangents.

Panels are REGIONS of that skin, described by signed functions f(P, s, t) (< 0 inside)
written with 2D signed distances in a projection (side / plan / front) or in
parameter space. A panel is meshed from a dense (s, t) grid: faces whose centre is
inside are kept, and vertices that fall outside are slid along the grid lines onto
the boundary f = 0 (bisection), which gives perfectly clean cut lines of any shape.
Gaps between panels come from shrinking the region by half the gap.

Everything here is plain numpy (vectorised) except the final mesh creation.
"""
import math
import numpy as np

from tb import geo


# =====================================================================
# 1D interpolation (vectorised)
# =====================================================================
class Spline1D:
    """Natural cubic spline through (xs, ys); linear extrapolation outside."""

    def __init__(self, xs, ys):
        x = np.asarray(xs, float)
        y = np.asarray(ys, float)
        n = len(x)
        self.x, self.y = x, y
        if n < 3:
            self.m = np.zeros(n)
            return
        h = np.diff(x)
        a = np.zeros(n)
        b = np.ones(n)
        c = np.zeros(n)
        d = np.zeros(n)
        for i in range(1, n - 1):
            a[i] = h[i - 1]
            b[i] = 2.0 * (h[i - 1] + h[i])
            c[i] = h[i]
            d[i] = 6.0 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
        # Thomas algorithm (natural ends: m0 = mn = 0)
        cp = np.zeros(n)
        dp = np.zeros(n)
        for i in range(1, n - 1):
            den = b[i] - a[i] * cp[i - 1]
            cp[i] = c[i] / den
            dp[i] = (d[i] - a[i] * dp[i - 1]) / den
        m = np.zeros(n)
        for i in range(n - 2, 0, -1):
            m[i] = dp[i] - cp[i] * m[i + 1]
        self.m = m

    def __call__(self, t):
        t = np.asarray(t, float)
        x, y, m = self.x, self.y, self.m
        if len(x) == 1:
            return np.full_like(t, y[0])
        i = np.clip(np.searchsorted(x, t) - 1, 0, len(x) - 2)
        h = x[i + 1] - x[i]
        A = (x[i + 1] - t) / h
        B = (t - x[i]) / h
        inside = A * y[i] + B * y[i + 1] + ((A ** 3 - A) * m[i] + (B ** 3 - B) * m[i + 1]) * h * h / 6.0
        # linear extrapolation with end slopes
        s0 = (y[1] - y[0]) / (x[1] - x[0]) - (x[1] - x[0]) * (2 * m[0] + m[1]) / 6.0
        s1 = (y[-1] - y[-2]) / (x[-1] - x[-2]) + (x[-1] - x[-2]) * (m[-2] + 2 * m[-1]) / 6.0
        out = np.where(t < x[0], y[0] + (t - x[0]) * s0, inside)
        out = np.where(t > x[-1], y[-1] + (t - x[-1]) * s1, out)
        return out


class Pchip1D:
    """Monotone cubic (no overshoot), vectorised."""

    def __init__(self, xs, ys):
        x = np.asarray(xs, float)
        y = np.asarray(ys, float)
        self.x, self.y = x, y
        n = len(x)
        h = np.diff(x)
        dl = np.diff(y) / h
        m = np.zeros(n)
        for i in range(1, n - 1):
            if dl[i - 1] * dl[i] > 0:
                w1 = 2 * h[i] + h[i - 1]
                w2 = h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])
        if n > 1:
            m[0] = dl[0]
            m[-1] = dl[-1]
        self.m = m

    def __call__(self, t):
        t = np.clip(np.asarray(t, float), self.x[0], self.x[-1])
        x, y, m = self.x, self.y, self.m
        i = np.clip(np.searchsorted(x, t) - 1, 0, len(x) - 2)
        h = x[i + 1] - x[i]
        u = (t - x[i]) / h
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1
        h10 = u ** 3 - 2 * u ** 2 + u
        h01 = -2 * u ** 3 + 3 * u ** 2
        h11 = u ** 3 - u ** 2
        return h00 * y[i] + h10 * h * m[i] + h01 * y[i + 1] + h11 * h * m[i + 1]


def table(knots, kind='spline'):
    xs = [k[0] for k in knots]
    ys = [k[1] for k in knots]
    return Spline1D(xs, ys) if kind == 'spline' else Pchip1D(xs, ys)


# =====================================================================
# rails and skin
# =====================================================================
class Rail:
    """Space curve parameterised by the station s.

    knots: list of (s, x, z) or (s, x, z, y). y defaults to s.
    tension: scalar or list of (s, value) knots (scales the section tangents at this rail).
    """

    def __init__(self, name, knots, tension=1.0, kind='spline'):
        self.name = name
        if isinstance(kind, str):
            kind = (kind, kind, kind)
        cls = [Spline1D if k == 'spline' else Pchip1D for k in kind]
        ss = [k[0] for k in knots]
        self.knots = knots
        self.fx = cls[0](ss, [k[1] for k in knots])
        ys = [k[3] if len(k) > 3 and k[3] is not None else k[0] for k in knots]
        self.fy = cls[1](ss, ys)
        self.fz = cls[2](ss, [k[2] for k in knots])
        if isinstance(tension, (int, float)):
            self.ft = lambda s, v=float(tension): np.full_like(np.asarray(s, float), v)
        else:
            self.ft = Pchip1D([k[0] for k in tension], [k[1] for k in tension])

    def __call__(self, s):
        s = np.asarray(s, float)
        return np.stack([self.fx(s), self.fy(s), self.fz(s)], axis=-1)


class Skin:
    """Half-body skin through an ordered list of rails (rail 0 on the centreline)."""

    def __init__(self, rails, s0, s1):
        self.rails = rails
        self.K = len(rails) - 1
        self.s0, self.s1 = s0, s1
        self.names = {r.name: i for i, r in enumerate(rails)}

    def t_of(self, name):
        return float(self.names[name])

    def rail_points(self, s):
        s = np.asarray(s, float)
        return np.stack([r(s) for r in self.rails], axis=0)   # (K+1, N, 3)

    def eval(self, s, t):
        s = np.asarray(s, float).ravel()
        t = np.clip(np.asarray(t, float).ravel(), 0.0, self.K)
        R = self.rail_points(s)                       # (K+1, N, 3)
        K = self.K
        # ghost points: mirror of rail 1 before rail 0 (symmetry -> pure +x tangent)
        ghost0 = R[1].copy()
        ghost0[:, 0] *= -1.0
        ghostK = 2 * R[K] - R[K - 1]
        Rx = np.concatenate([ghost0[None], R, ghostK[None]], axis=0)   # index k+1
        k = np.clip(np.floor(t).astype(int), 0, K - 1)
        u = (t - k)[:, None]
        idx = np.arange(len(s))
        P0 = Rx[k + 1, idx]
        P1 = Rx[k + 2, idx]
        Pm = Rx[k, idx]
        P2 = Rx[k + 3, idx]
        d0 = np.linalg.norm(P1 - P0, axis=1)[:, None] + 1e-9
        dm = np.linalg.norm(P0 - Pm, axis=1)[:, None] + 1e-9
        d2 = np.linalg.norm(P2 - P1, axis=1)[:, None] + 1e-9
        # unit tangent directions at both ends (average of adjacent chord directions)
        T0 = (P1 - P0) / d0 + (P0 - Pm) / dm
        T1 = (P2 - P1) / d2 + (P1 - P0) / d0
        T0 /= np.linalg.norm(T0, axis=1)[:, None] + 1e-9
        T1 /= np.linalg.norm(T1, axis=1)[:, None] + 1e-9
        tens = np.stack([r.ft(s) for r in self.rails], axis=0)  # (K+1, N)
        a0 = tens[k, idx][:, None]
        a1 = tens[k + 1, idx][:, None]
        M0 = T0 * d0 * a0
        M1 = T1 * d0 * a1
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1
        h10 = u ** 3 - 2 * u ** 2 + u
        h01 = -2 * u ** 3 + 3 * u ** 2
        h11 = u ** 3 - u ** 2
        return h00 * P0 + h10 * M0 + h01 * P1 + h11 * M1

    def normal(self, s, t, eps_s=2e-3, eps_t=2e-3):
        s = np.asarray(s, float).ravel()
        t = np.asarray(t, float).ravel()
        ps = self.eval(np.minimum(s + eps_s, self.s1), t) - self.eval(np.maximum(s - eps_s, self.s0), t)
        pt = self.eval(s, np.minimum(t + eps_t, self.K)) - self.eval(s, np.maximum(t - eps_t, 0.0))
        n = np.cross(ps, pt)
        # orientation: outward = away from the car's centre axis
        P = self.eval(s, t)
        out = P - np.stack([np.zeros_like(s), P[:, 1], np.full_like(s, 0.55)], axis=1)
        sgn = np.sign(np.sum(n * out, axis=1))
        sgn[sgn == 0] = 1
        n *= sgn[:, None]
        return n / (np.linalg.norm(n, axis=1)[:, None] + 1e-12)

    # -------------------------------------------------- grids
    def column_params(self, ds, s0=None, s1=None):
        """Stations spaced by ~ds metres of mean rail arc length."""
        s0 = self.s0 if s0 is None else s0
        s1 = self.s1 if s1 is None else s1
        ss = np.linspace(s0, s1, 600)
        R = self.rail_points(ss)
        seg = np.linalg.norm(np.diff(R, axis=1), axis=2)          # (K+1, 599)
        L = np.concatenate([[0.0], np.cumsum(np.sqrt(np.mean(seg ** 2, axis=0)))])
        n = max(8, int(math.ceil(L[-1] / ds)))
        return np.interp(np.linspace(0, L[-1], n + 1), L, ss)

    def row_params(self, dt, t0=0.0, t1=None):
        """Rail parameters spaced by ~dt metres of (max over the length) arc length."""
        t1 = self.K if t1 is None else t1
        tt = np.linspace(t0, t1, 400)
        ss = np.linspace(self.s0 + 0.05, self.s1 - 0.05, 40)
        S, T = np.meshgrid(ss, tt, indexing='ij')
        P = self.eval(S.ravel(), T.ravel()).reshape(len(ss), len(tt), 3)
        seg = np.linalg.norm(np.diff(P, axis=1), axis=2)            # (40, 399)
        w = np.sqrt(np.mean(seg ** 2, axis=0))
        L = np.concatenate([[0.0], np.cumsum(w)])
        n = max(4, int(math.ceil(L[-1] / dt)))
        return np.interp(np.linspace(0, L[-1], n + 1), L, tt)


# =====================================================================
# 2D signed distances (vectorised)
# =====================================================================
def seg_dist(p, a, b):
    """Distance from points p (N,2) to segments a->b (M,2) -> (N, M)."""
    ab = b - a
    ap = p[:, None, :] - a[None, :, :]
    tt = np.clip(np.sum(ap * ab[None], axis=2) / (np.sum(ab * ab, axis=1)[None] + 1e-18), 0, 1)
    d = ap - tt[..., None] * ab[None]
    return np.sqrt(np.sum(d * d, axis=2))


def polyline_dist(p, poly):
    poly = np.asarray(poly, float)
    p = np.asarray(p, float).reshape(-1, 2)
    out = np.empty(len(p))
    for i0 in range(0, len(p), 4000):
        out[i0:i0 + 4000] = seg_dist(p[i0:i0 + 4000], poly[:-1], poly[1:]).min(axis=1)
    return out


def point_in_poly(p, poly):
    poly = np.asarray(poly, float)
    p = np.asarray(p, float).reshape(-1, 2)
    a = poly
    b = np.roll(poly, -1, axis=0)
    out = np.zeros(len(p), bool)
    for i0 in range(0, len(p), 4000):
        q = p[i0:i0 + 4000]
        x, y = q[:, 0:1], q[:, 1:2]
        cond = (a[None, :, 1] > y) != (b[None, :, 1] > y)
        xint = a[None, :, 0] + (y - a[None, :, 1]) * (b[None, :, 0] - a[None, :, 0]) / (b[None, :, 1] - a[None, :, 1] + 1e-18)
        out[i0:i0 + 4000] = (np.sum(cond & (x < xint), axis=1) % 2) == 1
    return out


def poly_sdf(p, poly):
    """Signed distance to a closed polygon (negative inside)."""
    poly = np.asarray(poly, float)
    closed = np.vstack([poly, poly[:1]])
    d = polyline_dist(p, closed)
    return np.where(point_in_poly(p, poly), -d, d)


def smooth_closed(points, per_seg=10):
    """Closed Catmull-Rom curve through points -> dense polygon (no duplicate end)."""
    pts = geo.catmull_rom([tuple(p) + (0.0,) * (3 - len(p)) for p in points], per_seg=per_seg, closed=True)
    arr = np.array([(q[0], q[1]) for q in pts])
    if np.linalg.norm(arr[0] - arr[-1]) < 1e-9:
        arr = arr[:-1]
    return arr


def smooth_open(points, per_seg=10):
    pts = geo.catmull_rom([tuple(p) + (0.0,) * (3 - len(p)) for p in points], per_seg=per_seg, closed=False)
    return np.array([(q[0], q[1]) for q in pts])


def offset_polyline_band(poly, half_w):
    """Closed polygon of a band of half width half_w around an open polyline (2D)."""
    poly = np.asarray(poly, float)
    d = np.gradient(poly, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None] + 1e-12
    n = np.stack([-d[:, 1], d[:, 0]], axis=1)
    return np.vstack([poly + n * half_w, (poly - n * half_w)[::-1]])


# projections of 3D points
def proj(P, plane):
    if plane == 'side':      # (y, z)
        return P[:, [1, 2]]
    if plane == 'plan':      # (x, y)
        return P[:, [0, 1]]
    if plane == 'front':     # (x, z)
        return P[:, [0, 2]]
    raise ValueError(plane)


class Region:
    """Signed region function. f(P, s, t) -> array, negative inside."""

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, P, s, t):
        return self.fn(P, s, t)

    def __and__(self, o):
        return Region(lambda P, s, t: np.maximum(self.fn(P, s, t), o.fn(P, s, t)))

    def __or__(self, o):
        return Region(lambda P, s, t: np.minimum(self.fn(P, s, t), o.fn(P, s, t)))

    def __sub__(self, o):
        return Region(lambda P, s, t: np.maximum(self.fn(P, s, t), -o.fn(P, s, t)))

    def grow(self, d):
        """Positive d grows the region by d metres (approx.), negative shrinks it."""
        return Region(lambda P, s, t: self.fn(P, s, t) - d)


def R_poly(poly, plane):
    poly = np.asarray(poly, float)
    return Region(lambda P, s, t: poly_sdf(proj(P, plane), poly))


def R_circle(center2, radius, plane='side'):
    c = np.asarray(center2, float)
    return Region(lambda P, s, t: np.linalg.norm(proj(P, plane) - c[None], axis=1) - radius)


def R_halfplane_fn(fn):
    return Region(fn)


def R_all():
    return Region(lambda P, s, t: np.full(len(P), -1.0))


# =====================================================================
# meshing of a region of the skin
# =====================================================================
def _bisect(skin, region, sa, ta, sb, tb, iters=12):
    """Root of region along param segments a (outside, f>0) -> b (inside, f<0)."""
    lo = np.zeros(len(sa))
    hi = np.ones(len(sa))
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        sm = sa + (sb - sa) * mid
        tm = ta + (tb - ta) * mid
        f = region(skin.eval(sm, tm), sm, tm)
        out = f > 0
        lo = np.where(out, mid, lo)
        hi = np.where(out, hi, mid)
    u = 0.5 * (lo + hi)
    return sa + (sb - sa) * u, ta + (tb - ta) * u


def mesh_region(skin, S, T, region, name, coll=None, offset=0.0, flip=False, return_params=False,
                min_faces=1,
                weld=0.0):
    """Mesh the part of the skin grid (S stations x T rails) where region < 0.

    offset: push the surface along its normal (m). Returns the object (or None)."""
    nS, nT = len(S), len(T)
    SS, TT = np.meshgrid(S, T, indexing='ij')
    ss, tt = SS.ravel(), TT.ravel()
    P = skin.eval(ss, tt)
    fv = region(P, ss, tt).reshape(nS, nT)
    # face centres
    Sc = 0.5 * (S[:-1] + S[1:])
    Tc = 0.5 * (T[:-1] + T[1:])
    SC, TC = np.meshgrid(Sc, Tc, indexing='ij')
    Pc = skin.eval(SC.ravel(), TC.ravel())
    fc = region(Pc, SC.ravel(), TC.ravel()).reshape(nS - 1, nT - 1)
    keep = fc < 0
    if keep.sum() < min_faces:
        return None
    used = np.zeros((nS, nT), bool)
    used[:-1, :-1] |= keep
    used[1:, :-1] |= keep
    used[:-1, 1:] |= keep
    used[1:, 1:] |= keep
    vs = SS.copy()
    vt = TT.copy()
    bad = used & (fv > 0)
    bi, bj = np.nonzero(bad)
    if len(bi):
        best_s = np.full(len(bi), np.nan)
        best_t = np.full(len(bi), np.nan)
        best_d = np.full(len(bi), np.inf)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            ni, nj = bi + di, bj + dj
            ok = (ni >= 0) & (ni < nS) & (nj >= 0) & (nj < nT)
            ni2 = np.clip(ni, 0, nS - 1)
            nj2 = np.clip(nj, 0, nT - 1)
            ok &= fv[ni2, nj2] < 0
            if di != 0 and dj != 0:
                ok &= ~np.isfinite(best_d)      # diagonals only as a last resort
            if not ok.any():
                continue
            sa, ta = SS[bi[ok], bj[ok]], TT[bi[ok], bj[ok]]
            sb, tb = SS[ni2[ok], nj2[ok]], TT[ni2[ok], nj2[ok]]
            rs, rt = _bisect(skin, region, sa, ta, sb, tb)
            # metric move length
            pa = skin.eval(sa, ta)
            pr = skin.eval(rs, rt)
            dd = np.linalg.norm(pr - pa, axis=1)
            idx = np.nonzero(ok)[0]
            better = dd < best_d[idx]
            best_d[idx[better]] = dd[better]
            best_s[idx[better]] = rs[better]
            best_t[idx[better]] = rt[better]
        okm = np.isfinite(best_d)
        vs[bi[okm], bj[okm]] = best_s[okm]
        vt[bi[okm], bj[okm]] = best_t[okm]
    # vertex list
    vid = -np.ones((nS, nT), int)
    ui, uj = np.nonzero(used)
    vid[ui, uj] = np.arange(len(ui))
    ps, pt = vs[ui, uj], vt[ui, uj]
    V = skin.eval(ps, pt)
    if offset:
        V = V + skin.normal(ps, pt) * offset
    fi, fj = np.nonzero(keep)
    F = np.stack([vid[fi, fj], vid[fi + 1, fj], vid[fi + 1, fj + 1], vid[fi, fj + 1]], axis=1)
    # orientation: the grid (s along +y, t going down/outward) gives normals ... check one face
    if len(F):
        a, b, c = V[F[0, 0]], V[F[0, 1]], V[F[0, 2]]
        n = np.cross(b - a, c - a)
        nn = skin.normal(np.array([ps[F[0, 0]]]), np.array([pt[F[0, 0]]]))[0]
        if np.dot(n, nn) < 0:
            F = F[:, ::-1]
    if flip:
        F = F[:, ::-1]
    # remove degenerate quads (collapsed by snapping) -> triangles
    faces = []
    for q in F:
        pts = V[q]
        uniq = [q[0]]
        for k in range(1, 4):
            if np.linalg.norm(V[q[k]] - V[uniq[-1]]) > 1e-6:
                uniq.append(q[k])
        if len(uniq) > 1 and np.linalg.norm(V[uniq[-1]] - V[uniq[0]]) < 1e-6:
            uniq.pop()
        if len(uniq) >= 3:
            faces.append(uniq)
    ob = geo.new_object(name, V, faces, coll=coll, smooth=True, sharp_angle=None)
    geo.merge_by_distance(ob, max(1e-6, weld))
    if return_params:
        return ob, (ps, pt)
    return ob


# =====================================================================
# inverse mapping: find (s, t) whose projection hits a 2D point
# =====================================================================
class Inverter:
    """Find skin parameters for target points in a projection plane, restricted
    to a parameter window (s range, t range) where the projection is one-to-one."""

    def __init__(self, skin, plane, s_rng, t_rng, n=160):
        self.skin = skin
        self.plane = plane
        ss = np.linspace(s_rng[0], s_rng[1], n)
        tt = np.linspace(t_rng[0], t_rng[1], n)
        S, T = np.meshgrid(ss, tt, indexing='ij')
        self.S, self.T = S.ravel(), T.ravel()
        self.Q = proj(skin.eval(self.S, self.T), plane)
        self.s_rng, self.t_rng = s_rng, t_rng

    def __call__(self, pts2):
        pts2 = np.asarray(pts2, float).reshape(-1, 2)
        out_s = np.empty(len(pts2))
        out_t = np.empty(len(pts2))
        for i, q in enumerate(pts2):
            j = np.argmin(np.sum((self.Q - q) ** 2, axis=1))
            s, t = self.S[j], self.T[j]
            for _ in range(12):
                e = 1e-4
                p0 = proj(self.skin.eval([s], [t]), self.plane)[0]
                ps = (proj(self.skin.eval([s + e], [t]), self.plane)[0] - p0) / e
                pt = (proj(self.skin.eval([s], [t + e]), self.plane)[0] - p0) / e
                J = np.stack([ps, pt], axis=1)
                r = q - p0
                if np.linalg.norm(r) < 1e-7:
                    break
                try:
                    d = np.linalg.solve(J, r)
                except np.linalg.LinAlgError:
                    break
                lim = 0.05
                d = np.clip(d, -lim * 4, lim * 4)
                s = float(np.clip(s + d[0], self.s_rng[0] - 0.2, self.s_rng[1] + 0.2))
                t = float(np.clip(t + d[1], 0.0, self.skin.K))
            out_s[i], out_t[i] = s, t
        return out_s, out_t


# =====================================================================
# recesses / tunnels / lips from a 3D loop
# =====================================================================
def loop_on_skin(skin, inverter, poly2):
    s, t = inverter(poly2)
    return skin.eval(s, t), skin.normal(s, t), (s, t)


def tunnel(name, loop, normals, depth, coll=None, cap=True, taper=0.0, steps=3, bulge=0.0,
           direction=None):
    """Tube from a closed 3D loop pushed inwards (along -normals or along -direction)
    by `depth`, optionally shrinking towards the loop centroid (taper 0..1), with an
    end cap. Returns the object."""
    loop = np.asarray(loop, float)
    n = len(loop)
    nrm = np.asarray(normals, float)
    if direction is not None:
        dvec = np.tile(np.asarray(direction, float), (n, 1))
    else:
        dvec = nrm
    c = loop.mean(axis=0)
    rings = []
    for k in range(steps + 1):
        u = k / steps
        r = loop - dvec * depth * u
        cc = c - dvec.mean(axis=0) * depth * u
        r = cc + (r - cc) * (1.0 - taper * u)
        rings.append(r)
    verts = np.vstack(rings)
    faces = []
    for k in range(steps):
        for i in range(n):
            i2 = (i + 1) % n
            faces.append([k * n + i, k * n + i2, (k + 1) * n + i2, (k + 1) * n + i])
    if cap:
        cid = len(verts)
        verts = np.vstack([verts, rings[-1].mean(axis=0)[None]])
        for i in range(n):
            i2 = (i + 1) % n
            faces.append([steps * n + i, steps * n + i2, cid])
    ob = geo.new_object(name, verts, faces, coll=coll, smooth=True, sharp_angle=60.0)
    geo.recalc_normals(ob)
    return ob


def resample_closed(poly, n):
    poly = np.asarray(poly, float)
    closed = np.vstack([poly, poly[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, L[-1], n, endpoint=False)
    return np.stack([np.interp(u, L, closed[:, k]) for k in range(poly.shape[1])], axis=1)


def resample_open(poly, n):
    poly = np.asarray(poly, float)
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, L[-1], n)
    return np.stack([np.interp(u, L, poly[:, k]) for k in range(poly.shape[1])], axis=1)
