import math

import numpy as np
import pytest
from qiskit.quantum_info import DensityMatrix, Statevector, partial_trace, state_fidelity
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit import transpile

from qteleport import teleport_coherent, teleport_dynamic
from qteleport.run import STATES, success_probability

ANGLES = [(0.0, 0.0), (math.pi / 2, 0.0), (1.1, 2.3), (math.pi, 0.5), (2.7, -1.3)]


def target_state(theta, phi):
    qc = QuantumCircuit(1)
    qc.ry(theta, 0)
    qc.rz(phi, 0)
    return Statevector.from_instruction(qc)


@pytest.mark.parametrize("theta,phi", ANGLES)
def test_coherent_teleport_gives_bob_the_exact_state(theta, phi):
    final = Statevector.from_instruction(teleport_coherent(theta, phi))
    bob = partial_trace(final, [0, 1])          # trace out Alice's two qubits
    assert state_fidelity(bob, target_state(theta, phi)) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("theta,phi", ANGLES)
def test_dynamic_teleport_ideal_simulator_is_perfect(theta, phi):
    be = AerSimulator(seed_simulator=1)
    assert success_probability(theta, phi, be, corrections=True) == 1.0


def test_without_corrections_teleport_fails():
    # Without the X/Z fixes Bob's qubit, averaged over Alice's 4 random outcomes,
    # is maximally mixed, so any check on it is a coin flip: P(success) = 0.5,
    # clearly below the 1.0 of the corrected protocol.
    be = AerSimulator(seed_simulator=1)
    p = success_probability(*STATES["generic"], be, corrections=False)
    assert 0.4 < p < 0.6


def test_circuits_have_expected_registers():
    qc = teleport_dynamic(0.3, 0.4)
    assert qc.num_qubits == 3
    assert [c.name for c in qc.cregs] == ["m0", "m1", "bob"]
    assert teleport_dynamic(0.3, 0.4, verify=False).num_clbits == 2
