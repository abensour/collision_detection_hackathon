"""Independent verification of claimed close approaches.

Does not trust team algorithms: re-propagates both objects from the shared
catalog and improves the closest-approach time around the claimed moment.
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
    """How strict verification is when checking a claim.

    Attributes
    ----------
    distance_tolerance_km:
        Claimed miss distance must match the recomputed one within this
        many kilometers (default 0.1 km = 100 meters).
    tca_tolerance_seconds:
        Claimed time of closest approach must match within this many seconds
        (default 5 s). The field name on claims is still ``tca_utc``.
    max_miss_distance_km:
        If set, also reject claims whose true miss distance is larger than this.
    refine_window_seconds / coarse_step_seconds / fine_*:
        Internal search settings for ``improve_closest_approach_estimate``.
    """

    distance_tolerance_km: float = 0.1  # 100 m
    tca_tolerance_seconds: float = 5.0
    max_miss_distance_km: Optional[float] = None
    refine_window_seconds: float = 300.0  # ±5 minutes around the rough guess
    coarse_step_seconds: float = 5.0
    fine_window_seconds: float = 15.0
    fine_step_seconds: float = 0.25


def _closest_on_local_grid(
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
    closest_time, closest_distance_km, _ = closest_approach_on_grid(
        pos_a, pos_b, times
    )
    return closest_time, closest_distance_km


def improve_closest_approach_estimate(
    sat_a: EarthSatellite,
    sat_b: EarthSatellite,
    rough_closest_time: datetime,
    *,
    config: Optional[VerifyConfig] = None,
    ts: Optional[Timescale] = None,
) -> tuple[datetime, float]:
    """Improve a rough guess of when two objects were closest.

    Why this exists
    ---------------
    If you only check positions every 30 minutes, you get an *approximate*
    closest time (the sample where distance was smallest). That is often too
    coarse for verification (which needs ~seconds and ~100 m accuracy).

    What it does
    ------------
    1. Re-propagates both objects around ``rough_closest_time`` on a finer grid
       (seconds, not minutes).
    2. If the minimum sits near the edge of that search, expands and recenters.
    3. Runs an even finer pass and returns the improved time and distance.

    Parameters
    ----------
    sat_a, sat_b:
        The two satellites.
    rough_closest_time:
        Your approximate time of closest approach (for example the best time
        among coarse samples).

    Returns
    -------
    (improved_closest_time_utc, closest_distance_km)
    """
    config = config or VerifyConfig()
    ts = get_timescale(ts)
    center = ensure_utc(rough_closest_time)
    window = config.refine_window_seconds

    for _ in range(6):
        closest_time, closest_distance_km = _closest_on_local_grid(
            sat_a,
            sat_b,
            center,
            window_seconds=window,
            step_seconds=config.coarse_step_seconds,
            ts=ts,
        )
        edge_margin = 2.0 * config.coarse_step_seconds
        offset = abs((closest_time - center).total_seconds())
        if offset < window - edge_margin:
            break
        center = closest_time
        window *= 2.0
    else:
        closest_time, closest_distance_km = _closest_on_local_grid(
            sat_a,
            sat_b,
            center,
            window_seconds=window,
            step_seconds=config.coarse_step_seconds,
            ts=ts,
        )

    closest_time, closest_distance_km = _closest_on_local_grid(
        sat_a,
        sat_b,
        closest_time,
        window_seconds=config.fine_window_seconds,
        step_seconds=config.fine_step_seconds,
        ts=ts,
    )
    return closest_time, closest_distance_km


def verify_claim(
    claim: ConjunctionClaim,
    satellites: Dict[int, EarthSatellite],
    *,
    config: Optional[VerifyConfig] = None,
    ts: Optional[Timescale] = None,
) -> VerificationResult:
    """Independently re-check one close-approach claim.

    Re-propagates both objects, improves the closest-approach time near the
    claimed moment, and accepts the claim only if distance and time match
    within ``VerifyConfig`` tolerances.
    """
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
        closest_time, closest_distance_km = improve_closest_approach_estimate(
            sat_a, sat_b, claim.tca_utc, config=config, ts=ts
        )
    except Exception as exc:  # noqa: BLE001 — surface propagation failures cleanly
        return VerificationResult(
            ok=False,
            recomputed_distance_km=float("nan"),
            recomputed_tca_utc=None,
            distance_error_km=float("nan"),
            tca_error_seconds=None,
            messages=[f"Propagation / closest-approach improvement failed: {exc}"],
        )

    distance_error = abs(closest_distance_km - claim.min_distance_km)
    time_error = abs(
        (closest_time - ensure_utc(claim.tca_utc)).total_seconds()
    )

    ok = True
    if distance_error > config.distance_tolerance_km:
        ok = False
        messages.append(
            f"Distance mismatch: claimed {claim.min_distance_km:.6f} km, "
            f"recomputed {closest_distance_km:.6f} km (error {distance_error:.6f} km > "
            f"{config.distance_tolerance_km} km)"
        )
    if time_error > config.tca_tolerance_seconds:
        ok = False
        messages.append(
            f"Closest-time mismatch: claimed {claim.tca_utc.isoformat()}, "
            f"recomputed {closest_time.isoformat()} (error {time_error:.3f} s > "
            f"{config.tca_tolerance_seconds} s)"
        )
    if (
        config.max_miss_distance_km is not None
        and closest_distance_km > config.max_miss_distance_km
    ):
        ok = False
        messages.append(
            f"Recomputed miss distance {closest_distance_km:.6f} km exceeds "
            f"max_miss_distance_km={config.max_miss_distance_km}"
        )

    if ok:
        messages.append("Claim verified within tolerances.")

    return VerificationResult(
        ok=ok,
        recomputed_distance_km=closest_distance_km,
        recomputed_tca_utc=closest_time,
        distance_error_km=distance_error,
        tca_error_seconds=time_error,
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
