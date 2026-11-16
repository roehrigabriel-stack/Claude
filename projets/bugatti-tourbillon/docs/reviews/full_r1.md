# Full model review r1 (critic)

Renders: out/renders/full/v1/sheet.png (light), crit_dark, crit_open, crit_close, crit_door (sheet.png in each).

## 1. Verdict
The car is recognisable at first glance: horseshoe grille with red badge and centre ridge, two-tone pale blue / carbon, C-line with EB roundel, smile light bar, flying-buttress deck. Proportions are close to A4. It is not yet a professional render. It reads as a good low-poly-plus-subdivision model, not a press image. Surfaces are lumpy (wobbling highlights, pinched creases at fender corners, wavy rear lip), the glass is opaque black so the interior and the cabin story are lost from outside, the rear deck openings are empty tubs, and several small parts are crude (headlights, wheel spokes, diffuser comb). Three changes with the most impact: (1) smooth and re-tension the body surface (fender crowns, nose corners, tail lip) and remove the black stripe on the hood; (2) make windshield, roof and side glass transparent dark tint so the interior shows; (3) fill the rear deck openings with visible intake trumpets or glass, and rebuild the headlights as slim bars.

## 2. Defects per module (P0 kills, P1 clear, P2 polish)

### Body
| P | Problem | Render | Ref | Fix |
|---|---|---|---|---|
| P0 | Wide black stripe over the whole hood centre, flowing into the windshield. Hood should be pale blue; only the small power-dome and windshield base are black. Reads as a racing stripe, loses the Tourbillon look. | v1 f34, front; crit_close nose | A4, front_straight_01 | Hood and fender crowns in body colour. Black only on a trapezoid power dome at hood rear (x +/-0.30, y -1.6 to -1.1) and the windshield frame. |
| P0 | Surface quality: wavy/pinched highlights on fender tops, notch and jagged tear at headlight corner, creases at nose corners, wobbly rear lip above the light bar (very visible with wing open). | crit_close nose, wheel; crit_open rear; crit_dark front | A4 (clean flowing fenders) | Add subdivision or smooth shading with auto-smooth off and fix normals; remove local vertices spikes near headlight; resample the fender crown curve with fewer, evenly spaced control rings; smooth the tail lip. |
| P1 | Black / grey mismatch: lower rear body and sill are mid grey carbon while upper rear haunch and roof are glossy black, giving three tones. | v1 left, r34 | side_profile_02_shanghai (one deep navy-black) | Use one gloss black (or deep navy 0.02,0.03,0.06) for rear upper; carbon weave only on sill, lip, diffuser, rear panel. |
| P1 | Fender-to-hood crease (headlight to A-pillar base) is not visible; fender and hood merge in a soft blob with sharp seam artefacts. | v1 front, f34 | front_straight_01, A4 | Cut a clear shut line plus 3 mm crease from headlight outer end to A-pillar base. |
| P2 | Mirrors are on thin chrome stalks (silver) and far outboard; ref mirrors are body-coloured, short and teardrop. | v1 front | A4 | Body-colour shell, stalk shorter, outer x 1.08. |
| P2 | Hood slots beside the dome read as flat grey bands near the windshield. | v1 front | front_straight_01 | Make them black recessed slots with mesh. |

### Front
| P | Problem | Render | Ref | Fix |
|---|---|---|---|---|
| P1 | Headlights are tiny jagged specks (about 0.2 m) not slim 0.42 m bars; no smoked housing; lit state shows a few white dots. | crit_dark front, f34; crit_close nose | front_straight_01, front34_05_headlights_lit | Bar 0.42 x 0.08, inner end x 0.50 low/forward, outer 0.92; smoked lozenge housing, 4 LED squares plus thin lower line, soft glow. |
| P1 | Splitter lip has sharp wing spikes at the outer ends that stick out sideways past the bumper. | crit_close nose (right edge), wheel | front_straight_01 | Trim lip to end flush with the intake outer edge (x +/-0.95) with rounded end. |
| P1 | Rectangular cut panel ahead of the front wheel (hard vertical seam, plus small white rectangle vent) looks like a door cut, not a fender vent. | crit_close wheel | wheel_closeup_02_front | Remove the panel seam or turn it into a slim black vent; delete the white rectangle. |
| P2 | Lower intakes have coarse vertical bars and a loose silver blade; mesh not visible. Grille outline glow at night absent. | crit_close nose; crit_dark front | headlight_01_front_dark | Fine diamond mesh, one horizontal silver bar; add blue emissive grille outline when headlights=1. |

### Rear
| P | Problem | Render | Ref | Fix |
|---|---|---|---|---|
| P1 | Diffuser: about 14 tall comb fins, wider than the tail, looks like a race car, reads busy; side plates stick out beyond rear fender. | v1 rear, r34; crit_close rear | rear_straight_doors_open_01 | 4 strakes per side (x +/-0.20..0.28 and 0.40..0.60), short central fin, stop at x +/-0.82. |
| P1 | Light bar lit state is good, but unlit in studio it is a dull dark red strip with strongly visible segmented joints, and the ends do not flick upward. With wing open the body above is wavy. | v1 rear; crit_open rear | rear34_01 | Raise ends (z 0.77 centre, +0.05 at tips), smooth the panel above, small gap between cells. |
| P2 | Red reflector rectangles on both tail corners and a lit white plate-strip under the plate look added-on. | crit_dark rear | rear34_03_night_lightbar | Remove or dim; keep only the strip under the plate if it is a plate light. |
| P2 | Exhaust finishers good but dividers read as round tubes (twin cans), ref has 2 rectangular openings. | crit_close rear | rear_straight_doors_open_01 | Replace the round tips by 2 rectangular openings per finisher. |

### Wheels
| P | Problem | Render | Ref | Fix |
|---|---|---|---|---|
| P1 | Spokes are a thin 5-point star; the Y-shaped spoke with split arms meeting at the rim is missing, so rim windows are not pentagonal; face has no depth or dark inner barrel. | v1 left; crit_close wheel | wheel_closeup_02_front, A4 | Y spokes: stem 0.06 wide from hub splitting at r 0.14 into two arms 0.05 wide joining neighbours at the rim; dark barrel behind, bright diamond-cut face. |
| P1 | No brake disc or caliper visible through the spokes. | crit_close wheel | wheel_closeup_03_rear | Drilled disc and black caliper with white lettering on rear half. |
| P2 | Checker band on the tyre shoulder is too large and contrasty; wheel is well centred in the arch and clearance is good (keep). | crit_close wheel | wheel_closeup_02_front | Halve the checker size, lower contrast. |

### Interior
| P | Problem | Render | Ref | Fix |
|---|---|---|---|---|
| P0 | Glass is opaque black: windshield, roof and rear glass hide the interior entirely from outside, closed or in front view. Also dark view through windshield shows nothing but wipers. | v1 f34, front; crit_close cabin | A4 (dark tint but interior visible), B1 | Glass: transmission 0.9, tint 0.15 dark grey, roughness 0.02, no black base colour; remove any black backing plate behind roof glass. |
| P1 | Black void in the door sill: dark recess under seats and a dark floor strip between door opening and seat (see-through look). | crit_door door | B2, doors_open_front_02 | Add carbon sill plate and floor carpet reaching the sill; close the gap under the seat to the chassis tub. |
| P1 | Door opened: lower front corner of door overlaps the front fender and hinge area, mirror hangs inside the opening; door outside panel is plain pale blue with no visible C-line frame. | crit_door door; crit_open f34 | doors_open_front_02 | Move the hinge pivot 0.04 m inwards/back, reduce swing so lower front edge clears the arch by 0.03 m; keep mirror on the fender, not the door. |
| P2 | Interior colours (blue seats, dark blue dash) fit the references. Steering wheel and cluster small but legible in open views. | crit_open r34 | B1 | Keep. |

### Chassis / engine
| P | Problem | Render | Ref | Fix |
|---|---|---|---|---|
| P1 | The two rear deck openings are empty grey tubs with a flat floor; no intake trumpets or airboxes visible, seen as holes in the car. | v1 r34, rear, high_r34; crit_close deck | rear_straight_doors_open_01, engine_01_v16 | Place 8 silver trumpets per opening (0.05 radius, 0.08 tall) on a carbon airbox, floor at z 0.90; or add dark tinted glass. |
| P2 | Under-body is not visible; sill and rear bumper look slightly floating above the ground at the left view (grey strip detached from the body). | v1 left | side_profile_02 | Close the sill to the body (flush) and make the bottom line continuous. |
| P2 | engine_glow=1 has no visible effect from outside. | crit_dark r34 | rear34_03_night_lightbar | Add warm emissive glow in the deck openings or remove the switch. |

### Rig and integration
| P | Problem | Render | Ref | Fix |
|---|---|---|---|---|
| P1 | Wing: deployed it is a wavy hump on the deck, not a flush full-width panel; leading edge shows a dark gap and the surface ripples. | crit_open r34, rear | rear_straight_doors_open_01 | Make the panel flat/curved in a single plane at the tail, hinge at the front edge, rise 0.085 m, close the side gaps; closed state must be flush with deck. |
| P1 | Doors open: left door seen edge-on is very thin and reaches high; both doors near vertical (lean outward not visible), which is slightly stiff but no collision with wing or roof. Door glass is more transparent than the closed glass (inconsistent). | crit_open f34, rear | doors_open_front_02 | Lean the door 10 degrees outward at the top; use the same glass material closed and open. |
| P2 | Lights state: headlights, DRL, light bar, brake lights light up; engine glow, grille outline, interior lights barely visible; screen/cluster glow not readable at 800x600. | crit_dark, crit_open | headlight_01_front_dark | Increase emission strength for interior, cluster and screen about 3x. |
| P2 | Dark showroom floor reflection and back-glow are good; light studio floor edge line (left wall) visible in several views. | v1, crit_open | A4 | Extend floor or darken cyclorama join. |

## 3. Keep
- Grille shape, badge and centre ridge; horseshoe proportions (front view).
- C-line with EB roundel, side intake shape, sill gills with tricolour (side close-up).
- Two-tone concept and the pale blue paint colour (matches A4).
- Smile light bar with BUGATTI lettering and Tourbillon plate (dark rear view).
- Wheel position in the arches, overall stance and wheel size.
- Open doors reaching high above the roof, interior seats and blue colourway through the open door.
- Dark showroom lighting style and reflections.
