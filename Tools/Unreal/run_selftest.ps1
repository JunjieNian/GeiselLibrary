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
Write-Output 'All runtime assertions passed. Captures: UnrealProject/Saved/Screenshots/Geisel.'
