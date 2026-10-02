param(
    [string]$UnrealRoot = $(if ($env:GEISEL_UNREAL_ROOT) { $env:GEISEL_UNREAL_ROOT } else { 'D:\EpicGames\UE_5.7' }),
    [string]$DesktopPath = [Environment]::GetFolderPath('Desktop')
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$UProject = Join-Path $ProjectRoot 'UnrealProject\GeiselExplorer.uproject'
$IconPath = Join-Path $ProjectRoot 'Assets\Branding\GeiselLibrary.ico'
$EngineExe = Join-Path $UnrealRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
if (-not (Test-Path -LiteralPath $EngineExe)) {
    $CommonRoot = Join-Path $env:ProgramFiles 'Epic Games\UE_5.7'
    $CommonExe = Join-Path $CommonRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
    if (Test-Path -LiteralPath $CommonExe) { $EngineExe = $CommonExe }
    else { throw 'Unreal Engine 5.7 not found. Supply -UnrealRoot with its installation folder.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'UnrealProject\Binaries\Win64\UnrealEditor-GeiselExplorer.dll'))) {
    throw 'Build the project first with Tools/Unreal/build_and_setup.ps1 -SkipSceneImport.'
}
if (-not (Test-Path -LiteralPath $UProject)) { throw 'GeiselExplorer.uproject not found.' }
if (-not (Test-Path -LiteralPath $IconPath)) { & (Join-Path $PSScriptRoot 'Build_Icon.ps1') }
if ([string]::IsNullOrWhiteSpace($DesktopPath)) { throw 'Windows Desktop location is unavailable.' }
New-Item -ItemType Directory -Path $DesktopPath -Force | Out-Null
$ShortcutPath = Join-Path $DesktopPath 'Geisel Library - Snake Path.lnk'
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
if ((Test-Path -LiteralPath $ShortcutPath) -and $Shortcut.Arguments -notlike ('*' + $UProject + '*')) {
    throw 'An unrelated shortcut already uses this name. Choose another desktop location.'
}
# Direct engine launch opens the experience without a console window.
$Shortcut.TargetPath = $EngineExe
$Shortcut.Arguments = '"{0}" /Game/Geisel/Maps/L_GeiselLibrary -game -windowed -ResX=1600 -ResY=900 -nosplash' -f $UProject
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.IconLocation = "$IconPath,0"
$Shortcut.Description = 'Explore UC San Diego Geisel Library and Snake Path: walking, flight, viewpoints and lighting.'
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Output "Desktop shortcut installed: $ShortcutPath"
