"""
Hands-on labs for the Explore tab. Every number here is computed by numpy;
the model is not involved, so the labs cost no API credits.

- circuit_lab:  put up to four gates in a row and follow the state on the
                Bloch sphere step by step.
- measure_lab:  measure a qubit many times and watch the counts approach the
                predicted probabilities.
- pair_lab:     measure two qubits many times, in the 0/1 basis or the +/−
                basis, and see which pairs are correlated.
"""

import numpy as np
import streamlit as st

import figures
import quantum_viz as qv
import ui

def _colors() -> list[str]:
    return [qv.COLOR_A, qv.COLOR_B, qv.COLOR_MIX, qv.INK, "#9b59b6"]


# Single-qubit gates the circuit lab knows by name, to say what a whole
# circuit amounts to ("H, Z, H is the same as X").
_NAMED_U = {"I (do nothing)": np.eye(2), "X": qv.GATES["X"], "Z": qv.GATES["Z"],
            "H": qv.GATES["H"], "Y = iXZ": 1j * qv.GATES["X"] @ qv.GATES["Z"]}


def _same_up_to_phase(u: np.ndarray, v: np.ndarray) -> bool:
    k = np.vdot(v.flatten(), u.flatten())
    return abs(abs(k) - 2) < 1e-9          # |Tr(V†U)| = 2 only if U = e^(iα)V


def circuit_lab() -> None:
    st.caption("Pick a start state and up to four gates. The gates act from left "
               "to right; the sphere shows the state after every step.")
    names = list(qv.NAMED_STATES)
    start = st.selectbox("Start state", names, index=0, key="lab_c_start")
    cols = st.columns(4)
    gates = [cols[i].selectbox(f"Gate {i + 1}", ["—", "X", "Z", "H"],
                               index=[3, 2, 3, 0][i], key=f"lab_c_g{i}")
             for i in range(4)]
    gates = [g for g in gates if g != "—"]
    rho = qv.density_from_state(qv.pure_state(*qv.NAMED_STATES[start]))
    colors = _colors()
    points = [{"rho": rho, "label": f"start {start}", "color": colors[0]}]
    rows = [("start", rho)]
    total = np.eye(2, dtype=complex)
    for n, g in enumerate(gates, 1):
        rho = qv.apply_gate(g, rho)
        total = qv.GATES[g] @ total
        points.append({"rho": rho, "label": f"{n}: after {g}",
                       "color": colors[n % len(colors)]})
        rows.append((f"after {g}", rho))
    st.plotly_chart(qv.bloch_figure(points), width="stretch", key="lab_c_fig")
    ui.cards([{"top": f"step {i}" if i else "start", "title": label,
               "sub": "Bloch ({:.2f}, {:.2f}, {:.2f}) · P(0) = {:.2f}".format(
                   *(qv.bloch_vector(r) + 0.0), r[0, 0].real)}
              for i, (label, r) in enumerate(rows)], min_px=170)
    if gates:
        same = [n for n, u in _NAMED_U.items() if _same_up_to_phase(total, u)]
        written = " · ".join(reversed(gates))
        st.info(f"The whole circuit is one matrix: **{written}** (the first gate "
                "is written on the right). "
                + (f"It does the same as **{same[0]}** (up to a global phase)."
                   if same else "It is not one of X, Z, H, Y or I."))


def _sample(probs: np.ndarray, shots: int) -> np.ndarray:
    rng = np.random.default_rng()
    return rng.multinomial(shots, np.clip(probs, 0, None) / np.clip(probs, 0, None).sum())


def _counter(key: str, setting: tuple, size: int) -> np.ndarray:
    """Counts that belong to the current settings; reset when they change."""
    box = st.session_state.setdefault(key, {"setting": None, "counts": None})
    if box["setting"] != setting:
        box["setting"], box["counts"] = setting, np.zeros(size, dtype=int)
    return box["counts"]


def _shot_buttons(key: str) -> int:
    c1, c2, c3, c4 = st.columns(4)
    shots = 0
    if c1.button("Measure once", key=f"{key}_1", width="stretch"):
        shots = 1
    if c2.button("Measure 10×", key=f"{key}_10", width="stretch"):
        shots = 10
    if c3.button("Measure 100×", key=f"{key}_100", width="stretch"):
        shots = 100
    if c4.button("Start over", key=f"{key}_0", width="stretch"):
        shots = -1
    return shots


def measure_lab() -> None:
    st.caption("A measurement gives ONE answer, at random. The probabilities only "
               "show up when you repeat it many times on fresh copies of the "
               "same state. Try it.")
    left, right = st.columns([1, 1])
    with left:
        theta = st.slider("θ - tilt of the state (degrees)", 0, 180, 60, key="lab_m_t")
        phi = st.slider("φ - relative phase (degrees)", 0, 359, 0, key="lab_m_p")
        basis = st.radio("Measure in the basis", list(qv.BASIS_AXES), horizontal=True,
                         key="lab_m_b")
    axis, names = qv.BASIS_AXES[basis]
    rho = qv.density_from_state(qv.pure_state(theta, phi))
    p0 = qv.basis_probability(rho, axis)
    with right:
        st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": "|ψ⟩", "color": qv.COLOR_A}],
                                        axis=axis, axis_label="measurement axis"),
                        width="stretch", key="lab_m_fig")
    counts = _counter("lab_m_counts", (theta, phi, basis), 2)
    shots = _shot_buttons("lab_m")
    if shots == -1:
        counts[:] = 0
    elif shots:
        counts += _sample(np.array([p0, 1 - p0]), shots)
    total = int(counts.sum())
    st.plotly_chart(qv.counts_figure([names[0], names[1]], counts, [p0, 1 - p0]),
                    width="stretch", key="lab_m_counts_fig")
    ui.stats([("measurements", total),
              (f"seen {names[0]}", f"{counts[0] / total:.0%}" if total else "—",
               f"predicted {p0:.0%}"),
              (f"seen {names[1]}", f"{counts[1] / total:.0%}" if total else "—",
               f"predicted {1 - p0:.0%}")])
    if 0 < total < 30:
        st.caption("With few measurements the share can be far from the prediction. "
                   "Keep measuring and watch it settle.")


_PAIRS = {
    "Bell |Φ+⟩ = (|00⟩ + |11⟩)/√2": [qv._S, 0, 0, qv._S],
    "Bell |Ψ−⟩ = (|01⟩ − |10⟩)/√2": [0, qv._S, -qv._S, 0],
    "0.8|00⟩ + 0.6|11⟩": [0.8, 0, 0, 0.6],
    "product |+⟩|+⟩": [0.5, 0.5, 0.5, 0.5],
    "product |0⟩|+⟩": [qv._S, qv._S, 0, 0],
}


def pair_lab() -> None:
    st.caption("Two qubits are measured together, many times. Do the two answers "
               "agree? Measure in the 0/1 basis, then in the +/− basis.")
    left, right = st.columns([1, 1])
    with left:
        name = st.selectbox("Two-qubit state", list(_PAIRS), key="lab_p_s")
        basis = st.radio("Both qubits measured in", ["0/1 (Z)", "+/− (X)"],
                         horizontal=True, key="lab_p_b")
    state = np.array(_PAIRS[name], dtype=complex)
    if basis.startswith("+"):
        hh = np.kron(qv.GATES["H"], qv.GATES["H"])   # H on both, then read 0/1
        state = hh @ state
        labels = ["++", "+−", "−+", "−−"]
    else:
        labels = ["00", "01", "10", "11"]
    probs = np.abs(state) ** 2
    with right:
        ui.stats([("p·s − q·r", f"{qv.product_gap(_PAIRS[name]):.2f}",
                   "0 = product state"),
                  ("purity of one qubit",
                   f"{qv.purity(qv.reduced_a(_PAIRS[name])):.2f}", "1 = not entangled")])
    counts = _counter("lab_p_counts", (name, basis), 4)
    shots = _shot_buttons("lab_p")
    if shots == -1:
        counts[:] = 0
    elif shots:
        counts += _sample(probs, shots)
    total = int(counts.sum())
    st.plotly_chart(qv.counts_figure(labels, counts, probs), width="stretch",
                    key="lab_p_fig")
    agree = counts[0] + counts[3]
    ui.stats([("measurements", total),
              ("answers agree", f"{agree / total:.0%}" if total else "—",
               f"predicted {probs[0] + probs[3]:.0%}"),
              ("first qubit alone: first outcome",
               f"{(counts[0] + counts[1]) / total:.0%}" if total else "—",
               f"predicted {probs[0] + probs[1]:.0%}")], min_px=160)
    st.caption("A Bell state agrees (or disagrees) every time, in BOTH bases, while "
               "each qubit alone is a fair coin. A product state can be "
               "predictable in one basis, but then it is random in the other.")


def pair_parts_lab() -> None:
    st.caption("Make a Bell state step by step, then look at one qubit of the pair "
               "on its own.")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Making entanglement: H, then CNOT**")
        figures.show("entanglement", "bell_circuit", "lab_e1")
    with right:
        st.markdown("**One qubit of the pair, alone**")
        figures.show("reduced_density_matrix", "reduced", "lab_e2")
