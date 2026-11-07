@echo off
setlocal enabledelayedexpansion

rem ============================================================================
rem Sao Paulo GP (Interlagos) 2026 optimal lap - PRE-FP1 (2026-11-05). Mexico method.
rem Track = user's Autodromo_Jose_Carlos_Pace_(AKA_Interlagos)_track_map.svg (copy
rem cache\brazil\interlagos.svg), 4309 m, 13 m wide, R>=9. No API x/y.
rem ANTICLOCKWISE: sim on the x-mirrored outline, raceline un-mirrored for the video
rem (direction probe: mirrored corr 0.97-0.98 vs 2025 Q, as-drawn 0.61).
rem Car: autofit cda 0.643 cl 4.458 rho 1.1353 (785 m ISA) + env knobs:
rem   SUPERCLIP_MEASURED real 2026 clip shape   MU_LONG 2.1 (decel 1.01x 2025 Q)
rem   GRIP_MAP corner minima = 2025 Q x transfer (cache\brazil\_fit_grip_map.py)
rem No ICE_DERATE (785 m; Mexico's 0.035 was for 2240 m).
rem ============================================================================

set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "ROOT=%~dp0"
set "MIRR=%ROOT%F1_Pipeline_Assets\tracks\sao_paulo_grand_prix_mirror_outline.json"
set "OUTLINE=%ROOT%F1_Pipeline_Assets\tracks\sao_paulo_grand_prix_outline.json"
set "RL_M=%ROOT%cache\brazil\final_mirror_rl.json"
set "RACELINE=%ROOT%F1_Pipeline_Assets\tracks\sao_paulo_grand_prix_raceline.json"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\sao_paulo_2026_synthetic.csv"
set "REF=%ROOT%F1_Pipeline_Assets\exports\reference_2025_brazil_q.csv"
set "ELEV=%ROOT%F1_Pipeline_Assets\tracks\sao_paulo_grand_prix_elevation.json"
set "OUTMP4=%ROOT%sao_paulo_grand_prix_2026_optimal_lap.mp4"
if "%LABEL%"=="" set "LABEL=70.772"

set SUPERCLIP_MEASURED=1
set MU_LONG=2.1
set "GRIP_MAP=310:410:0.8963;414:514:1.2749;1344:1444:1.0554;2079:2179:0.9637;2274:2374:0.9743;2669:2769:1.0191;3153:3253:1.1377"

echo === Sim on the reviewed line (fixed raceline, mirrored frame) ===
"%PYTHON%" "%ROOT%sim_2026_lap.py" --outline "%MIRR%" --raceline-in "%ROOT%cache\brazil\line_v2_rl.json" --raceline-out "%RL_M%" --csv-out "%CSV%" --reference-csv "%REF%" --rho 1.1353 --cda 0.643 --cl 4.458
if errorlevel 2 goto :err

echo === Un-mirror raceline to the real (anticlockwise) track ===
"%PYTHON%" "%ROOT%cache\_singapore_prep.py" unmirror "%RL_M%" "%RACELINE%"
if errorlevel 1 goto :err

echo === Elevation (OpenF1 z only) ===
"%PYTHON%" "%ROOT%cache\brazil\_elevation_z_only.py"
if errorlevel 1 goto :err

echo === Render (zoom 20, user 2026-11-05) ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "Sao Paulo Grand Prix" --zoom 20 --elevation-json "%ELEV%" --display-laptime %LABEL% --tagline "ON A DRY TRACK" --out "%OUTMP4%" %EXTRA%
if errorlevel 1 goto :err

echo Done. -^> %OUTMP4%
exit /b 0

:err
echo FAILED with errorlevel %errorlevel%
exit /b 1
