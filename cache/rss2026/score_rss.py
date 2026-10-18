import os, sys, json, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', 'engine2'))
from variant_a import roll_to, lapdict, oldlap, hlib
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
res = json.load(open(os.path.join(H, 'rss_laps.json'))); out = []
fig, axs = plt.subplots(9, 1, figsize=(15, 30))
for o, ax in zip(res, axs):
    real = hlib.lap(o['circuit'], 2026); L = lapdict(None, np.array(o['v']), np.array(o['s'])); L['lap'] = o['lap']
    row = dict(track=o['key'], real=real['lap'])
    for tag, X in (('rss', L), ('old', oldlap(o['key']))):
        X = roll_to(real, X); A = hlib.align(real, X); e = A['v26'] - A['v25']
        row[tag] = dict(lap=X['lap'], err=X['lap'] - real['lap'], rmse=float(np.sqrt(np.mean(e**2))), vmax=float(np.max(X['v'])))
        if tag == 'rss': ax.plot(A['s'], A['v25'], 'k', lw=1.6, label=f"REAL 2026 Q {real['lap']:.3f}s (vmax {real['v'].max():.0f})")
        ax.plot(A['s'], A['v26'], color={'rss': '#d62728', 'old': '#1f6fd1'}[tag], lw=1.2,
                label=f"{'RSS 2026 car (Assetto Corsa data)' if tag=='rss' else 'OLD shipped engine'}: {X['lap']:.3f}s ({X['lap']-real['lap']:+.2f}), RMSE {row[tag]['rmse']:.1f} km/h, vmax {row[tag]['vmax']:.0f}")
    ax.set_title(o['circuit']); ax.legend(fontsize=8, loc='lower left'); ax.grid(alpha=.3); ax.set_ylabel('km/h')
    out.append(row); print(f"{o['key']:12s} real {real['lap']:7.3f} | RSS {row['rss']['lap']:7.3f} {row['rss']['err']:+6.2f}s rmse {row['rss']['rmse']:5.1f} vmax {row['rss']['vmax']:4.0f} | old {row['old']['err']:+6.2f}s rmse {row['old']['rmse']:5.1f} | real vmax {real['v'].max():.0f}")
plt.tight_layout(); plt.savefig(os.path.join(H, 'rss_vs_real.png'), dpi=60)
json.dump(out, open(os.path.join(H, 'rss_scores.json'), 'w'), indent=1)
m = lambda k, q: np.median([abs(r[k][q]) for r in out])
print(f"median |lap err|: RSS {m('rss','err'):.2f} s, old {m('old','err'):.2f} s;  median RMSE: RSS {m('rss','rmse'):.1f}, old {m('old','rmse'):.1f} km/h")
