"""tb.showroom: the dark showroom used for the final film and beauty stills.

build() creates, in collection 'TB_Showroom':
  * a polished dark floor and a slightly raised turntable with an LED ring
  * a ring of slim vertical light slats on a dark circular wall (backdrop,
    gives depth and long streak reflections on the paint)
  * the lighting rig: overhead softbox, two long side strips, rim lights, and a
    narrow sweep light for the intro
It returns a dict of the objects the film animates.
"""
import math
import bpy
from mathutils import Vector

from . import geo, mats, studio

COLL = 'TB_Showroom'
TURNTABLE_R = 3.35
WALL_R = 11.0


def _floor_material():
    name = 'Showroom_Floor'
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.008, 0.008, 0.009, 1)
    b.inputs['Roughness'].default_value = 0.34
    b.inputs['Specular IOR Level'].default_value = 0.6
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = 0.8
    n.inputs['Detail'].default_value = 6.0
    n.inputs['Roughness'].default_value = 0.6
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['To Min'].default_value = 0.28
    mr.inputs['To Max'].default_value = 0.42
    nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    nt.links.new(n.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
    return m


def _emit(name, color, strength):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.name = 'Emission'
    em.inputs['Color'].default_value = (color[0], color[1], color[2], 1)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m


def build(turntable=True, slats=28):
    coll = geo.collection(COLL)
    s = bpy.context.scene
    # ---- world: black with a whisper of ambient so shadows are not crushed
    if s.world is None:
        s.world = bpy.data.worlds.new('TB_World')
    w = s.world
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.010, 0.011, 0.014, 1)
    bg.inputs['Strength'].default_value = 1.0
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])

    objs = {}
    # ---- floor
    fl = geo.grid_surface('Showroom_Floor', [[(-80, -80, 0), (80, -80, 0)], [(-80, 80, 0), (80, 80, 0)]],
                          coll=coll, smooth=False, uv=False)
    fl.data.materials.append(_floor_material())
    objs['floor'] = fl
    z_top = 0.0
    if turntable:
        # ---- turntable: thin disc flush with z = 0 on top (the car stands on z = 0),
        # the surrounding floor is lowered by the disc height instead
        h = 0.035
        fl.location.z = -h
        prof = [(0.0, -h), (TURNTABLE_R, -h), (TURNTABLE_R, -0.004), (TURNTABLE_R - 0.004, 0.0), (0.0, 0.0)]
        tt = geo.revolve('Showroom_Turntable', prof, segments=160, axis='Z', coll=coll, sharp_angle=30)
        mats.assign(tt, mats.custom('Showroom_Turntable', base_color=(0.013, 0.013, 0.015), metallic=0.0, roughness=0.30))
        ring_p = [(TURNTABLE_R + 0.012, -h), (TURNTABLE_R + 0.012, -0.006), (TURNTABLE_R + 0.034, -0.006), (TURNTABLE_R + 0.034, -h)]
        ring = geo.revolve('Showroom_Turntable_LED', ring_p, segments=160, axis='Z', coll=coll, sharp_angle=30)
        ring.data.materials.append(_emit('Showroom_LED_Ring', (0.75, 0.86, 1.0), 6.0))
        objs['turntable'] = tt
        objs['ring'] = ring
    # ---- circular wall + vertical light slats
    wall_prof = [(WALL_R, -0.05), (WALL_R, 7.0)]
    wall = geo.revolve('Showroom_Wall', wall_prof, segments=96, axis='Z', coll=coll, flip=True, sharp_angle=None)
    mats.assign(wall, mats.custom('Showroom_Wall', base_color=(0.004, 0.004, 0.005), roughness=0.8))
    objs['wall'] = wall
    slat_mat = _emit('Showroom_Slat', (1.0, 0.93, 0.84), 5.0)
    verts, faces = [], []
    for k in range(slats):
        a = 2.0 * math.pi * (k + 0.5) / slats
        r = WALL_R - 0.25
        hw = 0.045
        z0, z1 = 0.25, 4.6 + 0.9 * math.sin(k * 2.399)
        c, sn = math.cos(a), math.sin(a)
        tx, ty = -sn, c
        base = len(verts)
        verts += [(r * c - tx * hw, r * sn - ty * hw, z0), (r * c + tx * hw, r * sn + ty * hw, z0),
                  (r * c + tx * hw, r * sn + ty * hw, z1), (r * c - tx * hw, r * sn - ty * hw, z1)]
        faces.append((base, base + 1, base + 2, base + 3))
    sl = geo.new_object('Showroom_Slats', verts, faces, coll=coll, smooth=False)
    sl.data.materials.append(slat_mat)
    geo.recalc_normals(sl)
    objs['slats'] = sl

    # ---- lights
    A = studio._area
    objs['key'] = A('Show_Key_Top', (0.0, 0.2, 4.4), (0, 0.2, 0), (4.6, 8.6), 5200.0, coll=coll)
    objs['strip_l'] = A('Show_Strip_L', (5.2, 0.0, 1.9), (0, 0, 0.55), (0.9, 8.5), 2300.0, coll=coll)
    objs['strip_r'] = A('Show_Strip_R', (-5.2, 0.0, 1.9), (0, 0, 0.55), (0.9, 8.5), 2000.0, coll=coll)
    objs['rim_f'] = A('Show_Rim_Front', (0.0, -7.0, 2.6), (0, -1.0, 0.5), (6.5, 1.2), 1500.0, coll=coll, color=(0.9, 0.95, 1.0))
    objs['rim_b'] = A('Show_Rim_Back', (0.0, 7.2, 2.8), (0, 1.0, 0.5), (6.5, 1.2), 1700.0, coll=coll, color=(0.9, 0.95, 1.0))
    objs['sweep'] = A('Show_Sweep', (0.0, -5.0, 2.7), (0.0, -5.0, 0.0), (5.0, 0.35), 0.0, coll=coll, color=(0.85, 0.93, 1.0))
    for k in ('key', 'strip_l', 'strip_r', 'rim_f', 'rim_b', 'sweep'):
        objs[k]['base_energy'] = objs[k].data.energy
    objs['sweep']['base_energy'] = 2600.0
    return objs


def base_energies(objs):
    return {k: objs[k]['base_energy'] for k in ('key', 'strip_l', 'strip_r', 'rim_f', 'rim_b', 'sweep')}
