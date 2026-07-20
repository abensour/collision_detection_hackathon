"""Fast geometric conjunction screener (altitude bands + spatial KD-tree).

Beats the O(N²×T) baseline by:
1. Skipping pairs whose approximate altitude bands cannot meet within threshold
2. Finding spatially nearby pairs each timestep via ``cKDTree.query_pairs``
   (same role as a spatial hash / neighbor voxels; KD-tree is faster in practice)
3. Running vectorized full-grid distance only on that candidate pair set

Propagation is still O(N×T). Pair work scales with local density, not N².

The query radius equals ``threshold_km``, so any pair that comes within threshold
on the discrete grid is a candidate. Positions and distances use GCRS km,
same as the baseline and verifier.
"""

from __future__ import annotations

from datetime import datetime
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from scipy.spatial import cKDTree
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
from conjunction_toolkit.verify import refine_closest_approach

_MU_KM3_S2 = 398600.8

PairKey = Tuple[int, int]


def altitude_band_km(sat: EarthSatellite) -> Tuple[float, float]:
    """Approximate geocentric perigee/apogee radius (km) from Satrec elements."""
    model = sat.model
    n = float(model.no_kozai) / 60.0
    if n <= 0.0:
        return (0.0, 1.0e9)
    e = float(model.ecco)
    a = (_MU_KM3_S2 / (n * n)) ** (1.0 / 3.0)
    return (a * (1.0 - e), a * (1.0 + e))


def bands_can_meet(
    band_a: Tuple[float, float],
    band_b: Tuple[float, float],
    *,
    threshold_km: float,
    pad_km: float,
) -> bool:
    """True if two radial bands can come within threshold (+ pad)."""
    lo_a, hi_a = band_a
    lo_b, hi_b = band_b
    margin = threshold_km + pad_km
    return not (hi_a + margin < lo_b or hi_b + margin < lo_a)


def overlapping_altitude_pairs(
    bands: Dict[int, Tuple[float, float]],
    *,
    threshold_km: float,
    pad_km: float,
) -> Set[PairKey]:
    """All unique NORAD pairs whose altitude bands can meet within threshold+pad."""
    ids = sorted(bands.keys())
    allowed: Set[PairKey] = set()
    for a, b in combinations(ids, 2):
        if bands_can_meet(
            bands[a], bands[b], threshold_km=threshold_km, pad_km=pad_km
        ):
            allowed.add((a, b))
    return allowed


def _stack_positions(
    ids: Sequence[int],
    positions: Dict[int, np.ndarray],
    n_times: int,
) -> np.ndarray:
    """Return array shaped (N, T, 3)."""
    n = len(ids)
    stacked = np.empty((n, n_times, 3), dtype=np.float64)
    for i, nid in enumerate(ids):
        pos = np.asarray(positions[nid], dtype=np.float64)
        if pos.ndim == 1:
            pos = pos.reshape(3, 1)
        # pos is (3, T) → (T, 3)
        stacked[i] = pos.T
    return stacked


def _candidate_pairs_kdtree(
    ids: Sequence[int],
    stacked: np.ndarray,
    *,
    threshold_km: float,
    allowed_pairs: Optional[Set[PairKey]],
    bands: Optional[Dict[int, Tuple[float, float]]],
    pad_km: float,
) -> Set[PairKey]:
    """Union of pairs within ``threshold_km`` at any timestep (KD-tree)."""
    candidates: Set[PairKey] = set()
    n_times = stacked.shape[1]
    id_of = list(ids)

    for t_idx in range(n_times):
        xyz = stacked[:, t_idx, :]  # (N, 3)
        finite = np.isfinite(xyz).all(axis=1)
        if finite.sum() < 2:
            continue
        idx_map = np.flatnonzero(finite)
        tree = cKDTree(xyz[finite])
        for ia_f, ib_f in tree.query_pairs(r=threshold_km, output_type="set"):
            ia = int(idx_map[ia_f])
            ib = int(idx_map[ib_f])
            na, nb = id_of[ia], id_of[ib]
            if na > nb:
                na, nb = nb, na
            pair = (na, nb)
            if pair in candidates:
                continue
            if allowed_pairs is not None:
                if pair not in allowed_pairs:
                    continue
            elif bands is not None:
                if not bands_can_meet(
                    bands[na],
                    bands[nb],
                    threshold_km=threshold_km,
                    pad_km=pad_km,
                ):
                    continue
            candidates.add(pair)

    return candidates


def screen_pairs_fast(
    satellites: Dict[int, EarthSatellite],
    t0: datetime,
    t1: datetime,
    *,
    step_seconds: float = 60.0,
    threshold_km: float = 10.0,
    altitude_pad_km: float = 20.0,
    cell_size_km: Optional[float] = None,
    refine: bool = True,
    ts: Optional[Timescale] = None,
    algorithm_id: str = "spatial_hash",
    materialize_altitude_pairs: bool = True,
) -> List[ConjunctionClaim]:
    """Fast conjunction screen: altitude filter + spatial KD-tree (+ optional refine).

    Parameters
    ----------
    cell_size_km:
        Accepted for API compatibility with the plan. Unused: neighbor search uses
        KD-tree radius ``threshold_km`` (equivalent safety to cell_size >= threshold).
    altitude_pad_km:
        Extra radial margin on element-based perigee/apogee bands.
    refine:
        If True, run ``refine_closest_approach`` on each grid hit ≤ threshold.
    materialize_altitude_pairs:
        If True and N ≤ 500, precompute allowed altitude pairs. Otherwise check
        bands on the fly while collecting spatial candidates.
    """
    del cell_size_km  # API compat; KD-tree radius == threshold_km

    ts = get_timescale(ts)
    t0 = ensure_utc(t0)
    t1 = ensure_utc(t1)
    ids = sorted(satellites.keys())
    if len(ids) < 2:
        return []

    bands = {nid: altitude_band_km(satellites[nid]) for nid in ids}

    allowed: Optional[Set[PairKey]]
    band_filter: Optional[Dict[int, Tuple[float, float]]]
    if materialize_altitude_pairs and len(ids) <= 500:
        allowed = overlapping_altitude_pairs(
            bands, threshold_km=threshold_km, pad_km=altitude_pad_km
        )
        if not allowed:
            return []
        band_filter = None
    else:
        allowed = None
        band_filter = bands

    t = time_grid(t0, t1, step_seconds, ts=ts)
    times = datetimes_of(t)
    positions = propagate_many(satellites, t)
    stacked = _stack_positions(ids, positions, len(times))

    candidates = _candidate_pairs_kdtree(
        ids,
        stacked,
        threshold_km=threshold_km,
        allowed_pairs=allowed,
        bands=band_filter,
        pad_km=altitude_pad_km,
    )

    claims: List[ConjunctionClaim] = []
    for a, b in candidates:
        tca, dmin, _ = closest_approach_on_grid(positions[a], positions[b], times)
        if dmin > threshold_km:
            continue
        if refine:
            tca, dmin = refine_closest_approach(
                satellites[a], satellites[b], tca, ts=ts
            )
            if dmin > threshold_km:
                continue
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
