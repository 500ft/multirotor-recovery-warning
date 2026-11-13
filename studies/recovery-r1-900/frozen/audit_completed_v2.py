"""Run only after all900 cases finish. Independent raw-output/manifest audit."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
FOLDER=ROOT/'bounded_v2_campaign_01'
summary=json.loads((FOLDER/'summary.json').read_text(encoding='utf-8'))
assert summary['status']=='ALL900_FINITE_BOUNDED_CASES_COMPLETE'
frozen=json.loads((FOLDER/'FROZEN_BEFORE_OUTCOMES.json').read_text(encoding='utf-8'))
for item in frozen['files']:
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
raw={}
def finite_recursive(v):
    if isinstance(v,dict):return all(finite_recursive(x) for x in v.values())
    if isinstance(v,list):return all(finite_recursive(x) for x in v)
    if isinstance(v,(int,float)):return bool(np.isfinite(v))
    return True

for name in frozen['plant_order']:
    data=json.loads((FOLDER/(name+'.json')).read_text(encoding='utf-8'))
    rows=data['runs'];raw[name]=rows
    assert len(rows)==300 and [r['case_id'] for r in rows]==list(range(300)),name
    assert finite_recursive(data),name
    for i,r in enumerate(rows):
        assert r['dt_s']==.0005 and r['available_height_m']==3,name
        assert r['initial_rate_rad_s']==(1. if i<75 else 2. if i<225 else 3.),name
        d=r['allocator']
        assert d['calls']>0 and d['min_force_n']>=-1e-12,name
        assert d['max_force_fraction']<=1+1e-12 and d['max_collective_error_n']<=1e-12,name
        assert 0<=d['min_lambda']<=1 and 0<=d['saturated_calls']<=d['calls'],name
    s=summary['models'][name]
    assert s['n']==300 and s['legacy_episode_recovery']==sum(r['success'] for r in rows),name
    assert s['terminal_stabilized']==sum(r['terminal_stabilized'] for r in rows),name
    assert s['crashes']==sum(r['crashed'] for r in rows),name
    assert s['max_descent_m']==max(r['max_descent_m'] for r in rows),name

audit={'status':'ALL900_RAW_CASES_AND_FROZEN_HASHES_AUDITED',
 'case_counts':{n:len(r) for n,r in raw.items()},
 'note':'Per-step motor and wrench checks enforced by frozen allocator; moment error maximum was not separately serialized.',
 'scope':'Synthetic computational sensitivity only; not measured authority or flight validation'}
(FOLDER/'INDEPENDENT_OUTPUT_AUDIT.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'text.color':'black',
  'axes.labelcolor':'black','xtick.color':'black','ytick.color':'black','svg.fonttype':'none'})
fig,axes=plt.subplots(1,3,figsize=(11,3.7),constrained_layout=True)
names=list(raw);labels=['Historical','R1 C','R1 H7'];x=np.arange(3)
axes[0].bar(x-.18,[summary['models'][n]['legacy_episode_recovery'] for n in names],.36,color='.35',label='Recovery episode')
axes[0].bar(x+.18,[summary['models'][n]['terminal_stabilized'] for n in names],.36,color='white',edgecolor='black',hatch='//',label='Terminal stabilization')
axes[0].set(xticks=x,xticklabels=labels,ylim=(0,330),ylabel='Cases / 300',title='(a) Separate outcome definitions')
axes[0].legend(fontsize=8,loc='lower left')
styles=[('-', 'black'),('--','.35'),(':','.55')]
for (name,rows),label,(ls,col) in zip(raw.items(),labels,styles):
    desc=np.sort([r['max_descent_m'] for r in rows])
    axes[1].step(desc,np.arange(1,301)/300,where='post',ls=ls,color=col,label=label)
    frac=np.sort([r['allocator']['saturated_calls']/r['allocator']['calls'] for r in rows])
    axes[2].step(frac*100,np.arange(1,301)/300,where='post',ls=ls,color=col,label=label)
axes[1].set(xlabel='Maximum descent (m)',ylabel='Cumulative case fraction',title='(b) All 300 cases per plant')
axes[1].axvline(3,color='.5',lw=1);axes[1].legend(fontsize=8,loc='lower right')
axes[2].set(xlabel='Time steps with torque scaling (%)',ylabel='Cumulative case fraction',title='(c) Bounded allocator activity')
for ax in axes:ax.grid(axis='y',color='.9',lw=.5)
fig.savefig(FOLDER/'bounded_recovery_comparison.png',dpi=220)
fig.savefig(FOLDER/'bounded_recovery_comparison.svg')
(FOLDER/'bounded_recovery_comparison.caption.txt').write_text(
 'Frozen paired300case computational comparison per plant, with the same controller '
 'and bounded four-rotor allocation. (a) Episode recovery and terminal stabilization '
 'are distinct outcomes. (b) Maximum descent includes every case without a success-only filter. (c) Fraction of '
 'active-control integration steps requiring torque scaling. Plant inputs are CAD/'
 'catalog estimates and assumed dispersions; no flight or measured-authority '
 'qualification follows from these results.',encoding='utf-8')

lines=[r'\begin{table*}[t]',r'\caption{Frozen paired computational sensitivity results; 300 synthetic cases per plant.}',
 r'\label{tab:bounded-recovery-results}',r'\centering',r'\begin{tabular}{lrrrrr}',r'\hline',
 r'Plant & Cases & Episodes & Terminal & Crashes & Max. descent (m) \\',r'\hline']
for name,label in zip(names,labels):
    s=summary['models'][name]
    lines.append(f"{label} & {s['n']} & {s['legacy_episode_recovery']} & {s['terminal_stabilized']} & {s['crashes']} & {s['max_descent_m']:.3f} " + r'\\')
lines += [r'\hline',r'\end{tabular}',r'\end{table*}',
 'The table reports a synthetic sensitivity cohort, not a passed measured-authority gate. '
 'Episode recovery need not imply terminal stability. The sampled plant uncertainties '
 'and noise are assumed rather than identified from hardware.']
(FOLDER/'audited_results_table.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(audit,indent=2))
print(json.dumps(summary,indent=2))
