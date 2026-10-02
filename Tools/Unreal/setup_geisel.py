"""Rebuild the editable UE scene from the Blender export and scene manifest.

Run using UnrealEditor-Cmd GeiselExplorer.uproject -ExecutePythonScript=... -RenderOffscreen.
No external libraries or downloaded assets are required.
"""
from pathlib import Path
import json
import math
import hashlib
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).parent
SOURCE = ROOT / "SourceAssets" / "GeiselSite.fbx"
MANIFEST = json.loads((ROOT / "SourceAssets" / "scene_manifest.json").read_text(encoding="utf-8"))
BASE = "/Game/Geisel"
LEVEL = BASE + "/Maps/L_GeiselLibrary"
ASSETS = unreal.AssetToolsHelpers.get_asset_tools()
EDIT = unreal.MaterialEditingLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TEXTURES = {}

def log(msg):
    unreal.log("[GEISEL_SETUP] " + str(msg))

def setprop(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as exc:
        log("Optional property {}: {}".format(name, exc))

def expr(mat, cls, x, y, **props):
    node = EDIT.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        node.set_editor_property(k, v)
    return node

def scalar(mat, name, value, y):
    return expr(mat, unreal.MaterialExpressionScalarParameter, -700, y,
                parameter_name=name, default_value=value)

def import_textures():
    for prefix in ("concrete_layers_02", "brown_mud_dry"):
        for role in ("diff", "rough", "nor_dx"):
            source=ROOT/"SourceAssets"/"Textures"/(prefix+"_"+role+"_1k.jpg")
            if not source.exists():
                continue
            task=unreal.AssetImportTask()
            task.set_editor_property("filename",str(source))
            task.set_editor_property("destination_path",BASE+"/Textures")
            task.set_editor_property("automated",True)
            task.set_editor_property("replace_existing",True)
            task.set_editor_property("save",True)
            ASSETS.import_asset_tasks([task])
            texture=unreal.EditorAssetLibrary.load_asset(BASE+"/Textures/"+source.stem)
            texture.set_editor_property("srgb",role=="diff")
            if role=="nor_dx":
                texture.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_NORMALMAP)
                texture.set_editor_property("flip_green_channel",False)
            elif role=="rough":
                texture.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_MASKS)
            unreal.EditorAssetLibrary.save_loaded_asset(texture)
            TEXTURES[(prefix,role)]=texture

def sample(mat, prefix, role, y):
    node=expr(mat,unreal.MaterialExpressionTextureSample,-1000,y,texture=TEXTURES[(prefix,role)])
    if role=="nor_dx":
        node.set_editor_property("sampler_type",unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    elif role=="rough":
        node.set_editor_property("sampler_type",unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    return node

def material(spec):
    name = "M_" + spec["name"]
    path = BASE + "/Materials/" + name
    mat = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if mat is None:
        mat = ASSETS.create_asset(name, BASE + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    EDIT.delete_all_material_expressions(mat)
    rgb = spec.get("base_color", [.5, .5, .5])[:3]
    color = expr(mat, unreal.MaterialExpressionVectorParameter, -700, 0,
                 parameter_name="SurfaceColor", default_value=unreal.LinearColor(*rgb, 1))
    roughness = scalar(mat, "Roughness", spec.get("roughness", .7), 180)
    metallic = scalar(mat, "Metallic", spec.get("metallic", 0), 280)
    specular = scalar(mat, "Specular", .65 if "Glass" in name else .35, 380)
    color_out = color
    texture_family="concrete_layers_02" if "concrete" in name.lower() else ("brown_mud_dry" if any(s in name.lower() for s in ("soil","sand","ground","earth","dry")) else None)
    foliage = any(s.lower() in name.lower() for s in ("leaf", "leaves", "foliage", "canopy", "grass", "chaparral"))
    textured = any(s.lower() in name.lower() for s in ("concrete", "soil", "sand", "gravel", "stone", "tile", "path", "bark", "trunk", "grass", "leaf", "leaves", "foliage", "canopy"))
    if textured:
        noise = expr(mat, unreal.MaterialExpressionNoise, -700, 520,
                     scale=.11 if "Concrete" in name else .035,
                     quality=1, levels=2, output_min=.76, output_max=1.08)
        color_out = expr(mat, unreal.MaterialExpressionMultiply, -320, 0)
        EDIT.connect_material_expressions(color, "", color_out, "A")
        EDIT.connect_material_expressions(noise, "", color_out, "B")
    EDIT.connect_material_property(color_out, "", unreal.MaterialProperty.MP_BASE_COLOR)
    EDIT.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
    EDIT.connect_material_property(metallic, "", unreal.MaterialProperty.MP_METALLIC)
    EDIT.connect_material_property(specular, "", unreal.MaterialProperty.MP_SPECULAR)
    if texture_family and (texture_family,"diff") in TEXTURES:
        diff=sample(mat,texture_family,"diff",-320)
        blend=expr(mat,unreal.MaterialExpressionLinearInterpolate,-280,-100,const_alpha=.38)
        EDIT.connect_material_expressions(color_out,"",blend,"A")
        EDIT.connect_material_expressions(diff,"RGB",blend,"B")
        EDIT.connect_material_property(blend,"",unreal.MaterialProperty.MP_BASE_COLOR)
        normal=sample(mat,texture_family,"nor_dx",-550)
        EDIT.connect_material_property(normal,"RGB",unreal.MaterialProperty.MP_NORMAL)
        rough=sample(mat,texture_family,"rough",-780)
        EDIT.connect_material_property(rough,"R",unreal.MaterialProperty.MP_ROUGHNESS)
    if foliage:
        mat.set_editor_property("two_sided", True)
        setprop(mat, "shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        EDIT.connect_material_property(color, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    if spec['name'].startswith('Light_') or spec['name']=='CAMPUS_LanternOpal':
        intensity = scalar(mat, "Emission", 3.5, 600)
        glow = expr(mat, unreal.MaterialExpressionMultiply, -280, 470)
        EDIT.connect_material_expressions(color, "", glow, "A")
        EDIT.connect_material_expressions(intensity, "", glow, "B")
        EDIT.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if spec['name'] in ('Glass_Reflective_01','Glass_Reflective_03'):
        # Subtle occupied interior glow; negligible next to physical daylight,
        # visible through selected glazing at twilight. No glowing concrete/foliage.
        glow_color=expr(mat,unreal.MaterialExpressionConstant3Vector,-300,740,constant=unreal.LinearColor(.32,.23,.12,1))
        EDIT.connect_material_property(glow_color,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    EDIT.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat

def import_meshes():
    # Pin the mature FBX importer: its absolute transform contract is stable.
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    data = options.get_editor_property("static_mesh_import_data")
    for key, value in {"combine_meshes":False, "auto_generate_collision":False,
                       "generate_lightmap_u_vs":False, "transform_vertex_to_absolute":True,
                       "convert_scene":True, "convert_scene_unit":True,
                       "force_front_x_axis":False, "import_uniform_scale":1.0}.items():
        data.set_editor_property(key, value)
    data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", BASE + "/Geometry")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    ASSETS.import_asset_tasks([task])
    meshes=[]
    for path in task.get_editor_property("imported_object_paths"):
        obj=unreal.EditorAssetLibrary.load_asset(path)
        if isinstance(obj, unreal.StaticMesh):
            meshes.append(obj)
    if not meshes:
        raise RuntimeError("FBX imported no StaticMesh objects")
    log("Imported {} mesh objects".format(len(meshes)))
    return meshes

def vec(p):
    return unreal.Vector(p[0]*100, -p[1]*100, p[2]*100)

def camera_rotation(position, target):
    delta = [target[i]-position[i] for i in range(3)]
    return unreal.Rotator(pitch=math.degrees(math.atan2(delta[2], math.hypot(delta[0],delta[1]))),
                          yaw=math.degrees(math.atan2(-delta[1],delta[0])),roll=0)

def spawn(cls, label, location=None, rotation=None):
    actor = ACTORS.spawn_actor_from_class(cls, location or unreal.Vector(), rotation or unreal.Rotator())
    actor.set_actor_label(label)
    actor.set_editor_property("tags", [unreal.Name("GeiselGenerated")])
    return actor

def build_level(meshes, materials):
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        levels.load_level(LEVEL)
    else:
        levels.new_level(LEVEL)
    for actor in ACTORS.get_all_level_actors():
        if actor.actor_has_tag("GeiselGenerated"):
            ACTORS.destroy_actor(actor)
    total_slots=0
    collision_count=0
    for mesh in meshes:
        name=mesh.get_name()
        for index, slot in enumerate(mesh.get_editor_property("static_materials")):
            slot_name=str(slot.get_editor_property("imported_material_slot_name"))
            if slot_name not in materials:
                slot_name=str(slot.get_editor_property("material_slot_name"))
            if slot_name not in materials:
                raise RuntimeError("Unmatched slot {} on {}".format(slot_name,name))
            mesh.set_material(index,materials[slot_name]);total_slots+=1
        collision=not any(word in name.lower() for word in ("vegetation", "foliage", "canopy", "grass", "eucalyptus", "tree", "shrub", "plants_"))
        body=mesh.get_editor_property("body_setup")
        if body:
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        nanite=mesh.get_editor_property("nanite_settings")
        nanite.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", nanite)
        actor=spawn(unreal.StaticMeshActor,name)
        component=actor.static_mesh_component
        component.set_static_mesh(mesh)
        component.set_collision_profile_name("BlockAll" if collision else "NoCollision")
        component.set_mobility(unreal.ComponentMobility.STATIC)
        if collision: collision_count+=1
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        log("MESH {} bounds={} collision={}".format(name, mesh.get_bounds(),collision))
    sun=spawn(unreal.DirectionalLight,"Pacific_Sun",unreal.Vector(0,0,15000),unreal.Rotator(pitch=-27.137072,yaw=-156.364926,roll=0))
    light=sun.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_editor_property("intensity",65000)
    light.set_editor_property("light_source_angle",1.1)
    light.set_editor_property("atmosphere_sun_light",True)
    setprop(light,"use_temperature",True)
    setprop(light,"temperature",5600)
    sky=spawn(unreal.SkyLight,"Pacific_Skylight")
    skylight=sky.get_component_by_class(unreal.SkyLightComponent)
    skylight.set_mobility(unreal.ComponentMobility.MOVABLE)
    skylight.set_editor_property("real_time_capture",True)
    skylight.set_editor_property("intensity",1.0)
    setprop(skylight,"lower_hemisphere_is_black",False)
    atmosphere=spawn(unreal.SkyAtmosphere,"Coastal_Atmosphere")
    atmosphere_component=atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent)
    setprop(atmosphere_component,"mie_scattering_scale",.009)
    setprop(atmosphere_component,"mie_anisotropy",.84)
    fog=spawn(unreal.ExponentialHeightFog,"Coastal_Haze",unreal.Vector(0,0,-900))
    fog_component=fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog_component.set_editor_property("fog_density",.002)
    fog_component.set_editor_property("fog_height_falloff",.2)
    setprop(fog_component,"volumetric_fog_enabled",True)
    setprop(fog_component,"fog_max_opacity",.65)
    setprop(fog_component,"start_distance",15000)
    cameras=MANIFEST["cameras"]
    for i, spec in enumerate(cameras[:4]):
        actor=spawn(unreal.TargetPoint,"View_"+spec["name"],vec(spec["position"]),camera_rotation(spec["position"],spec["target"]))
        actor.set_editor_property("tags",[unreal.Name("GeiselGenerated"),unreal.Name("View{}".format(i+1))])
    walk_spec=MANIFEST.get("landscape",{}).get("walk_start",[94,-3,3])
    walk=spawn(unreal.TargetPoint,"SnakePath_WalkStart",vec(walk_spec))
    walk.set_editor_property("tags",[unreal.Name("GeiselGenerated"),unreal.Name("WalkStart")])
    start=spawn(unreal.PlayerStart,"Visitor_Start",vec(cameras[0]["position"]))
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode",unreal.load_class(None,"/Script/GeiselExplorer.GeiselGameMode"))
    levels.save_current_level()
    unreal.EditorAssetLibrary.save_directory(BASE,only_if_is_dirty=False,recursive=True)
    report={"mesh_count":len(meshes),"material_count":len(materials),"bound_material_slots":total_slots,"collision_meshes":collision_count,"level":LEVEL,"source":str(SOURCE),"source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"camera_count":len(cameras[:4])}
    (ROOT/"UnrealProject"/"Saved"/"GeiselSetupReport.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    log("SETUP_COMPLETE "+json.dumps(report))

log("Root: "+str(ROOT))
unreal.SystemLibrary.execute_console_command(None, "Editor.AsyncStaticMeshCompilation 0")
if "-GeiselSkipImport" in unreal.SystemLibrary.get_command_line():
    mesh_objects=[unreal.EditorAssetLibrary.load_asset(path) for path in unreal.EditorAssetLibrary.list_assets(BASE+"/Geometry")]
    mesh_objects=[mesh for mesh in mesh_objects if isinstance(mesh,unreal.StaticMesh)]
else:
    mesh_objects=import_meshes()
import_textures()
material_map={spec["name"]:material(spec) for spec in MANIFEST["materials"]}
build_level(mesh_objects,material_map)
