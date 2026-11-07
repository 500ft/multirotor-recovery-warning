"""Generate both aircraft from retained airframe geometry; all dimensions in mm.

Purchased parts are dimensional envelopes. Printed/cut parts are CAD solids.
No physical performance is inferred from geometric validation.
"""
import csv, hashlib, importlib.util, json, math, shutil, sys
from pathlib import Path
import cadquery as cq
import numpy as np

PORTABLE = Path(__file__).with_name("variant_frames.py").exists()
ROOT = Path(__file__).parent.parent if PORTABLE else Path(r"C:\Users\Admin\Desktop\Drone")
OUT = ROOT if PORTABLE else ROOT / "10_Current_Designs"
VPATH = Path(__file__).parent if PORTABLE else ROOT / "01_Airframe_Structure/Variants"
sys.path.insert(0, str(VPATH))
import variant_frames as V
if PORTABLE: V.CATALOG = VPATH / "catalog.json"
spec = importlib.util.spec_from_file_location("cheap_helpers", VPATH / "cheapest_helpers.py" if PORTABLE else ROOT / "01_Airframe_Structure/Cheapest/cheapest_drone.py")
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
DATE = "2026-11-07"
SOURCES = {
    "flow": "https://micoair.com/optical_range_sensor_mtf-01/",
    "mico": "https://store.micoair.com/product/micoair743v2-aio-35a/",
    "matek": "https://www.flyingtech.co.uk/product/matek-h743-mini-20x20-flight-controller/",
    "aikon": "https://reduxair.com/products/aikon-ak32pin-v2-4-in-1-35a-6s",
    "motor_c": "https://rotorgeeks.com/download/GTS%20V2%201202.5-11500.pdf",
    "motor_cheap": "https://betafpv.com/products/1103-brushless-motors-aquila20",
    "pack_c": "https://betafpv.com/products/lava-2s-3s-4s-450mah-75c-battery-2pcs",
    "pack_cheap": "https://newbeedrone.com/a/p/products/cnhl-ministar-650mah-7-4v-2s-70c-lipo-battery-with-xt30-plug",
    "rx": "https://radiomasterrc.com/products/rp1-expresslrs-2-4ghz-nano-receiver",
}

def box(sx, sy, h, x=0, y=0, z=0):
    return cq.Workplane("XY").workplane(offset=z).center(x,y).rect(sx,sy).extrude(h)

def cyl(r,h,x=0,y=0,z=0,inner=0):
    w = cq.Workplane("XY").workplane(offset=z).center(x,y).circle(r)
    if inner: w=w.circle(inner)
    return w.extrude(h)

def board(sx,sy,h,pitch,z):
    b=box(sx,sy,1.6,z=z)
    for x in (-pitch/2,pitch/2):
        for y in (-pitch/2,pitch/2): b=b.cut(cyl(1.6,3.6,x,y,z-1))
    comps=box(sx-8,sy-8,h-1.6,z=z+1.6)
    for x in (-pitch/2,pitch/2):
        for y in (-pitch/2,pitch/2): comps=comps.cut(cyl(3.4,h+1,x,y,z))
    return b.union(comps)

def motor(d,h):
    return cyl(d/2-.5,1.5).union(cyl(d/2,h-1.5,z=1.5)).union(cyl(.75,4.7,z=h))

def prop(d,h):
    p=cyl(2.75,4.0,z=h+.3,inner=.8)
    for k in range(3):
        p=p.union(box(d/2-3.3,5,1,x=(d/2+2.3)/2,z=h+1.7).rotate((0,0,0),(0,0,1),k*120))
    return p

def mass_check(parts):
    props=[H.mass_props(s,m,rho) for _,s,_,m,rho,_ in parts]
    return H.combine(props), props

def bom_row(ref,item,qty,unit,url,status="planning estimate",notes="",category="BUY",spare=0):
    return dict(ref=ref,item=item,quantity_installed=qty,recommended_spares=spare,
                unit_price_usd=unit,extended_usd=round(qty*unit,2) if isinstance(unit,(int,float)) else "quote",
                price_status=status,source_url=url,notes=notes,make_or_buy=category,checked_date=DATE)

def build(kind):
    cheap=kind=="Cheapest_H7"
    dest=OUT/kind; dest.mkdir(parents=True,exist_ok=True)
    (dest/"Parts_STEP").mkdir(exist_ok=True)
    (dest/"Print_and_Cut").mkdir(exist_ok=True)
    if cheap:
        v=H.variant(*H.size_arm()[:3]); v.key="Print_and_Cut"
        v.notes.append("Current release uses a windowed ABS guard; validate printed stiffness and impact performance.")
        pack=(58.,30.,15.); pack_mass=49.; cap=.650; maxv=8.4; nominal=7.4
        motor_mass=3.5; bell=13.5; motor_h=10.; prop_mass=1.; full=142.; testv=7.82
        pitch=25.5; pcb_z=4.; top=12.; cradle_z=22.; frame_rho=1.04e-3
        title="MicoAir H7 / ABS research aircraft"
    else:
        from dataclasses import replace
        v=replace(next(x for x in V.VARIANTS if x.key=="C_Maxed_Out"), key="Print_and_Cut",bell_d=15.95)
        pack=(63.,15.5,13.5); pack_mass=26.1; cap=.450; maxv=8.7; nominal=7.6
        motor_mass=4.3; bell=15.95; motor_h=9.1; prop_mass=1.2; full=223.; testv=7.4
        pitch=20.; pcb_z=4.; top=19.; cradle_z=24.; frame_rho=1.55e-3
        title="Variant C / instrumented carbon research aircraft"
    V.HERE=dest
    V.build(v)
    outline,holes=V.plate_outline(v),V.plate_holes(v)
    plate=V.plate_solid(v,outline,holes).translate((0,0,-v.plate_t))
    # Real sensor mounting: four 2.5 mm holes on a 24.3 x 12 mm rectangle.
    for x in (-12.15,12.15):
        for y in (-6.,6.):
            plate=plate.cut(cyl(1.35,v.plate_t+2,x,y,-v.plate_t-1))
            holes.append((x,y,2.7,"MTF-01 M2.5 clearance"))
    V.write_dxf(v,outline,holes,str(dest/"Print_and_Cut/Frame_current.dxf"))
    guard,_,_=V.guard_solid(v)
    old_guard=guard
    if cheap:
        # Preserve the complete prop-height band; open the lower skirt except two supported columns.
        ri=v.prop_d/2+V.PROP_CLR; wall=v.guard_wall
        band=cyl(ri+wall,12,z=7,inner=ri)
        foot=guard.intersect(box(150,150,2.6,z=0))
        columns=box(4,wall,4.5,y=ri+wall/2,z=2.6).union(box(4,wall,4.5,y=-ri-wall/2,z=2.6))
        guard=foot.union(band).union(columns)
    cradle=V.cradle_solid(v)
    parts=[]
    C={"frame":(.18,.2,.23),"guard":(.93,.42,.10),"motor":(.56,.58,.63),"prop":(.12,.65,.53),
       "board":(.10,.34,.66),"pack":(.26,.27,.32),"mount":(.78,.76,.68),"sensor":(.08,.09,.11)}
    def add(n,s,col,m=None,rho=None,dz=0): parts.append((n,s,col,m,rho,dz))
    add("Frame_plate",plate,C["frame"],rho=frame_rho)
    for i in range(4):
        x,y,a=V.motor_xy(v,i)
        add(f"Guard_{i+1}",H.located(guard,x,y,0,math.degrees(a)),C["guard"],rho=1.04e-3 if cheap else 1.21e-3,dz=45)
        add(f"Motor_{i+1}",motor(bell,motor_h).translate((x,y,0)),C["motor"],motor_mass,dz=20)
        add(f"Propeller_{i+1}",H.located(prop(v.prop_d,motor_h),x,y,0,i*15),C["prop"],prop_mass,dz=32)
        # Feet protect full sensor envelope; attached to outer guard ear with common screw.
        ex=x+v.ear_r*math.cos(a+math.pi/2); ey=y+v.ear_r*math.sin(a+math.pi/2)
        foot=cyl(3.6,20,inner=1.1)
        add(f"Landing_foot_{i+1}",foot.translate((ex,ey,-v.plate_t-20)),C["frame"],rho=1.04e-3,dz=-25)
    for x in (-pitch/2,pitch/2):
        for y in (-pitch/2,pitch/2):
            add(f"Lower_standoff_{x}_{y}",cyl(2.6,4,x,y,0,1.6),C["mount"],.10,dz=8)
            # Board corner keep-outs leave continuous mounting posts unobstructed.
            if cheap:
                add(f"Upper_standoff_{x}_{y}",cyl(2.6,cradle_z-5.6,x,y,5.6,1.6),C["mount"],.35,dz=60)
            else:
                add(f"ESC_FC_standoff_{x}_{y}",cyl(2.6,7.4,x,y,5.6,1.6),C["mount"],.14,dz=18)
                add(f"FC_cradle_standoff_{x}_{y}",cyl(2.6,cradle_z-14.6,x,y,14.6,1.6),C["mount"],.21,dz=60)
    if cheap:
        add("MicoAir743v2_AIO",board(36,36,8,pitch,4),C["board"],10,dz=12)
    else:
        add("Aikon_35A_ESC_envelope",board(36,36,5,pitch,4),C["board"],10.,dz=10)
        add("Matek_H743_MINI_V3",board(36,28,6,pitch,13),(.10,.48,.36),7.,dz=22)
    add("ELRS_receiver",box(14,11,3.5,y=-6,z=top+.5),(.1,.1,.13),2.2,dz=26)
    ant=cq.Workplane("XY").add(cq.Solid.makeCylinder(.6,32,cq.Vector(0,-11.5,top+2.25),cq.Vector(0,-1,0)))
    add("Receiver_antenna",ant,(.12,.12,.12),.3,dz=26)
    # Four holes through the envelope correspond to mount pattern. Remaining sensor features are envelopes.
    sz=-v.plate_t-2-14.5
    flow=box(29.3,17,14.5,z=sz)
    for x in (-12.15,12.15):
        for y in (-6.,6.):
            flow=flow.cut(cyl(1.25,16.5,x,y,sz-1))
            add(f"Sensor_spacer_{x}_{y}",cyl(2.1,2,x,y,-v.plate_t-2,1.35),C["mount"],.04,dz=-6)
    add("MTF01_sensor_envelope",flow,C["sensor"],4.5,dz=-18)
    add("Battery_cradle",cradle.translate((0,0,cradle_z)),C["guard"],rho=1.04e-3,dz=74)
    pz=cradle_z+V.CRADLE_T
    add("Battery_pack",box(*pack,z=pz),C["pack"],pack_mass,dz=95)
    # Connector position is an installation envelope; wire mass kept separate from the pack.
    add("XT30_connector",box(10,5,5,x=pack[0]/2+9,z=pz+pack[2]/2-2.5),(.95,.78,.10),2.,dz=95)
    H.CONFIG["pack"]["dims"]=pack
    _,_,strap=H.pack_solids(pz)
    add("Battery_strap",strap,(.16,.16,.16),1.,dz=95)
    # Small parts modeled as separated installation envelopes; account for wires/fasteners without fictitious geometry.
    extra=5.0 if cheap else 7.0
    (mt,cg,I),mps=mass_check(parts)
    moving=[i for i,p in enumerate(parts) if p[0] in ("Battery_pack","XT30_connector")]
    movable=sum(mps[i][0] for i in moving)
    shift=-sum(m*c for m,c,_ in mps)/movable; shift[2]=0
    shift=np.round(shift,2)
    shift[1]=0  # slide along the cradle only; lateral motion would consume its 0.3 mm wall clearance
    parts=[(n,s.translate(tuple(shift)) if i in moving else s,col,m,r,dz) for i,(n,s,col,m,r,dz) in enumerate(parts)]
    (mt,cg,I),mps=mass_check(parts)
    mps.append((extra,np.zeros(3),np.diag([extra*30**2/2,extra*30**2/2,extra*30**2])))
    mt,cg,I=H.combine(mps)
    asm=cq.Assembly(name=kind); exp=cq.Assembly(name=kind+"_exploded")
    part_files=[]
    for n,s,col,m,r,dz in parts:
        name=n.replace(".","p").replace("-","n")
        asm.add(s,name=name,color=cq.Color(*col));exp.add(s.translate((0,0,dz)),name=name,color=cq.Color(*col))
        file="Parts_STEP/"+name+".step";cq.exporters.export(s,str(dest/file));part_files.append(file)
    asm.save(str(dest/(kind+"_Assembly.step")));exp.save(str(dest/(kind+"_Exploded.step")))
    cq.exporters.export(plate,str(dest/"Print_and_Cut/Frame_plate.step"))
    cq.exporters.export(plate,str(dest/"Print_and_Cut/Frame_plate.stl"))
    cq.exporters.export(guard,str(dest/"Print_and_Cut/Guard_current.step"))
    cq.exporters.export(guard,str(dest/"Print_and_Cut/Guard_current.stl"))
    cq.exporters.export(old_guard,str(dest/"Print_and_Cut/Guard_full_skirt_reference.step"))
    cq.exporters.export(cradle,str(dest/"Print_and_Cut/Battery_cradle.step"))
    cq.exporters.export(foot,str(dest/"Print_and_Cut/Landing_foot.stl"))
    # Pairwise represented solids, excluding deliberate zero-volume contacts.
    clashes=[]
    for i,(na,A,*_) in enumerate(parts):
        A=cq.Compound.makeCompound(A.vals());ba=A.BoundingBox()
        for nb,B,*_ in parts[i+1:]:
            B=cq.Compound.makeCompound(B.vals());bb=B.BoundingBox()
            if any((getattr(ba,k+"max") < getattr(bb,k+"min") or getattr(bb,k+"max") < getattr(ba,k+"min")) for k in "xyz"):continue
            vol=A.intersect(B).Volume()
            if vol>.05:clashes.append(dict(a=na,b=nb,overlap_mm3=round(vol,3)))
    guard_g=guard.val().Volume()*(1.04e-3 if cheap else 1.21e-3)
    retention=.85
    reference_tw=4*full*retention/mt
    thrust_full=4*full*retention*(maxv/testv)**2
    inertia=I*1e-9
    phys=dict(title=title,revision="R1",date=DATE,status="CAD and planning model; not built or flown",
       total_mass_g=round(mt,2),cg_mm=np.round(cg,3).tolist(),battery_shift_mm=shift.tolist(),
       inertia_kgm2_about_cg=inertia.tolist(),inertia_note="Purchased masses distributed uniformly over envelope solids; wiring/fasteners are estimates",
       motor_diagonal_mm=round(2*v.motor_r,2),plate_thickness_mm=v.plate_t,guard_mass_each_g=round(guard_g,2),
       guard_full_skirt_reference_mass_each_g=round(old_guard.val().Volume()*(1.04e-3 if cheap else 1.21e-3),2),
       sensor_dimensions_mm=[29.3,17,14.5],sensor_ground_clearance_mm=3.5,
       pack=dict(capacity_ah=cap,max_voltage_v=maxv,nominal_voltage_v=nominal,mass_g=pack_mass),
       propulsion=dict(vendor_thrust_per_motor_g=full,vendor_test_voltage_v=testv,guard_thrust_retention_assumed=retention,
           tw_at_vendor_voltage=round(reference_tw,2),tw_at_full_pack_v2_scaling=round(thrust_full/mt,2),
           thrust_limited_extra_mass_at_7v_tw_1p3_g=round(max(0,4*full*retention*(7/testv)**2/1.3-mt),1),
           guard_factor_sensitivity=[.75,1.0],ballast_note="Lift-only estimate; mount capacity, current, thermal and recovery limits require measurement"),
       modelled_parts=[dict(name=p[0],mass_g=round(mp[0],3),cg_mm=mp[1].tolist(),source="CAD density" if p[3] is None else "vendor or estimate") for p,mp in zip(parts,mps)],
       extra_wiring_fasteners_mass_g=extra,unverified=["propeller thrust/current with installed guard", "battery resistance and FC brownout margin",
         "printed material stiffness and impact strength", "motor dimensions and screw engagement on receipt", "all cable routing and connector access",
         "independent stop during a Lua fault", "physical ballast attachment and structural rating"])
    if not cheap:phys["unverified"].append("Aikon 36 x 36 x 5 mm envelope and connector pin order are planning assumptions")
    if cheap:
        H.CONFIG["motor"]["mass_g"]=motor_mass;H.CONFIG["prop"]["mass_g"]=prop_mass
        phys["arm_beam_estimate_hz"]=list(np.round(H.modes(v.motor_r,v.core,v.arm_w,v.plate_t,guard_g)[:3],1))
    # Calibrate thrust-space hover fraction to model convention; this is not a raw PWM setting.
    hover_fraction=mt/thrust_full
    hover_current=9.0 if cheap else 4.5
    sitl=dict(mass=round(mt/1000,6),diagonal_size=v.motor_r/1000,refSpd=8.,refAngle=25.,refVoltage=nominal,
              refCurrent=hover_current,refAlt=10,refTempC=20,refBatRes=.029,maxVoltage=maxv,battCapacityAh=cap,
              propExpo=.55,refRotRate=360,hoverThrOut=round(hover_fraction,5),pwmMin=1000,pwmMax=2000,
              spin_min=.1,spin_max=.95,slew_max=30,disc_area=4*math.pi*(v.prop_d/2000)**2,mdrag_coef=.2,
              moment_inertia=np.diag(inertia).tolist(),num_motors=4)
    for name,obj in [("physical_model.json",phys),("sitl_model.json",sitl),("assembly_interference.json",dict(pairs_checked=len(parts)*(len(parts)-1)//2,clashes=clashes,scope="Nominal represented solids; cables and fasteners partly represented by mass allowances")),("part_files.json",part_files)]:
        (dest/name).write_text(json.dumps(obj,indent=2))
    # Reproducible high-resolution CAD views, not photographs.
    for filename,elev,azim in [("assembled",26,-52),("top",90,-90),("side",0,-90),("exploded",20,-52)]:
        items=[(s.translate((0,0,dz)) if filename=="exploded" else s,col) for _,s,col,_,_,dz in parts]
        H.render(items,dest/(filename+".png"),title+" | "+filename+" | CAD",elev=elev,azim=azim)
    rows=[]
    if cheap:rows.append(bom_row("FC1","MicoAir743v2-AIO-35A (exact v2, Bluejay)",1,64.99,SOURCES["mico"],"manufacturer listed",notes="FC + ESC; external ELRS required"))
    else:
        rows += [bom_row("FC1","Matek H743-MINI V3",1,120.,SOURCES["matek"],"prior supplier/FX estimate; EOL; quote before purchase"),
                 bom_row("ESC1","Aikon AK32PIN 35A V2 2-6S",1,59.99,SOURCES["aikon"],"retailer listed; checkout stock unconfirmed",notes="Manufacturer 10 g with wires: https://aikon-electronics.com/index.php?id=28 . Outline and pinout unverified")]
    rows += [bom_row("RX1","RadioMaster RP1 V2 ELRS",1,18.99,SOURCES["rx"]),
             bom_row("M1-M4",v.motor,4,9.2475 if cheap else 13.49,SOURCES["motor_cheap" if cheap else "motor_c"],notes="Cheap price allocated from $36.99 four-pack" if cheap else "3.9 g trimmed / 4.3 g with long wires; mounting pattern verify delivered motor",spare=2),
             bom_row("P1-P4",v.prop+" 1.5 mm shaft (2 CW + 2 CCW)",1,3.20 if cheap else 3.,"https://www.gemfanhobby.com/",notes="One set of four; verify exact 65R SKU/shaft for C",spare=2),
             bom_row("BAT1",v.pack_name,1,5.99 if cheap else 8.995,SOURCES["pack_cheap" if cheap else "pack_c"],"retailer estimate" if cheap else "manufacturer $17.99 per two-pack; allocated",notes="Budget a two-pack cash purchase for LAVA",spare=3),
             bom_row("S1","MicoAir MTF-01 optical flow / ToF",1,22.9,SOURCES["flow"],notes="29.3 x 17 x 14.5 mm; 24.3 x 12 mount; onboard sensor, not independent height truth"),
             bom_row("LOG1","microSD card",1,5.,"",notes="One installed card; confirm manufacturer-supported media"),
             bom_row("HW1","Motor, stack, guard and sensor fasteners + spacers",1,6.,"",notes=("M1.4x5 motors; 4x M2x35 + 4x M2x10 guards" if cheap else "M2 motor screws: check engagement; 4x M2x30 + 4x M2x10 guards")+"; M2.5 sensor screws/spacers sized to delivered mount flange"),
             bom_row("WIRE1","XT30 pigtail, 470uF capacitor, wire, strap",1,4.,"",notes="Trim leads and route clear of rotors; current rating/temperature to qualify"),
             bom_row("FRAME1",f"Frame plate: {v.plate_t} mm "+("ABS" if cheap else "carbon"),1,0 if cheap else "quote","makerspace",notes="Zero printing charge assumed by owner; carbon cutting price excluded until quoted",category="MAKE"),
             bom_row("G1-G4","Windowed ABS guards" if cheap else "TPU ducts",4,0,"makerspace",notes="Impact and thrust testing required; full-skirt cheap guard retained for comparison",category="MAKE",spare=2),
             bom_row("CRADLE1","ABS battery cradle",1,0,"makerspace",category="MAKE"),
             bom_row("FEET1-4","20 mm ABS landing feet",4,0,"makerspace",notes="Protects full-height MTF-01 with 3.5 mm nominal level-ground clearance",category="MAKE")]
    if not cheap:rows += [bom_row("BUZZ1","5 V active buzzer and sync LED",1,2.,""),bom_row("BALLAST1","Weighed centred ballast and attachment hardware",1,8.,"",notes="No approved load rating; qualify mount before loading")]
    with (dest/"BOM.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    priced=sum(x["extended_usd"] for x in rows if isinstance(x["extended_usd"],(int,float)))
    (dest/"BOM.json").write_text(json.dumps(dict(currency="USD",priced_aircraft_subtotal=round(priced,2),rows=rows,excluded="Tax, shipping, bulk discount, carbon quote, radio, charger, tools and external test apparatus. Spares shown separately; not included in subtotal."),indent=2))
    md=f"# {title}\n\nRevision R1. CAD design, not built or flown.\n\nThe numerical source is [physical_model.json](physical_model.json); purchase quantities and prices are in [BOM.csv](BOM.csv).\n\n"
    md+="Open the assembly STEP or the native assembly in `SolidWorks/` when available. Individual STEP parts preserve separate component identity; purchased parts are envelopes.\n\n"
    md+=f"The priced aircraft subtotal is ${priced:.2f}, plus any quoted items, tax and shipping. Printing is priced at zero under the owner's makerspace assumption. Spares and shared test equipment are excluded.\n\n"
    md+="## Changes applied\n\n- Correct full MTF-01 envelope, mounting holes and longer landing feet.\n- Battery capacity and maximum charge voltage match the selected pack.\n- CAD mass and inertia generate the current simulation input. Prior simulation runs retain their original configuration and are not transferred to this revision.\n- Guard thrust retention is an assumption with a sensitivity range; no duct thrust gain is credited.\n- CG is balanced in the planning model by a recorded pack shift. Final balance requires weighing and physical adjustment.\n"
    if cheap:md+="- Windowed lower guard skirt reduces modeled mass while retaining a continuous 12 mm upper ring. The previous full skirt is retained for comparison and impact qualification.\n"
    md+="\n## Remaining physical qualifications\n\n"+"\n".join("- "+x for x in phys["unverified"])+"\n\nOnboard ToF supports the controller; independent video or motion capture is required for an independent height outcome. SITL level-drop checks address vertical recovery under their stated conditions.\n"
    (dest/"README.md").write_text(md)
    print(json.dumps(dict(aircraft=kind,mass_g=round(mt,2),priced_subtotal=round(priced,2),guard_g=round(guard_g,2),clashes=clashes),indent=2),flush=True)

if __name__=="__main__":
    OUT.mkdir(exist_ok=True)
    for kind in sys.argv[1:] or ["Cheapest_H7","Variant_C"]:build(kind)
