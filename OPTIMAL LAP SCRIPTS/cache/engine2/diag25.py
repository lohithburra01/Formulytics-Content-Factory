from common import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
x = json.load(open('fit25.json'))['x']
fig, ax = plt.subplots(4, 1, figsize=(16, 14))
for a, c in zip(ax, ['Silverstone', 'Catalunya', 'Shanghai', 'Zandvoort']):
    t = track(c); r = simulate(car25(x, c), t)
    a.plot(t['s'], t['v25']*3.6, 'k', lw=1, label='real 2025'); a.plot(t['s'], r['v']*3.6, 'r', lw=1, label='sim 2025')
    a.fill_between(t['s'], 0, 60, where=t['mask'], color='orange', alpha=.3, label='corner mask')
    a.fill_between(t['s'], 60, 90, where=t['drs'], color='g', alpha=.3, label='DRS')
    a.set_title(c); a.set_ylim(0, 360); a.legend(loc='lower right', fontsize=7)
plt.tight_layout(); plt.savefig('diag25.png', dpi=60)
