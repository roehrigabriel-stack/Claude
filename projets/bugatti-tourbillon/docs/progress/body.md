# Body shell: progress log

## Status (agent 2, took over from agent 1)
- [x] Read brief, spec, refs; measured blueprint -> out/renders/body/meas/measure.txt (measure.py)
- [x] out/scripts/body/check.py: numeric silhouette check of the skin vs blueprint (side top/bottom, plan, front/rear widths)
- [x] body.py rewritten: rails retuned (nose plan rounder, roof +1 cm, deck channel V below spine, buttress ridge P,
      tail edge ends at y 2.218), full panel split, holes, recesses, liners, spine, C-line, doors on hinges
- [ ] Stage A shape iteration on overlays (in progress)
- [ ] Stage B check door_L=1, gaps, materials vs A4
- [ ] Stage C anchors complete (only door_rear_cut, horseshoe, intakes, headlight, side intake, scoop, rear_opening so far)

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
