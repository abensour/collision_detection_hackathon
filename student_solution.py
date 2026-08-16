"""Student solution: fast altitude-band + spatial KD-tree close-approach search."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from skyfield.api import EarthSatellite

from conjunction_toolkit.models import ConjunctionClaim
from conjunction_toolkit.screener import screen_pairs_fast


def find_close_approaches(
    satellites: Dict[int, EarthSatellite],
    propagate_from_utc: datetime,
    propagate_until_utc: datetime,
    time_step_seconds: float,
    close_approach_threshold_km: float,
) -> List[ConjunctionClaim]:
    """Find close approaches using the toolkit fast screener.

    Same public arguments as the notebook baseline. Internally:
    1. Skip pairs whose altitude bands cannot meet
    2. Find nearby pairs each timestep with a KD-tree
    3. Measure miss distance on the time grid, then refine the closest time

    Stops after 5 minutes and returns claims found so far.
    """
    claims = screen_pairs_fast(
        satellites,
        propagate_from_utc,
        propagate_until_utc,
        step_seconds=time_step_seconds,
        threshold_km=close_approach_threshold_km,
        refine=True,
        algorithm_id="cloude_student_fast",
        max_runtime_seconds=300.0,
    )
    # Drop decayed/invalid objects (0 km at Earth center) and times outside the search span
    return [
        claim
        for claim in claims
        if claim.min_distance_km > 1e-6
        and propagate_from_utc <= claim.tca_utc <= propagate_until_utc
    ]
