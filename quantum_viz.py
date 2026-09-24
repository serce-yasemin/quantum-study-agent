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

# Categorical slots 1-3 of the validated default palette (light surface).
COLOR_A = "#2a78d6"     # state A
COLOR_B = "#eb6834"     # state B
COLOR_MIX = "#1baf7a"   # the mixture
INK = "#52514e"         # secondary text / axes
GRID = "#d9d8d4"        # recessive sphere wireframe

# Sequential blue ramp (step 100 -> 600) for |ρᵢⱼ| magnitudes.
SEQ_BLUE = [[0.0, "#cde2fb"], [0.35, "#86b6ef"], [0.7, "#2a78d6"], [1.0, "#184f95"]]

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


# ---------- math ----------

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

def bloch_figure(points: list[dict], chord: bool = False) -> go.Figure:
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
                        line=dict(color="#ffffff", width=2)),
            text=[pt["label"]], textposition="top center",
            textfont=dict(color="#0b0b0b", size=13),
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
                                         color="#ffffff" if mag[i, j] > 0.55 else "#0b0b0b"))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=300, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed"),
    )
    return fig
