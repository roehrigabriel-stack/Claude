# Bugatti Tourbillon in Blender: shared brief for every agent

Read this file completely before doing anything. It is the contract between all
the agents that build and review this model.

## 1. Goal

A modular, accurate, realistic 3D model of the **Bugatti Tourbillon** (2024,
V16 hybrid hypercar), generated entirely by Python scripts for **Blender 4.2 LTS**
(Cycles), with working doors, lights, wing, steering and wheels, followed by a
showcase animation. Quality bar: it must be instantly recognisable as a
Tourbillon from every angle and look like a professional studio render, not a
toy. Proportions must match the blueprint, details must match the photos.

Everything is procedural: no downloaded 3D models, no image textures (procedural
shaders only). Code is the deliverable: a clean rebuild from scripts must
reproduce the model.

## 2. Where things are

```
/home/user/Claude/projets/bugatti-tourbillon/
  docs/BRIEF.md            this file
  docs/REFERENCE.md        fact sheet + image index (written by the research agent; may appear later, check for it)
  docs/progress/<part>.md  YOUR running progress log (see section 9)
  docs/reviews/            critic reports
  refs/                    reference images supplied by the user (LOOK AT THEM with the Read tool)
  refs/web/                extra reference photos (may appear later, check for them)
  src/tb/spec.py           master dimensions, coordinate frame, control properties  (READ IT)
  src/tb/geo.py            geometry helpers
  src/tb/mats.py           material library
  src/tb/rig.py            control object, drivers, hinges, wheel pivots
  src/tb/studio.py         render settings, preview studio, cameras
  src/tb/build.py          assembles part modules
  src/tb/parts/<part>.py   ONE FILE (or a few) PER PART MODULE: this is what builders write
  src/build.py             CLI: build and save a .blend
  src/render_views.py      CLI: build and render review images
  tools/overlay.py         overlays the blueprint on orthographic renders
  out/                     generated files (renders, .blend); not versioned
```

Reference images in `refs/` (all are crops of the user's two reference sheets, upscaled 3x):

| file | content |
|------|---------|
| A1_bugatti_line_sketch.png | official design sketch: three side profiles (Veyron, Chiron, Tourbillon at the bottom) showing the Bugatti C-line |
| A2_rear34_sketch.png | official rear three-quarter design sketch: light bar, diffuser, rear haunches, wheels |
| A3_blueprint.png | four-view dimensioned drawing (side facing right, front, top with nose to the right, rear). 199.5 px per metre |
| A4_front34_render_twotone.png | front three-quarter render, pale blue + black two-tone: THE colour reference |
| B1_interior_front_dash.png | interior, straight-on view of dashboard, steering wheel, console |
| B2_interior_from_door.png | interior seen through the open driver door |
| B3_interior_side_seat_console.png | interior side view: seat shell, console profile |
| B4_interior_top_door_open.png | interior from above with the door raised |
| B5_side_sketch.png | official side-profile sketch (car facing left) |
| B6_grey_pitlane_front34.png | photo-like render of a grey car, front three-quarter |

## 3. Coordinate frame and dimensions (never deviate)

* Units: metres. Z up. Ground is z = 0.
* Origin: on the ground, on the centreline, at the middle of the wheelbase.
* **The front of the car points to -Y.** Nose tip at y = -2.400, tail at y = +2.271.
* **+X is the car's left side** (driver side, left-hand drive).
* Length 4.671, width 2.051 (max, at the rear haunches), height 1.189, wheelbase 2.740.
* Front axle y = -1.370, rear axle y = +1.370. Wheel centres, tyre sizes, track,
  cabin envelope, door hinge, wing pivot: see `spec.py`. Import them, do not copy numbers.

If you believe a value in `spec.py` is wrong, do NOT edit it: finish with the
current value and report the proposed change (with evidence) in your final answer.

## 4. How a part module is written

`src/tb/parts/<name>.py` must expose `build(ctx)`. Minimal example:

```python
from tb import geo, mats, rig, spec

def build(ctx):
    coll = ctx.collection('Wheels')          # collection 'TB_Wheels'
    root = ctx.module_root('Wheels')         # Empty 'MOD_Wheels', child of the root control
    rim = geo.revolve('Rim_FL', profile, axis='X', origin=spec.WHEELS['FL'], coll=coll)
    mats.assign(rim, 'aluminum_polished')
    steer, spin = rig.wheel_pivots('FL')
    geo.parent(rim, spin)                    # rotating parts follow the spin pivot
    rig.adopt([static_obj], root)            # everything else follows the module root
```

Rules:

* Author mesh data directly in **world coordinates** and leave objects at identity
  (location 0, rotation 0, scale 1). Pivots come from parenting to Empties
  (`rig.module_root`, `rig.door_hinge('L'|'R')`, `rig.wing_hinge()`, `rig.wheel_pivots(key)`,
  or your own `rig.hinge(...)`), never from moving object origins. `geo.parent`
  keeps the world position.
* **Every object must end up parented** (directly or not) under the root control
  object, otherwise it will not move with the car in the animation.
* The model is symmetric: build the left side (+X) and use `geo.mirror_copy(obj, name)`
  for separate right-hand objects (doors, wheels...) or `geo.mod_mirror(obj)` for
  one-piece symmetric parts. Asymmetric items (steering wheel on the left,
  single wiper...) are built once.
* Name objects `<Module>_<Thing>[_L|_R|_FL...]`, e.g. `Body_Door_L`, `Wheel_Rim_FL`.
  Use meaningful, stable names: the animation and other modules look objects up by name.
* Group objects into a small number of logical sub-assemblies under your module
  root if it helps the assembly animation (e.g. `MOD_Wheels` is not needed for
  wheels since each wheel has its pivot; an engine might have `MOD_Engine` only).
* `ctx.quality` is `'preview'` (default, fast) or `'final'`. Use it to pick
  subdivision levels / segment counts: `n = 2 if ctx.final() else 1`.
* Poly budget for the whole car in final quality: about 3 to 4 million triangles.
  Rough share: body 800k, each wheel 150k, interior 700k, chassis+engine 600k, rest 400k.
  Preview quality should be about one quarter of that.
* Use live modifiers (subsurf, bevel, solidify, mirror) when convenient; they
  render fine. Apply them only when a later step needs the real mesh.
* Do not use image textures or external files. Do not `import` other part modules
  (look objects up by name through `bpy.data.objects` / `ctx.data` instead).
* Helper files next to your module must be named `<name>_lib.py` or start with `_`
  (anything else in `parts/` is treated as a buildable module).
* Only edit the files you own (stated in your task). `spec.py`, `geo.py`,
  `mats.py`, `rig.py`, `studio.py`, `build.py` are shared: do not edit them. If
  you need a helper or material that does not exist, write it in your own file
  (`mats.custom(...)`, or build a node tree yourself); mention it in your report
  if it should be promoted to the shared library.

## 5. Shared API cheat sheet (read the source for details)

`tb.geo`
* interpolation: `Pchip(xs, ys)` (monotone, no overshoot), `CSpline(xs, ys)` (C2), `lerp`, `smoothstep`
* curves: `catmull_rom(points, per_seg, closed)`, `bspline(ctrl, n, closed)`, `bezier`, `resample(pts, n, closed)`, `superellipse`, `arc`
* meshes: `new_object(name, verts, faces)`, `grid_surface(name, P[nu][nv])`, `loft(name, sections)`,
  `revolve(name, [(r, a)...], axis, origin)`, `sweep(name, path, profile)`, `curve_tube(name, points, radius)`,
  `extrude_polygon(name, outline, depth, plane)`, `box`, `cylinder`, `uv_sphere`, `torus`, `text_mesh(name, 'BUGATTI', size, extrude)`
* editing: `merge_by_distance`, `recalc_normals`, `flip_normals`, `fill_holes`, `transform_mesh`, `place(obj, loc, rot_deg, scale)`,
  `delete_faces(obj, predicate)`, `separate_faces(obj, predicate, name)`, `apply_modifiers`, `duplicate`, `mirror_copy`, `join`, `boolean`, `radial_copies`
* modifiers: `mod_subsurf`, `mod_solidify`, `mod_bevel`, `mod_mirror`, `mod_weighted_normal`, `mod_array_circular`
* scene: `collection`, `link`, `parent(child, parent)`, `empty`, `world_matrix`, `bounds(objs)`, `shade(obj, smooth, sharp_angle)`
* `Raycaster(objs).cast(origin, direction)` / `.nearest(point)`: snap details onto existing surfaces

`tb.mats`: `mats.assign(obj, 'name')`, `mats.assign(obj, 'name2', append=True)`, `mats.assign_faces(obj, 'name', predicate)`,
`mats.get(name)`, `mats.custom(name, base_color='#hex', metallic=, roughness=, coat=, ...)`, `mats.emissive(name, color, strength, prop)`.
Library names: paint_primary (pale blue), paint_secondary (blue-black), carbon_gloss, carbon_matte, glass, glass_dark,
glass_clear, glass_red, crystal (solid refractive), chrome, aluminum_polished, aluminum_brushed, aluminum_dark, titanium,
steel_dark, gold, rubber_tire, rubber, plastic_black, plastic_gloss, mesh_grille (alpha diamond mesh), underbody, brake_disc,
caliper, leather_light, leather_dark, alcantara, fabric_light, carpet, emit_headlight, emit_drl, emit_tail, emit_brake,
emit_indicator, emit_reverse, emit_interior, emit_cluster, emit_screen, emit_engine.
The `emit_*` materials are dark until their control property is raised.

`tb.rig`
* `rig.ctrl()`: the root Empty `TOURBILLON` holding the control properties (`spec.CTRL_PROPS`):
  door_L, door_R, wing, steer, wheel_spin, headlights, drl, taillights, brake_lights, indicators,
  interior_lights, cluster_glow, screen, engine_glow.
* `rig.door_hinge('L'|'R')`, `rig.wing_hinge()`, `rig.wheel_pivots(key) -> (steer, spin)`
* `rig.hinge(name, pivot, axis, prop, max_angle_deg, translate=None)`: your own driven pivot
* `rig.drive(id_block, data_path, prop, scale, offset, index)`: generic driver (no Python expressions)
* `rig.drive_light(light_object, prop, watts)`: real lamps that follow a control property
* `rig.set_prop(name, value)` for test renders, `rig.key_prop(name, value, frame)` for animation
* `rig.adopt(objs, parent)`, `rig.module_root(name)`, `rig.all_car_objects()`

`tb.studio`: `setup_render(res, samples)`, `preview_studio(style='light'|'dark', center, scale)`,
`shot(path, eye, target, lens, ortho_scale=None)`, `render_views(out_dir, [views])`, `interior_light(power)`.

## 6. Building and rendering

Blender is at `/usr/local/bin/blender` (4.2.23 LTS, CPU only, 4 cores, no GPU, no display).
Always run it in background mode with `--factory-startup`.

```bash
cd /home/user/Claude/projets/bugatti-tourbillon
# build some modules and render standard review views (auto-framed on what was built)
blender -b --factory-startup -P src/render_views.py -- --parts wheels --views f34,left,front \
    --out out/renders/wheels --res 960x540 --samples 24 2>&1 | grep -E "tb.build|Error|Traceback|render_views" 
# options: --style light|dark   --set door_L=1 --set headlights=1   --hide TB_Glass,TB_Body
#          --cabin-light 40   --cam "ex,ey,ez,tx,ty,tz,lens" --name closeup   (repeatable)
#          --quality final   --suffix _v2
# views: front rear left right top f34 f34r r34 r34r low_f34 low_r34 high_f34 high_r34
#        ortho_side ortho_front ortho_rear ortho_top   (fixed-scale orthographic, whole car)
python3 tools/overlay.py out/renders/body     # blueprint lines (magenta) + metric grid over ortho_* renders
# build and save a .blend
blender -b --factory-startup -P src/build.py -- --parts wheels --out out/blend/wheels.blend
```

For anything special write your own small script under `out/scripts/<part>/` using the Python
API (`from tb import build, studio, rig`; see the docstring of `studio.py`).

`render_views.py` also writes ONE contact sheet `sheet<suffix>.png` in the output
folder containing every image of that call (labelled). **Look at the sheet, not at
the individual images** (one Read per iteration); open a single image only when
you need full resolution on a detail. `python3 tools/sheet.py out.png a.png b.png ...`
builds a sheet from any images (for example a render next to a reference crop).
You are expected to iterate: build, render, look at the sheet, fix.

USAGE BUDGET (important): the project runs under tight usage limits and agents
get cut off when the limit is reached. Work in few, large steps: write big
chunks of code per edit, chain build + render + sheet in one shell command, keep
command output short (grep / tail), avoid re-reading files you already know, and
do not narrate. Update your progress log every 10 to 15 tool calls so another
agent can continue from it.

Machine etiquette (several agents share 4 CPU cores):

* Test renders: at most 960x540 and 24 samples unless you really need more
  (close-ups of small details can use `--res 800x600`). Never render animations.
* Prefer a few well chosen views per iteration over many.
* Do not leave Blender processes running in the background when you finish.
* Scratch files go to `out/` (never to `/tmp`). Do not commit to git.

## 7. Quality requirements for geometry and shading

* Smooth, clean surfaces: no faceting on curved panels (enough resolution or
  subdivision), no pinching, no z-fighting, no visible holes, no interpenetration.
* Real thickness where an edge is visible (panel edges, glass edges, tyres, rims).
  Panel gaps: 3 to 5 mm dark gaps between body panels, not just colour changes.
* Small bevels on hard edges so they catch highlights (`geo.mod_bevel`).
* Materials from the library, assigned per part or per face. Every visible
  surface must have a deliberate material.
* Anything that moves must be a separate object parented to its pivot and must
  not intersect its neighbours over its travel.

## 8. Self-review before you report

1. Render the standard views of your part (light studio) and look at each image.
2. Compare with every relevant reference image. Write down the three biggest
   differences you see and fix them. Repeat until the remaining differences are small.
3. For anything rigged: render with the control property at 0 and at 1.
4. Build once with `--quality final` to check it works and report the triangle count
   (the build prints `[stats]` lines).

## 9. Progress log (mandatory, protects against interruptions)

Keep `docs/progress/<part>.md` up to date as you work (update it at least after
each major step): what is done, what is in progress, what is left, known
defects, decisions taken and why. Keep it short (under 60 lines). Your work can
be interrupted at any time by usage limits; this file plus the code on disk
must be enough for you or another agent to continue. Save code to disk early
and often: never keep more than a few minutes of work only in your head.

## 10. Final report format

When done, reply with: (1) what you built (object list by sub-assembly), (2) the
render files that best show the result, (3) triangle counts in preview and final
quality, (4) known defects and limitations, honestly, (5) anything other
modules need to know (anchors, names, `ctx.data` entries), (6) proposed changes
to shared files, if any.
