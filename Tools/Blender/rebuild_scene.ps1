param([string]$BlenderExe=$(if($env:GEISEL_BLENDER_EXE){$env:GEISEL_BLENDER_EXE}else{'D:\Blender\blender-4.5.13-windows-x64\blender.exe'}))
$ErrorActionPreference = 'Stop'
$geiselRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$geiselBlender = $BlenderExe
if (!(Test-Path -LiteralPath $geiselBlender)) { throw 'Blender 4.5 executable not found. Supply -BlenderExe with the blender.exe path.' }
& $geiselBlender --background --python (Join-Path $PSScriptRoot 'build_scene.py') -- --render
if ($LASTEXITCODE -ne 0) { throw 'Blender scene generation failed; inspect the preceding error.' }
Write-Host 'Editable Blender scene, FBX, GLB, manifest and previews regenerated.'
Write-Host 'Run Tools/Unreal/build_and_setup.ps1 to update the Unreal scene, then run its self-test.'
