#!/usr/bin/env python3
"""Extended ShieldLink-SR experiment sweeps.

Abstract frame-level simulator for paper planning. It is not a PHY, CXL/UCIe, or
AEAD implementation model. It compares CRC+ARQ, ShieldLink Mode A, Mode B
flush-all, Mode B selective retry, and an adaptive selective-retry policy under a
Gilbert-Elliott burst-error model.
"""
from __future__ import annotations
import argparse, csv, math, random, statistics as st
from pathlib import Path

P=256; B_CRC=268; B_A=288; B_B=276; TAG=12; W=8.0; DCRC=1.0; DAEAD=8.0; DPROP=2.0; DREPAIR=4.0; PGOOD=1e-6

def ci(xs): return 0 if len(xs)<2 else 1.96*st.stdev(xs)/math.sqrt(len(xs))
def pct(xs,q):
    xs=sorted(xs); return xs[min(len(xs)-1,max(0,math.ceil(q*len(xs))-1))] if xs else 0

def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

class GE:
    def __init__(self, pi, beta, pbad, seed):
        self.r=random.Random(seed); self.pi=pi; self.beta=beta; self.pbad=pbad
        self.alpha=0 if pi<=0 else pi*beta/max(1e-12,1-pi); self.bad=self.r.random()<pi
    def corrupt(self):
        c=self.r.random() < (self.pbad if self.bad else PGOOD)
        if self.bad:
            if self.r.random()<self.beta: self.bad=False
        else:
            if self.r.random()<self.alpha: self.bad=True
        return c

def summary(payload, wire, lat, rounds=None, rep=None, buf=None):
    rounds=rounds or [0]; rep=rep or [0]; buf=buf or [1]
    return dict(goodput=payload/wire, p50=pct(lat,.5), p95=pct(lat,.95), p99=pct(lat,.99), p999=pct(lat,.999), maxlat=max(lat),
        avg_repair_rounds=st.mean(rounds), avg_repair_frames=st.mean(rep), peak_repair_frames=max(rep), avg_buffer_frames=st.mean(buf), peak_buffer_frames=max(buf))

def frame_scheme(n, pi, beta, pbad, seed, bytes_per_frame, cycles_per_frame):
    ch=GE(pi,beta,pbad,seed); wire=0; lat=[]
    for _ in range(n):
        a=0
        while True:
            a+=1; wire+=bytes_per_frame
            if not ch.corrupt(): break
        lat.append(a*cycles_per_frame)
    return summary(n*P, wire, lat)

def mode_b_flush(epochs, m, pi, beta, pbad, seed):
    ch=GE(pi,beta,pbad,seed); wire=0; lat=[]; rounds=[]; reps=[]; bufs=[]
    ew=m*B_B+TAG; cyc=ew/W+DAEAD+DPROP
    for _ in range(epochs):
        a=0
        while True:
            a+=1; wire+=ew; fails=sum(ch.corrupt() for _ in range(m))
            if fails==0: break
        lat.append(a*cyc); rounds.append(a-1); reps.append((a-1)*m); bufs.append(m)
    return summary(epochs*m*P, wire, lat, rounds, reps, bufs)

def mode_b_sr(epochs, m, pi, beta, pbad, seed):
    ch=GE(pi,beta,pbad,seed); wire=0; lat=[]; rounds=[]; reps=[]; bufs=[]
    for _ in range(epochs):
        ew=m*B_B+TAG; wire+=ew; cost=ew/W+DAEAD+DPROP; fail=sum(ch.corrupt() for _ in range(m)); rr=0; rf=0
        while fail:
            rr+=1; rf+=fail; rw=fail*B_B+TAG; wire+=rw; cost+=rw/W+DAEAD+DREPAIR; fail=sum(ch.corrupt() for _ in range(fail))
        lat.append(cost); rounds.append(rr); reps.append(rf); bufs.append(m)
    return summary(epochs*m*P, wire, lat, rounds, reps, bufs)

def adaptive_sr(epochs, pi, beta, pbad, seed, allowed=(8,16,32,64)):
    ch=GE(pi,beta,pbad,seed); m=32; clean=0; wire=payload=0; lat=[]; rounds=[]; reps=[]; bufs=[]
    for _ in range(epochs):
        ew=m*B_B+TAG; wire+=ew; payload+=m*P; cost=ew/W+DAEAD+DPROP; initial=fail=sum(ch.corrupt() for _ in range(m)); rr=rf=0
        while fail:
            rr+=1; rf+=fail; rw=fail*B_B+TAG; wire+=rw; cost+=rw/W+DAEAD+DREPAIR; fail=sum(ch.corrupt() for _ in range(fail))
        lat.append(cost); rounds.append(rr); reps.append(rf); bufs.append(m)
        idx=allowed.index(m); ratio=initial/m
        if ratio>.08 and idx>0: m=allowed[idx-1]; clean=0
        elif ratio==0: clean+=1
        else: clean=0
        if clean>=32 and allowed.index(m)<len(allowed)-1: m=allowed[allowed.index(m)+1]; clean=0
    return summary(payload, wire, lat, rounds, reps, bufs)

def agg(named):
    out=[]
    for name in sorted(set(n for n,_ in named)):
        rs=[r for n,r in named if n==name]
        out.append(dict(scheme=name, goodput_mean=st.mean(r['goodput'] for r in rs), goodput_ci95=ci([r['goodput'] for r in rs]),
            p50_latency_mean=st.mean(r['p50'] for r in rs), p95_latency_mean=st.mean(r['p95'] for r in rs), p99_latency_mean=st.mean(r['p99'] for r in rs),
            p999_latency_mean=st.mean(r['p999'] for r in rs), max_latency_mean=st.mean(r['maxlat'] for r in rs),
            avg_repair_rounds_mean=st.mean(r['avg_repair_rounds'] for r in rs), avg_repair_frames_mean=st.mean(r['avg_repair_frames'] for r in rs),
            peak_repair_frames_max=max(r['peak_repair_frames'] for r in rs), avg_buffer_frames_mean=st.mean(r['avg_buffer_frames'] for r in rs), peak_buffer_frames_max=max(r['peak_buffer_frames'] for r in rs)))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out-dir',type=Path,default=Path('data')); ap.add_argument('--frames',type=int,default=2000); ap.add_argument('--epochs',type=int,default=250)
    a=ap.parse_args(); seeds=[0,1,2]; pis=[0,0.01,0.02,0.04,0.075,0.1,0.15,0.2]; ms=[4,8,16,32,64,128]
    mrows=[]
    for m in ms:
      for pi in pis:
        rows=[]
        for s in seeds:
          rows += [('modeA',frame_scheme(a.frames,pi,.2,.1,s+1,B_A,B_A/W+DCRC+DAEAD+DPROP)),('modeB_flush',mode_b_flush(a.epochs,m,pi,.2,.1,s+2)),('modeB_selective_retry',mode_b_sr(a.epochs,m,pi,.2,.1,s+3))]
        for r in agg(rows): r.update(experiment='m_sweep',M=m,piB=pi,beta=.2,p_bad=.1); mrows.append(r)
    crows=[]
    for beta in [.05,.1,.2,.5]:
      for pbad in [.01,.05,.1,.2]:
        for pi in pis:
          rows=[]
          for s in seeds:
            rows += [('crc_arq',frame_scheme(a.frames,pi,beta,pbad,s+10,B_CRC,B_CRC/W+DCRC)),('modeA',frame_scheme(a.frames,pi,beta,pbad,s+20,B_A,B_A/W+DCRC+DAEAD+DPROP)),('modeB_flush',mode_b_flush(a.epochs,32,pi,beta,pbad,s+30)),('modeB_selective_retry',mode_b_sr(a.epochs,32,pi,beta,pbad,s+40)),('adaptive_sr',adaptive_sr(a.epochs,pi,beta,pbad,s+50))]
          for r in agg(rows): r.update(experiment='channel_sweep',M=32,piB=pi,beta=beta,p_bad=pbad); crows.append(r)
    write(a.out_dir/'extended_m_sweep.csv',mrows); write(a.out_dir/'extended_channel_sweep.csv',crows)
    hi=[r for r in crows if r['beta']==.2 and r['p_bad']==.1 and r['piB'] in (.04,.1,.2)]
    write(a.out_dir/'extended_highlights.csv',hi)
    print('wrote extended experiment CSVs')
if __name__=='__main__': main()
