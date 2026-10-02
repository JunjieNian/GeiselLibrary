@echo off
setlocal
if not defined GEISEL_UNREAL_ROOT set "GEISEL_UNREAL_ROOT=D:\EpicGames\UE_5.7"
if not exist "%GEISEL_UNREAL_ROOT%\Engine\Binaries\Win64\UnrealEditor.exe" if exist "%ProgramFiles%\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" set "GEISEL_UNREAL_ROOT=%ProgramFiles%\Epic Games\UE_5.7"
if not exist "%GEISEL_UNREAL_ROOT%\Engine\Binaries\Win64\UnrealEditor.exe" (
  echo Set GEISEL_UNREAL_ROOT to your Unreal Engine 5.7 installation folder.
  pause
  exit /b 1
)
start "Geisel Library Editor" "%GEISEL_UNREAL_ROOT%\Engine\Binaries\Win64\UnrealEditor.exe" "%~dp0UnrealProject\GeiselExplorer.uproject"
