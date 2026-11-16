# Interior progress log

Owner files: src/tb/parts/interior.py, src/tb/parts/interior_lib.py, out/scripts/interior/, out/renders/interior/

## Status
- [x] Read brief, spec, shared API, studied refs B1..B4 (crops in out/scripts/interior/crop_*.png)
- [x] First full pass of interior.py existed and builds without errors (318k tris preview)
- [ ] Render + compare iterations
- [ ] Final quality build, triangle count

## Reference notes
- Wheel: D-shape, flat bottom, pale blue leather rim, navy sections at 12 o'clock, aluminium
  insert at 6 o'clock. Horizontal spokes at 3/9 with aluminium switch pods; dark lower spokes.
  Fixed rounded-square hub pod (pale blue, EB). Cluster above hub: big centre dial on top,
  two small dials lower left/right, polished skeleton frame. Small dark rotary knobs either side of hub.
- Dash: pale blue wing, navy upper "arches" over each side, aluminium spine from dash top
  widening into the console. Slim vertical vents with chrome lips beside the spine and at the outer ends.
- Console: aluminium teardrop frame; 2 large crystal knobs on top, small start button/screen,
  toggles and small knobs, drive selector, then a polished stripe running back on a dark tunnel.
- Seats: pale blue rounded bolsters, textured fabric centres, dark carbon shell, headrest slot.
- Door card: pale blue with textured oval inset, navy border, chrome handle front-top.
- Headliner dark with aluminium centre stripe.

## Decisions
(none yet)

## Known defects
(none yet)

## Session 2 log
- Scripts: out/scripts/interior/render.sh SUFFIX (5-view sheet), render2.sh (roof hidden via env TB_INT_NOROOF=1, doors open), render3.sh (dark, lights/cluster/screen on)
- Note: use --cam="..." (with =) because argparse chokes on negative numbers.
- Fixes done: dash front edge deep on centreline (Y_COWL+0.03) back to -1.22 at A-pillars; door card rear clamped to diagonal shut line - 4.5 cm;
  leather tints darker (_tint in build), alcantara sheen lowered; console frame rebuilt with exact window edge (no stair-steps).
- Session 2 end state: builds clean (preview ~290k tris, final ~420k). Envelope check script: out/scripts/interior/check.py (all objects inside z_headliner / belt / door rule; door cards <= door_rear_y(z)-4 cm).
- Portrait pop-up screen (0.13 x 0.18) with UI elements in emit_screen on a dark glass face; rig.hinge('Screen') prop screen; steering hinge 'SteeringWheel' prop steer, +120 deg (verified rim turns, hub fixed).
- Remaining differences: dash is smooth but box-like (no sculpted arches / Y-shaped spine of B1), seat piping names '.001' collisions (cosmetic), console crystal knobs smaller than B3, no embossed 'Tourbillon' script on door pocket, floor/footwell flat.

## Round 2 (critic report docs/reviews/interior_r1.md)
- Own materials only (Interior_*: LeatherPale/Dark/Slate, Alcantara, Carpet, Fabric, Stitch, DashTop shader, Ambient emissive) via L.IM wrapper in interior_lib; shared library untouched.
- Dash rebuilt: crowned hoods around a 5.5 cm centre valley (dash_profile top = ZDT - valley...), shader-based curved dark shelf / pale split.
- Floor blue carpet, footwell side panels pale leather; wheel rim slate with pale top band + posts; round domed hub; console narrowed (x0.78) with 3 glass knobs, 8 varied keys + red, glass start lever;
  cluster larger (0.25 m) with window / subdials / label / triangular cut-outs; seats wider + higher bolsters + oval headrest slot; door card pull loop, pocket lid + Tourbillon script, carbon trim; screen portrait, arm, knob; buckle anchored on console.
- Preview 211k tris. Renders suffix _r2 (sheet_r2, sheet_r2e dark, sheet_r2s steer/door).
- Round 3: sill tread widened to x 0.80, matte carbon sill, tub walls leather (no black void), own emissive Interior_ClusterGlow / ScreenGlow / Ambient (x3 stronger), lamps 26/14/11 W (were 40/25/18 in r3 renders, slightly burnt, lowered). Checked in body: no pokes seen (door_dark_r3d, wind_r3, top_r3).
