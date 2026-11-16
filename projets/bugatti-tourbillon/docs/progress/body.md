# Body shell: progress log

## Status: stages A, B, C done (agent 2). Builds cleanly in preview (~160k tris) and final (~661k tris).
- Shape: 9-rail half skin (body.py rails()), overlays out/renders/body/b3/sheet_all.png (side/rear/top) and
  a8 (front): within ~2 cm except the items under Known defects. Numeric check: out/scripts/body/check.py.
- Panels, gaps (2 x 2.2 mm, dark solidify rims / inner faces), two-tone after A4, glazing, doors on hinges.
- Openings with dark recess walls: horseshoe, lower intakes, headlights, side intakes, deck scoops, rear dish.
- Liners close the wells (tube + 28 mm flange behind the arch edge + inner wall at x 0.52).
- Door swing: out/scripts/body/door_check.py, spec hinge clears (max penetration 0 at 10..68 deg).
- Anchors: ctx.data['body'] and out/renders/body/anchors.json (rewritten on every build).

## How it works
- body_lib.Skin: half skin S(s, t), s ~ y, t = rail index (C V P H K W L B U). Column s=-2.40 = horseshoe
  outline, column s=2.27 = tail edge + rear opening outline. Skin.normal has one global orientation sign.
- PANELS (priority order): region = own - holes - all previous, shrunk by GAP; mesh_region keeps every grid
  cell touching the region and snaps outline vertices onto the boundary, weld 0.3*ds, orientation by majority.
- Shut lines (y_front, cl_low, x_strip, x_v, x_bi, x_can, x_ws) are Pchip curves -> smooth cut lines.
- OPENINGS: 2D polygon in a projection -> Inverter(facing=...) -> loop in (s, t) -> hole region in parameter
  space and recess tunnel from the same loop (anchors follow automatically if a polygon is moved).
- 'sym' panels: mirror modifier (first) + solidify; 'pair' panels: geo.mirror_copy -> _R.
- Scratch: out/scripts/body/go.sh OUTDIR VIEWS [samples=N] [final] [door_L=1] [cam=ex,ey,ez,tx,ty,tz,lens,name]
  (placeholder wheels, overlays, sheet_all.png); objs.py (per-object tris), door_check.py, check.py.

## Objects
TB_Body: Body_Bonnet (dark V), Body_Fender_F_L/R, Body_Bumper_F, Body_Door_L/R (frame above belt dark),
Body_Sill_L/R, Body_Lower_F, Body_Lower_R (carbon), Body_Roof (pillars + roof frame), Body_Quarter_L/R (inside
the C), Body_Rear_L/R (haunch + buttress), Body_Deck, Body_Tail, Body_Spine, Body_CLine_L/R (static lower+rear
leg), Body_CLine_Door_L/R (roof-edge part, on the doors), Body_Horseshoe_Lip, Body_Liner_FL/FR/RL/RR,
Body_Recess_Horseshoe / _Intake_F_L/R / _Headlight_L/R / _SideIntake_L/R / _Scoop_L/R / _Rear.
TB_Glass: Glass_Windshield, Glass_Roof, Glass_Side_L/R. Doors + side glass + door C-line under HINGE_Door_L/R.

## Anchors (keys stable): horseshoe{outline,center}, headlight_L{outline,normal,inner_end,outer_end},
intake_front_L, side_intake_L, deck_scoop_L, tail_edge (centre -> left corner), rear_opening, wing_seat
(skin line at y = WING pivot y), mirror_mount_L{point,normal} (~0.823,-0.74,0.865), roundel_L{center,normal}
(~0.786,0.571,0.92), sill_gill_zone_L{corners,normal}, cowl_line, door_rear_cut, door_inner_clearance
(x of door inner face at y -0.40: ~0.93 at z .30, 0.87 at .73, 0.80 at .82), roof_inner_height (~1.164).
Right-hand items = mirror x.

## Decisions
- Two-tone after A4 (not REFERENCE 3.3): primary = fenders + bonnet flanks, bumper, doors, quarter in the C.
- Side glass entirely on the door (rear tip limited by the door rear cut); no fixed quarter glass.
- No separate backing skin (it poked through concave areas); dark solidify inner faces close the gaps.

## Known defects
- Plan view: lower nose lip 4-8 cm wider than the drawing at y -2.35..-2.25; front-view fender side 2-4 cm
  narrow at z 0.75-0.80. Upper tail edge flat-ish (light bar curl only at the corners).
- Fender crown / headlight-to-A-pillar crease softer than A4; bumper surround reads larger and paler than A4.
- Some highlight waviness remains on the front fender tops near the headlights (rail interplay K/H/W).
- Side intake behind the door is a deep black hole (A4 shows it dark; photos of launch cars hide it).
