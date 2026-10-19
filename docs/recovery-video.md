# Recovery replay

The [video](../Figures/recovery-physical-replay.mp4) shows the historical parameter
cases with motor-level allocation, rotor-speed response, and full translation.
The [executed results](../Data/recovery-video/results.json) contain altitude loss,
attitude/vertical settling, horizontal motion, the motor-response sensitivity
runs, and integration-step convergence. The original envelope stays unchanged.

![Recovery replay preview](../Figures/recovery-physical-replay.png)

## Model

[The generator](../Analysis/recovery_video.py) imports the existing parameter
factories, attitude/altitude gains and controller from
[the historical simulation](../Analysis/sim_release_recovery.py). The new
allocator solves the full healthy-quad wrench map. It scales an infeasible
differential force uniformly and shifts collective to fit the rotor limits.
Thrust and all three moments therefore come from the same four motor forces.

Rotor speed follows an exact first-order step between commands. Rotor force is
proportional to squared normalized speed. Mid-interval motor forces drive rigid
body translation and rotation. The legacy activation dead time is retained;
the new motor response begins after activation. The code keeps ideal state
feedback, gravity, quadratic translational drag and gyroscopic coupling.

The [settings](../Data/recovery-video/settings.json) pin the source revision,
initial conditions, integration step, playback timing and motor assumptions.
The response constants are borrowed from the linked PX4 Gazebo X500 model as
simulation reference values. Their sensitivity multipliers are tested without
selecting values to obtain recovery. The shared arm estimate comes from the
existing mixer convention. No X500 mass, thrust coefficient or geometry is mixed
into the historical aircraft parameters.

## Reading the video

The blue trace follows the logged centre of mass. All cases use the same world
scale, camera orientation and playback speed. The camera follows horizontal
travel after the initial movement within the frame; camera height stays fixed.
Floor motion and the departing release pad show that travel. Graphs use the
same logged samples. Neither position nor attitude is amplified or eased.

The generic airframe is enlarged equally for visibility. It is an illustrative
glyph, not CAD or a collision envelope. Blade animation follows each motor's
normalized speed at a readable display rate; it does not show physical RPM.
The removed header/footer text stays absent. There is no "Recovered" badge:
this controller has no horizontal position loop, and the recorded settling
criterion only covers attitude, angular rate and vertical speed.

## Limits

These are estimated-aircraft simulations, with unmeasured inertia, propulsion,
drag, geometry and response parameters. The motor model has no electrical or
battery dynamics; the run has no wind, measurement noise or estimator delay
beyond the retained activation delay. Ground contact uses centre height. This
replay is neither a PX4 flight-stack run nor hardware validation. It does not
advance the component-measurement gates in [ROADMAP.md](../ROADMAP.md).

## Reproduce

Run from the repository root with the analysis dependencies installed:

```sh
python -m Analysis.recovery_video
python -m unittest Analysis.tests.test_recovery_video -v
python tools/recovery_video/prepare.py
blender --background --python tools/recovery_video/render.py
python tools/recovery_video/compose.py
```

Rendering additionally needs Blender with the EEVEE API used by the script
(tested with Blender 3.2.2), Pillow and FFmpeg. Use `-- --preview` after the Blender
command and `--preview` after the compositor for selected frames. Intermediate
frames stay in the ignored `.video-build/` directory. Copy a generated composite
frame to the preview image path if regenerating that thumbnail.

The tests independently check feasible allocation, saturation, analytical motor
steps, unpowered ballistic motion and contact termination. The run also halves
the integration step for every displayed case. Values and deviations are in the
result file, alongside all motor-response sensitivity outcomes.
