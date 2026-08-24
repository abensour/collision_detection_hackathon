"""Naive baseline: check every unique pair of satellites on a time grid.

Complexity is O(N² × T): every pair × every time sample.
This is the slow reference students may beat with a smarter algorithm.
"""

from __future__ import annotations

from datetime import datetime
from itertools import combinations
from typing import Dict, List, Optional

from skyfield.api import EarthSatellite
from skyfield.timelib import Timescale

from conjunction_toolkit.models import ConjunctionClaim
from conjunction_toolkit.propagate import (
    closest_approach_on_grid,
    datetimes_of,
    ensure_utc,
    propagate_many,
    time_grid,
)
from conjunction_toolkit.satellites import get_timescale


def screen_pairs(
    satellites: Dict[int, EarthSatellite],
    propagate_from_utc: datetime,
    propagate_until_utc: datetime,
    *,
    step_seconds: float = 60.0,
    threshold_km: float = 10.0,
    ts: Optional[Timescale] = None,
    algorithm_id: str = "naive_baseline",
) -> List[ConjunctionClaim]:
    """Brute-force: for every pair, find the closest sample in [from, until].

    Parameters
    ----------
    satellites:
        Object id → satellite that can be propagated.
    propagate_from_utc, propagate_until_utc:
        Propagate / search from this start time until this end time (UTC).
    step_seconds:
        Time between samples (e.g. ``30 * 60`` for every 30 minutes).
        Larger steps are faster but can miss short close approaches.
    threshold_km:
        Keep a pair if its closest sample distance is ≤ this value.
    """
    ts = get_timescale(ts)
    t0 = ensure_utc(propagate_from_utc)
    t1 = ensure_utc(propagate_until_utc)
    ids = sorted(satellites.keys())
    if len(ids) < 2:
        return []

    t = time_grid(t0, t1, step_seconds, ts=ts)
    times = datetimes_of(t)
    positions = propagate_many(satellites, t)

    claims: List[ConjunctionClaim] = []
    for a, b in combinations(ids, 2):
        closest_time, closest_distance_km, _ = closest_approach_on_grid(
            positions[a], positions[b], times
        )
        if closest_distance_km <= threshold_km:
            claims.append(
                ConjunctionClaim(
                    norad_a=a,
                    norad_b=b,
                    tca_utc=closest_time,
                    min_distance_km=closest_distance_km,
                    algorithm_id=algorithm_id,
                )
            )

    claims.sort(
        key=lambda c: float("inf") if c.min_distance_km is None else c.min_distance_km
    )
    return claims
