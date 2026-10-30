@echo off
setlocal enabledelayedexpansion

rem ============================================================================
rem Mexico City GP 2026 optimal lap - PRE-FP1 (2026-10-30).
rem Track = user's cache\mexico\Autodromo_Hermanos_Rodriguez_2015.svg (parse copy
rem mexico_2015_parse.svg only drops a stray trailing "M" after Z). No API x/y.
rem Car: cda 0.75 cl 4.6 rho 0.9824 (2240 m) + env knobs (sim defaults unchanged):
rem   ICE_DERATE 0.035   turbo without MGU-H at altitude (first-principles estimate)
rem   SUPERCLIP_MEASURED real 2026 clip shape (cache\mexico\_superclip_study.py)
rem   MU_LONG 2.1        braking matched to 2025 Q brake zones (_brake_compare.py)
rem   GRIP_MAP           corner minima = 2025 Q x transfer (_fit_grip_map.py)
rem Sim lap 76.758; video label 77.265 by user decision (transfer says +1.5 s).
rem ============================================================================

set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "ROOT=%~dp0"
set "OUTLINE=%ROOT%F1_Pipeline_Assets\tracks\mexico_city_grand_prix_outline.json"
set "RACELINE=%ROOT%F1_Pipeline_Assets\tracks\mexico_city_grand_prix_raceline.json"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\mexico_2026_synthetic.csv"
set "ELEV=%ROOT%F1_Pipeline_Assets\tracks\mexico_city_grand_prix_elevation.json"
set "OUTMP4=%ROOT%mexico_city_grand_prix_2026_optimal_lap.mp4"

set ICE_DERATE=0.035
set SUPERCLIP_MEASURED=1
set MU_LONG=2.1
set "GRIP_MAP=1144:1244:1.1816;1222:1322:0.9768;1965:2065:1.0345;2023:2123:0.8520;2181:2281:0.9223;2514:2614:1.2513;2706:2806:1.2374;2865:2965:0.8598;3515:3615:0.8729;3699:3799:0.9492;3882:3982:0.9808"

echo === Sim on the approved line (fixed raceline) ===
"%PYTHON%" "%ROOT%sim_2026_lap.py" --outline "%OUTLINE%" --raceline-in "%ROOT%cache\autofit_mexico_rl.json" --raceline-out "%RACELINE%" --csv-out "%CSV%" --rho 0.9824 --cda 0.75 --cl 4.6
if errorlevel 2 goto :err

echo === Elevation (OpenF1 z only) ===
"%PYTHON%" "%ROOT%cache\mexico\_elevation_z_only.py"
if errorlevel 1 goto :err

echo === Render (zoom 28, label 1:17.265) ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "Mexico City Grand Prix" --zoom 28 --elevation-json "%ELEV%" --display-laptime 77.265 --out "%OUTMP4%"
if errorlevel 1 goto :err

echo Done. -^> %OUTMP4%
pause & exit /b 0

:err
echo FAILED with errorlevel %errorlevel%
pause & exit /b 1
