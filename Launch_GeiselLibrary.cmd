@echo off
setlocal
if not defined GEISEL_UNREAL_ROOT set "GEISEL_UNREAL_ROOT=D:\EpicGames\UE_5.7"
if not exist "%GEISEL_UNREAL_ROOT%\Engine\Binaries\Win64\UnrealEditor.exe" if exist "%ProgramFiles%\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" set "GEISEL_UNREAL_ROOT=%ProgramFiles%\Epic Games\UE_5.7"
set "UE=%GEISEL_UNREAL_ROOT%\Engine\Binaries\Win64\UnrealEditor.exe"
if not exist "%UE%" (
  echo Unreal Engine 5.7 was not found. Set GEISEL_UNREAL_ROOT to its installation folder.
  echo See README.md for first-time setup.
  pause
  exit /b 1
)
if not exist "%~dp0UnrealProject\Binaries\Win64\UnrealEditor-GeiselExplorer.dll" (
  echo Build the C++ project first with Tools\Unreal\build_and_setup.ps1 -SkipSceneImport.
  echo See README.md for the full command and required tools.
  pause
  exit /b 1
)
start "Geisel Library" "%UE%" "%~dp0UnrealProject\GeiselExplorer.uproject" /Game/Geisel/Maps/L_GeiselLibrary -game -windowed -ResX=1600 -ResY=900 -nosplash
