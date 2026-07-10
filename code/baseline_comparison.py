#!/usr/bin/env python3
"""Compare ShieldLink variants with a non-authenticated selective-repeat ARQ ceiling.

Latency units differ by design: per-frame schemes report frame completion latency,
while epoch schemes report epoch-head commit latency.
"""
import argparse,statistics as st
from pathlib import Path
from protocol_realism_experiments import (ACK_BYTES,CRC_BYTES,CRC_CYCLES,HEADER_BYTES,LINK_BYTES_PER_CYCLE,PROP_CYCLES,WORKLOADS,GilbertElliott,ci95,percentile,run_mode_a,run_mode_b,write_csv)

def selective_arq(frames,pi_bad,beta,p_bad,seed):
    ch=GilbertElliott(pi_bad,beta,p_bad,seed);wire=0;lat=[];fb=HEADER_BYTES+256+CRC_BYTES
    for _ in range(frames):
        tries=0
        while True:
            tries+=1;wire+=fb
            if not ch.corrupt():break
        wire+=ACK_BYTES;lat.append(tries*(fb/LINK_BYTES_PER_CYCLE+CRC_CYCLES+PROP_CYCLES)+ACK_BYTES/LINK_BYTES_PER_CYCLE+PROP_CYCLES)
    payload=frames*256
    return {'goodput':payload/wire,'p99_latency_cycles':percentile(lat,.99),'security':'none'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('data/baseline_comparison.csv'));p.add_argument('--seeds',type=int,default=20);p.add_argument('--epochs',type=int,default=300);a=p.parse_args();raw=[]
    base=dict(pi_bad=.10,beta=.20,p_bad=.10,timeout_cycles=64.0)
    for seed in range(a.seeds):
        raw.append({'scheme':'selective_arq_no_auth','seed':seed,**selective_arq(a.epochs*32,.10,.20,.10,seed)})
        ma=run_mode_a(frames=a.epochs*32,seed=seed,workload=WORKLOADS['packet256'],**base).summarize();raw.append({'scheme':'modeA','seed':seed,'goodput':ma['goodput'],'p99_latency_cycles':ma['p99_latency_cycles'],'security':'per-frame AEAD'})
        for scheme,selective in [('modeB_flush',False),('modeB_sr',True)]:
            r=run_mode_b(epochs=a.epochs,m=32,seed=seed,selective=selective,workload=WORKLOADS['packet256'],pipeline_depth=1,tag_policy='repair_authenticator',**base).summarize();raw.append({'scheme':scheme,'seed':seed,'goodput':r['goodput'],'p99_latency_cycles':r['p99_latency_cycles'],'security':'epoch AEAD'})
    rows=[]
    for scheme in sorted({r['scheme'] for r in raw}):
        rs=[r for r in raw if r['scheme']==scheme];g=[r['goodput'] for r in rs];lat=[r['p99_latency_cycles'] for r in rs]
        rows.append({'scheme':scheme,'security':rs[0]['security'],'seeds':len(rs),'goodput_mean':st.mean(g),'goodput_ci95':ci95(g),'p99_latency_cycles_mean':st.mean(lat),'p99_latency_cycles_ci95':ci95(lat)})
    write_csv(a.out,rows);print('wrote baseline comparison')
if __name__=='__main__':main()
