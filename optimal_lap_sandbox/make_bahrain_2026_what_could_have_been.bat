@echo off
rem Bahrain (Sakhir) 2026 v2 "WHAT COULD HAVE BEEN" (2026-10-02) - satire: the 2026 Bahrain GP moved to Sepang.
rem v2 line = MIN-TIME line for the 2026 car (cache/bahrain/_opt_line_2026.py, corridor = road - 0.5 m),
rem knobs re-fitted ON that line by the unchanged autofit (cache/bahrain/_autofit_rl_in.py):
rem v2b (current): apex-touch line, cda 0.787 cl 3.639 rho 1.2242 -> 1:32.20, gate 8/9 (GAIN cap, as v1). v1 (1:32.186) files untouched,
rem backed up in cache/bahrain/v1_backup. Stage 1-3 regenerate the line (~10 min); stage 4 renders.
setlocal
set "ROOT=%~dp0"
set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "OUTLINE=%ROOT%F1_Pipeline_Assets\tracks\bahrain_grand_prix_outline.json"
set "BASE=%ROOT%cache\bahrain\v1_backup\bahrain_grand_prix_raceline.json"
set "RACELINE=%ROOT%F1_Pipeline_Assets\tracks\bahrain_grand_prix_raceline_v2.json"
set "ELEV=%ROOT%F1_Pipeline_Assets\tracks\bahrain_grand_prix_elevation.json"
set "CSV=%ROOT%F1_Pipeline_Assets\exports\bahrain_2026_v2_synthetic.csv"
set "V2=%ROOT%cache\bahrain\v2"
set "CLEAN=%ROOT%bahrain_2026_what_could_have_been_clean.mp4"
set "OUTMP4=%ROOT%bahrain_2026_what_could_have_been.mp4"
echo === Stage 1: min-time line (v1 knobs), refit knobs 0.777/4.200, re-polish (v2a) ===
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE%" --outline "%OUTLINE%" --cda 0.8005 --cl 4.4693 --rho 1.2242 --out "%V2%\opt" || exit /b 1
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE%" --outline "%OUTLINE%" --cda 0.777 --cl 4.200 --rho 1.2242 --steps 1,0.5,0.25 --init-knots "%V2%\opt_knots.npy" --out "%V2%\opt2" || exit /b 1
echo === Stage 2: inside-apex touch (user: line must hit every apex), margin 0.3, then knob fixed point (v2b) ===
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE%" --outline "%OUTLINE%" --cda 0.777 --cl 4.200 --rho 1.2242 --margin 0.3 --apex-w 0.3 --init-knots "%V2%\opt2_knots.npy" --out "%V2%\opt3" || exit /b 1
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE%" --outline "%OUTLINE%" --cda 0.777 --cl 4.200 --rho 1.2242 --margin 0.3 --apex-w 1.5 --steps 0.5,0.25 --init-knots "%V2%\opt3_knots.npy" --out "%V2%\opt4" || exit /b 1
"%PYTHON%" "%ROOT%cache\bahrain\_opt_line_2026.py" --base "%BASE%" --outline "%OUTLINE%" --cda 0.787 --cl 3.400 --rho 1.2242 --margin 0.3 --apex-w 1.5 --steps 1,0.5,0.25 --init-knots "%V2%\opt4_knots.npy" --out "%V2%\opt5" || exit /b 1
"%PYTHON%" "%ROOT%cache\bahrain\_autofit_rl_in.py" "%V2%\opt5_rl.json" --track bahrain || exit /b 1
copy /Y "%ROOT%cache\autofit_bahrain_sim.csv" "%CSV%" >nul
copy /Y "%ROOT%cache\autofit_bahrain_rl.json" "%RACELINE%" >nul
echo === Stage 3: checks ===
"%PYTHON%" "%ROOT%cache\_gate_2026.py" "%CSV%" 89.841 --targets "%ROOT%cache\predicted_bahrain.json"
"%PYTHON%" "%ROOT%cache\_check_ontrack.py" "%OUTLINE%" "%RACELINE%" bahrain_v2
echo === Stage 4: render - jets + tagline drawn INSIDE the render loop (one encode, same quality as every lap video) ===
"%PYTHON%" "%ROOT%raceline_video.py" --outline "%OUTLINE%" --raceline "%RACELINE%" --telemetry-csv "%CSV%" --track-name "Bahrain Grand Prix" --tagline "The lap that never was" --flights "b2:13,3.2,1240,1550,-160,300;sr71:58,2.6,-180,260,1260,1500" --zoom 18 --elevation-json "%ELEV%" --out "%ROOT%bahrain_grand_prix_2026_the_lap_that_never_was.mp4" || exit /b 1
echo DONE
