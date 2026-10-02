using UnrealBuildTool;
public class GeiselExplorerEditorTarget : TargetRules
{
    public GeiselExplorerEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
        ExtraModuleNames.Add("GeiselExplorer");
    }
}
