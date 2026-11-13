"""Isolated, source-pinned R1 recovery sensitivity experiment.

Default action is preparation. --pilot runs analytical checks and three cases.
--campaign is deliberately separate and requires parent review of the protocol.
No file in the source repository is changed.
"""
from __future__ import annotations

import argparse
import dataclasses
import difflib
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = Path(r"C:\Users\Admin\Documents\ChatGPT\Research\multirotor-recovery-warning")
sys.path.insert(0, str(REPO))
from Analysis import sim_release_recovery as legacy
from Analysis import monte_carlo_recovery as mc
from Analysis import rigid_body

SEED = 20260704
RATES = ((1.0, 75), (2.0, 150), (3.0, 75))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load_tensor_kernel():
    source = REPO / "Analysis/sim_release_recovery.py"
    text = source.read_text(encoding="utf-8")
    replacements = {
        "    I = p.inertia\n": "    I = np.asarray(p.inertia, float)\n    I = np.diag(I) if I.ndim == 1 else I\n    I_inv = np.linalg.inv(I)\n",
        "np.cross(omega_meas, I * omega_meas)": "np.cross(omega_meas, I @ omega_meas)",
        "np.cross(omega, I * omega)": "np.cross(omega, I @ omega)",
        "alpha = (torque - gyro + np.array([0.0, 0.0, drag_z])) / I": "alpha = I_inv @ (torque - gyro + np.array([0.0, 0.0, drag_z]))",
    }
    fork = text
    for old, new in replacements.items():
        if fork.count(old) != 1:
            raise ValueError("Tensor adapter source match failed: " + repr(old))
        fork = fork.replace(old, new)
    target = ROOT / "sim_release_recovery_tensor.py"
    target.write_text(fork, encoding="utf-8")
    (ROOT / "tensor_adapter.diff").write_text("".join(difflib.unified_diff(text.splitlines(True), fork.splitlines(True), fromfile=str(source), tofile=str(target))), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("r1_tensor_kernel", target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


KERNEL = load_tensor_kernel()


@dataclasses.dataclass(frozen=True)
class TensorParams(KERNEL.DroneParams):
    inertia_tensor: tuple = ((0.00035, 0, 0), (0, 0.00035, 0), (0, 0, 0.00056))

    @property
    def inertia(self):
        return np.array(self.inertia_tensor, dtype=float)


def cohort():
    """Reproduce the original sampler's order and distributions, before outcomes."""
    base = legacy.nominal_params()
    rng = np.random.default_rng(SEED)
    rows = []
    for rate, n in RATES:
        for index in range(n):
            p, imp = mc.draw_case(rng)
            rows.append({
                "case_id": len(rows), "rate_rad_s": rate, "index_within_rate": index,
                "multipliers": {key: getattr(p, key) / getattr(base, key) for key in (
                    "mass_kg", "inertia_lateral_kg_m2", "max_torque_n_m", "max_thrust_n",
                    "detection_latency_s", "motor_start_latency_s")},
                "imperfections": dataclasses.asdict(imp),
            })
    return rows


def models():
    p = legacy.nominal_params()
    result = {"historical_actual_code": {
        "mass_kg": p.mass_kg, "inertia_tensor": np.diag(p.inertia).tolist(),
        "max_thrust_n": p.max_thrust_n, "thrust_to_weight": p.max_thrust_n / (p.mass_kg * 9.81),
        "arm_m": 0.060, "nominal_thrust_line_offset_xy_m": [0, 0],
        "basis": "Actual nominal_params used by historical monte_carlo_recovery, not catalog budget",
    }}
    for name in ("Variant_C", "Cheapest_H7"):
        path = REPO / "cad/aircraft_r1" / name / "physical_model.json"
        x = json.loads(path.read_text(encoding="utf-8"))
        I = np.array(x["inertia_kgm2_about_cg"])
        if not np.allclose(I, I.T, atol=1e-15) or np.linalg.eigvalsh(I).min() <= 0:
            raise ValueError("Invalid R1 inertia tensor: " + name)
        thrust = x["propulsion"]["vendor_thrust_per_motor_g"] * 4 * 0.00981 * x["propulsion"]["guard_thrust_retention_assumed"]
        result[name] = {
            "mass_kg": x["total_mass_g"] / 1000, "inertia_tensor": I.tolist(),
            "max_thrust_n": thrust, "thrust_to_weight": thrust / (x["total_mass_g"] * 0.00981),
            "arm_m": x["motor_diagonal_mm"] / 2000,
            "nominal_thrust_line_offset_xy_m": [-a / 1000 for a in x["cg_mm"][:2]],
            "vendor_reference_voltage_v": x["propulsion"]["vendor_test_voltage_v"],
            "guard_retention_assumed": x["propulsion"]["guard_thrust_retention_assumed"],
            "guard_mass_g": sum(z["mass_g"] for z in x["modelled_parts"] if z["name"].startswith("Guard_")),
            "mass_headroom_to_165g_g": 165 - x["total_mass_g"],
            "extra_wiring_fasteners_mass_g": x["extra_wiring_fasteners_mass_g"],
            "max_normalized_offdiagonal": max(abs(I[i,j]) / math.sqrt(I[i,i] * I[j,j]) for i in range(3) for j in range(3) if i != j),
            "physical_model_path": str(path), "physical_model_sha256": sha(path),
            "basis": "CAD/estimated masses, vendor thrust at its stated voltage, assumed guard retention; no measured plant",
        }
    return result


def parameters(model, row):
    m = row["multipliers"]
    I = np.array(model["inertia_tensor"]) * m["inertia_lateral_kg_m2"]
    p = TensorParams(
        mass_kg=model["mass_kg"] * m["mass_kg"],
        inertia_lateral_kg_m2=float(I[0,0]), inertia_tensor=tuple(map(tuple, I)),
        max_torque_n_m=0.004 * m["max_torque_n_m"],
        max_thrust_n=model["max_thrust_n"] * m["max_thrust_n"],
        projected_area_m2=0.012, drag_coefficient=1.0,
        detection_latency_s=0.05 * m["detection_latency_s"],
        motor_start_latency_s=0.06 * m["motor_start_latency_s"],
    )
    # Effective authority-factor convention reproduces the source MC sampler.
    # CAD arm is not changed geometrically; the multiplier is an authority proxy.
    p = KERNEL.with_mixer(p, arm_m=model["arm_m"] * m["max_torque_n_m"])
    impd = dict(row["imperfections"])
    impd["cg_offset_m"] = tuple(np.array(impd["cg_offset_m"]) + model["nominal_thrust_line_offset_xy_m"])
    impd["torque_bias_n_m"] = tuple(impd["torque_bias_n_m"])
    return p, KERNEL.Imperfections(**impd)


def one_run(model, row, dt=0.0005):
    p, imp = parameters(model, row)
    t0 = time.perf_counter()
    r = KERNEL.simulate(p, row["rate_rad_s"], math.radians(60), imperfections=imp, dt=dt, t_max=6.0)
    elapsed = time.perf_counter() - t0
    if not all(np.isfinite(v).all() for v in r["log"].values()):
        raise ValueError("Non-finite integration output")
    result = {k: v for k, v in r.items() if k != "log"}
    result.update(case_id=row["case_id"], elapsed_s=elapsed, dt_s=dt,
                  final_low_tilt=bool(r["log"]["tilt"][-1] < math.radians(5)),
                  final_low_rate=bool(r["log"]["omega_mag"][-1] < 0.3),
                  final_low_vertical_speed=bool(abs(r["log"]["vz"][-1]) < 0.2))
    return result


def analytic_checks(model):
    checks = {}
    d = np.array([0.0002, 0.0003, 0.0005]); w=np.array([0.2,-0.3,0.5]); tau=np.array([0.01,-0.004,0.002])
    original = np.array(rigid_body.angular_acceleration(tuple(w),tuple(tau),tuple(d)))
    full = np.linalg.solve(np.diag(d), tau - np.cross(w, np.diag(d) @ w))
    checks["diagonal_angular_acceleration_equivalence"] = bool(np.allclose(original, full, rtol=1e-13, atol=1e-13))
    p, _ = parameters(model, {"multipliers":dict.fromkeys(("mass_kg","inertia_lateral_kg_m2","max_torque_n_m","max_thrust_n","detection_latency_s","motor_start_latency_s"),1.0), "imperfections":dataclasses.asdict(KERNEL.Imperfections())})
    free = dataclasses.replace(p, drag_coefficient=0.0,detection_latency_s=10.0,motor_start_latency_s=10.0)
    r=KERNEL.simulate(free,0.0,0.0,dt=0.0005,t_max=0.1)
    k=np.arange(len(r["log"]["z"]))
    expected=-9.81 * (0.0005**2) * k*(k+1)/2
    checks["semi_implicit_freefall_exact_sequence"] = bool(np.allclose(r["log"]["z"], expected, rtol=1e-12, atol=1e-12))
    hover=dataclasses.replace(p,drag_coefficient=0.0,detection_latency_s=0,motor_start_latency_s=0)
    h=KERNEL.simulate(hover,0.0,0.0,dt=0.0005,t_max=0.1)
    checks["zero_offset_hover_equilibrium"] = bool(np.max(abs(h["log"]["z"])) < 1e-12 and np.max(h["log"]["omega_mag"]) < 1e-12)
    moment=np.array([1e-4,2e-4,-1e-4])
    response=KERNEL.simulate(hover,0.0,0.0,dt=.0005,t_max=.0015,
                            imperfections=KERNEL.Imperfections(torque_bias_n_m=tuple(moment)))
    expected_first_rate=np.linalg.norm(np.linalg.solve(hover.inertia,moment))*.0005
    checks["full_tensor_first_step_constant_moment"] = bool(np.isclose(response['log']['omega_mag'][1],expected_first_rate,rtol=1e-12,atol=1e-12))
    oldp=legacy.with_mixer(legacy.nominal_params(),arm_m=0.06)
    newp=KERNEL.with_mixer(KERNEL.nominal_params(),arm_m=0.06)
    a=legacy.simulate(oldp,2.0,math.radians(60),dt=.0005,t_max=.2)
    b=KERNEL.simulate(newp,2.0,math.radians(60),dt=.0005,t_max=.2)
    checks["legacy_diagonal_trajectory_preserved"] = bool(all(np.allclose(a["log"][key],b["log"][key],rtol=1e-11,atol=1e-11) for key in a["log"]))
    if not all(checks.values()):
        dump("analytical_checks.json",checks)
        raise ValueError("Analytical check failed; stop before pilot")
    dump("analytical_checks.json",checks)
    return checks


def prepare():
    ROOT.mkdir(exist_ok=True, parents=True)
    ms=models(); rows=cohort()
    dump("model_comparison.json", ms)
    dump("frozen_cohort.json", {"seed":SEED,"rates_and_n":RATES,"rows":rows})
    paths=[REPO/'Analysis/sim_release_recovery.py',REPO/'Analysis/monte_carlo_recovery.py',REPO/'Analysis/rigid_body.py',REPO/'Data/monte_carlo_results.json',ROOT/'r1_recovery_runner.py',ROOT/'sim_release_recovery_tensor.py']
    for name in ('Variant_C','Cheapest_H7'):
        paths.extend([REPO/'cad/aircraft_r1'/name/'physical_model.json',REPO/'cad/aircraft_r1'/name/'BOM.csv',REPO/'cad/aircraft_r1'/name/'SolidWorks/native_check.txt'])
    dump("source_manifest.json",[{"path":str(p),"sha256":sha(p)} for p in paths])
    return ms,rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');parser.add_argument('--numerical-check',action='store_true');parser.add_argument('--campaign',action='store_true');args=parser.parse_args()
    ms,rows=prepare()
    if args.pilot:
        checks=analytic_checks(ms['Variant_C'])
        row=next(x for x in rows if x['rate_rad_s']==2.0)
        results={name:one_run(model,row) for name,model in ms.items()}
        dump('pilot_results.json',{'scope':'Three deterministic pilot cases only; no success-rate estimate','checks':checks,'cases':results,'source_unchanged':sha(REPO/'Analysis/sim_release_recovery.py')==json.loads((ROOT/'source_manifest.json').read_text())[0]['sha256']})
        print(json.dumps(results,indent=2))
    if args.numerical_check:
        allocation={
            'approved_by_parent':'2026-11-13, before these numerical outcomes',
            'case_id':75,'rate_rad_s':2.0,'dt_s':[.001,.0005,.00025],
            'same_legacy_success_classification':True,
            'final_step_max_descent_absolute_change_limit_m':.01,
            'basis':'.01m is 0.33% of the3m height budget allocated to this selected time-step check; no global error bound or stochastic-population convergence claim',
            'measurement_noise':'Original pilot imperfections and per-step noise convention retained; changing dt changes the physical noise sampling interpretation, explicitly a limitation.',
            'stop':'Stop on first failed analytical,finite-output,classification or final-increment check. No limits or gains retuned.'}
        dump('numerical_acceptance_frozen.json',allocation)
        analytic_checks(ms['Variant_C'])
        rvec=np.array([.002,-.003,0.0]); force=np.array([0.,0.,2.0])
        expected=np.array([-.006,-.004,0.0])
        implementation=np.array([rvec[1]*force[2],-rvec[0]*force[2],0.0])
        signcheck={'r_thrust_line_minus_CG_m':rvec.tolist(),'force_N':force.tolist(),'hand_expected_moment_Nm':expected.tolist(),'source_expression_moment_Nm':implementation.tolist(),'pass':bool(np.array_equal(implementation,expected) and np.array_equal(np.cross(rvec,force),expected)),'R1_mapping':'r_thrust_line_minus_CG_xy = -physical_model.cg_mm[:2]/1000 + uncertainty_draw'}
        dump('cg_moment_sign_check.json',signcheck)
        if not signcheck['pass']:raise ValueError('CG moment sign check failed')
        row=next(x for x in rows if x['case_id']==75)
        output={'allocation':allocation,'cg_sign':signcheck,'models':{}}
        for name,model in ms.items():
            runs=[one_run(model,row,dt) for dt in allocation['dt_s']]
            same=len({r['success'] for r in runs})==1
            delta=abs(runs[-1]['max_descent_m']-runs[-2]['max_descent_m'])
            item={'runs':runs,'same_classification':same,'final_step_max_descent_change_m':delta,'limit_m':.01,'margin_m':.01-delta,'pass':same and delta<=.01}
            output['models'][name]=item
            dump('numerical_check.json',output)
            print(json.dumps({name:{k:v for k,v in item.items() if k!='runs'}}),flush=True)
            if not item['pass']:raise ValueError('Numerical check failed:'+name)
        output['status']='ALL_THREE_PLANTS_PASS_SELECTED_TIME_STEP_CHECK'
        dump('numerical_check.json',output)
    if args.campaign:
        # Parent review required before invoking this option. This is a synthetic
        # design sensitivity study; do not feed it to measured_authority_gate.
        if json.loads((ROOT/'numerical_check.json').read_text()).get('status')!='ALL_THREE_PLANTS_PASS_SELECTED_TIME_STEP_CHECK':
            raise ValueError('Numerical check must pass before the approved campaign')
        out={'scope':'Unbuilt R1 catalog/CAD sensitivity; not measured authority qualification','models':{}}
        for name,model in ms.items():
            runs=[]
            for row in rows:
                result=one_run(model,row);runs.append(result)
                dump('campaign_'+name+'.json',{'model':model,'runs':runs})
            out['models'][name]={'successes':sum(r['success'] for r in runs),'n':len(runs),
                'one_sided_95pct_binomial_lower':mc.clopper_pearson_lower(sum(r['success'] for r in runs),len(runs)),
                'crashes':sum(r['crashed'] for r in runs),
                'terminal_stabilized':sum(r['final_low_tilt'] and r['final_low_rate'] and r['final_low_vertical_speed'] and not r['crashed'] for r in runs),
                'by_rate':{str(rate):{'successes':sum(r['success'] for r in runs if r['initial_rate_rad_s']==rate),'n':n} for rate,n in RATES},
                'max_descent_all_m':max(r['max_descent_m'] for r in runs)}
            print(json.dumps({name:out['models'][name]}),flush=True)
        dump('campaign_summary.json',out)


if __name__=='__main__': main()
