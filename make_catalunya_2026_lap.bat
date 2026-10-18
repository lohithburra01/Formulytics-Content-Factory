@echo off
setlocal enabledelayedexpansion

set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "ROOT=%~dp0"
set "SVG=%ROOT%Catalunya-2023.svg"
set "OUTLINE=%ROOT%F1_Pipeline_Assets\tracks\catalunya_grand_prix_outline.json"
set "RACELINE=%ROOT%F1_Pipeline_Assets\tracks\catalunya_grand_prix_raceline.json"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\catalunya_2026_synthetic.csv"
set "REFCSV=%ROOT%F1_Pipeline_Assets\exports\reference_2026_spain_q.csv"
set "OUTMP4=%ROOT%catalunya_grand_prix_2026_optimal_lap.mp4"

if not exist "%PYTHON%" goto :err_py
if not exist "%SVG%"    goto :err_svg

echo === Stage 1: SVG -^> outline (Catalunya 2023 layout, no chicane, 4657 m, 13.0 m wide) ===
"%PYTHON%" "%ROOT%svg_to_outline.py" --svg "%SVG%" --out "%OUTLINE%" --track-length 4657 --road-width 13.0 --min-corner-radius 9.0
if errorlevel 1 goto :err

echo === Stage 2: raceline + 2026 physics sim (active aero enabled, Canada-style) ===
rem REFCSV = real 2026 Catalunya FP1 (fetched via fetch_openf1_lap.py) -> auto-anchors
rem S/F to the real lap. Re-fetch with --session Qualifying to finalize against quali.
rem --inset 0: Catalunya has run-off, so the line uses the full track + kerbs
rem (Monaco keeps the default 1.0 for wall safety). Verified on-track at inset 0.
"%PYTHON%" "%ROOT%sim_2026_lap.py" --outline "%OUTLINE%" --raceline-out "%RACELINE%" --csv-out "%CSV%" --reference-csv "%REFCSV%" --inset 0
if errorlevel 1 goto :err

echo === Stage 3: render video ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "Spanish Grand Prix" --out "%OUTMP4%"
if errorlevel 1 goto :err

echo.
echo Done. -^> %OUTMP4%
pause & exit /b 0

:err_py
echo ERROR: Python not found at %PYTHON%
pause & exit /b 1

:err_svg
echo ERROR: SVG not found at %SVG%
pause & exit /b 1

:err
echo FAILED with errorlevel %errorlevel%
pause & exit /b 1
