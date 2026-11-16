from fit26 import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
x = np.array(json.load(open(sys.argv[1]))['x']) if len(sys.argv) > 1 else np.array(json.load(open('fit26_all.json'))['x'])
fig, ax = plt.subplots(4, 1, figsize=(16, 15))
for a, c in zip(ax, ['Silverstone', 'Monza', 'Zandvoort', 'Monte Carlo']):
    t = track(c); r = run(x, c); v26, lap26 = target(c)
    a.plot(t['s'], v26 * 3.6, 'k', lw=1.2, label=f'real 2026 {lap26:.2f}'); a.plot(t['s'], r['v'] * 3.6, 'r', lw=1, label=f"sim {r['lap']:.2f}")
    a.plot(t['s'], t['v25'] * 3.6, color='#999', lw=.8, label='real 2025')
    b = a.twinx(); b.plot(t['s'], r['u'] / 1e3, 'g', lw=.6); b.plot(t['s'], r['soc'] / 1e5, 'c', lw=.8); b.set_ylim(-400, 1200)
    a.set_title(c); a.set_ylim(50, 360); a.legend(loc='lower left', fontsize=8)
plt.tight_layout(); plt.savefig('diag26.png', dpi=60)
