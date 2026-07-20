"""Deliberately slow brute-force conjunction screener (baseline).

Complexity is O(N² × T): every unique pair is checked at every time step.
Teams should replace this with a faster algorithm; the claim verifier does
not depend on this module.
"""

from __future__ import annotations

from datetime import datetime
from itertools import combinations
from typing import Dict, List, Optional, Sequence

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
    t0: datetime,
    t1: datetime,
    *,
    step_seconds: float = 60.0,
    threshold_km: float = 10.0,
    ts: Optional[Timescale] = None,
    algorithm_id: str = "baseline_bruteforce",
) -> List[ConjunctionClaim]:
    """Brute-force screen all unique pairs for close approaches.

    Parameters
    ----------
    satellites:
        Mapping of NORAD ID → EarthSatellite (already built from the catalog).
    t0, t1:
        Inclusive UTC screening window.
    step_seconds:
        Propagation step. Coarser = faster but may miss brief dips.
    threshold_km:
        Report pairs whose discrete-grid minimum distance is ≤ this value.
    """
    ts = get_timescale(ts)
    t0 = ensure_utc(t0)
    t1 = ensure_utc(t1)
    ids = sorted(satellites.keys())
    if len(ids) < 2:
        return []

    t = time_grid(t0, t1, step_seconds, ts=ts)
    times = datetimes_of(t)
    positions = propagate_many(satellites, t)

    claims: List[ConjunctionClaim] = []
    for a, b in combinations(ids, 2):
        tca, dmin, _ = closest_approach_on_grid(positions[a], positions[b], times)
        if dmin <= threshold_km:
            claims.append(
                ConjunctionClaim(
                    norad_a=a,
                    norad_b=b,
                    tca_utc=tca,
                    min_distance_km=dmin,
                    algorithm_id=algorithm_id,
                )
            )

    claims.sort(key=lambda c: c.min_distance_km)
    return claims


def screen_catalog_subset(
    satellites: Dict[int, EarthSatellite],
    norad_ids: Sequence[int],
    t0: datetime,
    t1: datetime,
    **kwargs,
) -> List[ConjunctionClaim]:
    """Convenience wrapper: screen only the listed NORAD IDs."""
    subset = {nid: satellites[nid] for nid in norad_ids if nid in satellites}
    return screen_pairs(subset, t0, t1, **kwargs)
