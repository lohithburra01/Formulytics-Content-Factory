import fit26, json, sys, numpy as np
from multiprocessing import Pool
if __name__ == '__main__':
    x = np.array(json.load(open(sys.argv[1]))['x'])
    S = Pool(12).map(fit26.score, [(x, c) for c in fit26.TRACKS])
    for s in S: print(f"{s['track']:18s} err {s['err']:+6.3f} rmse {s['rmse']:5.1f} vmax {s['vmax_sim']:5.1f}/{s['vmax_real']:5.1f} first-quarter vmax {s['vmax_first']:5.1f} vcap {s['vcap']:.0f}")
    print('median |err|', np.median([abs(s['err']) for s in S]), 'median rmse', np.median([s['rmse'] for s in S]))
