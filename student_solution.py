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
    propagate_from_utc: datetime,
    propagate_until_utc: datetime,
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
    propagate_from_utc:
        Start time: begin propagating / searching at this UTC instant.
    propagate_until_utc:
        End time: stop searching at this UTC instant.
        Example: from + 6 hours means "propagate for 6 hours into the future".
    time_step_seconds:
        How far to jump forward between position checks.
        Example: ``30 * 60`` = check every 30 minutes.
        Larger steps are faster but can miss short close approaches.
    close_approach_threshold_km:
        Report a pair only if their closest distance on your search is less
        than or equal to this many kilometers.

    Returns
    -------
    list of ConjunctionClaim
        One entry per close pair. Each claim must set:

        - ``norad_a``, ``norad_b``: the two object ids
        - ``tca_utc``: time of closest approach (when they were nearest)
          — the field name is historical; it means that time in UTC
        - ``min_distance_km``: that closest distance in kilometers
        - ``algorithm_id``: a short name for your method (optional but useful)

    Notes
    -----
    A coarse ``time_step_seconds`` only gives an approximate closest time.
    Prefer improving that estimate (see
    ``improve_closest_approach_estimate`` in the toolkit) before relying on
    verification.
    """
    raise NotImplementedError(
        "Implement find_close_approaches() in student_solution.py. "
        "Return a list of ConjunctionClaim for every pair that comes within "
        "close_approach_threshold_km while propagating from "
        "propagate_from_utc until propagate_until_utc."
    )
