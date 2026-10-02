"""Read-back audit of the actual saved Blender artifact, not generator constants."""
import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets'/'GeiselLibrary.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
slabs=bpy.data.objects['Building_FloorSlabs']
bounds=[slabs.matrix_world@Vector(v) for v in slabs.bound_box]
span=max(v.x for v in bounds)-min(v.x for v in bounds)
top=max(v.z for v in bounds)
assert abs(span-60.96)<.15,span
assert abs(top-43.528)<.4,top
assert len(objects)>=40,len(objects)
assert all(len(o.data.uv_layers)>0 for o in objects)
assert all(len(o.data.vertices)>0 and len(o.data.polygons)>0 for o in objects)
assert 'CAMPUS_LowConcreteGardenEdges' not in bpy.data.objects, 'Unsupported approach frames remain'
detail=bpy.data.objects['Building_GroundDetail']
for x in (-8,8):
    hit,*_=detail.ray_cast(Vector((x,-23.9,11.3)),Vector((0,0,-1)),distance=1.5)
    assert not hit, ('Floating south entrance bollard remains',x)
manifest=json.loads((ROOT/'SourceAssets'/'scene_manifest.json').read_text())
assert abs(manifest['landscape']['modeled_centerline_plan_length_m']-170.688)<.02
report={'status':'PASS','mesh_objects':len(objects),'triangles_before_modifiers':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects),'tower_floor6_span_m':span,'roof_elevation_m':top,'all_meshes_have_surface_uv':True,'snake_centerline_m':manifest['landscape']['modeled_centerline_plan_length_m'],'south_entrance_floating_bollards_absent':True,'unsupported_snake_approach_frames_absent':True,'source':'GeiselLibrary.blend reopened and inspected'}
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.clip_end=2000
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.region_3d.view_camera_zoom=0
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.shading.use_scene_world=True
            area.spaces.active.shading.use_scene_lights=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SourceAssets'/'GeiselLibrary.blend'))
(ROOT/'Docs'/'GeometryValidation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GEISEL_GEOMETRY_AUDIT_PASS',json.dumps(report),flush=True)
