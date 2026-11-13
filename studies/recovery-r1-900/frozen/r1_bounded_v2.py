"""Isolated v2 healthy X-quad allocation; preparation/checks/pilot only.

The scalar-box campaign is stopped and unqualified. This kernel preserves the
legacy controller and 75% collective ceiling while realizing every commanded
wrench from four bounded motor forces. No original source/CAD is changed.
"""
from __future__ import annotations

import argparse
import dataclasses
import difflib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import r1_recovery_runner as base

ROOT = Path(__file__).resolve().parent


class BoundedXAllocation:
    """Fixed-collective, direction-preserving full-wrench allocation.

    B rows = (1, y, -x, kappa*spin), spin=(+,-,+,-). The equal-force
    zero-moment trim and the torque increment are obtained from B^{-1}.
    A single lambda scales the requested moment into the rotor box, preserving
    moment direction and collective exactly. Yaw shares authority with roll and
    pitch; kappa is an assumed drag/thrust ratio, not a measured motor constant.
    """

    def __init__(self, rotor_xy_m, nominal_max_thrust_n, yaw_bound_n_m):
        self.xy = np.asarray(rotor_xy_m, float)
        self.kappa = yaw_bound_n_m / (nominal_max_thrust_n / 2)
        self.B = np.vstack([np.ones(4), self.xy[:, 1], -self.xy[:, 0],
                            self.kappa*np.array([1, -1, 1, -1])])
        self.Binv = np.linalg.inv(self.B)
        self.trim_unit = self.Binv[:, 0]
        if np.min(self.trim_unit) < -1e-12:
            raise ValueError('No nonnegative zero-moment collective trim')
        self.calls = 0
        self.saturated_calls = 0
        self.max_force_fraction = 0.0
        self.min_force_n = 0.0
        self.max_collective_error_n = 0.0
        self.min_lambda = 1.0
        self.last = None

    def apply(self, torque_cmd, thrust_cmd, max_thrust_avail_n):
        cap = max_thrust_avail_n / 4
        T = float(np.clip(thrust_cmd, 0, max_thrust_avail_n))
        trim = self.trim_unit * T
        delta = self.Binv[:, 1:] @ np.asarray(torque_cmd, float)
        lam = 1.0
        for f0, df in zip(trim, delta):
            if df > 0:
                lam = min(lam, (cap-f0)/df)
            elif df < 0:
                lam = min(lam, -f0/df)
        lam = max(0., min(1., lam))
        forces = trim + lam*delta
        # Only floating-point boundary cleanup; never hide an infeasible solve.
        if not np.isfinite(forces).all() or forces.min() < -1e-12 or forces.max() > cap+1e-12:
            raise ValueError('Bounded allocation failed')
        forces = np.clip(forces, 0, cap)
        achieved = self.B @ forces
        err = abs(achieved[0]-T)
        if err > 1e-12 or not np.allclose(achieved[1:],lam*np.asarray(torque_cmd),rtol=1e-10,atol=1e-12):
            raise ValueError('Allocation wrench consistency failed')
        self.calls += 1
        self.saturated_calls += int(lam < 1-1e-12)
        self.min_lambda = min(self.min_lambda, lam)
        self.min_force_n = min(self.min_force_n, float(forces.min()))
        self.max_force_fraction = max(self.max_force_fraction, float(forces.max()/cap) if cap else 0.)
        self.max_collective_error_n = max(self.max_collective_error_n, err)
        self.last = dict(forces_n=forces.tolist(),cap_n=cap,requested_T_n=T,
                         requested_torque_n_m=np.asarray(torque_cmd).tolist(),
                         achieved_wrench=achieved.tolist(),lambda_scale=lam)
        return achieved[1:].copy(), float(achieved[0])

    def diagnostics(self):
        return {k:getattr(self,k) for k in ('calls','saturated_calls','min_lambda',
                    'min_force_n','max_force_fraction','max_collective_error_n')}


def kernel():
    source = (ROOT/'sim_release_recovery_tensor.py').read_text(encoding='utf-8')
    old_sig = '             motor_alloc=None,\n'
    new_sig = '             motor_alloc=None,\n             allocator_v2=None,\n'
    old = '''                    tau_rp = mixer_torque_limit(thrust, max_thrust_avail, p.arm_m)
                    torque[:2] = np.clip(torque[:2], -tau_rp, tau_rp)
                    yaw_lim = p.yaw_torque_n_m if p.yaw_torque_n_m is not None else tau_rp
                    torque[2] = np.clip(torque[2], -yaw_lim, yaw_lim)'''
    new = '''                    if allocator_v2 is None:
                        raise ValueError("v2 requires an explicit bounded rotor allocator")
                    torque, thrust = allocator_v2.apply(torque, thrust, max_thrust_avail)'''
    for expected in (old_sig,old):
        if source.count(expected) != 1:
            raise ValueError('Source patch guard failed')
    result = source.replace(old_sig,new_sig).replace(old,new)
    target = ROOT/'sim_release_recovery_bounded_v2.py'
    target.write_text(result,encoding='utf-8')
    (ROOT/'bounded_v2.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),result.splitlines(True),fromfile='tensor_v1',tofile=target.name)),encoding='utf-8')
    spec=importlib.util.spec_from_file_location('bounded_v2_kernel',target)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


KERNEL=kernel()


def rotor_centres(name,model):
    if name == 'historical_actual_code':
        return np.array([[1,1],[-1,1],[-1,-1],[1,-1]])*model['arm_m']/math.sqrt(2)
    data=json.loads(Path(model['physical_model_path']).read_text(encoding='utf-8'))
    motors=sorted((p for p in data['modelled_parts'] if p['name'].startswith('Motor_')),key=lambda p:p['name'])
    return np.array([p['cg_mm'][:2] for p in motors])/1000


def allocation(name,model,p):
    # CAD geometry and assumed kappa are fixed. The cohort's placeholder torque
    # multiplier is drawn-but-unused, retained only for common-cohort traceability.
    return BoundedXAllocation(rotor_centres(name,model),model['max_thrust_n'],.004)


def one_run(name,model,row,dt=.0005):
    p,imp=base.parameters(model,row)
    alloc=allocation(name,model,p)
    t0=time.perf_counter()
    r=KERNEL.simulate(p,row['rate_rad_s'],math.radians(60),imperfections=imp,
                      dt=dt,t_max=6.,allocator_v2=alloc)
    if not all(np.isfinite(v).all() for v in r['log'].values()):
        raise ValueError('Nonfinite trajectory')
    result={k:v for k,v in r.items() if k!='log'}
    result.update(case_id=row['case_id'],dt_s=dt,elapsed_s=time.perf_counter()-t0,
      terminal_stabilized=bool(r['log']['tilt'][-1]<math.radians(5) and
        r['log']['omega_mag'][-1]<.3 and abs(r['log']['vz'][-1])<.2 and not r['crashed']),
      allocator=alloc.diagnostics())
    return result


def checks(ms):
    output={'scope':'Pre-campaign v2 engineering checks; no hardware qualification','checks':{}}
    def accept(name,passed,detail=None):
        output['checks'][name]={'pass':bool(passed),'detail':detail}
        base.dump('bounded_v2_checks.json',output)
        if not passed:raise ValueError('STOP first failed check:'+name)
    # Known ideal X references permit closed-form pure-axis and simultaneous tests.
    arm=.06;Tmax=4.2;a=arm/math.sqrt(2);T=Tmax/2;cap=Tmax/4
    allocator=BoundedXAllocation([[a,a],[-a,a],[-a,-a],[a,-a]],Tmax,.004)
    tau_lim=2*a*cap
    for i in (0,1):
        command=np.zeros(3);command[i]=tau_lim
        tau,achT=allocator.apply(command,T,Tmax)
        accept('pure_axis_'+str(i),np.allclose(tau,command,atol=1e-12) and abs(achT-T)<1e-12,allocator.last)
    tau,achT=allocator.apply([tau_lim,tau_lim,0],T,Tmax)
    accept('simultaneous_RP_realizable',abs(allocator.last['lambda_scale']-.5)<1e-12 and
           np.allclose(tau,[tau_lim/2,tau_lim/2,0],atol=1e-12),allocator.last)
    tau,achT=allocator.apply([10,-20,3],100,Tmax)
    accept('collective_saturation',abs(achT-Tmax)<1e-12 and np.max(abs(tau))<1e-12,allocator.last)
    rng=np.random.default_rng(13012026)
    worst={'rotor_lower_margin_N':float('inf'),'rotor_upper_margin_N':float('inf'),
           'collective_closure_N':0.,'moment_closure_Nm':0.}
    for _ in range(10000):
        maxT=float(rng.uniform(.1,10));command=rng.uniform(-1,1,3);demand=float(rng.uniform(-2,12))
        tau,gotT=allocator.apply(command,demand,maxT)
        state=allocator.last;f=np.array(state['forces_n']);cap=state['cap_n']
        worst['rotor_lower_margin_N']=min(worst['rotor_lower_margin_N'],float(f.min()))
        worst['rotor_upper_margin_N']=min(worst['rotor_upper_margin_N'],float((cap-f).min()))
        worst['collective_closure_N']=max(worst['collective_closure_N'],abs(gotT-np.clip(demand,0,maxT)))
        worst['moment_closure_Nm']=max(worst['moment_closure_Nm'],float(np.max(abs(tau-state['lambda_scale']*command))))
    accept('arbitrary_10000_demands_force_bounds_and_wrench_closure',
       worst['rotor_lower_margin_N']>=0 and worst['rotor_upper_margin_N']>=0 and
       worst['collective_closure_N']<=1e-12 and worst['moment_closure_Nm']<=1e-12,worst)
    nominal_row={'multipliers':dict.fromkeys(('mass_kg','inertia_lateral_kg_m2','max_torque_n_m','max_thrust_n','detection_latency_s','motor_start_latency_s'),1.),'imperfections':dataclasses.asdict(KERNEL.Imperfections())}
    for name,model in ms.items():
        p,_=base.parameters(model,nominal_row)
        hover=dataclasses.replace(p,drag_coefficient=0,detection_latency_s=0,motor_start_latency_s=0)
        alloc=allocation(name,model,hover)
        h=KERNEL.simulate(hover,0.,0.,dt=.0005,t_max=.1,allocator_v2=alloc)
        accept(name+'_hover',np.max(abs(h['log']['z']))<1e-12 and np.max(h['log']['omega_mag'])<1e-12,alloc.diagnostics())
        free=dataclasses.replace(hover,detection_latency_s=10.,motor_start_latency_s=10.)
        f=KERNEL.simulate(free,0.,0.,dt=.0005,t_max=.1,allocator_v2=allocation(name,model,free))
        k=np.arange(len(f['log']['z']));expected=-9.81*.0005**2*k*(k+1)/2
        accept(name+'_freefall',np.allclose(f['log']['z'],expected,rtol=1e-12,atol=1e-12))
        moment=np.array([1e-4,2e-4,-1e-4])
        r=KERNEL.simulate(hover,0.,0.,dt=.0005,t_max=.0015,
             allocator_v2=allocation(name,model,hover),imperfections=KERNEL.Imperfections(torque_bias_n_m=tuple(moment)))
        accept(name+'_full_Euler_first_step',np.isclose(r['log']['omega_mag'][1],np.linalg.norm(np.linalg.solve(p.inertia,moment))*.0005,rtol=1e-12,atol=1e-12))
        cg=np.array([.002,-.003,0]);force=np.array([0,0,2.])
        accept(name+'_CG_sign',np.array_equal(np.cross(cg,force),[-.006,-.004,0.]))
    output['status']='ALL_ANALYTICAL_ALLOCATION_CHECKS_PASS'
    base.dump('bounded_v2_checks.json',output)
    return output


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--checks',action='store_true');parser.add_argument('--pilot',action='store_true');parser.add_argument('--campaign',action='store_true');args=parser.parse_args()
    ms=base.models();rows=base.cohort()
    if args.checks:print(json.dumps(checks(ms),indent=2))
    if args.pilot:
        checks(ms)
        allocation_limits={'frozen_before_v2_outcomes':True,'case_id':75,'dt_s':[.001,.0005,.00025],
            'same_legacy_episode_success':True,'last_step_max_descent_limit_m':.01,
            'stop_first_failure':True,'no_gain_or_limit_retuning':True}
        base.dump('bounded_v2_acceptance_frozen.json',allocation_limits)
        out={'scope':'One selected case per plant at three time steps; no population rate','allocation':allocation_limits,'models':{}}
        for name,model in ms.items():
            runs=[one_run(name,model,rows[75],dt) for dt in allocation_limits['dt_s']]
            delta=abs(runs[-1]['max_descent_m']-runs[-2]['max_descent_m'])
            passed=len({r['success'] for r in runs})==1 and delta<=.01
            out['models'][name]={'runs':runs,'last_step_max_descent_change_m':delta,'limit_m':.01,'margin_m':.01-delta,'pass':passed}
            base.dump('bounded_v2_pilot.json',out)
            print(json.dumps({name:out['models'][name]}),flush=True)
            if not passed:raise ValueError('STOP first time-step check failure:'+name)
        out['status']='READY_FOR_PARENT_REVIEW_NOT_CAMPAIGN_AUTHORIZATION'
        base.dump('bounded_v2_pilot.json',out)
    if args.campaign:
        # Parent explicitly approved one serial paired campaign after reviewing v2.
        pilot=json.loads((ROOT/'bounded_v2_pilot.json').read_text(encoding='utf-8'))
        if pilot.get('status')!='READY_FOR_PARENT_REVIEW_NOT_CAMPAIGN_AUTHORIZATION':
            raise ValueError('v2 pilot checks required')
        folder=ROOT/'bounded_v2_campaign_01'
        if folder.exists():raise ValueError('Campaign namespace exists; refusing overwrite or unreviewed retry')
        folder.mkdir()
        def save(name,value):
            temp=folder/(name+'.tmp')
            temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
            temp.replace(folder/name)
        cohortfile=json.loads((ROOT/'frozen_cohort.json').read_text(encoding='utf-8'))
        if cohortfile['rows']!=json.loads(json.dumps(rows)):raise ValueError('Frozen cohort mismatch')
        files=[Path(__file__),ROOT/'sim_release_recovery_bounded_v2.py',
           ROOT/'sim_release_recovery_tensor.py',ROOT/'r1_recovery_runner.py',
           ROOT/'frozen_cohort.json',ROOT/'bounded_v2_pilot.json',
           ROOT/'BOUNDED_V2_PROTOCOL.txt']
        files += [base.REPO/'Analysis'/n for n in ('sim_release_recovery.py','monte_carlo_recovery.py','rigid_body.py')]
        files += [Path(m['physical_model_path']) for m in ms.values() if 'physical_model_path' in m]
        frozen={'parent_approval':'2026-11-13 one serial paired900case v2 campaign',
           'scope':'Unbuilt CAD/catalog computational sensitivity; no measured authority or warning qualification',
           'dt_s':.0005,'n_each':300,'plant_order':list(ms),'models':ms,
           'force_bounds':'all0<=fi<=availableTmax/4 eachstep',
           'wrench_closure_absolute_limit':1e-12,'finite_outputs_required':True,
           'stop_first_numerical_failure':True,'fixed_actual_CAD_rotor_xy':True,
           'placeholder_torque_draw_unused':True,
           'files':[{'path':str(f),'sha256':base.sha(f)} for f in files]}
        save('FROZEN_BEFORE_OUTCOMES.json',frozen)
        allruns={};start=time.perf_counter()
        try:
            for name,model in ms.items():
                runs=[]
                for row in rows:
                    for record in frozen['files']:
                        # Verify tiny driver/input files before every episode.
                        if base.sha(record['path'])!=record['sha256']:
                            raise ValueError('Frozen file changed:'+record['path'])
                    result=one_run(name,model,row);runs.append(result)
                    save(name+'.json',{'model':model,'runs':runs})
                    progress={'status':'RUNNING','current_plant':name,'completed_current':len(runs),
                        'completed_total':sum(len(z) for z in allruns.values())+len(runs),
                        'elapsed_s':time.perf_counter()-start,'last_case_id':row['case_id']}
                    save('progress.json',progress)
                    if len(runs)%25==0:print(json.dumps(progress),flush=True)
                allruns[name]=runs
            summary={'scope':frozen['scope'],'status':'ALL900_FINITE_BOUNDED_CASES_COMPLETE','models':{},'paired_comparisons':{}}
            for name,runs in allruns.items():
                n=len(runs);success=sum(r['success'] for r in runs)
                summary['models'][name]={'n':n,'legacy_episode_recovery':success,
                 'one_sided_95pct_binomial_lower':base.mc.clopper_pearson_lower(success,n),
                 'terminal_stabilized':sum(r['terminal_stabilized'] for r in runs),
                 'crashes':sum(r['crashed'] for r in runs),
                 'max_descent_m':max(r['max_descent_m'] for r in runs),
                 'min_allocation_lambda':min(r['allocator']['min_lambda'] for r in runs),
                 'max_rotor_fraction':max(r['allocator']['max_force_fraction'] for r in runs),
                 'max_collective_closure_N':max(r['allocator']['max_collective_error_n'] for r in runs),
                 'by_rate':{str(rate):{'n':nrate,
                    'episode_recovery':sum(r['success'] for r in runs if r['initial_rate_rad_s']==rate),
                    'terminal_stabilized':sum(r['terminal_stabilized'] for r in runs if r['initial_rate_rad_s']==rate),
                    'crashes':sum(r['crashed'] for r in runs if r['initial_rate_rad_s']==rate)} for rate,nrate in base.RATES}}
            # Paired empirical bootstrap, same case resamples for both layouts.
            # These are uncertainty intervals of this synthetic cohort distribution.
            rng=np.random.default_rng(20261113)
            ix=rng.integers(0,len(rows),size=(10000,len(rows)))
            hist=allruns['historical_actual_code']
            for name in ('Variant_C','Cheapest_H7'):
                current=allruns[name];out={}
                for key in ('success','terminal_stabilized','max_descent_m'):
                    delta=np.array([float(a[key])-float(b[key]) for a,b in zip(current,hist)])
                    interval=np.quantile(delta[ix].mean(axis=1),[.025,.975])
                    out[key]={'mean_paired_difference':float(delta.mean()),
                      'empirical_paired_bootstrap_95pct_interval':interval.tolist()}
                summary['paired_comparisons'][name+'_minus_historical']=out
            save('summary.json',summary)
            save('progress.json',{'status':summary['status'],'completed_total':900,'elapsed_s':time.perf_counter()-start})
            print(json.dumps(summary,indent=2),flush=True)
        except BaseException as exc:
            save('STOP_STATUS.json',{'status':'STOPPED_PRESERVE_PARTIAL','exception':repr(exc),
              'elapsed_s':time.perf_counter()-start,'policy':'No automatic retry or gain/limit change'})
            raise


if __name__=='__main__':main()
