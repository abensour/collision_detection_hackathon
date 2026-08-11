"""Plotly visualization for trajectories and conjunctions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from skyfield.api import EarthSatellite
from skyfield.timelib import Time

from conjunction_toolkit.propagate import (
    datetimes_of,
    pair_distances,
    propagate_positions,
)

PathLike = Union[str, Path]
EARTH_RADIUS_KM = 6371.0


def _earth_sphere(radius_km: float = EARTH_RADIUS_KM, n: int = 36) -> go.Surface:
    u = np.linspace(0, 2 * np.pi, n)
    v = np.linspace(0, np.pi, n // 2)
    x = radius_km * np.outer(np.cos(u), np.sin(v))
    y = radius_km * np.outer(np.sin(u), np.sin(v))
    z = radius_km * np.outer(np.ones_like(u), np.cos(v))
    return go.Surface(
        x=x,
        y=y,
        z=z,
        opacity=0.35,
        colorscale=[[0, "#1a4a6e"], [1, "#3d8ecd"]],
        showscale=False,
        name="Earth",
        hoverinfo="skip",
    )


def plot_trajectories(
    satellites: Dict[int, EarthSatellite],
    t: Time,
    *,
    title: str = "Satellite trajectories (GCRS)",
    show_earth: bool = True,
) -> go.Figure:
    """3D Plotly figure: Earth + trajectories for the given satellites."""
    fig = go.Figure()
    if show_earth:
        fig.add_trace(_earth_sphere())

    times = datetimes_of(t)
    for nid, sat in satellites.items():
        pos = propagate_positions(sat, t)
        if pos.ndim == 1:
            pos = pos.reshape(3, 1)
        name = sat.name or str(nid)
        hover = [
            f"{name}<br>NORAD {nid}<br>{ti.isoformat()}<br>"
            f"x={pos[0, i]:.1f} y={pos[1, i]:.1f} z={pos[2, i]:.1f} km"
            for i, ti in enumerate(times)
        ]
        fig.add_trace(
            go.Scatter3d(
                x=pos[0],
                y=pos[1],
                z=pos[2],
                mode="lines",
                name=f"{name} ({nid})",
                text=hover,
                hoverinfo="text",
                line=dict(width=3),
            )
        )
        # Mark latest position
        fig.add_trace(
            go.Scatter3d(
                x=[pos[0, -1]],
                y=[pos[1, -1]],
                z=[pos[2, -1]],
                mode="markers",
                name=f"{name} end",
                marker=dict(size=4),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="X (km)",
            yaxis_title="Y (km)",
            zaxis_title="Z (km)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    return fig


def plot_pair_close_approach(
    sat_a: EarthSatellite,
    sat_b: EarthSatellite,
    t: Time,
    *,
    tca: Optional[datetime] = None,
    norad_a: Optional[int] = None,
    norad_b: Optional[int] = None,
    title: str = "Pair close approach",
) -> go.Figure:
    """3D trajectories for two sats with an optional TCA marker."""
    sats = {
        norad_a or 0: sat_a,
        norad_b or 1: sat_b,
    }
    # Use real names in legend
    fig = plot_trajectories(sats, t, title=title)

    if tca is not None:
        from conjunction_toolkit.propagate import ensure_utc
        from conjunction_toolkit.satellites import get_timescale

        ts = get_timescale()
        tt = ts.from_datetime(ensure_utc(tca))
        pa = propagate_positions(sat_a, tt)
        pb = propagate_positions(sat_b, tt)
        mid = 0.5 * (pa + pb)
        d = float(np.linalg.norm(pa - pb))
        fig.add_trace(
            go.Scatter3d(
                x=[mid[0]],
                y=[mid[1]],
                z=[mid[2]],
                mode="markers+text",
                name=f"TCA ({d:.3f} km)",
                marker=dict(size=6, color="#c0392b", symbol="diamond"),
                text=[f"TCA {d:.3f} km"],
                textposition="top center",
            )
        )
    return fig


def plot_distance_vs_time(
    sat_a: EarthSatellite,
    sat_b: EarthSatellite,
    t: Time,
    *,
    name_a: str = "A",
    name_b: str = "B",
    threshold_km: Optional[float] = None,
    title: str = "Miss distance vs time",
) -> go.Figure:
    """2D Plotly line chart of pairwise distance over the time grid."""
    pos_a = propagate_positions(sat_a, t)
    pos_b = propagate_positions(sat_b, t)
    dists = pair_distances(pos_a, pos_b)
    times = datetimes_of(t)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=dists,
            mode="lines",
            name=f"{name_a}–{name_b}",
            line=dict(width=2),
        )
    )
    if threshold_km is not None:
        fig.add_hline(
            y=threshold_km,
            line_dash="dash",
            annotation_text=f"threshold {threshold_km} km",
        )
    idx = int(np.argmin(dists))
    fig.add_trace(
        go.Scatter(
            x=[times[idx]],
            y=[dists[idx]],
            mode="markers+text",
            name="min",
            marker=dict(size=10, color="#c0392b"),
            text=[f"{dists[idx]:.3f} km"],
            textposition="top center",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="UTC",
        yaxis_title="Distance (km)",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def plot_pair_with_distance(
    sat_a: EarthSatellite,
    sat_b: EarthSatellite,
    t: Time,
    *,
    tca: Optional[datetime] = None,
    norad_a: int = 0,
    norad_b: int = 1,
    threshold_km: Optional[float] = None,
    title: str = "Conjunction view",
) -> go.Figure:
    """Combined 3D trajectory + distance-vs-time subplot."""
    fig3d = plot_pair_close_approach(
        sat_a,
        sat_b,
        t,
        tca=tca,
        norad_a=norad_a,
        norad_b=norad_b,
        title=title,
    )
    fig2d = plot_distance_vs_time(
        sat_a,
        sat_b,
        t,
        name_a=sat_a.name or str(norad_a),
        name_b=sat_b.name or str(norad_b),
        threshold_km=None,  # draw threshold on combined axes below
    )

    combined = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "scene"}, {"type": "xy"}]],
        subplot_titles=("Trajectories (GCRS)", "Distance vs time"),
        column_widths=[0.55, 0.45],
    )
    for tr in fig3d.data:
        combined.add_trace(tr, row=1, col=1)
    for tr in fig2d.data:
        combined.add_trace(tr, row=1, col=2)

    if threshold_km is not None:
        times = datetimes_of(t)
        combined.add_trace(
            go.Scatter(
                x=[times[0], times[-1]],
                y=[threshold_km, threshold_km],
                mode="lines",
                name=f"threshold {threshold_km} km",
                line=dict(dash="dash", width=1, color="#888"),
            ),
            row=1,
            col=2,
        )

    combined.update_layout(
        title=title,
        height=560,
        margin=dict(l=0, r=0, t=50, b=0),
        scene=dict(aspectmode="data", xaxis_title="X", yaxis_title="Y", zaxis_title="Z"),
    )
    combined.update_xaxes(title_text="UTC", row=1, col=2)
    combined.update_yaxes(title_text="Distance (km)", row=1, col=2)
    return combined


def save_html(fig: go.Figure, path: PathLike) -> Path:
    """Write a Plotly figure to an HTML file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(path), include_plotlyjs="cdn")
    return path
