#!/usr/bin/env python3
"""Fail fast on physically or semantically inconsistent generated results."""
import argparse
from pathlib import Path
import pandas as pd

EPS=1e-9

def one(df,**filters):
    x=df
    for k,v in filters.items():x=x[x[k]==v]
    if len(x)!=1:raise AssertionError(f'expected one row for {filters}, got {len(x)}')
    return x.iloc[0]

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,default=Path('data'));a=p.parse_args()
    pcol=pd.read_csv(a.data_dir/'protocol_realism_summary.csv')
    sr=one(pcol,experiment='adversarial',scheme='sr',adversary='none',tag_policy='repair_authenticator',workload='packet256',pipeline_depth=1,fec_t=0)
    flush=one(pcol,experiment='adversarial',scheme='flush',adversary='none',tag_policy='repair_authenticator',workload='packet256',pipeline_depth=1,fec_t=0)
    tag=one(pcol,experiment='adversarial',scheme='sr',adversary='tag_target',tag_policy='repair_authenticator',workload='packet256',pipeline_depth=1,fec_t=0)
    assert sr.goodput_mean>flush.goodput_mean
    assert tag.goodput_mean==0 and tag.delivery_ratio_mean==0 and tag.security_drops_mean>0
    assert pcol.throughput_payload_B_per_cycle_mean.max()<=8.0+EPS
    trace=pd.read_csv(a.data_dir/'trace_replay_summary.csv')
    d1=one(trace,**{'class':'packet','M':32,'pipeline_depth':1})
    d2=one(trace,**{'class':'packet','M':32,'pipeline_depth':2})
    assert d2.mean_latency<=d1.mean_latency
    adaptive=pd.read_csv(a.data_dir/'adaptive_ablation_summary.csv')
    oracle=one(adaptive,policy='offline_oracle').utility_mean
    assert oracle+EPS>=adaptive[adaptive.policy!='offline_oracle'].utility_mean.max()
    baseline=pd.read_csv(a.data_dir/'baseline_comparison.csv')
    assert one(baseline,scheme='selective_arq_no_auth').security=='none'
    print('validation invariants PASS')
if __name__=='__main__':main()
