# Singapore 2026 - lap-time impact of the 32 no-origin values (2026-10-20)
Baseline lap 93.0084 s, final sim step on the k3w line. Lap change in seconds.

## +-10%
```
CDA_CORNER_M2                1.79  -10%:  -0.058  +10%:  +0.068   (car/f1_2026_car)
CL_STRAIGHT_M2                1.4  -10%:  +0.115  +10%:  -0.096   (car/f1_2026_car)
MU_LONG                      1.35  -10%:  +0.540  +10%:  -0.456   (car/f1_2026_car)
MU_DRIVE                      1.0  -10%:  +1.250  +10%:  -0.936   (car/f1_2026_car)
KAPPA_CORNER_THRESH         0.005  -10%:  -0.056  +10%:  +0.112   (car/f1_2026_car)
E_BATTERY_CAP_J           4000000  -10%:  +0.000  +10%:  +0.000   (car/f1_2026_car)
SOC_INIT                      1.0  -10%:  +0.000  +10%:  +0.000   (car/f1_2026_car)
SOC_SUPERCLIP_THRESH          0.3  -10%:  +0.000  +10%:  +0.000   (car/f1_2026_car)
SUPERCLIP_SPEED_FRAC         0.96  -10%:  +0.152  +10%:    FAIL   (car/f1_2026_car)
TRAIL_V_FULL_KMH            235.0  -10%:  -0.302  +10%:  +0.279   (car/f1_2026_car)
TRAIL_FRAC_MIN                0.4  -10%:  +0.187  +10%:  -0.171   (car/f1_2026_car)
TRAIL_EXP                     1.6  -10%:  -0.148  +10%:  +0.142   (car/f1_2026_car)
BRAKE_DECEL_THRESH            4.0  -10%:  -0.004  +10%:  +0.000   (car/f1_2026_car)
DECEL_WINDOW_S                0.4  -10%:  +0.000  +10%:  +0.000   (car/f1_2026_car)
WARM_A_ACC_MAX              39.24  -10%:  +0.000  +10%:  +0.000   (car/f1_2026_car)
WARM_CDA                     0.55  -10%:  +0.000  +10%:  +0.000   (car/f1_2026_car)
WARM_V_CAP                  110.0  -10%:  +0.000  +10%:  +0.000   (car/f1_2026_car)
mu_lat_scale                  1.0  -10%:  +5.052  +10%:  -4.346   (track/singapore_2026_layout)
N_CORRIDOR_POINTS             800  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
CORR_SMOOTH_S                30.0  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
J_MAX_LAT_JERK               12.0  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
UNWIND_RATIO                  3.0  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
STRAIGHT_STIFF                5.0  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
KAPPA_FLOOR                 0.005  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
LAMBDA_SLACK               1000.0  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
SAFETY_MARGIN_REFINE          0.3  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
FB_TOL                     0.0001  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
V_FLOOR_MS                    5.0  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
BANK_DENOM_FLOOR            0.001  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
KGRIP_STENCIL                   4  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
LINE_WOBBLE_SIG               2.5  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
LINE_WOBBLE_ADAPTIVE            1  -10%:  +0.000  +10%:  +0.000   (run/sim_numerics)
```
## +-50%, byte-compare vs baseline (KGRIP 3/6, WOBBLE_ADAPTIVE 0/2)
```
E_BATTERY_CAP_J        x0.5/x1.5: ['differs(+0.000s)', 'differs(+0.000s)']
SOC_INIT               x0.5/x1.5: ['same', 'same']
SOC_SUPERCLIP_THRESH   x0.5/x1.5: ['same', 'same']
BRAKE_DECEL_THRESH     x0.5/x1.5: ['differs(+0.001s)', 'differs(+0.000s)']
DECEL_WINDOW_S         x0.5/x1.5: ['same', 'same']
WARM_A_ACC_MAX         x0.5/x1.5: ['same', 'same']
WARM_CDA               x0.5/x1.5: ['same', 'same']
WARM_V_CAP             x0.5/x1.5: ['same', 'same']
N_CORRIDOR_POINTS      x0.5/x1.5: ['same', 'same']
CORR_SMOOTH_S          x0.5/x1.5: ['same', 'same']
J_MAX_LAT_JERK         x0.5/x1.5: ['same', 'same']
UNWIND_RATIO           x0.5/x1.5: ['same', 'same']
STRAIGHT_STIFF         x0.5/x1.5: ['same', 'same']
KAPPA_FLOOR            x0.5/x1.5: ['same', 'same']
LAMBDA_SLACK           x0.5/x1.5: ['same', 'same']
SAFETY_MARGIN_REFINE   x0.5/x1.5: ['same', 'same']
FB_TOL                 x0.5/x1.5: ['same', 'same']
V_FLOOR_MS             x0.5/x1.5: ['same', 'same']
BANK_DENOM_FLOOR       x0.5/x1.5: ['same', 'same']
KGRIP_STENCIL          x0.5/x1.5: ['differs(+0.510s)', 'differs(-1.010s)']
LINE_WOBBLE_SIG        x0.5/x1.5: ['same', 'same']
LINE_WOBBLE_ADAPTIVE   x0.5/x1.5: ['same', 'same']
```
