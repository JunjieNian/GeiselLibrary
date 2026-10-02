param(
    [string]$UnrealRoot=$(if($env:GEISEL_UNREAL_ROOT){$env:GEISEL_UNREAL_ROOT}else{'D:\EpicGames\UE_5.7'}),
    [switch]$SkipSceneImport
)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$UProject=Join-Path $ProjectRoot 'UnrealProject\GeiselExplorer.uproject'
if(-not(Test-Path -LiteralPath (Join-Path $UnrealRoot 'Engine\Build\BatchFiles\Build.bat'))){throw 'Unreal Engine 5.7 was not found. Supply -UnrealRoot with its installation folder.'}
& (Join-Path $UnrealRoot 'Engine\Build\BatchFiles\Build.bat') GeiselExplorerEditor Win64 Development "-Project=$UProject" -WaitMutex -NoHotReloadFromIDE
if($LASTEXITCODE -ne 0){throw 'C++ build failed'}
if($SkipSceneImport){
    if(-not(Test-Path -LiteralPath (Join-Path $ProjectRoot 'UnrealProject\Content\Geisel\Maps\L_GeiselLibrary.umap'))){throw 'Saved map missing. Fetch Git LFS assets or rerun without -SkipSceneImport.'}
    Write-Output 'C++ build complete. Existing imported scene preserved; launch Launch_GeiselLibrary.cmd.'
    exit 0
}
& (Join-Path $UnrealRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe') $UProject "-ExecutePythonScript=$(Join-Path $PSScriptRoot 'setup_geisel.py')" -unattended -nop4 -nosplash -RenderOffscreen '-ExecCmds=r.AsyncStaticMeshCompilation 0,r.AsyncTextureCompilation 0'
if($LASTEXITCODE -ne 0){throw 'Scene setup failed'}
$Log=Join-Path $ProjectRoot 'UnrealProject\Saved\Logs\GeiselExplorer.log'
if(-not (Select-String -LiteralPath $Log -SimpleMatch '[GEISEL_SETUP] SETUP_COMPLETE' -Quiet)){throw 'Scene setup did not complete; inspect the Unreal log'}
Write-Output 'Geisel Library scene is ready.'
