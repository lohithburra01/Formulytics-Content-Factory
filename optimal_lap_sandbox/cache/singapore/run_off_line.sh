cd "/d/f1_hot_lap/OPTIMAL LAP SCRIPTS"; SG=cache/singapore; M=F1_Pipeline_Assets/tracks/singapore_grand_prix_mirror_outline.json; B=$SG/base_off_rl.json
python -c "import numpy as np,json,sys;sys.path.insert(0,'cache/era2017');import _opt_line_2017 as O;O.setup('$B','$M',None,None,0.3,12);np.save('$SG/zero_knots.npy',np.zeros(len(O.G['kidx'])))" 2>/dev/null
python $SG/_opt_line_2026_sg.py --base $B --outline $M --cda 0.617 --cl 4.148 --rho 1.2232 --margin 0.3 --apex-w 1.5 --apex-knots $SG/zero_knots.npy --out $SG/off1 > $SG/off1.log 2>&1
grep "apex penalty\|apex gaps\|done" $SG/off1.log
python -u $SG/_autofit_rl_in_sg.py $SG/off1_rl.json > $SG/off1_refit.log 2>&1; grep "\[autofit\] singapore:" $SG/off1_refit.log
