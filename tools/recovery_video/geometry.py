"""Generic display airframe; dimensions are illustrative, not measured CAD."""
import bpy, math
from mathutils import Vector
def material(name, rgb, metallic=0., roughness=.45):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb,1)
    m.use_nodes = True
    node = m.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*rgb,1)
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = roughness
    return m

carbon = material('Graphite frame',(.055,.065,.08),.2,.4)
black = material('Propeller polymer',(.022,.026,.032),.05,.4)
metal = material('Motor aluminum',(.31,.34,.38),.72,.27)
silver = material('Fasteners',(.66,.69,.73),.75,.25)
blue = material('Front orientation mark',(.045,.14,.42),.05,.42)
battery = material('Battery wrap',(.19,.21,.24),.12,.5)
rubber = material('Landing pads',(.028,.03,.034),0,.8)

parent = bpy.data.objects.new('Optimistic attitude',None)
bpy.context.collection.objects.link(parent)
parts = []

def finish(obj,name,mat):
    obj.name = name
    obj.data.materials.append(mat)
    obj.parent = parent
    parts.append(obj)
    return obj

def box(name,loc,scale,mat,bevel=.004):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(obj,name,mat)
    if bevel:
        mod=obj.modifiers.new('Machined edge','BEVEL');mod.width=bevel;mod.segments=3
        obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return obj

def cylinder(name,loc,radius,depth,mat,vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc)
    obj=finish(bpy.context.object,name,mat)
    for poly in obj.data.polygons: poly.use_smooth=True
    mod=obj.modifiers.new('Edge radius','BEVEL');mod.width=.0015;mod.segments=2
    obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return obj

def beam(name,a,b,radius,mat):
    a,b=Vector(a),Vector(b)
    obj=cylinder(name,(a+b)/2,radius,(b-a).length,mat)
    obj.rotation_mode='QUATERNION'
    obj.rotation_quaternion=(b-a).to_track_quat('Z','Y')
    return obj

# Generic display geometry, not a claimed CAD model or collision envelope.
box('Lower center plate',(0,0,-.012),(.115,.145,.008),carbon,.006)
box('Top center plate',(0,0,.020),(.105,.125,.009),carbon,.006)
box('Battery',(0,-.008,.043),(.065,.094,.035),battery,.008)
box('Battery strap',(0,-.008,.063),(.071,.018,.005),black,.001)
box('Blue forward plate',(0,.059,.022),(.065,.021,.009),blue,.002)
for x in [-.041,.041]:
    for y in [-.046,.046]:
        cylinder('Frame standoff',(x,y,.005),.004,.025,metal,16)
        cylinder('Plate screw',(x,y,.026),.0032,.002,silver,16)
for i,(x,y) in enumerate([(-.14,-.14),(.14,-.14),(-.14,.14),(.14,.14)]):
    beam('Carbon motor arm',(.018*(1 if x>0 else -1),.018*(1 if y>0 else -1),-.008),
         (x,y,-.008),.010,carbon)
    cylinder('Motor stator',(x,y,.002),.020,.023,metal)
    cylinder('Motor bell',(x,y,.017),.021,.015,blue if y>0 else carbon)
    cylinder('Motor cap',(x,y,.026),.013,.004,metal)
    cylinder('Propeller hub',(x,y,.033),.010,.009,black)
    cylinder('Prop nut',(x,y,.040),.004,.005,silver,16)
    # A conventional two-blade propeller with tapered planform and slight pitch.
    for angle in [i*.77,i*.77+math.pi]:
        shape=[(.008,-.008,0),(.037,-.012,.001),(.080,-.008,.002),
               (.091,-.003,.001),(.088,.004,-.001),(.052,.007,-.002),(.012,.006,0)]
        c,s=math.cos(angle),math.sin(angle)
        vertices=[(c*xx-s*yy,s*xx+c*yy,zz) for xx,yy,zz in shape]
        mesh=bpy.data.meshes.new('Tapered propeller mesh')
        mesh.from_pydata(vertices,[],[tuple(range(len(vertices)))])
        obj=bpy.data.objects.new('Propeller blade',mesh);bpy.context.collection.objects.link(obj)
        finish(obj,'Propeller blade',black)
        obj.location=(x,y,.035)
        obj['rotor_index']=i
        mod=obj.modifiers.new('Blade thickness','SOLIDIFY');mod.thickness=.0014
        bevel=obj.modifiers.new('Blade edge','BEVEL');bevel.width=.001;bevel.segments=2
    # Open prop guards make the model recognizable as a guarded quadcopter.
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=8,
        location=(x,y,.026),major_radius=.100,minor_radius=.0032)
    obj=finish(bpy.context.object,'Propeller guard',carbon)
    for poly in obj.data.polygons: poly.use_smooth=True
    for angle in [.65,2.75,4.85]:
        beam('Guard spoke',(x+.026*math.cos(angle),y+.026*math.sin(angle),-.004),
             (x+.1*math.cos(angle),y+.1*math.sin(angle),.026),.0025,carbon)
    cylinder('Landing pad',(x,y,-.032),.011,.019,rubber,20)
