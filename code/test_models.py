#!/usr/bin/env python3
import unittest
from protocol_realism_experiments import WORKLOADS,run_mode_b,run_mode_a

class ModelTests(unittest.TestCase):
    def test_selective_retry_beats_flush_under_bursts(self):
        common=dict(epochs=400,m=32,pi_bad=.1,beta=.2,p_bad=.1,seed=7,workload=WORKLOADS['packet256'],timeout_cycles=64,tag_policy='repair_authenticator',pipeline_depth=1)
        flush=run_mode_b(selective=False,**common).summarize();sr=run_mode_b(selective=True,**common).summarize()
        self.assertGreater(sr['goodput'],flush['goodput']);self.assertLess(sr['p99_latency_cycles'],flush['p99_latency_cycles'])
    def test_pipeline_improves_throughput_not_goodput(self):
        common=dict(epochs=200,m=32,pi_bad=.1,beta=.2,p_bad=.1,seed=9,selective=True,workload=WORKLOADS['packet256'],timeout_cycles=64,tag_policy='repair_authenticator')
        one=run_mode_b(pipeline_depth=1,**common).summarize();four=run_mode_b(pipeline_depth=4,**common).summarize()
        self.assertAlmostEqual(one['goodput'],four['goodput']);self.assertGreater(four['throughput_payload_B_per_cycle'],one['throughput_payload_B_per_cycle'])
    def test_tag_attack_is_security_drop(self):
        r=run_mode_b(epochs=20,m=8,pi_bad=0,beta=.2,p_bad=.1,seed=1,selective=True,workload=WORKLOADS['packet256'],timeout_cycles=64,tag_policy='repair_authenticator',pipeline_depth=1,adversary='tag_target').summarize()
        self.assertEqual(r['security_drops'],20)
    def test_fec_costs_goodput_on_clean_channel(self):
        common=dict(frames=320,pi_bad=0,beta=.2,p_bad=.1,seed=2,workload=WORKLOADS['packet256'],timeout_cycles=64)
        self.assertLess(run_mode_a(fec_t=1,**common).summarize()['goodput'],run_mode_a(fec_t=0,**common).summarize()['goodput'])
if __name__=='__main__':unittest.main()
