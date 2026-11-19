"""Quantum teleportation of one qubit state from Alice to Bob.

Qubits: q0 = Alice's message, q1 = Alice's half of a Bell pair, q2 = Bob's half.
The message state is |psi> = Rz(phi) Ry(theta) |0>, so it is fully set by two angles.
"""
from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


def _prepare(qc: QuantumCircuit, qubit: int, theta: float, phi: float) -> None:
    qc.ry(theta, qubit)
    qc.rz(phi, qubit)


def _unprepare(qc: QuantumCircuit, qubit: int, theta: float, phi: float) -> None:
    qc.rz(-phi, qubit)
    qc.ry(-theta, qubit)


def teleport_coherent(theta: float, phi: float) -> QuantumCircuit:
    """Deferred-measurement version: no measurements, corrections are controlled gates.

    Equivalent to the textbook protocol, and lets us check Bob's exact state
    with a statevector.
    """
    qc = QuantumCircuit(3, name="teleport_coherent")
    _prepare(qc, 0, theta, phi)
    qc.barrier()
    qc.h(1)
    qc.cx(1, 2)          # Bell pair shared by Alice (q1) and Bob (q2)
    qc.barrier()
    qc.cx(0, 1)          # Alice's Bell-basis measurement, part 1
    qc.h(0)              # part 2
    qc.barrier()
    qc.cx(1, 2)          # Bob's X correction (controlled by Alice's q1 result)
    qc.cz(0, 2)          # Bob's Z correction (controlled by Alice's q0 result)
    return qc


def teleport_dynamic(theta: float, phi: float, verify: bool = True,
                     apply_corrections: bool = True) -> QuantumCircuit:
    """Textbook version with mid-circuit measurement and classically controlled gates.

    If verify=True, Bob's qubit is rotated back with the inverse of the preparation
    and measured: a perfect teleport gives 0 every time.
    apply_corrections=False skips Bob's X/Z fixes (a negative control: it should fail).
    """
    q = QuantumRegister(3, "q")
    m0 = ClassicalRegister(1, "m0")   # Alice's result for q0 -> Z fix
    m1 = ClassicalRegister(1, "m1")   # Alice's result for q1 -> X fix
    regs = [q, m0, m1]
    out = ClassicalRegister(1, "bob") if verify else None
    if out is not None:
        regs.append(out)
    qc = QuantumCircuit(*regs, name="teleport_dynamic")

    _prepare(qc, 0, theta, phi)
    qc.barrier()
    qc.h(1)
    qc.cx(1, 2)
    qc.barrier()
    qc.cx(0, 1)
    qc.h(0)
    qc.measure(0, m0[0])
    qc.measure(1, m1[0])
    qc.barrier()
    if apply_corrections:
        with qc.if_test((m1, 1)):
            qc.x(2)
        with qc.if_test((m0, 1)):
            qc.z(2)
    if verify:
        qc.barrier()
        _unprepare(qc, 2, theta, phi)
        qc.measure(2, out[0])
    return qc
