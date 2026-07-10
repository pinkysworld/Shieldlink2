#!/usr/bin/env python3
"""Generate the deterministic synthetic mixed-workload trace used by validation."""
import argparse,csv,random
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('traces/synthetic_mixed_workload.csv'));p.add_argument('--transactions',type=int,default=800);p.add_argument('--seed',type=int,default=20260710);a=p.parse_args()
 rng=random.Random(a.seed);classes=[('coherence',64,500),('packet',256,1200),('dma',4096,8000),('bulk',16384,30000)];rows=[];cycle=0
 for flow in range(a.transactions):
  cycle+=rng.randint(0,24);c,payload,deadline=classes[rng.choices(range(4),weights=[45,30,18,7])[0]]
  rows.append({'arrival_cycle':cycle,'flow_id':flow,'class':c,'payload_bytes':payload,'deadline_cycles':deadline})
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(f'wrote {len(rows)} transactions to {a.out}')
if __name__=='__main__':main()
