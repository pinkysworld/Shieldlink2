# ShieldLink-SR

Selective-retry epoch authentication for secure chiplet interconnects.

This repository is the follow-up artifact track for **ShieldLink-SR**, a proposed extension of the accepted ShieldLink work. The original ShieldLink paper introduced the Deliverability Invariant, requiring authenticated delivery before ACK and buffer retirement. ShieldLink-SR focuses on the main practical weakness of epoch authentication: flush-all retransmission under burst errors.

## Core idea

Original ShieldLink Mode B amortizes authentication by verifying an epoch of `M` frames with one epoch tag. That improves wire efficiency, but a single CRC-failed frame can force retransmission of the whole epoch. ShieldLink-SR keeps the epoch-level authentication boundary but adds selective repair:

- Track which epoch slots have been received.
- Track which slots failed CRC.
- Emit a bitmap NAK for only missing or corrupted slots.
- Retain good frames across repair rounds.
- Commit the epoch only when all slots are present, no CRC failures remain, and epoch AEAD verification succeeds.

The security rule remains unchanged:

```text
ACK / commit only after authenticated deliverability.
```

## Repository contents

- `rtl/` contains synthesizable SystemVerilog control-plane skeletons:
  - `baseline_ctrl_crc_arq.sv`
  - `shieldlink_ctrl_modeA.sv`
  - `shieldlink_ctrl_modeB_flush.sv`
  - `shieldlink_ctrl_modeB_sr.sv`
  - synthesis top modules for comparison
- `code/` contains the preliminary follow-up simulator and resource estimator.
- `data/` contains generated preliminary CSV results.
- `synth/` contains a Yosys synthesis helper script.
- `.github/workflows/` contains a GitHub Actions workflow for reproducible synthesis.
- `FOLLOWUP_PAPER_PLAN.md` outlines the planned paper.

## Preliminary result snapshot

The preliminary Monte Carlo simulator compares CRC+ARQ, ShieldLink Mode A, original Mode B flush-all, and Mode B selective retry under a Gilbert-Elliott burst-error model. At the default `M=32`, `p_bad=0.1`, and `beta=0.2` stress regime, selective retry preserves most of Mode B's wire-efficiency advantage while avoiding the flush-all goodput cliff.

Representative points from `data/selective_retry_followup_results.csv`:

| Bad-state probability | Mode B flush-all goodput | Mode B-SR goodput |
|---:|---:|---:|
| 0.04 | 0.8396 | 0.9225 |
| 0.10 | 0.7196 | 0.9167 |

These are preliminary simulation results, not final publication claims.

## Reproduce preliminary simulation

```bash
python3 code/sim_selective_retry_followup.py --out data/selective_retry_followup_results.csv
python3 code/resource_estimator_selective_retry.py --out data/modeB_sr_resource_sizing.csv
```

## Run synthesis comparison

Install Yosys, then run:

```bash
bash synth/run_yosys_synthesis.sh synth/out
```

The script compares:

- baseline CRC+ARQ
- ShieldLink Mode A
- ShieldLink Mode B flush-all
- ShieldLink Mode B-SR selective retry

The GitHub Actions workflow can also run the same script and upload synthesis outputs as an artifact.

## Scope and limitations

This repository currently provides control-plane RTL skeletons, simulation scripts, generated preliminary data, and synthesis automation. It does not yet include an integrated PHY, full AEAD cipher core, post-place-and-route timing, ASIC PPA, or validated CXL/UCIe traffic traces.

## License

MIT License. See `LICENSE`.
