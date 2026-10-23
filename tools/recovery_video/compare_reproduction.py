"""Compare a rerun of the recovery replay with the committed result files.

Run ``python -m Analysis.recovery_video`` in a separate checkout of the same
revision, then run this script with the same interpreter so the recorded
Python and NumPy versions are the rerun's:

    python tools/recovery_video/compare_reproduction.py <rerun Data/recovery-video> --out <record.json>

The committed files are only read. The record holds every scalar field of
results.json side by side with its rerun value, the largest differences in
altitude loss and held-recovery time against the committed half-step
convergence deltas, and the largest array difference per logged quantity.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "Data/recovery-video"
CASES = ("best", "nominal", "worst")


def leaves(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from leaves(value, f"{prefix}{key}/")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from leaves(value, f"{prefix}{index}/")
    else:
        yield prefix.rstrip("/"), node


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_results(committed, rerun):
    expected = dict(leaves(committed))
    actual = dict(leaves(rerun))
    fields = {}
    for path, value in expected.items():
        other = actual.get(path, "missing")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or other == "missing" \
                or isinstance(other, bool) or not isinstance(other, (int, float)):
            fields[path] = {"committed": value, "reproduced": other, "equal": value == other}
        else:
            fields[path] = {"committed": value, "reproduced": other, "abs_difference": abs(value - other)}
    extra = sorted(set(actual) - set(expected))
    return fields, extra


def max_difference(fields, suffix):
    diffs = [f["abs_difference"] for path, f in fields.items()
             if path.endswith(suffix) and "abs_difference" in f]
    return max(diffs) if diffs else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rerun", type=Path, help="directory holding the rerun results.json and .npz files")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--command", default="python -m Analysis.recovery_video")
    parser.add_argument("--elapsed-s", type=float, default=None)
    args = parser.parse_args()

    committed = json.loads((COMMITTED / "results.json").read_text())
    rerun = json.loads((args.rerun / "results.json").read_text())
    fields, extra = compare_results(committed, rerun)
    arrays = {}
    for case in CASES:
        with np.load(COMMITTED / f"{case}.npz") as a, np.load(args.rerun / f"{case}.npz") as b:
            arrays[case] = {}
            for key in a.files:
                same_shape = a[key].shape == b[key].shape
                arrays[case][key] = {
                    "shape": list(a[key].shape),
                    "same_shape": same_shape,
                    "max_abs_difference": float(np.max(np.abs(a[key] - b[key]))) if same_shape else None}
    convergence = committed["convergence"]
    drop_delta = max(c["max_drop_difference_m"] for c in convergence.values())
    held_delta = max(c["recovery_held_to_end_difference_s"] for c in convergence.values())
    drop_diff = max_difference(fields, "max_drop_m")
    held_diff = max_difference(fields, "recovery_held_to_end_s")
    scalar_max = max((f["abs_difference"] for f in fields.values() if "abs_difference" in f), default=0.0)
    array_max = max(v["max_abs_difference"] for case in arrays.values() for v in case.values())
    identical = (scalar_max == 0.0 and array_max == 0.0 and not extra
                 and all(f.get("equal", True) for f in fields.values())
                 and all(v["same_shape"] for case in arrays.values() for v in case.values()))
    try:
        cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        cpu = platform.processor()
    record = {
        "date": dt.date.today().isoformat(),
        "committed": {
            "results": "results.json",
            "commit": git("log", "-1", "--format=%H", "--", "Data/recovery-video/results.json"),
            "results_sha256": sha256(COMMITTED / "results.json"),
            "settings_sha256": sha256(COMMITTED / "settings.json"),
            "rerun_results_sha256": sha256(args.rerun / "results.json"),
        },
        "rerun": {
            "command": args.command,
            "source_revision": git("rev-parse", "HEAD"),
            "elapsed_s": args.elapsed_s,
            "host": {"platform": platform.platform(), "machine": platform.machine(), "cpu": cpu},
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        },
        "summary": {
            "identical": identical,
            "scalar_fields": len(fields),
            "scalar_fields_differing": sum(1 for f in fields.values()
                                           if f.get("abs_difference", 0.0) != 0.0 or f.get("equal") is False),
            "unexpected_rerun_fields": extra,
            "max_abs_difference_all_scalars": scalar_max,
            "max_abs_difference_max_drop_m": drop_diff,
            "max_abs_difference_recovery_held_to_end_s": held_diff,
            "committed_half_step_delta_max_drop_m": drop_delta,
            "committed_half_step_delta_recovery_held_to_end_s": held_delta,
            "max_drop_within_half_step_delta": drop_diff <= drop_delta,
            "recovery_held_within_half_step_delta": held_diff <= held_delta,
            "max_abs_difference_logged_arrays": array_max,
        },
        "fields": fields,
        "arrays": arrays,
    }
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record["summary"], indent=2))


if __name__ == "__main__":
    main()
