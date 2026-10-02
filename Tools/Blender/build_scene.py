"""Geisel Library / Snake Path: repeatable editable reconstruction, metres, Z up.

Run Blender 4.5 in background with --python this file. Public-source exterior
study, not a measured survey. See Docs/ReferenceStudy.md for provenance.
"""
import bpy, math, random, json, sys, argparse
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
random.seed(1970)
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser()
parser.add_argument('--architecture-only',action='store_true')
parser.add_argument('--render',action='store_true')
opt=parser.parse_args(args)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for mat in list(bpy.data.materials): bpy.data.materials.remove(mat)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
scene.render.engine='CYCLES'; scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1920; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.film_transparent=False

def mat(name,color,rough=.7,metal=0,noise=False):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    if noise:
        n=m.node_tree.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=5
        n.inputs['Detail'].default_value=4; n.inputs['Roughness'].default_value=.73
        tc=m.node_tree.nodes.new('ShaderNodeTexCoord'); m.node_tree.links.new(tc.outputs['Object'],n.inputs['Vector'])
        mix=m.node_tree.nodes.new('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'
        mix.inputs[0].default_value=.22; mix.inputs[1].default_value=(*color,1)
        m.node_tree.links.new(n.outputs['Fac'],mix.inputs[2]); m.node_tree.links.new(mix.outputs[0],p.inputs['Base Color'])
        bump=m.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.22; bump.inputs['Distance'].default_value=.028
        m.node_tree.links.new(n.outputs['Fac'],bump.inputs['Height']); m.node_tree.links.new(bump.outputs[0],p.inputs['Normal'])
        if name.startswith('Concrete'):
            wave=m.node_tree.nodes.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='Z'
            wave.inputs['Scale'].default_value=1.7;wave.inputs['Distortion'].default_value=.08
            m.node_tree.links.new(tc.outputs['Object'],wave.inputs['Vector'])
            ramp=m.node_tree.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.93;ramp.color_ramp.elements[1].position=.97
            m.node_tree.links.new(wave.outputs['Fac'],ramp.inputs[0])
            board=m.node_tree.nodes.new('ShaderNodeBump');board.inputs['Strength'].default_value=.18;board.inputs['Distance'].default_value=.012
            m.node_tree.links.new(ramp.outputs[0],board.inputs['Height']);m.node_tree.links.new(bump.outputs[0],board.inputs['Normal'])
            m.node_tree.links.new(board.outputs[0],p.inputs['Normal'])
    return m
CON=mat('Concrete_WarmBoardForm',(.49,.475,.423),.83,noise=True)
LIP=mat('Concrete_EdgeLight',(.62,.607,.55),.76,noise=True)
DARK=mat('Concrete_Recess',(.24,.235,.209),.88,noise=True)
ALU=mat('Mullion_BronzeBlack',(.044,.052,.051),.29,.72)
GLASS=[mat('Glass_Reflective_%02d'%i,(.115+i*.009,.195+i*.013,.23+i*.016),.16+(i%3)*.019,.72) for i in range(5)]
ROOF=mat('Roof_Gravel',(.30,.30,.27),.92,noise=True)
LETTER=mat('Sign_BrushedMetal',(.15,.17,.16),.4,.65)
LIGHT=mat('Light_Warm',(.9,.66,.32),.25)
LIGHT.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(1,.64,.27,1)
LIGHT.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=1.6

# Mesh batching keeps source easily editable while limiting runtime draw calls.
class Batch:
    def __init__(self,name,materials): self.name=name; self.mats=materials; self.v=[]; self.f=[]; self.mi=[]
    def add(self,vs,fs,mi=0):
        off=len(self.v); self.v.extend(vs); self.f.extend([tuple(off+j for j in f) for f in fs]); self.mi.extend([mi]*len(fs))
    def box(self,c,d,mi=0):
        x,y,z=c; a,b,h=[q/2 for q in d]
        self.add([(x-a,y-b,z-h),(x+a,y-b,z-h),(x+a,y+b,z-h),(x-a,y+b,z-h),(x-a,y-b,z+h),(x+a,y-b,z+h),(x+a,y+b,z+h),(x-a,y+b,z+h)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mi)
    def beam(self,a,b,width,depth,mi=0):
        a,b=Vector(a),Vector(b); w=(b-a).normalized(); u=w.cross(Vector((0,0,1)))
        if u.length<.01:u=Vector((1,0,0))
        u.normalize(); v=w.cross(u).normalized()
        vs=[tuple(p+u*s*width/2+v*t*depth/2) for p in (a,b) for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        self.add(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mi)
    def finish(self,bevel=0):
        mesh=bpy.data.meshes.new(self.name); mesh.from_pydata(self.v,[],self.f); mesh.materials.clear()
        for m in self.mats:mesh.materials.append(m)
        ob=bpy.data.objects.new(self.name,mesh); bpy.context.collection.objects.link(ob)
        for p,i in zip(mesh.polygons,self.mi):p.material_index=i
        if bevel:
            mod=ob.modifiers.new('Small cast-concrete edge bevel','BEVEL');mod.width=bevel;mod.segments=2
        return ob

slabs=Batch('Building_FloorSlabs',[CON,LIP,ROOF,DARK])
supports=Batch('Building_SixteenInclinedPiers',[CON,DARK])
ribs=Batch('Building_SoffitRibs',[CON,DARK])
frames=Batch('Building_FacadeMullions',[ALU])
glass=Batch('Building_ReflectiveGlazing',GLASS)
detail=Batch('Building_GroundDetail',[CON,LIP,DARK,ALU,LIGHT])

def outline(r):
    # Floor edges keep structural grid positions. The outer steps disappear on
    # the smaller floors, rather than scaling the entire jagged perimeter.
    R=36.95; b=R*.38; d=(R-b)/3
    q=[(R,0),(R,b),(R-d,b),(R-d,b+d),(R-2*d,b+d),(R-2*d,b+2*d),(b,b+2*d),(b,R),(0,R)]
    # Adjacent collinear / duplicate points are intentionally simplified.
    ring=[]
    for k in range(4):
        for x,y in q[:-1]:
            for _ in range(k):x,y=-y,x
            if not ring or (x,y)!=ring[-1]:ring.append((x,y))
    for axis,limit,sgn in [(0,r,1),(0,-r,-1),(1,r,1),(1,-r,-1)]:
        result=[]
        for a,bp in zip(ring,ring[1:]+ring[:1]):
            inside_a=(a[axis]-limit)*sgn<=1e-8;inside_b=(bp[axis]-limit)*sgn<=1e-8
            if inside_a:result.append(a)
            if inside_a!=inside_b:
                t=(limit-a[axis])/(bp[axis]-a[axis]);result.append(tuple(a[j]+t*(bp[j]-a[j]) for j in range(2)))
        ring=result
    cleaned=[]
    for i,p in enumerate(ring):
        a=ring[i-1]; c=ring[(i+1)%len(ring)]
        if abs((p[0]-a[0])*(c[1]-p[1])-(p[1]-a[1])*(c[0]-p[0]))>1e-8:cleaned.append(p)
    return cleaned

def slab(poly,z,thick=.50):
    # Profiles flare at the top to reproduce the fine projecting eaves.
    n=len(poly); layers=[(z-thick,.18),(z-.12,.87),(z,1.0)]
    vs=[]
    for zz,e in layers:
        for x,y in poly:
            scale=1+e*.85/max(abs(x),abs(y))
            vs.append((x*scale,y*scale,zz))
    fs=[tuple(range(n-1,-1,-1))]; ids=[0]
    for l in range(2):
        for i in range(n):fs.append((l*n+i,l*n+(i+1)%n,(l+1)*n+(i+1)%n,(l+1)*n+i));ids.append(1)
    fs.append(tuple(range(2*n,3*n)));ids.append(2)
    offset=len(slabs.v);slabs.v.extend(vs)
    slabs.f.extend([tuple(offset+i for i in f) for f in fs]);slabs.mi.extend(ids)

LEVELS=[(4,22.65,20.22),(5,26.78,27.5),(6,30.91,36.95),(7,35.04,27.5),(8,39.17,20.22)]
for level,z,r in LEVELS:
    poly=outline(r); slab(poly,z)
    top=z+3.68
    # The external eave projects around both the floor and roof silhouette.
    slab(poly,top+.40,.33)
    for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
        va,vb=Vector((*a,0)),Vector((*b,0)); edge=vb-va;length=edge.length
        tangent=edge.normalized();out=Vector((tangent.y,-tangent.x,0))
        panel_count=max(1,round(length/1.45)); step=length/panel_count
        for j in range(panel_count):
            p1=va+tangent*(j*step+.035)-out*.10;p2=va+tangent*((j+1)*step-.035)-out*.10
            # Plane normals outward. Paired reverse faces improve reflecting glass from all angles.
            vs=[(p1.x,p1.y,z+.18),(p2.x,p2.y,z+.18),(p2.x,p2.y,top-.10),(p1.x,p1.y,top-.10)]
            glass.add(vs,[(0,1,2,3)],random.choices(range(5),[1,2,5,2,1])[0])
        for j in range(panel_count+1):
            p=va+tangent*j*step-out*.08
            frames.box((p.x,p.y,(z+top)/2),(.07,.07,top-z+.12))
        frames.beam((a[0],a[1],z+.12),(b[0],b[1],z+.12),.09,.1)
        frames.beam((a[0],a[1],top-.02),(b[0],b[1],top-.02),.09,.10)
    # Exposed coffer ribs under all cantilever wings, accurately continuous in 3D.
    for k in range(4):
        for t in [i*2.10 for i in range(-5,6)]:
            a=(11.0,t,z-.60);b=(r+.3,t,z-.60)
            for _ in range(k):a=(-a[1],a[0],a[2]);b=(-b[1],b[0],b[2])
            ribs.beam(a,b,.35,.76)
        for dist in [r-1.2,r-5.4]:
            a=(dist,-r/3,z-.65);b=(dist,r/3,z-.65)
            for _ in range(k):a=(-a[1],a[0],a[2]);b=(-b[1],b[0],b[2])
            ribs.beam(a,b,.38,.54)

# The unmistakable 16 concrete fingers supporting the stepped reading tower.
for k in range(4):
    for tangential in [-10.4,-3.47,3.47,10.4]:
        # Monolithic vertical foot, curved knee and inclined finger. The
        # lower upright section is a defining detail of Pereira's bents.
        profile=[(12.4,10.10),(14.2,10.10),(14.2,14.55),(14.35,15.1),(14.7,15.55),(37.85,30.45),(37.85,32.10),(13.7,17.05),(13.1,16.48),(12.62,15.72),(12.4,14.85)]
        vertices=[]
        for yy in [tangential-.66,tangential+.66]:
            for xx,zz in profile:
                a=(xx,yy,zz)
                for _ in range(k):a=(-a[1],a[0],a[2])
                vertices.append(a)
        n=len(profile);faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        faces.extend([(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)])
        supports.add(vertices,faces)

# Central service core / pedestal and enclosed base with deeply shaded arcade.
detail.box((0,0,16.1),(20.6,20.6,12.2),0)
for k in range(4):
    for t in [-7.7,-2.6,2.6,7.7]:
        a=(10.38,t,16.0)
        for _ in range(k):a=(-a[1],a[0],a[2])
        if k%2==0:detail.box(a,(.14,4.8,9.2),3)
        else:detail.box(a,(4.8,.14,9.2),3)

# Partly embedded two-level podium; most underground extension remains hidden by terrain.
for k in range(4):
    a=(21.0,-19.5,8.10);b=(21.0,19.5,8.10)
    for _ in range(k):a=(-a[1],a[0],a[2]);b=(-b[1],b[0],b[2])
    tangent=(Vector(b)-Vector(a)).normalized()
    for j in range(27):
        p=Vector(a)+tangent*(j*1.5)
        frames.box(tuple(p),(.09,.09,3.65))
    av=Vector(a);bv=Vector(b)
    glass.add([(av.x,av.y,6.37),(bv.x,bv.y,6.37),(bv.x,bv.y,9.79),(av.x,av.y,9.79)],[(0,1,2,3)],0)
detail.box((0,0,9.79),(43.4,43.4,.62),1)
detail.box((0,0,6.37),(43.4,43.4,.22),1)
# Roof access core with recess to keep original outline at overall 110 feet above terrace.
slabs.box((0,0,43.24),(16.0,16.0,.54),2)

# Geisel name plate on south elevation; engraved-looking dark lettering, editable text in blend.
detail.box((0,-21.78,9.28),(15.5,.20,1.16),1)
font=bpy.data.curves.new('Geisel Library lettering','FONT');font.body='Geisel Library';font.align_x='CENTER'
font.size=.57;font.extrude=.009;font.bevel_depth=.002
ob=bpy.data.objects.new('Building_GeiselLibrarySign',font);bpy.context.collection.objects.link(ob)
ob.location=(0,-21.90,9.08);ob.rotation_euler=(math.pi/2,0,0);font.materials.append(LETTER)

# Entrance glass doors, tubular handles, bollards, benches and warm soffit lights.
for x in [-3.2,-1.6,0,1.6,3.2]:
    frames.box((x,-21.17,7.65),(.065,.12,2.62))
for x in [-2.38,-.82,.82,2.38]:
    detail.box((x,-21.30,7.60),(.045,.05,.60),3)
for k in range(4):
    for t in [-16,-8,8,16]:
        # The south entrance drops below the terrace. These two positions
        # have no supporting paving at the terrace height.
        if k == 3 and abs(t) == 8:
            continue
        p=(23.9,t,10.50)
        for _ in range(k):p=(-p[1],p[0],p[2])
        detail.box(p,(.35,.35,1.0),3)
        detail.box((p[0],p[1],11.02),(.39,.39,.07),4)
for t in [-12,-6,0,6,12]:
    detail.box((t,-20,9.45),(1.4,.18,.035),4)
# The 1969 report explicitly gives the widest tower floor as 200 feet. The
# current website's 248 feet is treated as the overall complex span, not this floor.
TOWER_XY=60.96/75.60
for group in [slabs,supports,ribs]:
    group.v=[(x*TOWER_XY,y*TOWER_XY,z) for x,y,z in group.v]
for group in [frames,glass]:
    group.v=[(x*TOWER_XY,y*TOWER_XY,z) if z>18 else (x,y,z) for x,y,z in group.v]
for group in [slabs,supports,ribs,frames,glass,detail]:group.finish(.035 if group in [supports,slabs] else 0)

landscape_meta={}
if not opt.architecture_only:
    import landscape
    landscape_meta=landscape.build_landscape() or {}

# CC0 scanned surface microdetail complements the editable procedural geometry.
# These are surface measurements, never reference photographs pasted on the model.
for m in bpy.data.materials:
    name=m.name.lower()
    asset='concrete_layers_02' if 'concrete' in name else ('brown_mud_dry' if ('soil' in name or 'dryearth' in name) else None)
    if not asset:continue
    p=m.node_tree.nodes.get('Principled BSDF')
    if not p:continue
    paths={channel:ROOT/'SourceAssets'/'Textures'/(asset+'_'+channel+'_1k.jpg') for channel in ['diff','rough','nor_gl']}
    if not all(path.exists() for path in paths.values()):continue
    ns={}
    for channel,path in paths.items():
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True)
        if channel!='diff':tex.image.colorspace_settings.name='Non-Color'
        tex.image.pack();ns[channel]=tex
    blend=m.node_tree.nodes.new('ShaderNodeMixRGB');blend.inputs[0].default_value=.58
    blend.inputs[1].default_value=m.diffuse_color
    m.node_tree.links.new(ns['diff'].outputs['Color'],blend.inputs[2]);m.node_tree.links.new(blend.outputs[0],p.inputs['Base Color'])
    m.node_tree.links.new(ns['rough'].outputs['Color'],p.inputs['Roughness'])
    normal=m.node_tree.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.45
    m.node_tree.links.new(ns['nor_gl'].outputs['Color'],normal.inputs['Color']);m.node_tree.links.new(normal.outputs[0],p.inputs['Normal'])

# NOAA reference: San Diego 2026-09-30 09:00 PDT, azimuth 113.6351,
# elevation 27.1371 degrees. A separate sun avoids double-counting the sky disc.
world=bpy.data.worlds.new('La Jolla coastal atmosphere'); scene.world=world;world.use_nodes=True
nodes=world.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputWorld');bg=nodes.new('ShaderNodeBackground')
sky=nodes.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_elevation=math.radians(27.137072);sky.sun_rotation=math.radians(90-113.635074)
sky.sun_disc=False
sky.altitude=.11;sky.air_density=1;sky.dust_density=.55;sky.ozone_density=1
bg.inputs['Strength'].default_value=.32
world.node_tree.links.new(sky.outputs['Color'],bg.inputs['Color']);world.node_tree.links.new(bg.outputs[0],out.inputs[0])
sun_data=bpy.data.lights.new('San Diego morning sun','SUN');sun_data.energy=2.5;sun_data.angle=math.radians(.53)
sun=bpy.data.objects.new('Sun / 2026-09-30 09:00 PDT',sun_data);bpy.context.collection.objects.link(sun)
az=math.radians(113.635074);elev=math.radians(27.137072)
direction=Vector((math.cos(elev)*math.sin(az),math.cos(elev)*math.cos(az),math.sin(elev)))
sun.rotation_euler=direction.to_track_quat('Z','Y').to_euler()

CAMERAS=[
    {'name':'01_SnakePath_Hero','position':[112,-30,18],'target':[22,0,21],'lens':34},
    {'name':'02_GardenOfEden','position':[87,-20,12.0],'target':[0,0,24],'lens':30},
    {'name':'03_SouthElevation','position':[75,-110,28],'target':[0,0,24],'lens':49},
    {'name':'04_SiteAerial','position':[173,-142,127],'target':[48,0,12],'lens':43},
    {'name':'05_SnakePath_Coil','position':[38,-24,34],'target':[66,-5,7],'lens':45},
    {'name':'06_SouthEntrance_Review','position':[13,-34,12.5],'target':[0,-23.9,9.2],'lens':34},
    {'name':'07_SnakeApproach_North_Review','position':[112,8,13],'target':[99,21,3],'lens':34},
    {'name':'08_SnakeApproach_South_Review','position':[115,-36,13],'target':[100,-47,3],'lens':34},
]
for spec in CAMERAS:
    data=bpy.data.cameras.new(spec['name']);cam=bpy.data.objects.new(spec['name'],data);bpy.context.collection.objects.link(cam)
    cam.location=spec['position'];cam.rotation_euler=(Vector(spec['target'])-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=spec['lens'];data.clip_end=1500
    if spec==CAMERAS[0]:scene.camera=cam

# World-scaled dominant-axis UVs. Procedural meshes need a valid UV channel for
# UE's mesh build and for optional real scanned surface maps.
def ensure_uv(ob):
    if ob.type!='MESH':return
    mesh=ob.data
    uv=mesh.uv_layers.active or mesh.uv_layers.new(name='SurfaceUV')
    for polygon in mesh.polygons:
        axis=max(range(3),key=lambda j:abs(polygon.normal[j]))
        axes=[j for j in range(3) if j!=axis]
        for li in polygon.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]*.5,co[axes[1]]*.5)
for ob in bpy.context.scene.objects:ensure_uv(ob)
# Save editable file before transient export conversion: all logical components and cameras retained.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SourceAssets'/'GeiselLibrary.blend'))
mesh_meta=[]
for ob in bpy.context.scene.objects:
    if ob.type in {'MESH','FONT','CURVE'}:
        ob.select_set(True)
    else:ob.select_set(False)
selected=list(bpy.context.selected_objects)
if selected:
    bpy.context.view_layer.objects.active=selected[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for ob in bpy.context.selected_objects:ensure_uv(ob)
for ob in bpy.context.selected_objects:
    if ob.type=='MESH':mesh_meta.append({'name':ob.name,'vertices':len(ob.data.vertices),'polygons':len(ob.data.polygons),'materials':[m.name for m in ob.data.materials if m]})
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SourceAssets'/'GeiselSite.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,global_scale=1,axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
bpy.ops.export_scene.gltf(filepath=str(ROOT/'SourceAssets'/'GeiselSite.glb'),export_format='GLB',use_selection=True,export_apply=True)
materials=[]
for m in bpy.data.materials:
    p=m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
    materials.append({'name':m.name,'base_color':list(m.diffuse_color[:3]),'roughness':p.inputs['Roughness'].default_value if p else .8,'metallic':p.inputs['Metallic'].default_value if p else 0})
manifest={'coordinate_system':'Blender metres: X East, Y North, Z up; UE X=x*100,Y=-y*100,Z=z*100','confirmed_dimensions':{'tower_height_m':33.528,'tower_floor6_span_m':60.96,'complex_overall_span_m':75.59,'snake_path_length_m':170.688,'snake_path_width_m':3.048},'plateau_elevation_m':10,'cameras':CAMERAS,'meshes':mesh_meta,'materials':materials,'landscape':landscape_meta,'limits':'Exterior reconstruction from public references. No surveyed mesh, as-built drawings or calibrated light capture; minor facade dimensions, planting and surrounding grades are approximations.'}
(ROOT/'SourceAssets'/'scene_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('GEISEL_SOURCE_EXPORT_COMPLETE',len(mesh_meta),'objects',sum(m['vertices'] for m in mesh_meta),'vertices',flush=True)
if opt.render:
    # Cycles CUDA/OptiX when available, otherwise safe CPU fallback.
    try:
        pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
        for device in pref.devices:device.use=device.type!='CPU'
        scene.cycles.device='GPU'
    except Exception as e:print('GPU setup:',e)
    preview_dir=ROOT/'.cache'/'previews'/'blender'
    preview_dir.mkdir(parents=True,exist_ok=True)
    for spec in [CAMERAS[0],CAMERAS[3],CAMERAS[4]]:
        scene.camera=bpy.data.objects[spec['name']];scene.render.filepath=str(preview_dir/(spec['name']+'.png'))
        bpy.ops.render.render(write_still=True)
    print('GEISEL_RENDER_COMPLETE',flush=True)
