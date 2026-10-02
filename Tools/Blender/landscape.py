"""Editable UC San Diego Geisel landscape and Alexis Smith's Snake Path.

Metres, Z up, X east, Y north; library centre is (0, 0), grade is 10 m.
This is a photo-guided reconstruction, not survey geometry.  The real work's
560 ft x 10 ft dimensions, slate palette, Eden planting and Milton book are
preserved.  The precise turns/terrain grades are inferred from public photos.
All visible details are mesh geometry and work without texture downloads.
"""
import bpy
import math
import random
import bisect
import sys
from pathlib import Path
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'.cache'/'blender-python'))
try:
    from shapely import constrained_delaunay_triangles, set_precision
    from shapely.geometry import Polygon, Point, box
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
except ImportError as exc:
    raise RuntimeError('Run Tools/Blender/rebuild_scene.ps1 to prepare the geometry dependencies.') from exc

SEED = 1992
PATH_WIDTH = 3.048
PATH_DESIGN_LENGTH = 170.688
PATH_POINTS = []
PATH_NORMALS = []
PATH_SURFACE_REPORT = {}
METADATA = {}
RNG = random.Random(SEED)
GARDEN_CENTER = (67.2, -4.9)
BOOK_POSITION = (86.3, 7.4)
COLLECTION = None
MATERIALS = {}


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x-a)/(b-a)))
    return t*t*(3.0-2.0*t)


def terrain_height(x, y):
    """Smooth walkable campus grade, including east-facing canyon shoulder."""
    east = smoothstep(34.0, 114.0, x)
    lateral = smoothstep(38.0, 155.0, abs(y))
    west = smoothstep(52.0, 162.0, -x)
    grade = 10.0 - 10.0*east - 3.2*lateral*(1.0-east) - 2.0*west
    noise_mask = smoothstep(38.0, 61.0, max(x, abs(y), -x))
    undulation = (0.24*math.sin(x*0.078+y*0.043)
                  +0.14*math.sin(y*0.14-x*0.093)
                  +0.05*math.sin(x*.41)*math.sin(y*.31))
    south_court = 3.7 * (1-smoothstep(10,16,abs(x))) * smoothstep(19,23,-y) * (1-smoothstep(30,42,-y))
    head_forum=(1-smoothstep(42,49,x))*(1-smoothstep(14,22,abs(y))) if x>30 else 0
    grade=grade*(1-head_forum)+10.0*head_forum
    return grade + undulation*noise_mask*(1-head_forum) - south_court


def material(name, color, roughness=0.78, noise=0.0, scale=10.0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=roughness
    if noise:
        tex=m.node_tree.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value=scale
        tex.inputs['Detail'].default_value=3.0
        bump=m.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=noise
        bump.inputs['Distance'].default_value=.065
        m.node_tree.links.new(tex.outputs['Fac'],bump.inputs['Height'])
        m.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    MATERIALS[name]=m
    return m


class MeshBatch:
    def __init__(self,name,mats):
        self.name=name; self.mats=mats
        self.verts=[]; self.faces=[]; self.indices=[]
    def face(self,verts,mi=0):
        n=len(self.verts)
        self.verts.extend(verts)
        self.faces.append(tuple(range(n,n+len(verts))))
        self.indices.append(mi)
    def cylinder(self,a,b,r1,r2=None,mi=0,sides=6):
        a=Vector(a); b=Vector(b)
        d=(b-a).normalized()
        helper=Vector((0,0,1)) if abs(d.z)<.9 else Vector((1,0,0))
        u=d.cross(helper).normalized();v=d.cross(u).normalized()
        if r2 is None:r2=r1
        n=len(self.verts)
        for p,r in ((a,r1),(b,r2)):
            for i in range(sides):
                q=p+(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides))*r
                self.verts.append(tuple(q))
        for i in range(sides):
            self.faces.append((n+i,n+(i+1)%sides,n+sides+(i+1)%sides,n+sides+i));self.indices.append(mi)
        self.faces.append(tuple(n+sides+i for i in range(sides)));self.indices.append(mi)
    def leaf(self,center,direction,length,width,mi=0):
        c=Vector(center);d=Vector(direction).normalized()
        u=d.cross(Vector((0,0,1)))
        if u.length<.01:u=Vector((1,0,0))
        else:u.normalize()
        # Editable lanceolate leaf, two triangles; dense botanical silhouettes without alpha cards.
        n=len(self.verts)
        self.verts.extend([tuple(c-d*length*.52),tuple(c+u*width*.5),
                           tuple(c+d*length*.48),tuple(c-u*width*.5+Vector((0,0,width*.07)))])
        for f in ((0,1,2),(0,2,3)):
            self.faces.append(tuple(n+j for j in f));self.indices.append(mi)
    def finish(self,smooth=False):
        if not self.faces:return None
        mesh=bpy.data.meshes.new(self.name+'_Mesh')
        mesh.from_pydata(self.verts,[],self.faces);mesh.update()
        obj=bpy.data.objects.new(self.name,mesh)
        COLLECTION.objects.link(obj)
        for m in self.mats:mesh.materials.append(m)
        for p,idx in zip(mesh.polygons,self.indices):
            p.material_index=idx;p.use_smooth=smooth
        return obj


def mesh_box(name,location,scale,mat,bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o=bpy.context.object;o.name=name;o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    COLLECTION.objects.link(o);o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Small worn stone edges','BEVEL');mod.width=bevel;mod.segments=2
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
        o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    return o


def catmull(points,steps=10):
    p=[Vector(q) for q in points]
    out=[]
    for i in range(len(p)-1):
        a=p[max(0,i-1)];b=p[i];c=p[i+1];d=p[min(len(p)-1,i+2)]
        for j in range(steps):
            t=j/steps;t2=t*t;t3=t2*t
            q=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t2+(-a+3*b-3*c+d)*t3)
            out.append((q.x,q.y))
    out.append(tuple(p[-1]));return out


def resample(points,spacing=.24):
    out=[points[0]];remain=spacing;a=Vector(points[0])
    for pp in points[1:]:
        b=Vector(pp);d=b-a;length=d.length
        while length>=remain and length>1e-7:
            a=a+d*(remain/length);out.append(tuple(a));remain=spacing
            d=b-a;length=d.length
        remain-=length;a=b
    if (Vector(out[-1])-Vector(points[-1])).length>.01:out.append(points[-1])
    return out


def make_path_points():
    # Photo smith-a-02.jpg and plan smith-a-01.jpg: the body curls around
    # Eden and touches itself tangentially on its west side. Follow the
    # bottom, east and top of the coil before continuing downhill; the old
    # reversed arc doubled back into two tight hairpins at this contact.
    # Image top is library/west; image right is north.
    trace=[(168,169),(174,189),(177,211),(174,229),(165,247),(160,266),
           (164,279),(177,287),(191,285),(202,277),(205,264),(199,251),
           (186,244),(172,246),(161,256),(158,270),(162,285),(170,302),(188,316),(201,339),
           (226,349),(250,350),(271,362),(284,382),(299,400),(305,424),
           (298,450),(291,472),(295,493),(296,516),(291,537),(293,559),(301,575)]
    raw=[(py-169,px-168) for px,py in trace]
    p=resample(catmull(raw,10),.8)
    length=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(p,p[1:]))
    ratio=PATH_DESIGN_LENGTH/length
    return [(40+x*ratio,-10+y*ratio) for x,y in p]


def path_distance(x,y):
    return min((x-p[0])**2+(y-p[1])**2 for p in PATH_POINTS[::4])**.5


def ribbon_point(s,t,path,cum):
    i=max(0,min(len(path)-2,bisect.bisect_right(cum,s)-1))
    seg=max(.00001,cum[i+1]-cum[i]);f=(s-cum[i])/seg
    a=path[i];b=path[i+1]
    # Interpolated vertex frames keep neighboring tiles continuous across
    # sample boundaries; a per-segment normal leaves cracks on curves.
    nx=PATH_NORMALS[i][0]*(1-f)+PATH_NORMALS[i+1][0]*f
    ny=PATH_NORMALS[i][1]*(1-f)+PATH_NORMALS[i+1][1]*f
    size=math.hypot(nx,ny);nx/=size;ny/=size
    x=a[0]+(b[0]-a[0])*f+nx*t;y=a[1]+(b[1]-a[1])*f+ny*t
    # Subtle convex snake back, around four centimetres across the width.
    z=terrain_height(x,y)+.085+.038*max(0,1-(t/(PATH_WIDTH*.5))**2)
    return (x,y,z)


def create_terrain(m):
    extent=170;step=.8;n=round(extent*2/step)
    verts=[];faces=[];indices=[]
    for j in range(n+1):
        y=-extent+j*step
        for i in range(n+1):
            x=-extent+i*step;verts.append((x,y,terrain_height(x,y)))
    for j in range(n):
        y=-extent+(j+.5)*step
        for i in range(n):
            x=-extent+(i+.5)*step;k=j*(n+1)+i
            faces.append((k,k+1,k+n+2,k+n+1))
            # Broad, soft variation rather than random checkerboard patches.
            field=math.sin(x*.075+y*.032)+.55*math.sin(y*.11-x*.053)
            idx=0 if field<-.40 else (1 if field<.82 else 2)
            if x<30 and abs(y)<48:idx=3
            indices.append(idx)
    mb=MeshBatch('LAND_Terrain_OrganicEastSlope',m)
    mb.verts=verts;mb.faces=faces;mb.indices=indices
    ob=mb.finish(smooth=True);ob['collision']='walkable terrain'
    ob['reconstruction']='Photo-guided smooth grade, not a surveyed elevation model'
    # A coarse continuous land skirt prevents the finite study site appearing
    # as an island against the lower sky hemisphere. It is context, not a campus survey.
    far=MeshBatch('LAND_DistantCampusGround_Context',[m[2]])
    rings=[-4000,-1800,-850,-420,-250,-170,170,250,420,850,1800,4000]
    for a,x in enumerate(rings[:-1]):
        for b,y in enumerate(rings[:-1]):
            xx,yy=rings[a+1],rings[b+1]
            if x==-170 and y==-170:continue
            def point(px,py):
                distance=max(abs(px),abs(py))
                z=terrain_height(px,py)+smoothstep(200,800,distance)*(3*math.sin(px*.002)+2*math.cos(py*.003)-3)
                return (px,py,z)
            far.face([point(x,y),point(xx,y),point(xx,yy),point(x,yy)])
    far.finish(smooth=True)


def polygon_surface(name,points,mat,lift=.06):
    mb=MeshBatch(name,[mat])
    # These polygons are convex, giving editable, clean pavement meshes.
    mb.face([(x,y,terrain_height(x,y)+lift) for x,y in points])
    return mb.finish()


def create_paving(m):
    # Forum is level with the original building podium; the concrete is fine-grained.
    mesh_box('LAND_EastLibraryForum',(34.5,0,9.93),(19,32,.22),m['concrete'],.04)
    mesh_box('LAND_SouthEntryPromenade_West',(-27.5,-40.5,9.94),(23,15,.23),m['concrete'],.035)
    mesh_box('LAND_SouthEntryPromenade_East',(27,-40.5,9.94),(24,15,.23),m['concrete'],.035)
    court=MeshBatch('LAND_SouthSunkenEntranceCourt_Ramp',[m['concrete']])
    for i in range(64):
        xx=-16+i*.5
        for j in range(56):
            yy=-48+j*.5
            court.face([(xx,yy,terrain_height(xx,yy)+.055),(xx+.5,yy,terrain_height(xx+.5,yy)+.055),
                        (xx+.5,yy+.5,terrain_height(xx+.5,yy+.5)+.055),(xx,yy+.5,terrain_height(xx,yy+.5)+.055)])
    court.finish()
    mesh_box('LAND_WestEntryPromenade',(-40,0,9.93),(15,78,.22),m['concrete'],.035)
    joints=MeshBatch('LAND_ConcreteExpansionJoints',[m['joint']])
    for x in range(26,44,4):
        joints.face([(x-.009,-16,10.046),(x+.009,-16,10.046),(x+.009,16,10.046),(x-.009,16,10.046)])
    for y in range(-16,17,4):
        joints.face([(25,y-.009,10.046),(44,y-.009,10.046),(44,y+.009,10.046),(25,y+.009,10.046)])
    for x in range(-36,40,4):
        if abs(x)<17:continue
        joints.face([(x-.009,-48,10.061),(x+.009,-48,10.061),(x+.009,-33,10.061),(x-.009,-33,10.061)])
    joints.finish()
    # Campus path at the foot: the snake's tail goes beneath this existing walk.
    mb=MeshBatch('LAND_WarrenMallExistingWalk',[m['concrete']])
    x=144.5
    for y in [i*.8-40 for i in range(155)]:
        mb.face([(x-2.5,y,terrain_height(x-2.5,y)+.09),
                 (x+2.5,y,terrain_height(x+2.5,y)+.09),
                 (x+2.5,y+.8,terrain_height(x+2.5,y+.8)+.09),
                 (x-2.5,y+.8,terrain_height(x-2.5,y+.8)+.09)])
    mb.finish()
    # Narrow clipped lawns immediately beside the snake head, as in the photos.
    turf=MeshBatch('LAND_ForumLawnWedges',[m['grass']])
    for side in (-1,1):
        for ix in range(20):
            x=39+ix*.5
            for iy in range(18):
                y=-10+side*(2.7+iy*.5)
                if path_distance(x,y)<2.0:continue
                if x>44+(.35*abs(y)):continue
                turf.face([(x,y,terrain_height(x,y)+.025),(x+.5,y,terrain_height(x+.5,y)+.025),
                           (x+.5,y+side*.5,terrain_height(x+.5,y+side*.5)+.025),
                           (x,y+side*.5,terrain_height(x,y+side*.5)+.025)])
    turf.finish()


def create_snake(m):
    global PATH_SURFACE_REPORT
    cum=[0.0]
    for a,b in zip(PATH_POINTS,PATH_POINTS[1:]):cum.append(cum[-1]+math.hypot(b[0]-a[0],b[1]-a[1]))
    mb=MeshBatch('ART_SnakePath_HexagonalSlateScales',m['slate'])
    mortar=MeshBatch('ART_SnakePath_DarkMortar',[m['mortar']])
    width=PATH_WIDTH*.5

    def half_width(s):
        return width*min(1.0,max(.06,(cum[-1]-s)/7))

    # The real coil contacts the adjacent body. Union the paving footprint
    # before making its surface, so it has one continuous boundary and one
    # garden opening instead of overlapping strips and false internal edges.
    cells=[]
    for i in range(len(PATH_POINTS)-1):
        s0,s1=cum[i:i+2];w0=half_width(s0);w1=half_width(s1)
        cells.append(set_precision(Polygon([ribbon_point(s0,-w0,PATH_POINTS,cum)[:2],
                              ribbon_point(s1,-w1,PATH_POINTS,cum)[:2],
                              ribbon_point(s1,w1,PATH_POINTS,cum)[:2],
                              ribbon_point(s0,w0,PATH_POINTS,cum)[:2]]),1e-6))
    assert all(cell.is_valid and cell.area>0 for cell in cells), 'Folded snake ribbon cell'
    footprint=unary_union(cells)
    assert footprint.geom_type=='Polygon' and footprint.is_valid, 'Snake paving must be connected'
    assert len(footprint.interiors)==1, 'Eden must be enclosed by one complete coil'
    garden=Polygon(footprint.interiors[0])
    assert garden.contains(Point(GARDEN_CENTER)), 'Eden planting must remain inside the coil'
    boundary=footprint.boundary
    tree=STRtree(cells)

    def surface_vertex(x,y,lift=0):
        # Use one height field on both arms at the contact, including the
        # original subtle crowned profile. This prevents depth flicker.
        d=min(width,boundary.distance(Point(x,y)))
        crown=.038*(1-(1-d/width)**2)
        return (x,y,terrain_height(x,y)+.085+crown+lift)

    def emit_surface(batch,shape,mi=0,lift=0):
        if shape.is_empty or shape.area<1e-9:return
        for triangle in constrained_delaunay_triangles(shape).geoms:
            xy=list(triangle.exterior.coords)[:-1]
            a,b,c=xy
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:
                xy.reverse()
            batch.face([surface_vertex(x,y,lift) for x,y in xy],mi)

    # Grout is tessellated in small ground-following cells; one large polygon
    # would bridge the hillside and clip through the terrain at the coil.
    minx,miny,maxx,maxy=footprint.bounds
    step=.45
    for ix in range(math.floor(minx/step),math.ceil(maxx/step)):
        for iy in range(math.floor(miny/step),math.ceil(maxy/step)):
            patch=box(ix*step,iy*step,(ix+1)*step,(iy+1)*step)
            if footprint.intersects(patch):
                emit_surface(mortar,footprint.intersection(patch),lift=-.012)
    mortar.finish()

    # Tight elongated hexagonal tessellation in curvilinear coordinates.
    r=.237;h=r*math.sqrt(3);dl=1.5*r
    row_count=int(cum[-1]/dl)+1
    for row in range(row_count):
        s=row*dl
        taper=1.0
        if s>cum[-1]-7:taper=max(.06,(cum[-1]-s)/7)
        for col in range(-5,6):
            t=(col+.5*(row%2))*h
            if abs(t)>width*taper+.20:continue
            st=[]
            for k in range(6):
                a=k*math.pi/3
                ss=s+math.cos(a)*r*.986
                tt=t+math.sin(a)*r*.986
                tt=max(-width*taper,min(width*taper,tt))
                ss=max(0,min(cum[-1],ss));st.append((ss,tt))
            if max(q[1] for q in st)-min(q[1] for q in st)<.005:continue
            # Charcoal rhombi down the back, sand/grey flanks, lightly variable slate.
            phase=(s%4.3)/4.3
            diamond=1.0-abs(phase-.5)*2
            dark=abs(t)<(.17+diamond*1.14)
            if dark:idx=RNG.choice([0,0,0,1])
            else:idx=RNG.choices([1,2,3,4],[.14,.42,.30,.14])[0]
            tile=Polygon([ribbon_point(ss,tt,PATH_POINTS,cum)[:2] for ss,tt in st])
            if tile.area<1e-8:continue
            if not tile.is_valid:tile=tile.buffer(0)
            tile=tile.intersection(footprint)
            # Earlier paving owns the contact region. Clip the returning
            # coil against that full strip (including its grout), not against
            # individual slate tiles, leaving no coincident surfaces.
            earlier=[cells[int(j)] for j in tree.query(tile,predicate='intersects')
                     if cum[int(j)+1]<s-PATH_WIDTH*3]
            if earlier:tile=tile.difference(unary_union(earlier))
            emit_surface(mb,tile,idx)
    tiles=mb.finish();tiles['artist']='Alexis Smith';tiles['work']='Snake Path (1992)'
    tiles['documented_dimensions_m']='170.688 long by 3.048 wide'
    tiles['pattern']='Three slate families: charcoal, warm grey and pale sandstone; elongated hexagon scales'
    # Steel/stone-dark perimeter is visually as restrained as the real narrow edge.
    edging=MeshBatch('ART_SnakePath_ThinDarkPerimeter',[m['edging']])
    for ring in [footprint.exterior,*footprint.interiors]:
        for a,b in zip(ring.coords, list(ring.coords)[1:]):
            edging.cylinder(surface_vertex(*a),surface_vertex(*b),.022,mi=0,sides=4)
    edging.finish()
    PATH_SURFACE_REPORT={'connected_paving_regions':1,'garden_openings':1,
                         'garden_opening_area_m2':garden.area,'paving_area_m2':footprint.area,
                         'surface_join':'unioned tangent coil; overlapping tiles clipped',
                         'reference':'smith-a-02.jpg and smith-a-01.jpg'}
    # Head broadens into the forum.  Eyes and tongue are inlaid flush with paving.
    head=MeshBatch('ART_SnakeHead_InlaidSlate',[m['slate'][2],m['slate'][0],m['slate'][3],m['head_red']])
    cx=40;cy=-10
    ring=[]
    for k in range(48):
        a=math.tau*k/48;x=cx+2.5*math.cos(a);y=cy+2.0*math.sin(a)
        ring.append((x,y,max(10.062,terrain_height(x,y)+.12)))
    center=(cx,cy,10.125)
    for k in range(48):head.face([center,ring[k],ring[(k+1)%48]],0 if k%5 else 2)
    # Rhombus nose and symmetrical almond eyes on the broad end.
    head.face([(38.45,-10,10.135),(39.7,-10.62,10.135),(40.45,-10,10.135),(39.7,-9.38,10.135)],3)
    for side in (-1,1):
        ec=(39.35,-10+side*1.05)
        outer=[(ec[0]-.55,ec[1],10.143),(ec[0],ec[1]-.28,10.143),
               (ec[0]+.48,ec[1],10.143),(ec[0],ec[1]+.28,10.143)]
        head.face(outer,3)
        head.face([(ec[0]-.29,ec[1],10.149),(ec[0],ec[1]-.14,10.149),
                   (ec[0]+.26,ec[1],10.149),(ec[0],ec[1]+.14,10.149)],2)
        head.face([(ec[0]-.13,ec[1],10.155),(ec[0],ec[1]-.11,10.155),
                   (ec[0]+.15,ec[1],10.155),(ec[0],ec[1]+.11,10.155)],1)
    head.finish()
    tongue=MeshBatch('ART_SnakeHead_RedForkedTongue',[m['head_red']])
    tongue.face([(37.8,-10.22,10.065),(37.8,-9.78,10.065),(34.6,-9.60,10.065),
                 (32.0,-8.92,10.065),(34.2,-9.98,10.065),(32.0,-11.08,10.065),
                 (34.6,-10.40,10.065)])
    tongue.finish()
    return cum[-1]


def add_text(name,body,loc,size,mat,rotation):
    curve=bpy.data.curves.new(name+'_Type','FONT');curve.body=body;curve.align_x='CENTER';curve.align_y='CENTER'
    curve.size=size;curve.space_line=1.12;curve.extrude=.0004;curve.bevel_depth=0
    obj=bpy.data.objects.new(name,curve);COLLECTION.objects.link(obj)
    obj.location=loc;obj.rotation_euler=rotation;obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.convert(target='MESH');obj.select_set(False)
    return obj


def create_book(m):
    x,y=BOOK_POSITION;z=terrain_height(x,y)
    mesh_box('ART_ParadiseLost_GraniteBook_PageBlock',(x,y,z+1.105),(.33,1.51,2.12),m['pages'],.028)
    cover=mesh_box('ART_ParadiseLost_GraniteBook_FrontCover',(x+.205,y,z+1.11),(.065,1.61,2.134),m['book'],.018)
    mesh_box('ART_ParadiseLost_GraniteBook_BackCover',(x-.205,y,z+1.11),(.065,1.61,2.134),m['book'],.018)
    mesh_box('ART_ParadiseLost_GraniteBook_Spine',(x,y-.776,z+1.11),(.46,.075,2.134),m['book'],.026)
    cover['inscription']='THEN WILT THOU NOT BE LOTH TO LEAVE THIS PARADISE, BUT SHALT POSSESS A PARADISE WITHIN THEE, HAPPIER FAR.'
    cover['author']='John Milton, Paradise Lost, Book XII'
    line=MeshBatch('ART_ParadiseLost_EngravedCoverVines',[m['inscription']])
    face_x=x+.241
    def pt(u,v):return (face_x,y+u,z+.065+v)
    # Double rectangular border and scrolling botanical stone inlay.
    for border in (.04,.075):
        u=.805-border;v=2.134-border
        corners=[pt(-u,border),pt(u,border),pt(u,v),pt(-u,v),pt(-u,border)]
        for a,b in zip(corners,corners[1:]):line.cylinder(a,b,.0045,sides=4)
    for sign in (-1,1):
        vine=[]
        for i in range(91):
            t=i/90
            u=sign*(.47+.095*math.sin(t*math.tau*2.5));v=.17+t*1.77
            vine.append(pt(u,v))
        for a,b in zip(vine,vine[1:]):line.cylinder(a,b,.0085,sides=4)
        for j in range(10):
            v=.26+j*.166;u=sign*(.47+.095*math.sin((v-.17)/1.77*math.tau*2.5))
            tip=pt(u+sign*.13,v+.1)
            mid=pt(u+sign*.075,v+.085)
            line.face([pt(u,v),pt(u+sign*.015,v+.093),tip,pt(u+sign*.12,v+.006)])
            # Small curled tendril at each alternating leaf.
            if j%2==0:
                arc=[]
                for k in range(18):
                    a=k/17*math.tau*1.1;r=.07*(1-k/23)
                    arc.append(pt(u-sign*.065+r*math.cos(a),v+.10+r*math.sin(a)))
                for a,b in zip(arc,arc[1:]):line.cylinder(a,b,.0035,sides=4)
    line.finish()
    rot=Matrix(((0,0,1),(1,0,0),(0,1,0))).to_euler()
    quote='THEN WILT THOU NOT\nBE LOTH TO LEAVE\nTHIS PARADISE,\nBUT SHALT POSSESS\nA PARADISE WITHIN\nTHEE, HAPPIER FAR'
    add_text('ART_ParadiseLost_MiltonInscription',quote,(face_x+.004,y,z+1.45),.075,m['inscription'],rot)
    # Fine page channels visible around the right edge.
    pages=MeshBatch('ART_ParadiseLost_CarvedPageLines',[m['page_line']])
    for i in range(12):
        xx=x-.15+i*.026
        pages.cylinder((xx,y+.758,z+.105),(xx,y+.758,z+2.10),.0025,sides=4)
    pages.finish()


def create_garden_details(m):
    # Eden is intimate: three stone benches, a shallow bird bath and stepping stones.
    # Garden centre reflects the rescaling applied to the documentary path length.
    path_loop=PATH_POINTS[30:230]
    gx,gy=GARDEN_CENTER
    for i,(bx,by,rz) in enumerate([(gx+1.8,gy+3.1,.3),(gx-2.1,gy-2.1,-.3),(gx+2.7,gy-2.2,2.6)]):
        bz=terrain_height(bx,by)
        seat=mesh_box('EDEN_CarvedStoneBench_%02d'%i,(bx,by,bz+.48),(1.65,.5,.16),m['gardenstone'],.045)
        seat.rotation_euler.z=rz
        for sign in (-1,1):
            dx=sign*.60*math.cos(rz);dy=sign*.60*math.sin(rz)
            mesh_box('EDEN_BenchSupport_%02d_%s'%(i,sign),(bx+dx,by+dy,bz+.21),(.20,.4,.42),m['gardenstone'],.02)
    stones=MeshBatch('EDEN_IrregularSteppingStones',[m['slate'][2],m['gardenstone']])
    for i in range(15):
        y=gy-4.5+i*.57;x=gx-1.2+math.sin(i*.46)*.6
        rr=RNG.uniform(.22,.40)
        points=[]
        for j in range(7):
            a=j*math.tau/7;r=rr*RNG.uniform(.8,1.2)
            xx=x+math.cos(a)*r;yy=y+math.sin(a)*r
            points.append((xx,yy,terrain_height(xx,yy)+.06))
        stones.face(points,i%2)
    stones.finish()
    bath=MeshBatch('EDEN_WeatheredBirdBath',[m['gardenstone']])
    bx,by=gx+.9,gy-1.0;bz=terrain_height(bx,by)
    bath.cylinder((bx,by,bz),(bx,by,bz+.68),.09,.13,sides=9)
    bath.cylinder((bx,by,bz+.67),(bx,by,bz+.76),.48,.49,sides=24)
    bath.finish()
    water=MeshBatch('EDEN_BirdBathWater',[m['water']])
    water.face([(bx+math.cos(i*math.tau/32)*.445,by+math.sin(i*math.tau/32)*.445,bz+.765) for i in range(32)])
    water.finish()


def make_eucalyptus(x,y,height,trunks,leaves,seed):
    rr=random.Random(seed);z=terrain_height(x,y)
    base=Vector((x,y,z));lean=Vector((rr.uniform(-1.4,1.4),rr.uniform(-1.4,1.4),height))
    spine=[base+lean*t+Vector((.15*math.sin(t*5),.12*math.sin(t*7),0)) for t in (0,.22,.48,.70,.9,1)]
    for j in range(len(spine)-1):
        r=height*.014*(1-j*.14)
        trunks.cylinder(spine[j],spine[j+1],r,r*.82,mi=j%3,sides=7)
    for branch in range(13):
        t=rr.uniform(.42,.91);a=rr.random()*math.tau
        start=base+lean*t
        radial=height*rr.uniform(.12,.26)*(1-.42*t)
        tip=start+Vector((math.cos(a)*radial,math.sin(a)*radial,height*rr.uniform(.045,.17)))
        mid=start.lerp(tip,.56)+Vector((0,0,.30))
        trunks.cylinder(start,mid,height*.0055,height*.0028,mi=branch%3,sides=5)
        trunks.cylinder(mid,tip,height*.0028,.018,mi=branch%3,sides=5)
        for twig in range(4):
            az=a+rr.uniform(-1.25,1.25)
            stem=mid.lerp(tip,rr.uniform(.4,1.0))
            end=stem+Vector((math.cos(az)*rr.uniform(.4,1.2),math.sin(az)*rr.uniform(.4,1.2),rr.uniform(-.15,.65)))
            trunks.cylinder(stem,end,.015,.006,mi=1,sides=4)
            for leaf in range(72):
                center=end+Vector((rr.gauss(0,.65),rr.gauss(0,.65),rr.gauss(0,.52)))
                azl=rr.random()*math.tau
                direction=(math.cos(azl)*.75,math.sin(azl)*.75,rr.uniform(-1,-.15))
                leaves.leaf(center,direction,rr.uniform(.35,.68),rr.uniform(.11,.22),rr.randrange(4))


def make_cypress(x,y,height,trunks,leaves,seed):
    rr=random.Random(seed);z=terrain_height(x,y)
    trunks.cylinder((x,y,z),(x,y,z+height),.10,.015,mi=1,sides=6)
    for i in range(1400):
        t=rr.random();a=rr.random()*math.tau
        radius=(.48*(math.sin(t*math.pi)**.6)+.03)*rr.random()**.5
        center=(x+math.cos(a)*radius,y+math.sin(a)*radius,z+.5+t*(height-.45))
        leaves.leaf(center,(math.cos(a)*.35,math.sin(a)*.35,1),rr.uniform(.35,.65),rr.uniform(.16,.28),4+rr.randrange(2))


def make_fruit_tree(x,y,height,trunks,leaves,seed):
    rr=random.Random(seed);z=terrain_height(x,y)
    trunks.cylinder((x,y,z),(x+.12,y,z+height*.62),.10,.044,mi=1,sides=7)
    for j in range(9):
        a=j*2.39996;start=Vector((x+.08,y,z+height*rr.uniform(.30,.55)))
        tip=Vector((x+math.cos(a)*height*.32,y+math.sin(a)*height*.32,z+height*rr.uniform(.65,.98)))
        trunks.cylinder(start,tip,.042,.009,mi=2,sides=5)
        for k in range(210):
            q=tip+Vector((rr.gauss(0,.45),rr.gauss(0,.45),rr.gauss(0,.40)))
            a2=rr.random()*math.tau
            leaves.leaf(q,(math.cos(a2),math.sin(a2),rr.uniform(-.4,.6)),rr.uniform(.22,.35),rr.uniform(.10,.18),6+rr.randrange(2))


def create_vegetation(m):
    trunks=MeshBatch('PLANTS_EucalyptusCypressFruit_TrunksBranches',m['bark'])
    leaves=MeshBatch('PLANTS_EucalyptusCypressFruit_IndividualLeaves',m['leaves'])
    # Asymmetric groves frame, rather than occlude, the important view from the snake.
    positions=[]
    for i in range(110):
        if i<34:
            x=RNG.uniform(47,153);y=RNG.choice((-1,1))*RNG.uniform(40,80)
        elif i<88:
            x=RNG.uniform(-90,-34);y=RNG.uniform(-80,80)
        else:
            x=RNG.uniform(-90,145);y=RNG.choice((-1,1))*RNG.uniform(96,153)
        positions.append((x,y,RNG.uniform(15,25)))
    for i,(x,y,h) in enumerate(positions):make_eucalyptus(x,y,h,trunks,leaves,1000+i)
    for i,(x,y,h) in enumerate([(65.2,-6.5,6.5),(68.5,-2.5,7.2),(70.1,-6.0,6.2),(66.5,-2.2,6.8)]):
        make_cypress(x,y,h,trunks,leaves,2000+i)
    for i,(x,y,h) in enumerate([(65.5,-4.0,4.3),(68.2,-5.5,4.1),(69,-2.8,3.8)]):
        make_fruit_tree(x,y,h,trunks,leaves,2200+i)
    trunks.finish(smooth=True);leaves.finish()
    shrubs=MeshBatch('PLANTS_Chaparral_RosemarySageLeaves',m['shrubs'])
    twigs=MeshBatch('PLANTS_Chaparral_FineWoodyStems',[m['twig']])
    # Dry, planted eastern hillside; avoid the snake paving and podium explicitly.
    planted=[]
    for i in range(2400):
        x=RNG.uniform(43,163);y=RNG.uniform(-44,65)
        if path_distance(x,y)<2.2 or abs(x-144.5)<3.3:continue
        if x<49 and abs(y)<13:continue
        if (x-BOOK_POSITION[0])**2+(y-BOOK_POSITION[1])**2<3.5:continue
        height=RNG.uniform(.45,1.45);radius=RNG.uniform(.4,1.25)
        planted.append((x,y,height,radius))
    for i in range(130):
        a=RNG.random()*math.tau;r=RNG.uniform(1.7,5.5)
        x=GARDEN_CENTER[0]+math.cos(a)*r;y=GARDEN_CENTER[1]+math.sin(a)*r
        if path_distance(x,y)<2.15:continue
        if abs(x-(GARDEN_CENTER[0]-1.2))<.6:continue
        planted.append((x,y,RNG.uniform(.50,1.35),RNG.uniform(.3,.75)))
    for index,(x,y,height,radius) in enumerate(planted):
        z=terrain_height(x,y)
        for stem in range(7):
            a=RNG.random()*math.tau
            sx=x+math.cos(a)*radius*.15;sy=y+math.sin(a)*radius*.15
            tip=Vector((x+math.cos(a)*radius,y+math.sin(a)*radius,z+height*RNG.uniform(.65,1.0)))
            twigs.cylinder((sx,sy,z+.03),tip,.011,.003,sides=4)
            for j in range(9):
                t=.28+j*.078
                center=Vector((sx,sy,z)).lerp(tip,t)
                for sign in (-1,1):
                    az=a+sign*1.1
                    pp=center+Vector((math.cos(az)*radius*.19,math.sin(az)*radius*.19,.025))
                    shrubs.leaf(pp,(math.cos(az),math.sin(az),.45),RNG.uniform(.18,.35),RNG.uniform(.065,.13),index%len(m['shrubs']))
    twigs.finish();shrubs.finish()
    # Occasional agave / iris fans, visible in the photographed garden.
    agave=MeshBatch('PLANTS_Eden_IrisAgaveFans',[m['leaves'][1],m['leaves'][2]])
    for i in range(42):
        x=RNG.uniform(62,73);y=RNG.uniform(-10,1)
        if path_distance(x,y)<1.9:continue
        z=terrain_height(x,y)
        for k in range(11):
            a=k*2.399+.1*i;length=RNG.uniform(.4,.95)
            center=(x+math.cos(a)*length*.22,y+math.sin(a)*length*.22,z+length*.4)
            agave.leaf(center,(math.cos(a)*.55,math.sin(a)*.55,1),length,.06,i%2)
    agave.finish()


def create_site_details(m):
    b=MeshBatch('CAMPUS_DarkBronzeLightStandards',[m['metal']])
    lamps=MeshBatch('CAMPUS_LanternDiffusers',[m['lamp']])
    for x,y in [(48,17),(72,-30),(98,-29),(113,14),(112,-48),(-36,-51),(36,-51)]:
        z=terrain_height(x,y)
        b.cylinder((x,y,z),(x,y,z+3.8),.064,.05,sides=8)
        b.cylinder((x,y,z+3.8),(x,y,z+4.25),.12,.14,sides=8)
        lamps.cylinder((x,y,z+3.88),(x,y,z+4.19),.125,.12,sides=8)
        b.cylinder((x,y,z+4.23),(x,y,z+4.29),.20,.13,sides=8)
    b.finish(smooth=True);lamps.finish()
    # Curb-height retaining edges beside the lowered east footpath lawns.
    retaining=MeshBatch('CAMPUS_LowConcreteGardenEdges',[m['concrete']])
    for coords in [[(103,14),(96,14),(96,26),(107,26)],[(104,-43),(94,-43),(94,-53),(105,-53)]]:
        for a,bb in zip(coords,coords[1:]):
            za=terrain_height(*a);zb=terrain_height(*bb)
            retaining.face([(a[0],a[1],za),(bb[0],bb[1],zb),(bb[0],bb[1],zb+.32),(a[0],a[1],za+.32)])
    retaining.finish()


def build_landscape():
    global COLLECTION,PATH_POINTS,PATH_NORMALS,METADATA,RNG
    RNG=random.Random(SEED)
    COLLECTION=bpy.data.collections.get('02_Landscape_SnakePath')
    if COLLECTION is None:
        COLLECTION=bpy.data.collections.new('02_Landscape_SnakePath')
        bpy.context.scene.collection.children.link(COLLECTION)
    m={}
    m['soil']=[material('LAND_DrySandySoil',(0.35,.29,.19),noise=.32,scale=34),
               material('LAND_DryEarth_Warm',(0.39,.33,.23),noise=.28,scale=38),
               material('LAND_DryEarth_Cool',(0.30,.285,.22),noise=.27,scale=31),
               material('LAND_PlateauSubsoil',(.32,.30,.24),noise=.20)]
    m['concrete']=material('LAND_AgedWarmConcrete',(.57,.555,.49),.85,.14,44)
    m['joint']=material('LAND_ConcreteSeams',(.20,.195,.17),.95)
    m['grass']=material('LAND_ClippedLawn',(.21,.275,.055),.95,.25,110)
    m['mortar']=material('ART_SlateGrout',(.165,.16,.145),.94)
    m['edging']=material('ART_SnakeDarkEdge',(.10,.105,.095),.80)
    m['slate']=[material('ART_Slate_Charcoal',(.125,.15,.16),.88,.14,50),
                material('ART_Slate_BlueGrey',(.29,.325,.32),.85,.14,52),
                material('ART_Slate_WarmGrey',(.49,.465,.39),.85,.15,55),
                material('ART_Slate_PaleSand',(.66,.625,.50),.88,.14,54),
                material('ART_Slate_OliveGrey',(.41,.43,.34),.88,.14,48)]
    m['head_red']=material('ART_SnakeTerracottaInlay',(.32,.205,.155),.8)
    m['book']=material('ART_ParadiseLost_RedGranite',(.34,.205,.15),.66,.19,72)
    m['pages']=material('ART_ParadiseLost_StonePages',(.54,.51,.43),.76,.13,80)
    m['page_line']=material('ART_ParadiseLost_PageGrooves',(.25,.25,.21),.95)
    m['inscription']=material('ART_ParadiseLost_PaleEngraving',(.69,.64,.52),.82)
    m['gardenstone']=material('EDEN_WeatheredStone',(.42,.44,.38),.87,.19,39)
    m['water']=material('EDEN_ShallowBirdBathWater',(.13,.18,.09),.24)
    m['bark']=[material('PLANT_Eucalyptus_SilverBark',(.43,.425,.35)),
               material('PLANT_Eucalyptus_PeelingTanBark',(.32,.28,.20)),
               material('PLANT_Eucalyptus_DarkBark',(.21,.205,.16))]
    m['leaves']=[material('PLANT_Eucalyptus_LeafGreyOlive',(.22,.275,.145)),
                 material('PLANT_Eucalyptus_LeafSilverSage',(.33,.38,.23)),
                 material('PLANT_Eucalyptus_LeafDeepGreen',(.13,.215,.12)),
                 material('PLANT_Eucalyptus_LeafWarmOlive',(.30,.31,.12)),
                 material('PLANT_Cypress_LeafDark',(.07,.135,.055)),
                 material('PLANT_Cypress_LeafLight',(.17,.225,.08)),
                 material('PLANT_FruitTree_Leaf',(.20,.285,.105)),
                 material('PLANT_FruitTree_LeafLight',(.32,.37,.145))]
    m['shrubs']=[material('PLANT_Chaparral_Sage',(.34,.36,.205)),
                 material('PLANT_Chaparral_Rosemary',(.22,.28,.14)),
                 material('PLANT_Chaparral_DryGold',(.39,.355,.16)),
                 material('PLANT_Chaparral_DeepOlive',(.19,.235,.09))]
    m['twig']=material('PLANT_ShrubTwigs',(.245,.215,.145))
    m['metal']=material('CAMPUS_DarkBronze',(.12,.14,.13),.47)
    m['lamp']=material('CAMPUS_LanternOpal',(.78,.765,.63),.5)
    PATH_POINTS=make_path_points()
    PATH_NORMALS=[]
    for i,p in enumerate(PATH_POINTS):
        a=PATH_POINTS[max(0,i-1)];b=PATH_POINTS[min(len(PATH_POINTS)-1,i+1)]
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
        PATH_NORMALS.append((-dy/length,dx/length))
    create_terrain(m['soil'])
    create_paving(m)
    length=create_snake(m)
    create_book(m)
    create_garden_details(m)
    create_vegetation(m)
    create_site_details(m)
    METADATA={
        'source':'UCSD Stuart Collection official Snake Path photographs, Main_smith-a-01..06.jpg',
        'artist':'Alexis Smith','year':1992,'documented_length_m':PATH_DESIGN_LENGTH,
        'modeled_centerline_plan_length_m':length,'documented_width_m':PATH_WIDTH,
        'paving_validation':PATH_SURFACE_REPORT,
        'terrain_is_surveyed':False,'garden_center':(*GARDEN_CENTER,terrain_height(*GARDEN_CENTER)),
        'book_position':(*BOOK_POSITION,terrain_height(*BOOK_POSITION)),
        'camera_viewpoints':{
            'Snake_Path_Library_Hero':{'location':(92,-29,terrain_height(92,-29)+2.2),'target':(0,0,27)},
            'Garden_Of_Eden':{'location':(82,-4,terrain_height(82,-4)+1.75),'target':(0,0,28)},
            'Snake_Head':{'location':(31,-3,11.7),'target':(43,-10,10.1)},
            'Paradise_Lost':{'location':(BOOK_POSITION[0]+5,BOOK_POSITION[1]+1,terrain_height(*BOOK_POSITION)+1.65),'target':(*BOOK_POSITION,terrain_height(*BOOK_POSITION)+1.2)},
            'East_Aerial':{'location':(145,-103,82),'target':(22,-3,18)}},
        'walk_start':(145,28,terrain_height(145,28)+1.7),
        'coil_probe_points':[(x,y,terrain_height(x,y)+.1) for x,y in PATH_POINTS[::4] if 60<x<75],
        'path_points':[(x,y,terrain_height(x,y)+.1) for x,y in PATH_POINTS[::4]]}
    COLLECTION['documentation']='Official dimensions, photo-guided path turns and landform; editable mesh reconstruction.'
    print('LANDSCAPE_COMPLETE',len(COLLECTION.objects),'objects',round(length,3),'m snake centreline')
    return METADATA


if __name__=='__main__':
    build_landscape()
