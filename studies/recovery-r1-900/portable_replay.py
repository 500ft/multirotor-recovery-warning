"""Replay only registered case75 without importing side-effect drivers.

Original scientific files are immutable. Path remapping affects metadata only.
The exact saved class/function AST nodes supply parameter and allocator algebra.
"""
from __future__ import annotations

import argparse
import ast
import copy
import dataclasses
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys
import time
import traceback
import types

import numpy as np

HERE = Path(__file__).resolve().parent
EXPECTED_MAP_SHA256 = "2acf2f7bc01a3929dcdceb26d4431159196708e618eaca2424627efa27401c1b"
PLANTS = ("historical_actual_code", "Variant_C", "Cheapest_H7")
RTOL = ATOL = 1e-11


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def guarded_inputs():
    path = HERE / "source-map.json"
    if sha(path) != EXPECTED_MAP_SHA256:
        raise ValueError("Source map differs from declared review version")
    mapping = read(path)
    if len(mapping["records"]) != 40:
        raise ValueError("Expected exactly40 copied original records")
    repo = HERE.parents[1]
    resolved = {}
    for record in mapping["records"]:
        target = (repo / record["review_path"]).resolve(strict=True)
        if not target.is_relative_to(HERE.resolve()):
            raise ValueError("Mapped evidence leaves the study directory")
        if sha(target) != record["sha256"]:
            raise ValueError("Copied evidence hash mismatch: " + record["review_path"])
        registered = record["frozen_expected_sha256"]
        if registered is not None and registered != record["sha256"]:
            raise ValueError("Original freeze differs from copied evidence hash")
        resolved[record["original_path"]] = target
    freeze = read(HERE / "results/FROZEN_BEFORE_OUTCOMES.json")
    for item in freeze["files"]:
        if item["path"] not in resolved or sha(resolved[item["path"]]) != item["sha256"]:
            raise ValueError("Frozen input not resolved exactly")
    return mapping, resolved, freeze


def pure_kernel(filename, module_name):
    # These saved kernels have only definitions/constants plus a __main__ guard.
    spec = importlib.util.spec_from_file_location(module_name, HERE / "frozen" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def selected_definitions(filename, names, module_name, namespace):
    path = HERE / "frozen" / filename
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    selected = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    if {n.name for n in selected} != set(names) or len(selected) != len(names):
        raise ValueError("Selected definition guard failed")
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    isolated = ast.fix_missing_locations(ast.Module(body=[future] + selected, type_ignores=[]))
    module = types.ModuleType(module_name)
    module.__dict__.update(namespace)
    sys.modules[module_name] = module
    exec(compile(isolated, str(path), "exec"), module.__dict__)
    return module


def compare(expected, actual, prefix, record):
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            raise ValueError("Result fields differ at " + prefix)
        for key in expected:
            if key != "elapsed_s":
                compare(expected[key], actual[key], prefix + "." + key, record)
        return
    if isinstance(expected, (bool, str, int)) or expected is None:
        passed = type(actual) is type(expected) and actual == expected
        record.append({"field": prefix, "expected": expected, "measured": actual, "exact": True, "pass": passed})
    elif isinstance(expected, float):
        error = abs(float(actual) - expected)
        limit = ATOL + RTOL * abs(expected)
        passed = math.isfinite(float(actual)) and error <= limit
        record.append({"field": prefix, "expected": expected, "measured": float(actual), "absolute_error": error, "limit": limit, "margin": limit-error, "pass": passed})
    else:
        raise ValueError("Unexpected saved result type at " + prefix)
    if not passed:
        raise ValueError("First replay mismatch at " + prefix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh directory; must not already exist")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Output directory already exists; no retry/overwrite")
    if output.is_relative_to(HERE):
        raise ValueError("Output must be outside immutable study/input directory")
    output.mkdir(parents=True, exist_ok=False)
    status = {"status": "STARTED", "selected_case_id": 75, "dt_s": .0005, "completed": []}
    comparisons = {}
    write(output / "STATUS.json", status)
    try:
        sys.dont_write_bytecode = True
        protocol_path = HERE / "PORTABLE_CASE75_PROTOCOL.json"
        protocol = read(protocol_path)
        if protocol["wrapper_sha256"] != sha(__file__) or protocol["source_map_sha256"] != EXPECTED_MAP_SHA256:
            raise ValueError("Predeclared wrapper/protocol hash guard failed")
        if protocol["case_id"] != 75 or protocol["dt_s"] != .0005 or protocol["plant_order"] != list(PLANTS):
            raise ValueError("Replay selection changed")
        if protocol["scalar_rtol"] != RTOL or protocol["scalar_atol"] != ATOL:
            raise ValueError("Replay tolerance changed")
        mapping, resolved, freeze = guarded_inputs()
        write(output / "ENVIRONMENT.json", {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform(), "machine": platform.machine(), "numpy": np.__version__, "wrapper_sha256": sha(__file__), "protocol_sha256": sha(protocol_path), "source_map_sha256": EXPECTED_MAP_SHA256})
        write(output / "PROTOCOL_USED.json", protocol)
        cohort = read(HERE / "frozen/frozen_cohort.json")
        rows = cohort["cases"] if "cases" in cohort else cohort["rows"]
        matches = [row for row in rows if row["case_id"] == 75]
        if len(matches) != 1 or len(rows) != 300:
            raise ValueError("Frozen cohort selection mismatch")
        row = matches[0]
        tensor = pure_kernel("sim_release_recovery_tensor.py", "portable_saved_tensor")
        executed = pure_kernel("sim_release_recovery_bounded_v2.py", "portable_saved_executed")
        base = selected_definitions("r1_recovery_runner.py", {"TensorParams", "parameters"}, "portable_parameters", {"KERNEL": tensor, "np": np, "dataclasses": dataclasses})
        captured = {}

        def capture_simulate(*a, **kw):
            result = executed.simulate(*a, **kw)
            captured["log"] = result["log"]
            return result

        runner = selected_definitions("r1_bounded_v2.py", {"BoundedXAllocation", "rotor_centres", "allocation", "one_run"}, "portable_runner", {"np": np, "math": math, "json": json, "Path": Path, "time": time, "base": base, "KERNEL": types.SimpleNamespace(simulate=capture_simulate)})
        for name in PLANTS:
            guarded_inputs()
            model = copy.deepcopy(freeze["models"][name])
            if "physical_model_path" in model:
                original_path = model["physical_model_path"]
                model["physical_model_path"] = str(resolved[original_path])
            case_dir = output / name
            case_dir.mkdir()
            captured.clear()
            result = runner.one_run(name, model, row, dt=.0005)
            write(case_dir / "result.json", result)
            np.savez_compressed(case_dir / "available_scalar_trajectory.npz", **captured["log"])
            write(case_dir / "trajectory_fields.json", {"columns": {"t": "s", "tilt": "rad", "omega_mag": "rad/s", "z": "m", "vz": "m/s", "thrust": "N"}, "samples": len(captured["log"]["t"]), "scope": "Six logged scalar trajectories already exposed by unchanged kernel; not complete quaternion/body-state telemetry."})
            saved = read(HERE / "results" / (name + ".json"))
            expected = next(x for x in saved["runs"] if x["case_id"] == 75)
            comparisons[name] = []
            try:
                compare(expected, result, name, comparisons[name])
            finally:
                write(output / "COMPARISONS.json", comparisons)
            guarded_inputs()
            status["completed"].append(name)
            write(output / "STATUS.json", status)
            print("PASS case75 " + name, flush=True)
        guarded_inputs()
        status["status"] = "THREE_CASE75_REPLAYS_MATCH_SAVED_RESULTS"
        status["original_40_files_unchanged"] = True
        status["qualification"] = "Path/loading reproduction only; no900-case rerun or new physical conclusion"
        write(output / "STATUS.json", status)
        return 0
    except BaseException as exc:
        status["status"] = "STOP_FIRST_FAILURE_NO_RETRY"
        status["exception"] = repr(exc)
        write(output / "STOP_STATUS.json", status)
        (output / "TRACEBACK.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print("STOP: " + repr(exc), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
