@echo off
setlocal enabledelayedexpansion

rem ============================================================================
rem Italian GP 2026 (Monza) optimal lap - PRE-FP1 pipeline (zero 2026-session
rem data). Calibration: the track's own 2025 Q lap + the empirical 2025->2026
rem transfer (docs/2026-07-15-prefp1-universal-calibration-design.md).
rem The 2026 sessions are used only to VERIFY, never to fit.
rem
rem VIDEO: 3D ELEVATION flyover (--elevation-json), NOT the Zandvoort banking
rem cross-section. Monza is flat-to-gently-rolling and has no banked corner:
rem do not pass --banking-json here, it REPLACES the elevation band.
rem
rem NOTE: "Italy" resolves to TWO circuits in OpenF1 (Imola 2025 + Monza), so
rem every session lookup passes --circuit Monza.
rem ============================================================================

set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "ROOT=%~dp0"
set "SVG=%ROOT%Monza_track_map.svg"
set "OUTLINE=%ROOT%F1_Pipeline_Assets\tracks\italian_grand_prix_outline.json"
set "RACELINE=%ROOT%F1_Pipeline_Assets\tracks\italian_grand_prix_raceline.json"
set "ELEV=%ROOT%F1_Pipeline_Assets\tracks\italian_grand_prix_elevation.json"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\monza_2026_synthetic.csv"
set "REF25=%ROOT%F1_Pipeline_Assets\exports\reference_2025_monza_q.csv"
set "OUTMP4=%ROOT%italian_grand_prix_2026_optimal_lap.mp4"

rem 2025 Monza pole, seconds - VER lap 17, OpenF1 session_key 9908, fetched
rem the first real run. The gate's hard rail (2026 lap > 2025 pole + 0.8 s) is
rem meaningless with a wrong value, so the run stops rather than guess.
set "POLE25=78.792"

if not exist "%PYTHON%" goto :err_py
if not exist "%SVG%"    goto :err_svg

echo === Stage 0: 2025 Monza Q reference (FastF1 broken upstream; OpenF1) ===
if not exist "%REF25%" "%PYTHON%" "%ROOT%fetch_openf1_lap.py" --year 2025 --country "Italy" --circuit "Monza" --session "Qualifying" --out "%REF25%"
if not exist "%REF25%" goto :err_ref

echo === Stage 1: SVG -^> outline (5793 m, 14.0 m wide, R_min 9.0) ===
"%PYTHON%" "%ROOT%svg_to_outline.py" --svg "%SVG%" --out "%OUTLINE%" --track-length 5793 --road-width 14.0 --min-corner-radius 9.0
if errorlevel 1 goto :err
"%PYTHON%" "%ROOT%cache\_verify_outline.py" "%OUTLINE%"
if errorlevel 1 goto :err

echo === Stage 2: predict 2026 targets from 2025 ref + transfer ===
"%PYTHON%" "%ROOT%cache\_predict_track.py" --track monza
if errorlevel 1 goto :err

echo === Stage 3: autofit cda/cl to targets (runs the 2026 sim internally) ===
"%PYTHON%" "%ROOT%cache\_autofit_2026.py" --track monza
if errorlevel 2 goto :err
copy /Y "%ROOT%cache\autofit_monza_sim.csv" "%CSV%" >nul
copy /Y "%ROOT%cache\autofit_monza_rl.json" "%RACELINE%" >nul

echo === Stage 4: realism gate (predicted bands; 2025 pole %POLE25%) ===
if "%POLE25%"=="" goto :err_pole
"%PYTHON%" "%ROOT%cache\_gate_2026.py" "%CSV%" %POLE25% --targets "%ROOT%cache\predicted_monza.json"
if errorlevel 1 goto :err

echo === Stage 4b: real elevation from the OpenF1 z-channel (needs raceline) ===
if not exist "%ELEV%" "%PYTHON%" "%ROOT%cache\_fetch_elevation.py" --track monza --circuit "Monza"
if not exist "%ELEV%" goto :err_elev

echo === Stage 5: render video (3D elevation flyover; honest sim lap on HUD) ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "Italian Grand Prix" --zoom 30 --elevation-json "%ELEV%" --out "%OUTMP4%"
if errorlevel 1 goto :err

echo === Stage 6: standalone interactive 3D viewer (optional, offline HTML) ===
"%PYTHON%" "%ROOT%cache\_build_3d_viewer.py" --track monza --name "Monza"

echo.
echo Done. -^> %OUTMP4%
pause & exit /b 0

:err_py
echo ERROR: Python not found at %PYTHON%
pause & exit /b 1

:err_svg
echo ERROR: SVG not found at %SVG%  (drop the densest Monza SVG you can find there)
pause & exit /b 1

:err_ref
echo ERROR: no 2025 Monza Q reference at %REF25%
echo        OpenF1 returns 401 for EVERYTHING while any F1 session is live -
echo        re-run stage 0 once the current session has ended.
pause & exit /b 1

:err_pole
echo ERROR: POLE25 is unset - put the 2025 Monza pole time (seconds) at the top
echo        of this file first; the gate rail depends on it.
pause & exit /b 1

:err_elev
echo ERROR: elevation json not built (OpenF1 401 while a session is live?)
pause & exit /b 1

:err
echo FAILED with errorlevel %errorlevel%
pause & exit /b 1
