@echo off
setlocal enabledelayedexpansion

rem ============================================================================
rem Dutch GP 2026 optimal lap - PRE-FP1 pipeline (zero 2026-session data).
rem Calibration: track's own 2025 Q lap + empirical 2025->2026 transfer
rem (docs/2026-07-15-prefp1-universal-calibration-design.md). FP1, once it
rem exists, is used only to VERIFY (fetch_openf1_lap.py + cache/_overlay_speed.py).
rem
rem KNOWN BIAS (documented, do not "fix" with grip knobs): Zandvoort's banked
rem corners (Hugenholtz T3, Arie Luyendyk T14, ~18 deg) raise the real cornering
rem load. The frozen 2026 physics has no banking term, so the sim is expected to
rem UNDER-speed those two apexes. That is a geometry/physics gap, not a CL knob.
rem ============================================================================

set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "ROOT=%~dp0"
set "SVG=%ROOT%Zandvoort.svg"
set "OUTLINE=%ROOT%F1_Pipeline_Assets\tracks\dutch_grand_prix_outline.json"
set "RACELINE=%ROOT%F1_Pipeline_Assets\tracks\dutch_grand_prix_raceline.json"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\zandvoort_2026_synthetic.csv"
set "REF25=%ROOT%F1_Pipeline_Assets\exports\reference_2025_zandvoort_q.csv"
set "OUTMP4=%ROOT%dutch_grand_prix_2026_optimal_lap.mp4"
set "ELEV=%ROOT%F1_Pipeline_Assets\tracks\dutch_grand_prix_elevation.json"

if not exist "%PYTHON%" goto :err_py
if not exist "%SVG%"    goto :err_svg

echo === Stage 0: 2025 Zandvoort Q reference (FastF1 broken upstream; OpenF1) ===
rem non-fatal if offline; the existing CSV is reused (PIA 68.662s pole)
if not exist "%REF25%" "%PYTHON%" "%ROOT%fetch_openf1_lap.py" --year 2025 --country "Netherlands" --session "Qualifying" --out "%REF25%"

echo === Stage 1: SVG -^> outline (4259 m, 14.0 m wide, R_min 9.0) ===
"%PYTHON%" "%ROOT%svg_to_outline.py" --svg "%SVG%" --out "%OUTLINE%" --track-length 4259 --road-width 14.0 --min-corner-radius 9.0
if errorlevel 1 goto :err

echo === Stage 2: predict 2026 targets from 2025 ref + transfer ===
"%PYTHON%" "%ROOT%cache\_predict_track.py" --track zandvoort
if errorlevel 1 goto :err

echo === Stage 3: autofit cda/cl to targets (runs the 2026 sim internally) ===
"%PYTHON%" "%ROOT%cache\_autofit_2026.py" --track zandvoort
if errorlevel 2 goto :err
copy /Y "%ROOT%cache\autofit_zandvoort_sim.csv" "%CSV%" >nul
copy /Y "%ROOT%cache\autofit_zandvoort_rl.json" "%RACELINE%" >nul

echo === Stage 4: realism gate (predicted bands; 2025 pole 68.662) ===
"%PYTHON%" "%ROOT%cache\_gate_2026.py" "%CSV%" 68.662 --targets "%ROOT%cache\predicted_zandvoort.json"
if errorlevel 1 goto :err

echo === Stage 5: render video (honest sim lap time on the HUD) ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "Dutch Grand Prix" --zoom 30 --elevation-json "%ELEV%" --out "%OUTMP4%"
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
