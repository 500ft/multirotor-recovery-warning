"""Read-only kernel check with nonzero angular velocity and full CAD tensor."""
import importlib.util
import json
import sys
import types
import hashlib
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
source_path=ROOT/'sim_release_recovery_bounded_v2.py'
source=source_path.read_text(encoding='utf-8')
old='("t", "tilt", "omega_mag", "z", "vz", "thrust")'
new='("t", "tilt", "omega_mag", "z", "vz", "thrust", "omega_x", "omega_y", "omega_z")'
assignment='log["thrust"][k] = thrust'
instrumented=source.replace(old,new).replace(assignment,assignment+'\n        log["omega_x"][k], log["omega_y"][k], log["omega_z"][k] = omega')
assert source.count(old)==1 and source.count(assignment)==1
kernel=types.ModuleType('bounded_readonly_check');sys.modules[kernel.__name__]=kernel
exec(compile(instrumented,str(source_path)+' [in-memory vector logging only]','exec'),kernel.__dict__)
models=json.loads((ROOT/'model_comparison.json').read_text(encoding='utf-8'))
out={}
for name,model in models.items():
    I=np.array(model['inertia_tensor'])
    class TensorParams(kernel.DroneParams):
        @property
        def inertia(self):return I
    p=TensorParams(mass_kg=model['mass_kg'],inertia_lateral_kg_m2=I[0,0],
        detection_latency_s=10.,motor_start_latency_s=10.,drag_coefficient=0.)
    axis=np.array([.3,-.5,.7]);axis/=np.linalg.norm(axis);omega=1.7*axis;dt=.0005
    expected=omega+np.linalg.solve(I,-np.cross(omega,I@omega))*dt
    r=kernel.simulate(p,1.7,0.,tumble_axis=axis,dt=dt,t_max=.0015)
    measured=np.array([r['log'][key][1] for key in ('omega_x','omega_y','omega_z')])
    reference=np.linalg.norm(expected)
    passed=bool(np.allclose(measured,expected,rtol=1e-12,atol=1e-12))
    moment=np.array([1e-4,2e-4,-1e-4])
    h=TensorParams(mass_kg=model['mass_kg'],inertia_lateral_kg_m2=I[0,0],
        detection_latency_s=0.,motor_start_latency_s=0.,drag_coefficient=0.)
    response=kernel.simulate(h,0.,0.,dt=dt,t_max=.0015,
        imperfections=kernel.Imperfections(torque_bias_n_m=tuple(moment)))
    moment_measured=np.array([response['log'][key][1] for key in ('omega_x','omega_y','omega_z')])
    moment_expected=np.linalg.solve(I,moment)*dt
    passed=passed and bool(np.allclose(moment_measured,moment_expected,rtol=1e-12,atol=1e-12))
    out[name]={'initial_omega_rad_s':omega.tolist(),'full_Euler_hand_first_step_rad_s':expected.tolist(),
      'actual_next_omega_rad_s':measured.tolist(),'expected_norm_rad_s':float(reference),
      'max_component_error_rad_s':float(np.max(abs(measured-expected))),
      'constant_moment_expected_first_step_rad_s':moment_expected.tolist(),
      'constant_moment_actual_first_step_rad_s':moment_measured.tolist(),
      'constant_moment_max_component_error_rad_s':float(np.max(abs(moment_measured-moment_expected))),
      'instrumentation':'Read frozen kernel; add vector logs only in memory; no source file or dynamics changed',
      'kernel_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'pass':passed}
    (ROOT/'full_euler_nonlinear_check.json').write_text(json.dumps(out,indent=2,allow_nan=False),encoding='utf-8')
    if not passed:raise ValueError('Full Euler nonlinear check failed:'+name)
print(json.dumps(out,indent=2))
