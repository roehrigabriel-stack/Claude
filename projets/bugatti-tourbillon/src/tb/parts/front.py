"""Front end and exterior details: grille, intakes, splitter, headlights (+ real spots), mirrors, wipers,
sill gills, tricolour stripe, EB roundels.  Built after 'body' (reads ctx.data['body'] anchors, snaps with Raycaster)."""
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector
from tb import geo, mats, rig, spec
from tb.parts import front_lib as FL

Opening = FL.Opening


def build(ctx):
    coll = ctx.collection('Front')
    root = ctx.module_root('Front')
    A = ctx.data['body']
    fin = ctx.final()
    made = []          # every object built (left / centre)
    left = []          # objects to mirror to the right side

    def add(ob, mat, lst=None, bevel=None):
        if mat:
            mats.assign(ob, mat)
        if bevel:
            geo.mod_bevel(ob, bevel, 1)
        made.append(ob)
        if lst is not None:
            lst.append(ob)
        return ob

    bpy.context.view_layer.update()
    body_objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Body_')
                 and 'Recess' not in o.name and 'Liner' not in o.name and not o.name.endswith('_R')]
    rc_body = geo.Raycaster(body_objs)
    glass_ws = bpy.data.objects.get('Glass_Windshield')

    nu = 40 if fin else 28

    # ------------------------------------------------------------------ 1. grille
    hs = Opening(A['horseshoe']['outline'])
    g = add(hs.panel('Front_Grille_Mesh', nu, 24, inset=0.014, dome=0.016, coll=coll), 'mesh_grille')
    back = add(hs.panel('Front_Grille_Back', 12, 10, inset=0.026, dome=0.0, coll=coll), 'plastic_black')
    fr = geo.curve_tube('Front_Grille_Frame', hs.outline_pts(0.0), 0.0062, resolution=3, cyclic=True,
                        spline='POLY', coll=coll)
    add(fr, 'chrome')
    # central rib continuing the bonnet spine
    rib_path = []
    for v in np.linspace(0.0, 1.0, 22):
        p, tu, tv, out = hs.pos(0.5, v, 0.016 * (1 - (2 * v - 1) ** 2) - 0.014 + 0.0035)
        rib_path.append(p)
    rib = geo.sweep('Front_Grille_Rib', rib_path, [(-0.0045, -0.0045), (0.0045, -0.0045), (0.0045, 0.0045),
                                                   (-0.0045, 0.0045)], up=(0, -1, 0), coll=coll, cap=True)
    add(rib, 'chrome')
    # thin ridge on the bonnet spine above the grille
    ridge = []
    for y in np.linspace(-2.388, -2.0, 18):
        h = rc_body.cast((0, y, 1.2), (0, 0, -1))
        if h:
            ridge.append(tuple(np.array(h[0]) + np.array([0, 0, 0.0008])))
    if len(ridge) > 3:
        add(geo.curve_tube('Front_Spine_Line', ridge, 0.0022, resolution=3, spline='POLY', coll=coll), 'chrome')
    # BUGATTI badge
    gp = geo.Raycaster([g])
    hit = gp.cast((0, -3.0, 0.47), (0, 1, 0))
    bp = np.array(hit[0]) if hit else np.array([0, -2.40, 0.47])
    rim = geo.extrude_polygon('Front_Badge_Rim', FL.ellipse(0, 0, 0.037, 0.0245, 40), 0.006, plane='XZ', coll=coll)
    rim_f = geo.extrude_polygon('Front_Badge_Face', FL.ellipse(0, 0, 0.0335, 0.0212, 40), 0.0012, plane='XZ', coll=coll)
    for ob, dy in ((rim, 0.003), (rim_f, -0.0006)):
        geo.transform_mesh(ob, Matrix.Translation((bp[0], bp[1] + dy - 0.006 + 0.0025, bp[2])))
    add(rim, 'aluminum_polished', bevel=0.0008)
    mats.custom('badge_red', base_color='#B30F1B', metallic=0.2, roughness=0.22, coat=1.0)
    add(rim_f, 'badge_red')
    txt = geo.text_mesh('Front_Badge_Text', 'BUGATTI', size=0.012, extrude=0.0012, coll=coll)
    FL.fit_text(txt, 0.046, 0.012)
    geo.transform_mesh(txt, FL.basis_matrix((0, -1, 0), (bp[0], bp[1] - 0.0034 + 0.0025, bp[2]), 'Y'))
    add(txt, 'aluminum_polished')

    # ------------------------------------------------------------------ 2. lower intakes (left, mirrored)
    it = Opening(A['intake_front_L'])
    add(it.panel('Front_Intake_Mesh_L', nu, 20, inset=0.022, dome=0.004, coll=coll), 'mesh_grille', left)
    add(it.panel('Front_Intake_Back_L', 10, 8, inset=0.034, coll=coll), 'plastic_black', left)
    fr = geo.curve_tube('Front_Intake_Frame_L', it.outline_pts(0.0), 0.0022, resolution=3, cyclic=True,
                        spline='POLY', coll=coll)
    add(fr, 'aluminum_polished', left)
    # silver blade splitting the intake, wrapping round the corner
    zb = 0.292
    bpath = []
    for u in np.linspace(0.01, 0.99, 36):
        x = it.xmin + u * (it.xmax - it.xmin)
        c = it.col(it._cl(x))
        if c is None or not (c[0][2] < zb < c[1][2]):
            continue
        v = (zb - c[0][2]) / (c[1][2] - c[0][2])
        p, tu, tv, out = it.pos(u, v, -0.001)
        bpath.append(p)
    if len(bpath) > 3:
        blade = geo.sweep('Front_Intake_Blade_L', bpath, [(-0.004, -0.0065), (0.0032, -0.0065), (0.0032, 0.0065),
                                                          (-0.004, 0.0065)], up=(0, 0, 1), coll=coll, cap=True)
        add(blade, 'aluminum_polished', left)
    # vertical vanes
    for k, u in enumerate((0.2, 0.38, 0.56, 0.74)):
        vp = []
        for v in np.linspace(0.06, 0.94, 8):
            p, tu, tv, out = it.pos(u, v, -0.0015)
            vp.append(p)
        va = geo.sweep('Front_Intake_Vane_L%d' % k, vp, [(-0.0014, -0.016), (0.0014, -0.016), (0.0014, 0.0),
                                                          (-0.0014, 0.0)], up=tuple(out), coll=coll, cap=True)
        add(va, 'aluminum_dark', left)

    # ------------------------------------------------------------------ 3. splitter
    lf = bpy.data.objects.get('Body_Lower_F')
    pts = []
    if lf:
        ev = lf.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        for v in me.vertices:
            w = lf.matrix_world @ v.co
            pts.append((w.x, w.y))
            pts.append((-w.x, w.y))
        ev.to_mesh_clear()
    hull = FL.convex_hull_2d(pts)
    hull = FL.offset_polygon(hull, 0.010)
    sp = geo.extrude_polygon('Front_Splitter', hull, 0.016, plane='XY', offset=0.143, coll=coll)
    add(sp, 'carbon_gloss', bevel=0.0025)
    front_edge = [p for p in hull if p[1] < -2.1]
    front_edge.sort(key=lambda p: p[0])
    if len(front_edge) > 3:
        line = geo.curve_tube('Front_Splitter_Line', [(p[0], p[1] + 0.001, 0.1535) for p in front_edge],
                              0.0016, resolution=3, spline='POLY', coll=coll)
        add(line, 'chrome')
    hx = max(abs(p[0]) for p in hull)
    fx = 0.80
    yfs = [y for (x, y) in hull if abs(x - fx) < 0.12]
    yf = min(yfs) if yfs else -2.30
    fin_o = geo.extrude_polygon('Front_Winglet_L', [(yf + 0.02, 0.150), (yf + 0.20, 0.150), (yf + 0.16, 0.212),
                                                    (yf + 0.05, 0.226)], 0.004, plane='YZ', offset=fx, coll=coll)
    add(fin_o, 'carbon_gloss', left, bevel=0.0012)

    # ------------------------------------------------------------------ 4. headlights
    hl = A['headlight_L']
    nrm = np.array(hl['normal'])
    ho = Opening(hl['outline'], const_out=nrm)
    add(ho.panel('Front_Headlight_Housing_L', 24, 8, inset=0.016, coll=coll), 'plastic_black', left)
    add(ho.panel('Front_Headlight_Lens_L', 28, 10, inset=0.0012, dome=0.0015, coll=coll), 'glass_dark', left)
    fr = geo.curve_tube('Front_Headlight_Bezel_L', ho.outline_pts(0.0), 0.0016, resolution=3, cyclic=True,
                        spline='POLY', coll=coll)
    add(fr, 'chrome', left)
    for i, u in enumerate((0.20, 0.38, 0.56, 0.74)):
        p, tu, tv, out = ho.pos(u, 0.58, -0.0075)
        add(FL.oriented_box('Front_Headlight_Bezel_El_L%d' % i, p, tu, tv, out, (0.054, 0.020, 0.004), coll=coll),
            'chrome', left)
        p, tu, tv, out = ho.pos(u, 0.58, -0.0050)
        add(FL.oriented_box('Front_Headlight_LED_L%d' % i, p, tu, tv, out, (0.046, 0.0125, 0.004), coll=coll),
            'emit_headlight', left)
    p, tu, tv, out = ho.pos(0.47, 0.22, -0.0055)
    add(FL.oriented_box('Front_Headlight_DRL_L', p, tu, tv, out, (0.275, 0.0042, 0.004), coll=coll), 'emit_drl', left)
    p, tu, tv, out = ho.pos(0.90, 0.60, -0.0050)
    add(FL.oriented_box('Front_Headlight_Indicator_L', p, tu, tv, out, (0.050, 0.0075, 0.004), coll=coll),
        'emit_indicator', left)
    # real lamps
    cen = (np.array(hl['inner_end']) + np.array(hl['outer_end'])) / 2
    lamps = []
    for sgn in (1, -1):
        ld = bpy.data.lights.new('Front_Spot_%s' % ('L' if sgn > 0 else 'R'), 'SPOT')
        ld.spot_size = math.radians(70)
        ld.spot_blend = 0.6
        ld.color = (0.85, 0.92, 1.0)
        ld.shadow_soft_size = 0.04
        lo = bpy.data.objects.new(ld.name, ld)
        geo.link(lo, coll)
        lo.location = (sgn * cen[0] + 0.0, cen[1] - 0.02, cen[2] - 0.02) + Vector((sgn * 0.0, 0, 0)) if False else \
            Vector((sgn * cen[0], cen[1] - 0.02, cen[2] - 0.02))
        d = Vector((sgn * 0.06, -1.0, -0.13))
        lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        rig.drive_light(lo, 'headlights', 400.0)
        lamps.append(lo)
        made.append(lo)

    # ------------------------------------------------------------------ 5. mirrors
    mm = A['mirror_mount_L']
    mp = np.array(mm['point'])
    mn = np.array(mm['normal'])
    cx, cy, cz = 1.035, -0.805, 0.875
    shell = geo.uv_sphere('Front_Mirror_Shell_L', 1.0, (cx, cy, cz), segments=32 if fin else 24, rings=16,
                          scale=(0.045, 0.110, 0.056), coll=coll)
    ymax = cy + 0.062
    for v in shell.data.vertices:
        if v.co.y > ymax:
            v.co.y = ymax
    shell.data.update()
    geo.shade(shell, True, 50)
    add(shell, 'paint_secondary', left)
    gl = geo.extrude_polygon('Front_Mirror_Glass_L', FL.ellipse(cx, cz, 0.034, 0.042, 28), 0.0016,
                             plane='XZ', offset=ymax - 0.0006, coll=coll)
    add(gl, 'chrome', left)
    stalk = geo.curve_tube('Front_Mirror_Stalk_L', [tuple(mp - mn * 0.02), tuple(mp + mn * 0.005),
                                                    (cx - 0.045, cy + 0.045, cz - 0.020), (cx - 0.02, cy + 0.01, cz - 0.01)],
                           0.0135, resolution=4, spline='POLY', coll=coll)
    add(stalk, 'carbon_gloss', left)

    # ------------------------------------------------------------------ 6. wipers
    if glass_ws:
        rc_g = geo.Raycaster([glass_ws])
        cl = np.array(A['cowl_line'])
        order = np.argsort(cl[:, 0])
        wpath = []
        for x in np.linspace(0.50, 0.04, 14):
            y = float(np.interp(x, cl[order, 0], cl[order, 1])) + 0.055
            h = rc_g.cast((x, y, 1.6), (0, 0, -1))
            if h:
                wpath.append(np.array(h[0]) + np.array(h[1]) * 0.003)
        if len(wpath) > 5:
            n_ = len(wpath)
            ka = int(n_ * 0.45)
            arm = geo.sweep('Front_Wiper_Arm_L', [p + np.array([0, 0, 0.003]) for p in wpath[:ka + 1]],
                            [(-0.004, -0.0025), (0.004, -0.0025), (0.004, 0.0025), (-0.004, 0.0025)],
                            up=(0, 0, 1), coll=coll, cap=True)
            add(arm, 'plastic_black', left)
            bl = geo.sweep('Front_Wiper_Blade_L', wpath[max(0, ka - 1):],
                           [(-0.0075, -0.0022), (0.0075, -0.0022), (0.0075, 0.0030), (-0.0075, 0.0030)],
                           up=(0, 0, 1), coll=coll, cap=True)
            add(bl, 'plastic_black', left)
            piv = geo.cylinder('Front_Wiper_Pivot_L', 0.009, 0.010, axis='Z',
                               location=tuple(wpath[0] + np.array([0, 0, 0.002])), segments=16, coll=coll)
            add(piv, 'aluminum_dark', left)

    # ------------------------------------------------------------------ 7. side details
    gz = np.array(A['sill_gill_zone_L']['corners'])
    y0, y1 = gz[:, 1].min(), gz[:, 1].max()
    z0, z1 = gz[:, 2].min(), gz[:, 2].max()
    dx = (-1.0, 0.0, 0.0)
    for k in range(3):
        yo = y0 + (y1 - y0) * (0.06 + 0.30 * k)
        ya, yb = yo, yo + (y1 - y0) * 0.30
        za, zb2 = z0 + (z1 - z0) * 0.10, z1 - (z1 - z0) * 0.10
        # diagonal slot: lower-front to upper-rear
        pf = lambda t, ya=ya, yb=yb, za=za, zb2=zb2: (1.5, ya + (yb - ya) * t, za + (zb2 - za) * t)
        G = FL.strip_grid(rc_body, pf, dx, 18, 3, 0.017, 0.0007)
        slot = geo.grid_surface('Front_Gill_L%d' % k, G, coll=coll, smooth=True)
        if np.array(slot.data.polygons[0].normal)[0] < 0:
            geo.flip_normals(slot)
        add(slot, 'plastic_black', left)
        for sgn, nm in ((0.5, 'a'), (-0.5, 'b')):
            def pe(t, sgn=sgn, ya=ya, yb=yb, za=za, zb2=zb2):
                return (1.5, ya + (yb - ya) * t, za + (zb2 - za) * t)
            G = FL.strip_grid(rc_body, pe, dx, 18, 2, 0.0, 0.0)
            # edge line along the slot border (offset sideways by width/2)
            pts_e = []
            for i in range(18):
                t = i / 17
                p = np.array(pe(t))
                pa, pb = np.array(pe(min(1, t + 0.02))), np.array(pe(max(0, t - 0.02)))
                tg = FL._unit(pa - pb)
                side = FL._unit(np.cross(tg, np.array(dx)))
                q, _ = FL.snap(rc_body, p + side * (0.017 * sgn), dx, 0.0006)
                pts_e.append(tuple(q))
            e = geo.curve_tube('Front_Gill_Edge_L%d%s' % (k, nm), pts_e, 0.0009, resolution=2, spline='POLY', coll=coll)
            add(e, 'aluminum_polished', left)
    # tricolour stripe under the gills
    cols = [('tri_blue', '#16399B'), ('tri_white', '#F1F1F1'), ('tri_red', '#C4122E')]
    zs = z0 - 0.020
    ys0, seg = y0 + 0.03, 0.040
    for i, (nm, hexc) in enumerate(cols):
        mats.custom(nm, base_color=hexc, metallic=0.0, roughness=0.3, coat=0.8)
        ya, yb = ys0 + i * seg, ys0 + (i + 1) * seg - 0.0015
        pf = lambda t, ya=ya, yb=yb: (1.5, ya + (yb - ya) * t, zs)
        G = FL.strip_grid(rc_body, pf, dx, 4, 3, 0.012, 0.0007)
        st = geo.grid_surface('Front_Tricolour_L%d' % i, G, coll=coll, smooth=True)
        if np.array(st.data.polygons[0].normal)[0] < 0:
            geo.flip_normals(st)
        add(st, nm, left)
    # EB roundel on the rear quarter
    rd = A['roundel_L']
    rn = np.array(rd['normal'])
    rn = rn / np.linalg.norm(rn)
    surf, sn = FL.snap(rc_body, rd['center'], -rn, 0.0, back=0.3)
    if sn is not None:
        rn = np.array(sn)
    Mb = FL.basis_matrix(rn, surf, 'Y')
    R = rd['diameter'] / 2
    segs = 64 if fin else 40
    disc = geo.cylinder('Front_Roundel_Base_L', R - 0.001, 0.018, axis='Z', location=(0, 0, 0.003 - 0.009),
                        segments=segs, coll=coll)
    geo.transform_mesh(disc, Mb)
    add(disc, 'plastic_black', left)
    ring = geo.torus('Front_Roundel_Ring_L', R - 0.005, 0.0048, axis='Z', location=(0, 0, 0.0028),
                     major_seg=segs, minor_seg=12, coll=coll)
    geo.transform_mesh(ring, Mb)
    add(ring, 'aluminum_polished', left)
    cen_d = geo.cylinder('Front_Roundel_Centre_L', R - 0.010, 0.004, axis='Z', location=(0, 0, 0.0016),
                         segments=segs, coll=coll)
    geo.transform_mesh(cen_d, Mb)
    add(cen_d, 'plastic_black', left)
    et = geo.text_mesh('Front_Roundel_EB_L', 'EB', size=0.05, extrude=0.0014, coll=coll)
    FL.fit_text(et, 0.062, 0.042)
    geo.transform_mesh(et, Matrix.Translation((0, 0, 0.0036)))
    geo.transform_mesh(et, Mb)
    add(et, 'aluminum_polished', left)

    # ------------------------------------------------------------------ mirror to the right
    rights = []
    for ob in left:
        nm = ob.name[:-2] + '_R' if ob.name.endswith('_L') else (
            ob.name.rsplit('_L', 1)[0] + '_R' + ob.name.rsplit('_L', 1)[1])
        r = geo.mirror_copy(ob, nm, coll)
        r.data.materials.clear()
        for m in ob.data.materials:
            r.data.materials.append(m)
        rights.append(r)
    made += rights
    lamps[1].location = (-lamps[0].location[0], lamps[0].location[1], lamps[0].location[2])
    rig.adopt(made, root)
    for o in made:
        o.parent = root if o.parent is None else o.parent
    ctx.data['front'] = dict(objects=[o.name for o in made], lamps=[l.name for l in lamps])
