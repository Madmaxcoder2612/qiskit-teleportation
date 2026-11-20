"""Simulate teleportation: ideal vs noisy, with and without Bob's corrections.

Usage:  python -m qteleport.run [--noisy] [--sweep] [--out results]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from .circuits import teleport_dynamic

SHOTS = 4096
SEED = 42
# (theta, phi) test states: |0>-ish, |+>, a generic state, |1>
STATES = {
    "zero": (0.0, 0.0),
    "plus": (math.pi / 2, 0.0),
    "generic": (1.1, 2.3),
    "one": (math.pi, 0.0),
}


SWEEP_P2 = [0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]  # two-qubit error rates swept


def make_backend(noisy: bool, p1: float = 0.001, p2: float = 0.01) -> AerSimulator:
    """Aer simulator, ideal or with depolarizing noise (p1 one-qubit, p2 two-qubit)."""
    if not noisy:
        return AerSimulator(seed_simulator=SEED)
    nm = NoiseModel()
    # Illustrative error rates, NOT calibrated to any real IBM device.
    if p1 > 0:
        nm.add_all_qubit_quantum_error(depolarizing_error(p1, 1), ["h", "x", "z", "u", "sx", "rz", "ry"])
    if p2 > 0:
        nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["cx"])
    return AerSimulator(noise_model=nm, seed_simulator=SEED)


def success_probability(theta: float, phi: float, backend, corrections: bool) -> float:
    """P(Bob's verification bit == 0). 1.0 means perfect teleportation."""
    qc = teleport_dynamic(theta, phi, verify=True, apply_corrections=corrections)
    counts = backend.run(transpile(qc, backend, seed_transpiler=SEED), shots=SHOTS).result().get_counts()
    zeros = sum(v for k, v in counts.items() if k.split()[0] == "0")  # 'bob' register is leftmost
    return zeros / SHOTS


def noise_sweep(state: str = "generic", p2_values=SWEEP_P2) -> dict[float, float]:
    """Success probability against two-qubit error rate p2 (one-qubit rate is p2/10)."""
    theta, phi = STATES[state]
    return {p2: success_probability(theta, phi, make_backend(True, p1=p2 / 10, p2=p2), True)
            for p2 in p2_values}


def plot_sweep(sweep: dict[float, float], out: Path, state: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(list(sweep), list(sweep.values()), "o-", label="with corrections")
    ax.axhline(0.5, ls="--", color="gray", label="no corrections (coin flip)")
    ax.set_xlabel("two-qubit depolarizing error rate (one-qubit rate = a tenth of it)")
    ax.set_ylabel("P(Bob's check = 0)")
    ax.set_ylim(0.4, 1.02)
    ax.set_title(f"Teleportation against noise ('{state}' state, {SHOTS} shots)")
    ax.legend(loc="upper right")
    fig.savefig(out / "noise_sweep.png", dpi=120, bbox_inches="tight")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--noisy", action="store_true")
    ap.add_argument("--sweep", action="store_true",
                    help="sweep the two-qubit error rate and save noise_sweep.png and summary_sweep.json")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.sweep:
        sweep = noise_sweep()
        for p2, p in sweep.items():
            print(f"p2 = {p2:<6} success {p:.3f}")
        (out / "summary_sweep.json").write_text(
            json.dumps({"state": "generic", "shots": SHOTS, "seed": SEED,
                        "success_by_p2": {str(k): round(v, 4) for k, v in sweep.items()}}, indent=2))
        plot_sweep(sweep, out, "generic")
        return
    tag = "noisy" if args.noisy else "ideal"
    backend = make_backend(args.noisy)

    table = {}
    for name, (th, ph) in STATES.items():
        with_c = success_probability(th, ph, backend, True)
        without_c = success_probability(th, ph, backend, False)
        table[name] = {"theta": th, "phi": ph, "with_corrections": round(with_c, 4),
                       "without_corrections": round(without_c, 4)}
        print(f"{name:8s} with corrections {with_c:.3f} | without {without_c:.3f}")
    (out / f"summary_{tag}.json").write_text(json.dumps(table, indent=2))

    fig, ax = plt.subplots(figsize=(6, 3.5))
    xs = range(len(table))
    ax.bar([x - 0.2 for x in xs], [v["with_corrections"] for v in table.values()], 0.4, label="with corrections")
    ax.bar([x + 0.2 for x in xs], [v["without_corrections"] for v in table.values()], 0.4, label="without corrections")
    ax.set_xticks(list(xs), list(table))
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("P(Bob's check = 0)")
    ax.set_title(f"Teleportation success ({tag}, {SHOTS} shots)")
    ax.legend(loc="lower left")
    fig.savefig(out / f"success_{tag}.png", dpi=120, bbox_inches="tight")
    teleport_dynamic(*STATES["generic"]).draw("mpl").savefig(out / "teleport_circuit.png", dpi=120, bbox_inches="tight")


if __name__ == "__main__":
    main()
