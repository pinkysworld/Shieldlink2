#!/usr/bin/env python3
"""ShieldLink-SR protocol-realism experiment suite.

Abstract frame/epoch model with control serialization, propagation, timeout,
repair authentication, workload utilization, pipelining, adversarial schedules,
and abstract FEC. It is not a PHY, CXL/UCIe, or cryptographic implementation.
"""
from __future__ import annotations
import argparse, csv, math, random, statistics as stats
from dataclasses import dataclass
from pathlib import Path

LINK_BYTES_PER_CYCLE=8.0; HEADER_BYTES=16; CRC_BYTES=4; TAG_BYTES=12
ACK_BYTES=8; NAK_BASE_BYTES=8; PROP_CYCLES=2.0
CRC_CYCLES=1.0; AEAD_CYCLES=8.0; REPAIR_SCHED_CYCLES=4.0; P_GOOD=1e-6

def percentile(v,q):
    if not v:return 0.0
    v=sorted(v); return v[min(len(v)-1,max(0,math.ceil(q*len(v))-1))]
def ci95(v): return 0.0 if len(v)<2 else 1.96*stats.stdev(v)/math.sqrt(len(v))
def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

@dataclass(frozen=True)
class Workload:
    name:str; payload_bytes_per_frame:int; frames_per_flow:int
WORKLOADS={'coherence64':Workload('coherence64',64,1),'packet256':Workload('packet256',256,1),'dma4k':Workload('dma4k',256,16),'bulk64k':Workload('bulk64k',256,256)}

class GilbertElliott:
    def __init__(self,pi_bad,beta,p_bad,seed):
        if not 0<=pi_bad<1: raise ValueError('pi_bad must be in [0,1)')
        self.rng=random.Random(seed); self.beta=beta; self.p_bad=p_bad
        self.alpha=0 if pi_bad==0 else pi_bad*beta/(1-pi_bad); self.bad=self.rng.random()<pi_bad
    def corrupt(self):
        c=self.rng.random()<(self.p_bad if self.bad else P_GOOD)
        if self.bad:
            if self.rng.random()<self.beta:self.bad=False
        elif self.rng.random()<self.alpha:self.bad=True
        return c

@dataclass
class RunResult:
    offered_payload_bytes:int; delivered_payload_bytes:int; wire_bytes:int; elapsed_cycles:float; latencies:list[float]
    repair_rounds:list[int]; repair_frames:list[int]; security_drops:int=0; rejected_frames:int=0
    def summarize(self):
        return {'goodput':self.delivered_payload_bytes/self.wire_bytes if self.wire_bytes else 0.0,
        'offered_efficiency':self.offered_payload_bytes/self.wire_bytes if self.wire_bytes else 0.0,
        'delivery_ratio':self.delivered_payload_bytes/self.offered_payload_bytes if self.offered_payload_bytes else 0.0,
        'throughput_payload_B_per_cycle':self.delivered_payload_bytes/self.elapsed_cycles if self.elapsed_cycles else 0.0,
        'p50_latency_cycles':percentile(self.latencies,.5),'p95_latency_cycles':percentile(self.latencies,.95),
        'p99_latency_cycles':percentile(self.latencies,.99),'p999_latency_cycles':percentile(self.latencies,.999),
        'max_latency_cycles':max(self.latencies,default=0.0),'avg_repair_rounds':stats.mean(self.repair_rounds) if self.repair_rounds else 0.0,
        'avg_repair_frames':stats.mean(self.repair_frames) if self.repair_frames else 0.0,'peak_repair_frames':max(self.repair_frames,default=0),
        'security_drops':self.security_drops,'rejected_frames':self.rejected_frames}

def ctrl_cycles(n):return n/LINK_BYTES_PER_CYCLE+PROP_CYCLES
def epoch_wire_bytes(m):return m*(HEADER_BYTES+256+CRC_BYTES)+TAG_BYTES
def bitmap_nak_bytes(m):return NAK_BASE_BYTES+math.ceil(m/8)

def select_faults(m,ch,adversary,round_index,rng):
    failed={i for i in range(m) if ch.corrupt()}; tag=False; rejected=0
    if adversary=='one_per_epoch' and round_index==0: failed.add(rng.randrange(m))
    elif adversary=='final_frame' and round_index==0: failed.add(m-1)
    elif adversary=='repeat_repair': failed.add(0)
    elif adversary=='tag_target' and round_index==0: tag=True
    elif adversary=='replay': rejected=1
    elif adversary=='reorder': rejected=max(1,m//8)
    return failed,tag,rejected

def run_mode_b(*,epochs,m,pi_bad,beta,p_bad,seed,selective,workload,timeout_cycles,tag_policy,pipeline_depth,adversary='none',max_repair_rounds=16,fec_t=0):
    ch=GilbertElliott(pi_bad,beta,p_bad,seed); rng=random.Random(seed^0x51E1EC7)
    wire=offered=delivered=security_drops=rejected_frames=0; lats=[]; rounds=[]; repairs=[]; serial=0.0
    for _ in range(epochs):
        epoch_payload=m*workload.payload_bytes_per_frame; offered+=epoch_payload; parity=2*fec_t if fec_t else 0
        iw=epoch_wire_bytes(m)+parity*(HEADER_BYTES+256+CRC_BYTES); wire+=iw; serial+=iw/LINK_BYTES_PER_CYCLE
        lat=iw/LINK_BYTES_PER_CYCLE+AEAD_CYCLES+PROP_CYCLES
        failed,tag_attack,rejected=select_faults(m,ch,adversary,0,rng); rejected_frames+=rejected
        if rejected:
            aw=rejected*(HEADER_BYTES+256+CRC_BYTES); wire+=aw; serial+=aw/LINK_BYTES_PER_CYCLE; lat+=aw/LINK_BYTES_PER_CYCLE
        if fec_t and len(failed)<=fec_t: failed.clear()
        rr=rf=0
        while failed and rr<max_repair_rounds:
            rr+=1; count=len(failed) if selective else m; rf+=count
            nb=bitmap_nak_bytes(m) if selective else NAK_BASE_BYTES; wire+=nb; serial+=nb/LINK_BYTES_PER_CYCLE; lat+=ctrl_cycles(nb)
            rw=count*(HEADER_BYTES+256+CRC_BYTES)
            if tag_policy in {'resend_epoch_tag','repair_authenticator'}: rw+=TAG_BYTES
            elif tag_policy!='tag_once': raise ValueError(tag_policy)
            wire+=rw; serial+=rw/LINK_BYTES_PER_CYCLE; lat+=timeout_cycles+rw/LINK_BYTES_PER_CYCLE+AEAD_CYCLES+REPAIR_SCHED_CYCLES
            n=len(failed) if selective else m; failed={i for i in range(n) if ch.corrupt()}
            if adversary=='repeat_repair': failed.add(0)
        if failed: security_drops+=1; lat+=timeout_cycles
        elif tag_attack: security_drops+=1; lat+=timeout_cycles+AEAD_CYCLES
        else:
            delivered+=epoch_payload; wire+=ACK_BYTES; serial+=ACK_BYTES/LINK_BYTES_PER_CYCLE; lat+=ctrl_cycles(ACK_BYTES)
        lats.append(lat); rounds.append(rr); repairs.append(rf)
    elapsed=max(serial+epochs*(AEAD_CYCLES+PROP_CYCLES)/max(1,pipeline_depth),max(lats,default=0.0))
    return RunResult(offered,delivered,wire,elapsed,lats,rounds,repairs,security_drops,rejected_frames)

def run_mode_a(*,frames,pi_bad,beta,p_bad,seed,workload,timeout_cycles,adversary='none',fec_t=0):
    ch=GilbertElliott(pi_bad,beta,p_bad,seed); fb=HEADER_BYTES+256+CRC_BYTES+TAG_BYTES
    wire=offered=delivered=security_drops=rejected=0; elapsed=0.0; lats=[]; rounds=[]; repairs=[]; budget=0
    for fi in range(frames):
        if fi%32==0:
            budget=fec_t
            if fec_t: pw=2*fec_t*fb; wire+=pw; elapsed+=pw/LINK_BYTES_PER_CYCLE
        offered+=workload.payload_bytes_per_frame; attempts=0; lat=0.0; dropped=False
        while True:
            attempts+=1; wire+=fb; lat+=fb/LINK_BYTES_PER_CYCLE+CRC_CYCLES+AEAD_CYCLES+PROP_CYCLES
            bad=ch.corrupt()
            if adversary=='one_per_epoch' and fi%32==0 and attempts==1:bad=True
            if adversary=='final_frame' and fi%32==31 and attempts==1:bad=True
            if adversary=='repeat_repair':bad=attempts<=16
            if bad and budget>0 and attempts==1:budget-=1;bad=False;lat+=AEAD_CYCLES
            if not bad:break
            lat+=timeout_cycles
            if attempts>=16:security_drops+=1;dropped=True;break
        if adversary=='tag_target' and fi%32==31:security_drops+=1;dropped=True;lat+=timeout_cycles+AEAD_CYCLES
        if adversary in {'replay','reorder'} and fi%32==0:rejected+=1;wire+=fb;lat+=fb/LINK_BYTES_PER_CYCLE
        if not dropped:delivered+=workload.payload_bytes_per_frame;wire+=ACK_BYTES;lat+=ctrl_cycles(ACK_BYTES)
        elapsed+=lat;lats.append(lat);rounds.append(max(0,attempts-1));repairs.append(max(0,attempts-1))
    return RunResult(offered,delivered,wire,elapsed,lats,rounds,repairs,security_drops,rejected)

def aggregate(rows,keys):
    groups={}
    for r in rows:groups.setdefault(tuple(r[k] for k in keys),[]).append(r)
    metrics=['goodput','offered_efficiency','delivery_ratio','throughput_payload_B_per_cycle','p50_latency_cycles','p95_latency_cycles','p99_latency_cycles','p999_latency_cycles','max_latency_cycles','avg_repair_rounds','avg_repair_frames','peak_repair_frames','security_drops','rejected_frames']
    out=[]
    for name,members in sorted(groups.items()):
        row=dict(zip(keys,name));row['seeds']=len(members)
        for metric in metrics:
            vals=[float(x[metric]) for x in members];row[metric+'_mean']=stats.mean(vals);row[metric+'_ci95']=ci95(vals)
        out.append(row)
    return out

def run_suite(out_dir,seeds,epochs):
    raw=[];base=dict(pi_bad=.10,beta=.20,p_bad=.10,timeout_cycles=64.0)
    for policy in ['tag_once','resend_epoch_tag','repair_authenticator']:
      for selective in [False,True]:
       for seed in seeds:
        r=run_mode_b(epochs=epochs,m=32,seed=seed,selective=selective,workload=WORKLOADS['packet256'],pipeline_depth=1,tag_policy=policy,**base).summarize()
        raw.append({'experiment':'tag_policy','scheme':'sr' if selective else 'flush','tag_policy':policy,'workload':'packet256','pipeline_depth':1,'adversary':'none','fec_t':0,'seed':seed,**r})
    for workload in WORKLOADS.values():
      for depth in [1,2,4,8]:
       for seed in seeds:
        r=run_mode_b(epochs=epochs,m=32,seed=seed,selective=True,workload=workload,pipeline_depth=depth,tag_policy='repair_authenticator',**base).summarize()
        raw.append({'experiment':'workload_pipeline','scheme':'sr','tag_policy':'repair_authenticator','workload':workload.name,'pipeline_depth':depth,'adversary':'none','fec_t':0,'seed':seed,**r})
    for adv in ['none','one_per_epoch','final_frame','tag_target','repeat_repair','replay','reorder']:
      for scheme in ['modeA','flush','sr']:
       for seed in seeds:
        r=(run_mode_a(frames=epochs*32,seed=seed,workload=WORKLOADS['packet256'],adversary=adv,**base) if scheme=='modeA' else run_mode_b(epochs=epochs,m=32,seed=seed,selective=scheme=='sr',workload=WORKLOADS['packet256'],pipeline_depth=1,tag_policy='repair_authenticator',adversary=adv,**base)).summarize()
        raw.append({'experiment':'adversarial','scheme':scheme,'tag_policy':'repair_authenticator','workload':'packet256','pipeline_depth':1,'adversary':adv,'fec_t':0,'seed':seed,**r})
    for fec in [0,1,2]:
      for scheme in ['modeA','sr']:
       for seed in seeds:
        r=(run_mode_a(frames=epochs*32,seed=seed,workload=WORKLOADS['packet256'],fec_t=fec,**base) if scheme=='modeA' else run_mode_b(epochs=epochs,m=32,seed=seed,selective=True,workload=WORKLOADS['packet256'],pipeline_depth=1,tag_policy='repair_authenticator',fec_t=fec,**base)).summarize()
        raw.append({'experiment':'fec','scheme':scheme,'tag_policy':'repair_authenticator','workload':'packet256','pipeline_depth':1,'adversary':'none','fec_t':fec,'seed':seed,**r})
    write_csv(out_dir/'protocol_realism_raw.csv',raw)
    keys=['experiment','scheme','tag_policy','workload','pipeline_depth','adversary','fec_t'];summary=aggregate(raw,keys);write_csv(out_dir/'protocol_realism_summary.csv',summary)
    highlights=[r for r in summary if (r['experiment']=='adversarial' and r['adversary'] in {'none','one_per_epoch','repeat_repair','tag_target'}) or (r['experiment']=='workload_pipeline' and r['workload'] in {'coherence64','dma4k'} and r['pipeline_depth'] in {1,4,8}) or (r['experiment']=='tag_policy' and r['scheme']=='sr') or r['experiment']=='fec']
    write_csv(out_dir/'protocol_realism_highlights.csv',highlights)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out-dir',type=Path,default=Path('data'));p.add_argument('--epochs',type=int,default=400);p.add_argument('--seeds',type=int,default=20);a=p.parse_args();run_suite(a.out_dir,list(range(a.seeds)),a.epochs);print('wrote protocol-realism results')
if __name__=='__main__':main()
