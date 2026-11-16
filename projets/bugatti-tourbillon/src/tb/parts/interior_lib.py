"""Helpers for the interior module (local frames, lathes, dials, knobs, small parts).

Everything here builds meshes in a LOCAL frame (usually around the origin with
the part axis along +Z) and then bakes a 4x4 matrix into the mesh data, so
objects stay at identity as the brief requires.
"""
import math
import numpy as np
import bmesh
import bpy
from mathutils import Matrix, Vector

from tb import geo, mats


SEG_SCALE = 1.0   # lathe segment multiplier (set below 1 for preview quality)


# ----------------------------------------------------------------- frames
def frame(origin, a, b, c):
    """4x4 matrix whose columns are the local axes a, b, c and translation origin."""
    a, b, c, o = Vector(a), Vector(b), Vector(c), Vector(origin)
    return Matrix(((a.x, b.x, c.x, o.x), (a.y, b.y, c.y, o.y), (a.z, b.z, c.z, o.z), (0, 0, 0, 1)))


def frame_from_normal(origin, normal, up_hint=(0, 0, 1)):
    """Frame with local +Z = normal, local +Y as close as possible to up_hint."""
    n = Vector(normal).normalized()
    u = Vector(up_hint)
    if abs(n.dot(u.normalized())) > 0.98:
        u = Vector((0, 1, 0))
    x = u.cross(n).normalized()
    y = n.cross(x).normalized()
    return frame(origin, x, y, n)


def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation(Vector((x, y, z)))


def R(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def S(sx, sy=None, sz=None):
    sy = sx if sy is None else sy
    sz = sx if sz is None else sz
    return Matrix.Diagonal(Vector((sx, sy, sz, 1.0)))


def bake(obj, M):
    geo.transform_mesh(obj, M)
    return obj


def mat(obj, name):
    IM.assign(obj, name)
    return obj


# ----------------------------------------------------------------- 2D outlines
def rrect(w, h, r, n=6, cx=0.0, cy=0.0):
    """Counter-clockwise rounded rectangle outline (full width w, height h)."""
    r = min(r, w / 2.0 - 1e-5, h / 2.0 - 1e-5)
    pts = []
    for (qx, qy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                         (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            t = math.radians(a0 + 90.0 * k / n)
            pts.append((cx + qx + r * math.cos(t), cy + qy + r * math.sin(t)))
    return pts


def ellipse(rx, ry, n=48, cx=0.0, cy=0.0):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def convex_hull(pts):
    pts = sorted(set(map(tuple, pts)))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


# ----------------------------------------------------------------- meshes
def lathe(name, profile, seg=48, coll=None, knurl=None, sharp=35.0, closed_profile=False):
    """Revolve a profile [(r, z), ...] around local Z. knurl = (count, depth, z0, z1)
    adds axial ridges (knurled grip) between z0 and z1."""
    prof = list(profile)
    seg = max(12, int(seg * SEG_SCALE))
    if closed_profile:
        prof = prof + [prof[0]]
    rows = []
    for k in range(seg):
        t = 2.0 * math.pi * k / seg
        c, s = math.cos(t), math.sin(t)
        row = []
        for r, z in prof:
            rr = r
            if knurl is not None and knurl[2] - 1e-9 <= z <= knurl[3] + 1e-9 and r > 1e-6:
                rr = r - knurl[1] * (0.5 - 0.5 * math.cos(knurl[0] * t))
            row.append((rr * c, rr * s, z))
        rows.append(row)
    ob = geo.grid_surface(name, rows, close_u=True, coll=coll, sharp_angle=sharp)
    geo.merge_by_distance(ob, 1e-7)
    return ob


def prism(name, outline, z0, z1, coll=None, smooth=False, sharp=30.0):
    """Extrude a 2D outline (local XY) from z0 to z1."""
    ob = geo.extrude_polygon(name, outline, z1 - z0, plane='XY', offset=z0, coll=coll,
                             smooth=smooth, sharp_angle=sharp)
    return ob


def cubes(name, items, coll=None):
    """One mesh made of boxes; items = list of 4x4 matrices applied to the unit cube."""
    verts, faces = [], []
    base = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
            (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
    fq = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for M in items:
        o = len(verts)
        verts.extend([tuple(M @ Vector(p)) for p in base])
        faces.extend([tuple(o + i for i in f) for f in fq])
    return geo.new_object(name, verts, faces, coll=coll, smooth=False)


def annulus(name, r0, r1, z0, z1, seg=64, coll=None, teeth=0, tooth_h=0.0):
    """Flat ring (washer / gear rim) around local Z, optional outer teeth."""
    n = seg if teeth == 0 else teeth * 4
    outer, inner = [], []
    for k in range(n):
        t = 2 * math.pi * k / n
        ro = r1
        if teeth:
            ro = r1 + (tooth_h if (k % 4) in (1, 2) else 0.0)
        outer.append((ro * math.cos(t), ro * math.sin(t)))
        inner.append((r0 * math.cos(t), r0 * math.sin(t)))
    verts = []
    for z in (z0, z1):
        verts += [(x, y, z) for x, y in outer] + [(x, y, z) for x, y in inner]
    faces = []
    for k in range(n):
        j = (k + 1) % n
        o0, i0, o1, i1 = 0, n, 2 * n, 3 * n
        faces.append((o1 + k, o1 + j, i1 + j, i1 + k))       # top
        faces.append((o0 + k, i0 + k, i0 + j, o0 + j))       # bottom
        faces.append((o0 + k, o0 + j, o1 + j, o1 + k))       # outer wall
        faces.append((i0 + k, i1 + k, i1 + j, i0 + j))       # inner wall
    ob = geo.new_object(name, verts, faces, coll=coll, smooth=False)
    geo.recalc_normals(ob)
    return ob


def gear(name, r_hub, r_rim, z0, z1, teeth, coll=None, spokes=4):
    """Watch-style wheel: toothed rim, hub and spokes (local XY plane)."""
    teeth = max(10, int(teeth * (0.5 + 0.5 * SEG_SCALE)))
    w = r_rim - r_hub
    rim = annulus(name, r_rim - 0.18 * r_rim, r_rim, z0, z1, teeth=teeth, tooth_h=0.08 * r_rim, coll=coll)
    hub = annulus(name + '_h', r_hub * 0.35, r_hub, z0, z1, seg=24, coll=coll)
    items = []
    for k in range(spokes):
        a = 360.0 * k / spokes
        L = r_rim - 0.1 * r_rim - r_hub * 0.5
        items.append(R('Z', a) @ T((r_hub * 0.5 + L / 2.0), 0, (z0 + z1) / 2) @ S(L, 0.12 * r_rim, (z1 - z0)))
    sp = cubes(name + '_s', items, coll)
    _ = w
    return geo.join([rim, hub, sp], name)


def disc(name, r, z, seg=48, coll=None):
    verts = [(0, 0, z)] + [(r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z) for k in range(seg)]
    faces = [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)]
    return geo.new_object(name, verts, faces, coll=coll, smooth=False)


def dome(name, r, h, z0=0.0, seg=48, rings=6, coll=None):
    """Thin spherical cap (glass) of radius r, height h, base at z0."""
    prof = []
    for i in range(rings + 1):
        t = i / rings
        rr = r * (1 - t)
        prof.append((max(rr, 0.0), z0 + h * (1 - (rr / r) ** 2)))
    return lathe(name, prof, seg=seg, coll=coll, sharp=80)


def text(name, body, size, extrude, coll=None, align='CENTER', mirror_x=False):
    ob = geo.text_mesh(name, body, size=size, extrude=extrude, align=align, coll=coll)
    if mirror_x:
        geo.transform_mesh(ob, S(-1, 1, 1))
        geo.flip_normals(ob)
    return ob


def eb_logo(name, size, extrude, coll=None):
    """Bugatti 'EB' monogram: a mirrored E back to back with a B (local XY, facing +Z)."""
    e = text(name + '_E', 'E', size, extrude, coll, mirror_x=True)
    b = text(name + '_B', 'B', size, extrude, coll)
    lo_e, hi_e = geo.bounds([e])
    lo_b, hi_b = geo.bounds([b])
    geo.transform_mesh(e, T(-hi_e.x + 0.02 * size, 0, 0))
    geo.transform_mesh(b, T(-lo_b.x - 0.02 * size, 0, 0))
    return geo.join([e, b], name)


def tube(name, pts, r, coll=None, res=3, cyclic=False, spline='NURBS'):
    return geo.curve_tube(name, pts, r, resolution=res, cyclic=cyclic, spline=spline, coll=coll)


def stadium_path(w, h, n=10):
    """Closed stadium (slot) path in local XY, long axis Y."""
    r = w / 2.0
    pts = []
    for k in range(n + 1):
        t = math.pi * k / n
        pts.append((r * math.cos(t), h / 2 - r + r * math.sin(t)))
    for k in range(n + 1):
        t = math.pi + math.pi * k / n
        pts.append((r * math.cos(t), -h / 2 + r + r * math.sin(t)))
    return pts


# ----------------------------------------------------------------- composite parts
def dial(prefix, coll, radius, numerals, ticks=60, major_every=5, needle_deg=-120.0, sweep=(225.0, -45.0),
         detail=True, red_zone=False, window=False, sub=False, label=None):
    """Skeleton watch-style instrument around the local origin, axis +Z (facing the viewer).
    Returns a list of (object, material) already assigned."""
    r = radius
    out = []
    # bezel: polished stepped ring with a knurled (coin-edge) outer band
    bez = lathe(prefix + '_Bezel', [(r * 0.985, -0.003), (r * 0.985, 0.0035), (r * 1.02, 0.0062),
                                     (r * 1.07, 0.0058), (r * 1.10, 0.0035), (r * 1.115, 0.0),
                                     (r * 1.115, -0.006), (r * 0.985, -0.006)], seg=96, coll=coll,
                closed_profile=True, sharp=30)
    out.append(mat(bez, 'aluminum_polished'))
    knr = lathe(prefix + '_Knurl', [(r * 1.115, -0.0055), (r * 1.13, -0.005), (r * 1.13, 0.0005), (r * 1.115, 0.001)],
                seg=192, coll=coll, knurl=(96, r * 0.008, -0.0051, 0.0006), sharp=20)
    out.append(mat(knr, 'titanium'))
    # chapter ring (dark, slightly glossy)
    ch = annulus(prefix + '_Chapter', r * 0.70, r * 0.99, -0.0035, -0.0025, seg=96, coll=coll)
    out.append(mat(ch, mats.custom('Interior_DialFace', base_color='#15181c', metallic=0.4, roughness=0.32)))
    # back plate seen through the skeleton
    bp = disc(prefix + '_Back', r * 0.99, -0.011, seg=64, coll=coll)
    out.append(mat(bp, 'steel_dark'))
    # ticks
    a0, a1 = sweep
    items = []
    for k in range(ticks + 1):
        a = math.radians(a0 + (a1 - a0) * k / ticks)
        major = (k % major_every == 0)
        L = r * (0.14 if major else 0.07)
        wdt = r * (0.022 if major else 0.012)
        rc = r * 0.95 - L / 2
        items.append(T(rc * math.cos(a), rc * math.sin(a), -0.0021) @ R('Z', math.degrees(a)) @ S(L, wdt, 0.0008))
    tk = cubes(prefix + '_Ticks', items, coll)
    out.append(mat(tk, 'emit_cluster'))
    if red_zone:
        items = []
        for k in range(10):
            a = math.radians(a1 + 25.0 * (k / 10.0) - 25.0)
            rc = r * 0.92
            items.append(T(rc * math.cos(a), rc * math.sin(a), -0.0022) @ R('Z', math.degrees(a)) @ S(r * 0.05, r * 0.06, 0.0006))
        rz = cubes(prefix + '_Red', items, coll)
        out.append(mat(rz, mats.custom('Interior_DialRed', base_color='#b0141a', roughness=0.35)))
    # numerals
    nums = []
    n = len(numerals)
    for k, label in enumerate(numerals):
        a = math.radians(a0 + (a1 - a0) * k / max(n - 1, 1))
        rc = r * 0.62
        t = text(prefix + '_N%d' % k, label, r * 0.12, 0.0003, coll)
        geo.transform_mesh(t, T(rc * math.cos(a), rc * math.sin(a), -0.0024))
        nums.append(t)
    if nums:
        nm = geo.join(nums, prefix + '_Numerals')
        out.append(mat(nm, 'emit_cluster'))
    # skeleton movement: wheels, bridges and jewels
    if detail:
        g1 = gear(prefix + '_Gear1', r * 0.08, r * 0.30, -0.0095, -0.0082, 36, coll)
        geo.transform_mesh(g1, T(-r * 0.20, -r * 0.12, 0))
        out.append(mat(g1, 'gold'))
        g2 = gear(prefix + '_Gear2', r * 0.06, r * 0.20, -0.0080, -0.0068, 28, coll, spokes=5)
        geo.transform_mesh(g2, T(r * 0.24, -r * 0.18, 0))
        out.append(mat(g2, 'titanium'))
        g3 = gear(prefix + '_Gear3', r * 0.05, r * 0.16, -0.0066, -0.0056, 24, coll, spokes=3)
        geo.transform_mesh(g3, T(r * 0.05, r * 0.30, 0))
        out.append(mat(g3, 'gold'))
        # balance wheel (tourbillon cage) with its spiral
        bal = annulus(prefix + '_Balance', r * 0.15, r * 0.18, -0.0062, -0.0050, seg=48, coll=coll)
        geo.transform_mesh(bal, T(-r * 0.22, r * 0.25, 0))
        out.append(mat(bal, 'aluminum_polished'))
        spiral = []
        for k in range(60):
            t = k / 59.0
            ang = t * 6 * math.pi
            rr = r * (0.02 + 0.11 * t)
            spiral.append((-r * 0.22 + rr * math.cos(ang), r * 0.25 + rr * math.sin(ang), -0.0057))
        sp = tube(prefix + '_Spiral', spiral, 0.00025, coll, res=1, spline='POLY')
        out.append(mat(sp, 'gold'))
        items = [T(0, -r * 0.05, -0.0048) @ R('Z', 25) @ S(r * 0.75, r * 0.07, 0.0012),
                 T(r * 0.05, r * 0.10, -0.0046) @ R('Z', -50) @ S(r * 0.6, r * 0.06, 0.0012)]
        br = cubes(prefix + '_Bridges', items, coll)
        geo.mod_bevel(br, 0.0004, 1, 30)
        out.append(mat(br, 'aluminum_brushed'))
        jw = []
        for (x, y) in ((-r * 0.20, -r * 0.12), (r * 0.24, -r * 0.18), (r * 0.05, r * 0.30), (-r * 0.22, r * 0.25),
                       (r * 0.45, r * 0.0)):
            j = geo.uv_sphere(prefix + '_J', r * 0.035, (x, y, -0.0040), segments=12, rings=6, coll=coll)
            jw.append(j)
        jj = geo.join(jw, prefix + '_Jewels')
        out.append(mat(jj, mats.custom('Interior_Jewel', base_color='#a0001a', roughness=0.05,
                                       transmission=0.6, ior=1.76, coat=1.0)))
    # needle
    na = math.radians(needle_deg)
    L = r * 0.88
    nd = cubes(prefix + '_Needle', [R('Z', needle_deg) @ T(L * 0.42, 0, -0.0006) @ S(L * 0.95, r * 0.035, 0.0006)], coll)
    out.append(mat(nd, 'aluminum_polished'))
    tip = cubes(prefix + '_NeedleTip', [R('Z', needle_deg) @ T(L * 0.80, 0, -0.0002) @ S(L * 0.28, r * 0.03, 0.0005)], coll)
    out.append(mat(tip, 'emit_cluster'))
    cap = lathe(prefix + '_Cap', [(0, 0.0012), (r * 0.06, 0.0010), (r * 0.07, 0.0), (r * 0.07, -0.001)], seg=24, coll=coll)
    out.append(mat(cap, 'aluminum_polished'))
    _ = na
    if window:
        wn = prism(prefix + '_Win', rrect(r * 0.62, r * 0.20, r * 0.04, 3), -0.0031, -0.0026, coll)
        geo.transform_mesh(wn, T(0, -r * 0.50, 0))
        out.append(mat(wn, 'plastic_black'))
        tx = text(prefix + '_WinTxt', '000', r * 0.13, 0.0003, coll)
        geo.transform_mesh(tx, T(0, -r * 0.50, -0.0024))
        out.append(mat(tx, 'emit_cluster'))
    if sub:
        rs = r * 0.30
        for q, ang in enumerate((90.0, 210.0, 330.0)):
            cx, cy = r * 0.42 * math.cos(math.radians(ang)), r * 0.42 * math.sin(math.radians(ang))
            ring = annulus(prefix + '_SubR%d' % q, rs * 0.86, rs, -0.0032, -0.0019, seg=40, coll=coll)
            geo.transform_mesh(ring, T(cx, cy, 0))
            out.append(mat(ring, 'aluminum_polished'))
            dk = disc(prefix + '_SubD%d' % q, rs * 0.86, -0.0030, seg=32, coll=coll)
            geo.transform_mesh(dk, T(cx, cy, 0))
            out.append(mat(dk, 'plastic_black'))
            hd = cubes(prefix + '_SubH%d' % q, [T(cx, cy, -0.0026) @ R('Z', 40 + 70 * q) @ T(rs * 0.35, 0, 0) @ S(rs * 0.75, rs * 0.07, 0.0004)], coll)
            out.append(mat(hd, 'emit_cluster'))
    if label:
        lb = text(prefix + '_Label', label, r * 0.095, 0.0003, coll)
        geo.transform_mesh(lb, T(0, -r * 0.38, -0.0024))
        out.append(mat(lb, 'emit_cluster'))
    # sapphire glass dome
    gl = dome(prefix + '_Glass', r * 0.99, r * 0.10, z0=0.0045, seg=64, coll=coll)
    out.append(mat(gl, 'glass_clear'))
    return [o for o in out]


def knob(prefix, coll, r, h, crystal=True, knurl_n=40):
    """Crystal rotary knob along local +Z, base at z = 0: polished base ring, crystal body
    with an aluminium core, knurled aluminium cap."""
    out = []
    base = lathe(prefix + '_Base', [(r * 1.25, 0.0), (r * 1.25, 0.002), (r * 1.1, 0.004), (r * 1.02, 0.004),
                                    (r * 1.02, 0.0)], seg=48, coll=coll, closed_profile=True)
    out.append(mat(base, 'aluminum_polished'))
    if crystal:
        body = lathe(prefix + '_Crystal', [(0, 0.004), (r * 0.98, 0.004), (r * 1.0, 0.006), (r, h * 0.72),
                                           (r * 0.98, h * 0.74), (0, h * 0.74)], seg=48, coll=coll, sharp=40)
        out.append(mat(body, 'crystal'))
        core = lathe(prefix + '_Core', [(0, 0.004), (r * 0.30, 0.004), (r * 0.30, h * 0.30), (r * 0.18, h * 0.40),
                                        (r * 0.18, h * 0.73), (0, h * 0.73)], seg=24, coll=coll)
        out.append(mat(core, 'aluminum_polished'))
        z0 = h * 0.74
    else:
        z0 = 0.004
    cap = lathe(prefix + '_Cap', [(0, z0), (r * 1.02, z0), (r * 1.04, z0 + 0.002), (r * 1.04, h - 0.002),
                                  (r * 1.0, h), (r * 0.55, h + 0.0005), (0, h + 0.0005)],
                seg=max(96, knurl_n * 4), coll=coll, knurl=(knurl_n, r * 0.05, z0 + 0.002, h - 0.002), sharp=25)
    out.append(mat(cap, 'aluminum_polished'))
    mk = cubes(prefix + '_Mark', [T(r * 0.6, 0, h + 0.0006) @ S(r * 0.5, r * 0.08, 0.0006)], coll)
    out.append(mat(mk, 'emit_cluster'))
    return out


def toggle(prefix, coll, size=0.012, tilt=18.0):
    """Aircraft-style toggle switch along local +Z: polished guard, lever with a ball end."""
    out = []
    s = size
    base = prism(prefix + '_Base', rrect(s * 1.6, s * 2.4, s * 0.4), 0.0, s * 0.35, coll)
    geo.mod_bevel(base, s * 0.08, 2, 30)
    out.append(mat(base, 'aluminum_polished'))
    boss = lathe(prefix + '_Boss', [(0, s * 0.35), (s * 0.35, s * 0.35), (s * 0.30, s * 0.75), (0, s * 0.75)], seg=20, coll=coll)
    out.append(mat(boss, 'aluminum_brushed'))
    lev = lathe(prefix + '_Lever', [(0, 0), (s * 0.12, 0), (s * 0.08, s * 1.3), (0, s * 1.3)], seg=12, coll=coll)
    ball = geo.uv_sphere(prefix + '_Ball', s * 0.16, (0, 0, s * 1.35), segments=12, rings=8, coll=coll)
    lv = geo.join([lev, ball], prefix + '_Lever')
    geo.transform_mesh(lv, T(0, 0, s * 0.6) @ R('X', tilt))
    out.append(mat(lv, 'chrome'))
    return out


def vent(prefix, coll, w, h, depth=0.02):
    """Slim vertical air vent along local -Z (into the panel): polished lip, dark duct, one vane."""
    out = []
    path = stadium_path(w, h, 10)
    p3 = [(x, y, 0.0) for x, y in path]
    lip = geo.sweep(prefix + '_Lip', p3, [(0.0018 * math.cos(2 * math.pi * k / 10), 0.0018 * math.sin(2 * math.pi * k / 10))
                                          for k in range(10)], closed_path=True, up=(0, 0, 1), coll=coll)
    out.append(mat(lip, 'aluminum_polished'))
    # duct walls going back into the panel, and a dark bottom
    rows = [[(x * 0.98, y * 0.98, 0.0) for x, y in path], [(x * 0.9, y * 0.95, -depth) for x, y in path]]
    duct = geo.grid_surface(prefix + '_Duct', rows, close_v=True, coll=coll)
    geo.fill_holes(duct)
    out.append(mat(duct, 'plastic_black'))
    vane = cubes(prefix + '_Vane', [T(0, 0, -0.006) @ S(0.0025, h * 0.85, 0.012)], coll)
    geo.mod_bevel(vane, 0.0008, 1, 30)
    out.append(mat(vane, 'aluminum_dark'))
    return out


# ----------------------------------------------------------------- own materials (never mutate the shared library)
ALIAS = {'leather_light': 'Interior_LeatherPale', 'leather_dark': 'Interior_LeatherDark',
         'leather_slate': 'Interior_LeatherSlate', 'alcantara': 'Interior_Alcantara', 'carpet': 'Interior_Carpet',
         'fabric_light': 'Interior_Fabric', 'stitch': 'Interior_Stitch', 'dash_top': 'Interior_DashTop', 'emit_cluster': 'Interior_ClusterGlow', 'emit_screen': 'Interior_ScreenGlow', 'emit_interior': 'Interior_Ambient'}


def _bump(m, kind, scale, strength, dist):
    nt = m.node_tree
    b = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    tc = nt.nodes.new('ShaderNodeTexCoord')
    if kind == 'voronoi':
        t = nt.nodes.new('ShaderNodeTexVoronoi')
        t.feature = 'DISTANCE_TO_EDGE'
        t.inputs['Scale'].default_value = scale
        h = t.outputs['Distance']
    else:
        t = nt.nodes.new('ShaderNodeTexNoise')
        t.inputs['Scale'].default_value = scale
        t.inputs['Detail'].default_value = 3.0
        h = t.outputs['Fac']
    nt.links.new(tc.outputs['Object'], t.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = dist
    nt.links.new(h, bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])


def make_materials():
    if bpy.data.materials.get('Interior_LeatherPale') is not None:
        return
    lk = dict(specular=0.4, sheen=0.3, sheen_roughness=0.4)
    for name, col, rough in (('Interior_LeatherPale', '#7690a8', 0.5), ('Interior_LeatherDark', '#26394a', 0.5),
                             ('Interior_LeatherSlate', '#2c3a44', 0.55)):
        _bump(mats.custom(name, base_color=col, roughness=rough, **lk), 'voronoi', 900.0, 0.12, 0.0003)
    _bump(mats.custom('Interior_Alcantara', base_color='#0f1318', roughness=0.95, sheen=0.2, sheen_roughness=0.5), 'noise', 1400.0, 0.25, 0.0004)
    _bump(mats.custom('Interior_Carpet', base_color='#6f8aa3', roughness=0.92, sheen=0.3, sheen_roughness=0.5), 'noise', 500.0, 0.5, 0.0004)
    _bump(mats.custom('Interior_Fabric', base_color='#7e97ab', roughness=0.85, sheen=0.5, sheen_roughness=0.5, specular=0.2), 'noise', 700.0, 0.4, 0.0004)
    dt = mats.custom('Interior_DashTop', base_color='#26394a', roughness=0.5, **lk)
    _bump(dt, 'voronoi', 900.0, 0.12, 0.0003)
    nt = dt.node_tree
    b = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sp = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sp.inputs['Vector'])
    ab = nt.nodes.new('ShaderNodeMath')
    ab.operation = 'ABSOLUTE'
    nt.links.new(sp.outputs['X'], ab.inputs[0])
    mu = nt.nodes.new('ShaderNodeMath')
    mu.operation = 'MULTIPLY'
    mu.inputs[1].default_value = 0.30
    nt.links.new(ab.outputs['Value'], mu.inputs[0])
    ad = nt.nodes.new('ShaderNodeMath')
    ad.operation = 'ADD'
    nt.links.new(sp.outputs['Y'], ad.inputs[0])
    nt.links.new(mu.outputs['Value'], ad.inputs[1])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -1.00
    mr.inputs['From Max'].default_value = -0.94
    nt.links.new(ad.outputs['Value'], mr.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (0.0194, 0.0409, 0.0685, 1.0)
    mx.inputs['B'].default_value = (0.1912, 0.2788, 0.3918, 1.0)
    nt.links.new(mr.outputs['Result'], mx.inputs['Factor'])
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
    mats.custom('Interior_Stitch', base_color='#b8d0e0', roughness=0.6)
    mats.emissive('Interior_Ambient', '#6fe6e0', 16.0, 'interior_lights')
    mats.emissive('Interior_ClusterGlow', '#e4f2ff', 9.0, 'cluster_glow')
    mats.emissive('Interior_ScreenGlow', '#cfe8ff', 14.0, 'screen')


class _IM:
    """Drop-in for tb.mats inside the interior module: maps the shared leather/fabric names to Interior_ materials."""
    def _r(self, name):
        make_materials()
        if isinstance(name, str) and name in ALIAS:
            return bpy.data.materials[ALIAS[name]]
        return name

    def assign(self, obj, name, **kw):
        return mats.assign(obj, self._r(name), **kw)

    def assign_faces(self, obj, name, pred, **kw):
        return mats.assign_faces(obj, self._r(name), pred, **kw)

    def get(self, name):
        r = self._r(name)
        return r if not isinstance(r, str) else mats.get(r)

    def __getattr__(self, n):
        return getattr(mats, n)


IM = _IM()


def knob_glass(prefix, coll, r, h, knurl_n=48):
    """Large knob: polished base, knurled aluminium skirt, glass sleeve over an aluminium core, lit disc on top."""
    out = []
    base = lathe(prefix + '_Base', [(r * 1.3, 0.0), (r * 1.3, 0.003), (r * 1.15, 0.006), (r * 1.0, 0.006), (r, 0.0)],
                 seg=48, coll=coll, closed_profile=True)
    out.append(mat(base, 'aluminum_polished'))
    sk = lathe(prefix + '_Skirt', [(0, 0.006), (r * 1.05, 0.006), (r * 1.05, h * 0.30), (r * 1.0, h * 0.32), (0, h * 0.32)],
               seg=max(96, knurl_n * 3), coll=coll, knurl=(knurl_n, r * 0.07, 0.008, h * 0.30), sharp=25)
    out.append(mat(sk, 'aluminum_polished'))
    gl = lathe(prefix + '_Glass', [(r * 0.97, h * 0.32), (r * 0.97, h * 0.92), (r * 0.88, h * 0.97), (0, h * 0.97)],
               seg=64, coll=coll, sharp=40)
    out.append(mat(gl, 'crystal'))
    core = lathe(prefix + '_Core', [(0, h * 0.32), (r * 0.40, h * 0.32), (r * 0.40, h * 0.86), (0, h * 0.86)], seg=32, coll=coll)
    out.append(mat(core, 'aluminum_polished'))
    ds = lathe(prefix + '_Disc', [(0, h * 0.865), (r * 0.36, h * 0.865), (r * 0.36, h * 0.873), (0, h * 0.873)], seg=32, coll=coll)
    out.append(mat(ds, 'emit_cluster'))
    return out
