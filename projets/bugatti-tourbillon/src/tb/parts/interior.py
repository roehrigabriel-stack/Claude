"""Interior (cabin) of the Bugatti Tourbillon.

Every position is derived from spec.CABIN plus the named constants below, so the
cabin can be re-fitted by changing a few numbers.

Sub-assemblies
  MOD_Interior        tub lining, floor, sills, bulkhead, headliner, A-pillar trims,
                      mirror, pedals, lamps
  MOD_Interior_Seats  both seats, belts, buckles
  MOD_Interior_Dash   dashboard wing, console spine, column, fixed hub, cluster
     HINGE_SteeringWheel  rim + spokes + paddles (driven by 'steer')
     HINGE_Screen         pop-up screen (driven by 'screen')
  HINGE_Door_L / _R   door cards
"""
import math
import numpy as np
from mathutils import Vector, Matrix

from tb import geo, mats, rig, spec
from tb.parts import interior_lib as L
mats = L.IM   # own Interior_ materials; the shared library is never modified
from tb.parts.interior_lib import T, R, S

C = spec.CABIN
ZF = C['z_floor']
YFW = C['y_footwell']
YDR = C['y_dash_rear']
ZDT = C['z_dash_top']
YBH = C['y_bulkhead']
XS = C['x_seat']
HX, HY, HZ = C['h_point']
BACK = math.radians(C['seat_back_angle'])
XT = C['x_tunnel']
ZT = C['z_tunnel']
XSILL = C['x_inner_sill']
ZSILL = C['z_sill']
XBELT = C['x_inner_belt']
ZBELT = C['z_belt']
XROOF = C['x_inner_roof']
ZHEAD = C['z_headliner']
SC = Vector(C['steering_center'])
TILT = math.radians(C['steering_tilt'])
RWHEEL = C['steering_diameter'] / 2.0

# ---- own constants (derived offsets) ----
Y_DASH_FRONT = -1.22                 # dashboard front edge at the A-pillars
Y_DASH_CTR = spec.Y_COWL + 0.03      # dashboard front edge on the centreline (under the cowl)
X_DASH_END = XSILL + 0.025           # dashboard wing ends just inside the door card
Y_HEADER_IN = spec.Y_HEADER - 0.01   # front edge of the headliner
Z_HEAD_REAR = ZHEAD - 0.05           # headliner height at the bulkhead (roof falls)
PLAN_FRONT = 0.86                    # teardrop plan: width factor at the footwell front
PLAN_REAR = 0.84                     # width factor at the bulkhead
SEAT_W = 0.188                       # seat cushion half width (tunnel and sill limit it)
DOOR_X_OUT = XBELT + 0.023            # door card outer face
DOOR_Y0 = spec.DOOR_Y_FRONT + 0.05
DOOR_Y1 = 0.42
SCREEN_HINGE_Y = -0.855         # pop-up screen hinge line (front edge of its lid)
DASH_VALLEY = 0.055
ZSCR = ZDT - DASH_VALLEY            # dash top on the centreline (valley)
SCREEN_LEN = 0.178
SCREEN_HW = 0.066

# steering frame: a = driver's right (-X), b = up in the wheel plane, c = towards the driver
W_A = Vector((-1.0, 0.0, 0.0))
W_B = Vector((0.0, -math.sin(TILT), math.cos(TILT)))
W_C = Vector((0.0, math.cos(TILT), math.sin(TILT)))
MW = L.frame(SC, W_A, W_B, W_C)


def ss(e0, e1, x):
    return geo.smoothstep(e0, e1, x)


def env_x(y, z):
    """Maximum interior half width at (y, z): side wall profile times the teardrop plan factor."""
    if z <= ZSILL:
        xz = XSILL
    elif z <= ZBELT:
        xz = geo.lerp(XSILL, XBELT, (z - ZSILL) / (ZBELT - ZSILL))
    else:
        t = geo.clamp((z - ZBELT) / (ZHEAD - ZBELT))
        xz = XBELT + (XROOF - XBELT) * t ** 1.6
    f = 1.0
    if y < -0.75:
        f = geo.lerp(1.0, PLAN_FRONT, geo.clamp((-0.75 - y) / (0.75 + YFW)))
    elif y > 0.20:
        f = geo.lerp(1.0, PLAN_REAR, ss(0.20, YBH, y))
    return xz * f


class Ctx:
    def __init__(self, ctx):
        self.ctx = ctx
        self.coll = ctx.collection('Interior')
        self.fin = ctx.final()
        self.main, self.seats, self.dash, self.wheel, self.screen = [], [], [], [], []
        self.door_l = []


# =====================================================================
# tub lining
# =====================================================================
def wall_x(y):
    """Inner side wall (sill) half width along the cabin."""
    if y < -0.93:
        return geo.lerp(XSILL, XSILL * PLAN_FRONT + 0.01, ss(-0.93, -1.10, y))
    return geo.lerp(XSILL, XSILL * PLAN_REAR + 0.03, ss(0.25, YBH, y))


def wall_top(y):
    return geo.lerp(ZSILL, 0.575, ss(-0.955, -1.0, y))


def build_tub(K):
    coll = K.coll
    y0, y1 = -1.075, YBH
    ny = 60 if K.fin else 40
    rows = []
    for i in range(ny + 1):
        y = geo.lerp(y0, y1, i / ny)
        xw, zt = wall_x(y), wall_top(y)
        sec = [(xw, 0, zt), (xw, 0, ZF + 0.11), (xw, 0, ZF + 0.05), (xw - 0.012, 0, ZF + 0.012),
               (xw - 0.05, 0, ZF), (xw * 0.5, 0, ZF), (0, 0, ZF)]
        sec = sec + [(-p[0], 0, p[2]) for p in reversed(sec[:-1])]
        rows.append([(p[0], y, p[2]) for p in sec])
    tub = geo.grid_surface('Interior_Tub', rows, coll=coll, sharp_angle=50)
    geo.recalc_normals(tub)
    # make normals point into the cabin (up for the floor)
    me = tub.data
    up = [p for p in me.polygons if abs(p.center.x) < 0.2]
    if up and up[0].normal.z < 0:
        geo.flip_normals(tub)
    mats.assign(tub, 'carpet')
    mats.assign_faces(tub, 'carbon_gloss', lambda c, p: abs(p.normal.x) > 0.6 and c.y > -0.95)
    mats.assign_faces(tub, 'leather_light', lambda c, p: abs(p.normal.x) > 0.6 and c.y <= -0.95)
    K.main.append(tub)

    # toe board between the side walls, up to the dash underside
    prof = [(y0, ZF), (-1.115, 0.27), (-1.165, 0.43), (-1.19, 0.52), (-1.20, 0.585)]
    rows = []
    xw = wall_x(y0)
    for (y, z) in prof:
        rows.append([(geo.lerp(-xw, xw, j / 16.0), y, z) for j in range(17)])
    toe = geo.grid_surface('Interior_ToeBoard', rows, coll=coll, sharp_angle=60)
    if toe.data.polygons[0].normal.y < 0:
        geo.flip_normals(toe)
    mats.assign(toe, 'carpet')
    K.main.append(toe)

    # wide carbon sills with aluminium tread plates (left built, right mirrored)
    sy0, sy1 = spec.DOOR_Y_FRONT + 0.005, spec.DOOR_Y_REAR
    sill = L.prism('Interior_Sill_L', L.rrect(0.16, 0.06, 0.012), -0.03, 0.03, coll)
    geo.transform_mesh(sill, Matrix.Identity(4))
    sill = geo.box('Interior_Sill_L', (0.16, sy1 - sy0, 0.06), (XSILL + 0.08, (sy0 + sy1) / 2, ZSILL - 0.03), coll)
    geo.mod_bevel(sill, 0.01, 3, 30)
    mats.assign(sill, 'carbon_gloss')
    tread = geo.box('Interior_SillTread_L', (0.10, (sy1 - sy0) * 0.78, 0.004),
                    (XSILL + 0.075, (sy0 + sy1) / 2 - 0.02, ZSILL + 0.002), coll)
    geo.mod_bevel(tread, 0.0015, 2, 30)
    mats.assign(tread, 'aluminum_brushed')
    txt = L.text('Interior_SillText_L', 'BUGATTI', 0.032, 0.0006, coll, spacing=1.0) if False else \
        geo.text_mesh('Interior_SillText_L', 'B U G A T T I', size=0.03, extrude=0.0005, coll=coll)
    geo.transform_mesh(txt, T(XSILL + 0.075, (sy0 + sy1) / 2 - 0.02, ZSILL + 0.0045) @ R('Z', 90))
    mats.assign(txt, 'steel_dark')
    for ob in (sill, tread, txt):
        K.main.append(ob)
        K.main.append(geo.mirror_copy(ob, ob.name[:-2] + '_R', coll))

    # rear bulkhead (leather lower, alcantara upper) with an aluminium trim line
    nz, nx = 28, 32
    rows = []
    for i in range(nz + 1):
        z = geo.lerp(ZF, Z_HEAD_REAR - 0.01, i / nz)
        xm = env_x(YBH, z) * 0.995
        rows.append([(geo.lerp(xm, -xm, j / nx), YBH, z) for j in range(nx + 1)])
    bh = geo.grid_surface('Interior_Bulkhead', rows, coll=coll)
    if bh.data.polygons[0].normal.y > 0:
        geo.flip_normals(bh)
    mats.assign(bh, 'leather_dark')
    mats.assign_faces(bh, 'alcantara', lambda c, p: c.z > 0.76)
    K.main.append(bh)
    zt = 0.755
    xm = env_x(YBH, zt) * 0.98
    trim = L.tube('Interior_BulkheadTrim', [(-xm, YBH - 0.006, zt), (0, YBH - 0.006, zt), (xm, YBH - 0.006, zt)],
                  0.004, coll, spline='POLY')
    mats.assign(trim, 'aluminum_polished')
    K.main.append(trim)
    # small leather pad / storage net plate between the seat backs
    pad = geo.box('Interior_BulkheadPad', (0.18, 0.02, 0.30), (0, YBH - 0.012, 0.62), coll)
    geo.mod_bevel(pad, 0.02, 4, 30)
    mats.assign(pad, 'leather_light')
    K.main.append(pad)

    # headliner (alcantara, faces down), following the teardrop plan
    ny, nx = 36, 30
    rows = []
    for i in range(ny + 1):
        y = geo.lerp(Y_HEADER_IN, YBH, i / ny)
        zc = float(geo.Pchip([Y_HEADER_IN, -0.25, 0.10, YBH], [ZHEAD - 0.015, ZHEAD, ZHEAD, Z_HEAD_REAR])(y))
        hw = XROOF * geo.lerp(1.0, PLAN_REAR + 0.04, ss(0.1, YBH, y)) + 0.01
        rows.append([(geo.lerp(-hw, hw, j / nx), y, zc - 0.045 * (geo.lerp(-1, 1, j / nx)) ** 4) for j in range(nx + 1)])
    hl = geo.grid_surface('Interior_Headliner', rows, coll=coll)
    if hl.data.polygons[0].normal.z > 0:
        geo.flip_normals(hl)
    mats.assign(hl, 'alcantara')
    K.main.append(hl)
    hl_z = geo.Pchip([Y_HEADER_IN, -0.25, 0.10, YBH], [ZHEAD - 0.015, ZHEAD, ZHEAD, Z_HEAD_REAR])
    pts = [(0, y, float(hl_z(y)) - 0.004) for y in np.linspace(Y_HEADER_IN + 0.01, YBH - 0.01, 16)]
    sp = geo.sweep('Interior_RoofSpine', pts, L.rrect(0.022, 0.006, 0.0025, 3), up=(0, 0, 1), coll=coll)
    mats.assign(sp, 'aluminum_polished')
    K.main.append(sp)
    # overhead switch pod
    yo = Y_HEADER_IN + 0.10
    zo = float(hl_z(yo))
    pod = geo.box('Interior_RoofPod', (0.07, 0.11, 0.022), (0, yo, zo - 0.013), coll)
    geo.mod_bevel(pod, 0.006, 3, 30)
    mats.assign(pod, 'aluminum_brushed')
    K.main.append(pod)
    for k, dy in enumerate((-0.03, 0.0, 0.03)):
        parts = L.toggle('Interior_RoofToggle%d' % k, coll, size=0.008, tilt=15)
        for ob in parts:
            geo.transform_mesh(ob, T(0, yo + dy, zo - 0.024) @ R('X', 180))
            K.main.append(ob)

    # interior mirror hanging from the header
    ym, zm = Y_HEADER_IN - 0.035, ZHEAD - 0.075
    secs = []
    for t, s in ((-0.016, 0.85), (-0.008, 1.0), (0.008, 1.0), (0.014, 0.9), (0.018, 0.6)):
        secs.append([(x, ym - t, zm + z) for x, z in L.ellipse(0.11 * s, 0.032 * s, 40)])
    mir = geo.grid_surface('Interior_Mirror', secs, close_v=True, coll=coll)
    geo.fill_holes(mir)
    geo.recalc_normals(mir)
    mats.assign(mir, 'leather_dark')
    glass = geo.grid_surface('Interior_MirrorGlass', [[(x, ym + 0.0165, zm + z) for x, z in L.ellipse(0.1, 0.027, 40)],
                                                     [(0, ym + 0.0165, zm)] * 40], close_v=True, coll=coll)
    mats.assign(glass, 'chrome')
    stalk = L.tube('Interior_MirrorStalk', [(0, ym, zm + 0.02), (0, ym + 0.005, zm + 0.05), (0, ym + 0.02, ZHEAD - 0.012)],
                   0.006, coll)
    mats.assign(stalk, 'aluminum_polished')
    K.main += [mir, glass, stalk]

    # A-pillar inner trims
    base = Vector((X_DASH_END - 0.01, Y_DASH_FRONT + 0.09, ZDT - 0.02))
    top = Vector((XROOF + 0.005, Y_HEADER_IN - 0.01, ZHEAD - 0.032))
    path = [tuple(base.lerp(top, t) + Vector((0.012, 0, 0.012)) * math.sin(math.pi * t)) for t in np.linspace(0, 1, 14)]
    prof = [(0.036 * math.cos(math.pi * k / 10), -0.018 * math.sin(math.pi * k / 10)) for k in range(11)]
    ap = geo.sweep('Interior_APillar_L', path, prof, up=(1.0, 0.0, 0.7), coll=coll, cap=True)
    geo.fill_holes(ap)
    mats.assign(ap, 'alcantara')
    K.main.append(ap)
    K.main.append(geo.mirror_copy(ap, 'Interior_APillar_R', coll))

    # tweeters at the base of the A-pillars
    for side in (1, -1):
        g = L.lathe('Interior_Tweeter_%s' % ('L' if side > 0 else 'R'),
                    [(0, 0.004), (0.018, 0.003), (0.024, 0.0), (0.024, -0.004)], seg=32, coll=coll)
        geo.transform_mesh(g, L.frame_from_normal((side * (X_DASH_END - 0.06), Y_DASH_FRONT + 0.12, ZDT - 0.012),
                                                  (-side * 0.3, 0.4, 0.86)))
        mats.assign(g, 'aluminum_polished')
        K.main.append(g)


# =====================================================================
# seats
# =====================================================================
SEAT_PATH = None


def seat_path():
    s, c = math.sin(BACK), math.cos(BACK)
    pts = [(HY - 0.505, HZ - 0.060), (HY - 0.492, HZ - 0.004), (HY - 0.468, HZ + 0.026), (HY - 0.425, HZ + 0.036),
           (HY - 0.33, HZ + 0.029), (HY - 0.21, HZ + 0.003), (HY - 0.09, HZ - 0.032), (HY + 0.02, HZ - 0.050),
           (HY + 0.080, HZ - 0.046), (HY + 0.112, HZ - 0.018)]
    for d in (0.07, 0.20, 0.35, 0.50, 0.62, 0.70):
        pts.append((HY + 0.125 + d * s, HZ + d * c))
    py, pz = pts[-1]
    pts += [(py + 0.016, pz + 0.040), (py + 0.040, pz + 0.064), (py + 0.070, pz + 0.072)]
    return pts


def build_seat(K):
    """Left (driver) seat; returns the list of objects."""
    coll = K.coll
    ns = 300 if K.fin else 72
    p2 = geo.catmull_rom(seat_path(), per_seg=12)
    p2 = geo.resample(p2, ns)
    p2 = np.asarray(p2)[:, :2] if np.asarray(p2).shape[1] >= 2 else np.asarray(p2)
    seg = np.linalg.norm(np.diff(p2, axis=0), axis=1)
    sarc = np.concatenate([[0], np.cumsum(seg)])
    Wb = geo.Pchip([0.30, 0.45, 0.62, 0.74, 0.80, 0.86, 1.05], [0.200, 0.215, 0.228, 0.222, 0.15, 0.135, 0.125])
    Hbb = geo.Pchip([0.30, 0.42, 0.60, 0.74, 0.80, 1.05], [0.06, 0.110, 0.100, 0.085, 0.03, 0.02])
    Wcb = geo.Pchip([0.30, 0.74, 0.80, 1.05], [0.56, 0.58, 0.80, 0.80])
    rows, shell_rows, info = [], [], []
    for i in range(ns):
        y, z = p2[i]
        a0 = p2[max(i - 1, 0)]
        a1 = p2[min(i + 1, ns - 1)]
        t = (a1 - a0) / max(np.linalg.norm(a1 - a0), 1e-9)
        nrm = np.array([-t[1], t[0]])
        k = ss(HZ + 0.03, HZ + 0.13, z) if y > HY else 0.0
        Wc_ = SEAT_W - 0.006 * (1 - ss(HY - 0.50, HY - 0.40, y))
        Hc = 0.022 + 0.030 * ss(HY - 0.50, HY - 0.40, y)
        W = geo.lerp(Wc_, float(Wb(z)), k)
        Hb = geo.lerp(Hc, float(Hbb(z)), k)
        wcr = geo.lerp(0.56, float(Wcb(z)), k)
        re = min(0.024, 0.45 * Hb + 0.010)
        Wc = min(W * wcr, W - re - 0.008)
        # horizontal flutes on the centre panels
        flute = 0.0
        on = (k < 0.5 and HY - 0.43 < y < HY - 0.01) or (k >= 0.5 and z < 0.78)
        if on:
            flute = max(0.0, math.cos(2 * math.pi * sarc[i] / 0.055)) ** 6
        half = []
        crown = 0.010
        for j in range(10):
            a = (Wc - 0.010) * j / 9.0
            fade = 1.0 - ss(Wc - 0.03, Wc - 0.012, a)
            half.append((a, crown * (1 - (a / Wc) ** 2) - 0.006 * flute * fade))
        half += [(Wc - 0.004, 0.0005), (Wc, -0.004), (Wc + 0.005, 0.003)]
        for j in range(1, 11):
            tt = j / 10.0
            half.append((Wc + 0.005 + (W - re - Wc - 0.005) * tt, 0.003 + (Hb - 0.003) * math.sin(math.pi / 2 * tt) ** 0.7))
        for j in range(1, 9):
            ph = math.radians(150.0 * j / 8.0)
            half.append((W - re + re * math.sin(ph), Hb - re + re * math.cos(ph)))
        full = [(-a, b) for a, b in reversed(half[1:])] + half
        rows.append([(XS + a, y + nrm[0] * b, z + nrm[1] * b) for a, b in full])
        D = geo.lerp(max(0.045, (z - ZF - 0.008) * max(nrm[1], 0.3)), 0.058, k)
        sh = [(W + 0.012, Hb * 0.55), (W + 0.017, 0.0), (W + 0.012, -0.6 * D), (W - 0.02, -D), (0.0, -D - 0.004),
              (-(W - 0.02), -D), (-(W + 0.012), -0.6 * D), (-(W + 0.017), 0.0), (-(W + 0.012), Hb * 0.55),
              (-(W - 0.03), -0.006), (0.0, -0.012), (W - 0.03, -0.006)]
        shc = geo.resample(geo.catmull_rom([(a, b, 0) for a, b in sh], per_seg=6, closed=True), 48, closed=True)
        shell_rows.append([(XS + p[0], y + nrm[0] * p[1], z + nrm[1] * p[1]) for p in shc])
        info.append(dict(y=y, z=z, n=nrm, W=W, Wc=Wc, Hb=Hb, re=re, D=D, k=k))
    nv = len(rows[0])
    mid = nv // 2
    cushion = geo.grid_surface('Interior_Seat_Cushion_L', rows, coll=coll)
    mats.assign(cushion, 'leather_light')
    fab = mats.get('fabric_light')
    cushion.data.materials.append(fab)
    for p in cushion.data.polygons:
        j = p.index % (nv - 1)
        if max(abs(j - mid), abs(j + 1 - mid)) <= 11:
            p.material_index = 1
    shell = geo.grid_surface('Interior_Seat_Shell_L', shell_rows, close_v=True, coll=coll)
    geo.fill_holes(shell)
    geo.recalc_normals(shell)
    mats.assign(shell, 'carbon_gloss')
    out = [cushion, shell]

    def sp(i, a, b):
        d = info[i]
        return (XS + a, d['y'] + d['n'][0] * b, d['z'] + d['n'][1] * b)

    # navy piping along the seams between bolsters and centre panels
    for side in (1, -1):
        pts = [sp(i, side * (info[i]['Wc'] + 0.0055), 0.0035) for i in range(2, ns - 2, 3)]
        pip = L.tube('Interior_Seat_Piping%d_L' % (side > 0), pts, 0.0026, coll, res=2)
        mats.assign(pip, 'leather_dark')
        out.append(pip)
    # aluminium strip along the shell sides (seen in the side view)
    iz = [i for i in range(ns) if info[i]['k'] > 0.9 and 0.40 < info[i]['z'] < 0.80]
    for side in (1, -1):
        pts = [sp(i, side * (info[i]['W'] + 0.0175), -0.35 * info[i]['D']) for i in iz[::4]]
        st = L.tube('Interior_Seat_Strip%d_L' % (side > 0), pts, 0.0022, coll, res=2)
        mats.assign(st, 'aluminum_polished')
        out.append(st)
    # belt slots in the shell top (dark recess with an aluminium frame)
    ish = min(range(ns), key=lambda i: abs(info[i]['z'] - 0.80) + (0 if info[i]['k'] > 0.9 else 9))
    d = info[ish]
    for side in (1,):
        c = Vector(sp(ish, 0.0, -d['D'] - 0.006))
        n = Vector((0, -d['n'][0], -d['n'][1]))
        Mf = L.frame_from_normal(c, n, up_hint=(1, 0, 0))
        path = [(x, y, 0) for x, y in L.stadium_path(0.040, 0.110, 10)]
        ring = geo.sweep('Interior_Seat_Slot_L', path, [(0.002 * math.cos(2 * math.pi * q / 8), 0.002 * math.sin(2 * math.pi * q / 8))
                                                       for q in range(8)], closed_path=True, coll=coll)
        geo.transform_mesh(ring, Mf)
        mats.assign(ring, 'aluminum_dark')
        hole = geo.grid_surface('Interior_Seat_SlotIn_L', [path, [(0, 0, -0.002)] * len(path)], close_v=True, coll=coll)
        geo.transform_mesh(hole, Mf @ T(0, 0, 0.001))
        mats.assign(hole, 'plastic_black')
        out += [ring, hole]
    # seat belt hanging along the outboard bolster to the sill anchor
    ib = [i for i in range(ns) if info[i]['k'] > 0.5 and 0.38 < info[i]['z'] < 0.86][::-1]
    pts = []
    for i in ib[::6]:
        dd = info[i]
        pts.append(sp(i, dd['W'] - dd['re'] - 0.004, dd['Hb'] + 0.004))
    last = Vector(pts[-1])
    anchor = Vector((XS + SEAT_W + 0.035, HY + 0.10, ZF + 0.11))
    pts += [tuple(last.lerp(anchor, 0.5) + Vector((0.01, -0.01, 0))), tuple(anchor)]
    pts = geo.catmull_rom(pts, per_seg=4)
    belt = geo.sweep('Interior_Seat_Belt_L', pts, L.rrect(0.0026, 0.046, 0.0012, 2), up=(1, 0, 0), coll=coll)
    mats.assign(belt, mats.custom('Interior_Webbing', base_color='#1c2632', roughness=0.8, sheen=0.4))
    out.append(belt)
    # belt guide at the top and anchor plate
    g = geo.box('Interior_Seat_BeltGuide_L', (0.055, 0.02, 0.012), tuple(Vector(pts[0]) + Vector((0, 0.008, 0.006))), coll)
    geo.mod_bevel(g, 0.004, 2, 30)
    mats.assign(g, 'aluminum_polished')
    an = geo.box('Interior_Seat_Anchor_L', (0.012, 0.05, 0.03), tuple(anchor + Vector((0.006, 0, -0.01))), coll)
    geo.mod_bevel(an, 0.003, 2, 30)
    mats.assign(an, 'aluminum_polished')
    out += [g, an]
    # buckle on the tunnel side
    bx, by = XT - 0.035, HY + 0.06
    bz = con_z(bx, by)
    stalk = L.tube('Interior_Seat_BuckleStalk_L', [(bx, by + 0.02, bz - 0.05), (bx, by + 0.01, bz - 0.01), (bx, by, bz + 0.005)],
                   0.007, coll)
    mats.assign(stalk, 'leather_dark')
    bk = geo.box('Interior_Seat_Buckle_L', (0.022, 0.034, 0.062), (bx, by, bz + 0.03), coll)
    geo.mod_bevel(bk, 0.006, 3, 30)
    mats.assign(bk, 'aluminum_polished')
    btn = geo.box('Interior_Seat_BuckleBtn_L', (0.016, 0.02, 0.008), (bx, by, bz + 0.062), coll)
    geo.mod_bevel(btn, 0.003, 2, 30)
    mats.assign(btn, mats.custom('Interior_BuckleRed', base_color='#b3121a', roughness=0.35, coat=0.6))
    out += [stalk, bk, btn]
    return out


def build_seats(K):
    left = build_seat(K)
    for ob in left:
        K.seats.append(ob)
        K.seats.append(geo.mirror_copy(ob, ob.name[:-2] + '_R', K.coll))


# =====================================================================
# dashboard wing
# =====================================================================
def dash_profile(x):
    ax = abs(x)
    te = ss(0.42, X_DASH_END, ax)                 # outer end: the wing drops towards the door
    tc = 1.0 - ss(0.10, 0.24, ax)                 # centre: blends into the console spine
    top = (ZDT - DASH_VALLEY * (1.0 - ss(0.04, 0.30, ax)) - 0.012 * ss(0.34, 0.5, ax)
           - 0.10 * ss(0.46, X_DASH_END, ax))
    yf = geo.lerp(Y_DASH_CTR, Y_DASH_FRONT, ss(0.12, 0.60, ax))   # front edge: deep on the centreline, back at the A-pillars
    yr = YDR + 0.004 * te
    lip = 0.600 - 0.065 * te - 0.02 * tc
    pts = [(yf, top - 0.045), (yf + 0.16, top - 0.016), (yf + 0.34, top - 0.004), (-0.76, top), (-0.64, top - 0.0015),
           (yr - 0.028, top - 0.006), (yr - 0.006, top - 0.024), (yr, top - 0.060),
           (yr - 0.002, geo.lerp(top - 0.06, lip, 0.5)), (yr - 0.016, lip + 0.028), (yr - 0.05, lip + 0.002),
           (yr - 0.10, lip - 0.012), (-0.80, lip - 0.022), (-0.98, 0.566), (min(-1.16, yf + 0.07), 0.556), (yf - 0.01, 0.585),
           (yf - 0.02, 0.68)]
    return pts


def build_dash(K):
    coll = K.coll
    nx = 90 if K.fin else 64
    per = 6 if K.fin else 4
    xs = [X_DASH_END * math.sin(math.pi / 2 * geo.lerp(-1, 1, i / nx)) for i in range(nx + 1)]
    rows = []
    for x in xs:
        pr = geo.catmull_rom([(0, y, z) for y, z in dash_profile(x)], per_seg=per, closed=True)
        rows.append([(x, p[1], p[2]) for p in pr])
    dash = geo.grid_surface('Interior_Dash', rows, close_v=True, coll=coll, sharp_angle=60)
    geo.fill_holes(dash)
    geo.recalc_normals(dash)
    # opening for the pop-up screen lid
    geo.delete_faces(dash, lambda c, f: abs(c.x) < SCREEN_HW - 0.004 and
                     SCREEN_HINGE_Y + 0.004 < c.y < SCREEN_HINGE_Y + SCREEN_LEN - 0.004 and f.normal.z > 0.5)
    mats.assign(dash, 'leather_light')
    mats.assign_faces(dash, 'leather_dark', lambda c, p: p.normal.z < -0.5 or abs(p.normal.x) > 0.9)
    mats.assign_faces(dash, 'dash_top', lambda c, p: p.normal.z > 0.3)
    K.dash.append(dash)
    # well under the screen lid
    well = geo.box('Interior_ScreenWell', (2 * SCREEN_HW - 0.01, SCREEN_LEN - 0.01, 0.04),
                   (0, SCREEN_HINGE_Y + SCREEN_LEN / 2, ZSCR - 0.024), coll)
    geo.delete_faces(well, lambda c, f: c.z > ZSCR - 0.01)
    geo.flip_normals(well)
    mats.assign(well, 'plastic_black')
    K.dash.append(well)

    # navy piping along the rear roll of the wing, interrupted by the console
    for side in (1, -1):
        pts = []
        for x in np.linspace(0.12, X_DASH_END - 0.01, 22):
            pr = dash_profile(x)
            yr = pr[6][0] + 0.003
            pts.append((side * x, yr, pr[6][1] + 0.004))
        pp = L.tube('Interior_DashPiping_%s' % ('L' if side > 0 else 'R'), pts, 0.003, coll, res=2)
        mats.assign(pp, 'leather_dark')
        K.dash.append(pp)
    # ambient strip under the lower lip
    for side in (1, -1):
        pts = []
        for x in np.linspace(0.16, X_DASH_END - 0.03, 20):
            pr = dash_profile(x)
            pts.append((side * x, pr[10][0] + 0.004, pr[10][1] - 0.004))
        st = L.tube('Interior_DashLight_%s' % ('L' if side > 0 else 'R'), pts, 0.0025, coll, res=2)
        mats.assign(st, 'emit_interior')
        K.dash.append(st)
    # slim vertical vents: beside the spine and at the outer ends
    for xv in (0.19, X_DASH_END - 0.065):
        for side in (1, -1):
            x = side * xv
            pr = dash_profile(x)
            yv = pr[8][0] + 0.002
            zv = pr[8][1] + 0.01
            for ob in L.vent('Interior_Vent', coll, 0.018, 0.075, depth=0.03):
                geo.transform_mesh(ob, L.frame(Vector((x, yv, zv)), Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))))
                K.dash.append(ob)
    # aluminium spine on the dash top (front of the screen lid)
    pr0 = dash_profile(0.0)
    pts = [(0, y, float(np.interp(y, [q[0] for q in pr0[:4]], [q[1] for q in pr0[:4]])) + 0.004)
           for y in np.linspace(pr0[0][0] + 0.02, SCREEN_HINGE_Y - 0.004, 16)]
    sp = geo.sweep('Interior_DashSpine', pts, L.rrect(0.03, 0.004, 0.0018, 3), up=(0, 0, 1), coll=coll)
    mats.assign(sp, 'aluminum_polished')
    K.dash.append(sp)


# =====================================================================
# centre console spine
# =====================================================================
CON_Y = [-0.665, -0.58, -0.50, -0.40, -0.28, -0.15, 0.0, 0.15, YBH]
CON_Z = [0.790, 0.770, 0.715, 0.640, 0.555, 0.482, 0.437, 0.418, 0.410]
con_top = geo.Pchip(CON_Y, CON_Z)
con_hw = geo.Pchip([-0.665, -0.45, -0.20, 0.0, 0.40, YBH], [0.105, 0.120, XT - 0.008, XT - 0.006, XT - 0.006, XT - 0.012])
frame_hw = geo.Pchip([-0.600, -0.56, -0.49, -0.40, -0.27, -0.13, -0.05, 0.04, 0.20, YBH - 0.01],
                     [0.016, 0.030, 0.058, 0.068, 0.070, 0.058, 0.032, 0.012, 0.009, 0.008])
_fh, _wh = frame_hw, None
frame_hw = lambda y: 0.78 * _fh(y)
WIN_Y0, WIN_Y1 = -0.535, -0.075
win_hw = geo.Pchip([WIN_Y0, -0.50, -0.42, -0.27, -0.13, WIN_Y1], [0.0, 0.040, 0.054, 0.056, 0.042, 0.0])

_wh0 = win_hw
win_hw = lambda y: 0.78 * _wh0(y)


def con_z(x, y):
    return float(con_top(y)) + 0.004 - 2.0 * x * x


def con_normal(y):
    dz = (float(con_top(y + 0.002)) - float(con_top(y - 0.002))) / 0.004
    return Vector((0.0, -dz, 1.0)).normalized()


def build_console(K):
    coll = K.coll
    ny = 120 if K.fin else 80
    ys = np.linspace(CON_Y[0], YBH - 0.004, ny)
    rows = []
    for y in ys:
        hw = float(con_hw(y))
        zt = float(con_top(y))
        sec = [(hw, ZF), (hw, zt - 0.05), (hw - 0.002, zt - 0.02), (hw - 0.012, zt - 0.004)]
        for x in np.linspace(hw - 0.03, -(hw - 0.03), 13):
            sec.append((x, con_z(x, y) - 0.001))
        sec += [(-(hw - 0.012), zt - 0.004), (-(hw - 0.002), zt - 0.02), (-hw, zt - 0.05), (-hw, ZF)]
        pr = geo.catmull_rom([(x, 0, z) for x, z in sec], per_seg=3)
        rows.append([(p[0], y, p[2]) for p in pr])
    body = geo.grid_surface('Interior_Console', rows, coll=coll, sharp_angle=60)
    geo.fill_holes(body)
    geo.recalc_normals(body)
    geo.delete_faces(body, lambda c, f: WIN_Y0 < c.y < WIN_Y1 and abs(c.x) < float(win_hw(c.y)) - 0.008 and f.normal.z > 0.4)
    mats.assign(body, 'leather_dark')
    mats.assign_faces(body, 'leather_light', lambda c, p: c.y < -0.12 and abs(p.normal.x) > 0.6)
    K.dash.append(body)

    # polished aluminium frame plate (teardrop with an open window)
    nyf = 200 if K.fin else 100
    nh = 10 if K.fin else 6
    rows = []
    for y in np.linspace(-0.600, YBH - 0.012, nyf):
        hw = float(frame_hw(y))
        wh = float(win_hw(y)) if WIN_Y0 < y < WIN_Y1 else 0.0
        xl = list(np.linspace(-hw, -wh, nh))
        xr = list(np.linspace(wh, hw, nh))
        rows.append([(x, y, con_z(x, y) + 0.0012) for x in xl + xr])
    fr = geo.grid_surface('Interior_ConsoleFrame', rows, coll=coll)
    geo.delete_faces(fr, lambda c, f: abs(c.x) < 1e-4 and f.calc_area() > 1e-7)
    geo.merge_by_distance(fr, 1e-6)
    geo.mod_solidify(fr, 0.005, offset=1.0)
    geo.mod_bevel(fr, 0.0012, 2, 30)
    mats.assign(fr, 'aluminum_polished')
    K.dash.append(fr)

    # crystal window and the exposed mechanism underneath
    yw = np.linspace(WIN_Y0, WIN_Y1, 48)
    rows = [[(x, y, con_z(x, y) + 0.0045) for x in np.linspace(-float(win_hw(y)), float(win_hw(y)), 12)] for y in yw]
    cr = geo.grid_surface('Interior_ConsoleCrystal', rows, coll=coll)
    geo.mod_solidify(cr, 0.007, offset=-1.0)
    mats.assign(cr, 'crystal')
    K.dash.append(cr)
    right = [(float(win_hw(y)), y) for y in yw]
    loop = right + [(-x, y) for x, y in reversed(right[1:-1])]
    top = [(x, y, con_z(x, y)) for x, y in loop]
    bot = [(x * 0.97, y, con_z(x, y) - 0.030) for x, y in loop]
    wall = geo.grid_surface('Interior_ConsoleWell', [top, bot], close_v=True, coll=coll)
    geo.fill_holes(wall)
    geo.recalc_normals(wall, inside=True)
    mats.assign(wall, 'aluminum_dark')
    K.dash.append(wall)
    # mechanism: wheels and rods on the well floor
    for k, (y, r, m) in enumerate(((-0.47, 0.028, 'gold'), (-0.40, 0.022, 'titanium'), (-0.33, 0.03, 'gold'),
                                   (-0.25, 0.024, 'aluminum_polished'), (-0.17, 0.020, 'gold'))):
        x = (0.018 if k % 2 else -0.016)
        g = L.gear('Interior_ConsoleGear%d' % k, r * 0.25, r, -0.002, 0.0, 24 + 4 * k, coll, spokes=4 + k % 2)
        geo.transform_mesh(g, L.frame_from_normal((x, y, con_z(x, y) - 0.024), con_normal(y), up_hint=(0, -1, 0)))
        mats.assign(g, m)
        K.dash.append(g)
    for x in (-0.032, 0.0, 0.032):
        pts = [(x, y, con_z(x, y) - 0.019) for y in np.linspace(-0.50, -0.11, 12)]
        rod = L.tube('Interior_ConsoleRod', pts, 0.0025, coll, res=2)
        mats.assign(rod, 'aluminum_polished')
        K.dash.append(rod)

    def place(objs, x, y, up=(0, -1, 0), lift=0.0045, extra=Matrix.Identity(4)):
        n = con_normal(y)
        Mf = L.frame_from_normal(Vector((x, y, con_z(x, y) + lift)), n, up_hint=up)
        for ob in objs:
            geo.transform_mesh(ob, Mf @ extra)
            K.dash.append(ob)

    # exactly three large glass-capped knurled knobs on a diagonal
    for k, (kx, ky) in enumerate(((-0.013, -0.492), (0.0, -0.418), (0.013, -0.344))):
        place(L.knob_glass('Interior_Knob%s' % 'ABC'[k], coll, 0.020, 0.058, knurl_n=48), kx, ky)
    # key block of varied sizes
    keys = [(-0.020, -0.285, 0.016, 0.012), (0.0, -0.285, 0.011, 0.012), (0.019, -0.285, 0.016, 0.012),
            (-0.016, -0.258, 0.024, 0.011), (0.016, -0.258, 0.016, 0.011),
            (-0.020, -0.232, 0.011, 0.012), (0.0, -0.232, 0.020, 0.012), (0.020, -0.232, 0.011, 0.012)]
    for k, (kx, ky, kw, kh) in enumerate(keys):
        key = L.prism('Interior_Key', L.rrect(kw, kh, 0.003, 2), 0.0, 0.0045, coll)
        geo.mod_bevel(key, 0.0008, 2, 30)
        mats.assign(key, 'aluminum_brushed' if k % 3 else 'plastic_gloss')
        dot = L.prism('Interior_KeyDot', L.rrect(kw * 0.5, kh * 0.4, 0.001, 2), 0.0044, 0.0050, coll)
        mats.assign(dot, 'emit_cluster')
        place([key, dot], kx, ky)
    red = L.prism('Interior_KeyRed', L.rrect(0.016, 0.012, 0.003, 2), 0.0, 0.0055, coll)
    geo.mod_bevel(red, 0.0008, 2, 30)
    mats.assign(red, mats.custom('Interior_StartRed', base_color='#9a1016', metallic=0.2, roughness=0.3, coat=1.0))
    place([red], 0.0, -0.108)
    # pull-to-start lever with a glass handle
    lever_b = L.prism('Interior_StartLeverBase', L.rrect(0.036, 0.020, 0.008), 0.0, 0.006, coll)
    geo.mod_bevel(lever_b, 0.0015, 2, 30)
    mats.assign(lever_b, 'aluminum_polished')
    stem = L.lathe('Interior_StartLeverStem', [(0, 0.004), (0.0035, 0.004), (0.003, 0.026), (0, 0.026)], seg=16, coll=coll)
    mats.assign(stem, 'chrome')
    hd = L.lathe('Interior_StartLeverGlass', [(0, 0.024), (0.005, 0.024), (0.009, 0.032), (0.011, 0.044), (0.009, 0.056),
                                              (0.004, 0.062), (0, 0.064)], seg=32, coll=coll)
    mats.assign(hd, 'crystal')
    place([lever_b, stem, hd], 0.0, -0.170, extra=R('X', -18))
    # polished stripe along the tunnel top is the narrow tail of the frame (already built)

    # pop-up screen on its hinge (front edge of the lid)
    dash_root = rig.module_root('Interior_Dash')
    hinge = rig.hinge('Screen', (0.0, SCREEN_HINGE_Y, ZSCR + 0.001), (1.0, 0.0, 0.0), 'screen', 105.0, parent_obj=dash_root)
    y0 = SCREEN_HINGE_Y
    lid = L.prism('Interior_ScreenLid', L.rrect(2 * SCREEN_HW, SCREEN_LEN, 0.01), -0.003, 0.0015, coll)
    geo.transform_mesh(lid, T(0, y0 + SCREEN_LEN / 2, ZSCR))
    geo.mod_bevel(lid, 0.0012, 2, 30)
    mats.assign(lid, 'leather_dark')
    fr2 = L.prism('Interior_ScreenFrame', L.rrect(2 * SCREEN_HW - 0.008, SCREEN_LEN - 0.008, 0.008), -0.013, -0.003, coll)
    geo.transform_mesh(fr2, T(0, y0 + SCREEN_LEN / 2, ZSCR))
    geo.mod_bevel(fr2, 0.0015, 2, 30)
    mats.assign(fr2, 'aluminum_polished')
    disp = L.prism('Interior_Screen', L.rrect(2 * SCREEN_HW - 0.022, SCREEN_LEN - 0.022, 0.004), -0.0137, -0.0129, coll)
    geo.transform_mesh(disp, T(0, y0 + SCREEN_LEN / 2, ZSCR))
    mats.assign(disp, 'glass_dark')
    ui = []
    yc = y0 + SCREEN_LEN / 2
    zu0, zu1 = -0.0142, -0.0137
    ring = L.annulus('Interior_ScreenRing', 0.030, 0.035, zu0, zu1, seg=56, coll=coll)
    geo.transform_mesh(ring, T(0, yc + 0.030, ZSCR))
    ring2 = L.annulus('Interior_ScreenRing2', 0.011, 0.014, zu0, zu1, seg=32, coll=coll)
    geo.transform_mesh(ring2, T(-0.030, yc - 0.020, ZSCR))
    ring3 = L.annulus('Interior_ScreenRing3', 0.011, 0.014, zu0, zu1, seg=32, coll=coll)
    geo.transform_mesh(ring3, T(0.030, yc - 0.020, ZSCR))
    bar0 = L.prism('Interior_ScreenBar0', L.rrect(0.090, 0.006, 0.002, 2), zu0, zu1, coll)
    geo.transform_mesh(bar0, T(0, yc + 0.074, ZSCR))
    bars = [L.prism('Interior_ScreenBarB%d' % k, L.rrect(0.026, 0.012, 0.003, 2), zu0, zu1, coll) for k in range(3)]
    for k, b in enumerate(bars):
        geo.transform_mesh(b, T(-0.032 + 0.032 * k, yc - 0.062, ZSCR))
    uimesh = geo.join([ring, ring2, ring3, bar0] + bars, 'Interior_ScreenUI')
    mats.assign(uimesh, 'emit_screen')
    ui.append(uimesh)
    strip = geo.box('Interior_ScreenSpine', (0.03, SCREEN_LEN - 0.004, 0.0035), (0, y0 + SCREEN_LEN / 2, ZSCR + 0.0028), coll)
    geo.mod_bevel(strip, 0.0012, 2, 30)
    mats.assign(strip, 'aluminum_polished')
    arm = L.tube('Interior_ScreenArm', [(0, y0 + 0.004, ZSCR - 0.03), (0, y0 + 0.012, ZSCR - 0.012), (0, y0 + 0.030, ZSCR - 0.011)], 0.007, coll)
    mats.assign(arm, 'aluminum_polished')
    ui.append(arm)
    kn = L.knob('Interior_ScreenKnob', coll, 0.0225, 0.030, crystal=False, knurl_n=40)
    for ob in kn:
        geo.transform_mesh(ob, T(0, -0.705, ZSCR))
        K.dash.append(ob)
    for ob in (lid, fr2, disp, strip, *ui):
        geo.parent(ob, hinge)
        K.screen.append(ob)


# =====================================================================
# steering wheel, fixed hub and instrument cluster
# =====================================================================
def rim_path(per):
    q = [(0, 0.172), (0.092, 0.160), (0.150, 0.108), (0.176, 0.022), (0.171, -0.058), (0.142, -0.114),
         (0.082, -0.138), (0.0, -0.142)]
    full = q + [(-a, b) for a, b in reversed(q[1:-1])]
    pts = geo.catmull_rom([(a, b, 0.0) for a, b in full], per_seg=per, closed=True)
    return [tuple(p) for p in pts]


def build_wheel(K):
    coll = K.coll
    dash_root = rig.module_root('Interior_Dash')
    hinge = rig.hinge('SteeringWheel', tuple(SC), tuple(W_C), 'steer', 120.0, parent_obj=dash_root)
    rot, fix = [], []
    per = 10 if K.fin else 6
    path = rim_path(per)
    prof = [(0.0160 * math.cos(2 * math.pi * k / 18), 0.0190 * math.sin(2 * math.pi * k / 18)) for k in range(18)]
    rim = geo.sweep('Interior_Wheel_Rim', path, prof, closed_path=True, up=(0, 0, 1), coll=coll, sharp_angle=None)
    mats.assign(rim, 'leather_slate')
    mats.assign_faces(rim, 'leather_light', lambda c, p: c.y > 0.125 and abs(c.x) < 0.045)
    mats.assign_faces(rim, 'aluminum_polished', lambda c, p: c.y < -0.12 and abs(c.x) < 0.022)
    rot.append(rim)
    # stitching on the inner circumference
    inner = []
    for i, p in enumerate(path):
        v = Vector(p)
        n_in = -v.normalized()
        inner.append(tuple(v + n_in * 0.0142 + Vector((0, 0, 0.004))))
    st = L.tube('Interior_Wheel_Stitch', inner, 0.0009, coll, res=1, cyclic=True, spline='POLY')
    mats.assign(st, 'stitch')
    rot.append(st)
    # horizontal spokes (3 and 9 o'clock) curving back to the rotating collar
    for side in (1, -1):
        pts = [(side * 0.170, -0.004, -0.004), (side * 0.152, -0.008, -0.012), (side * 0.134, -0.010, -0.046),
               (side * 0.105, -0.009, -0.064), (side * 0.072, -0.006, -0.070)]
        pts = geo.catmull_rom(pts, per_seg=5)
        spk = geo.sweep('Interior_Wheel_Spoke', pts, L.rrect(0.014, 0.034, 0.006, 3), up=(0, 1, 0), coll=coll, cap=True)
        mats.assign(spk, 'leather_slate')
        rot.append(spk)
        # aluminium switch pod with two buttons and a small roller
        pod = L.prism('Interior_Wheel_Pod', L.rrect(0.026, 0.050, 0.008), -0.012, 0.0, coll)
        geo.mod_bevel(pod, 0.002, 2, 30)
        geo.transform_mesh(pod, T(side * 0.142, -0.012, 0.0))
        mats.assign(pod, 'aluminum_polished')
        rot.append(pod)
        for k, dy in enumerate((0.010, -0.010)):
            b = L.prism('Interior_Wheel_Btn', L.rrect(0.016, 0.011, 0.004), 0.0, 0.003, coll)
            geo.mod_bevel(b, 0.0012, 2, 30)
            geo.transform_mesh(b, T(side * 0.142, -0.012 + dy + 0.006, 0.0))
            mats.assign(b, 'plastic_gloss')
            rot.append(b)
        rl = L.lathe('Interior_Wheel_Roller', [(0, -0.004), (0.006, -0.004), (0.006, 0.004), (0, 0.004)], seg=32,
                     coll=coll, knurl=(16, 0.0006, -0.004, 0.004))
        geo.transform_mesh(rl, T(side * 0.142, -0.031, 0.002) @ R('Y', 90))
        mats.assign(rl, 'aluminum_polished')
        rot.append(rl)
        # paddle shifters behind the rim
        out = [(0.085, -0.012), (0.150, -0.020), (0.186, 0.000), (0.192, 0.030), (0.178, 0.052), (0.120, 0.040), (0.085, 0.018)]
        out = [(side * a, b) for a, b in out]
        if side < 0:
            out = list(reversed(out))
        pad = L.prism('Interior_Wheel_Paddle', out, -0.060, -0.054, coll)
        geo.mod_bevel(pad, 0.0015, 2, 30)
        mats.assign(pad, 'aluminum_polished')
        rot.append(pad)
    # two black posts reaching round behind the cluster
    for side in (1, -1):
        post = geo.box('Interior_Wheel_Post', (0.012, 0.115, 0.016), (side * 0.060, 0.112, -0.020), coll)
        geo.mod_bevel(post, 0.002, 2, 30)
        mats.assign(post, 'plastic_black')
        rot.append(post)
    # lower twin spoke (navy)
    for dx in (-0.011, 0.011):
        pts = geo.catmull_rom([(dx, -0.136, -0.004), (dx, -0.126, -0.022), (dx * 1.2, -0.104, -0.052), (dx * 1.4, -0.074, -0.068)],
                              per_seg=5)
        ls = geo.sweep('Interior_Wheel_LowSpoke', pts, L.rrect(0.010, 0.018, 0.004, 3), up=(0, 0, 1), coll=coll, cap=True)
        mats.assign(ls, 'leather_dark')
        rot.append(ls)
    # rotating collar (ring bearing) behind the cluster
    col = L.lathe('Interior_Wheel_Collar', [(0.050, -0.079), (0.078, -0.079), (0.081, -0.074), (0.081, -0.066),
                                            (0.076, -0.061), (0.050, -0.061)], seg=72, coll=coll, closed_profile=True)
    mats.assign(col, 'aluminum_polished')
    rot.append(col)

    # ---- fixed parts ----
    # column shroud through the collar into the dash
    sh = L.lathe('Interior_Column', [(0, -0.34), (0.066, -0.34), (0.062, -0.24), (0.046, -0.12), (0.041, -0.06),
                                     (0.040, -0.024), (0, -0.024)], seg=48, coll=coll)
    mats.assign(sh, 'leather_dark')
    fix.append(sh)
    # hub pod (fixed, pale blue leather) with the EB monogram
    secs = []
    for cz, s in ((-0.026, 0.93), (-0.014, 1.0), (0.018, 1.0), (0.031, 0.96), (0.038, 0.88), (0.042, 0.72)):
        secs.append([(x * s, -0.024 + y * s, cz) for x, y in L.ellipse(0.07, 0.07, 48)])
    hub = geo.grid_surface('Interior_Hub', secs, close_v=True, coll=coll)
    geo.fill_holes(hub)
    geo.recalc_normals(hub)
    geo.mod_subsurf(hub, 1, 2 if K.fin else 1)
    mats.assign(hub, 'leather_light')
    fix.append(hub)
    ring = geo.sweep('Interior_HubBadgeRing', [(x, -0.024 + y, 0.0425) for x, y in L.ellipse(0.036, 0.036, 40)],
                     [(0.0015 * math.cos(2 * math.pi * k / 8), 0.0015 * math.sin(2 * math.pi * k / 8)) for k in range(8)],
                     closed_path=True, coll=coll)
    mats.assign(ring, 'aluminum_polished')
    fix.append(ring)
    ring2 = geo.sweep('Interior_HubRing', [(x, -0.024 + y, 0.016) for x, y in L.ellipse(0.0715, 0.0715, 64)],
                      [(0.003 * math.cos(2 * math.pi * k / 8), 0.003 * math.sin(2 * math.pi * k / 8)) for k in range(8)],
                      closed_path=True, coll=coll)
    mats.assign(ring2, 'aluminum_polished')
    fix.append(ring2)
    eb = L.eb_logo('Interior_HubEB', 0.034, 0.0012, coll)
    geo.transform_mesh(eb, T(0, -0.025, 0.0425))
    mats.assign(eb, 'aluminum_polished')
    fix.append(eb)
    # small rotary controls either side of the hub
    for side in (1, -1):
        arm = geo.box('Interior_HubArm', (0.03, 0.016, 0.012), (side * 0.066, -0.016, -0.004), coll)
        geo.mod_bevel(arm, 0.004, 2, 30)
        mats.assign(arm, 'aluminum_brushed')
        fix.append(arm)
        cyl = L.lathe('Interior_HubKnob', [(0, -0.025), (0.0055, -0.025), (0.006, -0.022), (0.006, 0.022), (0.0055, 0.025), (0, 0.025)],
                      seg=48, coll=coll, knurl=(24, 0.0006, -0.021, 0.021))
        geo.transform_mesh(cyl, T(side * 0.082, -0.016, 0.001) @ R('Y', side * 75))
        mats.assign(cyl, 'plastic_black')
        fix.append(cyl)
    # cluster: skeleton frame + three dials
    dials = [((0.0, 0.094, 0.0), 0.047, ['0', '100', '200', '300', '400', '500'], True),
             ((-0.085, 0.050, -0.004), 0.034, [], False),
             ((0.085, 0.050, -0.004), 0.034, [], False)]
    hull = []
    for (cx, cy, cz), r, _n, _b in dials:
        hull += [(cx + (r * 1.13 + 0.005) * math.cos(t), cy + (r * 1.13 + 0.005) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 40)]
    hull += [(x, y) for x, y in L.rrect(0.12, 0.05, 0.02, 4, 0.0, 0.0)]
    hull += [(-0.125, 0.075), (0.125, 0.075), (-0.06, 0.145), (0.06, 0.145)]
    hull = L.convex_hull(hull)
    plate = L.prism('Interior_ClusterPlate', [(x, y) for x, y in hull], -0.036, -0.028, coll)
    cuts = []
    for sx in (1, -1):
        tri = [(sx * 0.060, 0.099), (sx * 0.082, 0.099), (sx * 0.071, 0.121)]
        cuts.append(L.prism('cut', tri if sx > 0 else tri[::-1], -0.05, -0.01, coll))
        cuts.append(L.prism('cut', [(sx * 0.108, 0.058), (sx * 0.121, 0.058), (sx * 0.114, 0.070)] if sx > 0 else
                            [(-0.121, 0.058), (-0.108, 0.058), (-0.114, 0.070)][::-1], -0.05, -0.01, coll))
    geo.boolean(plate, geo.join(cuts, 'cutter'), 'DIFFERENCE', solver='EXACT')
    geo.mod_bevel(plate, 0.0015, 2, 30)
    mats.assign(plate, 'aluminum_polished')
    fix.append(plate)
    for k, ((cx, cy, cz), r, nums, big) in enumerate(dials):
        house = L.lathe('Interior_DialHouse%d' % k, [(r * 1.115, -0.007), (r * 1.10, -0.020), (r * 1.06, -0.030),
                                                     (r * 0.9, -0.030)], seg=64, coll=coll)
        geo.transform_mesh(house, T(cx, cy, cz))
        mats.assign(house, 'titanium')
        fix.append(house)
        parts = L.dial('Interior_Dial%d' % k, coll, r, nums, ticks=50 if big else 30, major_every=5,
                       needle_deg=150.0 if big else (100.0 if k == 1 else 60.0), detail=True, red_zone=(k == 1), window=(k == 0), sub=(k == 1),
                       label=('PUISSANCE V16' if k == 2 else None))
        for ob in parts:
            geo.transform_mesh(ob, T(cx, cy, cz))
            fix.append(ob)
    # bridges linking the dials (open skeleton look)
    items = [T(-0.050, 0.100, -0.0125) @ R('Z', -8) @ S(0.03, 0.005, 0.004),
             T(0.050, 0.100, -0.0125) @ R('Z', 8) @ S(0.03, 0.005, 0.004),
             T(0.0, 0.020, -0.012) @ S(0.09, 0.007, 0.004)]
    br = L.cubes('Interior_ClusterBridges', items, coll)
    geo.mod_bevel(br, 0.001, 2, 30)
    mats.assign(br, 'aluminum_polished')
    fix.append(br)
    # screws on the frame
    sc = []
    for (x, y) in ((-0.100, 0.085), (0.100, 0.085), (-0.060, 0.020), (0.060, 0.020), (0.0, 0.150)):
        s = L.lathe('Interior_Screw', [(0, 0.0), (0.0025, 0.0), (0.0025, 0.001), (0.0015, 0.0016), (0, 0.0017)], seg=12, coll=coll)
        geo.transform_mesh(s, T(x, y, -0.028))
        sc.append(s)
    scr = geo.join(sc, 'Interior_ClusterScrews')
    mats.assign(scr, 'gold')
    fix.append(scr)

    for ob in rot:
        geo.transform_mesh(ob, MW)
        geo.parent(ob, hinge)
        K.wheel.append(ob)
    for ob in fix:
        geo.transform_mesh(ob, MW)
        K.dash.append(ob)


# =====================================================================
# pedals and footrest
# =====================================================================
def build_pedals(K):
    coll = K.coll
    n = Vector((0, math.cos(math.radians(20)), math.sin(math.radians(20))))
    for name, (x, y, z), (w, h) in (('Throttle', (XS - 0.085, -1.035, 0.255), (0.06, 0.12)),
                                    ('Brake', (XS + 0.03, -1.000, 0.285), (0.085, 0.075))):
        plate = L.prism('Interior_Pedal_' + name, L.rrect(w, h, 0.012), -0.004, 0.004, coll)
        cut = []
        for i in range(3):
            for j in range(4 if name == 'Throttle' else 2):
                cx = geo.lerp(-w / 2 + 0.014, w / 2 - 0.014, i / 2.0)
                cy = geo.lerp(-h / 2 + 0.016, h / 2 - 0.016, j / max((4 if name == 'Throttle' else 2) - 1, 1))
                c = geo.cylinder('cut', 0.0045, 0.03, 'Z', (cx, cy, 0), segments=16, coll=coll)
                cut.append(c)
        cutter = geo.join(cut, 'cutter')
        geo.boolean(plate, cutter, 'DIFFERENCE', solver='EXACT')
        geo.mod_bevel(plate, 0.0012, 2, 30)
        geo.transform_mesh(plate, L.frame_from_normal((x, y, z), n))
        mats.assign(plate, 'aluminum_brushed')
        arm = L.tube('Interior_PedalArm_' + name, [(x, y - 0.012, z), (x, y - 0.03, z + 0.10), (x, -1.12, 0.54)], 0.008, coll)
        mats.assign(arm, 'aluminum_dark')
        K.main += [plate, arm]
    fr = L.prism('Interior_Footrest', L.rrect(0.09, 0.17, 0.02), -0.005, 0.005, coll)
    geo.mod_bevel(fr, 0.0015, 2, 30)
    geo.transform_mesh(fr, L.frame_from_normal((XS + 0.17, -1.04, 0.255), n))
    mats.assign(fr, 'aluminum_brushed')
    items = [T(0, y, 0.006) @ S(0.075, 0.008, 0.004) for y in np.linspace(-0.065, 0.065, 7)]
    rb = L.cubes('Interior_FootrestStrips', items, coll)
    geo.transform_mesh(rb, L.frame_from_normal((XS + 0.17, -1.04, 0.255), n))
    mats.assign(rb, 'rubber')
    K.main += [fr, rb]


# =====================================================================
# door cards
# =====================================================================
def door_profile(y):
    wa = ss(-0.55, -0.42, y) * (1.0 - ss(0.22, 0.38, y))
    xi = 0.676
    pts = [(DOOR_X_OUT, 0.352), (DOOR_X_OUT, 0.60), (DOOR_X_OUT, ZBELT - 0.006), (DOOR_X_OUT - 0.008, ZBELT + 0.006),
           (DOOR_X_OUT - 0.026, ZBELT + 0.008), (xi + 0.016, ZBELT + 0.0), (xi + 0.010, ZBELT - 0.022),
           (xi + 0.004, 0.74), (xi, 0.68), (xi - 0.008 * wa, 0.640), (xi - 0.040 * wa, 0.626), (xi - 0.052 * wa, 0.604),
           (xi - 0.046 * wa, 0.582), (xi - 0.020 * wa, 0.566), (xi + 0.002, 0.52), (xi + 0.006, 0.44), (xi + 0.012, 0.385),
           (xi + 0.024, 0.358), (xi + 0.040, 0.352)]
    return pts, wa


def door_inner_x(y, z):
    return 0.676 + 0.0833 * max(z - 0.68, 0.0) + 0.003 * max(0.52 - z, 0.0) / 0.08


def build_doors(K):
    coll = K.coll
    ny = 70 if K.fin else 36
    rows = []
    ys = np.linspace(DOOR_Y0, DOOR_Y1, ny)
    for y in ys:
        pr, _wa = door_profile(y)
        pts = geo.catmull_rom([(x, 0, z) for x, z in pr], per_seg=4, closed=True)
        rows.append([(p[0], min(y, spec.door_rear_y(p[2]) - 0.045), p[2]) for p in pts])
    card = geo.grid_surface('Interior_DoorCard_L', rows, close_v=True, coll=coll, sharp_angle=60)
    geo.merge_by_distance(card, 1e-5)
    geo.fill_holes(card)
    geo.recalc_normals(card)
    mats.assign(card, 'leather_light')
    mats.assign_faces(card, 'leather_dark', lambda c, p: c.z > ZBELT - 0.012 or (0.565 < c.z < 0.645 and c.x < 0.668)
                      or c.z < 0.375 or c.x > DOOR_X_OUT - 0.002)
    parts = [card]
    # textured oval inset with navy piping
    yc, zc, ra, rb = -0.30, 0.700, 0.30, 0.050
    nr, nt = 6, 64
    rows = []
    for i in range(nr + 1):
        s = i / nr
        rows.append([(door_inner_x(yc + ra * s * math.cos(t), zc + rb * s * math.sin(t)) - 0.0035 - 0.002 * (1 - s * s),
                      yc + ra * s * math.cos(t), zc + rb * s * math.sin(t)) for t in np.linspace(0, 2 * math.pi, nt, endpoint=False)])
    ov = geo.grid_surface('Interior_DoorInset_L', rows, close_v=True, coll=coll)
    geo.merge_by_distance(ov, 1e-6)
    geo.recalc_normals(ov)
    if ov.data.polygons[0].normal.x > 0:
        geo.flip_normals(ov)
    mats.assign(ov, 'fabric_light')
    pts = [(door_inner_x(yc + ra * math.cos(t), zc + rb * math.sin(t)) - 0.0035, yc + ra * math.cos(t), zc + rb * math.sin(t))
           for t in np.linspace(0, 2 * math.pi, 64 if K.fin else 36, endpoint=False)]
    pip = L.tube('Interior_DoorPiping_L', pts, 0.003, coll, res=2, cyclic=True)
    mats.assign(pip, 'leather_dark')
    parts += [ov, pip]
    # speaker grille
    yg, zg, rg = -0.66, 0.46, 0.058
    xg = door_inner_x(yg, zg) - 0.002
    Mg = L.frame(Vector((xg, yg, zg)), Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0)))
    gr = L.disc('Interior_DoorGrille_L', rg, 0.002, seg=48, coll=coll)
    geo.transform_mesh(gr, Mg)
    mats.assign(gr, 'mesh_grille')
    back = L.disc('Interior_DoorGrilleBack_L', rg, -0.0005, seg=48, coll=coll)
    geo.transform_mesh(back, Mg)
    mats.assign(back, 'plastic_black')
    rim = L.lathe('Interior_DoorGrilleRing_L', [(rg - 0.002, -0.001), (rg + 0.004, -0.001), (rg + 0.004, 0.002),
                                                (rg + 0.001, 0.0035), (rg - 0.002, 0.003)], seg=64, coll=coll, closed_profile=True)
    geo.transform_mesh(rim, Mg)
    mats.assign(rim, 'aluminum_polished')
    parts += [gr, back, rim]
    # inner door handle: navy recess with a polished lever
    yh, zh = DOOR_Y0 + 0.13, 0.748
    xh = door_inner_x(yh, zh)
    rec = L.prism('Interior_DoorHandleRecess_L', L.ellipse(0.075, 0.022, 40), 0.0, 0.003, coll)
    geo.transform_mesh(rec, L.frame(Vector((xh - 0.0025, yh + 0.02, zh)), Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0))))
    mats.assign(rec, 'leather_dark')
    lev = L.tube('Interior_DoorHandle_L', [(xh - 0.004, yh - 0.065, zh), (xh - 0.026, yh - 0.060, zh + 0.003),
                                           (xh - 0.034, yh - 0.020, zh + 0.004), (xh - 0.034, yh + 0.020, zh + 0.004),
                                           (xh - 0.026, yh + 0.060, zh + 0.003), (xh - 0.004, yh + 0.065, zh)], 0.006, coll, res=3)
    mats.assign(lev, 'aluminum_polished')
    boss = L.lathe('Interior_DoorHandleBoss_L', [(0, 0.0), (0.012, 0.0), (0.012, 0.012), (0.009, 0.016), (0, 0.016)], seg=32, coll=coll)
    geo.transform_mesh(boss, L.frame(Vector((xh - 0.003, yh - 0.035, zh)), Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0))))
    mats.assign(boss, 'aluminum_polished')
    parts += [rec, lev, boss]
    # pocket lid with the Tourbillon script, and a carbon trim piece near the hinge
    yp, zp = -0.30, 0.455
    xp = door_inner_x(yp, zp)
    Fp = L.frame(Vector((xp - 0.0015, yp, zp)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0)))
    lidp = L.prism('Interior_DoorPocket_L', L.rrect(0.30, 0.075, 0.02, 6), 0.0, 0.003, coll)
    geo.transform_mesh(lidp, Fp)
    mats.assign(lidp, 'leather_dark')
    scr = geo.text_mesh('Interior_DoorScript_L', 'Tourbillon', size=0.032, extrude=0.0006, coll=coll)
    geo.transform_mesh(scr, L.frame(Vector((xp - 0.0045, yp, zp - 0.008)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0))))
    mats.assign(scr, 'aluminum_polished')
    yc2, zc2 = DOOR_Y0 + 0.09, 0.60
    ct = L.prism('Interior_DoorCarbon_L', L.rrect(0.15, 0.17, 0.02, 5), 0.0, 0.004, coll)
    geo.transform_mesh(ct, L.frame(Vector((door_inner_x(yc2, zc2) - 0.001, yc2, zc2)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0))))
    mats.assign(ct, 'carbon_gloss')
    parts += [lidp, scr, ct]
    pts = [(door_inner_x(y, 0.40) - 0.0015, y, 0.40) for y in np.linspace(DOOR_Y0 + 0.2, 0.05, 16)]
    amb2 = L.tube('Interior_DoorGlow_L', pts, 0.002, coll, res=2)
    mats.assign(amb2, 'emit_interior')
    parts.append(amb2)
    # ambient light strip under the window sill cap
    pts = [(door_inner_x(y, 0.795) - 0.0015, y, 0.795) for y in np.linspace(DOOR_Y0 + 0.03, spec.door_rear_y(0.795) - 0.075, 20)]
    amb = L.tube('Interior_DoorLight_L', pts, 0.0022, coll, res=2)
    mats.assign(amb, 'emit_interior')
    parts.append(amb)
    hl, hr = rig.door_hinge('L'), rig.door_hinge('R')
    for ob in parts:
        cp = geo.mirror_copy(ob, ob.name[:-2] + '_R', coll)
        geo.parent(ob, hl)
        geo.parent(cp, hr)
        K.door_l += [ob, cp]


# =====================================================================
# lamps
# =====================================================================
def build_lights(K):
    import bpy
    coll = K.coll
    spots = [('Interior_Lamp_Roof_L', (XS, HY - 0.12, ZHEAD - 0.02), 0.22, 0.10, 14.0),
             ('Interior_Lamp_Roof_R', (-XS, HY - 0.12, ZHEAD - 0.02), 0.22, 0.10, 14.0),
             ('Interior_Lamp_Foot_L', (XS, -0.86, 0.53), 0.16, 0.08, 9.0),
             ('Interior_Lamp_Foot_R', (-XS, -0.86, 0.53), 0.16, 0.08, 9.0),
             ('Interior_Lamp_Console', (0.0, -0.30, ZHEAD - 0.03), 0.12, 0.30, 6.0)]
    for name, loc, sx, sy, watts in spots:
        ld = bpy.data.lights.new(name, 'AREA')
        ld.shape = 'RECTANGLE'
        ld.size = sx
        ld.size_y = sy
        ld.color = (0.80, 0.90, 1.0)
        ld.energy = 0.0
        ob = bpy.data.objects.new(name, ld)
        coll.objects.link(ob)
        ob.location = loc
        rig.drive_light(ob, 'interior_lights', watts)
        K.main.append(ob)


# =====================================================================
def _tint(name, rgb):
    m = mats.get(name)
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs['Base Color'].default_value = (rgb[0] ** 2.2, rgb[1] ** 2.2, rgb[2] ** 2.2, 1.0)


def build(ctx):
    import os
    K = Ctx(ctx)
    L.make_materials()
    L.SEG_SCALE = 1.0 if K.fin else 0.55
    build_tub(K)
    build_seats(K)
    build_dash(K)
    build_console(K)
    build_wheel(K)
    build_pedals(K)
    build_doors(K)
    build_lights(K)
    if os.environ.get('TB_INT_NOROOF'):
        for ob in K.main:
            if ob.name.startswith(('Interior_Headliner', 'Interior_Roof', 'Interior_Mirror', 'Interior_APillar')):
                ob.hide_render = True
    rig.adopt(K.main, ctx.module_root('Interior'))
    rig.adopt(K.seats, rig.module_root('Interior_Seats'))
    rig.adopt(K.dash, rig.module_root('Interior_Dash'))
    ctx.data['interior'] = dict(
        steering_hinge='HINGE_SteeringWheel', screen_hinge='HINGE_Screen',
        dash_top_front=(0.0, Y_DASH_FRONT, ZDT - 0.045), dash_half_width=X_DASH_END,
        door_card_x_out=DOOR_X_OUT, driver_eye=(XS, HY + 0.18, HZ + 0.72))
