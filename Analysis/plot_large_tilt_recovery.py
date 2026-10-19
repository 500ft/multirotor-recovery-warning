"""Plot the executed large-tilt comparison; no simulation or tuning."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from Analysis.figure_style import style, save

ROOT = Path(__file__).resolve().parents[1]

def main():
    traces=json.loads((ROOT/'Data/large-tilt-recovery/plot-traces.json').read_text())
    cases=[('nominal',142.2387560927618,4.),('worst',60.,4.),('worst',180.,0.)]
    labels={'legacy':'Original controller','tilt_angle':'Angle-error controller'}
    with style():
        fig, axes=plt.subplots(2,3,figsize=(10,5.7),sharex=True)
        for col,(tier,tilt,rate) in enumerate(cases):
            for controller,color,ls in [('legacy','#7C8597','--'),('tilt_angle','#2C49A6','-')]:
                row=next(x for x in traces if x['tier']==tier and x['initial_tilt_deg']==tilt
                         and x['rate_rad_s']==rate and x['controller']==controller)
                axes[0,col].plot(row['t_s'],row['tilt_deg'],color=color,ls=ls,lw=1.5,label=labels[controller])
                axes[1,col].plot(row['t_s'],row['descent_m'],color=color,ls=ls,lw=1.5)
            axes[0,col].set_title(f"{'Pessimistic' if tier=='worst' else 'Nominal'}: {tilt:.1f}° / {rate:g} rad/s")
            axes[0,col].set_ylim(0,185)
            axes[1,col].axhline(3,color='#BE933A',ls=':',lw=1)
            axes[1,col].set_ylim(0,20 if tier=='worst' else 5)
            axes[1,col].invert_yaxis()
            axes[1,col].set_xlabel('Time since release (s)')
            for ax in axes[:,col]:
                ax.set_xlim(0,12);ax.grid(axis='y',alpha=.15)
        axes[0,0].set_ylabel('Tilt (degrees)')
        axes[1,0].set_ylabel('Descent below release (m)')
        fig.legend(*axes[0,0].get_legend_handles_labels(),loc='upper center',ncol=2,bbox_to_anchor=(.5,1.01))
        fig.tight_layout(rect=(0,0,1,.94))
        save(fig,ROOT/'Figures/large-tilt-recovery',formats=('png','svg'))
        plt.close(fig)
    (ROOT/'Figures/large-tilt-recovery.caption.md').write_text(
        'Simulation of the historical estimated aircraft. Columns compare matched '
        'starting states. Solid blue is the angle-error controller; dashed gray is '
        'the original. Dotted gold marks the old ground clearance. The inverted '
        'original-controller descent leaves the plotted range. Parameters and '
        'actuation limits are unchanged. Independent thrust/torque clipping remains '
        'an optimistic plant assumption. Data: Data/large-tilt-recovery/results.json '
        'and plot-traces.json.\n')

if __name__=='__main__':main()
