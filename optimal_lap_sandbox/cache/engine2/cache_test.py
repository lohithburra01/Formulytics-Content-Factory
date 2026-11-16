import sys, time, numpy as np
sys.path.insert(0, '../hypo'); import hlib
from engine2 import *
c25 = Car('2025', m=805, mu=1.8, ClA=4.5, CdA_c=1.10, CdA_s=0.95, P_ice=560e3, mu_b=1.5, mu_d=1.1)
L = hlib.lap('Silverstone', 2025); trk = identify_track(L, c25)
trk['straight'] = straight_zones(trk['kappa'], trk['ds'])
t0=time.time(); r = simulate(c25, trk); print('2025 sim', round(r['lap'],3), 'real', L['lap'], 'vmax', r['v'].max()*3.6, round(time.time()-t0,3),'s')
c26 = Car('2026', m=775, mu=1.75, ClA=3.3, CdA_c=0.95, CdA_s=0.60, P_ice=380e3, mu_b=1.5, mu_d=1.1, recharge_MJ=7, superclip_kw=350)
t0=time.time(); r0 = simulate(c26, trk); print('2026 naive deploy-till-empty', round(r0['lap'],3), 'rech', r0['rech']/1e6)
r1, ctrl = optimise_energy(c26, trk, verbose=True); print('2026 optimised', round(r1['lap'],3), 'rech', r1['rech']/1e6, 'minSoC', r1['soc'].min()/1e6, round(time.time()-t0,1),'s')
print('real 2026', hlib.lap('Silverstone',2026)['lap'])
