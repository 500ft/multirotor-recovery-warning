"""High-resolution views from the same retained component STEP files."""
import inspect,json
from pathlib import Path
import cadquery as cq
import build_drone_release as B
H=B.H
exec(inspect.getsource(H.render).replace("dpi=140","dpi=280").replace("0.4, 0.5","0.15, 0.15"),H.__dict__)
for kind in ["Cheapest_H7","Variant_C"]:
 d=B.OUT/kind
 items=[];exp=[]
 for name in json.loads((d/"part_files.json").read_text()):
  shape=cq.importers.importStep(str(d/name));n=Path(name).stem.lower();color=(.35,.38,.42);dz=10
  if "guard" in n:color=(.93,.42,.1);dz=45
  if "cradle" in n:color=(.93,.42,.1);dz=74
  if "propeller" in n:color=(.10,.65,.48);dz=32
  if "motor" in n:color=(.60,.63,.68);dz=20
  if "frame" in n or "landing" in n:color=(.18,.20,.24);dz=0 if "frame" in n else -25
  if "battery_pack" in n or "strap" in n:color=(.22,.24,.29);dz=95
  if "matek" in n or "micoair" in n or "aikon" in n:color=(.12,.42,.6);dz=12
  if "xt30" in n:color=(.95,.78,.10);dz=95
  if "mtf01" in n:color=(.08,.09,.1);dz=-18
  if "upper_standoff" in n or "fc_cradle" in n:dz=60
  items.append((shape,color));exp.append((shape.translate((0,0,dz)),color))
 title="Cheapest H7" if kind=="Cheapest_H7" else "Variant C"
 for file,data,elev,azim in [("assembled",items,26,-52),("top",items,90,-90),("exploded",exp,20,-52)]:
  H.render(data,d/(file+".png"),title+" CAD assembly"+(" - exploded" if file=="exploded" else ""),elev,azim)
 print("Rendered",kind,flush=True)
