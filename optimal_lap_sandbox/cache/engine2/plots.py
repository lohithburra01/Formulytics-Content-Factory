"""Per-track speed-graph proof plots from metrics.json: real 2026 Q (black) vs NEW engine blind LOO (red) vs OLD shipped
physics (blue) vs NEW engine on our raceline (orange dashed), + 2025 pole (grey); lower panel = new engine's battery SoC."""
import json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D = json.load(open('metrics.json')); M, T = D['metrics'], D['traces']
STY = [('real2025', 'real 2025 pole', '#aaaaaa', '-', 1.0), ('old', 'OLD engine (shipped optimal)', '#1f6fd1', '-', 1.1),
       ('new_geom', 'NEW engine on our raceline', '#f08c00', '--', 1.1), ('new_blind', 'NEW engine (blind, LOO)', '#d62728', '-', 1.6),
       ('real', 'REAL 2026 Q', 'k', '-', 1.6)]
for c in T:
    fig, (a, b) = plt.subplots(2, 1, figsize=(15, 7.5), gridspec_kw=dict(height_ratios=[3, 1]), sharex=False)
    for k, lab, col, ls, lw in STY:
        if k not in T[c]: continue
        s, v = T[c][k]; m = M[c].get(k)
        lab2 = lab if m is None or k == 'real' else f"{lab}: lap {m['err']:+.2f}s, RMSE {m['rmse']:.1f} km/h, r={m['corr']:.3f}"
        if k == 'real': lab2 = f"{lab} {M[c]['real']:.3f}s"
        a.plot(s, v, color=col, ls=ls, lw=lw, label=lab2)
    a.set_title(f'{c}: speed vs distance on the real 2026 lap axis'); a.set_ylabel('km/h'); a.legend(fontsize=8, loc='lower left'); a.grid(alpha=.3)
    s25 = np.array(T[c]['s25']); b.plot(s25, T[c]['soc'], color='#2a9d8f'); b.set_ylabel('SoC MJ (new)'); b.set_xlabel('m (2025 lap axis)'); b.grid(alpha=.3)
    b2 = b.twinx(); b2.plot(s25, T[c]['u'], color='#d62728', lw=.6, alpha=.6); b2.set_ylabel('MGU-K kW')
    plt.tight_layout(); plt.savefig(f"plot_{c.replace(' ', '_')}.png", dpi=70); plt.close()
print('ok')
