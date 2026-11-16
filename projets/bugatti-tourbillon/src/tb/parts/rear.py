"""Rear end: light bar, concave panel, plate, exhaust finishers, diffuser, active wing, tail lamp.

Built after body + engine. Uses ctx.data['body'] anchors (tail_edge, wing_seat) and ray casts on Body_*.
See docs/progress/rear.md.
"""
import math
import numpy as np
import bpy
from mathutils import Vector
from tb import geo, mats, rig, spec
from tb.parts.rear_lib import S, MB, tube, fit_text, face_up

Y_TAIL = spec.Y_TAIL


def build(ctx):
    coll = ctx.collection('Rear')
    root = ctx.module_root('Rear')
    final = ctx.final()
    anchors = ctx.data.get('body') or {}
    made = []          # objects parented to the module root
    left = []          # (obj, name) to mirror

    def reg(ob, mat=None, bevel=None):
        if mat:
            mats.assign(ob, mat)
        if bevel:
            geo.mod_bevel(ob, width=bevel, segments=2)
        made.append(ob)
        return ob

    # ---------------------------------------------------------------- body ray casters
    bodies = [o for o in bpy.data.objects if o.name.startswith('Body_') and o.type == 'MESH'
              and not o.name.startswith(('Body_Recess', 'Body_Liner', 'Body_Door', 'Body_CLine_Door'))]
    rc = geo.Raycaster(bodies)
    rc_ns = geo.Raycaster([o for o in bodies if o.name != 'Body_Spine'])

    def ray_y(x, z):
        h = rc.cast((x, 4.0, z), (0, -1, 0))
        return None if (h is None or h[0].y < 1.6) else h[0].y

    def top_z(x, y, r=rc_ns):
        h = r.cast((x, y, 1.4), (0, 0, -1))
        return None if h is None else h[0].z

    # ---------------------------------------------------------------- light bar path
    te = np.array(anchors.get('tail_edge') or [[0, 2.218, .795], [0.72, 2.128, .798]])
    te_x, te_y = te[:, 0], te[:, 1]
    HX = 0.92
    xs = np.linspace(0.0, HX, 93)

    def zc_f(x):
        return 0.768 + 0.075 * S(0.62, 0.92, abs(x))

    def h_f(x):
        a = abs(x)
        hh = 0.040 + 0.034 * S(0.10, 0.55, a)
        return hh * (1.0 - S(0.70, 0.935, a)) ** 0.9 + 0.004

    ys = []
    for x in xs:
        if x <= te_x[-1]:
            ys.append(float(np.interp(x, te_x, te_y)))
        else:
            yy = ray_y(x, zc_f(x))
            ys.append(ys[-1] - 0.02 if yy is None else yy)
    ys = np.array(ys)
    k = np.ones(5) / 5.0
    ysm = np.convolve(np.pad(ys, 2, mode='edge'), k, mode='valid')
    ysm[xs < 0.05] = ys[xs < 0.05]
    ys = ysm
    ZC = np.array([zc_f(x) for x in xs])
    HH = np.array([h_f(x) for x in xs])

    def ye(x):
        return float(np.interp(abs(x), xs, ys))

    def frame(x):
        """position, tangent, outward normal of the bar centre line at x (signed)."""
        a = abs(x)
        y = float(np.interp(a, xs, ys))
        z = float(np.interp(a, xs, ZC))
        h = float(np.interp(a, xs, HH))
        d = float(np.interp(min(a + 0.004, HX), xs, ys) - np.interp(max(a - 0.004, 0), xs, ys))
        dx = min(a + 0.004, HX) - max(a - 0.004, 0)
        t = np.array([dx, d, 0.0])
        if x < 0:
            t = np.array([dx, -d, 0.0])
        t /= np.linalg.norm(t)
        n = np.array([-t[1], t[0], 0.0])
        return np.array([x, y, z]), t, n, h

    # ---- housing (dark smoked) and red cover
    X = np.linspace(-HX, HX, 121)
    zlo_pad = 0.0
    sec_h, sec_c = [], []
    for x in X:
        P, t, n, h = frame(x)
        lo, hi = P[2] - h / 2, P[2] + h / 2
        def pt(off, z):
            return P + n * off + np.array([0, 0, z - P[2]])
        sec_h.append([pt(0.002, lo), pt(0.002, hi), pt(-0.050, hi), pt(-0.050, lo)])
        sec_c.append([pt(0.0125, lo + 0.0005), pt(0.0125, hi - 0.0005), pt(0.0078, hi - 0.0005), pt(0.0078, lo + 0.0005)])
    housing = reg(tube('Rear_LightBar_Housing', sec_h, coll), 'glass_dark', 0.0015)
    sec_c_l = [s for s, x in zip(sec_c, X) if x > 0.20]
    sec_c_r = [s for s, x in zip(sec_c, X) if x < -0.20]
    cov_l = reg(tube('Rear_LightBar_Cover_L', sec_c_l, coll), 'glass_red')
    cov_r = reg(tube('Rear_LightBar_Cover_R', sec_c_r, coll), 'glass_red')

    # ---- LED cells along arclength
    pts = np.array([frame(x)[0] for x in X])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])
    L = arc[-1]
    NC = 50
    cells = MB()
    CW = 0.0185
    for i in range(NC):
        s = (i + 0.5) / NC * L
        x = float(np.interp(s, arc, X))
        if abs(x) < 0.185:
            continue
        P, t, n, h = frame(x)
        hh = max(h - 0.010, 0.004)
        hw = CW * (0.45 + 0.55 * (1 - S(0.80, 0.93, abs(x))))
        for sx in (-1, 1):
            pass
        ring = []
        for (a, b, c) in [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                          (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]:
            ring.append(P + t * a * hw + n * (0.0045 + 0.0035 * b) + np.array([0, 0, c * hh / 2]))
        idx = cells.add(ring)
        for f in [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            cells.f.append([idx[q] for q in f])
    cell_ob = cells.obj('Rear_LightBar_Cells', coll, 30)
    geo.recalc_normals(cell_ob)
    reg(cell_ob, 'emit_tail')

    # ---- BUGATTI letters (centre third), built once
    y0 = ye(0.0)
    letters = fit_text('Rear_LightBar_Letters', 'BUGATTI', 0.33, 0.029, 0.0035, coll)
    letters.data.transform(__import__('mathutils').Matrix(((-1, 0, 0, 0), (0, 0, 1, y0 + 0.0065), (0, 1, 0, zc_f(0.0)), (0, 0, 0, 1))))
    letters.data.update()
    geo.recalc_normals(letters)
    reg(letters, 'emit_brake')
    # dark backing strip behind the letters
    bk = geo.box('Rear_LightBar_LetterBack', (0.36, 0.012, 0.040), (0, y0 - 0.003, zc_f(0.0)), coll=coll)
    reg(bk, 'plastic_black')

    # ---- EB logo above the bar
    zt = top_z(0.0, y0 - 0.075) or 0.86
    eb = fit_text('Rear_Logo_EB', 'EB', 0.052, 0.028, 0.0012, coll)
    eb.data.transform(__import__('mathutils').Matrix(((-1, 0, 0, 0), (0, -1, 0, y0 - 0.075), (0, 0, 1, zt + 0.0006), (0, 0, 0, 1))))
    eb.data.update()
    geo.recalc_normals(eb)
    reg(eb, 'chrome')

    # ---------------------------------------------------------------- concave panel + wall + bumper block
    XP = np.linspace(-0.795, 0.795, 65)
    ZLOW = 0.568

    def zL(x):
        return 0.585 + 0.060 * S(0.30, 0.80, abs(x))

    def zT(x):
        return float(np.interp(abs(x), xs, ZC - HH / 2)) + 0.004

    def taper(x):
        return 1.0 - 0.72 * S(0.45, 0.80, abs(x))

    def y_top(x):
        return ye(x) - 0.016

    def y_bot(x):
        return y_top(x) - 0.105 * taper(x)

    def e(s):
        return 1.0 - (1.0 - s) ** 2

    def pan_y(x, z):
        a, b = zT(x), zL(x)
        s = min(1.0, max(0.0, (a - z) / (a - b)))
        return y_top(x) + (y_bot(x) - y_top(x)) * e(s)

    NV = 14
    rows_p, rows_w = [], []
    for x in XP:
        a, b = zT(x), zL(x)
        rp = []
        for j in range(NV + 1):
            s = j / NV
            rp.append((x, y_top(x) + (y_bot(x) - y_top(x)) * e(s), a + (b - a) * s))
        rows_p.append(rp)
        rw = []
        for j in range(5):
            s = j / 4
            rw.append((x, y_bot(x), b + (ZLOW - b) * s))
        rows_w.append(rw)
    panel = geo.grid_surface('Rear_Panel_Carbon', np.array(rows_p), coll=coll, smooth=True, sharp_angle=None, uv=True)
    wall = geo.grid_surface('Rear_Wall', np.array(rows_w), coll=coll, smooth=True, sharp_angle=None, uv=True)
    for ob in (panel, wall):
        geo.mod_solidify(ob, 0.012, offset=-1.0)
    # make normals face +Y (rearwards)
    for ob in (panel, wall):
        nsum = sum(p.normal.y * p.area for p in ob.data.polygons)
        if nsum < 0:
            geo.flip_normals(ob)
    reg(panel, 'carbon_matte')
    reg(wall, 'carbon_matte')

    # bumper block that carries the exhausts
    BZ0, BZ1 = 0.400, 0.575

    def y_f(x):
        return 2.250 - 0.105 * S(0.60, 0.82, abs(x))

    XB = np.linspace(-0.822, 0.822, 97)
    secs = []
    for x in XB:
        yi = y_bot(min(abs(x), 0.795)) - 0.03
        yf = y_f(x)
        secs.append([(x, yi, BZ0), (x, yf, BZ0), (x, yf, BZ1), (x, yi, BZ1)])
    block = tube('Rear_Bumper_Block', secs, coll, sharp=40)
    # exhaust cut-outs
    FX, FZ = 0.40, 0.50
    OUT = [(-0.205, 0.066), (0.205, 0.066), (0.205, -0.004), (0.132, -0.074), (-0.132, -0.074), (-0.205, -0.004)]
    OUT = [(u, v) for u, v in OUT]
    IN = [(u * 0.925, v * 0.80 - 0.004) for u, v in OUT]
    cut_ok = True
    for sx in (1, -1):
        cutter = geo.extrude_polygon('cut', [(sx * FX + u, FZ + v) for u, v in (OUT if sx > 0 else OUT[::-1])],
                                     0.30, plane='XZ', offset=2.00, coll=coll)
        try:
            geo.boolean(block, cutter, 'DIFFERENCE', 'EXACT')
        except Exception as ex:   # pragma: no cover
            print('[rear] boolean failed', ex)
            cut_ok = False
            bpy.data.objects.remove(cutter)
    block.data.update()
    geo.shade(block, True, 40.0)
    reg(block, 'carbon_gloss')
    # dark-grille faces: centre between exhausts and the outer pockets
    mats.assign_faces(block, 'plastic_black', lambda c, p: p.normal.y > 0.5 and (abs(c.x) < 0.185 or abs(c.x) > 0.625)
                      and BZ0 + 0.02 < c.z < BZ1 - 0.012)

    # ---------------------------------------------------------------- exhaust finishers (left, mirrored)
    def finisher(sx):
        mb = MB()
        yF, yB = Y_TAIL, Y_TAIL - 0.030
        yT = 2.075
        out_f = mb.add([(sx * FX + u, yF, FZ + v) for u, v in OUT])
        out_b = mb.add([(sx * FX + u, yB, FZ + v) for u, v in OUT])
        in_f = mb.add([(sx * FX + u, yF, FZ + v) for u, v in IN])
        in_t = mb.add([(sx * FX + u * 0.97, yT, FZ + v * 0.97 - 0.003) for u, v in IN])
        cx = sx * FX
        mb.strip(out_f, out_b, lambda c: (c[0] - cx, 0, c[2] - FZ))
        mb.strip(out_f, in_f, lambda c: (0, 1, 0))
        rim = mb.obj('Rear_Exhaust_Rim_' + ('L' if sx > 0 else 'R'), coll, 40)
        mb2 = MB()
        in_f2 = mb2.add([(sx * FX + u, yF - 0.001, FZ + v) for u, v in IN])
        in_t2 = mb2.add([(sx * FX + u * 0.97, yT, FZ + v * 0.97 - 0.003) for u, v in IN])
        mb2.strip(in_f2, in_t2, lambda c: (cx - c[0], 0, FZ - c[2]))
        tun = mb2.obj('Rear_Exhaust_Tunnel_' + ('L' if sx > 0 else 'R'), coll, 40)
        # vertical divider
        dv = geo.box('Rear_Exhaust_Divider_' + ('L' if sx > 0 else 'R'), (0.014, 0.16, 0.112),
                     (cx, yF - 0.08 + 0.0, FZ - 0.003), coll=coll)
        return rim, tun, dv

    rl, tl, dl = finisher(+1)
    rr, tr, dr = finisher(-1)
    for ob in (rl, rr):
        reg(ob, 'aluminum_polished', 0.0012)
    for ob in (tl, tr):
        reg(ob, 'titanium')
    for ob in (dl, dr):
        reg(ob, 'aluminum_polished')

    # ---------------------------------------------------------------- number plate + nameplate
    def pslab(name, x0, x1, z0, z1, oa, ob_, nz=6):
        secs = []
        for i in range(nz + 1):
            z = z0 + (z1 - z0) * i / nz
            xm = 0.5 * (x0 + x1)
            y = pan_y(xm, z) if True else 0
            secs.append([(x0, pan_y(x0, z) + oa, z), (x1, pan_y(x1, z) + oa, z),
                         (x1, pan_y(x1, z) - ob_, z), (x0, pan_y(x0, z) - ob_, z)])
        return tube(name, secs, coll, sharp=40)

    PZ0, PZ1 = 0.585, 0.685
    bars = []
    for (a, b, c, d) in [(-0.228, 0.228, PZ1, PZ1 + 0.012), (-0.228, 0.228, PZ0 - 0.012, PZ0),
                         (-0.228, -0.2155, PZ0, PZ1), (0.2155, 0.228, PZ0, PZ1)]:
        bars.append(pslab('bar', a, b, c, d, 0.011, 0.006, 2))
    bezel = geo.join(bars, 'Rear_Plate_Bezel')
    geo.link(bezel, coll)
    reg(bezel, 'carbon_gloss', 0.001)
    plate = pslab('Rear_Plate', -0.2155, 0.2155, PZ0, PZ1, 0.0065, 0.006, 4)
    reg(plate, 'aluminum_dark')
    yp = pan_y(0.0, 0.635) + 0.0075
    shear = 0.28
    nm = fit_text('Rear_Nameplate_Script', 'Tourbillon', 0.30, 0.050, 0.0007, coll, shear=0.0)
    # italic by shear in local XY (x += 0.28 y), then rotate to face +Y
    nm.data.transform(__import__('mathutils').Matrix(((1, shear, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))))
    nm.data.transform(__import__('mathutils').Matrix(((-1, 0, 0, 0), (0, 0, 1, yp), (0, 1, 0, 0.635), (0, 0, 0, 1))))
    nm.data.update()
    geo.recalc_normals(nm)
    reg(nm, 'chrome')

    # ---------------------------------------------------------------- grilles, reverse strip, reflectors
    def grille_patch(name, x0, x1, z0, z1):
        secs = []
        for i in range(2):
            x = (x0, x1)[i]
            for_row = []
        P = []
        for x in np.linspace(x0, x1, 9):
            P.append([(x, y_f(x) + 0.0035, z) for z in np.linspace(z0, z1, 4)])
        ob = geo.grid_surface(name, np.array(P), coll=coll, smooth=True, sharp_angle=None, uv=True)
        if sum(p.normal.y * p.area for p in ob.data.polygons) < 0:
            geo.flip_normals(ob)
        return ob

    g_c = grille_patch('Rear_Grille_C', -0.172, 0.172, BZ0 + 0.024, BZ1 - 0.016)
    reg(g_c, 'mesh_grille')
    g_l = grille_patch('Rear_Grille_L', 0.64, 0.80, BZ0 + 0.024, BZ1 - 0.016)
    reg(g_l, 'mesh_grille')
    left.append((g_l, 'Rear_Grille_R'))

    rev = geo.box('Rear_ReverseStrip', (0.20, 0.010, 0.011), (0, y_f(0) - 0.002, 0.412), coll=coll)
    reg(rev, 'emit_reverse')
    refl_mat = mats.custom('rear_reflector', base_color='#B01010', roughness=0.25, metallic=0.0)
    rf = geo.box('Rear_Reflector_L', (0.075, 0.010, 0.026), (0.735, y_f(0.735) - 0.003, 0.445), coll=coll)
    reg(rf, refl_mat)
    left.append((rf, 'Rear_Reflector_R'))

    # ---------------------------------------------------------------- diffuser
    eng = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(('Chassis', 'Engine'))]
    rc_e = geo.Raycaster(eng) if eng else None

    def ramp(y):
        return 0.118 + (BZ0 - 0.118) * S(1.00, 2.25, y)

    def xmax(y):
        return 0.60 + 0.22 * S(1.80, 1.88, y)

    cnt_clip = 0

    def floor_z(x, y):
        nonlocal cnt_clip
        z = ramp(y)
        if rc_e is not None:
            h = rc_e.cast((x, y, -0.5), (0, 0, 1), 3.0)
            if h is not None and h[0].z < 0.6 and h[0].z - 0.018 < z:
                cnt_clip += 1
                z = max(0.112, h[0].z - 0.018)
        return z

    YS = np.concatenate([np.linspace(0.90, 2.0, 34), np.linspace(2.0, 2.25, 14)[1:]])
    rows = []
    for y in YS:
        r = []
        for f in np.linspace(0.0, 1.0, 22):
            x = f * xmax(y)
            r.append((x, y, ramp(y) if f > 0.35 and False else floor_z(x, y)))
        rows.append(r)
    floor_l = geo.grid_surface('Rear_Diffuser_Floor_L', np.array(rows), coll=coll, smooth=True, sharp_angle=None, uv=True)
    face_up(floor_l)
    geo.mod_solidify(floor_l, 0.014, offset=-1.0)
    reg(floor_l, 'carbon_gloss', 0.0015)
    left.append((floor_l, 'Rear_Diffuser_Floor_R'))

    def strake(name, xc, thick, y_start, bottom=0.17, y_end=2.255):
        ytop = np.linspace(y_end, y_start, 18)
        top = [(y, floor_z(xc, y) - 0.003) for y in ytop]
        poly = [(y_start, bottom), (y_end, bottom)] + top
        # CCW in (y, z): bottom edge goes +y, rear goes up, top goes back (-y)
        ob = geo.extrude_polygon(name, poly, thick, plane='YZ', offset=xc - thick / 2, coll=coll, smooth=False)
        return ob

    def y_when(xc, zlevel):
        for y in np.linspace(0.9, 2.2, 66):
            if floor_z(xc, y) >= zlevel:
                return y
        return 2.0

    for i, (xc, th) in enumerate([(0.215, 0.020), (0.335, 0.016), (0.465, 0.016), (0.600, 0.020)]):
        ys0 = y_when(xc, 0.205)
        reg(strake('Rear_Diffuser_Strake%d_L' % (i + 1), xc, th, ys0), 'carbon_gloss', 0.0012)
        left.append((made[-1], 'Rear_Diffuser_Strake%d_R' % (i + 1)))
    # side plate
    ys0 = max(1.83, y_when(0.82, 0.19))
    sp = strake('Rear_Diffuser_Side_L', 0.812, 0.018, 1.83, bottom=0.19, y_end=2.20)
    reg(sp, 'carbon_gloss', 0.0012)
    left.append((sp, 'Rear_Diffuser_Side_R'))
    # central fin (symmetric, built once)
    fin = geo.extrude_polygon('Rear_Diffuser_Fin', [(1.93, 0.205), (1.93, 0.17), (2.262, 0.17), (2.262, 0.275), (2.20, 0.255)],
                              0.022, plane='YZ', offset=-0.011, coll=coll)
    reg(fin, 'carbon_gloss', 0.0012)

    # ---------------------------------------------------------------- active wing
    W = 0.66
    YLE = spec.WING['pivot'][1]
    NX, NS = 39, 22
    wx = np.linspace(-W, W, NX)
    secs = []
    zmax_dev = 0
    for x in wx:
        a = abs(x)
        yle = YLE + 0.045 * S(0.50, W, a)
        yte = ye(min(a, 0.9)) - 0.042 - 0.030 * S(0.5, W, a)
        top, bot = [], []
        for j in range(NS + 1):
            s = j / NS
            y = yle + (yte - yle) * s
            z = top_z(x, y)
            if z is None:
                z = top_z(x * 0.95, y) or 0.86
            thick = 0.0224 * (0.2969 * math.sqrt(s) - 0.126 * s - 0.3516 * s * s + 0.2843 * s ** 3 - 0.1015 * s ** 4) / 0.098 + 0.003 * s
            top.append((x, y, z + 0.012))
            bot.append((x, y, z + 0.012 - max(thick, 0.0015)))
        secs.append(top + bot[::-1])
    # smooth the top heights a little across x to hide the sampling noise
    arr = np.array(secs)
    zt_arr = arr[:, :NS + 1, 2].copy()
    for _ in range(2):
        zt_arr[1:-1] = 0.25 * zt_arr[:-2] + 0.5 * zt_arr[1:-1] + 0.25 * zt_arr[2:]
    dz = zt_arr - arr[:, :NS + 1, 2]
    arr[:, :NS + 1, 2] += dz
    arr[:, NS + 1:, 2] += dz[:, ::-1]
    blade = tube('Rear_Wing_Blade', arr, coll, sharp=50)
    geo.merge_by_distance(blade, 1e-5)
    mats.assign(blade, 'paint_secondary')
    mats.assign_faces(blade, 'carbon_gloss', lambda c, p: p.normal.z < -0.25)
    geo.mod_bevel(blade, width=0.0012, segments=2)
    hinge = rig.wing_hinge()
    geo.parent(blade, hinge)
    struts = []
    for sx in (1, -1):
        zs = top_z(sx * 0.42, 1.99) or 0.86
        st = geo.extrude_polygon('Rear_Wing_Strut_' + ('L' if sx > 0 else 'R'),
                                 [(1.955, zs - 0.250), (2.015, zs - 0.250), (2.015, zs - 0.012), (1.955, zs - 0.012)],
                                 0.016, plane='YZ', offset=sx * 0.42 - 0.008, coll=coll)
        mats.assign(st, 'carbon_gloss')
        geo.parent(st, hinge)
        struts.append(st)

    # ---------------------------------------------------------------- tail glow lamp
    ld = bpy.data.lights.new('Rear_TailGlow', 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = 1.5, 0.12
    ld.color = (1.0, 0.04, 0.02)
    ld.energy = 30.0
    lamp = bpy.data.objects.new('Rear_TailGlow', ld)
    geo.link(lamp, coll)
    lamp.location = (0.0, y0 + 0.07, 0.735)
    lamp.rotation_euler = Vector((0.0, 0.55, -0.83)).to_track_quat('-Z', 'Y').to_euler()
    made.append(lamp)
    rig.drive_light(lamp, 'taillights', 30.0)

    # ---------------------------------------------------------------- mirrors, parenting
    for ob, name in left:
        m = geo.mirror_copy(ob, name, coll)
        made.append(m)
    # extra matching of the right cover etc. is built directly. Parent everything.
    rig.adopt(made, root)
    for ob in made:
        if ob.type == 'MESH' and ob.name.startswith('Rear_Diffuser_Floor'):
            pass
    ctx.data['rear'] = dict(light_bar_y0=y0, y_f0=y_f(0.0), plate_y=yp, floor_clipped=cnt_clip, cut_ok=cut_ok)
    print('[rear] floor clipped samples:', cnt_clip, 'cut_ok', cut_ok, 'bar y0', round(y0, 3))
