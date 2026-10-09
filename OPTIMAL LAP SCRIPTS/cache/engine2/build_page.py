import json, numpy as np
D = json.load(open('metrics.json')); M, T = D['metrics'], D['traces']
keys = ['real', 'new_blind', 'hybrid', 'old', 'new_geom', 'real2025']
out = {}
for c in T:
    s_real = np.array(T[c]['real'][0]); g = np.linspace(s_real.min(), s_real.max(), 700)
    o = {'s': list(np.round(g, 0))}
    for k in keys:
        if k in T[c]:
            s, v = map(np.array, T[c][k]); o[k] = list(np.round(np.interp(g, s, v), 1))
    s25 = np.array(T[c]['s25']); gg = np.linspace(0, s25[-1], 400)
    o['soc'] = list(np.round(np.interp(gg, s25, T[c]['soc']), 2)); o['soc_s'] = list(np.round(gg / s25[-1] * g[-1], 0))
    o['m'] = M[c]; out[c] = o
json.dump(out, open('page_data.json', 'w'), separators=(',', ':'))
tpl = open('page_template.html', encoding='utf8').read()
open('engine2_proof.html', 'w', encoding='utf8').write(tpl.replace('/*DATA*/null', json.dumps(out, separators=(',', ':'))))
print('ok', len(open('engine2_proof.html', encoding='utf8').read()) // 1024, 'KB')
