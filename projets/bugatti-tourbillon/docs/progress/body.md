# Body shell: progress log

## Status (agent 2, took over from agent 1)
- [x] Read brief, spec, refs; measured blueprint -> out/renders/body/meas/measure.txt (measure.py)
- [x] out/scripts/body/check.py: numeric silhouette check of the skin vs blueprint (side top/bottom, plan, front/rear widths)
- [x] body.py rewritten: rails retuned (nose plan rounder, roof +1 cm, deck channel V below spine, buttress ridge P,
      tail edge ends at y 2.218), full panel split, holes, recesses, liners, spine, C-line, doors on hinges
- [x] Stage A: overlays (out/renders/body/a8/sheet_all.png) match within ~2 cm except: plan nose y -2.35..-2.25
      4-10 cm too wide at the lower lip, front-view fender side z .75-.8 2-4 cm narrow (check.py lists '*')
- [x] mesh_region fixed: keep every cell touching the region, snap all outline verts (no saw-tooth edges);
      openings are parameter-space polygons from Inverter(facing=...) (no wrong-sheet holes); backing skin removed
      (it poked through concave areas); weld 0.3*ds kills slivers
- [x] door_L=1 renders (a7): door rises, roughly butterfly; clearance not yet verified numerically
- [x] Stage C anchors in publish_anchors() + out/renders/body/anchors.json
- [ ] character pass vs A4 (bonnet dome / valley / fender crease), final-quality build + tri count

## How it works
- body_lib.Skin: half skin through 9 rails C V P H K W L B U (see body.py docstring); s ~ y, t = rail index.
- Panels = PANELS list in priority order, each region = own - holes - all previous; shrunk by GAP (2.2 mm).
  Solidify with material_offset/_rim -> dark inner faces and dark shut-line rims. 'sym' panels use mirror modifier
  (moved to first), 'pair' panels use geo.mirror_copy -> _R.
- Body_Recess_Inner: dark skin 12 mm inside everything except glass/door/holes (no see-through gaps).
- Scratch: out/scripts/body/go.sh OUTDIR VIEWS [samples=8] [door_L=1] -> renders + overlays + sheet_all.png
  (render.py adds placeholder wheels).

## Decisions
- Two-tone after A4: paint_primary = fenders (incl. bonnet flanks), bumper, doors, quarter inside the C;
  paint_secondary = bonnet centre V, roof/pillars, deck, tail, rear haunches + buttresses, spine.
- Door rear tip of glass limited by the door rear cut (no fixed quarter glass).

## Known defects
(first full build pending)
