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
        "table": "the outer product as a multiplication table: column entry "
                 "times row entry",
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


def show(concept: str, key: str, k: str) -> None:
    """Draw one picture. k makes the widget keys unique (the same picture can
    be on the idea card and in an "I didn't get it" box)."""
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
    elif key == "normalize":
        left, right = st.columns(2)
        x = left.slider("first entry", 0.0, 5.0, 3.0, 0.5, key=f"{k}_x")
        y = right.slider("second entry", 0.0, 5.0, 4.0, 0.5, key=f"{k}_y")
        if x == 0 and y == 0:
            st.caption("The zero vector has no direction - it cannot be normalized.")
            return
        st.plotly_chart(qv.normalize_figure(x, y), key=f"{k}_a", **chart)
        length = float(np.hypot(x, y))
        st.code(f"length = √({x:g}² + {y:g}²) = {length:.3f}\n"
                f"divide both entries by it → [{x / length:.3f}; {y / length:.3f}]",
                language=None)
        st.caption("Grey: the vector you start with. Blue: the same direction, "
                   "shrunk or stretched until it touches the dotted circle "
                   "(length 1). Only a length-1 vector is a qubit state.")
    elif key == "orthogonal":
        theta = st.slider("Turn the state |ψ⟩", 0, 180, 60, key=f"{k}_t")
        st.plotly_chart(qv.orthogonal_figure(theta), key=f"{k}_a", **chart)
        a = float(np.cos(np.radians(theta) / 2))
        b = float(np.sin(np.radians(theta) / 2))
        st.code(f"inner product = a·(−b) + b·a = {a:.2f}·({-b:.2f}) + {b:.2f}·{a:.2f} = 0",
                language=None)
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
                f"P(0) = {a * a:.3f}    P(1) = {b * b:.3f}", language=None)
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
                f"purity = {qv.purity(rho):.3f}", language=None)
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
                f"P(0) = {(1 + az) / 2:.2f}", language=None)
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
