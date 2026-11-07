# Aircraft CAD and BOMs

Variant C and the MicoAir H7 aircraft are the owner's selected fully equipped and low-cost layouts. RevS remains the middle reference aircraft. RevAB remains frozen and was not used for these designs.

| Package | Native assembly | Parts and estimates |
|---|---|---|
| Variant C | [SOLIDWORKS 2026 assembly](Variant_C/SolidWorks/Variant_C_R1.SLDASM) | [BOM](Variant_C/BOM.csv), [physical model](Variant_C/physical_model.json) |
| Cheapest H7 | [SOLIDWORKS 2026 assembly](Cheapest_H7/SolidWorks/Cheapest_H7_R1.SLDASM) | [BOM](Cheapest_H7/BOM.csv), [physical model](Cheapest_H7/physical_model.json) |

[Editable BOM workbook](Drone_BOMs_R1.xlsx). Each native assembly has separate imported-body part files fixed at the modeled positions. Editable CAD generators and individual STEP parts are included. Keep the assembly and its parts together when downloading. Purchased components are installation envelopes.

## Corrections incorporated

- Both sensor mounts use MicoAir's 29.3 x 17 x 14.5 mm MTF-01 envelope and its mounting pattern. Twenty-millimetre feet give nominal level-ground clearance.
- The cheap build opens the lower guard skirt while retaining the continuous propeller-height ring. Its full-skirt reference remains available for comparison.
- Battery charge voltage and capacity match the selected pack. CAD mass and inertia generate each current simulator model. Aikon's specified mass with wires replaces the earlier planning value.
- Battery movement follows the cradle's longitudinal adjustment. The represented solids and full rotor sweeps are checked. Board posts terminate at their mounting surfaces.
- The assumed duct thrust gain is removed. The physical model carries a guard-factor range and a lift-only ballast estimate. Neither is a measured payload rating.
- BOMs distinguish installed quantities, suggested spares, price estimates, included items and missing quotes. Radio, charger, tools and external test apparatus are excluded.

## Checks and scope

Each package contains geometry and interference reports. These cover nominal represented shapes and rotor sweeps. Cable routes and some fasteners remain mass allowances. The current simulator input is tied to the retained run by its SHA-256 in `sitl_current.json`.

Level-drop SITL runs exercise stock altitude recovery on an estimated aircraft. They do not test the physical controller board or identify its regulator dropout. The two earlier Lua/ground-side procedures change controller state differently and are not a processor-performance comparison. Onboard ToF is controller feedback; independent video or motion capture is required for independent height outcomes.

Stop timing uses all four output channels and firmware timestamps. A missing timing reference or insufficient samples is reported as unverified. No aggregate safety-pass claim is made. Independent motor stop under a Lua fault, mode-change abort, physical propulsion, pack current, printed stiffness, impact strength and ballast attachment require separate qualification. Neither aircraft has been built or flown.

## Reproduce

Install `cadquery`, `numpy`, `shapely`, `ezdxf` and `matplotlib`, then run `python tools/build_drone_release.py`. It regenerates the layouts in this folder. Run `python tools/verify_geometry.py` for represented-part validity, rotor sweeps and model consistency. `tools/render_release_views.py` makes the high-resolution views. SOLIDWORKS source utilities target version 2026. Simulation uses the separately installed ArduPilot executable and `pymavlink`; it is a desktop test configuration, not a flight-ready parameter set.
