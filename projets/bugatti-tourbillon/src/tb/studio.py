"""tb.studio: scene reset, render settings, preview studio, cameras and shots.

Typical test script (run with: blender -b --factory-startup -P my_test.py):

    import sys; sys.path.insert(0, '/home/user/Claude/projets/bugatti-tourbillon/src')
    from tb import build, studio, rig
    build.build(parts=['wheels'])                 # fresh scene + requested modules
    studio.preview_studio()                       # floor, softboxes, world
    studio.shot('/path/out.png', eye=(2.5, -3.5, 1.0), target=(0.86, -1.37, 0.35), lens=60)
    studio.render_views('/path/outdir', ['f34', 'side'], objs=rig.all_car_objects())
"""
import math
import os
import bpy
from mathutils import Vector

from . import geo

STUDIO_COLL = 'TB_Studio'


# ----------------------------------------------------------------- scene / render settings
def reset_scene():
    """Empty factory scene (removes every object, mesh, material...)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def setup_render(res=(1280, 720), samples=32, denoise=True, transparent=False, threads=0,
                 max_bounces=6, exposure=0.0, view_transform='AgX', look='AgX - Medium High Contrast'):
    """Cycles CPU settings tuned for a 4-core machine without GPU."""
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    c = s.cycles
    c.device = 'CPU'
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.03
    c.adaptive_min_samples = max(4, samples // 4)
    c.use_denoising = denoise
    if denoise:
        c.denoiser = 'OPENIMAGEDENOISE'
        c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.max_bounces = max_bounces
    c.diffuse_bounces = 2
    c.glossy_bounces = 4
    c.transmission_bounces = 6
    c.transparent_max_bounces = 12
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 6.0
    c.blur_glossy = 0.6
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = transparent
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    s.render.use_persistent_data = False
    s.render.threads_mode = 'FIXED' if threads else 'AUTO'
    if threads:
        s.render.threads = threads
    s.view_settings.view_transform = view_transform
    try:
        s.view_settings.look = look
    except TypeError:
        pass
    s.view_settings.exposure = exposure
    return s


# ----------------------------------------------------------------- cameras
def look_at(obj, target, roll=0.0):
    d = Vector(target) - Vector(obj.location)
    q = d.to_track_quat('-Z', 'Y')
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = q.to_euler('XYZ')
    if roll:
        obj.rotation_euler.rotate_axis('Z', math.radians(roll))
    return obj


def camera(name, eye, target, lens=50.0, ortho_scale=None, up=None, clip=(0.02, 500.0), coll=None):
    """Create a camera at `eye` looking at `target`. ortho_scale (metres across the
    longer image side) switches to an orthographic camera. `up` forces the image-up
    direction (needed for straight top views)."""
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start, cd.clip_end = clip
    cd.sensor_width = 36.0
    if ortho_scale is not None:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho_scale
    ob = bpy.data.objects.new(name, cd)
    geo.link(ob, coll or geo.collection(STUDIO_COLL))
    ob.location = eye
    if up is None:
        look_at(ob, target)
    else:
        f = (Vector(target) - Vector(eye)).normalized()
        u = Vector(up).normalized()
        r = f.cross(u).normalized()
        u = r.cross(f).normalized()
        from mathutils import Matrix
        m = Matrix((r, u, -f)).transposed()
        ob.rotation_mode = 'XYZ'
        ob.rotation_euler = m.to_euler('XYZ')
    return ob


def render(path, cam=None):
    s = bpy.context.scene
    if cam is not None:
        s.camera = cam
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def shot(path, eye, target, lens=50.0, ortho_scale=None, up=None, res=None, samples=None, keep_camera=False):
    """One-call render from an arbitrary viewpoint (uses current render settings unless
    res / samples are given; call setup_render() once before)."""
    s = bpy.context.scene
    if s.render.engine != 'CYCLES':
        setup_render()
    if res is not None:
        s.render.resolution_x, s.render.resolution_y = res
    if samples is not None:
        s.cycles.samples = samples
        s.cycles.adaptive_min_samples = max(4, samples // 4)
    cam = camera('ShotCam', eye, target, lens, ortho_scale, up)
    render(path, cam)
    if not keep_camera:
        data = cam.data
        bpy.data.objects.remove(cam)
        bpy.data.cameras.remove(data)
    return path


# ----------------------------------------------------------------- preview studio
def _area(name, loc, target, size, power, color=(1, 1, 1), coll=None, shape='RECTANGLE', spread=None):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = shape
    ld.size = size[0]
    if shape in ('RECTANGLE', 'ELLIPSE'):
        ld.size_y = size[1]
    ld.energy = power
    ld.color = color
    if spread is not None:
        ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld)
    geo.link(ob, coll or geo.collection(STUDIO_COLL))
    ob.location = loc
    look_at(ob, target)
    return ob


def preview_studio(style='light', floor=True, center=(0.0, 0.0, 0.0), scale=1.0, floor_z=0.0):
    """Neutral studio for test renders.
    style 'light': bright grey cyclorama feel, good for judging shapes and colours.
    style 'dark' : dark showroom with strong softbox reflections, good for paint / lights.
    `scale` shrinks or grows the light rig around `center` (use ~0.3 for a single wheel)."""
    from . import mats
    coll = geo.collection(STUDIO_COLL)
    s = bpy.context.scene
    if s.world is None:
        s.world = bpy.data.worlds.new('TB_World')
    w = s.world
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    els = ramp.color_ramp.elements
    if style == 'light':
        els[0].position, els[0].color = 0.45, (0.30, 0.31, 0.33, 1)
        els[1].position, els[1].color = 0.75, (0.85, 0.87, 0.90, 1)
        bg.inputs['Strength'].default_value = 0.9
        floor_col, floor_rough = (0.42, 0.43, 0.45), 0.35
        key = 150.0
    else:
        els[0].position, els[0].color = 0.45, (0.004, 0.004, 0.005, 1)
        els[1].position, els[1].color = 0.80, (0.03, 0.032, 0.036, 1)
        bg.inputs['Strength'].default_value = 1.0
        floor_col, floor_rough = (0.015, 0.015, 0.017), 0.22
        key = 260.0
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])

    c = Vector(center)
    k = scale
    p2 = k * k
    # big overhead softbox + two long side strips + front/rear fill
    _area('Key_Top', c + Vector((0.0, 0.0, 4.2 * k)), c, (5.5 * k, 9.0 * k), key * 2.2 * p2, coll=coll)
    _area('Strip_L', c + Vector((5.0 * k, -0.5 * k, 2.2 * k)), c + Vector((0, 0, 0.5 * k)), (1.2 * k, 8.0 * k), key * 1.1 * p2, coll=coll)
    _area('Strip_R', c + Vector((-5.0 * k, 0.5 * k, 2.2 * k)), c + Vector((0, 0, 0.5 * k)), (1.2 * k, 8.0 * k), key * 0.9 * p2, coll=coll)
    _area('Fill_F', c + Vector((0.0, -6.5 * k, 1.8 * k)), c + Vector((0, 0, 0.6 * k)), (5.0 * k, 1.6 * k), key * 0.7 * p2, coll=coll)
    _area('Fill_B', c + Vector((0.0, 6.5 * k, 2.0 * k)), c + Vector((0, 0, 0.6 * k)), (5.0 * k, 1.6 * k), key * 0.6 * p2, coll=coll)
    if floor:
        fl = geo.grid_surface('Studio_Floor', [[(-60, -60, floor_z), (60, -60, floor_z)], [(-60, 60, floor_z), (60, 60, floor_z)]],
                              coll=coll, smooth=False, uv=False)
        mats.assign(fl, mats.custom('Studio_Floor_' + style, base_color=floor_col, roughness=floor_rough))
    return coll


def interior_light(power=40.0, location=(0.0, -0.1, 1.05), size=0.5):
    """Small soft light inside the cabin so interior test renders are readable."""
    return _area('Cabin_Fill', location, (location[0], location[1], 0.0), (size, size), power)


# ----------------------------------------------------------------- standard views
# name: (direction from target to camera, lens, vertical offset factor)
VIEW_DIRS = {
    'front':   ((0.0, -1.0, 0.10), 85),
    'rear':    ((0.0, 1.0, 0.10), 85),
    'left':    ((1.0, 0.0, 0.06), 85),
    'right':   ((-1.0, 0.0, 0.06), 85),
    'top':     ((0.0, -0.001, 1.0), 85),
    'f34':     ((0.62, -1.0, 0.30), 55),      # front three-quarter, driver side
    'f34r':    ((-0.62, -1.0, 0.30), 55),     # front three-quarter, passenger side
    'r34':     ((0.62, 1.0, 0.32), 55),       # rear three-quarter, driver side
    'r34r':    ((-0.62, 1.0, 0.32), 55),
    'low_f34': ((0.55, -1.0, 0.06), 45),
    'low_r34': ((0.55, 1.0, 0.07), 45),
    'high_f34': ((0.55, -0.9, 0.95), 55),
    'high_r34': ((0.55, 0.9, 0.95), 55),
}
# orthographic blueprint views: name -> (direction to camera, image-up vector)
ORTHO_DIRS = {
    'ortho_side':  ((-1.0, 0.0, 0.0), (0, 0, 1)),   # seen from the car's right: nose points to image right
    'ortho_front': ((0.0, -1.0, 0.0), (0, 0, 1)),
    'ortho_rear':  ((0.0, 1.0, 0.0), (0, 0, 1)),
    'ortho_top':   ((0.0, 0.0, 1.0), (1, 0, 0)),    # nose points to image right
}
ORTHO_PX_PER_M = 320.0   # fixed scale of ortho views (see tools/overlay.py)
ORTHO_RES = (1760, 990)  # 5.5 m x 3.09 m window
ORTHO_CENTER = {
    'ortho_side': (0.0, -0.0645, 0.75), 'ortho_front': (0.0, 0.0, 0.75),
    'ortho_rear': (0.0, 0.0, 0.75), 'ortho_top': (0.0, -0.0645, 0.6),
}


def frame_bounds(objs, pad=1.12):
    lo, hi = geo.bounds(objs)
    center = (lo + hi) / 2.0
    radius = (hi - lo).length / 2.0 * pad
    return center, max(radius, 0.01)


def _fit_distance(lo, hi, center, dv, lens, aspect, pad=1.10):
    """Camera distance along dv so that the whole box [lo, hi] is inside the frame."""
    f = (-dv).normalized()
    up = Vector((0, 0, 1)) if abs(f.z) < 0.999 else Vector((0, -1, 0))
    r = f.cross(up).normalized()
    u = r.cross(f).normalized()
    th = 18.0 / lens                    # tan(hfov / 2)
    tv = th / aspect
    best = 0.01
    for cx in (lo.x, hi.x):
        for cy in (lo.y, hi.y):
            for cz in (lo.z, hi.z):
                p = Vector((cx, cy, cz)) - center
                toward = p.dot(dv)
                best = max(best, abs(p.dot(r)) / th + toward, abs(p.dot(u)) / tv + toward)
    return best * pad


def render_views(out_dir, views, objs=None, res=None, samples=None, center=None, pad=1.10, suffix=''):
    """Render named views auto-framed on `objs` (default: every mesh in the scene that is
    not part of the studio). Perspective names: see VIEW_DIRS. Orthographic blueprint
    names: ortho_side, ortho_front, ortho_rear, ortho_top (fixed scale, whole car).
    res / samples default to the current render settings (see setup_render)."""
    s = bpy.context.scene
    if s.render.engine != 'CYCLES':
        setup_render()
    if objs is None:
        studio = set(geo.collection(STUDIO_COLL).objects)
        objs = [o for o in s.objects if o.type == 'MESH' and o not in studio]
    res = tuple(res) if res else (s.render.resolution_x, s.render.resolution_y)
    if samples:
        s.cycles.samples = samples
        s.cycles.adaptive_min_samples = max(4, samples // 4)
    lo, hi = geo.bounds(objs)
    center = Vector(center) if center is not None else (lo + hi) / 2.0
    paths = []
    for v in views:
        if v in ORTHO_DIRS:
            d, up = ORTHO_DIRS[v]
            tgt = Vector(ORTHO_CENTER[v])
            eye = tgt + Vector(d) * 30.0
            s.render.resolution_x, s.render.resolution_y = ORTHO_RES
            cam = camera('Cam_' + v, eye, tgt, ortho_scale=ORTHO_RES[0] / ORTHO_PX_PER_M, up=up)
        else:
            d, lens = VIEW_DIRS[v]
            dv = Vector(d).normalized()
            s.render.resolution_x, s.render.resolution_y = res
            dist = _fit_distance(lo, hi, center, dv, lens, res[0] / res[1], pad)
            eye = center + dv * dist
            eye.z = max(eye.z, 0.10)
            cam = camera('Cam_' + v, eye, center, lens=lens, up=(0, -1, 0) if v == 'top' else None)
        p = os.path.join(out_dir, '%s%s.png' % (v, suffix))
        render(p, cam)
        paths.append(p)
        data = cam.data
        bpy.data.objects.remove(cam)
        bpy.data.cameras.remove(data)
    s.render.resolution_x, s.render.resolution_y = res
    return paths
