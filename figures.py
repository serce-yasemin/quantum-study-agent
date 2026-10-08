"""
The pictures that go with a lesson - drawn by our own code, never by the model.

Each concept has a small catalogue of pictures. The model does not draw
anything: when it writes a lesson it only PICKS the one picture whose
description fits the idea it is teaching (or "none"). Code checks the pick
against the catalogue, exactly like the book sections in resources.py. So the
picture next to a lesson always belongs to that lesson, and every number in
it is computed.
"""

import numpy as np
import streamlit as st

import quantum_viz as qv

# concept -> {picture key: what it shows (this text is given to the model)}
CATALOGUE = {
    "state_vector": {
        "chances": "the two amplitudes a, b as an arrow of length 1; squaring "
                   "them gives the chances P(0) and P(1)",
        "normalize": "a vector that is too long or too short is scaled to length 1",
        "orthogonal": "a state and its orthogonal partner as two arrows at a "
                      "right angle; their inner product is 0",
        "phase": "the angles θ and φ place the state on the Bloch sphere; the "
                 "relative phase φ turns it without changing P(0) or P(1)",
    },
    "outer_product": {
        "outer_table": "any column vector times any row vector as a "
                       "multiplication table: entry (i, j) = column[i] · row[j]",
        "matrix": "the matrix |ψ⟩⟨ψ| of a chosen state as a coloured grid, next "
                  "to the state on the Bloch sphere",
    },
    "density_matrix": {
        "matrix": "the density matrix of a chosen pure state as a coloured grid "
                  "(diagonal = probabilities, off-diagonal = coherence)",
        "table": "how the entries of |ψ⟩⟨ψ| come from multiplying amplitudes",
    },
    "mixed_state": {
        "mixture": "mixing two states with weight p: the mixture moves along "
                   "the straight line between them, inside the sphere, and the "
                   "purity drops",
    },
    "bloch_sphere": {
        "point": "the angles θ, φ and the arrow length place a state on or "
                 "inside the Bloch sphere",
        "height": "the sphere seen from the side: the height z alone gives "
                  "P(0) = (1 + z)/2",
    },
    "single_qubit_gates": {
        "rotation": "a gate X, Z or H turns a chosen state half a turn around "
                    "an axis of the Bloch sphere (before and after)",
        "mirror": "in a flat cut through the sphere each gate acts like a "
                  "mirror: before and after arrows",
    },
    "measurement_bases": {
        "axis": "a state on the Bloch sphere and a measurement basis Z, X or Y "
                "drawn as an axis; the two chances come from where the arrow "
                "points along that axis",
        "shadow": "a flat cut through the sphere: the shadow of the state arrow "
                  "on a turnable measurement axis gives P = (1 + shadow)/2",
    },
    "two_qubits": {
        "tensor": "the tensor product [a; b] ⊗ [c; d] as a multiplication "
                  "table giving the four entries a·c, a·d, b·c, b·d",
        "gate2": "the four amplitudes of a two-qubit state as bars, before and "
                 "after a gate (X on one qubit, or CNOT)",
    },
    "entanglement": {
        "bell_circuit": "the four amplitudes step by step while H and then CNOT "
                        "turn a basis state into a Bell state, with the product "
                        "test p·s = q·r at each step",
        "how_entangled": "the state cos(t)|00⟩ + sin(t)|11⟩ for a chosen t: its "
                         "outcome probabilities and how far it is from a "
                         "product state",
    },
    "reduced_density_matrix": {
        "reduced": "the state cos(t)|00⟩ + sin(t)|11⟩ for a chosen t: the "
                   "reduced density matrix of qubit A, its point inside the "
                   "Bloch sphere and its purity",
        "partial_trace": "for a chosen two-qubit state: the 2×2 table M of its "
                         "amplitudes and the reduced density matrix ρ_A = M·M†",
    },
}


def options(concept: str) -> dict:
    return CATALOGUE.get(concept, {})


def valid(concept: str, key: str | None) -> str | None:
    """The picture to show: the picked key if it is in the catalogue, None if
    the lesson asked for no picture, else the concept's first picture."""
    choices = options(concept)
    if key in choices:
        return key
    if key == "none" or not choices:
        return None
    return next(iter(choices))


def _state(name: str) -> np.ndarray:
    return qv.density_from_state(qv.pure_state(*qv.NAMED_STATES[name]))


# Pictures that can start from the numbers of the lesson's worked example:
# picture key -> how many numbers it takes.
TAKES_NUMBERS = {"outer_table": 4, "normalize": 2, "tensor": 4}


def clean_numbers(key: str | None, numbers) -> list[float] | None:
    """The model may hand over the worked example's numbers so the picture
    starts from them. Accept them only if they are exactly the right count of
    small real numbers - otherwise the picture uses its own defaults."""
    want = TAKES_NUMBERS.get(key)
    try:
        values = [float(v) for v in numbers]
    except (TypeError, ValueError):
        return None
    if not want or len(values) != want or any(not -9 <= v <= 9 for v in values):
        return None
    return values


def show(concept: str, key: str, k: str, numbers: list[float] | None = None) -> None:
    """Draw one picture. k makes the widget keys unique (the same picture can
    be on the idea card and in an "I didn't get it" box). numbers: optional
    start values taken from the lesson's worked example."""
    chart = dict(width="stretch")
    if key == "chances":
        theta = st.slider("Turn the arrow", 0, 180, 60, key=f"{k}_t",
                          help="More turn = more |1⟩ in the state.")
        st.plotly_chart(qv.arrow_figure(theta), key=f"{k}_a", **chart)
        st.plotly_chart(qv.chance_bar(float(np.cos(np.radians(theta) / 2) ** 2)),
                        key=f"{k}_b", **chart)
        st.caption("The arrow is the qubit; it always has length 1. Its two "
                   "shadows are the amplitudes a and b. Square each shadow → the "
                   "two chances. They always fill the bar.")
    elif key == "outer_table":
        c1, c2, r1, r2 = numbers or [1.0, 2.0, 3.0, 4.0]
        st.caption("Change any number and watch the table.")
        cols = st.columns(4)
        column = [cols[0].number_input("column, top", -9.0, 9.0, c1, 1.0, key=f"{k}_c1"),
                  cols[1].number_input("column, bottom", -9.0, 9.0, c2, 1.0, key=f"{k}_c2")]
        row = [cols[2].number_input("row, left", -9.0, 9.0, r1, 1.0, key=f"{k}_r1"),
               cols[3].number_input("row, right", -9.0, 9.0, r2, 1.0, key=f"{k}_r2")]
        st.plotly_chart(qv.outer_table_figure(column, row), key=f"{k}_a", **chart)
        st.caption("A multiplication table: every entry of the column times every "
                   "entry of the row. Each row of the result is the row vector "
                   "scaled by one column entry. (If the row comes from a bra with "
                   "complex entries, those entries are the conjugates.)")
    elif key == "normalize":
        left, right = st.columns(2)
        x0, y0 = [min(5.0, abs(v)) for v in (numbers or [3.0, 4.0])]
        x = left.slider("first entry", 0.0, 5.0, x0, 0.5, key=f"{k}_x")
        y = right.slider("second entry", 0.0, 5.0, y0, 0.5, key=f"{k}_y")
        if x == 0 and y == 0:
            st.caption("The zero vector has no direction - it cannot be normalized.")
            return
        st.plotly_chart(qv.normalize_figure(x, y), key=f"{k}_a", **chart)
        length = float(np.hypot(x, y))
        st.code(f"length = √({x:g}² + {y:g}²) = {length:.3f}\n"
                f"divide both entries by it → [{x / length:.3f}; {y / length:.3f}]",
                language=None, wrap_lines=True)
        st.caption("Grey: the vector you start with. Blue: the same direction, "
                   "shrunk or stretched until it touches the dotted circle "
                   "(length 1). Only a length-1 vector is a qubit state.")
    elif key == "orthogonal":
        theta = st.slider("Turn the state |ψ⟩", 0, 180, 60, key=f"{k}_t")
        st.plotly_chart(qv.orthogonal_figure(theta), key=f"{k}_a", **chart)
        a = float(np.cos(np.radians(theta) / 2))
        b = float(np.sin(np.radians(theta) / 2))
        st.code(f"inner product = a·(−b) + b·a = {a:.2f}·({-b:.2f}) + {b:.2f}·{a:.2f} = 0",
                language=None, wrap_lines=True)
        st.caption("Swap the two entries and flip one sign: the partner arrow "
                   "always stands at a right angle to |ψ⟩. Right angle = inner "
                   "product 0 = orthogonal. (With complex entries you also take "
                   "the conjugates: [−b*; a*].)")
    elif key == "phase":
        theta = st.slider("θ - tilt the arrow away from |0⟩ (degrees)", 0, 180, 90,
                          key=f"{k}_t",
                          help="More tilt = more chance of measuring 1.")
        phi = st.slider("φ - turn the arrow around (degrees)", 0, 359, 0, key=f"{k}_p",
                        help="The relative phase. It does not change P(0) or P(1).")
        a, b = np.cos(np.radians(theta) / 2), np.sin(np.radians(theta) / 2)
        st.code(f"|ψ⟩ = {a:.3f}|0⟩ + {b:.3f}·e^(i·{phi}°)|1⟩\n"
                f"P(0) = {a * a:.3f}    P(1) = {b * b:.3f}", language=None, wrap_lines=True)
        rho = qv.density_from_state(qv.pure_state(theta, phi))
        st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": "|ψ⟩",
                                         "color": qv.COLOR_A}]), key=f"{k}_a", **chart)
        st.caption("θ changes the two chances. φ only turns the arrow around the "
                   "vertical line: the chances stay the same, but it is a "
                   "different state (φ = 0° is |+⟩, 180° is |−⟩ when θ = 90°).")
    elif key == "table":
        theta = st.slider("Change the state", 0, 180, 90, key=f"{k}_t")
        st.plotly_chart(qv.product_table_figure(theta), key=f"{k}_a", **chart)
        st.caption("A multiplication table: every entry of the column times every "
                   "entry of the row. The diagonal (a·a, b·b) holds the two chances.")
    elif key == "matrix":
        names = list(qv.NAMED_STATES)
        name = st.selectbox("State", names, index=names.index("|+⟩"), key=f"{k}_s")
        rho = _state(name)
        st.plotly_chart(qv.matrix_figure(rho, f"ρ = |ψ⟩⟨ψ| for {name}"),
                        key=f"{k}_a", **chart)
        st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": name,
                                         "color": qv.COLOR_A}]), key=f"{k}_b", **chart)
        st.caption("Pick a state: the matrix is |ψ⟩⟨ψ|. Diagonal = probabilities, "
                   "off-diagonal = coherence (it carries the phase).")
    elif key == "mixture":
        p = st.slider("p = share of |0⟩ in the mix (the rest is |+⟩)", 0.0, 1.0, 0.5,
                      0.05, key=f"{k}_p")
        rho_a, rho_b = _state("|0⟩"), _state("|+⟩")
        rho = qv.mix(p, rho_a, rho_b)
        st.metric("purity Tr(ρ²)", f"{qv.purity(rho):.3f}")
        st.plotly_chart(qv.bloch_figure([
            {"rho": rho_a, "label": "A |0⟩", "color": qv.COLOR_A},
            {"rho": rho_b, "label": "B |+⟩", "color": qv.COLOR_B},
            {"rho": rho, "label": "mixture", "color": qv.COLOR_MIX}], chord=True),
            key=f"{k}_a", **chart)
        st.caption("A mixture sits on the straight line between A and B - inside "
                   "the ball, not on its surface. Inside = purity below 1.")
    elif key == "point":
        theta = st.slider("θ (tilt from the top, degrees)", 0, 180, 60, key=f"{k}_t")
        phi = st.slider("φ (turn around the vertical axis, degrees)", 0, 359, 90,
                        key=f"{k}_p")
        r = st.slider("arrow length |r| (1 = pure)", 0.0, 1.0, 1.0, 0.05, key=f"{k}_r")
        th, ph = np.radians(theta), np.radians(phi)
        x, y, z = (r * np.sin(th) * np.cos(ph), r * np.sin(th) * np.sin(ph),
                   r * np.cos(th))
        rho = qv.rho_from_bloch(x, y, z)
        st.code(f"(x, y, z) = ({x + 0:.3f}, {y + 0:.3f}, {z + 0:.3f})\n"
                f"P(0) = (1 + z)/2 = {(1 + z) / 2:.3f}    "
                f"purity = {qv.purity(rho):.3f}", language=None, wrap_lines=True)
        st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": "state",
                                         "color": qv.COLOR_A}]), key=f"{k}_a", **chart)
        st.caption("θ sets the height (the probabilities), φ turns the arrow "
                   "around. Shorten the arrow to go inside: a mixed state.")
    elif key == "height":
        theta = st.slider("Tilt the arrow", 0, 180, 60, key=f"{k}_t")
        st.plotly_chart(qv.height_figure(theta), key=f"{k}_a", **chart)
        st.plotly_chart(qv.chance_bar((1 + float(np.cos(np.radians(theta)))) / 2),
                        key=f"{k}_b", **chart)
        st.caption("The sphere seen from the side. Only the height of the arrow tip "
                   "decides the chances: top = always 0, bottom = always 1, "
                   "middle = half and half.")
    elif key == "rotation":
        names = list(qv.NAMED_STATES)
        name = st.selectbox("Start state", names, index=0, key=f"{k}_s")
        gate = st.radio("Gate", list(qv.GATES), horizontal=True, key=f"{k}_g")
        before = _state(name)
        after = qv.apply_gate(gate, before)
        bx, by, bz = qv.bloch_vector(before) + 0.0
        ax, ay, az = qv.bloch_vector(after) + 0.0
        st.code(f"before: ({bx:.2f}, {by:.2f}, {bz:.2f})   P(0) = {(1 + bz) / 2:.2f}\n"
                f"after {gate}: ({ax:.2f}, {ay:.2f}, {az:.2f})   "
                f"P(0) = {(1 + az) / 2:.2f}", language=None, wrap_lines=True)
        st.plotly_chart(qv.bloch_figure([
            {"rho": before, "label": f"before {name}", "color": qv.COLOR_A},
            {"rho": after, "label": f"after {gate}", "color": qv.COLOR_B}],
            axis=qv.GATE_AXES[gate]), key=f"{k}_a", **chart)
        st.caption("Pick a start state and a gate. The gate turns the sphere half "
                   "a turn around the dashed axis.")
    elif key == "mirror":
        gate = st.radio("Gate", list(qv.GATES), horizontal=True, key=f"{k}_g")
        angle = st.slider("Start arrow (degrees from |0⟩)", 0, 359, 30, key=f"{k}_t")
        st.plotly_chart(qv.gate_slice_figure(gate, angle), key=f"{k}_a", **chart)
        st.caption("The sphere seen from the side. In this flat cut each gate works "
                   "like a mirror on the dashed line (in 3D: half a turn around "
                   "that line). An arrow lying on the line does not move.")
    elif key == "axis":
        theta = st.slider("θ - tilt of the state (degrees)", 0, 180, 106, key=f"{k}_t")
        phi = st.slider("φ - turn of the state (degrees)", 0, 359, 0, key=f"{k}_p")
        basis = st.radio("Measure in the basis", list(qv.BASIS_AXES), horizontal=True,
                         index=1, key=f"{k}_b")
        axis, names = qv.BASIS_AXES[basis]
        rho = qv.density_from_state(qv.pure_state(theta, phi))
        x, y, z = qv.bloch_vector(rho) + 0.0
        p0 = qv.basis_probability(rho, axis)
        st.code(f"Bloch vector r = ({x:.2f}, {y:.2f}, {z:.2f})\n"
                f"P({names[0]}) = (1 + r·n)/2 = {p0:.2f}    "
                f"P({names[1]}) = {1 - p0:.2f}", language=None, wrap_lines=True)
        st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": "|ψ⟩",
                                         "color": qv.COLOR_A}], axis=axis,
                                        axis_label="measurement axis"),
                        key=f"{k}_a", **chart)
        st.plotly_chart(qv.chance_bar(p0, names), key=f"{k}_c", **chart)
        st.caption("The dashed line is the question you ask. The closer the arrow "
                   "points to one end of that line, the more likely that answer. "
                   "Same state, different line → different chances.")
    elif key == "shadow":
        state = st.slider("State arrow (degrees from |0⟩)", 0, 359, 106, key=f"{k}_t")
        axis = st.slider("Measurement axis (degrees from |0⟩)", 0, 180, 90, key=f"{k}_n",
                         help="0° = the 0/1 basis, 90° = the +/− basis.")
        d = float(np.cos(np.radians(state - axis)))
        st.plotly_chart(qv.shadow_figure(state, axis), key=f"{k}_a", **chart)
        st.code(f"shadow r·n = {d + 0:.2f}\n"
                f"P(b₀) = (1 + {d + 0:.2f})/2 = {(1 + d) / 2:.2f}    "
                f"P(b₁) = {(1 - d) / 2:.2f}", language=None, wrap_lines=True)
        st.plotly_chart(qv.chance_bar((1 + d) / 2, ("b₀", "b₁")), key=f"{k}_c", **chart)
        st.caption("The thick line is the shadow of the arrow on the dashed "
                   "measurement axis. Long shadow toward b₀ → b₀ is almost "
                   "certain. No shadow (right angle) → half and half.")
    elif key == "tensor":
        a, b, c, d = numbers or [1.0, 2.0, 3.0, 4.0]
        st.caption("Change any number and watch the table.")
        cols = st.columns(4)
        first = [cols[0].number_input("first qubit, top", -9.0, 9.0, a, 0.1, key=f"{k}_a1"),
                 cols[1].number_input("first qubit, bottom", -9.0, 9.0, b, 0.1, key=f"{k}_a2")]
        second = [cols[2].number_input("second qubit, top", -9.0, 9.0, c, 0.1, key=f"{k}_b1"),
                  cols[3].number_input("second qubit, bottom", -9.0, 9.0, d, 0.1, key=f"{k}_b2")]
        st.plotly_chart(qv.outer_table_figure(first, second,
                                              ("first qubit, entry", "second qubit, entry")),
                        key=f"{k}_a", **chart)
        out = [x * y for x in first for y in second]
        st.code("read the table row by row:\n[" + "; ".join(f"{v + 0:g}" for v in out)
                + "]   (order 00, 01, 10, 11)", language=None, wrap_lines=True)
        st.caption("Each entry of the first vector multiplies the whole second "
                   "vector. Reading the table row by row gives the four entries "
                   "of the two-qubit state.")
    elif key == "gate2":
        names = list(qv.STATES2)
        name = st.selectbox("Start state", names, index=3, key=f"{k}_s")
        gate = st.radio("Gate", ["X on first", "X on second", "CNOT"], horizontal=True,
                        index=2, key=f"{k}_g")
        before = np.array(qv.STATES2[name], dtype=complex)
        after = qv.GATES2[gate] @ before
        st.plotly_chart(qv.amplitude_bars(before, after, ("before", f"after {gate}")),
                        key=f"{k}_a", **chart)
        st.caption("A gate only moves amplitudes between the four boxes. X on the "
                   "first qubit swaps 00 ↔ 10 and 01 ↔ 11; CNOT swaps 10 ↔ 11 (it "
                   "flips the second qubit only when the first is 1).")
    elif key == "bell_circuit":
        start = st.selectbox("Start state", qv.KETS2, key=f"{k}_s")
        step = st.radio("Step", ["start", "after H on first", "after CNOT"],
                        horizontal=True, index=2, key=f"{k}_g")
        state = np.zeros(4, dtype=complex)
        state[qv.KETS2.index(start)] = 1
        if step != "start":
            state = qv.GATES2["H on first"] @ state
        if step == "after CNOT":
            state = qv.CNOT @ state
        p, q, r, s_ = np.real(state) + 0.0
        gap = qv.product_gap(state)
        st.plotly_chart(qv.amplitude_bars(state), key=f"{k}_a", **chart)
        st.code(f"p·s = {p * s_ + 0:.2f}    q·r = {q * r + 0:.2f}    →  "
                + ("equal: a product state" if gap < 1e-9 else "not equal: entangled"),
                language=None, wrap_lines=True)
        st.caption("H spreads the first qubit over 0 and 1 - still a product "
                   "state. CNOT then ties the second qubit to the first: only "
                   "two boxes are left, and the state is entangled.")
    elif key in ("how_entangled", "reduced"):
        t = st.slider("t (degrees) in cos(t)|00⟩ + sin(t)|11⟩", 0, 90, 45, key=f"{k}_t",
                      help="0° = |00⟩, 45° = Bell state, 90° = |11⟩.")
        c, s_ = float(np.cos(np.radians(t))), float(np.sin(np.radians(t)))
        state = [c, 0, 0, s_]
        if key == "how_entangled":
            st.plotly_chart(qv.amplitude_bars(state, squared=True), key=f"{k}_a", **chart)
            st.code(f"state = {c:.2f}|00⟩ + {s_:.2f}|11⟩\n"
                    f"p·s − q·r = {c * s_:.2f}   (0 = product state, 0.5 = Bell state)",
                    language=None, wrap_lines=True)
            st.caption("The two results always agree. At 0° or 90° there is "
                       "nothing to correlate (a product state); at 45° the state "
                       "is a Bell state - as entangled as two qubits can be.")
        else:
            rho = qv.reduced_a(state)
            st.code(f"state = {c:.2f}|00⟩ + {s_:.2f}|11⟩\n"
                    f"ρ_A = [[{c * c:.2f}, 0], [0, {s_ * s_:.2f}]]    "
                    f"purity Tr(ρ_A²) = {qv.purity(rho):.3f}", language=None, wrap_lines=True)
            st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": "qubit A alone",
                                             "color": qv.COLOR_MIX}]),
                            key=f"{k}_a", **chart)
            st.caption("The more entangled the pair, the deeper qubit A alone sits "
                       "inside the ball. At 45° (Bell state) it is at the centre: "
                       "completely random on its own.")
    elif key == "partial_trace":
        names = list(qv.STATES2)
        name = st.selectbox("Two-qubit state", names, index=names.index("Bell |Φ+⟩"),
                            key=f"{k}_s")
        p, q, r, s_ = [float(v) for v in qv.STATES2[name]]
        rho = qv.reduced_a(qv.STATES2[name])
        st.code(f"M = [[{p:.3f}, {q:.3f}],     rows: qubit A\n"
                f"     [{r:.3f}, {s_:.3f}]]     columns: qubit B", language=None, wrap_lines=True)
        st.plotly_chart(qv.matrix_figure(rho, "ρ_A = M·M†"), key=f"{k}_a", **chart)
        st.metric("purity Tr(ρ_A²)", f"{qv.purity(rho):.3f}")
        st.caption("Each entry of ρ_A is one row of M times another row of M. "
                   "Purity 1 = A has a state of its own (product state); "
                   "below 1 = A is entangled with B.")
