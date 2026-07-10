#!/usr/bin/env python3
"""Generate publication-oriented SVG figures from checked-in validation CSVs."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def save(d,n):d.mkdir(parents=True,exist_ok=True);plt.savefig(d/n,bbox_inches='tight');plt.close()
def main():
 p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,default=Path('data'));p.add_argument('--fig-dir',type=Path,default=Path('figures'));a=p.parse_args()
 df=pd.read_csv(a.data_dir/'protocol_realism_summary.csv');x=df[(df.experiment=='adversarial')&df.adversary.isin(['none','one_per_epoch','tag_target','repeat_repair'])]
 x.pivot(index='adversary',columns='scheme',values='goodput_mean').reindex(['none','one_per_epoch','tag_target','repeat_repair']).plot(kind='bar');plt.ylabel('Normalized goodput');plt.xlabel('Fault schedule');plt.title('Adversarial availability');plt.xticks(rotation=20,ha='right');save(a.fig_dir,'adversarial_goodput.svg')
 x=df[df.experiment=='workload_pipeline']
 for w in sorted(x.workload.unique()):
  s=x[x.workload==w].sort_values('pipeline_depth');plt.plot(s.pipeline_depth,s.throughput_payload_B_per_cycle_mean,marker='o',label=w)
 plt.xlabel('Outstanding epoch depth');plt.ylabel('Payload bytes per cycle');plt.title('Pipelining sensitivity');plt.legend();save(a.fig_dir,'pipeline_throughput.svg')
 x=pd.read_csv(a.data_dir/'adaptive_ablation_summary.csv').sort_values('utility_mean',ascending=False).head(10);plt.barh(x.policy[::-1],x.utility_mean[::-1]);plt.xlabel('Utility');plt.title('Adaptive policy ablation');save(a.fig_dir,'adaptive_policy_utility.svg')
 x=pd.read_csv(a.data_dir/'trace_replay_summary.csv');x=x[x.M==32]
 for c in sorted(x['class'].unique()):
  s=x[x['class']==c].sort_values('pipeline_depth');plt.plot(s.pipeline_depth,s.p99_latency,marker='o',label=c)
 plt.xlabel('Outstanding epoch depth');plt.ylabel('p99 transaction latency, cycles');plt.title('Synthetic trace replay, M=32');plt.legend();save(a.fig_dir,'trace_replay_p99.svg')
 print(f'wrote figures to {a.fig_dir}')
if __name__=='__main__':main()
