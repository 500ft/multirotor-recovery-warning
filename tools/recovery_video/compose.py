"""Composite the physical replay and synchronized plots; add no explanatory text."""
from pathlib import Path
import json,sys,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'.video-build';SOURCE=ROOT/'Data/recovery-video'
sys.path.insert(0,str(ROOT))
from Analysis.recovery_video import CASES
D=json.loads((HERE/'display.json').read_text());CFG=json.loads((SOURCE/'settings.json').read_text());FPS=D['fps'];W,H=1440,1680
BLUE='#2C49A6';INK='#19233A';MUTED='#657085';GRID='#E5E9EF'
plt.rcParams.update({'font.family':'Helvetica Neue','text.color':INK,'axes.labelcolor':MUTED,'xtick.color':MUTED,'ytick.color':MUTED,'axes.spines.top':False,'axes.spines.right':False})
font_path=font_manager.findfont('Helvetica Neue');mono_path=font_manager.findfont('Menlo')
font=lambda n:ImageFont.truetype(font_path,n)
mono=lambda n:ImageFont.truetype(mono_path,n)
fig=plt.figure(figsize=(12,14),dpi=120,facecolor='white')
rows=[];artists=[]
for key,top in zip(D['keys'],[100,620,1140]):
 a=np.load(SOURCE/f'{key}.npz');parts=[]
 for metric,x,yl,ticks,title in [('tilt',885,(0,90),[0,45,90],'Tilt (°)'),('height',1195,(0,3.25),[0,1,2,3],'Height (m)')]:
  ax=fig.add_axes([x/W,(H-top-435)/H,205/W,330/H]);ax.set_xlim(0,CFG['duration_s']);ax.set_ylim(*yl);ax.set_xticks([0,2,4,6]);ax.set_yticks(ticks)
  ax.tick_params(labelsize=11,length=0,pad=7);ax.spines[['left','bottom']].set_color('#BAC2CC');ax.yaxis.grid(True,color=GRID,lw=.7)
  ax.set_title(title,loc='left',fontsize=14,pad=14)
  if key=='worst':ax.set_xlabel('Time (s)',fontsize=11,labelpad=10)
  if metric=='tilt':
   ax.axhline(5,color='#A7AFBB',ls=(0,(3,3)),lw=.7)
   ax.text(5.8,7,'5°',fontsize=8,color=MUTED,ha='right')
  else:ax.axhline(3,color='#A7AFBB',ls=(0,(3,3)),lw=.7)
  line,=ax.plot([],[],color=BLUE,lw=2.3,animated=True);dot,=ax.plot([],[],'o',color=BLUE,ms=5,animated=True)
  parts.append((line,dot,metric));artists.extend([line,dot])
 rows.append((key,top,a,parts))
fig.canvas.draw();bg=fig.canvas.copy_from_bbox(fig.bbox)
preview='--preview' in sys.argv
manifest=json.loads((HERE/('preview_manifest.json' if preview else 'manifest.json')).read_text())
# Keep all three cases on one clock; sample the startup at real speed.
startup_end=round((CFG['initial_hold_s']+CFG.get('realtime_startup_until_s',0)/CFG['playback_speed'])*FPS)
hold_frames=round(CFG['initial_hold_s']*FPS)
startup_stride=round(1/CFG['playback_speed'])
if not preview:
 manifest=[e for e in manifest if e['frame']<hold_frames or e['frame']>=startup_end or (e['frame']-hold_frames)%startup_stride==0]
proc=None
if not preview:
 proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-threads','4','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(ROOT/'Figures/recovery-physical-replay.mp4')],stdin=subprocess.PIPE)
for entry in manifest:
 f=entry['frame'];s=D['timeline'][f];fig.canvas.restore_region(bg)
 for (key,top,a,parts),j in zip(rows,s['indices']):
  ix=np.unique(np.r_[np.arange(0,j+1,16),j]).astype(int)
  for line,dot,metric in parts:
   yy=np.degrees(a['tilt']) if metric=='tilt' else CASES[key]().available_height_m+a['pos'][:,2]
   line.set_data(a['t'][ix],yy[ix]);dot.set_data([a['t'][j]],[yy[j]])
 for artist in artists:artist.axes.draw_artist(artist)
 im=Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert('RGB');draw=ImageDraw.Draw(im)
 draw.text((1400,22),f'{s["t"]:0.2f} s',font=mono(30),fill=INK,anchor='ra')
 speed=1.0 if f<startup_end else CFG['playback_speed']
 draw.text((1400,62),f"{speed:g}× speed",font=font(21),fill=MUTED,anchor='ra')
 for c,((key,top,a,parts),j,render) in enumerate(zip(rows,s['indices'],entry['files'])):
  draw.text((40,top),['Optimistic','Nominal','Pessimistic'][c],font=font(30),fill=INK)
  drop=max(0.0,float(-np.min(a['pos'][:j+1,2])));draw.text((1400,top+3),f'Drop  {drop:.2f} m',font=mono(25),fill=INK,anchor='ra')
  stage=Image.open(HERE/'frames'/render).convert('RGB')
  im.paste(stage,(40,top+47))
  if c<2:draw.line((40,top+492,1400,top+492),fill=GRID,width=1)
 if preview or f in [0,60,108,144,240,420,588]:im.save(HERE/f'composite-{f:04}.png')
 if proc:proc.stdin.write(np.asarray(im).tobytes())
if proc:
 proc.stdin.close()
 if proc.wait()!=0:raise RuntimeError('Video encoding failed')
print('Preview complete' if preview else str(ROOT/'Figures/recovery-physical-replay.mp4'))
