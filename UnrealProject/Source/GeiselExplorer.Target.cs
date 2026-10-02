using UnrealBuildTool;
public class GeiselExplorerTarget : TargetRules
{
    public GeiselExplorerTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
        ExtraModuleNames.Add("GeiselExplorer");
    }
}
