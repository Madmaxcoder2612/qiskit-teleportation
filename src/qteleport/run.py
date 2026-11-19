"""Simulate teleportation: ideal vs noisy, with and without Bob's corrections.

Usage:  python -m qteleport.run [--noisy] [--out results]
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


def make_backend(noisy: bool) -> AerSimulator:
    if not noisy:
        return AerSimulator(seed_simulator=SEED)
    nm = NoiseModel()
    # Illustrative error rates, NOT calibrated to any real IBM device.
    nm.add_all_qubit_quantum_error(depolarizing_error(0.001, 1), ["h", "x", "z", "u", "sx", "rz", "ry"])
    nm.add_all_qubit_quantum_error(depolarizing_error(0.01, 2), ["cx"])
    return AerSimulator(noise_model=nm, seed_simulator=SEED)


def success_probability(theta: float, phi: float, backend, corrections: bool) -> float:
    """P(Bob's verification bit == 0). 1.0 means perfect teleportation."""
    qc = teleport_dynamic(theta, phi, verify=True, apply_corrections=corrections)
    counts = backend.run(transpile(qc, backend, seed_transpiler=SEED), shots=SHOTS).result().get_counts()
    zeros = sum(v for k, v in counts.items() if k.split()[0] == "0")  # 'bob' register is leftmost
    return zeros / SHOTS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--noisy", action="store_true")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
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
