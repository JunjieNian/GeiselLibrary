param([string]$BlenderExe=$(if($env:GEISEL_BLENDER_EXE){$env:GEISEL_BLENDER_EXE}else{'D:\Blender\blender-4.5.13-windows-x64\blender.exe'}))
$ErrorActionPreference = 'Stop'
$geiselRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$geiselBlender = $BlenderExe
if (!(Test-Path -LiteralPath $geiselBlender)) { throw 'Blender 4.5 executable not found. Supply -BlenderExe with the blender.exe path.' }
$geiselPython = Join-Path (Split-Path -Parent $geiselBlender) '4.5\python\bin\python.exe'
$geiselPackages = Join-Path $geiselRoot 'work\blender_python'
if (!(Test-Path -LiteralPath (Join-Path $geiselPackages 'shapely-2.1.2.dist-info'))) {
    & $geiselPython -m pip install --disable-pip-version-check --no-deps --target $geiselPackages -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the Snake Path geometry dependency.' }
}
& $geiselBlender --background --python-exit-code 1 --python (Join-Path $PSScriptRoot 'build_scene.py') -- --render
if ($LASTEXITCODE -ne 0) { throw 'Blender scene generation failed; inspect the preceding error.' }
foreach ($geiselAudit in @('audit_scene.py','audit_snake_path.py')) {
    & $geiselBlender --background --python-exit-code 1 --python (Join-Path $PSScriptRoot $geiselAudit)
    if ($LASTEXITCODE -ne 0) { throw "Saved scene validation failed: $geiselAudit" }
}
Write-Host 'Editable Blender scene, FBX, GLB, manifest and previews regenerated.'
Write-Host 'Run Tools/Unreal/build_and_setup.ps1 to update the Unreal scene, then run its self-test.'
