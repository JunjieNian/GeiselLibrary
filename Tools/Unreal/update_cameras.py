"""Correct explicit camera Euler components in existing level without geometry reimport."""
import unreal,json,math
from pathlib import Path
root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).parent
manifest=json.loads((root/'SourceAssets/scene_manifest.json').read_text())
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
levels.load_level('/Game/Geisel/Maps/L_GeiselLibrary')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for i,spec in enumerate(manifest['cameras']):
    p=spec['position']; t=spec['target'];d=[t[j]-p[j] for j in range(3)]
    rotation=unreal.Rotator(pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),yaw=math.degrees(math.atan2(-d[1],d[0])),roll=0)
    for a in actors:
        if a.actor_has_tag('View'+str(i+1)):
            unreal.log('[GEISEL_CAMERA] before '+str(a.get_actor_rotation()))
            a.set_actor_rotation(rotation,False)
            unreal.log('[GEISEL_CAMERA] after '+str(a.get_actor_rotation()))
            assert abs(a.get_actor_rotation().roll)<.001
levels.save_current_level()
unreal.log('[GEISEL_CAMERA] ALL_PASSED')
