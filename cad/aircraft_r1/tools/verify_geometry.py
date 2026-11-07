import json,math
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent.parent
for kind,dia,rotor_d,motor_h in [('Cheapest_H7',120.6,55.88,10.),('Variant_C',128.9,65.,9.1)]:
 d=ROOT/kind;files=json.loads((d/'part_files.json').read_text());parts={Path(f).stem:cq.importers.importStep(str(d/f)).val() for f in files}
 invalid=[n for n,s in parts.items() if not s.isValid() or s.Volume()<=0]
 sweep_clashes=[]
 for i in range(4):
  a=math.radians(45+90*i);r=dia/2
  sweep=cq.Workplane('XY').workplane(offset=motor_h+1.2).center(r*math.cos(a),r*math.sin(a)).circle(rotor_d/2).circle(2.75).extrude(2).val()
  sb=sweep.BoundingBox()
  for n,s in parts.items():
   if n in [f'Propeller_{i+1}',f'Motor_{i+1}']:continue
   b=s.BoundingBox()
   if any(getattr(sb,k+'max')<getattr(b,k+'min') or getattr(b,k+'max')<getattr(sb,k+'min') for k in 'xyz'):continue
   vol=sweep.intersect(s).Volume()
   if vol>.05:sweep_clashes.append(dict(rotor=i+1,part=n,overlap_mm3=round(vol,3)))
 p=json.loads((d/'physical_model.json').read_text());model=json.loads((d/'sitl_model.json').read_text())
 assert abs(model['mass']*1000-p['total_mass_g'])<.006 # displayed CAD total rounded to 0.01 g
 assert model['battCapacityAh']==p['pack']['capacity_ah']
 assert model['maxVoltage']==p['pack']['max_voltage_v']
 report=dict(valid_parts=len(parts)-len(invalid),part_count=len(parts),invalid_parts=invalid,
    rotor_sweep_clashes=sweep_clashes,rotor_sweep_scope='Full nominal blade radius, blade thickness plus 0.5 mm each axial side; purchased geometry is enveloped',
    mass_and_battery_model_match=True,passed=not invalid and not sweep_clashes)
 (d/'geometry_verification.json').write_text(json.dumps(report,indent=2));print(kind,json.dumps(report),flush=True)
