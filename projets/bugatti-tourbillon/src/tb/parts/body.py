"""Body shell of the Bugatti Tourbillon (painted / carbon outer surfaces + glazing).

Technique (see body_lib.py): one parametric half skin S(s, t) through nine
longitudinal rails (C centreline, V, P roof edge / buttress ridge, H, K fender
crown / belt shoulder, W max width, L, B sill edge, U underside). Column s = S0
is the outline of the horseshoe opening, column s = S1 the tail edge + rear
opening. Panels are regions of that skin (signed functions in side / plan /
front projections), meshed with snapped clean edges, shrunk by half the panel
gap, given thickness by a solidify modifier whose rim / inner face use a dark
material (dark shut lines). Openings are holes with recessed dark walls.

Rail knots: blueprint (refs/A3_blueprint.png, 199.5 px/m, out/scripts/body/measure.py)
plus docs/REFERENCE.md section 4. Numeric check: out/scripts/body/check.py.
"""
import math
import numpy as np

from tb import geo, mats, rig, spec
from tb.parts import body_lib as BL

S0 = -2.40          # first column: outline of the horseshoe opening
S1 = 2.27           # last column: tail edge + outline of the rear opening
GAP = 0.0022        # half panel gap (m)
YF, ZF = spec.Y_FRONT_AXLE, spec.WHEELS['FL'][2]
YR, ZR = spec.Y_REAR_AXLE, spec.WHEELS['RL'][2]


# =====================================================================
# rails
# =====================================================================
def rails():
    R = []
    sp3 = ('spline', 'spline', 'pchip')
    R.append(BL.Rail('C', [
        (-2.40, 0.0, 0.590, -2.394), (-2.33, 0.0, 0.612), (-2.20, 0.0, 0.640), (-2.00, 0.0, 0.660),
        (-1.80, 0.0, 0.702), (-1.65, 0.0, 0.762), (-1.54, 0.0, 0.808), (-1.40, 0.0, 0.856),
        (-1.20, 0.0, 0.918), (-1.00, 0.0, 0.978), (-0.80, 0.0, 1.040), (-0.63, 0.0, 1.090),
        (-0.45, 0.0, 1.135), (-0.25, 0.0, 1.163), (-0.06, 0.0, 1.179), (0.17, 0.0, 1.181),
        (0.40, 0.0, 1.170), (0.636, 0.0, 1.140), (0.87, 0.0, 1.092), (1.10, 0.0, 1.043),
        (1.34, 0.0, 0.985), (1.57, 0.0, 0.940), (1.80, 0.0, 0.908), (2.04, 0.0, 0.862),
        (2.18, 0.0, 0.822), (2.27, 0.0, 0.795, 2.218)], kind=sp3))
    R.append(BL.Rail('V', [
        (-2.40, 0.170, 0.580, -2.394), (-2.33, 0.200, 0.600, -2.345), (-2.20, 0.250, 0.632), (-2.00, 0.330, 0.660),
        (-1.80, 0.420, 0.700), (-1.60, 0.510, 0.752), (-1.40, 0.590, 0.822), (-1.20, 0.625, 0.876),
        (-1.00, 0.610, 0.935), (-0.80, 0.585, 0.995), (-0.63, 0.570, 1.045), (-0.40, 0.555, 1.100),
        (-0.10, 0.545, 1.138), (0.20, 0.535, 1.140), (0.45, 0.450, 1.130), (0.70, 0.310, 1.065),
        (0.95, 0.275, 1.000), (1.20, 0.270, 0.952), (1.45, 0.270, 0.915), (1.70, 0.270, 0.885),
        (1.95, 0.270, 0.852), (2.12, 0.270, 0.820), (2.27, 0.270, 0.792, 2.214)], kind=sp3))
    R.append(BL.Rail('P', [
        (-2.40, 0.248, 0.545, -2.396), (-2.33, 0.310, 0.585, -2.355), (-2.20, 0.450, 0.622, -2.23),
        (-2.00, 0.540, 0.640), (-1.80, 0.610, 0.678), (-1.60, 0.665, 0.738), (-1.40, 0.700, 0.805),
        (-1.20, 0.715, 0.872), (-1.00, 0.700, 0.925), (-0.80, 0.680, 0.980), (-0.63, 0.666, 1.025),
        (-0.40, 0.652, 1.075), (-0.10, 0.646, 1.100), (0.20, 0.640, 1.105), (0.45, 0.615, 1.095),
        (0.70, 0.560, 1.075), (0.95, 0.530, 1.045), (1.20, 0.520, 1.005), (1.45, 0.510, 0.965),
        (1.70, 0.500, 0.930), (1.95, 0.490, 0.890), (2.12, 0.480, 0.845), (2.27, 0.470, 0.800, 2.200)]))
    R.append(BL.Rail('H', [
        (-2.40, 0.280, 0.475, -2.398), (-2.33, 0.400, 0.555, -2.345), (-2.20, 0.620, 0.625, -2.23),
        (-2.00, 0.720, 0.708), (-1.80, 0.765, 0.765), (-1.60, 0.780, 0.805), (-1.40, 0.785, 0.835),
        (-1.20, 0.778, 0.860), (-1.00, 0.785, 0.885), (-0.80, 0.770, 0.920), (-0.63, 0.760, 0.950),
        (-0.40, 0.752, 0.975), (-0.10, 0.750, 0.980), (0.20, 0.748, 0.980), (0.45, 0.740, 0.970),
        (0.70, 0.720, 0.950), (0.95, 0.690, 0.930), (1.20, 0.665, 0.915), (1.45, 0.645, 0.900),
        (1.70, 0.625, 0.880), (1.95, 0.610, 0.860), (2.12, 0.600, 0.825), (2.27, 0.620, 0.792, 2.170)],
        tension=[(-2.4, 0.7), (-1.6, 0.45), (-1.1, 0.6), (-0.6, 1.0), (2.27, 1.0)]))
    R.append(BL.Rail('K', [
        (-2.40, 0.290, 0.415, -2.400), (-2.30, 0.460, 0.575, -2.280), (-2.15, 0.690, 0.680, -2.140),
        (-2.00, 0.840, 0.745), (-1.80, 0.890, 0.790), (-1.60, 0.900, 0.825), (-1.40, 0.895, 0.835),
        (-1.20, 0.870, 0.840), (-1.00, 0.855, 0.843), (-0.80, 0.845, 0.840), (-0.50, 0.835, 0.838),
        (-0.20, 0.830, 0.837), (0.10, 0.830, 0.838), (0.35, 0.835, 0.845), (0.60, 0.860, 0.860),
        (0.85, 0.885, 0.875), (1.10, 0.905, 0.890), (1.35, 0.915, 0.910), (1.60, 0.905, 0.920),
        (1.85, 0.850, 0.905), (2.05, 0.810, 0.865, 2.050), (2.27, 0.760, 0.815, 2.110)],
        tension=[(-2.4, 0.75), (-1.8, 0.6), (-1.2, 0.65), (-0.6, 0.8), (1.0, 0.9), (2.27, 1.0)]))
    R.append(BL.Rail('W', [
        (-2.40, 0.288, 0.355, -2.400), (-2.30, 0.410, 0.400, -2.280), (-2.20, 0.600, 0.445, -2.190),
        (-2.10, 0.790, 0.480, -2.100), (-2.00, 0.895, 0.510, -2.000), (-1.90, 0.970, 0.535),
        (-1.80, 1.012, 0.585), (-1.50, 1.031, 0.622), (-1.10, 1.012, 0.612),
        (-0.60, 0.990, 0.602), (-0.05, 0.976, 0.610), (0.45, 0.928, 0.645), (0.95, 1.010, 0.702),
        (1.37, 1.030, 0.720), (1.65, 1.022, 0.713),
        (1.80, 0.960, 0.700), (1.90, 0.900, 0.690), (2.00, 0.850, 0.690, 2.000), (2.27, 0.790, 0.700, 2.095)]))
    R.append(BL.Rail('L', [
        (-2.40, 0.280, 0.265, -2.400), (-2.30, 0.440, 0.250, -2.300), (-2.15, 0.700, 0.260, -2.150),
        (-2.00, 0.885, 0.270, -2.000), (-1.85, 0.985, 0.280, -1.850), (-1.60, 1.012, 0.300),
        (-1.37, 1.005, 0.320), (-0.90, 0.980, 0.345), (-0.30, 0.966, 0.350),
        (0.45, 0.927, 0.360), (1.10, 1.000, 0.370),
        (1.37, 1.005, 0.370), (1.70, 0.985, 0.370), (1.90, 0.880, 0.400), (2.05, 0.790, 0.430, 2.030),
        (2.27, 0.700, 0.440, 2.100)]))
    R.append(BL.Rail('B', [
        (-2.40, 0.200, 0.215, -2.400), (-2.30, 0.400, 0.190, -2.320), (-2.15, 0.670, 0.180, -2.160),
        (-2.00, 0.860, 0.180, -2.010), (-1.85, 0.955, 0.180, -1.850), (-1.60, 0.975, 0.180),
        (-1.37, 0.975, 0.170), (-1.10, 0.960, 0.150), (-0.80, 0.945, 0.135), (0.00, 0.930, 0.130), (0.40, 0.915, 0.133),
        (0.80, 0.940, 0.140), (1.10, 0.970, 0.170), (1.37, 0.980, 0.200), (1.70, 0.960, 0.240),
        (1.90, 0.870, 0.260), (2.05, 0.740, 0.290, 2.010), (2.27, 0.580, 0.300, 2.080)]))
    R.append(BL.Rail('U', [
        (-2.40, 0.000, 0.205, -2.400), (-2.30, 0.370, 0.170, -2.330), (-2.15, 0.640, 0.160, -2.165),
        (-2.00, 0.830, 0.160, -2.015), (-1.85, 0.915, 0.160, -1.850), (-1.37, 0.935, 0.155),
        (-1.10, 0.915, 0.135), (-0.80, 0.900, 0.120), (0.00, 0.895, 0.115), (0.80, 0.905, 0.125),
        (1.37, 0.940, 0.190), (1.90, 0.850, 0.250), (2.05, 0.660, 0.265, 1.990), (2.27, 0.380, 0.270, 2.050)]))
    return R


def make_skin():
    return BL.Skin(rails(), S0, S1)


# =====================================================================
# shut lines / feature curves (left side, +X)
# =====================================================================
def _pi(xs, ys):
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    return BL.Pchip1D(xs, ys)


# door + front-fender rear edge in side view: y as a function of z
y_front = _pi([0.20, 0.40, 0.55, 0.65, 0.72, 0.76, 0.84, 1.00, 1.10, 1.25],
              [-0.935, -0.935, -0.982, -1.060, -1.115, -1.120, -1.020, -0.760, -0.600, -0.420])
# C-line lower leg = door bottom / sill top: z as a function of y
cl_low = _pi([-1.20, -0.93, -0.50, 0.00, 0.30, 0.60, 1.00], [0.272, 0.272, 0.287, 0.302, 0.330, 0.360, 0.360])
# door top edge (roof strip) in plan: x as a function of y
x_strip = _pi([-1.30, -0.90, -0.60, -0.20, 0.20, 0.55], [0.660, 0.620, 0.578, 0.548, 0.505, 0.400])
# windshield: base (cowl) in plan, side edge in plan
def y_cowl(x):
    return -1.545 + 0.29 * (np.asarray(x) / 0.655) ** 2
x_ws = _pi([-1.26, -0.63], [0.655, 0.552])
# glass roof canopy outer edge in plan
x_can = _pi([-0.63, -0.20, 0.20, 0.45, 0.60], [0.440, 0.430, 0.395, 0.300, 0.120])
# bonnet centre V edge in plan
x_v = _pi([-2.40, -2.20, -1.80, -1.50, -1.30, -1.20], [0.120, 0.150, 0.270, 0.440, 0.600, 0.680])
# engine-deck edge (inside the buttress ridge) in plan
x_bi = _pi([0.55, 1.00, 1.50, 1.98], [0.430, 0.480, 0.480, 0.460])


def door_rear(z):
    (y0, z0), (y1, z1) = spec.DOOR_REAR_CUT
    t = np.clip((np.asarray(z) - z0) / (z1 - z0), 0.0, 1.0)
    return y0 + (y1 - y0) * t


# C-line static path (lower leg + rear leg), side view (y, z)
CLINE_SIDE = [(-0.935, 0.272), (-0.70, 0.279), (-0.40, 0.290), (0.00, 0.302), (0.30, 0.330), (0.52, 0.405),
              (0.68, 0.540), (0.770, 0.720), (0.775, 0.880), (0.705, 1.000), (0.600, 1.075), (0.500, 1.110)]
# side window opening (DLO) in side view, further clipped by the door frame
DLO = [(-1.10, 0.846), (-0.20, 0.848), (0.20, 0.862), (0.36, 0.900), (0.44, 0.975), (0.47, 1.06),
       (0.47, 1.30), (-1.20, 1.30)]
# openings
INTAKE_F = [(0.42, 0.440), (0.62, 0.452), (0.79, 0.442), (0.875, 0.405), (0.895, 0.310), (0.865, 0.238),
            (0.62, 0.222), (0.43, 0.228), (0.395, 0.270), (0.395, 0.400)]
SIDE_INTAKE = [(0.14, 0.42), (0.45, 0.44), (0.62, 0.55), (0.69, 0.70), (0.66, 0.83), (0.50, 0.875), (0.36, 0.86)]
SCOOP = [(0.07, 0.76), (0.40, 0.78), (0.43, 0.86), (0.43, 1.52), (0.40, 1.60), (0.07, 1.62), (0.05, 1.55),
         (0.05, 0.83)]


def headlight_poly():  # noqa (defined below OPENINGS uses it lazily)
    """Slim lozenge in front view (x, z): inner end lower, tapered ends."""
    a = np.array([0.510, 0.590])
    b = np.array([0.880, 0.640])
    pts_top, pts_bot = [], []
    for u in np.linspace(0, 1, 9):
        c = a + (b - a) * u
        h = 0.025 * math.sin(math.pi * (0.08 + 0.84 * u)) ** 0.45
        pts_top.append((c[0], c[1] + h))
        pts_bot.append((c[0], c[1] - h * 0.85))
    return np.array(pts_top + pts_bot[::-1])


OPENINGS = [
    # key, polygon, projection plane, s window, t window, seed facing (see Inverter)
    ('intake_F', INTAKE_F, 'front', (-2.40, -1.90), (4.0, 8.4), (1, -0.4)),
    ('headlight', None, 'front', (-2.38, -1.95), (2.6, 5.4), (1, -0.25)),
    ('side_intake', SIDE_INTAKE, 'side', (-0.20, 1.00), (3.5, 7.2), (0, 0.5)),
    ('scoop', SCOOP, 'plan', (0.60, 1.80), (0.0, 2.6), (2, 0.5)),
]


# =====================================================================
# regions
# =====================================================================
R = BL.Region


def _xyz(P):
    return P[:, 0], P[:, 1], P[:, 2]


def mx(*fs):
    return np.maximum.reduce(fs)


def side_poly(poly):
    poly = BL.smooth_closed(poly, 8) if len(poly) > 4 else np.asarray(poly, float)
    return lambda P: BL.poly_sdf(P[:, [1, 2]], poly)


TW = 0.2       # metres per unit of t (approx.), for parameter-space regions
LOOPS = {}


def regions(skin):
    def nrm(s, t):
        return skin.normal(s, t)
    sdf_cl = side_poly(CLINE_SIDE + [(0.53, 1.30), (-0.40, -0.20)])
    sdf_dlo = side_poly(DLO)
    reg = {}
    # ---- holes
    def arch(P, s, t, yc, zc, r):
        x, y, z = _xyz(P)
        return mx(np.hypot(y - yc, z - zc) - r, 0.55 - x)
    reg['arch_F'] = R(lambda P, s, t: arch(P, s, t, YF, ZF, spec.ARCH_R_F))
    reg['arch_R'] = R(lambda P, s, t: arch(P, s, t, YR, ZR, spec.ARCH_R_R))
    # openings: loop found on the skin by inverting a projection inside a parameter window,
    # hole region = polygon in parameter space (unambiguous)
    for key, poly, plane, srng, trng, fac in OPENINGS:
        poly = headlight_poly() if poly is None else poly
        inv = BL.Inverter(skin, plane, srng, trng, n=120, facing=fac)
        pp = BL.resample_closed(BL.smooth_closed(poly, 8) if key != 'headlight' else poly, 72)
        ls, lt = inv(pp)
        res = np.abs(BL.proj(skin.eval(ls, lt), plane) - pp).max()
        print('[body] opening %s inversion residual %.4f' % (key, res))
        LOOPS[key] = (ls, lt)
        st = np.stack([ls, lt * TW], 1)
        reg[key] = R(lambda P, s, t, st=st: BL.poly_sdf(np.stack([s, t * TW], 1), st))
    # ---- panels (priority order)
    def ws(P, s, t):
        x, y, z = _xyz(P)
        return mx(y_cowl(x) - y, y + 0.630, x - x_ws(y), 0.6 - z)
    def canopy(P, s, t):
        x, y, z = _xyz(P)
        return mx(-0.622 - y, y - 0.600, x - x_can(y), 0.9 - z)
    def door(P, s, t):
        x, y, z = _xyz(P)
        return mx(y_front(z) - y, y - door_rear(z), cl_low(y) - z, x_strip(y) - x, 0.4 - x, z - 1.25)
    def side_glass(P, s, t):
        x, y, z = _xyz(P)
        return mx(sdf_dlo(P), y - door_rear(z) + 0.022, y_front(z) + 0.022 - y, x_strip(y) + 0.026 - x,
                  0.4 - x)
    def lower_side(P, s, t):
        x, y, z = _xyz(P)
        return mx(z - cl_low(y), -1.05 - y, y - 0.95, 0.55 - x)
    def lower_front(P, s, t):
        x, y, z = _xyz(P)
        return mx(z - 0.200, s + 1.95)
    def lower_rear(P, s, t):
        x, y, z = _xyz(P)
        return np.minimum(mx(z - 0.300, 0.95 - y, 0.5 - x), mx(z - 0.48, 1.88 - y))
    def bumper(P, s, t):
        x, y, z = _xyz(P)
        return mx(s + 1.85, z - 0.535)
    def bonnet(P, s, t):
        x, y, z = _xyz(P)
        return mx(x - x_v(y), y - y_cowl(x), 0.55 - z, y + 1.20)
    def roof(P, s, t):
        x, y, z = _xyz(P)
        return mx(0.86 - z, x - 0.74, y_cowl(np.minimum(x, 0.655)) - 0.03 - y, y - 0.75)
    def fender(P, s, t):
        x, y, z = _xyz(P)
        return mx(y - y_front(z), y + 0.88)
    def quarter(P, s, t):
        x, y, z = _xyz(P)
        return mx(sdf_cl(P), door_rear(z) - y, 0.45 - x, 0.55 - nrm(s, t)[:, 0])
    def deck(P, s, t):
        x, y, z = _xyz(P)
        return mx(x - x_bi(y), 0.55 - y, y - 1.96, 0.8 - z)
    def tail(P, s, t):
        x, y, z = _xyz(P)
        return mx(1.96 - y, 0.55 - z, x - 0.70)
    for k, f in list(locals().items()):
        if k in ('ws', 'canopy', 'door', 'side_glass', 'lower_side', 'lower_front', 'lower_rear', 'bumper',
                 'bonnet', 'roof', 'fender', 'quarter', 'deck', 'tail'):
            reg[k] = R(f)
    return reg


HOLES = ['arch_F', 'arch_R', 'intake_F', 'headlight', 'side_intake', 'scoop']
# (name, region key, material, mirror mode 'sym' | 'pair', kind)
PANELS = [
    ('Glass_Windshield', 'ws', 'glass', 'sym', 'glass'),
    ('Glass_Roof', 'canopy', 'glass_dark', 'sym', 'glass'),
    ('Glass_Side_L', 'side_glass', 'glass', 'pair', 'glass_door'),
    ('Body_Door_L', 'door', 'paint_primary', 'pair', 'door'),
    ('Body_Sill_L', 'lower_side', 'carbon_gloss', 'pair', 'panel'),
    ('Body_Lower_F', 'lower_front', 'carbon_gloss', 'sym', 'panel'),
    ('Body_Lower_R', 'lower_rear', 'carbon_gloss', 'sym', 'panel'),
    ('Body_Bumper_F', 'bumper', 'paint_primary', 'sym', 'panel'),
    ('Body_Bonnet', 'bonnet', 'paint_secondary', 'sym', 'panel'),
    ('Body_Roof', 'roof', 'paint_secondary', 'sym', 'panel'),
    ('Body_Fender_F_L', 'fender', 'paint_primary', 'pair', 'panel'),
    ('Body_Quarter_L', 'quarter', 'paint_primary', 'pair', 'panel'),
    ('Body_Deck', 'deck', 'paint_secondary', 'sym', 'panel'),
    ('Body_Tail', 'tail', 'paint_secondary', 'sym', 'panel'),
    ('Body_Rear_L', None, 'paint_secondary', 'pair', 'panel'),
]


# =====================================================================
# geometry helpers
# =====================================================================
def rib(name, P, N, half_w, height, coll, n_prof=9, sink=0.004):
    """Raised rounded rib along a surface path P (n,3) with surface normals N."""
    P = np.asarray(P, float)
    N = np.asarray(N, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-12
    B = np.cross(T, N)
    B /= np.linalg.norm(B, axis=1)[:, None] + 1e-12
    h = np.broadcast_to(np.asarray(height, float), (len(P),))
    prof = [(-half_w, -sink)]
    for a in np.linspace(math.pi, 0, n_prof):
        prof.append((half_w * math.cos(a), math.sin(a)))
    prof.append((half_w, -sink))
    m = len(prof)
    V = []
    for i in range(len(P)):
        for (u, v) in prof:
            vv = v * h[i] if v >= 0 else v
            V.append(P[i] + B[i] * u + N[i] * vv)
    F = []
    for i in range(len(P) - 1):
        for j in range(m):
            j2 = (j + 1) % m
            F.append([i * m + j, i * m + j2, (i + 1) * m + j2, (i + 1) * m + j])
    F.append(list(range(m))[::-1])
    F.append([(len(P) - 1) * m + j for j in range(m)])
    ob = geo.new_object(name, V, F, coll=coll, smooth=True, sharp_angle=70.0)
    geo.recalc_normals(ob)
    return ob


def _smooth_path(P, k=7):
    P = np.asarray(P, float)
    if len(P) < 2 * k:
        return P
    w = np.ones(k) / k
    out = P.copy()
    for c in range(P.shape[1]):
        pad = np.concatenate([np.full(k, P[0, c]), P[:, c], np.full(k, P[-1, c])])
        out[:, c] = np.convolve(pad, w, mode='same')[k:-k]
    out[0], out[-1] = P[0], P[-1]
    return out


def liner(name, skin, key, coll):
    x_w, yc, zc = spec.WHEELS[key]
    r = (spec.ARCH_R_F if key[0] == 'F' else spec.ARCH_R_R) + 0.004
    a0 = math.asin(max(-0.95, (0.125 - zc) / r))
    ang = np.linspace(math.pi - a0, a0, 56)      # front-bottom -> over the top -> rear-bottom
    ys = yc + r * np.cos(ang)
    zs = zc + r * np.sin(ang)
    inv = BL.Inverter(skin, 'side', (yc - 0.6, yc + 0.6), (4.0, 8.9), n=90)
    s, t = inv(np.stack([ys, zs], 1))
    xo = skin.eval(s, t)[:, 0] - 0.006
    xi = 0.52
    nx = 6
    V = []
    for i in range(len(ang)):
        for j in range(nx):
            u = j / (nx - 1)
            V.append((xi + (xo[i] - xi) * u, ys[i], zs[i]))
    F = [[i * nx + j, i * nx + j + 1, (i + 1) * nx + j + 1, (i + 1) * nx + j]
         for i in range(len(ang) - 1) for j in range(nx - 1)]
    nv = len(V)
    # inward lip: a 25 mm flange just inside the arch edge (radius r .. r + 0.025)
    for i in range(len(ang)):
        V.append((xo[i] - 0.002, yc + (r + 0.028) * math.cos(ang[i]), zc + (r + 0.028) * math.sin(ang[i])))
    for i in range(len(ang) - 1):
        F.append([i * nx + nx - 1, (i + 1) * nx + nx - 1, nv + i + 1, nv + i])
    # inner wall at x = xi closing the well (fan from the axle centre)
    c = len(V)
    V.append((xi, yc, zc))
    for i in range(len(ang) - 1):
        F.append([i * nx, c, (i + 1) * nx])
    F.append([(len(ang) - 1) * nx, c, 0])
    ob = geo.new_object(name, V, F, coll=coll, smooth=True, sharp_angle=50.0)
    mats.assign(ob, 'plastic_black')
    return ob


def recess(name, skin, key, depth, coll, direction=None, taper=0.15):
    ls, lt = LOOPS[key]
    P = skin.eval(ls, lt)
    N = skin.normal(ls, lt)
    P = P - N * 0.002
    ob = BL.tunnel(name, P, N, depth, coll=coll, taper=taper, steps=3, direction=direction)
    mats.assign(ob, 'plastic_black')
    return ob, P, N


def _solid(ob, thick, inner='plastic_black'):
    mats.assign(ob, inner, append=True)
    m = geo.mod_solidify(ob, thick, offset=-1.0, even=False)
    m.material_offset = 1
    m.material_offset_rim = 1
    return m


# =====================================================================
# build
# =====================================================================
def build(ctx):
    coll = ctx.collection('Body')
    gcoll = ctx.collection('Glass')
    root = ctx.module_root('Body')
    skin = make_skin()
    final = ctx.final()
    ds = 0.0095 if final else 0.021
    S = skin.column_params(ds)
    T = skin.row_params(ds)
    reg = regions(skin)
    holes = None
    for h in HOLES:
        holes = reg[h] if holes is None else (holes | reg[h])
    taken = None
    statics, door_parts = [], []
    made = {}
    for name, key, mat, mode, kind in PANELS:
        own = BL.R_all() if key is None else reg[key]
        r = own - holes
        if taken is not None:
            r = r - taken
        taken = own if taken is None else (taken | own)
        ob = BL.mesh_region(skin, S, T, r.grow(-GAP), name, gcoll if kind.startswith('glass') else coll,
                              weld=0.3 * ds)
        if ob is None:
            print('[body] empty panel', name)
            continue
        mats.assign(ob, mat)
        if kind.startswith('glass'):
            m = geo.mod_solidify(ob, 0.005, offset=-1.0, even=False)
        elif kind == 'door':
            _solid(ob, 0.035, 'carbon_matte')
            # window frame above the belt is dark like the pillars (A4)
            mats.assign_faces(ob, 'paint_secondary', lambda c, p: c.z > 0.858)
        else:
            _solid(ob, 0.004)
        if mode == 'sym':
            mir = geo.mod_mirror(ob)
            bpy_move_first(ob, mir)
            statics.append(ob)
        else:
            mirror = geo.mirror_copy(ob, name[:-2] + '_R', gcoll if kind.startswith('glass') else coll)
            if kind in ('door', 'glass_door'):
                door_parts.append((ob, 'L'))
                door_parts.append((mirror, 'R'))
            else:
                statics += [ob, mirror]
        made[name] = ob

    # (no separate backing skin: every panel has dark inner faces and rims, so gaps read dark)

    # ---- wheel-arch liners
    for key in ('FL', 'RL'):
        ob = liner('Body_Liner_' + key, skin, key, coll)
        statics += [ob, geo.mirror_copy(ob, 'Body_Liner_' + key[0] + 'R', coll)]

    # ---- recesses behind the openings
    anchors = {}
    ob, P, N = recess('Body_Recess_Intake_F_L', skin, 'intake_F', 0.10, coll, direction=(0, -1, 0))
    statics += [ob, geo.mirror_copy(ob, 'Body_Recess_Intake_F_R', coll)]
    anchors['intake_front_L'] = P.tolist()
    ob, P, N = recess('Body_Recess_Headlight_L', skin, 'headlight', 0.06, coll, direction=(0, -1, 0), taper=0.05)
    statics += [ob, geo.mirror_copy(ob, 'Body_Recess_Headlight_R', coll)]
    i0, i1 = np.argmin(P[:, 0]), np.argmax(P[:, 0])
    anchors['headlight_L'] = dict(outline=P.tolist(), normal=N.mean(0).tolist(),
                                  inner_end=P[i0].tolist(), outer_end=P[i1].tolist())
    ob, P, N = recess('Body_Recess_SideIntake_L', skin, 'side_intake', 0.10, coll, direction=(1, 0, 0))
    statics += [ob, geo.mirror_copy(ob, 'Body_Recess_SideIntake_R', coll)]
    anchors['side_intake_L'] = P.tolist()
    ob, P, N = recess('Body_Recess_Scoop_L', skin, 'scoop', 0.16, coll, direction=(0, 0, 1), taper=0.1)
    statics += [ob, geo.mirror_copy(ob, 'Body_Recess_Scoop_R', coll)]
    anchors['deck_scoop_L'] = P.tolist()
    # horseshoe: the first skin column is its outline
    tt = np.linspace(0, skin.K, 40)
    hl = skin.eval(np.full_like(tt, S0), tt)
    hs = np.vstack([hl, (hl[::-1] * [-1, 1, 1])[1:-1]])
    ob = BL.tunnel('Body_Recess_Horseshoe', hs, None, 0.09, coll=coll, taper=0.06, direction=(0, -1, 0))
    mats.assign(ob, 'plastic_black')
    statics.append(ob)
    anchors['horseshoe'] = dict(outline=hs.tolist(), center=hs.mean(0).tolist())
    hn = skin.normal(np.full_like(tt, S0 + 0.004), tt)
    hn = np.vstack([hn, (hn[::-1] * [-1, 1, 1])[1:-1]])
    hsc = np.vstack([hs, hs[:2]])
    hnc = np.vstack([hn, hn[:2]])
    ob = rib('Body_Horseshoe_Lip', hsc - np.array([0, 0.004, 0]), hnc, 0.010, 0.010, coll, sink=0.006)
    mats.assign(ob, 'paint_primary')
    statics.append(ob)
    # rear: last column closes with a dark wall
    rl = skin.eval(np.full_like(tt, S1), tt)
    rs = np.vstack([rl, (rl[::-1] * [-1, 1, 1])])
    ob = BL.tunnel('Body_Recess_Rear', rs, None, 0.16, coll=coll, taper=0.10, steps=4, direction=(0, 1, 0))
    ob.data.vertices[len(ob.data.vertices) - 1].co.y -= 0.12     # concave dish
    mats.assign(ob, 'carbon_matte')
    statics.append(ob)
    anchors['rear_opening'] = rs.tolist()

    # ---- spine rib on the centreline
    ss = np.linspace(S0 + 0.012, S1 - 0.004, 400 if final else 220)
    Pc = skin.eval(ss, np.zeros_like(ss))
    Nc = skin.normal(ss, np.zeros_like(ss))
    hgt = np.interp(ss, [-2.4, -2.2, -1.6, -0.6, 0.6, 0.9, 1.9, 2.15, 2.27],
                    [0.004, 0.009, 0.009, 0.007, 0.008, 0.016, 0.016, 0.010, 0.006])
    ob = rib('Body_Spine', Pc, Nc, 0.009, hgt, coll)
    mats.assign(ob, 'paint_secondary')
    statics.append(ob)

    # ---- C-line trims
    cs = BL.resample_open(BL.smooth_open(CLINE_SIDE, 10), 160)
    inv_cl = BL.Inverter(skin, 'side', (-1.1, 0.9), (1.5, 7.8), n=130)
    s_, t_ = inv_cl(cs)
    P = skin.eval(s_, t_)
    N = skin.normal(s_, t_)
    P, N = _smooth_path(P), _smooth_path(N)
    ob = rib('Body_CLine_L', P + N * 0.0005, N, 0.0048, 0.0025, coll, n_prof=7)
    mats.assign(ob, 'aluminum_polished')
    statics += [ob, geo.mirror_copy(ob, 'Body_CLine_R', coll)]
    yy = np.linspace(-1.00, 0.47, 120)
    inv_top = BL.Inverter(skin, 'plan', (-1.1, 0.6), (1.0, 3.6), n=110)
    s_, t_ = inv_top(np.stack([x_strip(yy) + 0.016, yy], 1))
    P = skin.eval(s_, t_)
    N = skin.normal(s_, t_)
    P, N = _smooth_path(P), _smooth_path(N)
    ob = rib('Body_CLine_Door_L', P + N * 0.0005, N, 0.0048, 0.0025, coll, n_prof=7)
    mats.assign(ob, 'aluminum_polished')
    door_parts += [(ob, 'L'), (geo.mirror_copy(ob, 'Body_CLine_Door_R', coll), 'R')]

    # ---- parenting
    rig.adopt(statics, root)
    for ob, side in door_parts:
        geo.parent(ob, rig.door_hinge(side))

    # ---- anchors for other modules (world coordinates)
    anchors.update(publish_anchors(skin))
    ctx.data['body'] = anchors
    try:
        import json, os
        d = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'out', 'renders', 'body')
        os.makedirs(d, exist_ok=True)
        json.dump(anchors, open(os.path.join(d, 'anchors.json'), 'w'))
    except Exception as e:  # noqa
        print('[body] anchors not saved', e)


def bpy_move_first(ob, mod):
    import bpy
    with bpy.context.temp_override(object=ob):
        bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)


def publish_anchors(skin):
    """Reference points for other modules (world coordinates, left side unless named otherwise)."""
    a = {}
    ip = BL.Inverter(skin, 'plan', (-1.8, 2.27), (0.0, 4.0), n=140, facing=(2, 0.3))
    isd = BL.Inverter(skin, 'side', (-1.3, 1.9), (3.0, 7.8), n=140, facing=(0, 0.4))

    def on(inv, pts):
        s, t = inv(np.asarray(pts, float))
        return skin.eval(s, t), skin.normal(s, t)

    r3 = lambda A: np.round(np.asarray(A), 4).tolist()
    tt = np.linspace(0, skin.t_of('K'), 24)
    a['tail_edge'] = r3(skin.eval(np.full_like(tt, S1), tt))          # centre -> left corner
    xs = np.linspace(0.0, 0.78, 14)
    P, N = on(ip, np.stack([xs, np.full_like(xs, spec.WING['pivot'][1])], 1))
    a['wing_seat'] = r3(P)                                             # skin line under the wing hinge
    P, N = on(isd, [(-0.74, 0.865)])
    a['mirror_mount_L'] = dict(point=r3(P[0]), normal=r3(N[0]))
    P, N = on(isd, [(0.571, 0.92)])
    a['roundel_L'] = dict(center=r3(P[0]), normal=r3(N[0]), diameter=0.15)
    P, N = on(isd, [(-0.86, 0.205), (-0.58, 0.205), (-0.58, 0.262), (-0.86, 0.262)])
    a['sill_gill_zone_L'] = dict(corners=r3(P), normal=r3(N.mean(0)))
    xs = np.linspace(0.0, 0.655, 12)
    P, N = on(ip, np.stack([xs, y_cowl(xs)], 1))
    a['cowl_line'] = r3(P)
    a['door_rear_cut'] = [list(p) for p in spec.DOOR_REAR_CUT]
    zs = [0.30, 0.45, 0.60, 0.75, 0.84]
    P, N = on(isd, [(-0.40, z) for z in zs])
    a['door_inner_clearance'] = dict(note='x of the door inner face at y=-0.40 (door shell 35 mm)',
                                     points=r3(P - N * 0.035))
    P, N = on(ip, [(spec.CABIN['x_seat'], 0.02)])
    a['roof_inner_height'] = round(float(P[0, 2] - 0.006), 4)
    return a
