"""Independent hand counterexample for simultaneous scalar-axis torque clips."""
from pathlib import Path
import json,sys
import numpy as np

ROOT=Path(__file__).parent
REPO=Path(r'C:\Users\Admin\Documents\ChatGPT\Research\multirotor-recovery-warning')
sys.dont_write_bytecode=True
sys.path.insert(0,str(REPO))
from Analysis.sim_release_recovery import mixer_torque_limit,nominal_params
from Analysis.failure_allocation import healthy_wrench_map

p=nominal_params();arm=.06;T=p.max_thrust_n/2
limit=mixer_torque_limit(T,p.max_thrust_n,arm)
B=healthy_wrench_map(arm,p.max_thrust_n,.004)
w=np.array([T,limit,limit,0.])
f=np.linalg.solve(B,w)
cap=p.max_thrust_n/4
a=arm/np.sqrt(2)
out={'question':'Are simultaneous independently clipped maximum roll/pitch torques feasible for four bounded rotors?',
     'collective_N':T,'per_rotor_cap_N':cap,'independent_scalar_RP_limit_Nm':limit,
     'requested_wrench_T_tx_ty_tz':w.tolist(),'zero_yaw_inverse_rotor_forces_N':f.tolist(),
     'per_rotor_box_feasible':bool(np.all(f>=0)&np.all(f<=cap)),
     'yaw_free_hand_reference':{'equation':'tau_x+tau_y=2*a*(f2-f4); for0<=fi<=cap,abs(sum)<=2*a*cap',
                                'requested_sum_Nm':2*limit,'maximum_possible_sum_Nm':2*a*cap},
     'conclusion':'The independent roll/pitch box admits physically unrealizable simultaneous wrenches. This is a structural idealization of the healthy scalar-mixer model; it limits physical interpretation of historical and unchanged-controller R1 sensitivity successes.',
     'no_campaign_change':'The approved frozen sensitivity campaign is not modified by this check.'}
(ROOT/'mixer_feasibility_counterexample.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
