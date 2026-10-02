@echo off
setlocal
set "PROJECT=%~dp0"
if not defined GEISEL_BLENDER_EXE set "GEISEL_BLENDER_EXE=D:\Blender\blender-4.5.13-windows-x64\blender.exe"
set "BLENDER=%GEISEL_BLENDER_EXE%"
if not exist "%BLENDER%" (
  echo Blender was not found at %BLENDER%
  echo Open SourceAssets\GeiselLibrary.blend in Blender 4.5 or newer.
  echo Or set GEISEL_BLENDER_EXE to your blender.exe path.
  pause
  exit /b 1
)
start "Geisel Library - editable scene" "%BLENDER%" "%PROJECT%SourceAssets\GeiselLibrary.blend"
