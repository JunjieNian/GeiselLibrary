# Geisel Library desktop icon

`GeiselLibrary_Icon.png` is the original generated artwork with transparent outer corners. `GeiselLibrary.ico` packages the same artwork at 16, 24, 32, 48, 64, 128 and 256 pixels for Windows desktop use.

The icon combines Geisel Library's stepped cantilever tower and inclined concrete piers with the hillside Snake Path. Warm concrete and golden-hour light contrast with blue glazing and a navy tile. It is a stylized project emblem, not a drawing for architectural measurements or an official UC San Diego logo.

Created on 2026-10-01 using Codex's built-in image generation tool, under the `imagegen` skill. The artwork was preserved; only resizing and ICO format packaging were applied. No API key or fallback CLI was used. See [generation-prompt.txt](generation-prompt.txt) for the complete prompt.

On Windows, after building the project, run `Tools/Windows/Install_DesktopShortcut.ps1` to install **Geisel Library - Snake Path** on the current user's Desktop. The shortcut opens the same saved Unreal experience as the main launcher, using the supplied icon and no console window. Supply `-UnrealRoot` if the engine is installed elsewhere.

`Tools/Windows/Build_Icon.ps1` recreates the ICO from the saved PNG. Both scripts derive the project location from their own path.
