"""Run frozen 2026 physics on a Madring line with explicit per-track inputs.

Every trial has new exclusive paths. No deletion or shared physics mutation
on disk. FP1 informs calibration; there is no invented 2025 reference rail.
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
import sim_2026_lap as sim
from _track_registry import rho_isa
from _gate_2026 import load as gate_load, rate_kmh_s


def run(args):
    dest=ROOT/"cache/madring_final_calibration"
    dest.mkdir(exist_ok=True)
    assert args.name.replace("_","").isalnum(), "Simple trial name required"
    csv_path=dest/f"{args.name}.csv"
    meta_path=dest/f"{args.name}.json"
    state_path=dest/f"{args.name}_stations.npz"
    for p in (csv_path,meta_path,state_path):
        if p.exists(): raise FileExistsError(p)
    line_path=Path(args.line)
    data=json.loads(line_path.read_text(encoding="utf-8"))
    points=np.asarray(data["raceline"],dtype=float)
    arc=np.asarray(data["arc_length"],dtype=float)
    curvature=np.asarray(data["kappa"],dtype=float)
    length=float(data["track_length_m"])
    rho=rho_isa(args.altitude)
    sim._apply_car_overrides(SimpleNamespace(cda=args.cda,cl=args.cl,rho=rho))
    frac=arc/length
    bank=np.zeros_like(frac)
    if args.bank_peak:
        # Track-specific bank interval, with 0.01-lap smooth transitions.
        window=(frac>=args.bank_start)&(frac<=args.bank_end)
        ramp=np.minimum((frac-args.bank_start)/0.01,(args.bank_end-frac)/0.01)
        bank[window]=args.bank_peak*0.5*(1-np.cos(np.pi*np.clip(ramp[window],0,1)))
    sim.BANKING_RAD=np.radians(bank) if np.any(bank) else None
    v,soc,mode,power,t=sim.simulate_lap(points,arc,curvature,length)
    raw_lap=float(t[-1])
    v,t=sim.smooth_longitudinal(v,arc,length,win_s=0.45)
    v,t=sim.suppress_microhumps(v,arc,length,t)
    sim.write_csv(str(csv_path),v,soc,mode,power,t,arc,length,fps=30)
    sanity=True
    try: sim.assert_sanity(v,soc,mode,power,t)
    except SystemExit: sanity=False
    np.savez_compressed(state_path,v_ms=v,soc=soc,mode=np.asarray(mode),power_kw=power,
                        time_s=t,arc_length=arc,kappa=curvature,banking_deg=bank)
    real=pd.read_csv(ROOT/"F1_Pipeline_Assets/exports/reference_2026_madring_fp1.csv")
    grid=np.linspace(0,1,5000,endpoint=False)
    rd=real.distance.to_numpy()-float(real.distance.iloc[0])
    rv=np.interp(grid,rd/rd[-1],real.speed)
    sv=np.interp(grid,frac,v*3.6,period=1)
    minima,_=find_peaks(-rv,prominence=15,distance=125)
    corners=[]
    for i in minima:
        win=np.abs(((grid-grid[i]+0.5)%1)-0.5)<=0.015
        corners.append(dict(frac=round(float(grid[i]),5),real_kmh=round(float(rv[i]),2),
                            sim_kmh=round(float(sv[win].min()),2),
                            error_kmh=round(float(sv[win].min()-rv[i]),2)))
    tt,vv,th,br,dd=gate_load(csv_path)
    rates=rate_kmh_s(tt,vv)
    gain=rates[(th>80)&(br<5)&(vv<0.88*vv.max())&(rates>2)]
    drop=-rates[(br>15)&(rates<-2)]
    near=(th>90)&(br<5)&(vv>0.85*vv.max())
    clip=-rates[near&(rates<-1)]
    physics=dict(gain_median=float(np.median(gain)),gain_peak=float(gain.max()),
                 drop_median=float(np.median(drop)),drop_peak=float(drop.max()),
                 superclip_fraction=float(len(clip)/max(1,near.sum())),
                 superclip_peak=float(clip.max()) if len(clip) else 0)
    result=dict(name=args.name,line=str(line_path.resolve()),cda=args.cda,cl=args.cl,
                altitude_assumption_m=args.altitude,rho=rho,
                bank_peak_deg=args.bank_peak,bank_start=args.bank_start,bank_end=args.bank_end,
                raw_lap_s=raw_lap,lap_s=float(t[-1]),lap_vs_fp1_s=float(t[-1]-94.077),
                min_speed_kmh=float((v*3.6).min()),top_speed_kmh=float((v*3.6).max()),
                correlation=float(np.corrcoef(sv,rv)[0,1]),
                speed_mae_kmh=float(np.mean(np.abs(sv-rv))),
                corner_median_error_kmh=float(np.median([c["error_kmh"] for c in corners])),
                corners=corners,physics=physics,sanity_pass=sanity)
    with meta_path.open("x",encoding="utf-8") as stream: json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if sanity else 10


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--name",required=True)
    parser.add_argument("--line",default=str(ROOT/"cache/madring_fp1_elevation/madring_fp1_raceline.json"))
    parser.add_argument("--cda",type=float,default=0.8)
    parser.add_argument("--cl",type=float,default=4.2)
    parser.add_argument("--altitude",type=float,default=684.0)
    parser.add_argument("--bank-peak",type=float,default=0.0)
    parser.add_argument("--bank-start",type=float,default=0.50)
    parser.add_argument("--bank-end",type=float,default=0.60)
    raise SystemExit(run(parser.parse_args()))
