"""Ground-side drop trigger for flight controllers that cannot run ArduPilot Lua (F405/F411/F7 1 MB boards).

drop_trigger.lua is the reference method (motor outputs held at MOT_SPIN_ARM idle for exactly t_cut, on the
flight controller's own clock). Boards without Lua need a different way to make the cut. The obvious options fail:
  - Motor Emergency Stop (RCx_OPTION 31) forces SHUT_DOWN, then a re-spool that hides ~1 s inside t_cut (SITL, RevS).
  - A radio mode switch is debounced by ArduPilot (~200 ms), so the recovery would start ~200 ms late.

This tool does it over MAVLink from a laptop:
  1. checks: armed, in ALT_HOLD, height >= 1.5 m, pack (measured) >= 7.4 V on 2S  -> otherwise refuse
  2. SET_MODE STABILIZE and RC override throttle = 1000 (same instant)
     -> ArduCopter Stabilize at zero throttle keeps the motors at MOT_SPIN_MIN with attitude control active.
        It only spools down to ground idle after 400 ms of zero throttle (THROTTLE_ZERO_DEBOUNCE), so cuts must
        stay <= 350 ms or the recovery inherits a spool-up delay. The tool refuses longer cuts.
  3. after t_cut: RC override throttle = 1500 and SET_MODE ALT_HOLD -> stock AltHold arrests the fall
  4. aborts: kill switch (aux 31) stays with the pilot and wins at any time; Ctrl-C releases the override at once

Differences from the Lua method (record them in the paper's method section):
  - cut thrust is MOT_SPIN_MIN (with attitude control), not MOT_SPIN_ARM idle;
  - t_cut is timed on the laptop and carried over the link: link latency/jitter (SiK or ELRS MAVLink: ~10-50 ms)
    shifts both edges. Take the real cut and release times from the dataflash log (RCOU / MODE), never from here.

SITL FINDING (2026-11-06, cheapest-drone model): the recovery is NOT the same controller as with the Lua method.
  Re-entering ALT_HOLD re-initialises its altitude controller at the current height and sink rate, then eases the sink
  to zero within PILOT_ACC_Z (2.5 m/s^2) and PSC_D_JERK (5 m/s^3). With defaults it lost 1.85 m after a 100 ms cut
  (Lua method: 0.15 m), because under Lua AltHold never stops and keeps its original target. See
  01_Airframe_Structure/Cheapest/README.md. With PILOT_ACC_Z 5 and PSC_D_JERK 30 it improves to 0.86 / 1.59 / 2.07 m
  at 100 / 200 / 300 ms (Lua: 0.14 / 0.39 / 0.82 m with the same limits). Treat ground-timed drops as a separate
  experimental condition, not as equivalent to drop_trigger.lua.

Usage (real aircraft, props on, in the net cage):  python gcs_drop_trigger.py <mavlink url> <t_cut_ms>
         e.g.  python gcs_drop_trigger.py udp:0.0.0.0:14550 200
Imported by sitl_drop_test.py (--cut-method gcs).
"""
import sys
import time

from pymavlink import mavutil

MIN_ALT_M = 1.5
MIN_V_2S = 7.4
MAX_CUT_MS = 350          # ArduCopter THROTTLE_ZERO_DEBOUNCE is 400 ms: beyond it Stabilize spools to ground idle
SEND_PERIOD_S = 0.02


def _mode_id(m, name):
    return m.mode_mapping()[name]


def _override(m, thr, kill=0):
    # channel 8 = 0 releases it back to the radio, so the pilot's kill switch stays live (MAVLink: 0 = release)
    kill = kill[0] if isinstance(kill, list) else kill   # a list lets a test harness flip it mid-cut
    m.mav.rc_channels_override_send(m.target_system, m.target_component, 1500, 1500, thr, 1500, 0, 0, 0, kill)


def preconditions(m, state):
    """state: dict with keys armed, mode, rel_alt_m, volt. Returns (ok, reason)."""
    if not state.get("armed"):
        return False, "disarmed"
    if state.get("mode") != "ALT_HOLD":
        return False, f"mode {state.get('mode')}"
    if state.get("rel_alt_m", 0) < MIN_ALT_M:
        return False, f"too low ({state.get('rel_alt_m', 0):.2f} m)"
    if state.get("volt") is None or state["volt"] < MIN_V_2S:
        return False, f"pack {state.get('volt')} V < {MIN_V_2S} V"
    return True, ""


def read_state(m, timeout=1.0):
    st, end = {}, time.time() + timeout
    while time.time() < end and len(st) < 4:
        msg = m.recv_match(type=["HEARTBEAT", "GLOBAL_POSITION_INT", "SYS_STATUS"], blocking=True, timeout=0.2)
        if msg is None:
            continue
        t = msg.get_type()
        if t == "HEARTBEAT" and msg.type != mavutil.mavlink.MAV_TYPE_GCS:
            st["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            st["mode"] = mavutil.mode_string_v10(msg)
        elif t == "GLOBAL_POSITION_INT":
            st["rel_alt_m"] = msg.relative_alt / 1000.0
        elif t == "SYS_STATUS":
            st["volt"] = msg.voltage_battery / 1000.0
    return st


def gcs_drop(m, cut_ms, state=None, on_sample=None, kill=0):
    """Run one ground-timed cut. Returns dict(refused, reason, t_cmd_cut, t_cmd_release, samples)."""
    if cut_ms > MAX_CUT_MS:
        return {"refused": True, "reason": f"t_cut {cut_ms} ms > {MAX_CUT_MS} ms (Stabilize spools down after 400 ms)"}
    state = state if state is not None else read_state(m)
    ok, why = preconditions(m, state)
    if not ok:
        return {"refused": True, "reason": why}
    t0 = time.time()
    m.mav.set_mode_send(m.target_system, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, _mode_id(m, "STABILIZE"))
    _override(m, 1000, kill)
    try:
        while time.time() - t0 < cut_ms / 1000.0:
            _override(m, 1000, kill)
            if on_sample:
                on_sample()
            time.sleep(max(0.0, min(SEND_PERIOD_S, cut_ms / 1000.0 - (time.time() - t0))))
    finally:   # release on any exit, including Ctrl-C
        t1 = time.time()
        _override(m, 1500, kill)
        m.mav.set_mode_send(m.target_system, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, _mode_id(m, "ALT_HOLD"))
    return {"refused": False, "reason": "", "t_cmd_cut": t0, "t_cmd_release": t1, "cmd_cut_ms": round((t1 - t0) * 1000, 1)}


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    m = mavutil.mavlink_connection(sys.argv[1], source_system=255)
    m.wait_heartbeat(timeout=10)
    m.mav.request_data_stream_send(m.target_system, m.target_component, mavutil.mavlink.MAV_DATA_STREAM_ALL, 25, 1)
    res = gcs_drop(m, int(sys.argv[2]))
    print(res)
    # keep sending the neutral override briefly, then release the override so the transmitter has control again
    end = time.time() + 2.0
    while time.time() < end:
        _override(m, 1500)
        time.sleep(SEND_PERIOD_S)
    m.mav.rc_channels_override_send(m.target_system, m.target_component, 0, 0, 0, 0, 0, 0, 0, 0)


if __name__ == "__main__":
    main()
