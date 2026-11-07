# Desktop drop-test tools

The current script accepts 50 to 400 ms requests. It holds motors at armed idle, so this is a thrust-reduction maneuver rather than a guaranteed zero-thrust free fall. The forced output override expires in firmware. Clearing it immediately on E-stop depends on Lua execution; independent stop under a script fault remains unqualified.

The retained runs identify their actual script as `drop_trigger_used.lua` in each aircraft folder. That snapshot and the model match the hashes in the result. The main script's comments were subsequently clarified without changing its behavior.

All-channel stop checking requires a firmware-timestamped RC8 transition and a sustained stopped output on every motor within 100 ms. Missing references remain unverified. Average PWM and a single low sample do not qualify this check. Run `python GroundTools/check_stop.py` for the four adversarial checker cases.

The flight-controller calibration, sensor orientation, UART assignments, motor order, regulator margin and physical kill circuit require bench qualification. These desktop parameters are not flight-ready settings. The ground-side mode-switch procedure remains a separate experimental condition.
