#!/usr/bin/env python3
"""Generate SVG figures from the extended ShieldLink-SR experiment CSVs."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def plot_goodput_pi(data_dir: Path, fig_dir: Path) -> None:
    df = pd.read_csv(data_dir / "extended_channel_sweep.csv")
    df = df[(df["M"] == 32) & (df["beta"] == 0.2) & (df["p_bad"] == 0.1)]
    plt.figure()
    for scheme in ["modeA", "modeB_flush", "modeB_selective_retry", "adaptive_sr"]:
        s = df[df["scheme"] == scheme].sort_values("piB")
        plt.plot(s["piB"], s["goodput_mean"], marker="o", label=scheme)
    plt.xlabel("Bad-state probability piB")
    plt.ylabel("Normalized goodput")
    plt.title("Goodput under burst errors, M=32, beta=0.2, p_bad=0.1")
    plt.grid(True, alpha=0.3)
    plt.legend()
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(fig_dir / "goodput_vs_piB_default.svg", bbox_inches="tight")
    plt.close()

def plot_p99_pi(data_dir: Path, fig_dir: Path) -> None:
    df = pd.read_csv(data_dir / "extended_channel_sweep.csv")
    df = df[(df["M"] == 32) & (df["beta"] == 0.2) & (df["p_bad"] == 0.1)]
    plt.figure()
    for scheme in ["modeA", "modeB_flush", "modeB_selective_retry", "adaptive_sr"]:
        s = df[df["scheme"] == scheme].sort_values("piB")
        plt.plot(s["piB"], s["p99_latency_mean"], marker="o", label=scheme)
    plt.xlabel("Bad-state probability piB")
    plt.ylabel("p99 commit latency, cycles")
    plt.title("Tail latency under burst errors, M=32, beta=0.2, p_bad=0.1")
    plt.grid(True, alpha=0.3)
    plt.legend()
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(fig_dir / "p99_latency_vs_piB_default.svg", bbox_inches="tight")
    plt.close()

def plot_m_sweep(data_dir: Path, fig_dir: Path) -> None:
    df = pd.read_csv(data_dir / "extended_m_sweep.csv")
    df = df[(df["piB"] == 0.1) & (df["beta"] == 0.2) & (df["p_bad"] == 0.1)]
    plt.figure()
    for scheme in ["modeB_flush", "modeB_selective_retry"]:
        s = df[df["scheme"] == scheme].sort_values("M")
        plt.plot(s["M"], s["goodput_mean"], marker="o", label=scheme)
    plt.xscale("log", base=2)
    plt.xlabel("Epoch size M")
    plt.ylabel("Normalized goodput")
    plt.title("Epoch-size sensitivity at piB=0.1")
    plt.grid(True, alpha=0.3)
    plt.legend()
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(fig_dir / "m_sweep_goodput_piB_0p10.svg", bbox_inches="tight")
    plt.close()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--fig-dir", type=Path, default=Path("figures"))
    args = ap.parse_args()
    plot_goodput_pi(args.data_dir, args.fig_dir)
    plot_p99_pi(args.data_dir, args.fig_dir)
    plot_m_sweep(args.data_dir, args.fig_dir)
    print(f"Wrote SVG figures to {args.fig_dir}")

if __name__ == "__main__":
    main()
