"""Shared evaluation for the naive baseline and the student solution.

Swap which finder you pass in — the report format stays the same.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Sequence

from skyfield.api import EarthSatellite

from conjunction_toolkit.models import ConjunctionClaim
from conjunction_toolkit.verify import VerifyConfig, refine_closest_approach, verify_claim

FindCloseApproachesFn = Callable[..., List[ConjunctionClaim]]


@dataclass
class EvaluationReport:
    """Plain-language summary of one algorithm run."""

    algorithm_name: str
    close_approaches_detected: int
    claims_verified_ok: int
    claims_failed: int
    runtime_seconds: float
    messages: List[str] = field(default_factory=list)
    claims: List[ConjunctionClaim] = field(default_factory=list)

    def print_summary(self) -> None:
        print(f"=== Evaluation: {self.algorithm_name} ===")
        print(f"  Close approaches detected : {self.close_approaches_detected}")
        print(f"  Verified OK               : {self.claims_verified_ok}")
        print(f"  Failed verification       : {self.claims_failed}")
        print(f"  Runtime                   : {self.runtime_seconds:.2f} seconds")
        for msg in self.messages:
            print(f"  - {msg}")


def refine_claims(
    claims: Sequence[ConjunctionClaim],
    satellites: Dict[int, EarthSatellite],
    *,
    algorithm_id: Optional[str] = None,
) -> List[ConjunctionClaim]:
    """Improve each claim's closest-approach time and distance.

    A coarse time grid only finds an approximate moment. Refinement zooms in
    around that moment so verification has a fair chance to pass.
    """
    refined: List[ConjunctionClaim] = []
    for claim in claims:
        closest_time, closest_distance_km = refine_closest_approach(
            satellites[claim.norad_a],
            satellites[claim.norad_b],
            claim.tca_utc,
        )
        refined.append(
            ConjunctionClaim(
                norad_a=claim.norad_a,
                norad_b=claim.norad_b,
                tca_utc=closest_time,
                min_distance_km=closest_distance_km,
                algorithm_id=algorithm_id or claim.algorithm_id,
            )
        )
    refined.sort(key=lambda c: c.min_distance_km)
    return refined


def evaluate_finder(
    find_close_approaches: FindCloseApproachesFn,
    satellites: Dict[int, EarthSatellite],
    window_start_utc: datetime,
    window_end_utc: datetime,
    *,
    time_step_seconds: float,
    close_approach_threshold_km: float,
    algorithm_name: str,
    refine_before_verify: bool = True,
    verify_config: Optional[VerifyConfig] = None,
    max_claims_to_verify: Optional[int] = None,
) -> EvaluationReport:
    """Run one finder, optionally refine, then verify every claim.

    Parameters
    ----------
    find_close_approaches:
        Any function with the same interface as
        ``student_solution.find_close_approaches`` (including the naive
        baseline wrapper in the notebook).
    refine_before_verify:
        If True, improve closest-approach time/distance before checking.
    max_claims_to_verify:
        If set, only verify the closest N claims (useful for slow demos).
    """
    import time

    config = verify_config or VerifyConfig(
        max_miss_distance_km=close_approach_threshold_km
    )

    t0 = time.perf_counter()
    raw_claims = find_close_approaches(
        satellites,
        window_start_utc,
        window_end_utc,
        time_step_seconds=time_step_seconds,
        close_approach_threshold_km=close_approach_threshold_km,
    )
    runtime_seconds = time.perf_counter() - t0

    claims = list(raw_claims)
    if refine_before_verify and claims:
        claims = refine_claims(
            claims,
            satellites,
            algorithm_id=algorithm_name,
        )

    if max_claims_to_verify is not None:
        claims = claims[:max_claims_to_verify]

    ok_count = 0
    fail_count = 0
    messages: List[str] = []

    for claim in claims:
        result = verify_claim(claim, satellites, config=config)
        if result.ok:
            ok_count += 1
        else:
            fail_count += 1
            reason = result.messages[0] if result.messages else "verification failed"
            messages.append(
                f"FAIL {claim.norad_a}–{claim.norad_b}: "
                f"claimed {claim.min_distance_km:.3f} km @ {claim.tca_utc.isoformat()} "
                f"({reason})"
            )

    return EvaluationReport(
        algorithm_name=algorithm_name,
        close_approaches_detected=len(raw_claims),
        claims_verified_ok=ok_count,
        claims_failed=fail_count,
        runtime_seconds=runtime_seconds,
        messages=messages,
        claims=claims,
    )
