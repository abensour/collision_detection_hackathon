"""Student solution: find close approaches between satellites.

Replace ``find_close_approaches`` with your own algorithm.
Do not change the function name or the arguments — the notebook verifier
calls this interface for both the naive baseline and your code.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from skyfield.api import EarthSatellite

from conjunction_toolkit.models import ConjunctionClaim


def find_close_approaches(
    satellites: Dict[int, EarthSatellite],
    window_start_utc: datetime,
    window_end_utc: datetime,
    *,
    time_step_seconds: float,
    close_approach_threshold_km: float,
) -> List[ConjunctionClaim]:
    """Find pairs of satellites that come closer than the distance threshold.

    Parameters
    ----------
    satellites:
        Dictionary mapping each object id (NORAD catalog number) to a
        Skyfield ``EarthSatellite`` that can be propagated in time.
    window_start_utc:
        Start of the prediction window (timezone-aware UTC).
    window_end_utc:
        End of the prediction window (timezone-aware UTC).
        Example: start + 6 hours means "look 6 hours into the future".
    time_step_seconds:
        How far to jump forward in time between position checks.
        Example: ``30 * 60`` = check every 30 minutes.
        Larger steps are faster but can miss short close approaches.
    close_approach_threshold_km:
        Report a pair only if their closest distance on the time grid
        is less than or equal to this many kilometers.

    Returns
    -------
    list of ConjunctionClaim
        One entry per close pair. Each claim must set:

        - ``norad_a``, ``norad_b``: the two object ids
        - ``tca_utc``: time of closest approach (when they were nearest)
        - ``min_distance_km``: that closest distance in kilometers
        - ``algorithm_id``: a short name for your method (optional but useful)

    Notes
    -----
    The field name ``tca_utc`` on ``ConjunctionClaim`` means
    "time of closest approach" in UTC. Prefer computing a careful
    closest-approach time — a coarse grid alone is often not accurate enough
    for verification.
    """
    raise NotImplementedError(
        "Implement find_close_approaches() in student_solution.py. "
        "Return a list of ConjunctionClaim for every pair that comes within "
        "close_approach_threshold_km during the time window."
    )
