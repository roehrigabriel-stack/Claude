"""tb.mats: shared material library (Cycles, procedural, no image files).

Usage
    from tb import mats
    mats.assign(obj, 'paint_primary')            # replace all slots by one material
    mats.assign(obj, 'chrome', append=True)      # add a second slot
    m = mats.get('leather_light')                # get-or-create
    m = mats.custom('MyPart_Red', base_color='#aa1111', roughness=0.4, coat=1.0)

Shared names (see the registry at the bottom):
  paint_primary, paint_secondary, carbon_gloss, carbon_matte,
  glass, glass_dark, glass_clear, glass_red, crystal,
  chrome, aluminum_polished, aluminum_brushed, aluminum_dark, titanium, steel_dark, gold,
  rubber_tire, rubber, plastic_black, plastic_gloss, mesh_grille, underbody,
  brake_disc, caliper, leather_light, leather_dark, alcantara, fabric_light, carpet,
  emit_headlight, emit_drl, emit_tail, emit_brake, emit_indicator, emit_interior,
  emit_cluster, emit_screen, emit_engine, emit_reverse

Emissive materials are driven by the control properties of the root object
(see tb.rig / spec.CTRL_PROPS): they are dark when the property is 0.
"""
import bpy

from . import spec


# ----------------------------------------------------------------- colour helpers
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h, alpha=1.0):
    """'#RRGGBB' (sRGB) -> linear RGBA tuple for Blender colour sockets."""
    h = h.lstrip('#')
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (alpha,)


def _rgba(c):
    if isinstance(c, str):
        return hex_rgba(c)
    c = tuple(c)
    return c if len(c) == 4 else c + (1.0,)


# ----------------------------------------------------------------- node helpers
def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (600, 0)
    return m, nt, out


def _bsdf(nt, out=None, **kw):
    """Principled BSDF with keyword shortcuts."""
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    b.location = (300, 0)
    names = dict(base_color='Base Color', metallic='Metallic', roughness='Roughness', ior='IOR',
                 alpha='Alpha', transmission='Transmission Weight', coat='Coat Weight',
                 coat_roughness='Coat Roughness', coat_ior='Coat IOR', coat_tint='Coat Tint',
                 sheen='Sheen Weight', sheen_roughness='Sheen Roughness', sheen_tint='Sheen Tint',
                 specular='Specular IOR Level', anisotropic='Anisotropic',
                 anisotropic_rotation='Anisotropic Rotation', emission_color='Emission Color',
                 emission_strength='Emission Strength', subsurface='Subsurface Weight')
    for k, v in kw.items():
        sock = b.inputs[names[k]]
        sock.default_value = _rgba(v) if sock.type == 'RGBA' else v
    if out is not None:
        nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    return b


def _texcoord(nt, kind='Object', scale=(1, 1, 1), rotation=(0, 0, 0)):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    tc.location = (-900, 0)
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.location = (-700, 0)
    mp.inputs['Scale'].default_value = scale
    mp.inputs['Rotation'].default_value = rotation
    nt.links.new(tc.outputs[kind], mp.inputs['Vector'])
    return mp.outputs['Vector']


def _bump(nt, height_socket, strength=0.2, distance=0.001, normal_in=None):
    bp = nt.nodes.new('ShaderNodeBump')
    bp.location = (100, -300)
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    nt.links.new(height_socket, bp.inputs['Height'])
    if normal_in is not None:
        nt.links.new(normal_in, bp.inputs['Normal'])
    return bp.outputs['Normal']


def _noise(nt, vec, scale=50.0, detail=2.0, roughness=0.5):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.location = (-450, -200)
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = roughness
    if vec is not None:
        nt.links.new(vec, n.inputs['Vector'])
    return n


def _ramp(nt, fac, stops):
    """stops: [(pos, colour or grey float), ...]"""
    r = nt.nodes.new('ShaderNodeValToRGB')
    r.location = (-200, -200)
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = (col, col, col, 1.0) if isinstance(col, (int, float)) else _rgba(col)
    nt.links.new(fac, r.inputs['Fac'])
    return r.outputs['Color']


# ----------------------------------------------------------------- generic builders
def custom(name, **kw):
    """Get-or-create a simple Principled material. Keywords: base_color ('#hex' or rgb),
    metallic, roughness, coat, coat_roughness, transmission, ior, alpha, sheen,
    anisotropic, emission_color, emission_strength, specular, subsurface."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m, nt, out = _new(name)
    _bsdf(nt, out, **kw)
    return m


def emissive(name, color, strength, prop, off_color='#1a1a1a', off_roughness=0.25, off_metallic=0.0):
    """Emissive material whose strength = `strength` * TOURBILLON[prop].
    When the property is 0 the surface looks like an unlit lens / LED element."""
    from . import rig
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=off_color, roughness=off_roughness, metallic=off_metallic,
              emission_color=color)
    lvl = nt.nodes.new('ShaderNodeValue')
    lvl.name = 'TB_LEVEL'
    lvl.label = 'driven by TOURBILLON["%s"]' % prop
    lvl.location = (-200, -350)
    lvl.outputs[0].default_value = 0.0
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.location = (50, -350)
    mul.inputs[1].default_value = strength
    nt.links.new(lvl.outputs[0], mul.inputs[0])
    nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    m['tb_prop'] = prop
    rig.drive_node_value(m, 'TB_LEVEL', prop)
    return m


# ----------------------------------------------------------------- specific builders
def _paint(name, color, metallic=0.35, roughness=0.36, flake=0.25):
    """Car paint: slightly metallic base with micro flakes under a glossy clear coat."""
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=color, metallic=metallic, roughness=roughness,
              coat=1.0, coat_roughness=0.025, coat_ior=1.55)
    if flake > 0.0:
        vec = _texcoord(nt, 'Object', scale=(1, 1, 1))
        vo = nt.nodes.new('ShaderNodeTexVoronoi')
        vo.location = (-450, -250)
        vo.inputs['Scale'].default_value = 2600.0
        nt.links.new(vec, vo.inputs['Vector'])
        nrm = _bump(nt, vo.outputs['Distance'], strength=flake, distance=0.0002)
        nt.links.new(nrm, b.inputs['Normal'])      # base layer only: the clear coat stays smooth
    return m


def _carbon(name, gloss=True):
    """2x2 twill carbon fibre weave (procedural) with optional clear coat."""
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=(0.012, 0.013, 0.015), metallic=0.0, roughness=0.42 if gloss else 0.6,
              coat=1.0 if gloss else 0.0, coat_roughness=0.04, specular=0.6)
    vec = _texcoord(nt, 'Object', scale=(1, 1, 1))
    tow = 380.0     # weave frequency (about 2.6 mm tows)
    w1 = nt.nodes.new('ShaderNodeTexWave')
    w1.location = (-450, 150)
    w1.wave_type = 'BANDS'
    w1.bands_direction = 'DIAGONAL'
    w1.wave_profile = 'SAW'
    w1.inputs['Scale'].default_value = tow / 6.283
    nt.links.new(vec, w1.inputs['Vector'])
    ck = nt.nodes.new('ShaderNodeTexChecker')
    ck.location = (-450, -100)
    ck.inputs['Scale'].default_value = tow / 3.1416
    nt.links.new(vec, ck.inputs['Vector'])
    mix = nt.nodes.new('ShaderNodeMath')
    mix.operation = 'MULTIPLY'
    mix.location = (-250, 50)
    nt.links.new(w1.outputs['Fac'], mix.inputs[0])
    nt.links.new(ck.outputs['Fac'], mix.inputs[1])
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    add.location = (-100, 50)
    add.inputs[1].default_value = 0.0
    nt.links.new(mix.outputs[0], add.inputs[0])
    w2 = nt.nodes.new('ShaderNodeTexWave')
    w2.location = (-450, -350)
    w2.wave_type = 'BANDS'
    w2.bands_direction = 'DIAGONAL'
    w2.wave_profile = 'SIN'
    w2.inputs['Scale'].default_value = tow / 6.283
    nt.links.new(vec, w2.inputs['Vector'])
    col = _ramp(nt, w2.outputs['Fac'], [(0.0, (0.006, 0.0065, 0.008)), (1.0, (0.035, 0.037, 0.042))])
    nt.links.new(col, b.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.location = (50, 150)
    rr.inputs['To Min'].default_value = 0.30 if gloss else 0.5
    rr.inputs['To Max'].default_value = 0.55 if gloss else 0.7
    nt.links.new(w1.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    nrm = _bump(nt, w2.outputs['Fac'], strength=0.15, distance=0.0003)
    nt.links.new(nrm, b.inputs['Normal'])
    return m


def _thin_glass(name, tint=(0.80, 0.90, 0.93), darkness=0.0, roughness=0.0):
    """Fast, clean 'architectural' glass for single-surface or thin solid panes:
    a Fresnel mix of a tinted transparent BSDF and a sharp glossy BSDF.
    darkness 0 = clear, 0.8 = privacy tint."""
    m, nt, out = _new(name)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    tr.location = (0, 100)
    k = 1.0 - darkness
    tr.inputs['Color'].default_value = (tint[0] * k, tint[1] * k, tint[2] * k, 1.0)
    gl = nt.nodes.new('ShaderNodeBsdfGlossy')
    gl.location = (0, -100)
    gl.inputs['Roughness'].default_value = roughness
    gl.inputs['Color'].default_value = (1, 1, 1, 1)
    fr = nt.nodes.new('ShaderNodeFresnel')
    fr.location = (0, 300)
    fr.inputs['IOR'].default_value = 1.5
    mx = nt.nodes.new('ShaderNodeMixShader')
    mx.location = (300, 0)
    nt.links.new(fr.outputs['Fac'], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
    nt.links.new(gl.outputs['BSDF'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    m.blend_method = 'BLEND'
    return m


def _crystal(name, color=(1.0, 1.0, 1.0)):
    """Real refractive glass for SOLID closed meshes (crystal console parts, lenses)."""
    m, nt, out = _new(name)
    _bsdf(nt, out, base_color=color, roughness=0.0, transmission=1.0, ior=1.52)
    return m


def _metal(name, color, roughness, anisotropic=0.0, brushed=False, coat=0.0):
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=color, metallic=1.0, roughness=roughness, anisotropic=anisotropic, coat=coat)
    if brushed:
        vec = _texcoord(nt, 'Object', scale=(1.0, 220.0, 220.0))
        n = _noise(nt, vec, scale=18.0, detail=3.0, roughness=0.6)
        nrm = _bump(nt, n.outputs['Fac'], strength=0.06, distance=0.0002)
        nt.links.new(nrm, b.inputs['Normal'])
    return m


def _rubber(name, tire=False):
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=(0.018, 0.018, 0.019), roughness=0.78 if tire else 0.6, specular=0.35)
    vec = _texcoord(nt, 'Object', scale=(1, 1, 1))
    n = _noise(nt, vec, scale=900.0, detail=2.0)
    nrm = _bump(nt, n.outputs['Fac'], strength=0.08, distance=0.0002)
    nt.links.new(nrm, b.inputs['Normal'])
    return m


def _leather(name, color, roughness=0.5):
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=color, roughness=roughness, specular=0.4, sheen=0.15, sheen_roughness=0.4)
    vec = _texcoord(nt, 'Object', scale=(1, 1, 1))
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.location = (-450, -250)
    vo.feature = 'DISTANCE_TO_EDGE'
    vo.inputs['Scale'].default_value = 900.0
    nt.links.new(vec, vo.inputs['Vector'])
    nrm = _bump(nt, vo.outputs['Distance'], strength=0.12, distance=0.0003)
    nt.links.new(nrm, b.inputs['Normal'])
    return m


def _fabric(name, color, roughness=0.9, sheen=0.6, scale=1400.0, strength=0.25):
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=color, roughness=roughness, sheen=sheen, sheen_roughness=0.5, specular=0.2)
    vec = _texcoord(nt, 'Object', scale=(1, 1, 1))
    n = _noise(nt, vec, scale=scale, detail=3.0, roughness=0.7)
    nrm = _bump(nt, n.outputs['Fac'], strength=strength, distance=0.0004)
    nt.links.new(nrm, b.inputs['Normal'])
    return m


def _mesh_grille(name):
    """Dark metal diamond mesh with see-through holes (alpha), for grilles and vents.
    Uses Object coordinates: apply on roughly planar panels."""
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=(0.02, 0.02, 0.022), metallic=1.0, roughness=0.38)
    vec = _texcoord(nt, 'Object', scale=(1, 1, 1), rotation=(0.6, 0.6, 0.785))
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.location = (-450, -250)
    vo.feature = 'DISTANCE_TO_EDGE'
    vo.distance = 'MANHATTAN'
    vo.inputs['Scale'].default_value = 95.0
    vo.inputs['Randomness'].default_value = 0.0
    nt.links.new(vec, vo.inputs['Vector'])
    lt = nt.nodes.new('ShaderNodeMath')
    lt.operation = 'LESS_THAN'
    lt.location = (-200, -250)
    lt.inputs[1].default_value = 0.11
    nt.links.new(vo.outputs['Distance'], lt.inputs[0])
    nt.links.new(lt.outputs[0], b.inputs['Alpha'])
    m.blend_method = 'HASHED'
    return m


def _brake_disc(name):
    """Carbon-ceramic disc: dark grey, satin, with a faint circular texture."""
    m, nt, out = _new(name)
    b = _bsdf(nt, out, base_color=(0.045, 0.045, 0.048), metallic=0.3, roughness=0.5)
    vec = _texcoord(nt, 'Object', scale=(1, 1, 1))
    n = _noise(nt, vec, scale=260.0, detail=4.0, roughness=0.7)
    col = _ramp(nt, n.outputs['Fac'], [(0.3, (0.03, 0.03, 0.032)), (0.7, (0.07, 0.07, 0.075))])
    nt.links.new(col, b.inputs['Base Color'])
    return m


# ----------------------------------------------------------------- registry
C = spec.COLORS
REGISTRY = {
    # exterior
    'paint_primary':     lambda n: _paint(n, C['paint_primary'], metallic=0.30, roughness=0.38, flake=0.20),
    'paint_secondary':   lambda n: _paint(n, C['paint_secondary'], metallic=0.45, roughness=0.30, flake=0.25),
    'carbon_gloss':      lambda n: _carbon(n, gloss=True),
    'carbon_matte':      lambda n: _carbon(n, gloss=False),
    'glass':             lambda n: _thin_glass(n, darkness=0.12),
    'glass_dark':        lambda n: _thin_glass(n, tint=(0.75, 0.82, 0.88), darkness=0.72),
    'glass_clear':       lambda n: _thin_glass(n, tint=(1.0, 1.0, 1.0), darkness=0.0),
    'glass_red':         lambda n: _thin_glass(n, tint=(0.9, 0.05, 0.04), darkness=0.15),
    'crystal':           lambda n: _crystal(n),
    'chrome':            lambda n: _metal(n, (0.92, 0.92, 0.93), 0.04),
    'aluminum_polished': lambda n: _metal(n, (0.88, 0.89, 0.90), 0.12),
    'aluminum_brushed':  lambda n: _metal(n, (0.80, 0.81, 0.83), 0.28, anisotropic=0.6, brushed=True),
    'aluminum_dark':     lambda n: _metal(n, (0.20, 0.21, 0.23), 0.32),
    'titanium':          lambda n: _metal(n, (0.48, 0.45, 0.42), 0.34),
    'steel_dark':        lambda n: _metal(n, (0.10, 0.10, 0.11), 0.45),
    'gold':              lambda n: _metal(n, (0.83, 0.62, 0.28), 0.22),
    'rubber_tire':       lambda n: _rubber(n, tire=True),
    'rubber':            lambda n: _rubber(n, tire=False),
    'plastic_black':     lambda n: custom(n, base_color=(0.012, 0.012, 0.013), roughness=0.55),
    'plastic_gloss':     lambda n: custom(n, base_color=(0.006, 0.006, 0.007), roughness=0.08, coat=0.5),
    'mesh_grille':       lambda n: _mesh_grille(n),
    'underbody':         lambda n: custom(n, base_color=(0.01, 0.01, 0.01), roughness=0.7),
    'brake_disc':        lambda n: _brake_disc(n),
    'caliper':           lambda n: custom(n, base_color=C['caliper'], roughness=0.3, coat=1.0, metallic=0.2),
    # interior
    'leather_light':     lambda n: _leather(n, C['leather_light'], 0.48),
    'leather_dark':      lambda n: _leather(n, C['leather_dark'], 0.5),
    'alcantara':         lambda n: _fabric(n, (0.020, 0.024, 0.030), roughness=0.95, sheen=0.8),
    'fabric_light':      lambda n: _fabric(n, '#8FA6B8', roughness=0.85, sheen=0.5, scale=700.0, strength=0.4),
    'carpet':            lambda n: _fabric(n, (0.015, 0.018, 0.024), roughness=1.0, sheen=0.3, scale=500.0, strength=0.6),
    # lights (strength in W/m2-ish emission units; tuned for the studio scenes)
    'emit_headlight':    lambda n: emissive(n, (1.0, 0.97, 0.92), 60.0, 'headlights', off_color='#c8ccd0', off_roughness=0.15, off_metallic=0.8),
    'emit_drl':          lambda n: emissive(n, (0.92, 0.96, 1.0), 25.0, 'drl', off_color='#d0d4d8', off_roughness=0.2),
    'emit_tail':         lambda n: emissive(n, (1.0, 0.03, 0.015), 14.0, 'taillights', off_color='#3a0606', off_roughness=0.12),
    'emit_brake':        lambda n: emissive(n, (1.0, 0.02, 0.01), 40.0, 'brake_lights', off_color='#3a0606', off_roughness=0.12),
    'emit_indicator':    lambda n: emissive(n, (1.0, 0.45, 0.02), 30.0, 'indicators', off_color='#b0b4b8', off_roughness=0.2),
    'emit_reverse':      lambda n: emissive(n, (1.0, 1.0, 1.0), 20.0, 'headlights', off_color='#c0c0c0'),
    'emit_interior':     lambda n: emissive(n, (0.55, 0.78, 1.0), 6.0, 'interior_lights', off_color='#20262c', off_roughness=0.3),
    'emit_cluster':      lambda n: emissive(n, (0.85, 0.93, 1.0), 4.0, 'cluster_glow', off_color='#d8d8d4', off_roughness=0.3),
    'emit_screen':       lambda n: emissive(n, (0.35, 0.60, 1.0), 3.0, 'screen', off_color='#050608', off_roughness=0.05),
    'emit_engine':       lambda n: emissive(n, (1.0, 0.75, 0.45), 5.0, 'engine_glow', off_color='#2a2a2a'),
}


def get(name):
    """Get-or-create a library material by name."""
    m = bpy.data.materials.get(name)
    if m is None:
        if name not in REGISTRY:
            raise KeyError('unknown material %r (known: %s)' % (name, ', '.join(sorted(REGISTRY))))
        m = REGISTRY[name](name)
        m.name = name
    return m


def assign(obj, name_or_mat, append=False):
    """Assign a material (library name or Material) to a mesh object."""
    m = get(name_or_mat) if isinstance(name_or_mat, str) else name_or_mat
    if not append:
        obj.data.materials.clear()
    obj.data.materials.append(m)
    return m


def assign_faces(obj, name_or_mat, predicate):
    """Add a material slot and assign it to faces whose centre satisfies predicate(center, polygon)."""
    m = get(name_or_mat) if isinstance(name_or_mat, str) else name_or_mat
    me = obj.data
    if m.name not in [s.name for s in me.materials if s]:
        me.materials.append(m)
    idx = [s.name if s else None for s in me.materials].index(m.name)
    for p in me.polygons:
        if predicate(p.center, p):
            p.material_index = idx
    return m
