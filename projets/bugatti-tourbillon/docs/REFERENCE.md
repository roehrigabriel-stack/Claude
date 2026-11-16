# Bugatti Tourbillon reference sheet

Researcher output. Everything marked "(estimate)" is read off photos or the blueprint by eye and is not an official figure.
Sources: S1 = Bugatti newsroom technical sheet `technical-specifications-bugatti-TB-en.pdf` (status 06.2024); S2 = press release 6/21/2024 "The Bugatti Tourbillon: an automotive icon Pour l'eternite"; S3 = press release 10/3/2024 "A new foundation for a new era" (platform); S4 = press release 2/27/2025 "Mastering a new era of aerodynamics"; S5 = press release 12/18/2025 "Exploring the interior concept"; S6 = press release 6/18/2025 "Tourbillon configuration"; S7 = dimensions.com Tourbillon drawing (SVG, vector, rendered by `out/scripts/research/render_svg.py`); P = observed in the photos in `refs/web/` (file names given).
All newsroom documents are at newsroom.bugatti.com (press-release pages and `/api/en/press-releases/pdf/<slug>`).

## 1. Verified specifications

| item | value | source |
|---|---|---|
| Length | 4,671 mm | S1 |
| Width | 2,051 mm body, 2,165 mm over mirrors (mirrors add about 57 mm each side) | S1 |
| Height | 1,189 mm | S1 |
| Wheelbase | 2,740 mm | S1 |
| Mass | below 1,995 kg (DIN) | S1 |
| Front / rear track | NOT PUBLISHED. Blueprint gives about 1.70 m front and 1.72 m rear tyre-centre to tyre-centre (estimate, drawn tyres have equal width front and rear so this is rough). `spec.py` uses 1.72 / 1.66 | S7 (estimate) |
| Ground clearance | NOT PUBLISHED. Blueprint: lowest body edge (front splitter, sill) about 0.10 to 0.14 m above ground (estimate) | S7 (estimate) |
| Tyres | Michelin Pilot Sport Cup 2, bespoke: 285/35 R20 front, 345/30 R21 rear. Sidewall text in photos reads "285/35 ZR 20" and "345/30 ZR 21" (confirmed). Sidewall has a chequered-flag band pattern near the tread shoulder | S2, P wheel_closeup_02_front, wheel_closeup_03_rear |
| Tyre outer diameter | about 0.71 m front (computed: 2 x 0.285 x 0.35 + 0.508), about 0.74 m rear (2 x 0.345 x 0.30 + 0.5334). Blueprint measures 0.716 m both ends, 0.572 m for the wheel face circle | computed, S7 |
| Brakes | carbo-ceramic discs (drilled, visible in photos), brake-by-wire integrated with a movable pedal box. Calipers: black, white "BUGATTI" lettering, fixed multi-piston type. Piston counts and disc diameters are NOT in any official document (a third-party site claims 8 piston front, 6 rear: unverified). Nine caliper colours are offered | S2, S6, P wheel_closeup_03_rear |
| Wheels | alloy, 5 forked spokes (see 3.8), diamond-cut / duo-tone options; centre cap with the EB oval | S6, P |
| Powertrain | 8.3 l naturally aspirated V16 (90 deg, 1,000 hp, 900 Nm, 9,000 rpm, 252 kg), 3 e-motors (2 x 250 kW on front axle, 1 x 250 kW at rear), 1,800 hp total, 8-speed longitudinal DCT, 24.8 kWh 800 V T-shaped battery in the central tunnel, AWD with torque vectoring | S1, S2, S3 |
| Packaging | front: frunk between two radiators, 5 of 8 radiators at the front (2 outer ones feed the engine, centre ones fed by the horseshoe grille), front e-axle behind the luggage compartment. Rear: V16 with third e-motor, fuel tanks moved to the sides. Rear crash structure is integrated in the diffuser (open rear end, no rear beam) | S3, S2 |
| Structure | T800 carbon monocoque with the battery structural, aluminium front and rear frames, multi-link suspension with 3D printed uprights and arms (blue springs and dampers visible in chassis photos) | S2, P chassis_03_rear34 |
| Exhaust | two finishers, one on each side of the number plate recess, at the top of the diffuser boxes. Each is a "stretched pentagon" (flat top, angled lower corners) in a silver rim, split by a vertical bar into two rectangular windows (the right-hand window is the larger one on both sides, estimate). See 3.5 | P rear_straight_doors_open_01, S7 rear view |
| Doors | electrically actuated dihedral doors, opened from the key fob, from a button "just underneath the Bugatti Line" and from the centre console. Hinge: at the A-pillar base / front of the door, axis inclined so the door swings up and forward (see 3.7). Press text does not describe a roof part; photos show the glass roof stays on the body with a glazed strip going up with the door (estimate) | S2, P |
| Active rear wing | patented system, wing stays submerged (flush) even at top speed; it rises for downforce at lower speeds and acts as an airbrake under deceleration. Car reaches top speed without the wing deployed. Photos show it retracted as a flat full-width panel at the tail | S2, S4, P |
| Top speed | 380 km/h limited, 445 km/h with Speed Key | S1 |
| Launch configuration | Two-tone: light pale blue / silver-blue metallic upper body, black (carbon) lower body, with a thin bright (silver) Bugatti Line. No official colour name was found in any source (the configurator release only says 23 new colours, gloss/metallic/matt, 7 carbon weaves). Do not invent a name | S6, P |
| Production | 250 units, from 3.8 m EUR net, hand built in Molsheim | S2 |
| Four stated design elements | horseshoe grille, Bugatti Line (C-line), central ridge, dual colour split | S2 |

Dimension check on the blueprint (S7, vector coordinates): total length 570.2 units, height 145.3 units (ratio 3.925, official 4671/1189 = 3.929, good), width over mirrors 265.9 units (2.178 m at 122.07 units per metre, official 2.165 m). The blueprint wheelbase measures 2.761 m against the official 2.740 m (0.8 percent too long).

## 2. Image index

### refs/ (user's, content as listed in BRIEF.md, not re-checked)
- A1_bugatti_line_sketch.png: official sketch of Veyron, Chiron, Tourbillon profiles showing the C-line. Use: C-line path.
- A2_rear34_sketch.png: official rear 3/4 sketch. Use: light bar, diffuser, haunches.
- A3_blueprint.png: four-view drawing, 199.5 px per metre. Use: proportions (a cleaner vector version is `refs/web/blueprint_large.png`).
- A4_front34_render_twotone.png: front 3/4 render, pale blue + black. Use: colour reference.
- B1..B4: interior dash, from door, side seat+console, top with door open.
- B5_side_sketch.png: official side sketch. B6_grey_pitlane_front34.png: grey front 3/4.
- sheet_A_exterior.jpg, sheet_B_interior.jpg: the source sheets.

### refs/web/ (all verified by eye to be a Tourbillon; sources: Wikimedia Commons CC images and Bugatti newsroom press images; dimensions.com for the drawing)
Exterior, straight views
- front_straight_01.jpg: launch car head-on on the stage, perfectly symmetric. Best: grille shape, headlight bars, lower intakes, hood centre ridge, windshield width.
- front_straight_02_windtunnel_model.jpg: grey scale model head-on in wind tunnel (stable lighting, shows the intake and fender forms, tape marks).
- front_straight_03_doha.jpg: pale blue car head-on, slightly high camera, outdoors.
- blueprint_large.png: cleaned vector rendering of the dimensions.com drawing (side facing right, front, rear, plan with nose to the right), 2000x1300. Scale 122.07 units/m in the SVG, i.e. 61.0 px per metre in this PNG (x 2 of the SVG units).
- rear_straight_doors_open_01.jpg: rear view with both doors up: light bar with BUGATTI letters, Tourbillon plate, two exhaust finishers, diffuser strakes, engine intake openings and central spine, door inner sides. Best rear reference.
- side_profile_01.jpg (Wikimedia, flat side, blue car), side_profile_02_shanghai.jpg (cleanest, sunlit), side_profile_03_hongkong.jpg, side_profile_04_doha.jpg: side profiles. Use: C-line, colour split, wheel position, side gills, glasshouse shape. side_profile_02 is the best.
Three-quarter views
- front34_01.jpg, front34_02.jpg (Wikimedia, blue car on stand), front34_03_scale_person.jpg (person for scale), front34_04_clean_gravel.jpg (clean low 3/4 in front of a chateau), front34_05_headlights_lit.jpg (dusk, LEDs on, dark car), front34_press_grey_01.jpg (grey car, press kit), side34_stage_01.jpg (stage, side 3/4 with presenter).
- rear34_01.jpg (Wikimedia, rear 3/4 on stand, shows wing/deck), rear34_02_hongkong.jpg (diffuser from behind-side), rear34_03_night_lightbar.jpg (light bar, rear quarter roundel, Tourbillon plate).
- top_34_01_prototype.jpg: high 3/4 from above, grey taped prototype: roof, buttresses, engine area.
- top_down_01_prototype.jpg: straight plan view of a taped prototype (tail at left): central spine, rear deck panels, glass roof, C-line loops. The best plan reference after the blueprint.
Doors
- doors_open_front_01.jpg (Wikimedia, silver car, doors up, seen from front), doors_open_front_02.jpg (3/4 front, doors up, street), doors_open_34_01_doha.jpg (high 3/4 from front-left, doors up, desert), rear_straight_doors_open_01.jpg (from behind).
Details
- headlight_01_front_dark.jpg: dark car head-on, LED daytime signature lit, glowing grille outline.
- intake_closeup_01_model.jpg: close-up of the lower front intake mesh on the model.
- side_wheel_01_model.jpg: model side/front 3/4 with wheel and sill vents.
- taillight_01.jpg: close-up of the light bar end with BUGATTI lettering and EB logo.
- wheel_closeup_01.jpg (wheel behind a seated person, cap with front 3/4), wheel_closeup_02_front.jpg (front wheel crop at 4000 px source: tyre text 285/35 ZR 20, discs, caliper), wheel_closeup_03_rear.jpg (rear wheel crop: 345/30 ZR 21, black caliper with BUGATTI).
Interior
- interior_cluster_01.jpg (Wikimedia: steering wheel, cluster, dash, tan interior), interior_cluster_02_closeup.jpg (best cluster close-up: dial layout), interior_wheel_console_01.jpg (steering wheel and centre console from the passenger side), interior_console_01_screen_knob.jpg (pop-up screen and rotary knob on the console), interior_seats_01_wide.jpg (wide view through the open driver door: seat, dash, console, door), interior_door_open_01.jpg (through the open door, side view), interior_sketch_top_01.jpg (design sketch of the cabin from above, symmetrical).
Chassis / powertrain
- chassis_01_side.jpg (dark studio, carbon tub and wheels from the side), chassis_02_front34.jpg (front 3/4 rolling chassis), chassis_03_rear34.jpg (rear 3/4: V16, exhaust manifolds, springs, diffuser box), engine_01_v16.jpg (V16 top view with "BUGATTI V16" plaque and intake trumpets).

Not found: a straight rear view of the car with doors closed and flat daylight; a close view of the exposed V16 from the side; a roof/door-hinge close-up; a clear photo of the door card. wheel/headlight/taillight views are available only as crops or in context.

## 3. Design feature checklist

Coordinates: front of the car = -Y, +X = left side (driver). Numbers from the blueprint are given as fractions of length L = 4.671 m, width W = 2.051 m, height H = 1.189 m.

### 3.1 Overall stance and silhouette
- Very low and wide: H/L = 0.255, W/L = 0.44. The cabin sits centrally, the nose is long and low, the tail is short and tapered. The greenhouse is a single glass canopy that blends the windshield into the roof.
- Mid-engine layout with a fuselage-like central body (horseshoe grille origin) onto which "flying fenders" are docked left and right (S2): the fenders are separate-looking volumes with a visible crease from the headlight back to the A-pillar base.
- A thin continuous central ridge (the "central line") runs on the vehicle centreline from the grille top through the hood, windshield, roof, spine between the rear openings, to the light bar (P front_straight_01, rear_straight_doors_open_01, top_down_01_prototype). It is a narrow raised rib about 15 to 20 mm wide, bright metal / body colour. In front view it passes through the grille badge.

### 3.2 Front end
- Horseshoe grille: tall rounded "arch", flat-topped dome. Width about 0.59 m, height about 0.36 m (blueprint front view), centre z about 0.39 m, top at z about 0.57 m, bottom at about 0.21 m. Sides are nearly vertical, top corners well rounded (radius about 0.18 m), bottom corners rounded with a small outward curl (estimate). Black fine mesh (a diamond/honeycomb pattern), thin bright metal frame (chrome edge) around it. A red oval BUGATTI badge (about 0.07 m wide) at the grille centre, z about 0.47 m, with the central ridge line vertical through it, splitting the grille visually into two halves.
- Left and right of the grille: two wide lower intakes, rounded-trapezoid shape (wider at the bottom outside), black mesh, each about 0.5 m wide x 0.30 m high, centre z about 0.34 m, outer edge at about x = +/-0.92 m. Each has two mesh bands: an upper larger mesh and a lower narrow slot, separated by a thin silver horizontal bar that extends outwards and wraps around the corner. A thin bright splitter line runs across the whole width under the intakes. Below it the splitter and lip are black carbon.
- Headlights: slim, horizontal, almost straight bars angled slightly (inner end a little lower and further forward), one per fender above the intake. Each is about 0.42 m long and 0.08 m high, centre z about 0.61 m, inner end 0.50 m from the centreline, outer end 0.92 m. Inside a smoked lozenge housing: one row of 4 small rectangular LED elements (daytime signature) plus a thin lower line (estimate: 4 squares, front_straight_01 and headlight_01). At night the grille outline also glows blue (headlight_01_front_dark.jpg).
- Hood: low, with a trapezoid raised "power dome" panel at the rear centre (near the windshield base), and the central ridge. Front fender crowns peak at about z = 0.83 m (0.70 H), x = +/-0.88 m, higher than the hood centre at about 0.62 m, so the hood is a shallow valley between two fender peaks (P front_straight_01).
- Air exits: radiator air leaves through the hood (S2); two slim slots on the hood sides beside the dome (estimate).
- Mirrors: on short stalks from the base of the A-pillar / top of the front fender, mirror head small and rounded, tear-drop shape (about 0.16 m wide), centre z about 0.875 m, outermost point at x = +/-1.08 m (over-mirror width 2.165 m). Body-coloured shell.
- Wipers: two wipers parked at the lower windshield edge, pointing toward the centre (front34_05, interior); estimate: pantograph-style single arm each.
- Windshield: wide, low, shallow; base width about 1.31 m, height about 0.27 m in front view; it continues into the roof glass without a pillar-to-roof header band visible from the front (single canopy). A-pillars are thin dark.

### 3.3 Side profile and colour split
- Colour scheme: upper body pale blue-silver metallic (hood, front fenders, doors, roof glass surround, rear haunches), lower body black carbon (front splitter and lip, sill, rear lower bumper and diffuser, the rear wheel-arch lower part, rear light-bar panel concave area). In side_profile_02 the black starts right below the door at the sill line and under the rear fender; the front fender lower edge is blue with a thin black lip below it.
- The Bugatti Line (C-line): a thin bright silver / chrome line that traces a "C" opening on the side. Path (side_profile_02, side_profile_03): starts low at the sill just behind the front wheel arch, sweeps back along the lower edge of the door in a shallow rising curve, curves up behind the rear of the door/glass (the rear leg of the C) over the round roundel on the quarter, goes around the top rear of the greenhouse, and runs forward along the upper roof edge over the door window to the A-pillar base, "leaning forward" (S2). Everything inside the C (door, window, roof side) is the primary light colour; the area behind the rear leg of the C (rear haunch) is also light blue; below the lower leg is black. Line thickness about 8 to 10 mm.
- Door cut line: the rear shut line of the door runs from the roof near x about 0.625 L (from the nose) diagonally down and forward to the sill at about 0.49 L (blueprint); the front door cut is short, from the beltline at 0.296 L down to about 0.266 L at z 0.70 m (it sits behind the front wheel arch top, the door front edge ends at the fender behind the front wheel).
- Beltline: a horizontal line at z about 0.84 m (0.70 H) from 0.30 L to 0.58 L (blueprint) = the lower edge of the side window and mirror stalk line.
- Rear quarter roundel: a circular badge (about 0.15 m diameter, centre at about 0.636 L from the nose, z about 0.92 m) inside the C (blueprint circle; photos show an EB roundel on the quarter, rear34_03_night_lightbar).
- Side intake: the main side intake sits behind the door "within the C-line" (S4); in the photos it is hidden by the tall rear haunch. Visible side detail: 3 diagonal gill slots (swooshes, black on black) in the carbon sill immediately behind the front wheel arch, about 0.25 to 0.30 m above ground, spanning 0.33 to 0.39 L from the nose (blueprint), and a tricolour (blue, white, red) stripe on the sill under them (side_profile_02, 03). A small "BUGATTI" lettering on the sill under the door (doors_open_front_02).
- Greenhouse: rear end of the glass at about 0.65 L; side glass is one long teardrop that narrows to the rear and ends in the C-line rear leg. Roof peak at about 0.56 L from the nose (z = 1.19 m), roof then falls smoothly toward the tail to z about 0.88 m at 0.95 L.
- Wheel arches: front arch radius about 0.50 m (blueprint outer arch circle roughly 20 percent larger than the tyre, estimate), rear about 0.52 m; arch opening has a thin dark inner lip. Wheel centres: front axle 1.027 m from the nose, rear axle 0.883 m from the tail (blueprint; with official wheelbase 2.74 use front overhang 1.03 m, rear overhang 0.90 m, matching `spec.py`).

### 3.4 Roof, buttresses, rear deck
- The roof is glass (one canopy from windshield to behind the seats; top_down_01_prototype shows transparent roof with interior visible). A narrow central body-colour spine runs from the windshield header to the rear deck along the centreline, a raised ridge about 15 to 20 mm wide that bridges to the roof edges (estimate).
- Flying buttresses: two sweeping arms rise from the rear haunches up to the roof edge on each side of the rear deck (rear blueprint view: arcs from the rear shoulder at x = +/-0.8 m, z 0.9 m up to x = +/-0.50 m, z 1.14 m). They enclose the rear deck between them like channels; the roof sides drop into them.
- Rear deck (between the buttresses): a central spine ridge, left and right of it two rectangular rounded openings (each about 0.39 m wide x 0.19 m high in rear view, z 0.90 to 1.09 m), through which the V16 intake system (silver intake trumpets, carbon airboxes) and the cabin rear are visible (rear_straight_doors_open_01). Whether these are open scoops or glass is not clear from photos; the photo shows carbon ducting with no glass reflections, so treat as open air intakes with a dark carbon floor (estimate). The prototype top view shows dark rectangular panels each side of the spine at the rear deck (glass or vents).
- Engine: not exposed as a showpiece; only the intake plenums are visible through the two rear openings; the V16 itself sits below the deck.

### 3.5 Rear end
- Light bar: one continuous LED band spanning the full width of the tail, shaped like a wide smile: it sits at z about 0.77 m in the middle and curls upwards at both ends, turning round the rear corners and ending in a point on the rear fenders (blueprint rear view: ends at x = +/-0.92 m, z about 0.77 m; the ends curve downward slightly in the blueprint but in photos they flick upward, rear_straight_doors_open_01). About 45 to 50 small rectangular segment-cells in a staggered row (estimate), red when lit. The BUGATTI lettering is formed by the LED cells in the centre of the bar (centre third), white/red. The EB logo sits above the light bar on the centreline (about 0.05 m wide).
- Below the light bar: a concave carbon-fibre panel (matt carbon weave, black), curving down to the number plate area. Centre: a rectangular plate recess for the plate about 0.43 m x 0.10 m at z 0.58 to 0.69 m, with a silver "Tourbillon" script nameplate in the photo (P).
- Exhaust: 2 finishers, one each side of the plate, each about 0.41 m wide x 0.14 m high, centre at x = +/-0.40 m, z about 0.50 m (rear blueprint), flat-top "stretched pentagon" silver rims, each with a vertical divider making 2 rectangular openings.
- Diffuser: rises from behind the cabin (S2). Seen from behind it is a set of 4 vertical tall strakes on each side forming two big boxes under the exhausts (outer strake px 243..340, inner 412..450 in the blueprint rear crop; i.e. at about x = +/-0.60 to 0.40 m outer, +/-0.28 to 0.20 m inner) plus a short central fin on the centreline at the bottom (z about 0.17 to 0.26 m). The sides of the diffuser stop at about x = +/-0.82 m. All carbon. The diffuser dips down to z about 0.17 m at the strake bottoms; the lowest tail extreme (side blueprint) is at z about 0.17 to 0.49 m.
- Wing: a full-width flush panel at the tail between the rear deck and the light bar that rises (hinge near the front edge, tail edge lifts by about 0.085 m, estimate); blueprint side view shows it drawn deployed. It also acts as an airbrake.
- Rear wheels: stand clear of the body, tyres 345 wide are very wide; rear fender tops are the widest part of the car (2.051 m).

### 3.6 Wheels
- 5 spokes, each "Y"-shaped: a stem from the hub that splits into two arms that go to the rim; the arms of neighbouring spokes meet at the rim so there are 5 pentagonal open windows between the spokes, with 5 smaller triangular/pentagonal gaps near the hub. Same pattern front and rear (blueprint and wheel_closeup_02/03: identical designs, the rear wheel is bigger: 21 inch vs 20 inch rim, 345 vs 285 tyre). Bright diamond-cut face, dark inner barrel / duo-tone, dark rim lip. 5 lugs / central fixing visible around a round cap with the dark EB oval. Face diameter about 0.57 m (blueprint).
- Visible brake: drilled carbo-ceramic disc and a black caliper with white "BUGATTI" lettering, caliper on the rear half of the front wheel and the rear wheel (wheel_closeup_03_rear).
- Tyre sidewall: chequered band pattern on the shoulder, white Michelin lettering.

### 3.7 Doors
- Dihedral doors, hinged at the front, hinge axis near the A-pillar base inclined forward and upward so that the door swings up and slightly forward and out; opened angle about 70 to 80 degrees from vertical (photo doors_open_front_02: the door is almost vertical, its upper edge leaning outward over the roof). The door includes the full side window and the upper roof edge strip with the C-line frame; the central roof canopy stays fixed (estimate, glass strip rises with the door). The door's inner surface is carbon with a fabric panel and speaker exciter; the hinge cut-out is visible at the front of the A-pillar. Both doors opened are higher than the roof at the tail (rear view: doors reach about 0.45 m above the roofline).
- Door width at the door cut: front shut line x about 0.296 L at the beltline, 0.266 L at the lower front; rear line at 0.625 L at the roof, 0.49 L at the sill.

### 3.8 Interior (P interior_*; two-tone shown in these photos is a pale-blue / teal-blue, other photos show a tan colour scheme)
- Steering wheel: fixed-hub: an oblong, flattened-top-and-bottom "squircle" rim in leather/Alcantara (black top with light blue stitching, black upper bar), rim rotates around a fixed central hub; the central hub is a round leather pad with an EB logo in silver, ringed by polished metal, diameter about 0.14 m. Two thin spokes reach round behind the instrument cluster (they are seen as 2 black vertical posts at the top). Small button pods at 3 and 9 o'clock, paddle shifters behind. Rim has a bright metal marker at 6 o'clock (centre mark). Steering wheel centre per `spec.py`: (0.335, -0.440, 0.700).
- Instrument cluster: a polished-metal skeleton binnacle in the shape of a wide rounded "bridge" with three circular dials: large centre speedometer (0 to 550 km/h, skeletonised mechanism with gears visible, digital gear/speed readout "000 km/h" window at the bottom), left dial group containing 3 small subdials (fuel, battery charge, clock/other, with a clock face on top) in one common bezel, right dial "PUISSANCE V16" (power gauge, 0 to 1001 hp style scale, skeleton gears). Between the dials the metal frame has triangular cut-outs. 3 dials in a horizontal row; total width about 0.30 m (estimate). Two small knurled knobs sit at the base on both sides below the cluster; a round start ring sits at the left of the cluster on the dash (interior_cluster_02).
- Dashboard: low, sculpted, one big wing-shaped soft-leather surface; two-tone: darker teal upper, lighter pale blue lower; flat-bottom smooth form with round vents hidden; a vent slot with a bright blade at the passenger end and at the driver end (small oval with a metal blade). Centreline of the interior divided into driver and passenger sides (a continuous line down the centre, S5).
- Centre console: a slim, tall, sloping "blade" rising from the floor toward the dash: polished aluminium frame with crystal glass top, switchgear visible under the glass; 3 large knurled rotary knobs with glass caps and small lit numeric/icon discs, stacked in a diagonal row along the top section (volume, temperature, etc.), a pull-to-start lever (glass handle) lower down, and a block of small push-switch keys with a red button at the bottom (interior_wheel_console_01). A portrait pop-up screen deploys from the top of the console / dash (portrait first, then landscape in 5 s) with a large rotary knob in front of it (interior_console_01_screen_knob).
- Seats: fixed-floor bucket seats, low, one-piece shell with integrated headrest, a separate raised bolster, 2 horizontal ribs, two-tone: smooth leather on the bolsters, textured fabric on the centre inserts; seats are fixed, pedals and wheel move. Pale blue leather in the sample.
- Door card: sculpted sweep matching the dash, leather upper with a metal door handle (pull-loop), speaker exciters (no grilles), a "Tourbillon" signature script embossed on the door pocket lid (interior_wheel_console_01 right bottom). Carbon trim visible near the door hinge area.
- Colour split: horizontal colour split in the interior, darker above the line, lighter below (S5); the sample photos use teal-blue and pale blue (a tan version exists as well in the Wikimedia photo interior_cluster_01).

### 3.9 Chassis (for the rolling-chassis / show parts if modelled)
- Black carbon tub, open between the wheels (the tub is cut for the doors); front bulkhead with the horseshoe-shaped crash structure; rear: the V16 sits behind the cabin, two exhaust manifolds with silver round silencers/catalysts, a gearbox/e-motor unit between the rear wheels, blue springs and dampers (rear), a large dark diffuser box with 4 vertical sections; wheels as above (chassis_03_rear34).

## 4. Proportions from the dimensioned drawing (S7, fraction of overall length L = 4.671 m from the nose, vector values; "(estimate)" where read by eye on the rendered drawing)

Scale: 122.07 units per metre in the SVG (570.2 units long). All heights are above the ground line.

| feature | position along the length from the nose | height |
|---|---|---|
| Nose tip (front-most point) | 0.000 L | z = 0.25 m (0.21 H) (estimate) |
| Upper nose / hood leading edge | 0.012 L | 0.63 m (0.53 H) |
| Front axle | 1.027 m = 0.220 L | wheel centre z = 0.358 m |
| Rear axle | 3.788 m (= 4.671 - 0.883) = 0.811 L | wheel centre z = 0.358 m |
| Wheelbase | 2.761 m = 0.591 L (official 2.740 m = 0.587 L) | |
| Front overhang | 0.220 L | |
| Rear overhang | 0.189 L (0.883 m; `spec.py` has 0.901 m) | |
| Headlight centre | 0.099 L | 0.61 m (0.52 H) |
| Front lower intake centre | 0.063 L | 0.36 m (0.30 H) |
| Windshield base (cowl) | 0.184 L (0.86 m) | 0.82 m (0.69 H) |
| Windshield top / roof start | 0.378 L (1.77 m) | 1.08 m (0.91 H) |
| Roof peak | 0.561 L (2.62 m) | 1.19 m (1.00 H) |
| Roof falls to | 0.673 L (3.15 m) | 1.11 m (0.93 H) |
| Rear deck shoulder | 0.868 L (4.06 m) | 0.94 m (0.79 H) |
| Rear wing top / light bar level (side) | 0.945 L | 0.88 m (0.74 H) |
| Tail extreme | 1.000 L (4.67 m) | 0.49 m (0.41 H) |
| Door front cut | beltline 0.296 L, lower 0.266 L | z = 0.84 m / 0.70 m |
| Door rear cut | roof 0.625 L, sill 0.491 L | z = 1.16 m / 0.14 m |
| Beltline | 0.30 L to 0.58 L | z = 0.836 m (0.70 H) |
| Sill (flat bottom of door) | up to about 0.60 L | z = 0.14 m (0.12 H) |
| Side-gill slots | 0.33 to 0.39 L | z = 0.30 to 0.34 m |
| Rear quarter roundel | 0.636 L | z = 0.92 m (0.77 H) |
| Mirror | 0.368 L | z = 0.88 m (0.74 H) |

Roof height profile (top silhouette, metres above ground, vs distance from nose as fraction of L): 0.02 L 0.61, 0.04 L 0.68, 0.06 L 0.71, 0.10 L 0.76, 0.15 L 0.81, 0.20 L 0.82, 0.25 L 0.91, 0.30 L 0.98, 0.35 L 1.05, 0.40 L 1.13, 0.45 L 1.17, 0.50 L 1.19, 0.55 L 1.19, 0.60 L 1.18, 0.65 L 1.15, 0.70 L 1.10, 0.75 L 1.05, 0.80 L 1.00, 0.85 L 0.95, 0.90 L 0.92, 0.95 L 0.88, 0.98 L 0.83. (Computed from the silhouette of the vector drawing by `out/scripts/research/side_profile.py`; the top line is the outer outline, not the beltline.)

Front and rear views (fractions of the body width W = 2.044 m measured, official 2.051 m, and height):
- Mirror outer edge: x = +/-1.09 m (2.178 m over mirrors on the drawing; official 2.165 m).
- Body max half-width: 1.02 m, at the rear haunches (rear view) and also at the front fender (same width in the drawing, both about 2.04 m).
- Greenhouse width at the base of the A-pillar: about 1.6 m (0.78 W); windshield glass width at the base 1.31 m (0.64 W); roof crown half-width at the rear (between buttress tops) about 1.0 m total (0.49 W) at z about 1.14 m.
- Horseshoe grille: 0.288 W wide (0.59 m), 0.36 m tall (0.30 H), top at z = 0.57 m (0.48 H).
- Lower intakes: each 0.5 m wide (0.24 W), 0.30 m tall.
- Headlight bar: each 0.42 m long, inner end 0.50 m from the centreline.
- Front fender crown: z about 0.83 m (0.70 H) at x = +/-0.88 m.
- Mirror height: 0.875 m (0.74 H).
- Rear view: light bar spans x = +/-0.92 m (0.90 W), z 0.77 m middle (0.65 H); number-plate recess 0.43 m wide at z 0.58 to 0.69 m; exhaust finishers 0.41 m wide at x = +/-0.40 m, z 0.42 to 0.57 m; rear glass openings 0.39 m wide each at z 0.90 to 1.09 m; central spine top at z 1.19 m.
- Wheel arch: arch circle diameter about 1.15 x tyre diameter (estimate) front radius about 0.42 m, rear about 0.44 m (estimate, from the drawing outer arch line which is drawn about 6 to 8 cm above the tyre).
- Tyre width in the drawing: 0.31 m (front and rear are drawn equal; real 0.285 / 0.345 m).

Limits: the drawing is a third-party tracing (dimensions.com), which agrees with the official numbers to within 1 percent in length, height and mirror width but has an overstated wheelbase (2.761 m). Heights read off the rendered image have an error of about 1 to 2 cm; "(estimate)" items are by eye and may be off by 2 to 5 cm.

## 5. Open points / could not verify
- Official launch colour name (not found in any Bugatti source).
- Front and rear track, ground clearance, brake disc diameters and piston counts (not published).
- Exact count of LED segments in the headlight and light bar (counted by eye only).
- Whether the two rear-deck openings are open or glazed.
- How much of the roof glass moves with the door (photos suggest only a narrow strip).
