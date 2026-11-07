@echo off
chcp 65001 >nul
rem Interlagos: HAMILTON 2018 POLE 1:07.281 (fastest lap ever at Interlagos; real F1IH trace, lap 16, own 2018-car line h18)
rem vs 2026 OPTIMAL LAP 1:10.772 (shipped CSV, stretched 0.05% to the label by _scale_2026.py). Anticlockwise track:
rem lines optimised in the mirrored frame, un-mirrored (h18_real_rl.json). Zoom 20 (user, 2026-11-05).
set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "H=%~dp0"
set "ROOT=%~dp0..\..\"
set "T=%ROOT%F1_Pipeline_Assets\tracks"
"%PYTHON%" "%ROOT%cache\era2017\dual_lap_video_v3.py" --outline "%T%\sao_paulo_grand_prix_outline.json" --a-csv "%H%ham2018_q.csv" --a-raceline "%H%h18_real_rl.json" --a-lap 67.281 --a-label "HAMILTON 2018 · LAP RECORD" --a-tag 2018 --b-csv "%H%sao_paulo_2026_at_70772.csv" --b-raceline "%T%\sao_paulo_grand_prix_raceline.json" --b-lap 70.772 --b-label "2026 OPTIMAL LAP" --b-tag 2026 --title "2018 vs 2026" --track-name "Sao Paulo" --zoom 20 --out "%H%sao_paulo_2018_vs_2026.mp4" %*
