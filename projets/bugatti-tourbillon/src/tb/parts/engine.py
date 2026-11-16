"""Engine module: 8.3 l V16 (90 deg), carbon airboxes + trumpets, exhaust, 8-speed DCT + rear e-motor.

Crankshaft along Y at x = 0, z = ZC. Banks at +-45 deg. Left bank (+X) is authored and mirrored.
Sub-roots (children of MOD_Engine): MOD_Engine_Exhaust, MOD_Engine_Gearbox.
Published: ctx.data['engine'] (exhaust outlets, extents, anchors).
"""
import importlib
import math
import numpy as np
import bpy
from mathutils import Matrix

from tb import geo, mats, rig, spec
from tb.parts import chassis_lib as L
importlib.reload(L)
from tb.parts.chassis_lib import MeshBuilder, Parts, V, unit, catmull, rect_profile, circle, rot_x, rot_y, frame_from_axis

EX, EY, EZ = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
S2 = math.sqrt(0.5)
ZC = 0.30                    # crank axis height
Y0 = 0.76                    # front face of the block
PCH = 0.092                  # cylinder pitch
NC = 8
Y1 = Y0 + NC * PCH           # 1.496
A_ = np.array([S2, 0, S2])   # bank axis (up/out) of the left bank
NO = np.array([S2, 0, -S2])  # 'outward' direction across the bank (exhaust side)
RB = np.stack([NO, EY, A_], axis=1)     # local x = t (across), y = Y, z = s (along the bank axis)
CYL_Y = [Y0 + PCH * (i + 0.5) for i in range(NC)]


def bp(s, t, y):
    """Point from bank coordinates (s along the bank axis, t across, positive = exhaust side)."""
    return np.array([(s + t) * S2, y, ZC + (s - t) * S2])


def bbox(mb, s0, s1, t0, t1, y0, y1, ch=0.0, seg=1):
    mb.box(bp((s0 + s1) / 2, (t0 + t1) / 2, (y0 + y1) / 2), (t1 - t0, y1 - y0, s1 - s0), R=RB, ch=ch, seg=seg)


def _materials():
    mats.custom('HV_Orange', base_color='#E5600B', roughness=0.42, specular=0.5)
    mats.custom('Anodised_Blue', base_color='#1B4F9C', metallic=0.85, roughness=0.28)
    mats.custom('Hose_Black', base_color=(0.012, 0.012, 0.013), roughness=0.5)
    mats.custom('Engine_Cover', base_color='#15171A', metallic=0.7, roughness=0.38, coat=0.3)


def _lamp(coll, root, name, loc, watts, color=(1.0, 0.72, 0.45)):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = 0.0
    ld.color = color
    ld.shadow_soft_size = 0.06
    ob = bpy.data.objects.new(name, ld)
    coll.objects.link(ob)
    ob.location = loc
    geo.parent(ob, root)
    rig.drive_light(ob, 'engine_glow', watts)
    return ob


def _text(coll, parent, name, body, size, centre, R, mat, extrude=0.0022):
    ob = geo.text_mesh(name, body, size, extrude, coll=coll)
    m = Matrix([[R[0][0], R[0][1], R[0][2], centre[0]], [R[1][0], R[1][1], R[1][2], centre[1]],
                [R[2][0], R[2][1], R[2][2], centre[2]], [0, 0, 0, 1]])
    geo.transform_mesh(ob, m)
    mats.assign(ob, mat)
    geo.parent(ob, parent)
    return ob


def hull_loop(circles, n_pts=96, samples=28):
    pts = []
    for (cx, cz, r) in circles:
        for k in range(samples):
            a = 2 * math.pi * k / samples
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    pts = sorted(set(pts))

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
    hull = np.array(lo[:-1] + up[:-1])
    return geo.resample(hull, n_pts, closed=True)


def build(ctx):
    importlib.reload(L)
    _materials()
    final = ctx.final()
    q = 1.5 if final else 1.0
    SEG = int(14 * q)        # cylinder segments
    TSEG = int(10 * q)       # tube segments
    coll = ctx.collection('Engine')
    root = ctx.module_root('Engine')
    r_exh = rig.module_root('Engine_Exhaust')
    r_gbx = rig.module_root('Engine_Gearbox')
    for r in (r_exh, r_gbx):
        geo.parent(r, root)
        r.empty_display_size = 0.15

    P = Parts(coll, root, 'Engine_')
    PX = Parts(coll, r_exh, 'Engine_X_')
    PG = Parts(coll, r_gbx, 'Engine_G_')

    # ------------------------------------------------------------ crankcase, blocks, heads
    cc = P.get('Crankcase', 'aluminum_dark', bevel=(0.0025, 2))
    cc.box((0, (Y0 + Y1) / 2, ZC - 0.05), (0.36, Y1 - Y0, 0.19), ch=0.014, seg=2)
    cc.box((0, (Y0 + Y1) / 2 - 0.01, 0.158), (0.26, Y1 - Y0 - 0.14, 0.05), ch=0.01)          # sump pan
    for k in range(NC + 1):                                                                  # bearing cap ribs
        y = Y0 + k * PCH
        for sx in (-1, 1):
            cc.box((sx * 0.186, min(max(y, Y0 + 0.008), Y1 - 0.008), 0.255), (0.014, 0.018, 0.14), ch=0.003)
    for sx in (-1, 1):
        cc.box((sx * 0.178, (Y0 + Y1) / 2, 0.205), (0.024, Y1 - Y0 - 0.02, 0.02), ch=0.004)   # lower flange
    pan_bolts = P.get('CrankcaseBolts', 'aluminum_brushed', mirror=True)
    for y in np.linspace(Y0 + 0.03, Y1 - 0.03, 12):
        pan_bolts.bolts([(0.19, y, 0.205)], (1, 0, 0), r=0.0065, h=0.005)
    blk = P.get('Blocks', 'aluminum_dark', mirror=True, bevel=(0.002, 2))
    bbox(blk, 0.04, 0.147, -0.098, 0.098, Y0, Y1, ch=0.008, seg=2)
    for k in range(NC + 1):                                                                  # water jacket ribs
        y = min(max(Y0 + k * PCH, Y0 + 0.009), Y1 - 0.009)
        bbox(blk, 0.075, 0.147, 0.098, 0.106, y - 0.008, y + 0.008, ch=0.002)
    hd = P.get('Heads', 'aluminum_brushed', mirror=True, bevel=(0.002, 2))
    bbox(hd, 0.147, 0.238, -0.1, 0.1, Y0 - 0.004, Y1 + 0.004, ch=0.007, seg=2)
    gk = P.get('HeadGasket', 'steel_dark', mirror=True)
    bbox(gk, 0.1435, 0.1485, -0.104, 0.104, Y0 - 0.006, Y1 + 0.006)
    cv = P.get('CamCovers', 'Engine_Cover', mirror=True, bevel=(0.002, 2))
    bbox(cv, 0.238, 0.292, -0.083, 0.083, Y0 + 0.002, Y1 - 0.002, ch=0.012, seg=2)
    cvr = P.get('CamCoverRims', 'aluminum_polished', mirror=True)
    for t in (-0.0835, 0.0835):
        bbox(cvr, 0.2375, 0.2925, t - 0.003, t + 0.003, Y0 + 0.001, Y1 - 0.001, ch=0.001)
    hb = P.get('HeadBolts', 'steel_dark', mirror=True)
    exf = P.get('ExhaustFlanges', 'titanium', mirror=True)
    inf = P.get('IntakeFlanges', 'aluminum_polished', mirror=True)
    coil = P.get('Coils', 'plastic_black', mirror=True)
    coilc = P.get('CoilCaps', 'aluminum_polished', mirror=True)
    pl = P.get('Plugs', 'steel_dark', mirror=True)
    for y in CYL_Y:
        for dy in (-0.03, 0.03):
            for t in (-0.063, 0.063):
                hb.bolts([bp(0.292, t, y + dy)], A_, r=0.0058, h=0.005)
        # head side flange studs
        for dy in (-0.034, 0.034):
            hb.bolts([bp(0.19, 0.1, y + dy)], NO, r=0.0055, h=0.005)
        bbox(exf, 0.162, 0.218, 0.1, 0.106, y - 0.03, y + 0.03, ch=0.002)
        bbox(inf, 0.162, 0.218, -0.106, -0.1, y - 0.027, y + 0.027, ch=0.002)
        # coil on plug (outer half of the cam cover)
        bbox(coil, 0.292, 0.352, 0.032, 0.062, y - 0.016, y + 0.016, ch=0.003)
        bbox(coilc, 0.352, 0.358, 0.037, 0.057, y - 0.012, y + 0.012, ch=0.002)
        pl.cyl(bp(0.292, 0.047, y), bp(0.31, 0.047, y), 0.007, seg=8)

    # ------------------------------------------------------------ plaque on the cam cover, text
    pq = P.get('Plaque', 'aluminum_brushed', bevel=(0.0006, 1))
    pg = P.get('PlaqueGrooves', 'plastic_black')
    ylo, yhi = 1.005, 1.295
    for sgn in (1, -1):
        def mx(p):
            return np.array([sgn * p[0], p[1], p[2]])
        c0 = mx(bp(0.2945, 0.0, (ylo + yhi) / 2))
        Rm = np.stack([np.array([sgn * NO[0], 0, NO[2]]), EY, np.array([sgn * A_[0], 0, A_[2]])], axis=1)
        pq.box(c0, (0.112, yhi - ylo, 0.005), R=Rm, ch=0.001)
        for t in (-0.052, -0.040, 0.040, 0.052):
            pg.box(mx(bp(0.2975, t, (ylo + yhi) / 2)), (0.0016, yhi - ylo - 0.016, 0.0016), R=Rm)
        # lettering (left bank reads from the left side, right bank mirrored reading direction)
        up_dir = -np.array([sgn * NO[0], 0, NO[2]])
        read = EY if sgn == 1 else -EY
        norm = np.array([sgn * A_[0], 0, A_[2]])
        Rt = np.stack([read, up_dir, norm], axis=1)
        _text(coll, root, 'Engine_Plaque_Text_%s' % ('L' if sgn == 1 else 'R'), 'BUGATTI', 0.030,
              mx(bp(0.2975, 0.012, (ylo + yhi) / 2 + sgn * 0.0 + (0.012 if sgn == 1 else -0.012))), Rt, 'plastic_gloss')
        _text(coll, root, 'Engine_Plaque_V16_%s' % ('L' if sgn == 1 else 'R'), 'V16', 0.016,
              mx(bp(0.2975, -0.030, (ylo + yhi) / 2 + (0.0 if sgn == 1 else 0.0))), Rt, 'plastic_gloss', 0.0018)

    # ------------------------------------------------------------ airboxes, trunk, trumpets, runners
    ab = P.get('Airboxes', 'carbon_gloss', mirror=True, bevel=None, sharp=60.0)
    abt = P.get('AirboxTrim', 'aluminum_polished', mirror=True)
    trp = P.get('TrumpetRings', 'aluminum_brushed', mirror=True)
    trk = P.get('TrumpetCarbon', 'carbon_matte', mirror=True)
    run = P.get('Runners', 'aluminum_polished', mirror=True)
    tb_ = P.get('ThrottleBodies', 'aluminum_dark', mirror=True)
    tbp = P.get('ThrottleBodyPlates', 'titanium', mirror=True)
    inj = P.get('Injectors', 'gold', mirror=True)
    fr = P.get('FuelRails', 'aluminum_polished', mirror=True)
    loom = P.get('Looms', 'Hose_Black', mirror=True)
    brk = P.get('AirboxBrackets', 'aluminum_dark', mirror=True)

    def lobe(cx, cy, ax, ay, z0, z1, nz=7, np_=36, n=2.8, skew=0.0):
        rings = []
        prof = [(0.0, 0.93), (0.07, 1.0), (0.45, 1.0), (0.75, 0.93), (0.92, 0.78), (1.0, 0.55)]
        # build rings bottom to top, closing the bottom with a flat cap
        for (u, sc) in prof:
            z = z0 + (z1 - z0) * u
            ring = []
            for k in range(np_):
                th = 2 * math.pi * k / np_
                c, s = math.cos(th), math.sin(th)
                x = ax * sc * math.copysign(abs(c) ** (2 / n), c)
                y = ay * sc * math.copysign(abs(s) ** (2 / n), s)
                ring.append((cx + x + skew * (z - z0), cy + y, z))
            rings.append(ring)
        ab.rings(rings, caps=True)
    # fore and aft airbox lobes + connecting trunk
    lobe(0.235, 0.883, 0.145, 0.095, 0.605, 0.725, np_=int(36 * q))
    lobe(0.235, 1.413, 0.145, 0.095, 0.605, 0.725, np_=int(36 * q))
    # trunk along the inner side of the cam cover
    trunk = []
    ys = np.linspace(0.86, 1.44, 24)
    for yv in ys:
        pass
    ab.box_between((0.115, 0.88, 0.635), (0.115, 1.41, 0.635), 0.085, 0.05, ch=0.016, up=(0, 0, 1))
    # silver trumpet rings at the outer ends of the lobes (axis along y), like the press photo
    for (yc, d) in ((0.803, -1), (1.493, 1)):
        c0 = V((0.235, yc, 0.665))
        c1 = c0 + EY * d * 0.052
        trp.lathe(c0, c1, [(0.0, 0.050), (0.0, 0.062), (0.35, 0.064), (1.0, 0.060), (1.0, 0.047), (0.4, 0.049)], seg=int(28 * q))
        trk.lathe(c0 - EY * d * 0.002, c0 + EY * d * 0.02, [(0.0, 0.0), (0.0, 0.049), (1.0, 0.049), (1.0, 0.0)], seg=int(28 * q)) \
            if False else None
        # slotted cage windows around the ring
        for k in range(8):
            a = 2 * math.pi * k / 8
            p = c0 + EY * d * 0.026 + V((math.cos(a), 0, math.sin(a))) * 0.0645
            trk.box(p, (0.026, 0.026, 0.026), R=_rot_to(V((math.cos(a), 0, math.sin(a)))), ch=0.004)
        # inner funnel (dark)
        trk.lathe(c0 + EY * d * 0.02, c0 + EY * d * 0.052 + EY * d * 0.0, [(0.0, 0.048), (0.0, 0.040), (1.0, 0.030), (1.0, 0.020)], seg=int(24 * q)) if False else None
    # straps over the lobes
    rc = geo.Raycaster([o for o in bpy.data.objects if False]) if False else None
    for yc in (0.883, 1.413):
        for dy in (-0.045, 0.045):
            pts = []
            for xv in np.linspace(0.105, 0.365, 14):
                u = (xv - 0.235) / 0.145
                if abs(u) < 0.985:
                    zt = 0.605 + 0.12 * (1.0 - abs(u) ** 2.8) ** 0.5 * 0.96
                    pts.append((xv, yc + dy, zt + 0.0015))
            if len(pts) > 3:
                abt.sweep(np.array(pts), rect_profile(0.014, 0.003), up=(1, 0, 0), caps=True) if False else \
                    abt.tube(np.array(pts), 0.0035, seg=6)
    for yc in (0.883, 1.413):
        for xv in (0.14, 0.33):
            brk.box_between((xv, yc, 0.56), (xv, yc, 0.612), 0.03, 0.03, ch=0.003)
    # runners: 8 per bank from the port flange in the valley up into the trunk
    for i, y in enumerate(CYL_Y):
        port = bp(0.19, -0.106, y)
        pts = [port, port + V((-0.016, 0, 0.016)), V((0.049, y, 0.545)), V((0.062, y, 0.58)), V((0.092, y, 0.612)),
               V((0.112, y, 0.64))]
        run.tube(catmull(pts, 5), 0.0165, seg=TSEG, radii=None)
        tb_.cyl(V((0.058, y, 0.57)) - V((0.012, 0, 0.012)), V((0.058, y, 0.57)) + V((0.012, 0, 0.012)) * 1.2, 0.0235, seg=SEG)
        tbp.cyl(V((0.058, y, 0.57)) - V((0.002, 0, 0.002)), V((0.058, y, 0.57)) + V((0.002, 0, 0.002)), 0.0215, seg=SEG)
        inj.cyl(V((0.098, y, 0.552)), V((0.075, y, 0.584)), 0.0062, seg=8)
    fr.tube(np.array([(0.105, Y0 + 0.02, 0.552), (0.105, Y1 - 0.02, 0.552)]), 0.0075, seg=TSEG)
    for y in (Y0 + 0.02, Y1 - 0.02):
        fr.sphere((0.105, y, 0.552), 0.0105, seg=10, rings=6)
    loom.tube(catmull([(0.134, Y0 + 0.02, 0.575), (0.134, 1.0, 0.585), (0.134, 1.25, 0.585), (0.134, Y1 - 0.02, 0.575)], 8),
              0.0085, seg=8)
    # fuel line
    fr.tube(catmull([(0.105, Y1 - 0.02, 0.552), (0.115, Y1 + 0.03, 0.54), (0.15, Y1 + 0.06, 0.50)], 6), 0.0065, seg=8)

    # ------------------------------------------------------------ front accessory drive
    pul = P.get('Pulleys', 'aluminum_dark')
    plp = P.get('PulleyFaces', 'aluminum_polished')
    belt = P.get('Belt', 'rubber')
    acc = P.get('Accessories', 'aluminum_brushed', bevel=(0.0015, 1))
    fc = P.get('FrontCover', 'aluminum_dark', bevel=(0.002, 2))
    fc.box((0, Y0 - 0.0095, ZC + 0.03), (0.38, 0.019, 0.32), ch=0.012, seg=2)
    yb = 0.728
    pulleys = [(0.0, ZC, 0.074), (0.165, 0.455, 0.042), (-0.165, 0.445, 0.042), (0.125, 0.175, 0.046),
               (-0.115, 0.225, 0.034)]
    for (px, pz, pr) in pulleys:
        pul.cyl((px, yb - 0.014, pz), (px, yb + 0.014, pz), pr, seg=SEG * 2)
        plp.cyl((px, yb - 0.016, pz), (px, yb - 0.0135, pz), pr * 0.72, seg=SEG * 2)
        for sd in (-1, 1):
            pul.cyl((px, yb + sd * 0.014, pz), (px, yb + sd * 0.0195, pz), pr * 1.06, seg=SEG * 2)
    # crank damper and nose
    pul.cyl((0, 0.69, ZC), (0, 0.705, ZC), 0.088, seg=SEG * 2)
    plp.cyl((0, 0.672, ZC), (0, 0.69, ZC), 0.026, seg=12)
    plp.ring_bolts((0, 0.69, ZC), (0, -1, 0), 0.07, 8, r=0.0055, h=0.004)
    # belt
    loop = hull_loop([(px, pz, pr + 0.0035) for (px, pz, pr) in pulleys])
    path = np.column_stack([loop[:, 0], np.full(len(loop), yb), loop[:, 1]])
    belt.sweep(path, rect_profile(0.004, 0.026), up=(0, 1, 0), loop=True, caps=False)
    # accessory bodies (alternator, water pump, compressor) between pulleys and firewall
    acc.cyl((-0.165, 0.665, 0.445), (-0.165, yb - 0.014, 0.445), 0.058, seg=SEG)     # alternator
    acc.cyl((-0.165, 0.650, 0.445), (-0.165, 0.665, 0.445), 0.040, seg=SEG)
    acc.cyl((0.165, 0.67, 0.455), (0.165, yb - 0.014, 0.455), 0.052, seg=SEG)        # water pump
    acc.cyl((0.125, 0.655, 0.175), (0.125, yb - 0.014, 0.175), 0.060, seg=SEG)       # a/c compressor
    for k in range(6):
        acc.cyl((0.125, 0.66 + k * 0.009, 0.175), (0.125, 0.664 + k * 0.009, 0.175), 0.064, seg=SEG)
    # oil filter and oil cooler lines
    acc.cyl((-0.215, 0.66, 0.255), (-0.215, 0.745, 0.255), 0.040, seg=SEG)
    P.get('OilFilterCap', 'Anodised_Blue').cyl((-0.215, 0.645, 0.255), (-0.215, 0.66, 0.255), 0.044, seg=SEG)
    loom.tube(catmull([(-0.20, 0.755, 0.31), (-0.22, 0.74, 0.39), (-0.15, 0.735, 0.47), (-0.07, 0.736, 0.50)], 6), 0.0085, seg=8)
    P.get('Hoses', 'Hose_Black').tube(catmull([(0.165, 0.67, 0.50), (0.19, 0.67, 0.56), (0.20, 0.75, 0.55)], 6), 0.016, seg=TSEG)

    # ------------------------------------------------------------ exhaust: headers, collectors, silencers, tail pipes
    hdr = PX.get('Headers', 'titanium', mirror=True)
    flh = PX.get('HeaderFlanges', 'steel_dark', mirror=True)
    col = PX.get('Collectors', 'titanium', mirror=True)
    gold = PX.get('HeatShields', 'gold', mirror=True, bevel=(0.0008, 1))
    sil = PX.get('Silencers', 'aluminum_polished', mirror=True)
    silb = PX.get('SilencerBands', 'steel_dark', mirror=True)
    tip = PX.get('TailTips', 'aluminum_polished', mirror=True)
    tipd = PX.get('TailTipLiners', 'steel_dark', mirror=True)
    tpipe = PX.get('TailPipes', 'titanium', mirror=True)
    w3 = unit(V((0.906, 0, -0.423)))
    u3 = unit(V((0.423, 0, 0.906)))
    CA = V((0.40, 1.70, 0.43))
    CB = V((0.30, 1.70, 0.47))

    def rise(yv):
        return 0.16 * min(1.0, max(0.0, (yv - 1.36) / 0.30))
    for i, y in enumerate(CYL_Y):
        port = bp(0.19, 0.106, y)
        off = 0.035 + 0.030 * (NC - 1 - i)
        lane = lambda yy: port + w3 * off + V((0, yy - y, 0)) + V((0, 0, rise(yy)))
        grp = CA if i < 4 else CB
        k = i % 4
        ang = 2 * math.pi * k / 4 + 0.6
        spread = V((math.cos(ang), 0, math.sin(ang))) * 0.019
        q1 = lane(1.36)
        q3 = grp + spread - EY * 0.06
        q2 = (q1 * 0.45 + q3 * 0.55) + V((0, 0.0, 0.0))
        q2[1] = 1.52
        pts = [port, port + NO * 0.034, lane(y + 0.06), lane(y + 0.16), lane(min(y + 0.30, 1.30)), q1, q2, q3, grp + spread * 0.5]
        # drop duplicates in y ordering
        hdr.tube(catmull(pts, 5), 0.0155, seg=TSEG)
        flh.cyl(port - NO * 0.002, port + NO * 0.012, 0.0285, seg=12)
    # heat shield patches (gold foil) above the header bundle
    Rg = np.stack([w3, EY, u3], axis=1)
    for (ya, yb_) in ((0.80, 1.00), (1.12, 1.30)):
        c0 = bp(0.19, 0.106, 0) + w3 * 0.145 + u3 * 0.042 + V((0, (ya + yb_) / 2, 0))
        gold.box(c0, (0.31, yb_ - ya, 0.003), R=Rg, ch=0.001)
        for xo in np.linspace(-0.12, 0.12, 5):
            gold.box(c0 + w3 * xo + u3 * 0.002, (0.008, yb_ - ya - 0.012, 0.003), R=Rg)
    # collectors: cones merging the 4 pipes of each group
    for c, lbl in ((CA, 'A'), (CB, 'B')):
        col.cyl(c - EY * 0.075, c + EY * 0.0, 0.050, 0.040, seg=SEG)
        col.cyl(c, c + EY * 0.075, 0.040, seg=SEG)
    M = V((0.345, 1.80, 0.50))
    col.tube(catmull([CA + EY * 0.075, V((0.385, 1.78, 0.45)), M], 6), 0.036, seg=TSEG)
    col.tube(catmull([CB + EY * 0.075, V((0.31, 1.78, 0.485)), M], 6), 0.036, seg=TSEG)
    col.tube(catmull([M, V((0.34, 1.84, 0.515), ), V((0.335, 1.88, 0.52))], 6), 0.045, seg=TSEG)
    # round silver silencer / catalyst
    sc = V((0.335, 1.87, 0.52))
    sil.lathe(sc - EY * 0.05, sc + EY * 0.095, [(0.0, 0.04), (0.06, 0.07), (0.5, 0.082), (0.92, 0.078), (1.0, 0.055),
                                                 (1.0, 0.04), (0.95, 0.06), (0.5, 0.0745), (0.08, 0.063)], seg=int(32 * q))
    sil.cyl(sc + EY * 0.095, sc + EY * 0.1, 0.055, seg=int(24 * q))
    for yy in (-0.015, 0.03, 0.075):
        silb.cyl(sc + EY * yy, sc + EY * (yy + 0.008), 0.0845, seg=int(32 * q))
    # tail pipes: two per side, ending at y = 2.05
    outlets = []
    for xt in (0.30, 0.48):
        z_t = 0.495
        start = V((0.335 + (0.0 if xt < 0.4 else 0.03), 1.968, 0.52))
        pts = [start, V((0.335 + (xt - 0.335) * 0.35, 1.995, 0.515 - 0.004)), V((xt, 2.02, z_t)), V((xt, 2.04, z_t))]
        tpipe.tube(catmull(pts, 6), 0.036 if xt < 0.4 else 0.036, seg=TSEG)
        tip.lathe(V((xt, 1.995, z_t)), V((xt, 2.05, z_t)), [(0.0, 0.047), (0.0, 0.0535), (0.9, 0.0545), (1.0, 0.0535),
                                                            (1.0, 0.047), (0.2, 0.046)], seg=int(28 * q))
        tipd.cyl(V((xt, 2.01, z_t)), V((xt, 2.046, z_t)), 0.048, seg=int(24 * q), caps=False)
        outlets.append(dict(pos=(xt, 2.05, z_t), dia=0.113, axis=(0.0, 1.0, 0.0)))
    out_all = []
    for o in outlets:
        out_all.append(dict(o))
        out_all.append(dict(pos=(-o['pos'][0], o['pos'][1], o['pos'][2]), dia=o['dia'], axis=o['axis']))

    # ------------------------------------------------------------ gearbox: bell, 8-speed DCT casing, diff, rear e-motor
    gb = PG.get('Casing', 'aluminum_brushed', bevel=(0.0015, 1))
    gbd = PG.get('CasingDark', 'aluminum_dark', bevel=(0.0015, 1))
    gbb = PG.get('CasingBolts', 'steel_dark')
    em = PG.get('EMotor', 'aluminum_dark')
    emf = PG.get('EMotorFins', 'aluminum_brushed')
    emc = PG.get('EMotorHV', 'HV_Orange')
    mech = PG.get('Mechatronics', 'plastic_black', bevel=(0.002, 1))
    pa = V((0, 1.50, ZC))
    pb = V((0, 1.84, ZC))
    prof = [(0.0, 0.0), (0.0, 0.178), (0.05, 0.186), (0.27, 0.186), (0.30, 0.168), (0.40, 0.168), (0.43, 0.158),
            (0.97, 0.158), (1.0, 0.14), (1.0, 0.0)]
    gb.disc_stack(pa, pb, prof, seg=int(36 * q))
    for t in (0.075, 0.15, 0.225, 0.52, 0.64, 0.76, 0.88):                        # cooling / stiffening ribs
        r = 0.1885 if t < 0.28 else 0.163
        gbd.cyl(pa + (pb - pa) * t, pa + (pb - pa) * t + EY * 0.007, r, seg=int(36 * q))
    gbb.ring_bolts(pa + EY * 0.0, EY, 0.172, 14, r=0.0065, h=0.006)
    # bellhousing flange facing the engine
    gbd.cyl(pa - EY * 0.004, pa + EY * 0.012, 0.189, seg=int(36 * q))
    # diff drum across the casing and flanges for the half shafts
    gbd.cyl((-0.33, 1.60, 0.285), (0.33, 1.60, 0.285), 0.082, seg=int(24 * q))
    gb.box((0, 1.60, 0.285), (0.45, 0.16, 0.13), ch=0.014, seg=2)
    for sx in (-1, 1):
        gbd.cyl((sx * 0.30, 1.60, 0.285), (sx * 0.345, 1.60, 0.285), 0.065, seg=int(20 * q))
        gbb.ring_bolts((sx * 0.345, 1.60, 0.285), (sx, 0, 0), 0.05, 6, r=0.0055, h=0.005)
    # mounting ears
    for sx in (-1, 1):
        for y in (1.62, 1.80):
            gbd.box((sx * 0.13, y, 0.20), (0.07, 0.07, 0.07), ch=0.006)
    # longitudinal ribs on top and sides
    for sx in (-1, 1):
        gbd.box((sx * 0.12, 1.72, 0.40), (0.012, 0.22, 0.07), ch=0.003)
        gbd.box((sx * 0.158, 1.72, 0.30), (0.014, 0.22, 0.05), ch=0.003)
    # mechatronics block on top
    mech.box((0, 1.70, 0.485), (0.17, 0.14, 0.05), ch=0.008, seg=2)
    for k in range(5):
        gbd.box((-0.06 + k * 0.03, 1.70, 0.512), (0.012, 0.12, 0.008), ch=0.002)
    # rear e-motor: finned housing + end cap + HV connectors
    ya, yb2 = 1.84, 1.948
    em.cyl((0, ya, ZC), (0, yb2, ZC), 0.136, seg=int(32 * q))
    for k in range(9):
        y = ya + 0.008 + k * 0.011
        emf.cyl((0, y, ZC), (0, y + 0.0055, ZC), 0.1445, seg=int(32 * q))
    gbd.cyl((0, yb2, ZC), (0, yb2 + 0.004, ZC), 0.118, seg=int(32 * q))
    gbb.ring_bolts((0, yb2 + 0.004, ZC), EY, 0.10, 10, r=0.0065, h=0.005)
    for dx in (-0.045, 0.045):
        emc.cyl((dx, 1.89, ZC + 0.135), (dx, 1.89, ZC + 0.178), 0.0195, seg=14)
        emc.tube(catmull([(dx, 1.89, ZC + 0.175), (dx * 0.8, 1.84, 0.50), (dx * 0.6, 1.70, 0.545), (dx * 0.5, 1.62, 0.54)], 6),
                 0.0165, seg=TSEG)
    # engine to bell housing adapter ring
    gbd.cyl(pa - EY * 0.012, pa + EY * 0.0, 0.17, seg=int(32 * q))

    # ------------------------------------------------------------ lighting (engine bay accent)
    glow = P.get('GlowStrips', 'emit_engine', mirror=True)
    for xs in (0.095,):
        glow.box((xs, (0.88 + 1.41) / 2, 0.598), (0.008, 0.62, 0.006))
    for xs in (0.356,):
        glow.box((xs, 0.883, 0.62), (0.006, 0.12, 0.006))
        glow.box((xs, 1.413, 0.62), (0.006, 0.12, 0.006))
    _lamp(coll, root, 'Engine_Glow_L', (0.27, 1.15, 0.50), 30.0)
    _lamp(coll, root, 'Engine_Glow_R', (-0.27, 1.15, 0.50), 30.0)
    _lamp(coll, root, 'Engine_Glow_C', (0.0, 1.13, 0.62), 22.0)

    P.flush()
    PX.flush()
    PG.flush()
    ctx.data['engine'] = dict(
        crank_axis=dict(z=ZC, y_front=Y0, y_rear=Y1),
        exhaust_outlets=out_all,
        exhaust_tip_end_y=2.05,
        silencer_centres=[(0.335, 1.87, 0.52), (-0.335, 1.87, 0.52)],
        gearbox_y=(1.50, 1.948),
        intake_top_z=0.725,
        plaque_y=(ylo, yhi),
        roots=dict(engine='MOD_Engine', exhaust='MOD_Engine_Exhaust', gearbox='MOD_Engine_Gearbox'),
        glow_lamps=['Engine_Glow_L', 'Engine_Glow_R', 'Engine_Glow_C'],
    )


def _rot_to(n):
    """3x3 matrix whose local z axis is n."""
    u, v, w = frame_from_axis(n)
    return np.stack([u, v, w], axis=1)
