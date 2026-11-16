# Front and exterior details: progress log

## Status
- [x] src/tb/parts/front.py + front_lib.py: built, runs after body (reads ctx.data['body']).
- Method: Opening(outline) = ruled surface between lower and upper outline edge per x (flush by construction);
  panels inset along local outward normal; detail items placed with Opening.pos(u,v,off); side items snapped with Raycaster.
- Done: horseshoe grille (mesh_grille panel, chrome frame, rib, spine line, red badge + text), intakes (mesh, blade, 4 vanes, frame),
  splitter (hull of Body_Lower_F, carbon, chrome line, winglets), headlights (housing, smoked lens, 4 LED, DRL, indicator,
  2 spot lamps driven by 'headlights' 400 W), mirrors (shell, glass, stalk), wipers, 3 sill gills + edges, tricolour, EB roundels. Right side = mirror_copy.
- Scratch: out/scripts/front/cl.sh OUTNAME [extra render args] = 4 close-ups (hl, nose, side, mir).

## Known defects
- Body headlight opening is ragged (body agent's work); lens follows the anchor outline.
