"""Chassis module: carbon monocoque tub, underfloor, front crash structure + e-axle,
rear subframe, double-wishbone suspension at four corners, radiators, plumbing.

Sub-roots (all children of MOD_Chassis):
  MOD_Chassis_Tub    monocoque, underfloor, tunnel, bulkheads
  MOD_Chassis_Front  crash structure, subframe, e-axle, radiators, front suspension
  MOD_Chassis_Rear   rear subframe, suspension, side radiators, plumbing
Left side is authored (+X); right side by mirroring.
"""
import importlib
import math
import numpy as np
import bpy

from tb import geo, mats, rig, spec
from tb.parts import chassis_lib as L
importlib.reload(L)
from tb.parts.chassis_lib import MeshBuilder, Parts, emit, V, unit, frame_from_axis, circle, rect_profile, \
    catmull, helix_path, rot_x, rot_y, rot_z

EX, EY, EZ = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
ZF = spec.TIRE_F['radius']
ZR = spec.TIRE_R['radius']
YF, YR = spec.Y_FRONT_AXLE, spec.Y_REAR_AXLE


def _materials():
    mats.custom('HV_Orange', base_color='#E5600B', roughness=0.42, specular=0.5)
    mats.custom('Anodised_Blue', base_color='#1B4F9C', metallic=0.85, roughness=0.28)
    mats.custom('Anodised_Gold', base_color='#C99A3C', metallic=0.9, roughness=0.3)
    mats.custom('Hose_Black', base_color=(0.012, 0.012, 0.013), roughness=0.5)
    mats.custom('Radiator_Core', base_color='#25272B', metallic=0.7, roughness=0.5)
    mats.custom('Spring_Red', base_color='#B01818', metallic=0.3, roughness=0.35, coat=0.6)


# ---------------------------------------------------------------- small assemblies
def bellows(mb, p0, p1, r0, r1, folds=5, seg=14):
    """CV boot: ridged cone from p0 to p1."""
    prof = [(0.0, r0 * 0.8)]
    n = folds * 2
    for k in range(n + 1):
        t = k / n
        r = (r0 + (r1 - r0) * t) * (1.0 if k % 2 == 0 else 0.78)
        prof.append((t, r))
    prof.append((1.0, r1 * 0.8))
    mb.disc_stack(p0, p1, prof, seg=seg)


def rod_end(mb, c, r=0.011, seg=8):
    mb.sphere(c, r, seg=seg, rings=5)


def wishbone_leg(mb, inner, outer, w=0.011, h=0.019, bow=0.0, seg=10, taper=0.78):
    inner, outer = V(inner), V(outer)
    mid = (inner + outer) / 2.0
    d = outer - inner
    side = unit(np.cross(d, EZ))
    mid = mid + side * bow
    path = catmull([inner, mid, outer], per=6)
    n = len(path)
    sc = np.linspace(1.0, taper, n)
    prof = geo.superellipse(w, h, 3.2, seg)
    mb.sweep(path, prof, scale=np.stack([sc, sc], axis=1), up=(0, 0, 1))


def wishbone(P_arm, P_hard, inners, outer, bow=0.012, w=0.011, h=0.019):
    for k, i in enumerate(inners):
        wishbone_leg(P_arm, i, outer, w=w, h=h, bow=bow * (1 if k == 0 else -1))
        P_hard.cyl(V(i) - EY * 0.028, V(i) + EY * 0.028, 0.0135, seg=12)       # bushing sleeve
        P_hard.cyl(V(i) - EY * 0.034, V(i) - EY * 0.028, 0.009, seg=8)
    # cross web at ~62% of the legs
    a = V(inners[0]) + (V(outer) - V(inners[0])) * 0.55
    b = V(inners[1]) + (V(outer) - V(inners[1])) * 0.55
    P_arm.box_between(a, b, 0.012, 0.012)
    P_hard.cyl(V(outer) - EZ * 0.02, V(outer) + EZ * 0.02, 0.0195, seg=14)


def spring(mb, p0, p1, radius, turns, wire=0.0032, per_turn=12, seg=6):
    path = helix_path(p0, p1, radius, turns, per_turn)
    mb.tube(path, wire, seg=seg)


def damper(P, p0, p1, r_body=0.019, spring_r=0.030, turns=7, q=1):
    """Coil-over: body tube from p0 (fixed end), rod to p1 (moving end), spring around."""
    p0, p1 = V(p0), V(p1)
    d = unit(p1 - p0)
    L_ = np.linalg.norm(p1 - p0)
    P['dmp_body'].cyl(p0, p0 + d * L_ * 0.50, r_body, seg=14)
    P['dmp_body'].cyl(p0 + d * L_ * 0.50, p0 + d * L_ * 0.54, r_body * 1.18, seg=14)
    P['dmp_rod'].cyl(p0 + d * L_ * 0.50, p1, 0.0075, seg=10)
    # reservoir canister, offset sideways
    side = unit(np.cross(d, EZ))
    rc = p0 + d * L_ * 0.18 + side * 0.040
    P['dmp_body'].cyl(rc, rc + d * 0.075, 0.014, seg=12)
    P['dmp_body'].cyl(p0 + d * L_ * 0.18, rc, 0.004, seg=6)
    # spring seats
    P['dmp_seat'].cyl(p0 + d * L_ * 0.12, p0 + d * L_ * 0.135, spring_r + 0.006, seg=16)
    P['dmp_seat'].cyl(p1 - d * L_ * 0.14, p1 - d * L_ * 0.125, spring_r + 0.006, seg=16)
    spring(P['spring'], p0 + d * L_ * 0.135, p1 - d * L_ * 0.14, spring_r, turns, per_turn=10 + 4 * q)
    # eyes
    for c in (p0, p1):
        P['dmp_body'].cyl(c - EY * 0.017, c + EY * 0.017, 0.012, seg=12)


# ================================================================= TUB
def build_tub(ctx, coll, root, final):
    P = Parts(coll, root, 'Chassis_')
    S = 1.5 if final else 1.0
    cg = P.get('Tub_Floor', 'carbon_gloss', bevel=(0.0015, 2))
    cs = P.get('Tub_Sills', 'carbon_gloss', mirror=True, bevel=(0.002, 2))
    cb = P.get('Tub_Bulkheads', 'carbon_gloss', bevel=(0.002, 2))
    cm = P.get('Tub_Ribs', 'carbon_matte', bevel=(0.001, 1))
    cms = P.get('Tub_RibsSide', 'carbon_matte', mirror=True, bevel=(0.001, 1))
    hw = P.get('Tub_Hardware', 'aluminum_brushed')
    hws = P.get('Tub_HardwareSide', 'aluminum_brushed', mirror=True)
    hv = P.get('Tub_HV', 'HV_Orange')
    gd = P.get('Tub_HeatShield', 'gold', bevel=(0.0008, 1))
    ff = P.get('Tub_FrontFloor', 'carbon_matte', bevel=(0.0015, 1))

    ZFL0, ZFL1 = 0.115, 0.125          # tub floor slab
    # --- floor slab (cabin)
    outline = [(-0.61, -1.20), (0.61, -1.20), (0.61, -0.95), (0.80, -0.95), (0.80, 0.625), (-0.80, 0.625),
               (-0.80, -0.95), (-0.61, -0.95)]
    cg.extrude_poly_z(outline, ZFL0, ZFL1)
    # --- front floor extension (under the subframe)
    ff.extrude_poly_z([(-0.50, -2.00), (0.50, -2.00), (0.61, -1.80), (0.61, -1.20), (-0.61, -1.20), (-0.61, -1.80)],
                      ZFL0, ZFL1)

    # --- side sills: tall and wide, sculpted section
    sill = [(0.66, 0.115), (0.792, 0.115), (0.792, 0.255), (0.766, 0.33), (0.71, 0.33), (0.685, 0.305), (0.66, 0.305)]
    # extrude along y: profile is (x, z)
    cs.extrude_poly_y(sill, -0.92, 0.625)
    # inner closing wall details: three longitudinal grooves as dark strips on the outer face
    for z in (0.17, 0.215):
        cms.box((0.794, -0.15, z), (0.004, 1.40, 0.012))
    for k in range(13):                                      # outer cross ribs
        y = -0.80 + k * 0.1
        cms.box((0.795, y, 0.2), (0.006, 0.018, 0.12), ch=0.002)
    # top stiffening ribs and bolt row on the sill top
    cms.box((0.745, -0.15, 0.328), (0.07, 1.45, 0.004))
    for k in range(18):
        hws.bolts([(0.72, -0.85 + k * 0.09, 0.326)], (0, 0, 1), r=0.0055, h=0.004)
        hws.bolts([(0.788, -0.85 + k * 0.09, 0.28)], (1, 0, 0), r=0.0055, h=0.004)
    # sill nose chamfer wedge + end plate
    cs.extrude_poly_z([(0.66, -0.92), (0.792, -0.92), (0.792, -0.80), (0.66, -0.78)], 0.115, 0.30)

    # --- front bulkhead (y -1.20 .. -1.16) and dash cross beam
    bh = [(-0.61, 0.115), (0.61, 0.115), (0.61, 0.50), (0.56, 0.60), (-0.56, 0.60), (-0.61, 0.50)]
    cb.extrude_poly_y(bh, -1.20, -1.16)
    cb.box_between((-0.60, -1.215, 0.60), (0.60, -1.215, 0.60), 0.085, 0.07, ch=0.012)
    for x in (-0.50, -0.33, -0.16, 0.0, 0.16, 0.33, 0.50):
        cm.box((x, -1.222, 0.34), (0.022, 0.026, 0.46), ch=0.003)
    cm.box((0, -1.222, 0.36), (1.10, 0.026, 0.022), ch=0.003)
    cm.box((0, -1.222, 0.17), (1.10, 0.026, 0.022), ch=0.003)

    # --- rear bulkhead / firewall (y 0.585 .. 0.625)
    fw = [(-0.80, 0.115), (0.80, 0.115), (0.80, 0.33), (0.66, 0.60), (0.56, 0.80), (-0.56, 0.80), (-0.66, 0.60),
          (-0.80, 0.33)]
    cb.extrude_poly_y(fw, 0.5851, 0.625)
    for x in (-0.62, -0.45, -0.30, -0.15, 0.0, 0.15, 0.30, 0.45, 0.62):
        cm.box((x, 0.633, 0.45), (0.022, 0.016, 0.62), ch=0.003)
    cm.box((0, 0.633, 0.30), (1.4, 0.016, 0.024), ch=0.003)
    cm.box((0, 0.633, 0.60), (1.0, 0.016, 0.024), ch=0.003)
    # shoulder beam on top of the firewall
    cb.box_between((-0.56, 0.613, 0.79), (0.56, 0.613, 0.79), 0.05, 0.04, ch=0.008)
    # gold heat shield on the engine side of the firewall
    gd.box((0, 0.6425, 0.45), (1.10, 0.004, 0.60), ch=0.0015)
    for x in np.linspace(-0.48, 0.48, 9):
        gd.box((x, 0.6465, 0.45), (0.010, 0.004, 0.56), ch=0.001)
    for x in (-0.50, -0.25, 0.0, 0.25, 0.50):
        for z in (0.2, 0.7):
            hw.bolts([(x, 0.6485, z)], (0, 1, 0), r=0.007, h=0.005)

    # --- centre tunnel (battery housing): half width 0.13 (+ flange to 0.14), top 0.385..0.395
    tun = [(-0.13, 0.125), (0.13, 0.125), (0.13, 0.32), (0.105, 0.386), (-0.105, 0.386), (-0.13, 0.32)]
    cb.extrude_poly_y(tun, -1.16, 0.585)
    cb.box((0, -0.29, 0.389), (0.18, 1.70, 0.008), ch=0.002)
    for k in range(12):                                      # lid cross ribs
        y = -1.05 + k * 0.145
        cm.box((0, y, 0.393), (0.205, 0.022, 0.008), ch=0.002)
    for k in range(12):                                      # side ribs
        y = -1.07 + k * 0.145
        cm.box((0, y + 0.07, 0.22), (0.272, 0.016, 0.10), ch=0.003)
    for sx in (-1, 1):
        for k in range(24):
            hw.bolts([(sx * 0.1315, -1.12 + k * 0.071, 0.145)], (0, 0, 1), r=0.0045, h=0.004)
    # end plates with HV connectors
    hw.box((0, -1.1635, 0.255), (0.24, 0.008, 0.20), ch=0.003)
    hw.box((0, 0.5895, 0.255), (0.24, 0.008, 0.20), ch=0.003)
    for sx in (-1, 1):
        for y0, d in ((-1.1675, -1), (0.5935, 1)):
            hv.cyl((sx * 0.06, y0, 0.28), (sx * 0.06, y0 + d * 0.035, 0.28), 0.020, seg=14)
    # HV cables to the front inverter and the rear motor (path published through ctx.data)
    for sx in (-1, 1):
        hv.tube(catmull([(sx * 0.06, -1.20, 0.28), (sx * 0.06, -1.27, 0.28), (sx * 0.045, -1.36, 0.30),
                         (sx * 0.035, -1.45, 0.31)], 6), 0.0165, seg=10)

    # --- structural flange line at the sill-to-floor joint and cross beams under the tub (hidden but real)
    ctx.data.setdefault('chassis', {})['tub'] = dict(floor_top=ZFL1, sill_inner_x=0.66, sill_top=0.33,
                                                      tunnel_half=0.14, tunnel_top=0.395)
    P.flush()
    return P.objs


def build_underfloor(coll, root):
    P = Parts(coll, root, 'Chassis_')
    u = P.get('Underfloor', 'underbody', bevel=(0.002, 2))
    half = [(0.0, -2.10), (0.56, -2.10), (0.61, -1.95), (0.61, -1.02), (0.80, -1.02), (0.80, 0.88), (0.72, 0.90), (0.0, 0.90)]
    full = half + [(-x, y) for (x, y) in reversed(half[1:-1])]
    u.extrude_poly_z(full, 0.1055, 0.1135)
    # embossed centre stiffeners and perimeter fastener discs (flush with the floor)
    st = P.get('Underfloor_Ribs', 'carbon_matte')
    for x in (-0.30, 0.30):
        st.box((x, -0.6, 0.1055), (0.05, 2.9, 0.0008), ch=0.0)
    fa = P.get('Underfloor_Bolts', 'aluminum_dark')
    for sx in (-1, 1):
        for y in np.linspace(-1.0, 0.82, 15):
            fa.cyl((sx * 0.76, y, 0.1052), (sx * 0.76, y, 0.1058), 0.0065, seg=8)
        for y in np.linspace(-2.04, -1.1, 8):
            fa.cyl((sx * 0.57, y, 0.1052), (sx * 0.57, y, 0.1058), 0.0065, seg=8)
    P.flush()
    return P.objs


# ================================================================= FRONT STRUCTURE
def build_front_structure(ctx, coll, root, final):
    P = Parts(coll, root, 'Chassis_F_')
    sg = 1.5 if final else 1.0
    seg = int(16 * sg)
    ad = P.get('Subframe', 'aluminum_dark', bevel=(0.0025, 2))
    ab = P.get('SubframeHardware', 'aluminum_brushed')
    cr = P.get('CrashStructure', 'aluminum_brushed', bevel=(0.002, 2))
    cf = P.get('CrashCarbon', 'carbon_matte', bevel=(0.002, 1))
    ml = P.get('E_Motors', 'aluminum_dark', mirror=True)
    mc = P.get('E_MotorCoils', 'Anodised_Gold', mirror=True)
    mg = P.get('E_Gearbox', 'aluminum_brushed', mirror=True, bevel=(0.0015, 1))
    mb_ = P.get('E_Inverter', 'aluminum_dark', bevel=(0.002, 2))
    hv = P.get('E_HVCables', 'HV_Orange', mirror=True)
    rad = P.get('Radiators', 'Radiator_Core', mirror=True)
    radt = P.get('RadiatorTanks', 'aluminum_brushed', mirror=True)
    hose = P.get('Hoses', 'Hose_Black', mirror=True)
    ds = P.get('Driveshafts', 'steel_dark', mirror=True)
    boot = P.get('CVBoots', 'rubber', mirror=True)
    cv = P.get('CVJoints', 'aluminum_polished', mirror=True)

    # ---- subframe: rails, cross members, braces
    for sx in (-1, 1):
        ad.box_between((sx * 0.26, -1.80, 0.17), (sx * 0.26, -1.20, 0.17), 0.075, 0.095, ch=0.012)
    ad.box_between((-0.26, -1.78, 0.17), (0.26, -1.78, 0.17), 0.075, 0.095, ch=0.012)
    ad.box_between((-0.26, -1.245, 0.17), (0.26, -1.245, 0.17), 0.075, 0.095, ch=0.012)
    # diagonals
    for sx in (-1, 1):
        ad.box_between((sx * 0.26, -1.78, 0.17), (0.0, -1.245, 0.17), 0.04, 0.05)
    # lower arm bracket lugs (fore/aft) from rails to the pickups
    for (py, ) in ((-1.68,), (-1.22,)):
        ad.box_between((0.26, py, 0.17), (0.31, py, 0.20), 0.07, 0.06, ch=0.006)
    # side towers: fore tower and aft tower carry the upper wishbone pickups
    for (y0, y1) in ((-1.72, -1.65), (-1.26, -1.20)):
        ad.box((0.40, (y0 + y1) / 2.0, 0.30), (0.12, abs(y1 - y0), 0.38), ch=0.008)
    ad.box((0.40, -1.685, 0.485), (0.12, 0.07, 0.02), ch=0.004)
    ad.box((0.40, -1.23, 0.50), (0.12, 0.06, 0.02), ch=0.004)
    # cross brace between the rocker pivots (front damper beam) + struts to the dash beam
    cf.box_between((-0.31, -1.39, 0.5425), (0.31, -1.39, 0.5425), 0.09, 0.085, ch=0.012)
    for sx in (-1, 1):
        cf.box_between((sx * 0.24, -1.39, 0.5425), (sx * 0.24, -1.225, 0.585), 0.05, 0.07, ch=0.006)
        ad.box_between((sx * 0.31, -1.39, 0.49), (sx * 0.40, -1.39, 0.49), 0.05, 0.05)
        ad.box_between((sx * 0.40, -1.39, 0.42), (sx * 0.40, -1.39, 0.49), 0.06, 0.06)
    # struts: from beam end down to the rail (keeps the beam supported)
    for sx in (-1, 1):
        ad.box_between((sx * 0.30, -1.39, 0.49), (sx * 0.26, -1.30, 0.20), 0.045, 0.045)
    # bolts on rails
    for sx in (-1, 1):
        for y in np.linspace(-1.76, -1.26, 6):
            ab.bolts([(sx * 0.26, y, 0.2175)], (0, 0, 1), r=0.0065, h=0.005)
    for x in np.linspace(-0.22, 0.22, 5):
        ab.bolts([(x, -1.78, 0.2175)], (0, 0, 1), r=0.0065, h=0.005)

    # ---- crash structure: bumper beam, crash cans, front splitter support
    cr.box_between((-0.68, -2.12, 0.34), (0.68, -2.12, 0.34), 0.07, 0.12, ch=0.012)
    for sx in (-1, 1):
        # crash can: tapered box with ribs (loft of two rect sections)
        for k, (yy, w, h) in enumerate([(-2.08, 0.17, 0.115), (-1.90, 0.15, 0.10)]):
            pass
        cr.box_between((sx * 0.55, -2.085, 0.34), (sx * 0.55, -1.84, 0.34), 0.15, 0.105, ch=0.01)
        for y in np.linspace(-2.04, -1.88, 4):
            cr.box((sx * 0.55, y, 0.34), (0.162, 0.012, 0.118), ch=0.003)
        cr.box((sx * 0.55, -1.835, 0.34), (0.18, 0.012, 0.14), ch=0.004)
        ad.box_between((sx * 0.55, -1.84, 0.34), (sx * 0.30, -1.79, 0.20), 0.07, 0.07, ch=0.006)
    cf.box_between((-0.60, -2.14, 0.20), (0.60, -2.14, 0.20), 0.05, 0.03, ch=0.004)     # splitter bracket
    for sx in (-1, 1):
        cf.box_between((sx * 0.45, -2.14, 0.20), (sx * 0.33, -1.80, 0.17), 0.04, 0.03)
    for x in np.linspace(-0.62, 0.62, 9):
        ab.bolts([(x, -2.158, 0.34)], (0, -1, 0), r=0.0065, h=0.005)

    # ---- front radiators: thin finned blocks leaning forward (top forward)
    lean = 22.0
    for (xc, wx) in ((0.31, 0.40),):
        c = V((xc, -1.965, 0.31))
        ang = lean
        R = rot_x(-ang)       # tilt: top towards -y
        n_f = 46
        # core
        rad.box(c, (wx, 0.034, 0.30), R=R, ch=0.002)
        for k in range(n_f):                               # fins visible on both faces
            z = -0.14 + 0.28 * k / (n_f - 1)
            rad.box(c + R @ V((0, 0.0215, z)), (wx - 0.004, 0.006, 0.0022), R=R)
            rad.box(c + R @ V((0, -0.0215, z)), (wx - 0.004, 0.006, 0.0022), R=R)
        # side tanks
        for sx2 in (-1, 1):
            radt.box(c + R @ V((sx2 * (wx / 2 + 0.014), 0, 0)), (0.034, 0.048, 0.31), R=R, ch=0.006, seg=2)
        radt.cyl(c + R @ V((wx / 2 + 0.032, 0, -0.10)), c + R @ V((wx / 2 + 0.07, 0, -0.10)), 0.017, seg=12)
        radt.cyl(c + R @ V((-wx / 2 - 0.032, 0, 0.10)), c + R @ V((-wx / 2 - 0.07, 0, 0.10)), 0.017, seg=12)
        # mounting brackets to the subframe cross member / crash structure
        ad.box_between(c + R @ V((-wx / 2, 0, -0.15)), (xc - wx / 2, -1.78, 0.2), 0.03, 0.03)
        ad.box_between(c + R @ V((wx / 2, 0, -0.15)), (xc + wx / 2, -1.78, 0.2), 0.03, 0.03)
        # hoses to the motors / inverter
        hose.tube(catmull([c + R @ V((wx / 2 + 0.07, 0, -0.10)), (0.58, -1.88, 0.20), (0.50, -1.74, 0.15),
                           (0.40, -1.62, 0.14), (0.33, -1.55, 0.20)], 6), 0.015, seg=10)
        hose.tube(catmull([c + R @ V((-wx / 2 - 0.07, 0, 0.10)), (0.06, -1.93, 0.44), (0.07, -1.80, 0.45),
                           (0.07, -1.66, 0.40), (0.07, -1.56, 0.30)], 6), 0.015, seg=10)
    ctx.data.setdefault('chassis', {})['front_radiator_center'] = (0.31, -1.965, 0.31)

    # ---- e-axle: two motors side by side, reduction gearboxes, inverter, driveshafts
    ym = -1.52
    zm = 0.30
    for x0, x1 in ((0.075, 0.345),):
        ml.cyl((x0, ym, zm), (x1, ym, zm), 0.086, seg=seg)
        for k in range(10):                                       # cooling fins
            xx = x0 + 0.02 + k * 0.024
            ml.cyl((xx, ym, zm), (xx + 0.008, ym, zm), 0.092, seg=seg)
        mc.cyl((x0 + 0.002, ym, zm), (x0 + 0.04, ym, zm), 0.078, seg=seg)       # copper end winding hint
        ml.cyl((x0 - 0.026, ym, zm), (x0, ym, zm), 0.06, seg=seg)               # end bell
        ml.cyl((0.345, ym, zm), (0.355, ym, zm), 0.098, seg=seg)
    # reduction gear case: two lobes (motor axis, output axis) + web
    ya, za = YF, ZF
    mg.cyl((0.345, ym, zm), (0.465, ym, zm), 0.100, seg=seg)
    mg.cyl((0.345, ya, za), (0.465, ya, za), 0.080, seg=seg)
    mg.box_between((0.405, ym, zm), (0.405, ya, za), 0.20, 0.12, ch=0.012)
    mg.cyl((0.465, ya, za), (0.482, ya, za), 0.055, seg=seg)
    for ang in range(0, 360, 60):
        a = math.radians(ang)
        mg.bolts([(0.466, ym + 0.082 * math.cos(a), zm + 0.082 * math.sin(a))], (1, 0, 0), r=0.006, h=0.005)
    # case ribs
    for k in range(3):
        mg.box((0.375 + k * 0.045, (ym + ya) / 2.0, (zm + za) / 2.0 + 0.045), (0.010, 0.22, 0.10), ch=0.002)
    # inverter / power electronics between the motors
    mb_.box((0.0, -1.52, 0.255), (0.15, 0.20, 0.15), ch=0.012, seg=2)
    mb_.box((0.0, -1.52, 0.345), (0.13, 0.17, 0.02), ch=0.004)
    for k in range(7):
        mb_.box((0.0, -1.60 + k * 0.027, 0.36), (0.12, 0.008, 0.016), ch=0.002)
    hv.tube(catmull([(0.04, -1.45, 0.31), (0.07, -1.40, 0.31), (0.12, -1.47, 0.36), (0.20, -1.60, 0.395),
                     (0.30, -1.60, 0.40)], 6), 0.0145, seg=10)
    hv.tube(catmull([(0.04, -1.58, 0.30), (0.10, -1.66, 0.29), (0.20, -1.67, 0.24), (0.29, -1.62, 0.28)], 6),
            0.0125, seg=10)
    # driveshafts + CV boots + outer joints (hub stub is on the upright)
    hub = V((0.86, ya, za))
    ds.cyl((0.50, ya, za), (0.71, ya, za), 0.0165, seg=12)
    boot_r = 0.047
    bellows(boot, V((0.482, ya, za)), V((0.575, ya, za)), boot_r, 0.030, folds=5, seg=int(14 * sg))
    cv.cyl((0.575, ya, za), (0.600, ya, za), 0.034, seg=14)
    bellows(boot, V((0.640, ya, za)), V((0.700, ya, za)), 0.036, 0.047, folds=3, seg=int(14 * sg))
    cv.cyl((0.700, ya, za), (0.745, ya, za), 0.050, seg=16)
    P.flush()
    return P.objs


# ================================================================= suspension corner
def build_corner(ctx, P, key, front, root_hinge=None):
    """Build the LEFT corner into the Parts P (keys per object). Returns nothing."""
    if front:
        hubc = V((0.86, YF, ZF))
        stub_end = 0.82
        lbj, ubj = V((0.72, YF, 0.22)), V((0.72, YF, 0.50))
        low_in = [V((0.30, YF - 0.31, 0.20)), V((0.30, YF + 0.15, 0.20))]
        up_in = [V((0.40, YF - 0.31, 0.47)), V((0.40, YF + 0.14, 0.47))]
    else:
        hubc = V((0.83, YR, ZR))
        stub_end = 0.79
        lbj, ubj = V((0.72, YR, 0.23)), V((0.72, YR, 0.52))
        low_in = [V((0.48, YR - 0.20, 0.20)), V((0.48, YR + 0.20, 0.20))]
        up_in = [V((0.50, YR - 0.17, 0.55)), V((0.50, YR + 0.17, 0.55))]
    return dict(hub=hubc, stub_end=stub_end, lbj=lbj, ubj=ubj, low_in=low_in, up_in=up_in)


def build_suspension_front(ctx, coll, root_front, final):
    sg = 1.5 if final else 1.0
    seg = int(16 * sg)
    ctxd = ctx.data.setdefault('chassis', {})
    # shared (static) parts of both sides
    PS = Parts(coll, root_front, 'Chassis_F_')
    arm = PS.get('Wishbones', 'aluminum_brushed', mirror=True)
    hard = PS.get('WishboneHardware', 'aluminum_dark', mirror=True)
    pr = PS.get('Pushrods', 'steel_dark', mirror=True)
    roc = PS.get('Rockers', 'aluminum_brushed', mirror=True, bevel=(0.0015, 1))
    dmp = {
        'dmp_body': PS.get('DamperBodies', 'Anodised_Blue', mirror=True),
        'dmp_rod': PS.get('DamperRods', 'chrome', mirror=True),
        'dmp_seat': PS.get('DamperSeats', 'aluminum_polished', mirror=True),
        'spring': PS.get('Springs', 'Spring_Red', mirror=True),
    }
    rack = PS.get('SteeringRack', 'aluminum_dark')
    rackb = PS.get('SteeringBoots', 'rubber')
    rodm = PS.get('TieRodInner', 'steel_dark')
    arb = PS.get('AntiRollBar', 'steel_dark')
    arbh = PS.get('AntiRollBarHardware', 'aluminum_brushed', mirror=True)
    c = build_corner(ctx, None, 'FL', True)
    lbj, ubj, low_in, up_in, hubc = c['lbj'], c['ubj'], c['low_in'], c['up_in'], c['hub']
    wishbone(arm, hard, low_in, lbj, bow=0.010)
    wishbone(arm, hard, up_in, ubj, bow=0.010, w=0.010, h=0.017)
    # pushrod through the opening of the upper wishbone to the rocker
    y_d = -1.39
    p_low = V((0.735, y_d, 0.265))
    rk_pivot = V((0.31, y_d, 0.565))
    rk_a = V((0.385, y_d, 0.530))
    rk_b = V((0.262, y_d, 0.625))
    pr.cyl(p_low, rk_a, 0.0085, seg=10)
    for e in (p_low, rk_a):
        rod_end(pr, e, 0.0125)
    tri = [(0.325, 0.585), (0.402, 0.535), (0.392, 0.512), (0.300, 0.532), (0.248, 0.605), (0.262, 0.642),
           (0.298, 0.630)]
    roc.extrude_poly_y(tri, y_d - 0.014, y_d + 0.014)
    roc.cyl((0.31, y_d - 0.03, 0.565), (0.31, y_d + 0.03, 0.565), 0.011, seg=12)
    hard.cyl((0.31, y_d - 0.045, 0.565), (0.31, y_d + 0.045, 0.565), 0.0055, seg=8)
    # coil-over lying along X (rocker -> centre cross beam)
    damper(dmp, V((0.045, y_d, 0.625)), rk_b, spring_r=0.025, q=int(sg))
    hard.box((0.045, y_d, 0.60), (0.034, 0.05, 0.05), ch=0.004)
    # anti-roll bar across the front, brackets and links to the lower arms
    arb.tube(catmull([(0.50, -1.60, 0.25), (0.50, -1.65, 0.27), (0.45, -1.76, 0.275), (0.30, -1.775, 0.275),
                      (0.0, -1.775, 0.275), (-0.30, -1.775, 0.275), (-0.45, -1.76, 0.275), (-0.50, -1.65, 0.27),
                      (-0.50, -1.60, 0.25)], 6), 0.0125, seg=12)
    arbh.box((0.20, -1.775, 0.2375), (0.05, 0.05, 0.08), ch=0.006)
    arbh.cyl((0.20, -1.805, 0.275), (0.20, -1.745, 0.275), 0.0185, seg=14)
    pr.cyl(V((0.50, -1.60, 0.25)), V((0.52, -1.50, 0.205)), 0.006, seg=8)
    rod_end(pr, V((0.50, -1.60, 0.25)), 0.012)
    rod_end(pr, V((0.52, -1.50, 0.205)), 0.012)
    # steering rack: housing, boots, inner rods; left-hand drive pinion on the +x side
    yr, zr = -1.25, 0.425
    rack.cyl((-0.215, yr, zr), (0.215, yr, zr), 0.0285, seg=seg)
    rack.cyl((0.14, yr, zr), (0.14, yr, zr + 0.065), 0.024, seg=14)                    # pinion housing
    rack.cyl((0.14, yr, zr + 0.065), (0.14, yr, zr + 0.09), 0.012, seg=10)
    rack.torus((0.14, yr, zr + 0.085), (0, 0, 1), 0.012, 0.004, 14, 6)
    for sx in (-1, 1):
        bellows(rackb, V((sx * 0.215, yr, zr)), V((sx * 0.285, yr, zr)), 0.034, 0.020, folds=4, seg=12)
        rodm.cyl((sx * 0.285, yr, zr), (sx * 0.33, yr, zr), 0.0085, seg=8)
        rod_end(rodm, V((sx * 0.33, yr, zr)), 0.012)
        # rack mounting clamps to the dash beam / bulkhead
    PS.get('RackClamps', 'aluminum_dark').box((0.18, yr + 0.035, zr), (0.045, 0.03, 0.075), ch=0.005)
    PS.get('RackClamps', 'aluminum_dark').box((-0.18, yr + 0.035, zr), (0.045, 0.03, 0.075), ch=0.005)
    PS.get('RackClamps', 'aluminum_dark').box((0.0, yr + 0.041, zr), (0.30, 0.012, 0.05), ch=0.004)

    # uprights (steered): per side separate object parented to a steer hinge at the kingpin axis
    objs = PS.flush()
    ups = []
    for side in ('L', 'R'):
        mir = (side == 'R')
        sgn = -1 if mir else 1
        U = Parts(coll, root_front, 'Chassis_F_')
        up = U.get('Upright_' + side, 'aluminum_brushed', bevel=(0.0015, 1))
        hb = U.get('HubStub_' + side, 'aluminum_polished')
        sb = U.get('UprightSteel_' + side, 'steel_dark')
        fb = U.get('UprightHardware_' + side, 'aluminum_dark')
        # upright body from lower to upper ball joint, a forged plate with a hub boss
        path = catmull([lbj + V((0.0, 0, 0.0)), V((0.738, YF + 0.004, 0.36)), ubj], per=6)
        up.sweep(path, geo.superellipse(0.034, 0.017, 3.0, 14),
                 scale=np.concatenate([np.linspace(0.9, 1.15, 9), np.linspace(1.15, 0.8, len(path) - 9)]),
                 up=(1, 0, 0))
        up.cyl((0.70, YF, ZF), (0.795, YF, ZF), 0.056, seg=seg)
        # webbing between body and boss
        up.box_between((0.735, YF, 0.255), (0.735, YF, 0.30), 0.075, 0.03, ch=0.004)
        up.box_between((0.735, YF, 0.41), (0.735, YF, 0.46), 0.06, 0.03, ch=0.004)
        # hub bearing flange and stub up to 4 cm inboard of the wheel plane
        hb.cyl((0.795, YF, ZF), (0.82, YF, ZF), 0.066, seg=seg)
        hb.cyl((0.78, YF, ZF), (0.82, YF, ZF), 0.030, seg=seg)
        # ball joint pins + dust boots
        for bj, d in ((lbj, -1), (ubj, 1)):
            sb.sphere(bj, 0.0185, seg=12, rings=7)
            sb.cyl(bj, bj + EZ * d * 0.045, 0.011, seg=8)
        # caliper mount lugs
        up.box((0.75, YF + 0.13, ZF + 0.06), (0.05, 0.035, 0.05), ch=0.005)
        up.box((0.75, YF - 0.13, ZF + 0.06), (0.05, 0.035, 0.05), ch=0.005)
        up.box_between((0.745, YF, ZF + 0.03), (0.75, YF + 0.13, ZF + 0.06), 0.03, 0.025)
        up.box_between((0.745, YF, ZF + 0.03), (0.75, YF - 0.13, ZF + 0.06), 0.03, 0.025)
        # steering arm and tie rod outer end, tie rod
        up.box_between((0.735, YF + 0.03, 0.40), (0.71, yr, zr), 0.028, 0.024, ch=0.004)
        rod_end(sb, V((0.71, yr, zr)), 0.0135)
        sb.cyl(V((0.33, yr, zr)), V((0.71, yr, zr)), 0.0085, seg=8)
        # collect + mirror manually for the right side
        for key, mb in list(U.b.items()):
            pass
        if mir:
            for key, mb in U.b.items():
                U.meta[key]['mirror'] = 'only'
        objs2 = U.flush()
        if not mir:
            pass
        # steering hinge per side at the kingpin axis
        pivot = ((-1 if mir else 1) * 0.72, YF, ZF)
        hinge = rig.hinge('Chassis_Steer_' + side, pivot, (0, 0, 1), 'steer', spec.MAX_STEER_DEG, parent_obj=root_front)
        # the right side tie rod / upright geometry already mirrored: sign of steer is the same
        for o in objs2:
            geo.parent(o, hinge)
        ups.extend(objs2)
    # the rack-side tie rod stub uses a static rod: nothing else to do
    return objs + ups


def build_suspension_rear(ctx, coll, root_rear, final):
    sg = 1.5 if final else 1.0
    seg = int(16 * sg)
    PS = Parts(coll, root_rear, 'Chassis_R_')
    arm = PS.get('Wishbones', 'aluminum_brushed', mirror=True)
    hard = PS.get('WishboneHardware', 'aluminum_dark', mirror=True)
    pr = PS.get('Pushrods', 'steel_dark', mirror=True)
    roc = PS.get('Rockers', 'aluminum_brushed', mirror=True, bevel=(0.0015, 1))
    dmp = {
        'dmp_body': PS.get('DamperBodies', 'Anodised_Blue', mirror=True),
        'dmp_rod': PS.get('DamperRods', 'chrome', mirror=True),
        'dmp_seat': PS.get('DamperSeats', 'aluminum_polished', mirror=True),
        'spring': PS.get('Springs', 'Spring_Red', mirror=True),
    }
    sub = PS.get('Subframe', 'aluminum_dark', mirror=True, bevel=(0.0025, 2))
    subc = PS.get('SubframeCentre', 'aluminum_dark', bevel=(0.0025, 2))
    carb = PS.get('DeckBeam', 'carbon_matte', bevel=(0.002, 1))
    arb = PS.get('AntiRollBar', 'steel_dark')
    ab = PS.get('SubframeHardware', 'aluminum_brushed', mirror=True)
    ds = PS.get('Driveshafts', 'steel_dark', mirror=True)
    boot = PS.get('CVBoots', 'rubber', mirror=True)
    cv = PS.get('CVJoints', 'aluminum_polished', mirror=True)
    rad = PS.get('Radiators', 'Radiator_Core', mirror=True)
    radt = PS.get('RadiatorTanks', 'aluminum_brushed', mirror=True)
    hose = PS.get('Hoses', 'Hose_Black', mirror=True)
    pipes = PS.get('CoolantPipes', 'aluminum_brushed', mirror=True)
    hvc = PS.get('HVCables', 'HV_Orange', mirror=True)
    c = build_corner(ctx, None, 'RL', False)
    lbj, ubj, low_in, up_in, hubc = c['lbj'], c['ubj'], c['low_in'], c['up_in'], c['hub']

    # ---- subframe: side rails, tower posts, cross members, engine / gearbox brackets
    sub.box_between((0.51, 0.66, 0.20), (0.51, 2.00, 0.20), 0.09, 0.14, ch=0.012)
    subc.box_between((-0.51, 0.69, 0.20), (0.51, 0.69, 0.20), 0.07, 0.12, ch=0.012)
    subc.box_between((-0.51, 1.99, 0.20), (0.51, 1.99, 0.20), 0.07, 0.12, ch=0.012)
    sub.box_between((0.51, 0.69, 0.20), (0.42, 0.655, 0.34), 0.04, 0.05)           # tie to the firewall
    for y in (YR - 0.17, YR + 0.17):
        sub.box_between((0.50, y, 0.27), (0.50, y, 0.575), 0.07, 0.06, ch=0.008)     # tower posts
    sub.box_between((0.50, YR - 0.17, 0.57), (0.50, YR + 0.17, 0.57), 0.07, 0.05, ch=0.008)
    for y in (YR - 0.20, YR + 0.20):
        sub.box_between((0.51, y, 0.16), (0.48, y, 0.20), 0.07, 0.06, ch=0.006)
    # lower arm bracket lugs
    for sx in (1,):
        for y in (YR - 0.20, YR + 0.20):
            hard.box((0.485, y, 0.20), (0.04, 0.06, 0.06), ch=0.004)
    # engine brackets (rails -> engine flank, under the exhaust lane)
    for y in (0.85, 1.15, 1.45):
        sub.box_between((0.47, y, 0.165), (0.20, y, 0.165), 0.05, 0.035, ch=0.004)
    for y in (1.62, 1.80):
        sub.box_between((0.47, y, 0.20), (0.20, y, 0.20), 0.06, 0.06, ch=0.005)
    # bolts
    for y in np.linspace(0.78, 1.95, 8):
        ab.bolts([(0.51, y, 0.2725)], (0, 0, 1), r=0.0065, h=0.005)
    # rear deck beam (carries the damper rockers): spans the engine bay at y = 1.40
    yb = YR + 0.03
    zb = 0.75
    carb.box_between((-0.455, yb, zb), (0.455, yb, zb), 0.075, 0.085, ch=0.012)
    for sx in (-1, 1):
        sub.box_between((sx * 0.48, yb, 0.57), (sx * 0.48, yb, zb - 0.02), 0.06, 0.06, ch=0.006)

    # ---- wishbones
    wishbone(arm, hard, low_in, lbj, bow=0.010)
    wishbone(arm, hard, up_in, ubj, bow=0.010, w=0.010, h=0.017)
    # pushrod + rocker + damper (along X, forward of the beam)
    y_d = YR - 0.04
    p_low = V((0.735, y_d, 0.285))
    rk_pivot = V((0.425, y_d, 0.665))
    rk_a = V((0.49, y_d, 0.625))
    rk_b = V((0.352, y_d, 0.705))
    pr.cyl(p_low, rk_a, 0.0085, seg=10)
    for e in (p_low, rk_a):
        rod_end(pr, e, 0.0125)
    tri = [(0.44, 0.69), (0.505, 0.637), (0.495, 0.612), (0.415, 0.640), (0.34, 0.70), (0.352, 0.724), (0.385, 0.715)]
    roc.extrude_poly_y(tri, y_d - 0.014, y_d + 0.014)
    roc.cyl((0.425, y_d - 0.03, 0.665), (0.425, y_d + 0.03, 0.665), 0.011, seg=12)
    hard.cyl((0.425, y_d - 0.05, 0.665), (0.425, y_d + 0.05, 0.665), 0.0055, seg=8)
    hard.box_between((0.425, yb, 0.70), (0.425, y_d + 0.02, 0.675), 0.03, 0.03)
    damper(dmp, V((0.075, y_d, 0.705)), rk_b, q=int(sg))
    hard.box_between((0.075, yb, 0.73), (0.075, y_d, 0.705), 0.03, 0.03)
    # toe link
    arm.tube(catmull([V((0.50, YR + 0.28, 0.32)), V((0.62, YR + 0.18, 0.325)), V((0.735, YR + 0.07, 0.33))], 6), 0.009, seg=10)
    rod_end(arm, V((0.50, YR + 0.28, 0.32)), 0.0125)
    rod_end(arm, V((0.735, YR + 0.07, 0.33)), 0.0125)
    hard.box((0.485, YR + 0.28, 0.32), (0.04, 0.04, 0.04), ch=0.004)
    # anti-roll bar behind the gearbox, links to the lower arms
    arb.tube(catmull([(0.56, 1.585, 0.215), (0.52, 1.70, 0.22), (0.50, 1.92, 0.22), (0.46, 2.05, 0.23),
                      (0.30, 2.06, 0.23), (-0.30, 2.06, 0.23), (-0.46, 2.05, 0.23), (-0.50, 1.92, 0.22),
                      (-0.52, 1.70, 0.22), (-0.56, 1.585, 0.215)], 6), 0.0125, seg=12)
    rod_end(pr, V((0.56, 1.585, 0.215)), 0.012)
    pr.cyl(V((0.56, 1.585, 0.215)), V((0.60, 1.462, 0.235)), 0.006, seg=8)
    rod_end(pr, V((0.60, 1.462, 0.235)), 0.012)
    ab.cyl((0.20, 2.035, 0.23), (0.20, 2.085, 0.23), 0.019, seg=14)

    # ---- driveshafts from the final-drive flange to the hub stub
    p_in = V((0.345, 1.60, 0.285))
    p_out = V((0.742, YR + 0.005, ZR))
    d = unit(p_out - p_in)
    Ls = np.linalg.norm(p_out - p_in)
    cv.cyl(p_in, p_in + d * 0.03, 0.045, seg=14)
    bellows(boot, p_in + d * 0.03, p_in + d * 0.115, 0.050, 0.032, folds=5, seg=int(14 * sg))
    ds.cyl(p_in + d * 0.115, p_out - d * 0.08, 0.0165, seg=12)
    bellows(boot, p_out - d * 0.075, p_out - d * 0.04, 0.035, 0.048, folds=3, seg=int(14 * sg))
    cv.cyl(p_out - d * 0.04, p_out, 0.050, seg=16)

    # ---- side radiators behind the side intakes (leaning: top inboard)
    ctr = V((0.715, 0.79, 0.43))
    R = rot_y(-18.0)               # lean: top towards -x ... verified by bounds check
    wy, hz = 0.235, 0.34
    rad.box(ctr, (0.040, wy, hz), R=R, ch=0.002)
    nf = 44
    for k in range(nf):
        z = -hz / 2 + 0.01 + (hz - 0.02) * k / (nf - 1)
        rad.box(ctr + R @ V((0.0235, 0, z)), (0.006, wy - 0.004, 0.0022), R=R)
        rad.box(ctr + R @ V((-0.0235, 0, z)), (0.006, wy - 0.004, 0.0022), R=R)
    for sy in (-1, 1):
        radt.box(ctr + R @ V((0, sy * (wy / 2 + 0.014), 0)), (0.05, 0.034, hz + 0.01), R=R, ch=0.006, seg=2)
    p_a = ctr + R @ V((-0.02, -(wy / 2 + 0.005), -0.10))
    p_b = ctr + R @ V((-0.02, wy / 2 + 0.005, 0.10))
    radt.cyl(p_a, p_a + R @ V((-0.05, 0, 0)), 0.017, seg=12)
    radt.cyl(p_b, p_b + R @ V((-0.05, 0, 0)), 0.017, seg=12)
    p_a = p_a + R @ V((-0.05, 0, 0))
    p_b = p_b + R @ V((-0.05, 0, 0))
    sub.box_between(ctr + R @ V((0, -wy / 2, -hz / 2)), (0.55, 0.69, 0.22), 0.03, 0.03)
    sub.box_between(ctr + R @ V((0, wy / 2, -hz / 2)), (0.55, 0.88, 0.20), 0.03, 0.03)
    # hoses: radiator -> engine water pump / head outlets
    hose.tube(catmull([p_a, (0.52, 0.665, 0.33), (0.42, 0.66, 0.37), (0.30, 0.69, 0.42),
                       (0.18, 0.72, 0.43)], 6), 0.0155, seg=10)
    hose.tube(catmull([p_b, (0.56, 0.92, 0.52), (0.48, 0.96, 0.54), (0.40, 0.93, 0.52),
                       (0.29, 0.88, 0.47)], 6), 0.0155, seg=10)
    # coolant pipes from the rear radiator down the subframe side to the front cross line
    # HV cable to the rear motor
    hvc.tube(catmull([(0.06, 0.60, 0.28), (0.07, 0.68, 0.24), (0.10, 0.80, 0.19), (0.20, 1.20, 0.155),
                      (0.16, 1.62, 0.18), (0.14, 1.78, 0.20)], 6), 0.0165, seg=10)
    objs = PS.flush()
    return objs


# ================================================================= module entry
def build(ctx):
    importlib.reload(L)
    _materials()
    final = ctx.final()
    coll = ctx.collection('Chassis')
    root = ctx.module_root('Chassis')
    r_tub = rig.module_root('Chassis_Tub')
    r_front = rig.module_root('Chassis_Front')
    r_rear = rig.module_root('Chassis_Rear')
    for r in (r_tub, r_front, r_rear):
        geo.parent(r, root)
        r.empty_display_size = 0.15
    ctx.data.setdefault('chassis', {})
    objs = []
    objs += build_tub(ctx, coll, r_tub, final)
    objs += build_underfloor(coll, r_tub)
    objs += build_front_structure(ctx, coll, r_front, final)
    objs += build_suspension_front(ctx, coll, r_front, final)
    objs += build_suspension_rear(ctx, coll, r_rear, final)
    ctx.data['chassis']['roots'] = dict(root='MOD_Chassis', tub='MOD_Chassis_Tub', front='MOD_Chassis_Front',
                                        rear='MOD_Chassis_Rear')
