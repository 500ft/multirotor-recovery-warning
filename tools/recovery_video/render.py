"""Blender scene with actual XYZ travel, equal scale and a horizontal follow camera."""
from pathlib import Path
import json, sys, math, time
import bpy
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / '.video-build'
OUT = BUILD / 'frames'
OUT.mkdir(exist_ok=True)
DATA = json.loads((BUILD / 'display.json').read_text())
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry
parent = geometry.parent
# Equal-sized glyphs keep the small airframe legible. World travel and attitude
# remain exactly the simulated values; this is not an aircraft CAD rendering.
parent.scale = (2.4,) * 3
parent.rotation_mode = 'QUATERNION'
blades = [o for o in parent.children if 'rotor_index' in o]

def mat(name, rgb):
    m = bpy.data.materials.new(name); m.diffuse_color = (*rgb,1); m.use_nodes = True
    n = m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value = (*rgb,1); n.inputs['Roughness'].default_value = .65
    return m

floor = mat('Slate floor', (.13,.19,.26))
grid = mat('Grid', (.25,.32,.40))
wall = mat('Wall', (.19,.25,.32))
blue = mat('Flight path', (.035,.15,.52))
pad = mat('Release pad', (.065,.10,.16))

def box(name, loc, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale; o.data.materials.append(material)
    return o

box('Floor', (25,0,-.05), (160,160,.1), floor)
for i in range(-20,75):
    box('Grid across travel', (i,0,.002), (.012,70,.003), grid)
for i in range(-30,30):
    box('Grid along travel', (25,i,.002), (120,.012,.003), grid)
box('Release pad', (0,0,.008), (1.65,1.65,.014), pad)
for x in [-.83,.83]: box('Pad edge',(x,0,.019),(.018,1.68,.008),blue)
for y in [-.83,.83]: box('Pad edge',(0,y,.019),(1.68,.018,.008),blue)
box('Background', (25,6,3), (140,.1,8), wall)
for z in range(1,7): box('Horizontal seam',(25,5.94,z),(140,.012,.009),grid)
for x in range(-20,80,2): box('Vertical seam',(x,5.94,3),(.009,.012,8),grid)

curve = bpy.data.curves.new('Logged center trajectory','CURVE')
curve.dimensions = '3D'; curve.bevel_depth = .012; curve.bevel_resolution = 2
trail = bpy.data.objects.new('Trajectory',curve); bpy.context.collection.objects.link(trail)
trail.data.materials.append(blue)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_gtao = True; scene.eevee.gtao_distance = 1.; scene.eevee.gtao_factor = 1.2
scene.eevee.taa_render_samples = 16; scene.eevee.use_soft_shadows = True
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.68,.74,.82,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .55
scene.view_settings.view_transform = 'Filmic'; scene.view_settings.look = 'Medium High Contrast'
scene.render.resolution_x = 800; scene.render.resolution_y = 420
scene.render.resolution_percentage = 100
scene.render.image_settings.color_mode = 'RGB'; scene.render.image_settings.file_format = 'PNG'
scene.render.threads_mode = 'FIXED'; scene.render.threads = 4

lights = []
for name,offset,power,size in [('Key',(1,-3,8),600,2.5),('Fill',(-4,-1,5),350,5),('Rim',(2,4,6),600,4)]:
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.size=size
    o=bpy.data.objects.new(name,d); scene.collection.objects.link(o)
    lights.append((o,Vector(offset)))
d=bpy.data.cameras.new('Common scale camera'); camera=bpy.data.objects.new('Camera',d)
scene.collection.objects.link(camera); scene.camera=camera
d.type='ORTHO'; d.ortho_scale=8.8
preview='--preview' in sys.argv
frames=[0,60,108,144,240,420,588] if preview else range(len(DATA['timeline']))
manifest=[]; cache={}; start=time.time()
# Display rotor indices (-x,-y),(+x,-y),(-x,+y),(+x,+y)
# map to the allocation order (+x,+y),(-x,+y),(-x,-y),(+x,-y).
rotor_map=[2,3,1,0]
for f in frames:
    s=DATA['timeline'][f]; files=[]
    for c,key in enumerate(DATA['keys']):
        pos=Vector(s['pos'][c]); q=s['q'][c]; phases=s['phase'][c]
        state=tuple(round(v,8) for v in [*pos,*q,*phases])
        if state not in cache:
            parent.location=pos; parent.rotation_quaternion=Quaternion(q)
            for b in blades:
                i=rotor_map[b['rotor_index']]
                b.rotation_euler.z=(1 if i in [0,2] else -1)*phases[i]
            # Let the aircraft travel one metre in the frame, then follow XY.
            # Camera height and orientation stay fixed; altitude is never followed.
            xy=Vector((pos.x,pos.y,0)); length=xy.length
            follow=xy*(max(0,length-1.0)/length) if length else Vector((0,0,0))
            target=follow+Vector((0,0,1.85))
            camera.location=follow+Vector((5,-9,5.2))
            camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
            for light,offset in lights:
                light.location=follow+offset
                light.rotation_euler=(follow+Vector((0,0,1.4))-light.location).to_track_quat('-Z','Y').to_euler()
            curve.splines.clear()
            points=[DATA['timeline'][j]['pos'][c] for j in range(0,f+1,3)]
            if points[-1]!=list(pos): points.append(list(pos))
            spline=curve.splines.new('POLY'); spline.points.add(len(points)-1)
            for point,xyz in zip(spline.points,points): point.co=(*xyz,1)
            name=f'{key}-{f:04}.png'; scene.render.filepath=str(OUT/name)
            bpy.ops.render.render(write_still=True); cache[state]=name
        files.append(cache[state])
    manifest.append({'frame':f,'files':files})
    if f%24==0: print(f'PROGRESS {f}/{len(DATA["timeline"])} {time.time()-start:.1f}s',flush=True)
(BUILD/('preview_manifest.json' if preview else 'manifest.json')).write_text(json.dumps(manifest))
print(f'COMPLETE {len(manifest)} frames {len(cache)} renders {time.time()-start:.1f}s',flush=True)
