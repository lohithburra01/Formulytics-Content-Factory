cd "/d/f1_hot_lap/OPTIMAL LAP SCRIPTS"
for v in orig rev mir mirrev; do
  python sim_2026_lap.py --outline cache/brazil/outline_$v.json --raceline-out cache/brazil/dir_$v.json --csv-out cache/brazil/dir_$v.csv --reference-csv F1_Pipeline_Assets/exports/reference_2025_brazil_q.csv --rho 1.1353 > cache/brazil/dir_$v.log 2>&1 &
done
wait; tail -n 3 cache/brazil/dir_*.log
