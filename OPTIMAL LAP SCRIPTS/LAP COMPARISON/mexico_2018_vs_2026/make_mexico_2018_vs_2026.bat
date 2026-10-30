@echo off
chcp 65001 >nul
rem Mexico: RICCIARDO 2018 POLE 1:14.759 (fastest lap ever at the track, real F1IH trace, own 2018-car line)
rem vs 2026 OPTIMAL LAP shown at the user's 1:17.265 (shipped sim 76.758 uniformly scaled, _scale_2026.py).
set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "H=%~dp0"
set "ROOT=%~dp0..\..\"
set "T=%ROOT%F1_Pipeline_Assets\tracks"
"%PYTHON%" "%ROOT%cache\era2017\dual_lap_video_v3.py" --outline "%T%\mexico_city_grand_prix_outline.json" --a-csv "%H%ric2018_q.csv" --a-raceline "%H%k18_rl.json" --a-lap 74.759 --a-label "RICCIARDO 2018 · LAP RECORD" --a-tag 2018 --b-csv "%H%mexico_2026_at_77265.csv" --b-raceline "%T%\mexico_city_grand_prix_raceline.json" --b-lap 77.265 --b-label "2026 OPTIMAL LAP" --b-tag 2026 --title "2018 vs 2026" --track-name "Mexico City" --zoom 28 --out "%H%mexico_2018_vs_2026_record.mp4" %*
