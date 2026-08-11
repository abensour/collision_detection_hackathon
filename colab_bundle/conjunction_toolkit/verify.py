"""Independent verification of claimed conjunctions.

Does not trust team algorithms: re-propagates both objects from the shared
catalog and refines TCA around the claimed epoch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from skyfield.api import EarthSatellite
from skyfield.timelib import Timescale

from conjunction_toolkit.models import ConjunctionClaim, VerificationResult
from conjunction_toolkit.propagate import (
    closest_approach_on_grid,
    datetimes_of,
    ensure_utc,
    propagate_positions,
    time_grid,
)
from conjunction_toolkit.satellites import get_timescale


@dataclass
class VerifyConfig:
    """Acceptance tolerances and TCA refinement window."""

    # Claimed miss distance must be within this of the recomputed value
    distance_tolerance_km: float = 0.1  # 100 m
    # Claimed TCA must be within this of the refined TCA
    tca_tolerance_seconds: float = 5.0
    # Optional: also require that the true miss distance is below this
    # (None = only check claim consistency, not absolute closeness)
    max_miss_distance_km: Optional[float] = None
    # Coarse then fine refinement around claimed TCA
    refine_window_seconds: float = 300.0  # ±5 minutes
    coarse_step_seconds: float = 5.0
    fine_window_seconds: float = 15.0
    fine_step_seconds: float = 0.25


def _refine_tca(
    sat_a: EarthSatellite,
    sat_b: EarthSatellite,
    center: datetime,
    *,
    window_seconds: float,
    step_seconds: float,
    ts: Timescale,
) -> tuple[datetime, float]:
    t0 = center - timedelta(seconds=window_seconds)
    t1 = center + timedelta(seconds=window_seconds)
    t = time_grid(t0, t1, step_seconds, ts=ts)
    times = datetimes_of(t)
    pos_a = propagate_positions(sat_a, t)
    pos_b = propagate_positions(sat_b, t)
    tca, dmin, _ = closest_approach_on_grid(pos_a, pos_b, times)
    return tca, dmin


def refine_closest_approach(
    sat_a: EarthSatellite,
    sat_b: EarthSatellite,
    approximate_tca: datetime,
    *,
    config: Optional[VerifyConfig] = None,
    ts: Optional[Timescale] = None,
) -> tuple[datetime, float]:
    """Multi-pass TCA refinement around ``approximate_tca``.

    Expands the coarse window if the discrete minimum sits near an edge
    (so a nearby deeper approach is not missed), then runs a fine grid.
    """
    config = config or VerifyConfig()
    ts = get_timescale(ts)
    center = ensure_utc(approximate_tca)
    window = config.refine_window_seconds

    for _ in range(6):
        tca, dmin = _refine_tca(
            sat_a,
            sat_b,
            center,
            window_seconds=window,
            step_seconds=config.coarse_step_seconds,
            ts=ts,
        )
        # If min is near the edge, expand and recenter
        edge_margin = 2.0 * config.coarse_step_seconds
        offset = abs((tca - center).total_seconds())
        if offset < window - edge_margin:
            break
        center = tca
        window *= 2.0
    else:
        tca, dmin = _refine_tca(
            sat_a,
            sat_b,
            center,
            window_seconds=window,
            step_seconds=config.coarse_step_seconds,
            ts=ts,
        )

    tca, dmin = _refine_tca(
        sat_a,
        sat_b,
        tca,
        window_seconds=config.fine_window_seconds,
        step_seconds=config.fine_step_seconds,
        ts=ts,
    )
    return tca, dmin


def verify_claim(
    claim: ConjunctionClaim,
    satellites: Dict[int, EarthSatellite],
    *,
    config: Optional[VerifyConfig] = None,
    ts: Optional[Timescale] = None,
) -> VerificationResult:
    """Recompute TCA/distance for a claim and accept or reject with reasons."""
    config = config or VerifyConfig()
    ts = get_timescale(ts)
    messages: list[str] = []

    sat_a = satellites.get(claim.norad_a)
    sat_b = satellites.get(claim.norad_b)
    if sat_a is None or sat_b is None:
        missing = []
        if sat_a is None:
            missing.append(str(claim.norad_a))
        if sat_b is None:
            missing.append(str(claim.norad_b))
        return VerificationResult(
            ok=False,
            recomputed_distance_km=float("nan"),
            recomputed_tca_utc=None,
            distance_error_km=float("nan"),
            tca_error_seconds=None,
            messages=[f"Missing satellites in catalog: {', '.join(missing)}"],
        )

    try:
        tca, dmin = refine_closest_approach(
            sat_a, sat_b, claim.tca_utc, config=config, ts=ts
        )
    except Exception as exc:  # noqa: BLE001 — surface propagation failures cleanly
        return VerificationResult(
            ok=False,
            recomputed_distance_km=float("nan"),
            recomputed_tca_utc=None,
            distance_error_km=float("nan"),
            tca_error_seconds=None,
            messages=[f"Propagation/refinement failed: {exc}"],
        )

    distance_error = abs(dmin - claim.min_distance_km)
    tca_error = abs((tca - ensure_utc(claim.tca_utc)).total_seconds())

    ok = True
    if distance_error > config.distance_tolerance_km:
        ok = False
        messages.append(
            f"Distance mismatch: claimed {claim.min_distance_km:.6f} km, "
            f"recomputed {dmin:.6f} km (error {distance_error:.6f} km > "
            f"{config.distance_tolerance_km} km)"
        )
    if tca_error > config.tca_tolerance_seconds:
        ok = False
        messages.append(
            f"TCA mismatch: claimed {claim.tca_utc.isoformat()}, "
            f"recomputed {tca.isoformat()} (error {tca_error:.3f} s > "
            f"{config.tca_tolerance_seconds} s)"
        )
    if (
        config.max_miss_distance_km is not None
        and dmin > config.max_miss_distance_km
    ):
        ok = False
        messages.append(
            f"Recomputed miss distance {dmin:.6f} km exceeds "
            f"max_miss_distance_km={config.max_miss_distance_km}"
        )

    if ok:
        messages.append("Claim verified within tolerances.")

    return VerificationResult(
        ok=ok,
        recomputed_distance_km=dmin,
        recomputed_tca_utc=tca,
        distance_error_km=distance_error,
        tca_error_seconds=tca_error,
        messages=messages,
    )


def verify_claims(
    claims: list[ConjunctionClaim],
    satellites: Dict[int, EarthSatellite],
    *,
    config: Optional[VerifyConfig] = None,
    ts: Optional[Timescale] = None,
) -> list[VerificationResult]:
    """Verify a batch of claims."""
    return [verify_claim(c, satellites, config=config, ts=ts) for c in claims]
