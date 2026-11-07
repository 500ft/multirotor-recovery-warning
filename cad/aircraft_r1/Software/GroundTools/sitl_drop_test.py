"""ArduPilot SITL verification of scripts/drop_trigger.lua (programmed in-flight motor cut).

Runs the stock ArduCopter SITL (quad model), loads drop_trigger.lua, takes off, switches to
AltHold, fires drops with several cut times, and records height lost / time to re-stabilise.
Also checks the script's safety refusals (wrong mode, too low).

Usage:  python sitl_drop_test.py <folder with ArduCopter.elf> <out.json>
            [--model x | x:RevS_sitl_150g.json] [--param NAME=VALUE ...] [--cuts 100,200,300] [--alt 12]
            [--cut-method lua | gcs]   gcs = ground-timed Stabilize/zero-throttle cut for boards without Lua
                                       (gcs_drop_trigger.py); both methods report the MEASURED output cut
SITL binaries: https://firmware.ardupilot.org/Tools/MissionPlanner/sitl/CopterStable/
(ArduCopter.elf + cyg*.dll).  Needs pymavlink.  Simulation only - the SITL quad is a ~1.5 kg
model, so absolute heights differ from RevS; the test verifies MECHANISM and SAFETY LOGIC.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time

from pymavlink import mavutil

HERE = os.path.dirname(os.path.abspath(__file__))
LUA = os.path.join(HERE, "..", "ArduPilot", "scripts", "drop_trigger.lua")
ap = argparse.ArgumentParser()
ap.add_argument("sitl_dir")
ap.add_argument("out")
ap.add_argument("--model", default="x", help="SITL frame, e.g. x or x:RevS_sitl_150g.json")
ap.add_argument("--param", action="append", default=[], help="NAME=VALUE set before the reboot")
ap.add_argument("--cuts", default="200,400,600")
ap.add_argument("--alt", type=float, default=12.0)
ap.add_argument("--hover-only", action="store_true", help="take off, hover 20 s in AltHold, report motor spread, stop")
ap.add_argument("--no-pack-test", action="store_true", help="skip the low-pack refusal test (e.g. 3S generic model)")
ap.add_argument("--cut-method", choices=("lua", "gcs"), default="lua")
ARGS = ap.parse_args()
SITL_DIR, OUT = ARGS.sitl_dir, ARGS.out
MODEL_FILE = ARGS.model.split(":", 1)[1] if ":" in ARGS.model else None
MODEL_DATA = json.load(open(MODEL_FILE)) if MODEL_FILE and os.path.isfile(MODEL_FILE) else {}
PACK_MAX_V = MODEL_DATA.get("maxVoltage", 8.4)
KILL = [1000]   # RC channel 8 (Motor Emergency Stop switch) value sent with every override
G = 9.80665
log = {"events": [], "drops": [], "refusals": [], "model": ARGS.model, "params": ARGS.param, "cut_method": ARGS.cut_method}
log["model_input"] = MODEL_DATA
log["model_sha256"] = hashlib.sha256(open(MODEL_FILE,"rb").read()).hexdigest() if MODEL_FILE else None
log["script_sha256"] = hashlib.sha256(open(LUA,"rb").read()).hexdigest()
log["scope"] = "Level vertical recovery in desktop SITL; physical board, arbitrary-attitude recovery and hardware kill behavior unqualified"
SERVO = []     # (t, mean motor PWM) from SERVO_OUTPUT_RAW, to measure the real cut
MOTOR_SAMPLES = [] # firmware microseconds and all four channels, preserved without averaging
LAST = {"att": (0.0, 0.0), "pwr": (float("nan"), float("nan"))}
if ARGS.cut_method == "gcs":
    import gcs_drop_trigger as GCS


def dump():
    json.dump(log, open(OUT, "w"), indent=1)


def watchdog(seconds, proc_ref):
    """Hard stop: if the run hangs anywhere, kill SITL, write what we have and exit."""
    def fire():
        say(f"WATCHDOG: run exceeded {seconds} s, aborting")
        log["aborted"] = True
        try:
            proc_ref[0].kill()
        except Exception:
            pass
        dump()
        os._exit(2)
    t = threading.Timer(seconds, fire)
    t.daemon = True
    t.start()


def say(m):
    print(m, flush=True)
    log["events"].append(m)


def start_sitl(wipe):
    os.makedirs(os.path.join(SITL_DIR, "scripts"), exist_ok=True)
    shutil.copy(LUA, os.path.join(SITL_DIR, "scripts", "drop_trigger.lua"))
    model = ARGS.model
    if ":" in model:   # frame:file.json -> copy the JSON next to the binary, pass it by name
        frame, js = model.split(":", 1)
        if os.path.isfile(js):
            shutil.copy(js, os.path.join(SITL_DIR, os.path.basename(js)))
        model = f"{frame}:{os.path.basename(js)}"
    args = [os.path.join(SITL_DIR, "ArduCopter.elf"), "-S", "--model", model, "--speedup", "1",
            "--home", "40.6942,-73.9866,10,0", "-I0"]
    if wipe:
        args.append("-w")
    return subprocess.Popen(args, cwd=SITL_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect():
    for _ in range(60):
        try:
            m = mavutil.mavlink_connection("tcp:127.0.0.1:5760", source_system=255)
            if m.wait_heartbeat(timeout=5):
                return m
        except Exception:
            time.sleep(1)
    raise RuntimeError("no heartbeat from SITL")


def setp(m, name, val):
    for _ in range(5):
        m.mav.param_set_send(m.target_system, m.target_component, name.encode(), float(val),
                             mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=3)
        if msg and msg.param_id.rstrip("\x00") == name and abs(msg.param_value - val) < 1e-3:
            return True
    say(f"WARN param {name} not confirmed")
    return False


def drain_text(m, t=0.2):
    end = time.time() + t
    while time.time() < end:
        msg = m.recv_match(type="STATUSTEXT", blocking=False)
        if msg is None:
            time.sleep(0.01)
            continue
        say("STATUSTEXT: " + msg.text)


def wait_text(m, needle, timeout):
    end = time.time() + timeout
    while time.time() < end:
        rc_hold(m)
        msg = m.recv_match(type=["STATUSTEXT", "SERVO_OUTPUT_RAW", "ATTITUDE", "SYS_STATUS"], blocking=True, timeout=0.1)
        if msg:
            handle(msg, [])
            if msg.get_type() == "STATUSTEXT" and needle in msg.text:
                return True
    return False


def rc_hold(m, thr=1500):
    m.mav.rc_channels_override_send(m.target_system, m.target_component, 1500, 1500, thr, 1500,
                                    0, 0, 0, KILL[0])


def arm(m, timeout=60):
    """Arm with retries; logs PreArm messages instead of blocking forever."""
    end = time.time() + timeout
    while time.time() < end:
        m.arducopter_arm()
        t1 = time.time() + 3
        while time.time() < t1:
            msg = m.recv_match(type=["HEARTBEAT", "STATUSTEXT"], blocking=True, timeout=0.5)
            if msg is None:
                continue
            if msg.get_type() == "STATUSTEXT":
                say("STATUSTEXT: " + msg.text)
            elif msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                return True
    return False


def set_mode(m, name):
    m.set_mode(m.mode_mapping()[name])
    for _ in range(20):
        hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if hb and mavutil.mode_string_v10(hb) == name:
            return True
    return False


def climb_to(m, alt, settle=8):
    """GUIDED climb back to `alt` m above home, then return to ALT_HOLD."""
    set_mode(m, "GUIDED")
    for _ in range(3):
        m.mav.set_position_target_local_ned_send(0, m.target_system, m.target_component,
                                                 mavutil.mavlink.MAV_FRAME_LOCAL_NED, 0b0000111111111000,
                                                 0, 0, -alt, 0, 0, 0, 0, 0, 0, 0, 0)
    alt_stream(m, settle, rc=False)
    set_mode(m, "ALT_HOLD")
    alt_stream(m, 4)


def alt_stream(m, seconds, rc=True):
    """Return list of (t, rel_alt_m, vz_up, roll_deg, pitch_deg, volt, amp) for `seconds`."""
    data = []
    end = time.time() + seconds
    while time.time() < end:
        if rc == "none":
            pass
        elif rc:
            rc_hold(m)
        else:   # leave sticks to the autopilot but keep the kill-switch channel defined
            m.mav.rc_channels_override_send(m.target_system, m.target_component, 0, 0, 0, 0, 0, 0, 0, KILL[0])
        msg = m.recv_match(type=["GLOBAL_POSITION_INT", "ATTITUDE", "STATUSTEXT", "SYS_STATUS", "SERVO_OUTPUT_RAW"],
                           blocking=True, timeout=0.2)
        if msg is None:
            continue
        handle(msg, data)
    return data


def handle(msg, data):
    t = msg.get_type()
    if t == "ATTITUDE":
        LAST["att"] = (math.degrees(msg.roll), math.degrees(msg.pitch))
    elif t == "GLOBAL_POSITION_INT":
        data.append((time.time(), msg.relative_alt / 1000.0, -msg.vz / 100.0, *LAST["att"], *LAST["pwr"]))
    elif t == "SYS_STATUS":
        LAST["pwr"] = (msg.voltage_battery / 1000.0, msg.current_battery / 100.0)
    elif t == "SERVO_OUTPUT_RAW":
        SERVO.append((time.time(), (msg.servo1_raw + msg.servo2_raw + msg.servo3_raw + msg.servo4_raw) / 4.0))
        MOTOR_SAMPLES.append((int(msg.time_usec),[msg.servo1_raw,msg.servo2_raw,msg.servo3_raw,msg.servo4_raw]))
    elif t == "STATUSTEXT":
        say("STATUSTEXT: " + msg.text)


def drain(m, data):
    """Non-blocking: read whatever is queued (used inside the timed gcs cut)."""
    while True:
        msg = m.recv_match(type=["GLOBAL_POSITION_INT", "ATTITUDE", "STATUSTEXT", "SYS_STATUS", "SERVO_OUTPUT_RAW"],
                           blocking=False)
        if msg is None:
            return
        handle(msg, data)


def measured_cut(t_from, t_to, hover_us):
    """Length of the window in which mean motor PWM sat below the hover/idle midpoint (SITL stream ~20 ms)."""
    s = [(t, v) for t, v in SERVO if t_from <= t <= t_to]
    thr = 1000 + 0.5 * (hover_us - 1000)
    low = [t for t, v in s if v < thr]
    if not low:
        return None, None
    return round((max(low) - min(low)) * 1000), round(min(v for _, v in s))


def gcs_state(m):
    st = GCS.read_state(m, 1.0)
    return st


def try_refusal(m, needle="DROP refused"):
    """Fire a 300 ms drop request that SHOULD be refused; True if it was."""
    if ARGS.cut_method == "lua":
        setp(m, "SCR_USER6", 300)
        return wait_text(m, needle, 5)
    res = GCS.gcs_drop(m, 300, state=gcs_state(m), kill=KILL)
    say(f"GCS drop request: {res}")
    return bool(res["refused"])


def main():
    p = start_sitl(wipe=True)
    pref = [p]
    watchdog(600, pref)
    try:
        m = connect()
        say("connected to SITL")
        for k, v in (("FRAME_CLASS", 1), ("FRAME_TYPE", 1), ("SCR_ENABLE", 1), ("SCR_HEAP_SIZE", 200000),
                     ("SCR_USER6", 0), ("RC8_OPTION", 31), ("BATT_MONITOR", 4)):
            setp(m, k, v)
        for kv in ARGS.param:
            k, v = kv.split("=", 1)
            setp(m, k, float(v))
        # ArduPilot 4.7 replaced ARMING_CHECK with ARMING_SKIPCHK (bitmask of checks to skip)
        if not setp(m, "ARMING_SKIPCHK", -1):
            setp(m, "ARMING_CHECK", 0)
        m.mav.command_long_send(m.target_system, m.target_component,
                                mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN, 0, 1, 0, 0, 0, 0, 0, 0)
        time.sleep(3)
        p.terminate(); p.wait(10)
        p = start_sitl(wipe=False)
        pref[0] = p
        m = connect()
        say("restarted with scripting enabled")
        log["script_loaded"] = wait_text(m, "drop_trigger.lua loaded", 30)
        m.mav.request_data_stream_send(m.target_system, m.target_component, mavutil.mavlink.MAV_DATA_STREAM_ALL, 25, 1)
        for msg_id in (36, 33, 30):   # SERVO_OUTPUT_RAW, GLOBAL_POSITION_INT, ATTITUDE at 50 Hz
            m.mav.command_long_send(m.target_system, m.target_component, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                                    0, msg_id, 20000, 0, 0, 0, 0, 0)
        # wait for EKF / GPS
        t0 = time.time()
        while time.time() - t0 < 90:
            msg = m.recv_match(type="GPS_RAW_INT", blocking=True, timeout=2)
            if msg and msg.fix_type >= 3:
                break
        time.sleep(15)
        # refusal 1: disarmed
        log["refusals"].append({"case": "disarmed", "refused": try_refusal(m)})
        # take off in GUIDED
        log["guided_ok"] = set_mode(m, "GUIDED")
        log["armed"] = arm(m)
        if not log["armed"]:
            say("could not arm; stopping")
            return
        m.mav.command_long_send(m.target_system, m.target_component, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                                0, 0, 0, 0, 0, 0, 0, ARGS.alt)
        alt_stream(m, 15, rc=False)
        # refusal 2: wrong mode (GUIDED)
        log["refusals"].append({"case": "mode GUIDED", "refused": try_refusal(m)})
        set_mode(m, "ALT_HOLD")
        alt_stream(m, 6)
        if ARGS.hover_only:
            outs, atts, end = [], [], time.time() + 20
            while time.time() < end:
                rc_hold(m)
                msg = m.recv_match(type=["SERVO_OUTPUT_RAW", "ATTITUDE"], blocking=True, timeout=0.2)
                if msg is None:
                    continue
                if msg.get_type() == "SERVO_OUTPUT_RAW":
                    outs.append([msg.servo1_raw, msg.servo2_raw, msg.servo3_raw, msg.servo4_raw])
                else:
                    atts.append(max(abs(math.degrees(msg.roll)), abs(math.degrees(msg.pitch))))
            log["hover"] = {"motor_spread_us_mean": round(sum(max(o) - min(o) for o in outs) / max(1, len(outs)), 1),
                            "motor_mean_us": round(sum(sum(o) / 4 for o in outs) / max(1, len(outs)), 1),
                            "att_abs_max_deg": round(max(atts), 1) if atts else None}
            say(f"HOVER {log['hover']}")
            return
        if not ARGS.no_pack_test:
            # refusal 3: pack below the window (simulated full-pack voltage lowered to 7.3 V)
            setp(m, "SIM_BATT_VOLTAGE", 7.3)
            alt_stream(m, 4)
            log["refusals"].append({"case": "pack 7.3 V < 7.4 V", "refused": try_refusal(m, "DROP refused: pack")})
            setp(m, "SIM_BATT_VOLTAGE", PACK_MAX_V)
            alt_stream(m, 4)
        for cut in [int(c) for c in ARGS.cuts.split(",")]:
            climb_to(m, ARGS.alt)
            pre = alt_stream(m, 3)
            h0 = sum(a for _, a, *_ in pre[-10:]) / max(1, len(pre[-10:]))
            hover_us = sum(v for t, v in SERVO[-50:]) / max(1, len(SERVO[-50:]))
            t_start = time.time()
            cmd = None
            if ARGS.cut_method == "lua":
                setp(m, "SCR_USER6", cut)
                data = alt_stream(m, 10)
            else:
                data = []
                res = GCS.gcs_drop(m, cut, state=gcs_state(m), on_sample=lambda: drain(m, data), kill=KILL)
                if res["refused"]:
                    say(f"GCS drop refused: {res['reason']}")
                    continue
                cmd = res["cmd_cut_ms"]
                data += alt_stream(m, 10)
            meas_ms, min_us = measured_cut(t_start, t_start + 3.0, hover_us)
            if not data:
                continue
            tt = [d[0] - data[0][0] for d in data]
            alts = [d[1] for d in data]
            i_min = min(range(len(alts)), key=lambda i: alts[i])
            # re-stabilised: vz within +-0.3 m/s and |att| < 10 deg for 1 s after the minimum
            t_stable = None
            for i in range(i_min, len(data)):
                win = [d for d in data[i:] if d[0] - data[i][0] <= 1.0]
                if win and win[-1][0] - data[i][0] >= 0.9 and all(abs(d[2]) < 0.3 and abs(d[3]) < 10 and abs(d[4]) < 10 for d in win):
                    t_stable = tt[i]
                    break
            ff = 0.5 * G * (cut / 1000) ** 2
            rec = {"cut_ms": cut, "h_start_m": round(h0, 2), "h_min_m": round(alts[i_min], 2),
                   "height_lost_m": round(h0 - alts[i_min], 2), "free_fall_only_m": round(ff, 2),
                   "t_min_s": round(tt[i_min], 2), "t_restabilised_s": None if t_stable is None else round(t_stable, 2),
                   "h_end_m": round(alts[-1], 2),
                   "pack_v_before": round(pre[-1][5], 2) if pre else None,
                   "pack_v_min": round(min(d[5] for d in data if d[5] == d[5]), 2),
                   "pack_a_max": round(max(d[6] for d in data if d[6] == d[6]), 1),
                   "att_abs_max_deg": round(max(max(abs(d[3]), abs(d[4])) for d in data), 1),
                   "measured_output_cut_ms": meas_ms, "min_mean_motor_us": min_us,
                   "hover_mean_motor_us": round(hover_us), "commanded_cut_ms_gcs": cmd}
            log["drops"].append(rec)
            say(f"DROP RESULT {rec}")
        # Abort observations are not certification. Evaluate every channel against firmware timestamps below.
        climb_to(m, ARGS.alt)
        if ARGS.cut_method == "lua":
            m.mav.param_set_send(m.target_system,m.target_component,b"SCR_USER6",400,mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
            log["kill_trial_cut_started"] = wait_text(m,"DROP cut 400",2)
            alt_stream(m, 0.12)
            KILL[0] = 2000
            rc_hold(m)
            log["kill_abort_message_seen"] = wait_text(m, "DROP aborted", 0.8)
            log["abort_on_kill_switch"] = "pending all-channel dataflash timing check"
            alt_stream(m, 0.3)
            log["abort_on_mode_change"] = "not run after stop test; separate test required"
            log["landed_disarmed"] = "simulation terminated after sustained kill; landing not tested"
            return
        else:
            # pilot kill switch (aux 31) flipped 150 ms into a 300 ms ground-timed cut: motors must stop at once
            t_k = time.time()
            def flip():
                drain(m, [])
                if time.time() - t_k > 0.15:
                    KILL[0] = 2000
            n_ev = len(log["events"])
            GCS.gcs_drop(m, 300, state=gcs_state(m), on_sample=flip, kill=KILL)
            alt_stream(m, 0.6)
            # pass = ArduPilot reports the E-stop AND the motor outputs reach 1000 us within 1.5 s of the flip.
            # (Timing samples by arrival in Python is too coarse to require "all samples after 350 ms".)
            estop = any("MotorEStop HIGH" in e for e in log["events"][n_ev:])
            low = [v for t, v in SERVO if t_k < t < t_k + 1.5 and v <= 1010]
            log["kill_abort_message_seen"] = bool(estop)
            log["abort_on_kill_switch"] = "pending all-channel dataflash timing check"
        KILL[0] = 1000
        alt_stream(m, 8)
        # abort 2: a mode change during a long cut must end the override at once
        climb_to(m, ARGS.alt)
        if ARGS.cut_method == "lua":
            setp(m, "SCR_USER6", 400)
            time.sleep(0.15)
            set_mode(m, "LAND")
            log["abort_on_mode_change"] = wait_text(m, "DROP aborted", 5)
        else:
            # the ground tool itself switches modes; instead check it refuses a cut longer than the 400 ms debounce
            log["refusals"].append({"case": "t_cut 500 ms > 350 ms", "refused": GCS.gcs_drop(m, 500, state=gcs_state(m))["refused"]})
            log["abort_on_mode_change"] = "n/a (gcs method)"
        set_mode(m, "LAND")
        alt_stream(m, 25, rc=False)
        log["landed_disarmed"] = not m.motors_armed()
        # the "loaded" banner is sent at boot, often before we connect; any DROP text proves it ran
        log["script_loaded"] = log["script_loaded"] or any("DROP " in e for e in log["events"])
        if ARGS.cut_method == "gcs":
            log["script_loaded"] = "n/a (gcs method)"
    finally:
        try:
            p.terminate(); p.wait(10)
        except Exception:
            pass
        with open(OUT.replace('.json','_motor_outputs.json'),'w') as f:
            json.dump(MOTOR_SAMPLES,f)
        dump()
        say(f"wrote {OUT}")


if __name__ == "__main__":
    main()
