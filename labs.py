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


# ---------- "what this means" texts ----------
# Each lab shows a few plain sentences that react to the current settings,
# and a few small challenges ("Try this"). Computed here, not by the model.

TRIES = {
    "pure": ["Pick |+⟩, then |−⟩. Which numbers stay the same, which change?",
             "Choose custom, keep θ = 90° and move φ. Which entries of the matrix change?",
             "Find a state with P(0) = 0.75. Is there more than one?"],
    "mix": ["Mix |0⟩ and |1⟩ with p = 0.5. Where is the point, and what is the purity?",
            "Mix |+⟩ with |+⟩. Why does nothing change?",
            "For |0⟩ and |+⟩, which p gives the lowest purity?"],
    "circuit": ["Turn |0⟩ into |1⟩ using only H and Z.",
                "Find two gates in a row that bring |0⟩ back to |0⟩.",
                "Which single gate is H, X, H? Check the box under the sphere."],
    "measure": ["Find a state that gives + every time in the X basis but 50/50 in Z.",
                "Press Start over and Measure 10× a few times: how far does the share jump?",
                "Keep the state and switch Z → X → Y. Which basis is certain, which is random?"],
    "pair": ["Bell Φ+: measure in 0/1, then in +/−. Do the answers still agree?",
             "|+⟩|+⟩: in which basis do the answers always agree? Why is it still not "
             "entangled?",
             "Compare Bell Ψ− with Φ+: what changes in the answers?"],
    "parts": ["At which step does p·s stop being equal to q·r?",
              "Move t to 0°, 45° and 90°. Where is qubit A on the sphere each time?",
              "At 45° qubit A is at the centre: what does that say about measuring it alone?"],
}


def _name(rho: np.ndarray) -> str | None:
    """The landmark name of a pure state (|0⟩, |+⟩, …) if it is one."""
    r = qv.bloch_vector(rho)
    for name, angles in qv.NAMED_STATES.items():
        if np.allclose(r, qv.bloch_vector(qv.density_from_state(qv.pure_state(*angles))),
                       atol=1e-6):
            return name
    return None


def _call(rho: np.ndarray) -> str:
    return _name(rho) or "the state ({:.2f}, {:.2f}, {:.2f})".format(*(qv.bloch_vector(rho) + 0.0))


def pure_insight(rho: np.ndarray, name: str) -> list[str]:
    p0 = rho[0, 0].real
    out = [f"P(0) = {p0:.2f}: measured in the 0/1 basis, {name} gives 0 in "
           f"{p0:.0%} of the cases and 1 in {1 - p0:.0%}."]
    if abs(rho[0, 1]) < 1e-9:
        out.append("The coherence is 0: this state has no relative phase to show. It "
                   "sits at the top or the bottom of the sphere.")
    else:
        out.append(f"The coherence |ρ₀₁| = {abs(rho[0, 1]):.2f} carries the relative "
                   "phase. Changing φ turns the arrow around the vertical axis: the "
                   "diagonal (the chances) stays, only the off-diagonal entries change.")
    out.append("Purity is 1 and the arrow touches the surface: a pure state is known "
               "completely, even when its measurement result is random.")
    return out


def mix_insight(p: float, rho_a, rho_b, rho) -> list[str]:
    pur = qv.purity(rho)
    length = float(np.linalg.norm(qv.bloch_vector(rho)))
    out = [f"The mixture is {p:.0%} of A and {1 - p:.0%} of B. It sits on the straight "
           f"line between them, {length:.2f} from the centre (1 = surface)."]
    if np.allclose(rho_a, rho_b):
        out.append("A and B are the same state, so mixing them changes nothing: "
                   "purity stays 1.")
    elif pur > 0.999:
        out.append("With p at 0 or 1 you simply have one of the two states: pure again.")
    else:
        out.append(f"Purity {pur:.2f} < 1: this is a mixed state. It is not a "
                   "superposition - it describes NOT KNOWING which of the two states "
                   "was prepared.")
    if length < 0.05:
        out.append("The point is at the centre: the maximally mixed state I/2. "
                   "Every measurement on it is 50/50.")
    return out


def _step_text(g: str, before: np.ndarray, after: np.ndarray) -> str:
    p_b, p_a = before[0, 0].real, after[0, 0].real
    if np.allclose(before, after, atol=1e-9):
        return (f"{g} left {_call(before)} where it was: the state lies on the "
                f"axis that {g} turns around.")
    if abs(p_b - p_a) < 1e-9:
        return (f"{g} turned {_call(before)} into {_call(after)}. P(0) stayed "
                f"{p_a:.2f}: only the phase changed. A 0/1 measurement cannot see this, "
                "an X-basis measurement can.")
    return (f"{g} turned {_call(before)} into {_call(after)}: P(0) went from "
            f"{p_b:.2f} to {p_a:.2f}.")


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
    notes = []
    for n, g in enumerate(gates, 1):
        notes.append(f"Step {n}: " + _step_text(g, rho, qv.apply_gate(g, rho)))
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
    ui.explain(notes or ["Choose a gate: each one turns the sphere half a turn "
                         "around its own axis (X: x axis, Z: z axis, H: halfway "
                         "between x and z)."], TRIES["circuit"])


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
    notes = []
    if p0 > 0.995 or p0 < 0.005:
        sure = names[0] if p0 > 0.5 else names[1]
        notes.append(f"The arrow lies on the measurement axis, so the answer is "
                     f"always {sure}. No randomness at all.")
    elif abs(p0 - 0.5) < 0.005:
        notes.append("The arrow is at a right angle to the measurement axis: exactly "
                     "50/50. The state is perfectly known - the question just does "
                     "not fit it.")
    else:
        lean = names[0] if p0 > 0.5 else names[1]
        notes.append(f"The arrow leans toward the {lean} end of the axis, so {lean} "
                     f"comes up more often: P({names[0]}) = (1 + r·n)/2 = {p0:.2f}.")
    if total:
        spread = 2 * np.sqrt(p0 * (1 - p0) / total)
        seen = counts[0] / total
        notes.append(f"After {total} measurements {names[0]} came up {seen:.0%} of the "
                     f"time (predicted {p0:.0%}). With {total} measurements a "
                     f"difference of up to about ±{spread:.0%} is normal chance"
                     + (" - yours is inside that." if abs(seen - p0) <= spread + 1e-9
                        else " - yours is a little outside; it happens about 1 time in "
                             "20. Keep measuring."))
    else:
        notes.append("Press a Measure button. One measurement gives one answer; "
                     "the probability only appears after many.")
    notes.append("Changing the basis keeps the state but changes the question, so "
                 "the chances change. Changing φ only matters in the X and Y bases.")
    ui.explain(notes, TRIES["measure"])


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
    pa = probs[0] + probs[3]
    gap = qv.product_gap(_PAIRS[name])
    which = "+/−" if basis.startswith("+") else "0/1"
    notes = [("In the " + which + " basis the two answers "
              + ("ALWAYS agree." if pa > 0.999 else "NEVER agree - they are always opposite."
                 if pa < 0.001 else f"agree {pa:.0%} of the time."))]
    first = probs[0] + probs[1]
    notes.append(f"The first qubit alone gives its first outcome {first:.0%} of the time"
                 + (" - on its own it is a fair coin." if abs(first - 0.5) < 1e-6 else "."))
    if gap > 1e-9:
        notes.append(f"p·s − q·r = {gap:.2f} ≠ 0: the pair is entangled. The answers are "
                     "linked even though each one alone is random. Switch the basis: "
                     + ("a Bell state stays perfectly linked in both." if gap > 0.499
                        else "the link is weaker than for a Bell state."))
    else:
        notes.append("p·s − q·r = 0: a product state. Any agreement comes from each "
                     "qubit being predictable by itself, not from a link - switch "
                     "the basis and it disappears.")
    ui.explain(notes, TRIES["pair"])


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
    ui.explain(["Before CNOT the state is still a product (p·s = q·r): each qubit "
                "has its own state. CNOT ties the second qubit to the first.",
                "The more entangled the pair (t closer to 45°), the deeper qubit A "
                "alone sits inside the sphere: the pair is known exactly, but each "
                "part on its own is mixed."], TRIES["parts"])
