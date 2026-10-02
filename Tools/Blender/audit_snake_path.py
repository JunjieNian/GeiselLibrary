"""Regression check on the saved paving mesh, including its former broken coil."""
import bpy
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.cache'/'blender-python'))
from shapely import set_precision
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets'/'GeiselLibrary.blend'))
grout=bpy.data.objects['ART_SnakePath_DarkMortar'].data
polygons=[]
for face in grout.polygons:
    assert face.normal.z>0, 'Inverted paving face'
    shape=Polygon([tuple(grout.vertices[i].co[:2]) for i in face.vertices])
    assert shape.is_valid and shape.area>1e-10, 'Degenerate paving face'
    polygons.append(set_precision(shape,1e-5))
footprint=unary_union(polygons)
# Saved Blender vertices are float32. Snap only at 0.01 mm for this topology
# check so adjacent triangles agree after storage without hiding real gaps.
assert footprint.geom_type=='Polygon' and footprint.is_valid
assert len(footprint.interiors)==1, len(footprint.interiors)
garden=Polygon(footprint.interiors[0])
assert garden.contains(Point(67.2,-4.9))
assert garden.area>40
overlap=sum(p.area for p in polygons)-footprint.area
assert abs(overlap)<.002, overlap
manifest=json.loads((ROOT/'SourceAssets'/'scene_manifest.json').read_text())
probes=manifest['landscape']['coil_probe_points']
assert len(probes)>=30
assert all(footprint.covers(Point(p[:2])) for p in probes)
slate=bpy.data.objects['ART_SnakePath_HexagonalSlateScales'].data
assert all(face.normal.z>0 for face in slate.polygons)
slate_polygons=[Polygon([tuple(slate.vertices[i].co[:2]) for i in face.vertices]) for face in slate.polygons]
coil_review=box(55,-20,80,10)
coil_slate=[p.intersection(coil_review) for p in slate_polygons if p.intersects(coil_review)]
slate_union=unary_union(coil_slate)
slate_overlap=sum(p.area for p in coil_slate)-slate_union.area
assert slate_overlap<.005, ('Coincident slate surfaces at the coil contact',slate_overlap)
report={'status':'PASS','source':'Saved GeiselLibrary.blend paving meshes',
        'connected_paving_regions':1,'garden_openings':1,
        'garden_opening_area_m2':garden.area,'paving_area_m2':footprint.area,
        'overlapping_grout_area_m2':overlap,'upward_facing_slate_triangles':len(slate.polygons),
        'overlapping_coil_slate_area_m2':slate_overlap,
        'coil_centerline_probes':len(probes),'all_coil_probes_on_paving':True,
        'reference':'Stuart Collection smith-a-02.jpg and smith-a-01.jpg'}
(ROOT/'Docs'/'SnakePathValidation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GEISEL_SNAKE_PATH_AUDIT_PASS',json.dumps(report),flush=True)
