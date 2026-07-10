#!/usr/bin/env python3
"""Adaptive epoch-size ablation on a non-stationary synthetic channel."""
from __future__ import annotations
import argparse,random,statistics as st
from pathlib import Path
from protocol_realism_experiments import WORKLOADS,run_mode_b,ci95,write_csv
MS=(8,16,32,64); SEGMENTS=((.01,80),(.10,80),(.20,80),(.04,80),(.15,80),(.01,80))
def utility(r):return r['goodput']-.00002*r['p99_latency_cycles']
def combine(rs):return {k:st.mean(r[k] for r in rs) for k in rs[0]}
def one(m,pi,epochs,seed):return run_mode_b(epochs=epochs,m=m,pi_bad=pi,beta=.2,p_bad=.1,seed=seed,selective=True,workload=WORKLOADS['packet256'],timeout_cycles=64,tag_policy='repair_authenticator',pipeline_depth=1).summarize()
def fixed(m,seed):return combine([one(m,pi,n,seed+i*1009) for i,(pi,n) in enumerate(SEGMENTS)])
def threshold(seed,t,w):
 rng=random.Random(seed);m=32;clean=0;rs=[]
 for pi,n in SEGMENTS:
  for _ in range(n):
   r=one(m,pi,1,rng.randrange(1<<30));rs.append(r);ratio=r['avg_repair_frames']/m;idx=MS.index(m)
   if ratio>t and idx>0:m=MS[idx-1];clean=0
   elif ratio==0:
    clean+=1
    if clean>=w and idx<len(MS)-1:m=MS[idx+1];clean=0
   else:clean=0
 return combine(rs)
def ewma(seed,a):
 rng=random.Random(seed);m=32;e=0.;rs=[]
 for pi,n in SEGMENTS:
  for _ in range(n):
   r=one(m,pi,1,rng.randrange(1<<30));rs.append(r);e=a*(r['avg_repair_frames']/m)+(1-a)*e
   m=8 if e>.08 else 16 if e>.04 else 32 if e>.015 else 64
 return combine(rs)
def oracle(seed):
 out=[]
 for i,(pi,n) in enumerate(SEGMENTS):
  candidates=[one(m,pi,n,seed+i*1009+m) for m in MS];out.append(max(candidates,key=utility))
 return combine(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out-dir',type=Path,default=Path('data'));p.add_argument('--seeds',type=int,default=20);a=p.parse_args();raw=[]
 for seed in range(a.seeds):
  for m in MS:raw.append({'policy':f'fixed_M{m}','seed':seed,**fixed(m,seed)})
  for t in (.04,.08,.12):
   for w in (8,32):raw.append({'policy':f'threshold_t{t}_w{w}','seed':seed,**threshold(seed,t,w)})
  for x in (.1,.3,.6):raw.append({'policy':f'ewma_a{x}','seed':seed,**ewma(seed,x)})
  raw.append({'policy':'offline_oracle','seed':seed,**oracle(seed)})
 write_csv(a.out_dir/'adaptive_ablation_raw.csv',raw);rows=[]
 for policy in sorted({r['policy'] for r in raw}):
  rs=[r for r in raw if r['policy']==policy];row={'policy':policy,'seeds':len(rs)}
  for metric in ['goodput','throughput_payload_B_per_cycle','p99_latency_cycles','avg_repair_frames','security_drops']:
   vals=[r[metric] for r in rs];row[metric+'_mean']=st.mean(vals);row[metric+'_ci95']=ci95(vals)
  row['utility_mean']=st.mean(utility(r) for r in rs);rows.append(row)
 write_csv(a.out_dir/'adaptive_ablation_summary.csv',rows);print('wrote adaptive policy ablation')
if __name__=='__main__':main()
