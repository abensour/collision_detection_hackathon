"""Ephemeris propagation helpers (Skyfield / SGP4).

Positions are returned in **kilometers** in the **GCRS** (Geocentric Celestial
Reference System) frame — Skyfield's default for ``EarthSatellite.at(t).position``.
All conjunction screening and verification in this toolkit use this frame
consistently so team algorithms and the verifier are comparable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from skyfield.api import EarthSatellite, load
from skyfield.timelib import Time, Timescale

from conjunction_toolkit.satellites import get_timescale

ArrayLike = Union[np.ndarray, Sequence[float]]


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def time_grid(
    t0: datetime,
    t1: datetime,
    step_seconds: float,
    *,
    ts: Optional[Timescale] = None,
) -> Time:
    """Build evenly spaced sample times from ``t0`` until ``t1``.

    Example: ``time_grid(start, start + 6 hours, step_seconds=30*60)`` gives
    one sample every 30 minutes while you propagate for 6 hours.
    """
    ts = get_timescale(ts)
    t0 = ensure_utc(t0)
    t1 = ensure_utc(t1)
    if t1 < t0:
        raise ValueError("t1 must be >= t0")
    if step_seconds <= 0:
        raise ValueError("step_seconds must be positive")

    total = (t1 - t0).total_seconds()
    n = int(total // step_seconds) + 1
    times = [t0 + timedelta(seconds=i * step_seconds) for i in range(n)]
    if times[-1] < t1:
        times.append(t1)
    return ts.from_datetimes(times)


def datetimes_of(t: Time) -> List[datetime]:
    """Convert a Skyfield Time (scalar or array) to UTC datetimes."""
    if getattr(t, "shape", ()):
        return [ti.utc_datetime().replace(tzinfo=timezone.utc) for ti in t]
    return [t.utc_datetime().replace(tzinfo=timezone.utc)]


def propagate_positions(
    sat: EarthSatellite,
    t: Time,
) -> np.ndarray:
    """Compute where one satellite is at each sample time.

    Returns positions in kilometers (GCRS), shape ``(3, N)`` for N times
    or ``(3,)`` for a single time.
    """
    geo = sat.at(t)
    return np.asarray(geo.position.km)


def propagate_many(
    satellites: Dict[int, EarthSatellite],
    t: Time,
) -> Dict[int, np.ndarray]:
    """Propagate many satellites on the same time grid.

    Returns ``{norad_id: positions}`` with positions shaped ``(3, N)`` km GCRS.
    """
    return {nid: propagate_positions(sat, t) for nid, sat in satellites.items()}


def pair_distances(
    pos_a: np.ndarray,
    pos_b: np.ndarray,
) -> np.ndarray:
    """Euclidean distances (km) between two ``(3, N)`` position arrays."""
    a = np.asarray(pos_a)
    b = np.asarray(pos_b)
    if a.ndim == 1:
        a = a.reshape(3, 1)
        b = b.reshape(3, 1)
    return np.linalg.norm(a - b, axis=0)


def closest_approach_on_grid(
    pos_a: np.ndarray,
    pos_b: np.ndarray,
    times: Sequence[datetime],
) -> Tuple[datetime, float, int]:
    """Among discrete time samples, find when two objects were nearest.

    This only looks at the provided samples (for example every 30 minutes).
    It does **not** zoom in between samples — use
    ``improve_closest_approach_estimate`` for that.

    Returns
    -------
    (closest_sample_time, closest_distance_km, sample_index)
    """
    dists = pair_distances(pos_a, pos_b)
    idx = int(np.argmin(dists))
    return times[idx], float(dists[idx]), idx


def distance_at(
    sat_a: EarthSatellite,
    sat_b: EarthSatellite,
    when: datetime,
    *,
    ts: Optional[Timescale] = None,
) -> float:
    """Single-epoch miss distance in km (GCRS)."""
    ts = get_timescale(ts)
    t = ts.from_datetime(ensure_utc(when))
    return float(pair_distances(propagate_positions(sat_a, t), propagate_positions(sat_b, t))[0])
