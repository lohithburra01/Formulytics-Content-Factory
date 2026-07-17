@echo off
rem ============================================================================
rem Double-click to open the elevated 3D Spa toy in Blender, ready to orbit/scrub.
rem Uses --factory-startup (clean scene, skips your addons) so it always works.
rem Tune the look by editing the KNOBS at the top of elevation_3d_toy.py, then
rem re-run (Run Script in Blender, or just launch this .bat again).
rem ============================================================================
setlocal

set "BLENDER=C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
if not exist "%BLENDER%" set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
if not exist "%BLENDER%" set "BLENDER=C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
if not exist "%BLENDER%" set "BLENDER=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
if not exist "%BLENDER%" set "BLENDER=C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"

if not exist "%BLENDER%" (
    echo Could not find blender.exe under C:\Program Files\Blender Foundation\
    echo Edit this .bat and set BLENDER to your blender.exe path.
    pause
    exit /b 1
)

echo Launching Blender: "%BLENDER%"
start "" "%BLENDER%" --factory-startup --python "%~dp0_open_elevation_toy.py"
