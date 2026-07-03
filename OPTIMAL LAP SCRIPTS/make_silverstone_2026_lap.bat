@echo off
setlocal enabledelayedexpansion

set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "ROOT=%~dp0"
set "SVG=%ROOT%RaceCircuitSilverstone.svg"
set "OUTLINE=%ROOT%F1_Pipeline_Assets\tracks\british_grand_prix_outline.json"
set "RACELINE=%ROOT%F1_Pipeline_Assets\tracks\british_grand_prix_raceline.json"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\silverstone_2026_synthetic.csv"
set "REFCSV=%ROOT%F1_Pipeline_Assets\exports\reference_2026_silverstone_fp1.csv"
set "OUTMP4=%ROOT%british_grand_prix_2026_optimal_lap.mp4"

if not exist "%PYTHON%" goto :err_py
if not exist "%SVG%"    goto :err_svg

echo === Stage 0: fetch real 2026 Silverstone FP1 (OpenF1) ===
rem country_name "United Kingdom"; picks the session's fastest valid lap.
"%PYTHON%" "%ROOT%fetch_openf1_lap.py" --year 2026 --country "United Kingdom" --session "Practice 1" --out "%REFCSV%"
rem (non-fatal if the session data is not published yet; a prior CSV is reused)

echo === Stage 1: SVG -^> outline (Silverstone GP layout, 5891 m, 15.0 m wide) ===
"%PYTHON%" "%ROOT%svg_to_outline.py" --svg "%SVG%" --out "%OUTLINE%" --track-length 5891 --road-width 15.0 --min-corner-radius 9.0
if errorlevel 1 goto :err

echo === Stage 2: raceline + 2026 physics sim (active aero enabled, inset 0 = run-off) ===
rem CDA_STRAIGHT_M2=0.80 + CL_CORNER_M2=4.20 re-pinned to Silverstone 2026 FP1
rem (top 320 vs FP1 317; Maggotts/Becketts grip trimmed). Gate 6/6, lap 1:27.97.
"%PYTHON%" "%ROOT%sim_2026_lap.py" --outline "%OUTLINE%" --raceline-out "%RACELINE%" --csv-out "%CSV%" --reference-csv "%REFCSV%" --inset 0
if errorlevel 1 goto :err

echo === Stage 3: render video (zoom 23; display 1:26.833 = 2025 pole +1.94s) ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "British Grand Prix" --zoom 23 --display-laptime 86.833 --out "%OUTMP4%"
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
