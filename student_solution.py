"""Student solution: find close approaches between satellites.

This file ships a fast altitude-band + KD-tree search so Colab Run all
can evaluate a working finder. Replace ``find_close_approaches`` with your
own algorithm if you want — keep the function name and arguments.
"""

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
        - ``min_distance_km``: that closest distance in kilometers
        - ``algorithm_id``: a short name for your method (optional but useful)
    """
    claims = screen_pairs_fast(
        satellites,
        propagate_from_utc,
        propagate_until_utc,
        step_seconds=time_step_seconds,
        threshold_km=close_approach_threshold_km,
        refine=True,
        algorithm_id="fast_kdtree",
    )
    return [
        claim
        for claim in claims
        if claim.min_distance_km > 1e-6
        and propagate_from_utc <= claim.tca_utc <= propagate_until_utc
    ]
