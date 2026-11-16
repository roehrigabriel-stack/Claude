"""Helpers for tb.parts.wheels: tyre, rim, brake geometry of the Tourbillon wheels.

Everything is authored in a WHEEL-LOCAL frame and baked into world coordinates:
  a = axial coordinate, positive OUTBOARD (world +X for left wheels, -X for right)
  (y, z) = world y / z offsets from the wheel centre; polar angle phi with
  y = r cos(phi), z = r sin(phi)   (phi = 0 points to the rear of the car, 90 up).
side s = +1 (left, +X) or -1 (right): world = centre + (s * a, y, z).
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from tb import geo, mats, spec

TAU = 2.0 * math.pi


# =====================================================================
# axle specific parameters
# =====================================================================
def axle_params(key):
    front = key[0] == 'F'
    t = spec.TIRE_F if front else spec.TIRE_R
    disc = spec.BRAKE_DISC_F if front else spec.BRAKE_DISC_R
    P = dict(front=front, key=key)
    P['W'] = t['width']
    P['H'] = t['sidewall']
    P['Rr'] = t['rim_d'] / 2.0                 # bead seat radius
    P['Ro'] = t['radius']                      # tyre outer radius
    P['J2'] = (9.5 if front else 11.5) * 0.0254 / 2.0   # half rim width (bead seat to bead seat)
    P['fl_t'] = 0.0085                         # flange thickness
    P['fl_h'] = 0.0175                         # flange height above the bead seat
    P['Rf'] = P['Rr'] - 0.008                  # outer radius of the spoke face (meets the lip)
    P['a_rim'] = P['J2'] + 0.0015              # spoke front face at the rim
    P['a_hub'] = P['a_rim'] - 0.044            # spoke front face at the hub (dish depth)
    P['d_hub'] = 0.033                         # spoke depth at the hub
    P['a_mount'] = P['a_hub'] - P['d_hub']     # hub mounting face
    P['x_d'] = P['a_mount'] - 0.066            # brake disc centre plane
    P['disc_ro'] = disc['d'] / 2.0
    P['disc_t'] = disc['t']
    P['disc_ri'] = P['disc_ro'] - (0.066 if front else 0.060)
    P['cal_span'] = 30.0 if front else 25.0    # caliper half span (deg) at the outer radius
    P['cal_phi'] = 18.0     # rear half of the disc at both axles (photos)
    P['cal_w'] = 0.060 if front else 0.052     # caliper half width (axial)
    P['pitches'] = 58 if front else 62
    P['aspect'] = t['aspect']
    return P


def to_world_matrix(key, side):
    c = spec.WHEELS[key]
    return Matrix(((side, 0, 0, c[0]), (0, 1, 0, c[1]), (0, 0, 1, c[2]), (0, 0, 0, 1)))


def bake(obj, key, side=1):
    """Bake local -> world. For side -1 the reflection is compensated by flipping normals."""
    obj.data.transform(to_world_matrix(key, side))
    if side < 0:
        obj.data.flip_normals()
    obj.data.update()
    return obj


def polar(r, phi_deg):
    p = math.radians(phi_deg)
    return (r * math.cos(p), r * math.sin(p))


# =====================================================================
# 2D convex polygon tools (window outlines of the spokes)
# =====================================================================
def hp_line(p, q, offset, ref):
    """Half plane bounded by the line p-q shifted by `offset` towards `ref`,
    containing ref. Returns (n, d): inside is n.x <= d."""
    p, q, ref = np.asarray(p, float), np.asarray(q, float), np.asarray(ref, float)
    e = q - p
    n = np.array([e[1], -e[0]]) / np.linalg.norm(e)
    if np.dot(n, ref - p) > 0:
        n = -n
    return (n, float(np.dot(n, p)) - offset)


def hp_circle_inside(radius, a0, a1, step=3.0):
    """Tangent half planes approximating 'inside the circle' between angles a0..a1 (deg)."""
    out = []
    a = a0
    while a <= a1 + 1e-9:
        n = np.array(polar(1.0, a))
        out.append((n, radius))
        a += step
    return out


def clip_convex(hps, big=10.0):
    poly = [np.array(v, float) for v in ((-big, -big), (big, -big), (big, big), (-big, big))]
    for n, d in hps:
        out = []
        m = len(poly)
        for i in range(m):
            a, b = poly[i], poly[(i + 1) % m]
            da, db = np.dot(n, a) - d, np.dot(n, b) - d
            if da <= 0:
                out.append(a)
            if da * db < 0:
                t = da / (da - db)
                out.append(a + t * (b - a))
        poly = out
        if not poly:
            break
    # drop near duplicates
    res = []
    for p in poly:
        if not res or np.linalg.norm(p - res[-1]) > 1e-7:
            res.append(p)
    if len(res) > 1 and np.linalg.norm(res[0] - res[-1]) < 1e-7:
        res.pop()
    return res


def rounded_outline(hps, rc, grow=0.0, deg_step=7.5):
    """Convex region of half planes with every corner rounded (radius rc), then
    offset by `grow`. Same vertex count for any `grow` (lofting front/back)."""
    inset = [(n, d - rc) for n, d in hps]
    Q = clip_convex(inset)
    m = len(Q)
    pts = []
    for k in range(m):
        prev, cur, nxt = Q[k - 1], Q[k], Q[(k + 1) % m]
        e0, e1 = cur - prev, nxt - cur
        n0 = math.atan2(-e0[0], e0[1])
        n1 = math.atan2(-e1[0], e1[1])
        sweep = (n1 - n0) % TAU
        if sweep > math.pi:            # should not happen for CCW convex input
            sweep = 0.0
        cnt = max(1, int(math.ceil(math.degrees(sweep) / deg_step)))
        R = rc + grow
        for i in range(cnt + 1):
            t = n0 + sweep * i / cnt
            pts.append((cur[0] + R * math.cos(t), cur[1] + R * math.sin(t)))
    return pts


def prism_between(name, front_pts, back_pts, a_front, a_back, coll=None, to_yz=None):
    """Closed prism lofted from a front outline (at axial a_front) to a back outline."""
    n = len(front_pts)
    verts = []
    for (u, v) in front_pts:
        y, z = to_yz(u, v) if to_yz else (u, v)
        verts.append((a_front, y, z))
    for (u, v) in back_pts:
        y, z = to_yz(u, v) if to_yz else (u, v)
        verts.append((a_back, y, z))
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, n + i, n + j, j])
    ob = geo.new_object(name, verts, faces, coll=coll, smooth=False)
    geo.recalc_normals(ob)
    return ob


# =====================================================================
# profile curve utilities
# =====================================================================
class Profile:
    """Dense (a, r) polyline parametrised by arc length."""

    def __init__(self, pts, per_seg=10):
        dense = geo.catmull_rom([tuple(p) for p in pts], per_seg=per_seg, closed=False)
        P = np.asarray(dense, float)[:, :2]
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        keep = np.concatenate([[True], seg > 1e-9])
        P = P[keep]
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        self.P = P
        self.s = np.concatenate([[0.0], np.cumsum(seg)])
        self.L = float(self.s[-1])

    def at(self, s):
        s = min(max(s, 0.0), self.L)
        a = float(np.interp(s, self.s, self.P[:, 0]))
        r = float(np.interp(s, self.s, self.P[:, 1]))
        return a, r

    def normal(self, s, h=4e-4):
        a0, r0 = self.at(s - h)
        a1, r1 = self.at(s + h)
        t = np.array([a1 - a0, r1 - r0])
        t /= np.linalg.norm(t)
        return np.array([t[1], -t[0]])      # rotate -90 deg


# =====================================================================
# TYRE
# =====================================================================
def tyre_half_profile(P):
    """Outer surface of the tyre from the crown centre (a=0) to the bead, outboard half."""
    W, H, Rr, Ro, J2 = P['W'], P['H'], P['Rr'], P['Ro'], P['J2']
    afo = J2 + P['fl_t']
    hw = W / 2.0
    pts = [
        (0.000, Ro),
        (0.35 * hw, Ro - 0.0006),
        (0.62 * hw, Ro - 0.0022),
        (hw - 0.030, Ro - 0.0050),
        (hw - 0.015, Ro - 0.0105),
        (hw - 0.0055, Ro - 0.0200),
        (hw - 0.0010, Ro - 0.0340),
        (hw + 0.0000, Rr + 0.56 * H),
        (hw - 0.0030, Rr + 0.36 * H),
        (hw - 0.0090, Rr + 0.050),
        (afo + 0.0125, Rr + 0.0345),
        (afo + 0.0128, Rr + 0.0300),   # rim protector rib nose
        (afo + 0.0122, Rr + 0.0262),
        (afo + 0.0040, Rr + 0.0205),   # tuck onto the flange curl
        (J2 - 0.0005, Rr + 0.0150),    # (inside the flange from here, hidden)
        (J2 - 0.0020, Rr + 0.0020),
        (J2 - 0.0200, Rr - 0.0010),
    ]
    return Profile(pts, per_seg=12)


def tyre_pattern(P):
    """Tread pattern in terms of the signed profile arc length q (0 at the crown
    centre, + outboard). Returns dict of grooves and slot families."""
    T = P['W'] / 2.0 - 0.030           # half tread width (approx arc length)
    g = dict(T=T)
    # circumferential grooves: (q_centre, width, depth)
    g['circ'] = [(-0.50 * T, 0.105 * T, 0.0068),
                 (-0.04 * T, 0.090 * T, 0.0065),
                 (0.47 * T, 0.030 * T, 0.0035)]
    # slot families: q range (closed end, open end), theta' window as pitch fraction, depth
    g['slots'] = [
        dict(q0=-0.72 * T, q1=-1.6 * T, t0=0.06, t1=0.30, depth=0.0055),   # inboard shoulder blocks
        dict(q0=0.80 * T, q1=1.6 * T, t0=0.52, t1=0.64, depth=0.0045),     # outboard shoulder
        dict(q0=-0.42 * T, q1=-0.10 * T, t0=0.52, t1=0.60, depth=0.0040, both=True),  # centre sipes
    ]
    return g


def build_tyre(name, key, side, quality, coll):
    """Tyre = sidewall revolve + patterned tread band + raised sidewall lettering."""
    P = axle_params(key)
    prof = tyre_half_profile(P)
    pat = tyre_pattern(P)
    T = pat['T']
    final = quality == 'final'
    pat['slots'] = pat['slots'][:2] if final else pat['slots'][:1]
    if not final:
        P = dict(P, pitches=P['pitches'] // 4)
    q_seam = 1.62 * T                       # tread band ends here (on the upper sidewall)
    if q_seam > prof.L * 0.6:
        q_seam = prof.L * 0.6

    def point(q):
        """(a, r) and INWARD unit normal (towards the tyre interior) for signed arc length q."""
        s = abs(q)
        a, r = prof.at(s)
        n = prof.normal(s)                  # profile runs crown -> bead: this is the inward normal
        if q < 0:
            a = -a
            n = np.array([-n[0], n[1]])
        return a, r, n

    # ---- column positions across the tread band (q), with doubled columns at walls
    eps = 0.0004
    cols = set()
    nb = 18 if final else 8
    for i in range(nb + 1):
        cols.add(round(-q_seam + 2 * q_seam * i / nb, 6))
    walls = []
    for qc, w, d in pat['circ']:
        for e in (qc - w / 2, qc + w / 2):
            walls.append(e)
    for sl in pat['slots']:
        walls.append(sl['q0'])
        if sl.get('both'):
            walls.append(sl['q1'])
    for e in walls:
        cols.add(round(e - eps / 2, 6))
        cols.add(round(e + eps / 2, 6))
    # extra columns near the fading slot ends over the shoulders
    for q in np.linspace(T, q_seam, 5 if final else 3):
        cols.add(round(q, 6))
        cols.add(round(-q, 6))
    cols = sorted(c for c in cols if -q_seam - 1e-9 <= c <= q_seam + 1e-9)

    def circ_depth(q):
        for qc, w, d in pat['circ']:
            if abs(q - qc) < w / 2:
                return d
        return 0.0

    # ---- rows per pitch (theta' as pitch fraction); 'inside' rows of each slot family
    epst = 0.0004 / P['Ro'] / (TAU / P['pitches'])     # 0.4 mm in pitch units
    rows = []   # (t, {family index: inside?})
    edges = []
    for fi, sl in enumerate(pat['slots']):
        edges += [(sl['t0'], fi, False), (sl['t0'] + epst, fi, True),
                  (sl['t1'] - epst, fi, True), (sl['t1'], fi, False)]
    fill = [0.0, 0.42]
    tlist = sorted(set([round(t, 6) for t in fill] + [round(e[0], 6) for e in edges]))

    def inside_family(t, fi):
        sl = pat['slots'][fi]
        return sl['t0'] + epst * 0.5 < t < sl['t1'] - epst * 0.5

    def slot_depth(q, t):
        d = 0.0
        for fi, sl in enumerate(pat['slots']):
            if not inside_family(t, fi):
                continue
            q0, q1 = sl['q0'], sl['q1']
            lo, hi = min(q0, q1), max(q0, q1)
            if sl.get('both'):
                if lo < q < hi:
                    d = max(d, sl['depth'])
                continue
            # closed at q0, fades out towards q1 over the shoulder
            if not (lo < q < hi) and not (abs(q - q0) < 1e-9):
                continue
            if (q - q0) * (q1 - q0) <= 1e-9:
                continue
            u = abs(q - q0) / abs(q1 - q0)
            fade = 1.0 - geo.smoothstep(0.35, 1.0, u)
            d = max(d, sl['depth'] * fade)
        return d

    Np = P['pitches']
    pitch = TAU / Np

    def warp(q):
        x = q / T
        return pitch * (0.10 * x + 0.16 * x * abs(x) * x / (1 + abs(x)))

    grid = []
    for k in range(Np):
        for t in tlist:
            row = []
            th0 = (k + t) * pitch
            for q in cols:
                a, r, n = point(q)
                d = max(circ_depth(q), slot_depth(q, t))
                a += n[0] * d
                r += n[1] * d
                th = th0 + warp(q)
                row.append((a, r * math.cos(th), r * math.sin(th)))
            grid.append(row)
    tread = geo.grid_surface(name + '_Tread', grid, close_u=True, coll=coll, sharp_angle=50.0, uv=False)
    # orientation: make normals point away from the axle at the crown
    _orient_outward(tread)

    # ---- sidewalls: revolve the rest of the profile (both halves)
    nseg = 128 if final else 64
    s_seam = q_seam
    ss = np.linspace(s_seam - 0.006, prof.L, 30 if final else 14)
    half = []
    for s_ in ss:
        a_, r_ = prof.at(s_)
        if s_ < s_seam + 0.004:          # tuck the overlap under the tread band (no crack at the seam)
            n_ = prof.normal(s_)
            a_ += n_[0] * 0.0006
            r_ += n_[1] * 0.0006
        half.append((a_, r_))
    side_objs = []
    for sgn, tag in ((1, 'Out'), (-1, 'In')):
        prof2 = [(r, sgn * a) for a, r in half]
        # the seam must coincide with the warped tread row positions: revolve uses
        # plain angles, the tiny chord gap is invisible at this resolution
        ob = geo.revolve(name + '_Side' + tag, prof2, segments=nseg, axis='X', coll=coll,
                         sharp_angle=60.0)
        _orient_outward(ob)
        side_objs.append(ob)

    # ---- raised lettering on the outboard sidewall
    letters = build_sidewall_text(name + '_Text', P, prof, side, coll, final)

    objs = [tread] + side_objs + letters
    for ob in objs[:3]:
        mats.assign(ob, 'rubber_tire')
    for ob in objs[3:]:
        mats.assign(ob, mats.custom('tyre_marking', base_color='#4A4B4D', metallic=0.0, roughness=0.55))
    for ob in objs:
        bake(ob, key, side)
    tyre = geo.join(objs, name)
    return tyre


def _orient_outward(ob):
    """Flip an open surface of revolution about the local a-axis so that its normals
    point away from the tyre interior (towards larger radius / outside)."""
    me = ob.data
    score = 0.0
    for p in me.polygons:
        c = p.center
        radial = Vector((0.0, c.y, c.z))
        if radial.length < 1e-6:
            continue
        # outward = away from the torus core circle at radius ~ 0.31
        core = radial.normalized() * 0.30
        out = Vector((c.x, c.y, c.z)) - Vector((0.0, core.y, core.z))
        score += p.normal.dot(out.normalized()) * p.area
    if score < 0:
        me.flip_normals()
        me.update()


def build_sidewall_text(name, P, prof, side, coll, final):
    """MICHELIN / PILOT SPORT CUP 2 / size marking as raised letters bent around the axle."""
    # sidewall a(r) lookup from the profile (r increasing between the rib and the bulge)
    s_vals = np.linspace(0.0, prof.L, 600)
    ar = np.array([prof.at(s) for s in s_vals])
    Rr, H = P['Rr'], P['H']
    mask = (ar[:, 1] > Rr + 0.030) & (ar[:, 1] < P['Ro'] - 0.030)
    sub = ar[mask]
    order = np.argsort(sub[:, 1])
    r_tab, a_tab = sub[order, 1], sub[order, 0]

    def a_of_r(r):
        return float(np.interp(r, r_tab, a_tab))

    t = spec.TIRE_F if P['front'] else spec.TIRE_R
    size_txt = '%d/%d ZR %d' % (round(t['width'] * 1000), round(t['aspect'] * 100), t['rim_in'])
    rho_m = Rr + 0.50 * H
    items = [
        ('MICHELIN', 0.026, rho_m, 90.0, 1.06),
        ('MICHELIN', 0.026, rho_m, 270.0, 1.06),
        ('PILOT SPORT CUP 2', 0.0165, rho_m, 0.0, 1.0),
        ('PILOT SPORT CUP 2', 0.0165, rho_m, 180.0, 1.0),
        (size_txt, 0.0125, Rr + 0.30 * H, 135.0, 1.0),
        (size_txt, 0.0125, Rr + 0.30 * H, 315.0, 1.0),
    ]
    out = []
    for i, (txt, size, rho0, phi0, spacing) in enumerate(items):
        ob = geo.text_mesh('%s_%d' % (name, i), txt, size=size, extrude=0.0006, coll=coll, spacing=spacing)
        _subdivide_long_edges(ob, 0.004 if final else 0.009)
        me = ob.data
        lo = min(v.co.y for v in me.vertices)
        hi = max(v.co.y for v in me.vertices)
        vmid = 0.5 * (lo + hi)
        for v in me.vertices:
            u, w = v.co.x, v.co.z + 0.00025
            rr = rho0 + (v.co.y - vmid)
            phi = math.radians(phi0) - side * u / rho0
            a = a_of_r(rr) + w
            # local a is outboard; bake() applies the side reflection later, so the
            # reading direction is reversed here for the right side (u -> -u)
            v.co = Vector((a, rr * math.cos(phi), rr * math.sin(phi)))
        if side < 0:
            me.flip_normals()   # u was reflected; bake() reflects again
        me.update()
        out.append(ob)
    # chequered flag band on the upper sidewall (shoulder)
    sub2 = ar[(ar[:, 1] > Rr + 0.030) & (ar[:, 1] < P['Ro'] - 0.012)]
    o2 = np.argsort(sub2[:, 1])
    r2, a2 = sub2[o2, 1], sub2[o2, 0]
    rows = np.linspace(P['Ro'] - 0.034, P['Ro'] - 0.014, 4)
    N = 240 if final else 90
    verts, faces = [], []
    for j in range(3):
        for i in range(N):
            if (i + j) % 2:
                continue
            quad = []
            for (rr, ph) in ((rows[j], i), (rows[j + 1], i), (rows[j + 1], i + 1), (rows[j], i + 1)):
                a = float(np.interp(rr, r2, a2)) + 0.0004
                phi = TAU * ph / N
                quad.append(len(verts))
                verts.append((a, rr * math.cos(phi), rr * math.sin(phi)))
            f = quad if side > 0 else quad[::-1]
            v0, v1, v3 = (Vector(verts[f[0]]), Vector(verts[f[1]]), Vector(verts[f[3]]))
            if (v1 - v0).cross(v3 - v0).x * side < 0:
                f = f[::-1]
            faces.append(f)
    chk = geo.new_object(name + '_Chk', verts, faces, coll=coll)
    out.append(chk)
    return out


def _subdivide_long_edges(ob, max_len):
    """Triangulate and split long edges so letters follow curved surfaces."""
    def fn(bm):
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        for _ in range(3):
            long_e = [e for e in bm.edges if e.calc_length() > max_len]
            if not long_e:
                break
            bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=False)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
    geo._bm_edit(ob, fn)


# =====================================================================
# RIM
# =====================================================================
def face_a(P, rho):
    """Axial position of the spoke front face at normalised radius rho = r / Rf."""
    g = geo.Pchip([0.0, 0.34, 0.50, 0.70, 0.88, 1.0, 1.1], [0.0, 0.0, 0.22, 0.60, 0.88, 1.0, 1.0])
    return P['a_hub'] + (P['a_rim'] - P['a_hub']) * float(g(min(max(rho, 0.0), 1.1)))


def spoke_depth(P, rho):
    return geo.lerp(P['d_hub'], 0.021, geo.smoothstep(0.25, 1.0, rho))


def _edge_pts(ang_deg, r0, w0, r1, w1, sgn):
    """Two points of one edge of a tapered radial bar along direction ang_deg
    (normalised units). sgn=+1: edge on the counter-clockwise side."""
    d = np.array(polar(1.0, ang_deg))
    n = np.array([-d[1], d[0]]) * sgn
    return d * r0 + n * w0 / 2, d * r1 + n * w1 / 2


def window_outlines(P, grow, design=None):
    """The 10 spoke windows as lists of (y, z) in metres for one `grow` offset.
    Tourbillon Y spokes: stem k at angle s_k (hub to fork node F), forks into two arms to the
    rim pads at s_k +- 36 deg, where it meets the neighbouring spoke's arm.
      big windows  (5): inside each fork, between the two arms, closed by the rim arc
      small gaps   (5): between neighbouring stems, closed at the pad, open to the hub"""
    D = dict(rhoF=0.48, wA=0.135, wS=0.185, pad_deg=26.0, rho_hub=0.30, rho_rim=0.955, rcW=0.075, rcG=0.065, pad=0.0)
    if design:
        D.update(design)
    Rf = P['Rf']
    wA, wS = D['wA'], D['wS']
    fr = D['rhoF']
    s0, p0 = 90.0, 90.0 - 36.0         # spoke 0 at 90 deg, pad between spoke 0 and the next CW
    F0 = np.array(polar(fr, s0))
    Pl = np.array(polar(1.03, s0 + 36.0))
    Pr = np.array(polar(1.03, s0 - 36.0))
    c_big = np.array(polar(0.75, s0))
    big = [hp_line(F0, Pl, wA / 2, c_big), hp_line(F0, Pr, wA / 2, c_big)]
    o = np.zeros(2)
    big += [hp_line(o, np.array(polar(1.0, s0 + D['pad_deg'])), 0.0, c_big),
            hp_line(o, np.array(polar(1.0, s0 - D['pad_deg'])), 0.0, c_big)]
    big += hp_circle_inside(D['rho_rim'], s0 - 40.0, s0 + 40.0, 2.0)
    W = rounded_outline(big, D['rcW'], grow / Rf)
    # small gap centred on the pad at p0, between spoke 0 (s0) and spoke -1 (s0 - 72)
    F1 = np.array(polar(fr, s0 - 72.0))
    Pp = np.array(polar(1.03, p0))
    c_g = np.array(polar(0.55, p0))
    gap = [hp_line(F0, Pp, wA / 2, c_g), hp_line(F1, Pp, wA / 2, c_g),
           hp_line(np.array(polar(0.0, 0.0)), F0, wS / 2, c_g),
           hp_line(np.array(polar(0.0, 0.0)), F1, wS / 2, c_g)]
    nrm = np.array(polar(1.0, p0))
    gap.append((-nrm, -D['rho_hub']))
    G = rounded_outline(gap, D['rcG'], grow / Rf)
    ps = []
    for k in range(5):
        rot = math.radians(72.0 * k)
        c, sn = math.cos(rot), math.sin(rot)
        for poly in (W, G):
            ps.append([((x * c - y * sn) * Rf, (x * sn + y * c) * Rf) for x, y in poly])
    return ps


SPOKE = dict(rhoF=0.47, wS=0.20, wA0=0.13, wA1=0.19, a0=40.0, k1=0.26, k2=0.22, rho_end=1.02,
             top_frac=0.80, depth_k=1.0, pad_off=3.2)


def _mat_brushed():
    return _bevel_mat('wheel_brushed', 0.0012, base_color='#B9BDC2', metallic=0.85, roughness=0.32,
                      anisotropic=0.4, coat=0.3, coat_roughness=0.1)


def build_rim(name, key, quality, coll):
    """Barrel + spoke face for the LEFT-side wheel (local frame, not yet baked).
    Returns (barrel, face, cap_parts, bolts)."""
    P = axle_params(key)
    final = quality == 'final'
    Rr, J2, ft, fh, Rf = P['Rr'], P['J2'], P['fl_t'], P['fl_h'], P['Rf']
    th = 0.0055
    # ---------------- barrel (closed profile, (r, a) for revolve)
    a_in = -J2
    well0, well1 = -J2 + 0.040, -J2 + 0.115
    wd = 0.016
    outer = [  # tyre side surface, inboard -> outboard
        (Rr - 0.004, a_in - ft),
        (Rr + fh - 0.004, a_in - ft),
        (Rr + fh, a_in - ft + 0.003),
        (Rr + fh - 0.0005, a_in - 0.0012),
        (Rr + fh - 0.0050, a_in),
        (Rr + 0.0010, a_in + 0.0010),
        (Rr, a_in + 0.018),
        (Rr + 0.0025, a_in + 0.022),
        (Rr - 0.0005, a_in + 0.027),
        (Rr - wd + 0.002, well0),
        (Rr - wd, well0 + 0.006),
        (Rr - wd, well1 - 0.006),
        (Rr - wd + 0.002, well1),
        (Rr - 0.0005, J2 - 0.030),
        (Rr + 0.0025, J2 - 0.024),
        (Rr, J2 - 0.019),
        (Rr + 0.0010, J2 - 0.0010),
        (Rr + fh - 0.0050, J2),
        (Rr + fh - 0.0005, J2 + 0.0012),
        (Rr + fh, J2 + ft - 0.003),
        (Rr + fh - 0.004, J2 + ft),
        # outer lip face (diamond cut) running down to the spoke face
        (Rr + 0.004, J2 + ft),
        (Rr - 0.004, J2 + ft - 0.0015),
        (Rf + 0.006, J2 + ft - 0.0025),
        (Rf + 0.003, J2 + 0.004),
        (Rf + 0.002, P['a_rim'] - 0.004),
    ]
    inner = [  # inside surface, outboard -> inboard
        (Rr - th - 0.002, P['a_rim'] - 0.020),
        (Rr - th, J2 - 0.035),
        (Rr - wd - th + 0.002, well1 + 0.004),
        (Rr - wd - th, well1 - 0.004),
        (Rr - wd - th, well0 + 0.004),
        (Rr - wd - th + 0.002, well0 - 0.004),
        (Rr - th, a_in + 0.025),
        (Rr - th + 0.001, a_in - ft + 0.003),
    ]
    prof = outer + inner + [outer[0]]
    nseg = 160 if final else 64
    barrel = geo.revolve(name + '_Barrel', prof, segments=nseg, axis='X', coll=coll, sharp_angle=50.0)
    geo.merge_by_distance(barrel, 1e-6)
    geo.recalc_normals(barrel)
    mats.assign(barrel, _mat_dark())
    mats.assign_faces(barrel, _mat_bright(), lambda c, p: c.x > J2 + 0.0005 and p.normal.x > 0.25
                      and math.hypot(c.y, c.z) > Rf + 0.004)

    # ---------------- skeletal Y spokes: compact hub + swept stems/arms (no boolean)
    hub_rhos = [0.0, 0.10, 0.20, 0.30, 0.33]
    front = [(r_ * Rf, face_a(P, r_) - 0.0008) for r_ in hub_rhos]
    back = [(r_ * Rf, face_a(P, r_) - 0.0008 - 0.030) for r_ in reversed(hub_rhos)]
    hub = geo.revolve(name + '_Hub', front + back, segments=nseg, axis='X', coll=coll, sharp_angle=40.0)
    geo.merge_by_distance(hub, 1e-6)
    geo.recalc_normals(hub)
    parts = [hub]
    D = SPOKE
    F_r = D['rhoF']

    def bez(p0, p1, p2, p3, n=22):
        t = np.linspace(0, 1, n)[:, None]
        return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3

    def sweep(nm, path, wfun):
        verts, faces = [], []
        N = len(path)
        tang = np.gradient(path, axis=0)
        tang /= np.linalg.norm(tang, axis=1)[:, None]
        for i in range(N):
            c = path[i] * Rf
            nh = np.array([-tang[i][1], tang[i][0]])
            rho = float(np.linalg.norm(path[i]))
            af = face_a(P, rho)
            d = spoke_depth(P, rho) * D['depth_k']
            wb = 0.5 * wfun(i / (N - 1.0)) * Rf
            wt = D['top_frac'] * wb
            for n_, a_ in ((-wb, af - d), (-wb, af - 0.55 * d), (-wt, af), (wt, af), (wb, af - 0.55 * d), (wb, af - d)):
                verts.append((a_, c[0] + n_ * nh[0], c[1] + n_ * nh[1]))
        for i in range(N - 1):
            for j in range(6):
                j1 = (j + 1) % 6
                faces.append((i * 6 + j, i * 6 + j1, (i + 1) * 6 + j1, (i + 1) * 6 + j))
        faces.append(tuple(range(6)))
        faces.append(tuple(range((N - 1) * 6, N * 6)))
        ob = geo.new_object(nm, verts, faces, coll=coll, sharp_angle=40.0)
        geo.recalc_normals(ob)
        return ob

    for k in range(5):
        sa = 90.0 + 72.0 * k
        F = np.array(polar(F_r, sa))
        stem = np.linspace(np.array(polar(0.20, sa)), F, 14)
        parts.append(sweep('%s_Stem%d' % (name, k), stem, lambda u: D['wS']))
        for sg in (-1.0, 1.0):
            Pend = np.array(polar(D['rho_end'], sa + sg * (36.0 - D['pad_off'])))
            P1 = F + D['k1'] * np.array(polar(1.0, sa + sg * D['a0']))
            P2 = Pend - D['k2'] * np.array(polar(1.0, sa + sg * (36.0 - D['pad_off'])))
            arm = bez(F, P1, P2, Pend, 30 if final else 20)
            parts.append(sweep('%s_Arm%d%d' % (name, k, int(sg)), arm,
                               lambda u: D['wA0'] + (D['wA1'] - D['wA0']) * u))
    face = geo.join(parts, name + '_Spokes')
    geo.recalc_normals(face)
    geo.shade(face, True, 38.0)
    mats.assign(face, _mat_dark())
    mats.assign_faces(face, _mat_brushed(), lambda c, p: p.normal.x > 0.85 and math.hypot(c.y, c.z) > 0.335 * Rf)
    if final:
        geo.mod_bevel(face, 0.0012, 1, 35.0, harden=False)
        geo.apply_modifiers(face)

    # ---------------- bolts (on the hub, between the stems)
    bolt_r = 0.265 * Rf
    bolt_phis = [126.0 + 72.0 * k for k in range(5)]
    bolts = []
    for k, ph in enumerate(bolt_phis):
        y, z = polar(bolt_r, ph)
        a0 = face_a(P, 0.265) - 0.0016
        rb = 0.0075
        prof_b = [(0.0, a0), (rb, a0), (rb, a0 + 0.0055), (0.9 * rb, a0 + 0.0070), (0.5 * rb, a0 + 0.0070),
                  (0.5 * rb, a0 + 0.0052), (0.0, a0 + 0.0052)]
        b = geo.revolve('%s_Bolt%d' % (name, k), prof_b, segments=24, axis='X', origin=(0, y, z), coll=coll,
                        sharp_angle=40.0)
        geo.merge_by_distance(b, 1e-6)
        bolts.append(b)
    bolt_obj = geo.join(bolts, name + '_Bolts')
    geo.recalc_normals(bolt_obj)
    mats.assign(bolt_obj, 'titanium')

    # ---------------- centre cap with raised EB oval
    cap = build_cap(name + '_Cap', P, coll)
    return barrel, face, cap, bolt_obj


def build_cap(name, P, coll):
    k = 0.19 * P['Rf'] / 0.037
    a0 = P['a_hub'] - 0.010
    prof = [(0.0, a0 + 0.0135), (k * 0.026, a0 + 0.0131), (k * 0.033, a0 + 0.0120), (k * 0.0365, a0 + 0.0102),
            (k * 0.0370, a0), (0.0, a0)]
    cap = geo.revolve(name, prof, segments=64, axis='X', coll=coll, sharp_angle=35.0)
    geo.merge_by_distance(cap, 1e-6)
    geo.recalc_normals(cap)
    mats.assign(cap, _mat_dark())
    # oval badge ring
    top = a0 + 0.0135
    ell = [(k * 0.0235 * math.cos(t), k * 0.0160 * math.sin(t)) for t in np.linspace(0, TAU, 64, endpoint=False)]
    ell_in = [(k * 0.0205 * math.cos(t), k * 0.0131 * math.sin(t)) for t in np.linspace(0, TAU, 64, endpoint=False)]
    ring = _ring_prism(name + '_Oval', ell, ell_in, top - 0.001, top + 0.0012, coll)
    plate = prism_between(name + '_OvalPlate', ell_in, ell_in, top + 0.0004, top - 0.001, coll)
    mats.assign(ring, _mat_bright())
    mats.assign(plate, mats.custom('wheel_badge_enamel', base_color='#0B0C0E', roughness=0.12, coat=1.0))
    # EB letters: a mirrored E back to back with a B
    letters = []
    e = geo.text_mesh(name + '_E', 'E', size=0.019 * k, extrude=0.0006, coll=coll)
    b = geo.text_mesh(name + '_B', 'B', size=0.019 * k, extrude=0.0006, coll=coll)
    for ob, sx, dx in ((e, -1.0, -0.0058 * k), (b, 1.0, 0.0058 * k)):
        me = ob.data
        xs = [v.co.x for v in me.vertices]
        cx = 0.5 * (min(xs) + max(xs))
        for v in me.vertices:
            u = (v.co.x - cx) * sx + dx
            # text plane (u right, v up) -> wheel face seen from outside: y = u, z = v, a = w
            v.co = Vector((top + 0.0010 + v.co.z, u, v.co.y))
        if sx < 0:
            me.flip_normals()
        me.update()
        letters.append(ob)
    eb = geo.join(letters, name + '_EB')
    # text was laid out with u -> +y; seen from +X the viewer's right is +Y: correct
    _fix_text_orientation(eb)
    mats.assign(eb, _mat_bright())
    return geo.join([cap, ring, plate, eb], name)


def _fix_text_orientation(ob):
    """Text mesh in (u, v, w) mapped to (a=w, y=u, z=v): (y, z, a) is right handed, but the
    mapping (u,v,w)->(w,u,v) is a cyclic permutation, so orientation is preserved."""
    return ob


def _ring_prism(name, outer, inner, a0, a1, coll):
    n = len(outer)
    verts = [(a1, x, y) for x, y in outer] + [(a1, x, y) for x, y in inner] + \
            [(a0, x, y) for x, y in outer] + [(a0, x, y) for x, y in inner]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])                  # top
        faces.append([2 * n + i, 2 * n + j, j, i])          # outer wall
        faces.append([n + i, n + j, 3 * n + j, 3 * n + i])  # inner wall
    ob = geo.new_object(name, verts, faces, coll=coll, smooth=True, sharp_angle=40.0)
    geo.recalc_normals(ob)
    return ob


# =====================================================================
# BRAKES
# =====================================================================
def build_disc(name, key, quality, coll):
    """Vented, cross-drilled carbon-ceramic disc + aluminium bell (local frame)."""
    P = axle_params(key)
    final = quality == 'final'
    ro, ri, t, xd = P['disc_ro'], P['disc_ri'], P['disc_t'], P['x_d']
    ring_t = 0.30 * t
    nseg = 144 if final else 64
    rings = []
    for sgn in (1, -1):
        a_out = xd + sgn * t / 2
        a_in = xd + sgn * (t / 2 - ring_t)
        lo, hi = min(a_out, a_in), max(a_out, a_in)
        prof = [(ri, lo), (ro - 0.0012, lo), (ro, lo + 0.0012), (ro, hi - 0.0012), (ro - 0.0012, hi), (ri, hi), (ri, lo)]
        rg = geo.revolve('%s_ring%d' % (name, sgn), prof, segments=nseg, axis='X', coll=coll, sharp_angle=40.0)
        geo.merge_by_distance(rg, 1e-6)
        geo.recalc_normals(rg)
        rings.append(rg)
    disc = geo.join(rings, name + '_Disc')
    # cross-drilled holes, spiral groups placed between the vanes
    groups = 24 if final else 12
    nvanes = groups * 2
    curve = 22.0      # deg of vane sweep from ri to ro
    cutters = []
    hole_r = 0.0046
    for g in range(groups):
        base = 360.0 * g / groups + 360.0 / nvanes * 0.5
        for j, f in enumerate((0.20, 0.42, 0.64, 0.86) if final else (0.25, 0.55, 0.85)):
            r = ri + f * (ro - ri)
            ph = base + curve * f
            y, z = polar(r, ph)
            cutters.append(geo.cylinder('%s_h%d_%d' % (name, g, j), hole_r, t + 0.01, 'X', (xd, y, z),
                                        segments=12 if final else 8, coll=coll))
    cut = geo.join(cutters, name + '_holes')
    geo.boolean(disc, cut, 'DIFFERENCE', solver='EXACT')
    geo.shade(disc, True, 40.0)
    # vanes
    vane_pts = []
    for i in range(7):
        f = i / 6.0
        r = ri + 0.004 + f * (ro - ri - 0.006)
        vane_pts.append((r, curve * (r - ri) / (ro - ri)))
    gap = t - 2 * ring_t
    vane = _vane(name + '_Vane', vane_pts, 0.0028, xd - gap / 2 - 0.0005, xd + gap / 2 + 0.0005, coll)
    geo.radial_copies(vane, nvanes, axis='X', pivot=(0, 0, 0))
    disc = geo.join([disc, vane], name + '_Disc')
    mats.assign(disc, mats.custom('wheel_disc_satin', base_color='#5A5D63', metallic=0.75, roughness=0.32))
    # bell / hat (aluminium) from the hub mount face to the disc inner edge
    am = P['a_mount']
    bell_prof = [
        (0.0, am + 0.002), (0.064, am + 0.002), (0.072, am - 0.002), (0.080, am - 0.010),
        (ri - 0.004, xd + t / 2 + 0.004), (ri + 0.010, xd + t / 2 + 0.002), (ri + 0.010, xd + t / 2 - 0.004),
        (ri - 0.006, xd + t / 2 - 0.004), (0.074, am - 0.014), (0.064, am - 0.006), (0.0, am - 0.006),
    ]
    bell = geo.revolve(name + '_Bell', bell_prof, segments=nseg, axis='X', coll=coll, sharp_angle=35.0)
    geo.merge_by_distance(bell, 1e-6)
    geo.recalc_normals(bell)
    geo.mod_bevel(bell, 0.001, 1, 40.0)
    mats.assign(bell, mats.custom('wheel_bell_anodised', base_color='#2B2E33', metallic=1.0, roughness=0.3))
    # bobbins connecting bell and disc
    bobs = []
    nb = 12
    for k in range(nb):
        y, z = polar(ri + 0.004, 360.0 * k / nb + 7.5)
        bobs.append(geo.cylinder('%s_bob%d' % (name, k), 0.0055, 0.010, 'X', (xd + t / 2 + 0.002, y, z),
                                 segments=16, coll=coll))
    bob = geo.join(bobs, name + '_Bobbins')
    mats.assign(bob, 'steel_dark')
    return disc, bell, bob


def _vane(name, pts, thick, a0, a1, coll):
    """Curved vane between the friction rings: pts = [(r, phi_deg)]."""
    left, right = [], []
    for i, (r, ph) in enumerate(pts):
        j = min(i + 1, len(pts) - 1)
        k = max(i - 1, 0)
        p0 = np.array(polar(pts[k][0], pts[k][1]))
        p1 = np.array(polar(pts[j][0], pts[j][1]))
        tng = (p1 - p0) / np.linalg.norm(p1 - p0)
        n = np.array([-tng[1], tng[0]])
        c = np.array(polar(r, ph))
        left.append(c + n * thick / 2)
        right.append(c - n * thick / 2)
    outline = left + right[::-1]
    return prism_between(name, outline, outline, a1, a0, coll)


def caliper_outline(P, grow=0.0):
    """Kidney shaped side outline of the caliper (y, z)."""
    ro = P['disc_ro'] + 0.016 + grow
    ri = P['disc_ri'] - 0.004 - grow
    span = P['cal_span']
    ph0 = P['cal_phi']
    rm, hr = 0.5 * (ro + ri), 0.5 * (ro - ri)
    pts = []
    n_arc = 28
    for i in range(n_arc + 1):
        pts.append(polar(ro, ph0 - span + 2 * span * i / n_arc))
    # end cap (rounded) at +span
    c = np.array(polar(rm, ph0 + span))
    ang = math.radians(ph0 + span)
    for i in range(1, 12):
        t = ang + math.pi * i / 12
        pts.append((c[0] + hr * math.cos(t), c[1] + hr * math.sin(t)))
    span_i = span * 0.80
    for i in range(n_arc + 1):
        pts.append(polar(ri, ph0 + span_i - 2 * span_i * i / n_arc))
    c = np.array(polar(rm, ph0 - span))
    ang = math.radians(ph0 - span) + math.pi
    for i in range(1, 12):
        t = ang + math.pi * i / 12
        pts.append((c[0] + hr * math.cos(t), c[1] + hr * math.sin(t)))
    return pts


def build_caliper(name, key, quality, coll):
    """Monoblock caliper straddling the disc + pads (local frame, left side)."""
    P = axle_params(key)
    xd, t, w = P['x_d'], P['disc_t'], P['cal_w']
    outline = caliper_outline(P)
    body = prism_between(name, outline, outline, xd + w, xd - w, coll)
    # slot for the disc
    gap = t / 2 + 0.0035
    prof = [(0.0, xd - gap), (P['disc_ro'] + 0.0045, xd - gap), (P['disc_ro'] + 0.0045, xd + gap), (0.0, xd + gap)]
    slot = geo.revolve(name + '_slot', prof + [prof[0]], segments=96, axis='X', coll=coll)
    geo.merge_by_distance(slot, 1e-6)
    geo.recalc_normals(slot)
    geo.boolean(body, slot, 'DIFFERENCE', solver='EXACT')
    m = geo.mod_bevel(body, width=0.0045, segments=3, angle=30.0)
    m.harden_normals = False
    geo.apply_modifiers(body)
    geo.shade(body, True, 50.0)
    mats.assign(body, mats.custom('wheel_caliper_black', base_color='#08090A', metallic=0.1, roughness=0.25,
                                  coat=1.0, coat_roughness=0.03))
    # pads (backing plate + friction material) on both sides of the disc
    pads = []
    pout = caliper_outline(dict(P, cal_span=P['cal_span'] * 0.78), grow=-0.008)
    for sgn in (1, -1):
        a0 = xd + sgn * (t / 2 + 0.0004)
        a1 = xd + sgn * (t / 2 + 0.0105)
        a2 = xd + sgn * (t / 2 + 0.0145)
        fr = prism_between('%s_padf%d' % (name, sgn), pout, pout, a1, a0, coll)
        bp = prism_between('%s_padb%d' % (name, sgn), pout, pout, a2, a1, coll)
        mats.assign(fr, mats.custom('wheel_pad_friction', base_color='#141414', roughness=0.85))
        mats.assign(bp, 'steel_dark')
        pads += [fr, bp]
    pad = geo.join(pads, name + '_Pads')
    return body, pad


def build_caliper_text(name, key, side, coll):
    """Raised BUGATTI on the outboard face of the caliper, readable from outside on both sides."""
    P = axle_params(key)
    rm = 0.5 * (P['disc_ro'] + 0.016 + P['disc_ri'] - 0.004)
    a_face = P['x_d'] + P['cal_w']
    ob = geo.text_mesh(name, 'BUGATTI', size=0.0215, extrude=0.0006, coll=coll, spacing=1.12)
    _subdivide_long_edges(ob, 0.006)
    me = ob.data
    ys = [v.co.y for v in me.vertices]
    vmid = 0.5 * (min(ys) + max(ys))
    phi0 = P['cal_phi']
    # front caliper at the rear (phi ~ 0): letters upright pointing outwards, reading
    # clockwise; rear caliper at the front (phi ~ 180): same rule
    for v in me.vertices:
        u = v.co.x
        rr = rm + (v.co.y - vmid)
        phi = math.radians(phi0) - side * u / rm
        v.co = Vector((a_face + v.co.z + 0.0002, rr * math.cos(phi), rr * math.sin(phi)))
    if side < 0:
        me.flip_normals()
    me.update()
    mats.assign(ob, mats.custom('wheel_caliper_letter', base_color='#E8E8E8', roughness=0.3, coat=1.0))
    return ob


def build_carrier(name, key, quality, coll):
    """Dark hub carrier / upright, bearing housing and dust shield behind the disc."""
    P = axle_params(key)
    xd, t, w = P['x_d'], P['disc_t'], P['cal_w']
    a_sh = xd - w - 0.010
    rmax = P['Rr'] - 0.016 - 0.0055 - 0.006
    prof = [(0.0, a_sh - 0.012), (rmax, a_sh - 0.004), (rmax, a_sh), (0.0, a_sh + 0.002)]
    shield = geo.revolve(name + '_Shield', prof, segments=96, axis='X', coll=coll, sharp_angle=40.0)
    geo.merge_by_distance(shield, 1e-6)
    geo.recalc_normals(shield)
    hub = geo.cylinder(name + '_Hub', 0.062, (P['a_mount'] - 0.008) - (a_sh - 0.04), 'X',
                       (0.5 * ((P['a_mount'] - 0.008) + (a_sh - 0.04)), 0, 0), segments=48, coll=coll)
    up = geo.box(name + '_Upright', (0.07, 0.13, 0.36), (a_sh - 0.05, 0.0, 0.0), coll)
    geo.mod_bevel(up, 0.012, 3, 40.0)
    geo.apply_modifiers(up)
    carrier = geo.join([shield, hub, up], name)
    mats.assign(carrier, mats.custom('wheel_carrier', base_color='#0D0E10', metallic=0.4, roughness=0.55))
    return carrier


# =====================================================================
# materials
# =====================================================================
def _bevel_mat(name, radius, **kw):
    """Principled material whose shading normal is rounded by a Bevel node (render-time
    edge rounding: crisp highlights on machined edges without extra geometry)."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = mats.custom(name, **kw)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bev = nt.nodes.new('ShaderNodeBevel')
    bev.samples = 6
    bev.inputs['Radius'].default_value = radius
    bev.location = (0, -300)
    nt.links.new(bev.outputs['Normal'], b.inputs['Normal'])
    nt.links.new(bev.outputs['Normal'], b.inputs['Coat Normal'])
    return m


def _mat_bright():
    return _bevel_mat('wheel_diamond_cut', 0.0016, base_color='#D9DCDF', metallic=1.0, roughness=0.12,
                      anisotropic=0.3, coat=0.5, coat_roughness=0.05)


def _mat_dark():
    return _bevel_mat('wheel_paint_dark', 0.0016, base_color='#1C1E21', metallic=0.55, roughness=0.32,
                      coat=1.0, coat_roughness=0.04)
