# Trace input format

`trace_replay_experiments.py` accepts a CSV with these columns:

```text
arrival_cycle,flow_id,class,payload_bytes,deadline_cycles
```

Generate the bundled deterministic synthetic workload with:

```bash
python3 code/generate_synthetic_trace.py --out traces/synthetic_mixed_workload.csv
```

The generated workload is synthetic and trace-inspired. It is not a measured CXL or UCIe trace. External traces can be converted to the same schema for comparative experiments.
