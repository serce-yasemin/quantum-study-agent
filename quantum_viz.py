"""
Visual building blocks for single-qubit states: the math (numpy) and the
figures (plotly). No LLM calls here - every number on screen is computed
exactly, so the visuals are a trustworthy reference next to the AI tutor.

Convention (same as tutor.CONVENTIONS):
    |ψ⟩ = cos(θ/2)|0⟩ + e^(iφ) sin(θ/2)|1⟩
    ρ = ½ (I + x·σx + y·σy + z·σz),  Bloch vector r = (x, y, z)
    ρ₀₁ = ½ (x − i·y)  →  relative phase φ = −arg(ρ₀₁)
"""

import numpy as np
import plotly.graph_objects as go

# Categorical slots 1-3 of the validated default palette, stepped separately
# for light and dark surfaces. Sequential blue ramp: near-zero recedes toward
# the surface in both modes.
THEMES = {
    "light": dict(COLOR_A="#2a78d6", COLOR_B="#eb6834", COLOR_MIX="#1baf7a",
                  INK="#52514e", GRID="#d9d8d4", TEXT="#0b0b0b", RING="#ffffff",
                  SEQ_BLUE=[[0.0, "#cde2fb"], [0.35, "#86b6ef"],
                            [0.7, "#2a78d6"], [1.0, "#184f95"]],
                  CELL_DARK_ABOVE=0.55),
    "dark": dict(COLOR_A="#3987e5", COLOR_B="#d95926", COLOR_MIX="#199e70",
                 INK="#c3c2b7", GRID="#4a4a46", TEXT="#ffffff", RING="#1a1a19",
                 SEQ_BLUE=[[0.0, "#1c2a3d"], [0.35, "#1c5cab"],
                           [0.7, "#3987e5"], [1.0, "#9ec5f4"]],
                 CELL_DARK_ABOVE=None),
}
COLOR_A = COLOR_B = COLOR_MIX = INK = GRID = TEXT = RING = None
SEQ_BLUE = CELL_DARK_ABOVE = None


def set_theme(dark: bool) -> None:
    """Switch every figure color to the light or dark palette."""
    globals().update(THEMES["dark" if dark else "light"])


set_theme(False)

PAULI = {
    "x": np.array([[0, 1], [1, 0]], dtype=complex),
    "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "z": np.array([[1, 0], [0, -1]], dtype=complex),
}

NAMED_STATES = {
    "|0⟩": (0.0, 0.0),
    "|1⟩": (180.0, 0.0),
    "|+⟩": (90.0, 0.0),
    "|−⟩": (90.0, 180.0),
    "|+i⟩": (90.0, 90.0),
    "|−i⟩": (90.0, 270.0),
}


GATES = {
    "X": PAULI["x"],
    "Z": PAULI["z"],
    "H": (PAULI["x"] + PAULI["z"]) / np.sqrt(2),
}
# The axis each gate turns the Bloch sphere around (by half a turn).
GATE_AXES = {"X": (1.0, 0.0, 0.0), "Z": (0.0, 0.0, 1.0),
             "H": (1 / np.sqrt(2), 0.0, 1 / np.sqrt(2))}


# ---------- math ----------

def rho_from_bloch(x: float, y: float, z: float) -> np.ndarray:
    """ρ = ½ (I + x·σx + y·σy + z·σz)"""
    return 0.5 * (np.eye(2) + x * PAULI["x"] + y * PAULI["y"] + z * PAULI["z"])


def apply_gate(gate: str, rho: np.ndarray) -> np.ndarray:
    """ρ → U ρ U†"""
    u = GATES[gate]
    return u @ rho @ u.conj().T


def pure_state(theta_deg: float, phi_deg: float) -> np.ndarray:
    th, ph = np.radians(theta_deg), np.radians(phi_deg)
    return np.array([np.cos(th / 2), np.exp(1j * ph) * np.sin(th / 2)])


def density_from_state(psi: np.ndarray) -> np.ndarray:
    return np.outer(psi, psi.conj())


def mix(p: float, rho_a: np.ndarray, rho_b: np.ndarray) -> np.ndarray:
    """ρ = p·ρA + (1 − p)·ρB"""
    return p * rho_a + (1 - p) * rho_b


def bloch_vector(rho: np.ndarray) -> np.ndarray:
    return np.array([np.real(np.trace(rho @ PAULI[k])) for k in "xyz"])


def purity(rho: np.ndarray) -> float:
    return float(np.real(np.trace(rho @ rho)))


def fmt_complex(z: complex, digits: int = 3) -> str:
    re, im = round(z.real, digits) + 0.0, round(z.imag, digits) + 0.0
    if abs(im) < 10 ** -digits:
        return f"{re:.{digits}f}"
    if abs(re) < 10 ** -digits:
        return f"{im:.{digits}f}i"
    sign = "+" if im >= 0 else "−"
    return f"{re:.{digits}f} {sign} {abs(im):.{digits}f}i"


# ---------- figures ----------

def bloch_figure(points: list[dict], chord: bool = False,
                 axis: tuple | None = None,
                 axis_label: str = "rotation axis") -> go.Figure:
    """points: [{"rho": ndarray, "label": str, "color": hex}, ...]
    chord=True draws the dashed segment between the first two points - every
    mixture of them lies on it."""
    fig = go.Figure()

    # Recessive wireframe sphere: 3 great circles + a few latitude rings.
    t = np.linspace(0, 2 * np.pi, 120)
    rings = [
        (np.cos(t), np.sin(t), 0 * t),
        (np.cos(t), 0 * t, np.sin(t)),
        (0 * t, np.cos(t), np.sin(t)),
    ]
    for lat in (-0.5, 0.5):
        r = np.sqrt(1 - lat ** 2)
        rings.append((r * np.cos(t), r * np.sin(t), lat + 0 * t))
    for x, y, z in rings:
        fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines",
                                   line=dict(color=GRID, width=2),
                                   hoverinfo="skip", showlegend=False))

    # Axes with pole labels.
    axes = {"x": ((-1.15, 1.15), (0, 0), (0, 0)),
            "y": ((0, 0), (-1.15, 1.15), (0, 0)),
            "z": ((0, 0), (0, 0), (-1.15, 1.15))}
    for x, y, z in axes.values():
        fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines",
                                   line=dict(color=INK, width=2),
                                   hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter3d(
        x=[0, 0, 1.3, -1.3, 0, 0], y=[0, 0, 0, 0, 1.3, -1.3],
        z=[1.3, -1.3, 0, 0, 0, 0],
        mode="text", text=["|0⟩", "|1⟩", "|+⟩", "|−⟩", "|+i⟩", "|−i⟩"],
        textfont=dict(color=INK, size=13), hoverinfo="skip", showlegend=False))

    if chord and len(points) >= 2:
        (ax, ay, az), (bx, by, bz) = (bloch_vector(points[0]["rho"]),
                                      bloch_vector(points[1]["rho"]))
        fig.add_trace(go.Scatter3d(x=[ax, bx], y=[ay, by], z=[az, bz], mode="lines",
                                   line=dict(color=INK, width=3, dash="dash"),
                                   name="all mixtures of A and B",
                                   hoverinfo="skip"))

    if axis is not None:                    # the line a gate turns the sphere around
        ax, ay, az = (1.25 * np.array(axis)).tolist()
        fig.add_trace(go.Scatter3d(x=[-ax, ax], y=[-ay, ay], z=[-az, az], mode="lines",
                                   line=dict(color=COLOR_MIX, width=5, dash="dash"),
                                   name=axis_label, hoverinfo="skip"))

    # State vectors: line from origin + marker at the tip, directly labeled.
    for pt in points:
        x, y, z = bloch_vector(pt["rho"])
        length = float(np.sqrt(x * x + y * y + z * z))
        fig.add_trace(go.Scatter3d(
            x=[0, x], y=[0, y], z=[0, z], mode="lines",
            line=dict(color=pt["color"], width=6),
            hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z], mode="markers+text",
            marker=dict(size=7, color=pt["color"],
                        line=dict(color=RING, width=2)),
            text=[pt["label"]], textposition="top center",
            textfont=dict(color=TEXT, size=13),
            name=pt["label"],
            hovertemplate=(f"<b>{pt['label']}</b><br>"
                           "x = %{x:.3f}<br>y = %{y:.3f}<br>z = %{z:.3f}<br>"
                           f"|r| = {length:.3f}<extra></extra>")))

    fig.update_layout(
        height=480, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.02, x=0.5, xanchor="center"),
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            zaxis=dict(visible=False), aspectmode="cube",
            camera=dict(eye=dict(x=1.0, y=0.8, z=0.5)),
        ),
    )
    return fig


def _cell_ink(value: float) -> str:
    """White ink on dark cells, near-black on light cells (both modes)."""
    if CELL_DARK_ABOVE is None:          # dark mode: ramp gets LIGHTER with value
        return "#0b0b0b" if value > 0.75 else "#ffffff"
    return "#ffffff" if value > CELL_DARK_ABOVE else "#0b0b0b"


def matrix_figure(rho: np.ndarray, title: str, show_scale: bool = True) -> go.Figure:
    """Heat map of |ρᵢⱼ| (sequential blue) with the exact complex entry printed
    in each cell, so color is never the only carrier of the value."""
    mag = np.abs(rho)
    labels = [[fmt_complex(rho[i, j]) for j in range(2)] for i in range(2)]
    roles = [["P(0)", "coherence ρ₀₁"], ["coherence ρ₁₀", "P(1)"]]
    text = [[f"{labels[i][j]}<br><span style='font-size:11px'>{roles[i][j]}</span>"
             for j in range(2)] for i in range(2)]
    fig = go.Figure(go.Heatmap(
        z=mag, x=["|0⟩", "|1⟩"], y=["⟨0|", "⟨1|"],
        zmin=0, zmax=1, colorscale=SEQ_BLUE, xgap=2, ygap=2,
        showscale=show_scale,
        colorbar=dict(title=dict(text="|ρᵢⱼ|"), thickness=10, len=0.8),
        hovertemplate="%{y} ρ %{x}<br>|ρᵢⱼ| = %{z:.3f}<extra></extra>",
    ))
    # Per-cell ink: white on the dark end of the ramp, near-black elsewhere.
    for i in range(2):
        for j in range(2):
            fig.add_annotation(x=j, y=i, text=text[i][j], showarrow=False,
                               font=dict(size=15,
                                         color=_cell_ink(mag[i, j])))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=300, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed"),
    )
    return fig


# ---------- simple pictures for "I didn't get it" ----------

def arrow_figure(theta_deg: float) -> go.Figure:
    """A qubit with real amplitudes as an arrow of length 1 in a flat plane.
    Its shadow on each axis is an amplitude (a, b); squaring gives the chances."""
    a = float(np.cos(np.radians(theta_deg) / 2))
    b = float(np.sin(np.radians(theta_deg) / 2))
    arc = np.linspace(0, np.pi / 2, 60)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.cos(arc), y=np.sin(arc), mode="lines",
                             line=dict(color=GRID, width=2, dash="dot"),
                             hoverinfo="skip"))
    for x0, y0, x1, y1 in ((a, 0, a, b), (0, b, a, b)):         # the two shadows
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                      line=dict(color=INK, width=1, dash="dash"))
    fig.add_annotation(x=a, y=b, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y",
                       arrowhead=3, arrowsize=1.2, arrowwidth=4, arrowcolor=COLOR_A,
                       text="")
    fig.add_annotation(x=a, y=b, text="|ψ⟩  (length 1)", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(color=TEXT, size=14))
    fig.add_annotation(x=a, y=-0.07, text=f"a = {a:.2f}", showarrow=False,
                       font=dict(color=COLOR_A, size=14))
    fig.add_annotation(x=-0.04, y=b, text=f"b = {b:.2f}", showarrow=False,
                       xanchor="right", font=dict(color=COLOR_B, size=14))
    axis = dict(range=[-0.22, 1.25], showgrid=False, zeroline=True,
                zerolinecolor=INK, showticklabels=False, fixedrange=True)
    fig.update_layout(
        xaxis=dict(title=dict(text="how much |0⟩"), **axis),
        yaxis=dict(title=dict(text="how much |1⟩"), scaleanchor="x", **axis),
        showlegend=False, height=330, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT))
    return fig


def chance_bar(p0: float, names: tuple = ("0", "1")) -> go.Figure:
    """One bar of length 1, split into the chance of the two outcomes."""
    fig = go.Figure()
    for value, name, color in ((p0, names[0], COLOR_A), (1 - p0, names[1], COLOR_B)):
        fig.add_trace(go.Bar(
            x=[value], y=[""], orientation="h", marker=dict(color=color),
            text=f"chance of {name}: {value:.0%}" if value >= 0.12 else "",
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color="#ffffff", size=14),
            hovertemplate=f"chance of {name}: {value:.1%}<extra></extra>"))
    fig.update_layout(
        barmode="stack", showlegend=False, height=90,
        margin=dict(l=10, r=10, t=5, b=5),
        xaxis=dict(range=[0, 1], visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def product_table_figure(theta_deg: float) -> go.Figure:
    """|ψ⟩⟨ψ| as a multiplication table: column entry times row entry."""
    a = float(np.cos(np.radians(theta_deg) / 2))
    b = float(np.sin(np.radians(theta_deg) / 2))
    v = [a, b]
    names = ["a", "b"]
    z = [[v[i] * v[j] for j in range(2)] for i in range(2)]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"a = {a:.2f}", f"b = {b:.2f}"], y=[f"a = {a:.2f}", f"b = {b:.2f}"],
        zmin=0, zmax=1, colorscale=SEQ_BLUE, xgap=2, ygap=2, showscale=False,
        hoverinfo="skip"))
    for i in range(2):
        for j in range(2):
            fig.add_annotation(
                x=j, y=i, showarrow=False,
                text=f"{names[i]}·{names[j]}<br><b>{z[i][j]:.2f}</b>",
                font=dict(size=15, color=_cell_ink(z[i][j])))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(side="top", title=dict(text="row ⟨ψ|"), fixedrange=True),
        yaxis=dict(autorange="reversed", title=dict(text="column |ψ⟩"),
                   fixedrange=True),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT))
    return fig



def _slice_base(fig: go.Figure) -> None:
    """The flat cut through the Bloch sphere that holds |0⟩, |1⟩, |+⟩, |−⟩."""
    t = np.linspace(0, 2 * np.pi, 120)
    fig.add_trace(go.Scatter(x=np.cos(t), y=np.sin(t), mode="lines",
                             line=dict(color=GRID, width=2), hoverinfo="skip"))
    for (x, y, label) in ((0, 1.14, "|0⟩"), (0, -1.14, "|1⟩"),
                          (1.16, 0, "|+⟩"), (-1.16, 0, "|−⟩")):
        fig.add_annotation(x=x, y=y, text=label, showarrow=False,
                           font=dict(color=INK, size=14))
    axis = dict(range=[-1.45, 1.45], showgrid=False, zeroline=True,
                zerolinecolor=GRID, showticklabels=False, fixedrange=True)
    fig.update_layout(
        xaxis=axis, yaxis=dict(scaleanchor="x", **axis), showlegend=False,
        height=360, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT))


def _slice_arrow(fig: go.Figure, x: float, z: float, color: str, label: str) -> None:
    fig.add_annotation(x=x, y=z, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y",
                       arrowhead=3, arrowsize=1.2, arrowwidth=4, arrowcolor=color,
                       text="")
    fig.add_annotation(x=1.13 * x, y=1.13 * z, text=label, showarrow=False,
                       font=dict(color=color, size=14))


def height_figure(theta_deg: float) -> go.Figure:
    """Side view of the Bloch sphere: the height z of the arrow tip sets the
    chance of measuring 0, P(0) = (1 + z)/2."""
    th = np.radians(theta_deg)
    x, z = float(np.sin(th)), float(np.cos(th))
    fig = go.Figure()
    _slice_base(fig)
    fig.add_shape(type="line", x0=0, y0=z, x1=x, y1=z,
                  line=dict(color=INK, width=1, dash="dash"))
    fig.add_shape(type="line", x0=-1.4, y0=-1, x1=-1.4, y1=1,      # height ruler
                  line=dict(color=INK, width=2))
    fig.add_trace(go.Scatter(x=[-1.4], y=[z], mode="markers",
                             marker=dict(color=COLOR_A, size=12), hoverinfo="skip"))
    fig.add_annotation(x=-1.37, y=z, xanchor="left", yanchor="bottom", showarrow=False,
                       text=f"height z = {z:.2f}", font=dict(color=COLOR_A, size=13))
    _slice_arrow(fig, x, z, COLOR_A, "|ψ⟩")
    return fig


def gate_slice_figure(gate: str, angle_deg: float) -> go.Figure:
    """Before and after a gate, for a state in the flat cut through |0⟩, |+⟩,
    |1⟩, |−⟩. In this cut each gate acts like a mirror (dashed line)."""
    a = np.radians(angle_deg)
    x, z = float(np.sin(a)), float(np.cos(a))
    x2, _, z2 = bloch_vector(apply_gate(gate, rho_from_bloch(x, 0.0, z)))
    mirror = {"X": (1.3, 0.0), "Z": (0.0, 1.3), "H": (0.95, 0.95)}[gate]
    fig = go.Figure()
    _slice_base(fig)
    fig.add_shape(type="line", x0=-mirror[0], y0=-mirror[1], x1=mirror[0], y1=mirror[1],
                  line=dict(color=COLOR_MIX, width=3, dash="dash"))
    _slice_arrow(fig, x, z, COLOR_A, "before")
    _slice_arrow(fig, float(x2), float(z2), COLOR_B, f"after {gate}")
    return fig


def _flat_axes(fig: go.Figure, lo: float, hi: float, height: int = 340) -> None:
    axis = dict(range=[lo, hi], showgrid=False, zeroline=True, zerolinecolor=INK,
                showticklabels=False, fixedrange=True)
    fig.update_layout(
        xaxis=dict(title=dict(text="how much |0⟩"), **axis),
        yaxis=dict(title=dict(text="how much |1⟩"), scaleanchor="x", **axis),
        showlegend=False, height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT))


def _flat_arrow(fig: go.Figure, x: float, y: float, color: str, label: str,
                width: int = 4, below: bool = False) -> None:
    fig.add_annotation(x=x, y=y, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y",
                       arrowhead=3, arrowsize=1.2, arrowwidth=width, arrowcolor=color,
                       text="")
    fig.add_annotation(x=x, y=y, text=label, showarrow=False,
                       xanchor="left" if x >= 0 else "right",
                       yanchor="top" if below else "bottom",
                       font=dict(color=color, size=14))


def orthogonal_figure(theta_deg: float) -> go.Figure:
    """A state with real amplitudes [a; b] and its orthogonal partner [−b; a]:
    two arrows of length 1 at a right angle. Their inner product is 0."""
    a = float(np.cos(np.radians(theta_deg) / 2))
    b = float(np.sin(np.radians(theta_deg) / 2))
    t = np.linspace(0, 2 * np.pi, 120)
    fig = go.Figure(go.Scatter(x=np.cos(t), y=np.sin(t), mode="lines",
                               line=dict(color=GRID, width=2, dash="dot"),
                               hoverinfo="skip"))
    s = 0.13                                           # the little right-angle mark
    fig.add_trace(go.Scatter(x=[s * a, s * (a - b), -s * b], y=[s * b, s * (a + b), s * a],
                             mode="lines", line=dict(color=INK, width=2),
                             hoverinfo="skip"))
    _flat_arrow(fig, a, b, COLOR_A, f"|ψ⟩ = [{a:.2f}; {b:.2f}]")
    _flat_arrow(fig, -b, a, COLOR_B, f"partner = [{-b:.2f}; {a:.2f}]")
    _flat_axes(fig, -1.5, 1.5, height=380)
    return fig


def normalize_figure(x: float, y: float) -> go.Figure:
    """A vector that is too long or too short (grey) and the same direction
    scaled to length 1 (blue): divide both entries by the length."""
    length = float(np.hypot(x, y)) or 1.0
    arc = np.linspace(0, np.pi / 2, 60)
    fig = go.Figure(go.Scatter(x=np.cos(arc), y=np.sin(arc), mode="lines",
                               line=dict(color=GRID, width=2, dash="dot"),
                               hoverinfo="skip"))
    fig.add_annotation(x=1.0, y=-0.02, text="length 1", showarrow=False,
                       xanchor="center", yanchor="top", font=dict(color=INK, size=12))
    _flat_arrow(fig, x, y, INK, f"before: [{x:g}; {y:g}], length {length:.2f}", width=2)
    _flat_arrow(fig, x / length, y / length, COLOR_A,
                f"  after: [{x / length:.2f}; {y / length:.2f}]", below=True)
    top = max(1.3, x + 0.6, y + 0.6)
    _flat_axes(fig, -0.25, top, height=380)
    return fig


def outer_table_figure(column: list[float], row: list[float],
                       names: tuple = ("column entry", "row entry")) -> go.Figure:
    """Any column times any row as a multiplication table: entry (i, j) of
    the outer product is column[i] · row[j]."""
    z = [[c * r for r in row] for c in column]
    top = max(1.0, max(abs(v) for line in z for v in line))
    fig = go.Figure(go.Heatmap(
        z=[[abs(v) / top for v in line] for line in z],
        x=[f"{names[1]} {j + 1}:  {r:g}" for j, r in enumerate(row)],
        y=[f"{names[0]} {i + 1}:  {c:g}" for i, c in enumerate(column)],
        zmin=0, zmax=1, colorscale=SEQ_BLUE, xgap=2, ygap=2, showscale=False,
        hoverinfo="skip"))
    for i, c in enumerate(column):
        for j, r in enumerate(row):
            fig.add_annotation(
                x=j, y=i, showarrow=False,
                text=f"{c:g} · {r:g}<br><b>{c * r:g}</b>",
                font=dict(size=15, color=_cell_ink(abs(c * r) / top)))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(side="top", fixedrange=True),
        yaxis=dict(autorange="reversed", fixedrange=True),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT))
    return fig


# ---------- measuring in other bases ----------

BASIS_AXES = {"Z": ((0.0, 0.0, 1.0), ("0", "1")),
              "X": ((1.0, 0.0, 0.0), ("+", "−")),
              "Y": ((0.0, 1.0, 0.0), ("+i", "−i"))}


def basis_probability(rho: np.ndarray, axis: tuple) -> float:
    """P(first state of the basis) = (1 + r·n)/2."""
    return float((1 + np.dot(bloch_vector(rho), axis)) / 2)


def shadow_figure(state_deg: float, axis_deg: float) -> go.Figure:
    """Flat cut through the sphere: the shadow of the state arrow on the
    measurement axis sets the two chances."""
    a, n = np.radians(state_deg), np.radians(axis_deg)
    x, z = float(np.sin(a)), float(np.cos(a))
    nx, nz = float(np.sin(n)), float(np.cos(n))
    d = x * nx + z * nz                                   # r·n
    fig = go.Figure()
    _slice_base(fig)
    fig.add_shape(type="line", x0=-1.3 * nx, y0=-1.3 * nz, x1=1.3 * nx, y1=1.3 * nz,
                  line=dict(color=COLOR_MIX, width=3, dash="dash"))
    fig.add_annotation(x=1.36 * nx, y=1.36 * nz, text="b₀", showarrow=False,
                       font=dict(color=COLOR_MIX, size=14))
    fig.add_annotation(x=-1.36 * nx, y=-1.36 * nz, text="b₁", showarrow=False,
                       font=dict(color=COLOR_MIX, size=14))
    fig.add_shape(type="line", x0=x, y0=z, x1=d * nx, y1=d * nz,
                  line=dict(color=INK, width=1, dash="dot"))
    fig.add_shape(type="line", x0=0, y0=0, x1=d * nx, y1=d * nz,
                  line=dict(color=COLOR_B, width=7))
    _slice_arrow(fig, x, z, COLOR_A, "|ψ⟩")
    return fig


# ---------- two qubits ----------

KETS2 = ["|00⟩", "|01⟩", "|10⟩", "|11⟩"]
CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)
_I2 = np.eye(2, dtype=complex)
GATES2 = {
    "X on first": np.kron(GATES["X"], _I2),
    "X on second": np.kron(_I2, GATES["X"]),
    "H on first": np.kron(GATES["H"], _I2),
    "CNOT": CNOT,
}
_S = 1 / np.sqrt(2)
STATES2 = {
    "|00⟩": [1, 0, 0, 0],
    "|10⟩": [0, 0, 1, 0],
    "|+⟩|0⟩": [_S, 0, _S, 0],
    "(0.6|0⟩ + 0.8|1⟩)|+⟩": [0.6 * _S, 0.6 * _S, 0.8 * _S, 0.8 * _S],
    "Bell |Φ+⟩": [_S, 0, 0, _S],
    "0.8|00⟩ + 0.6|11⟩": [0.8, 0, 0, 0.6],
    "½(|00⟩ + |01⟩ + |10⟩ − |11⟩)": [0.5, 0.5, 0.5, -0.5],
}


def product_gap(state) -> float:
    """p·s − q·r for [p; q; r; s]: 0 exactly for a product state."""
    p, q, r, s = np.asarray(state, dtype=complex)
    return float(abs(p * s - q * r))


def reduced_a(state) -> np.ndarray:
    """ρ_A = M·M† with M = [[p, q], [r, s]] (rows: qubit A, columns: qubit B)."""
    m = np.asarray(state, dtype=complex).reshape(2, 2)
    return m @ m.conj().T


def amplitude_bars(before, after=None, names: tuple = ("before", "after"),
                   squared: bool = False) -> go.Figure:
    """The four amplitudes (or, squared, the four probabilities) of a two-qubit
    state as bars; with `after`, two groups side by side."""
    def values(v):
        v = np.real_if_close(np.asarray(v, dtype=complex))
        return (np.abs(v) ** 2 if squared else np.real(v)).astype(float)
    fig = go.Figure()
    groups = [(before, names[0], COLOR_A)] + ([(after, names[1], COLOR_B)]
                                              if after is not None else [])
    for state, name, color in groups:
        vals = values(state)
        fig.add_trace(go.Bar(x=KETS2, y=vals, name=name, marker=dict(color=color),
                             text=[f"{v + 0:.2f}" for v in vals],
                             textposition="outside", cliponaxis=False,
                             hovertemplate="%{x}: %{y:.3f}<extra>" + name + "</extra>"))
    fig.update_layout(
        barmode="group", height=280, margin=dict(l=10, r=10, t=30, b=10),
        showlegend=after is not None,
        legend=dict(orientation="h", y=1.18, x=0),
        yaxis=dict(range=[0, 1.12] if squared else [-1.12, 1.12], gridcolor=GRID,
                   zerolinecolor=INK, fixedrange=True,
                   title=dict(text="probability" if squared else "amplitude")),
        xaxis=dict(fixedrange=True),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT))
    return fig
