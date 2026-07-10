#!/usr/bin/env python3
"""Queueing-level replay of synthetic or external transaction traces.

Input CSV columns: arrival_cycle,flow_id,class,payload_bytes,deadline_cycles.
The bundled generator creates a trace-inspired workload, not measured CXL/UCIe data.
A single shared serializer enforces raw link bandwidth. Pipeline depth only allows
verification and commit work to overlap with later serialized epochs.
"""
import argparse,csv,math,random,statistics as st
from collections import deque,defaultdict
from pathlib import Path
FRAME_PAYLOAD=256;FRAME_WIRE=276;TAG=12;CTRL=13;W=8.;VERIFY=10.

def load(path):
 with path.open() as f:rows=[{**r,'arrival_cycle':int(r['arrival_cycle']),'payload_bytes':int(r['payload_bytes']),'deadline_cycles':int(r['deadline_cycles'])} for r in csv.DictReader(f)]
 return sorted(rows,key=lambda r:r['arrival_cycle'])

def run(trace,m,depth,seed):
 rng=random.Random(seed);classes=sorted({r['class'] for r in trace});queues=defaultdict(deque);order=deque(classes);pending=deque(trace)
 inflight=[];done=[];now=0.;link_free=0.;peak=0
 def admit():
  nonlocal peak
  while pending and pending[0]['arrival_cycle']<=now:
   t=pending.popleft();queues[t['class']].append(t)
  peak=max(peak,sum(len(q) for q in queues.values()))
 while pending or any(queues.values()) or inflight:
  admit()
  while inflight and inflight[0][0]<=now:
   finish,batch=inflight.pop(0);done.extend((t,finish) for t in batch)
  if len(inflight)>=depth:
   now=max(now,inflight[0][0]);continue
  picked=None
  for _ in range(len(order)):
   c=order[0];order.rotate(-1)
   if queues[c]:picked=c;break
  if picked is None:
   candidates=([pending[0]['arrival_cycle']] if pending else [])+([inflight[0][0]] if inflight else [])
   if not candidates:break
   now=max(now,min(candidates));continue
  batch=[];frames=0
  while queues[picked]:
   t=queues[picked][0];need=math.ceil(t['payload_bytes']/FRAME_PAYLOAD)
   if frames and frames+need>m:break
   queues[picked].popleft();batch.append(t);frames+=need
   if frames>=m:break
  peak=max(peak,sum(len(q) for q in queues.values()));failed=sum(1 for _ in range(frames) if rng.random()<.01)
  wire=frames*FRAME_WIRE+TAG+CTRL+failed*(FRAME_WIRE+TAG+CTRL)
  start=max(now,link_free);link_finish=start+wire/W;commit=link_finish+VERIFY+failed*64
  link_free=link_finish;inflight.append((commit,batch));inflight.sort(key=lambda x:x[0]);now=link_finish
 while inflight:
  finish,batch=inflight.pop(0);done.extend((t,finish) for t in batch)
 per=defaultdict(list);miss=defaultdict(int)
 for t,finish in done:
  lat=finish-t['arrival_cycle'];per[t['class']].append(lat);miss[t['class']]+=lat>t['deadline_cycles']
 rows=[]
 for c in classes:
  v=per[c];rows.append({'class':c,'M':m,'pipeline_depth':depth,'count':len(v),'mean_latency':st.mean(v),'p99_latency':sorted(v)[max(0,math.ceil(.99*len(v))-1)],'deadline_misses':miss[c],'peak_queue':peak})
 xs=[1/st.mean(per[c]) for c in classes];return rows,sum(xs)**2/(len(xs)*sum(x*x for x in xs))

def main():
 p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,default=Path('traces/synthetic_mixed_workload.csv'));p.add_argument('--out',type=Path,default=Path('data/trace_replay_summary.csv'));p.add_argument('--seeds',type=int,default=20);a=p.parse_args();trace=load(a.trace);out=[]
 for m in (8,16,32,64):
  for d in (1,2,4,8):
   allrows=[];fair=[]
   for seed in range(a.seeds):r,f=run(trace,m,d,seed);allrows.extend(r);fair.append(f)
   for c in sorted({r['class'] for r in allrows}):
    rs=[r for r in allrows if r['class']==c];out.append({'class':c,'M':m,'pipeline_depth':d,'seeds':a.seeds,'mean_latency':st.mean(r['mean_latency'] for r in rs),'p99_latency':st.mean(r['p99_latency'] for r in rs),'deadline_misses':st.mean(r['deadline_misses'] for r in rs),'peak_queue':max(r['peak_queue'] for r in rs),'jain_fairness':st.mean(fair)})
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
 print('wrote trace replay summary')
if __name__=='__main__':main()
