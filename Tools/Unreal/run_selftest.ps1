param([string]$UnrealRoot=$(if($env:GEISEL_UNREAL_ROOT){$env:GEISEL_UNREAL_ROOT}else{'D:\EpicGames\UE_5.7'}))
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$UProject=Join-Path $ProjectRoot 'UnrealProject\GeiselExplorer.uproject'
$Log=Join-Path $ProjectRoot 'UnrealProject\Saved\Logs\GeiselSelfTest.log'
$Arguments=@('"'+$UProject+'"','/Game/Geisel/Maps/L_GeiselLibrary','-game','-GeiselSelfTest','-RenderOffscreen','-unattended','-nosound','-nosplash','-windowed','-ResX=1920','-ResY=1080','-ForceRes','-NoVSync',('-abslog="'+$Log+'"'))
$Process=Start-Process -FilePath (Join-Path $UnrealRoot 'Engine\Binaries\Win64\UnrealEditor.exe') -ArgumentList $Arguments -WindowStyle Hidden -PassThru
Write-Output "Geisel self-test process: $($Process.Id). Log: $Log"
$Process.WaitForExit()
if($Process.ExitCode -ne 0){throw 'Runtime self-test process failed'}
if(-not(Select-String -LiteralPath $Log -SimpleMatch '[GEISEL_SELFTEST] ALL_PASSED' -Quiet)){throw 'Runtime assertions did not all pass'}
$PreviewNames = [ordered]@{
    '01_East_Canyon_Daylight.png' = 'Library-Daylight.png'
    '03_East_Canyon_Golden_Hour.png' = 'Library-Golden-Hour.png'
    '04_Library_Plaza.png' = 'South-Elevation.png'
    '05_East_Canyon_Blue_Hour.png' = 'Library-Blue-Hour.png'
    '06_Interactive_Walk.png' = 'Walking.png'
    '07_Aerial_Site.png' = 'Site-Aerial.png'
    '08_Snake_Coil_Continuity.png' = 'Snake-Path.png'
}
$PreviewDirectory = Join-Path $ProjectRoot 'Previews'
New-Item -ItemType Directory -Path $PreviewDirectory -Force | Out-Null
foreach ($CaptureName in $PreviewNames.Keys) {
    $CapturePath = Join-Path $ProjectRoot (Join-Path 'UnrealProject\Saved\Screenshots\Geisel' $CaptureName)
    if(-not (Test-Path -LiteralPath $CapturePath)){throw "Runtime capture missing: $CaptureName"}
    Copy-Item -LiteralPath $CapturePath -Destination (Join-Path $PreviewDirectory $PreviewNames[$CaptureName]) -Force
}
Write-Output 'All runtime assertions passed. Curated runtime previews refreshed in Previews/.'
$ReviewNames = [ordered]@{
    '09_South_Entrance_Clearance.png' = 'South-Entrance.png'
    '10_Snake_Approach_North.png' = 'Snake-Approach-North.png'
    '11_Snake_Approach_South.png' = 'Snake-Approach-South.png'
}
$ReviewDirectory = Join-Path $ProjectRoot '.cache\validation\site-details'
New-Item -ItemType Directory -Path $ReviewDirectory -Force | Out-Null
foreach ($CaptureName in $ReviewNames.Keys) {
    $CapturePath = Join-Path $ProjectRoot (Join-Path 'UnrealProject\Saved\Screenshots\Geisel' $CaptureName)
    if(-not (Test-Path -LiteralPath $CapturePath)){throw "Detail review capture missing: $CaptureName"}
    Copy-Item -LiteralPath $CapturePath -Destination (Join-Path $ReviewDirectory $ReviewNames[$CaptureName]) -Force
}
Write-Output 'Entrance and Snake Path approach review captures refreshed in .cache/validation/site-details/.'
