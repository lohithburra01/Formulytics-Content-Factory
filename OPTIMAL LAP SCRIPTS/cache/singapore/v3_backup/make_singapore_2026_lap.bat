@echo off
rem Singapore (Marina Bay) 2026 optimal lap - standard pre-FP1 transfer pipeline (2026-10-08).
rem SVG: Marina_Bay_circuit_2023.svg (4.2 seg/turn, post-2023 layout) @ 4940 m, 12 m, min R 10.
rem Marina Bay runs ANTICLOCKWISE; the engine drives CW -> sim on an x-mirrored outline and
rem un-mirror the raceline for the video (cache/_singapore_prep.py). S/F re-pinned +855 m
rem (speed-profile match corr 0.942 vs 2025 Q). Three drawn kinks relaxed (FITTED, default
rem knobs, rule: |resid| > 20 km/h): T1 sigma 24, 2653 m sigma 20, final corner sigma 32.
rem GAIN guard 36.3 via cache/_sim_singapore.py (real 2025 gain 23.9 = highest in the set).
setlocal
set "ROOT=%~dp0"
set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "T=%ROOT%F1_Pipeline_Assets\tracks"
set "OUTLINE=%T%\singapore_grand_prix_outline.json"
set "MIRROR=%T%\singapore_grand_prix_mirror_outline.json"
set "RACELINE=%T%\singapore_grand_prix_raceline.json"
set "MRACELINE=%T%\singapore_grand_prix_mirror_raceline.json"
set "REF25=%ROOT%F1_Pipeline_Assets\exports\reference_2025_singapore_q.csv"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\singapore_2026_synthetic.csv"
set "OUTMP4=%ROOT%singapore_grand_prix_2026_optimal_lap.mp4"
if not exist "%PYTHON%" (echo ERROR: Python not found at %PYTHON% & exit /b 1)
echo === Stage 0: 2025 Q reference ===
if not exist "%REF25%" "%PYTHON%" "%ROOT%fetch_openf1_lap.py" --year 2025 --country Singapore --session Qualifying --out "%REF25%"
echo === Stage 1: SVG -^> outline, S/F re-pin, corner relaxations, mirror ===
"%PYTHON%" "%ROOT%svg_to_outline.py" --svg "%ROOT%Marina_Bay_circuit_2023.svg" --out "%ROOT%cache\singapore_outline_autoSF.json" --track-length 4940 --road-width 12.0 --min-corner-radius 10.0 || exit /b 1
"%PYTHON%" "%ROOT%cache\_singapore_prep.py" prep || exit /b 1
copy /Y "%OUTLINE%" "%T%\singapore_grand_prix_outline_svgraw.json" >nul
"%PYTHON%" "%ROOT%cache\_outline_local_smooth.py" "%OUTLINE%" "%ROOT%cache\sg_relax_a.json" --near 617.4,375.5 --half 70 --sigma 24 || exit /b 1
"%PYTHON%" "%ROOT%cache\_outline_local_smooth.py" "%ROOT%cache\sg_relax_a.json" "%ROOT%cache\sg_relax_b.json" --near=-749.4,-198.8 --half 70 --sigma 20 || exit /b 1
"%PYTHON%" "%ROOT%cache\_outline_local_smooth.py" "%ROOT%cache\sg_relax_b.json" "%OUTLINE%" --near 635.7,-249.2 --half 100 --sigma 32 || exit /b 1
"%PYTHON%" "%ROOT%cache\_singapore_prep.py" mirror "%OUTLINE%" "%MIRROR%" || exit /b 1
echo === Stage 2: predict targets ===
"%PYTHON%" "%ROOT%cache\_predict_track.py" --track singapore || exit /b 1
echo === Stage 3: autofit cda/cl (registry inset 1.0, Singapore GAIN guard) ===
"%PYTHON%" "%ROOT%cache\_autofit_singapore.py" || exit /b 1
echo === Stage 3b: apex-touch line (user: line must touch every apex) + knob refit to a fixed point ===
rem v1 min-curvature line = the fixed base every knot vector below is measured from
set "BASE1=%ROOT%cache\singapore\base_v1_rl.json"
copy /Y "%ROOT%cache\autofit_singapore_rl.json" "%BASE1%" >nul
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE1%" --outline "%MIRROR%" --cda 0.570 --cl 4.171 --rho 1.2232 --margin 0.3 --apex-w 1.5 --out "%ROOT%cache\singapore\opt1" || exit /b 1
"%PYTHON%" "%ROOT%cache\singapore\_autofit_rl_in_sg.py" "%ROOT%cache\singapore\opt1_rl.json" || exit /b 1
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE1%" --outline "%MIRROR%" --cda 0.599 --cl 3.400 --rho 1.2232 --margin 0.3 --apex-w 1.5 --steps 1,0.5,0.25 --init-knots "%ROOT%cache\singapore\opt1_knots.npy" --out "%ROOT%cache\singapore\opt2" || exit /b 1
"%PYTHON%" "%ROOT%cache\singapore\_autofit_rl_in_sg.py" "%ROOT%cache\singapore\opt2_rl.json" || exit /b 1
rem v3 (user): T8 exit must cross back to the far side before T9 (RUS 2025). Pattern search was trapped
rem on the inside; a wide-entry seed is 0.04 s faster (pure lap) and the optimiser keeps it.
"%PYTHON%" "%ROOT%cache\singapore\_seed_wide.py" "%BASE1%" "%MIRROR%" "%ROOT%cache\singapore\opt2_knots.npy" "%ROOT%cache\singapore\seed_wide.npy" 2010 2140 0.8 || exit /b 1
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE1%" --outline "%MIRROR%" --cda 0.599 --cl 3.400 --rho 1.2232 --margin 0.3 --apex-w 1.5 --steps 1,0.5,0.25 --init-knots "%ROOT%cache\singapore\seed_wide.npy" --out "%ROOT%cache\singapore\opt3w" || exit /b 1
"%PYTHON%" "%ROOT%cache\singapore\_autofit_rl_in_sg.py" "%ROOT%cache\singapore\opt3w_rl.json" || exit /b 1
"%PYTHON%" "%ROOT%cache\singapore\_scan_crossings.py" "%BASE1%" "%MIRROR%" "%ROOT%cache\singapore\opt3w_rl.json"
copy /Y "%ROOT%cache\autofit_singapore_sim_best.csv" "%CSV%" >nul
copy /Y "%ROOT%cache\autofit_singapore_rl.json" "%MRACELINE%" >nul
"%PYTHON%" "%ROOT%cache\_singapore_prep.py" unmirror "%MRACELINE%" "%RACELINE%" || exit /b 1
echo === Stage 4: checks (GAIN median above fixed 28 gate cap - see cache/singapore_2026.md) ===
"%PYTHON%" "%ROOT%cache\_gate_2026.py" "%CSV%" 89.241 --targets "%ROOT%cache\predicted_singapore.json"
"%PYTHON%" "%ROOT%cache\_check_ontrack.py" "%OUTLINE%" "%RACELINE%" singapore
"%PYTHON%" "%ROOT%cache\_corner_compare.py" "%CSV%" "%REF25%" 4940
echo === Stage 5: render (no elevation flyover: flat street circuit) ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "Singapore Grand Prix" --zoom 28 --out "%OUTMP4%" || exit /b 1
echo DONE: %OUTMP4%
