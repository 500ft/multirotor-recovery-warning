# Variant C / instrumented carbon research aircraft

Revision R1. CAD design, not built or flown.

The numerical source is [physical_model.json](physical_model.json); purchase quantities and prices are in [BOM.csv](BOM.csv).

Open the assembly STEP or the native assembly in `SolidWorks/` when available. Individual STEP parts preserve separate component identity; purchased parts are envelopes.

The priced aircraft subtotal is $312.83, plus any quoted items, tax and shipping. Printing is priced at zero under the owner's makerspace assumption. Spares and shared test equipment are excluded.

## Changes applied

- Correct full MTF-01 envelope, mounting holes and longer landing feet.
- Battery capacity and maximum charge voltage match the selected pack.
- CAD mass and inertia generate the current simulation input. Prior simulation runs retain their original configuration and are not transferred to this revision.
- Guard thrust retention is an assumption with a sensitivity range; no duct thrust gain is credited.
- CG is balanced in the planning model by a recorded pack shift. Final balance requires weighing and physical adjustment.

## Remaining physical qualifications

- propeller thrust/current with installed guard
- battery resistance and FC brownout margin
- printed material stiffness and impact strength
- motor dimensions and screw engagement on receipt
- all cable routing and connector access
- independent stop during a Lua fault
- physical ballast attachment and structural rating
- Aikon 36 x 36 x 5 mm envelope and connector pin order are planning assumptions

Onboard ToF supports the controller; independent video or motion capture is required for an independent height outcome. SITL level-drop checks address vertical recovery under their stated conditions.

Aikon mass follows the manufacturer specification. The selected battery and full-throttle current need qualification; see the physical model for the current comparison.
