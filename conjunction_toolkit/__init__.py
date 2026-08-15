"""Skyfield-based toolkit for catalog loading, propagation, and close approaches.

Public functions (import from ``conjunction_toolkit``)
------------------------------------------------------
Loading
  - ``load_default_catalog`` — load ``spacetrack_data.json`` from the project root
  - ``load_spacetrack_json`` — load any SpaceTrack-style JSON catalog file
  - ``load_tle_file`` — load a classic TLE text file (hackathon-day format)

Build satellites
  - ``catalog_to_satellites`` — turn catalog rows into propagatable satellites

Propagate / distances
  - ``time_grid`` — build evenly spaced sample times from start → end
  - ``propagate_positions`` — positions (km) of one satellite at those times
  - ``propagate_many`` — positions for many satellites at once
  - ``pair_distances`` — distances between two position arrays
  - ``closest_approach_on_grid`` — among discrete samples, find nearest approach
  - ``distance_at`` — distance between two satellites at one instant

Screening
  - ``screen_pairs`` — check every unique pair on a time grid (slow baseline)
  - ``screen_pairs_fast`` — altitude bands + KD-tree (used by student_solution.py)

Verify
  - ``improve_closest_approach_estimate`` — zoom in around a rough closest time
  - ``verify_claim`` — independently accept/reject one claim
  - ``VerifyConfig`` — tolerances for verification

Plot
  - ``plot_trajectories`` — 3D orbits
  - ``plot_pair_with_distance`` — two objects + distance-vs-time
  - ``save_html`` — write a Plotly figure to an HTML file

Data types: ``Catalog``, ``OrbitalElements``, ``ConjunctionClaim``,
``VerificationResult``.
"""

from conjunction_toolkit.baseline import screen_pairs
from conjunction_toolkit.screener import screen_pairs_fast
from conjunction_toolkit.models import (
    Catalog,
    ConjunctionClaim,
    OrbitalElements,
    VerificationResult,
)
from conjunction_toolkit.parse import (
    load_default_catalog,
    load_spacetrack_json,
    load_tle_file,
)
from conjunction_toolkit.propagate import (
    closest_approach_on_grid,
    distance_at,
    pair_distances,
    propagate_many,
    propagate_positions,
    time_grid,
)
from conjunction_toolkit.satellites import catalog_to_satellites
from conjunction_toolkit.verify import (
    VerifyConfig,
    improve_closest_approach_estimate,
    verify_claim,
)
from conjunction_toolkit.visualize import (
    plot_pair_with_distance,
    plot_trajectories,
    save_html,
)

__all__ = [
    "Catalog",
    "ConjunctionClaim",
    "OrbitalElements",
    "VerificationResult",
    "VerifyConfig",
    "catalog_to_satellites",
    "closest_approach_on_grid",
    "distance_at",
    "improve_closest_approach_estimate",
    "load_default_catalog",
    "load_spacetrack_json",
    "load_tle_file",
    "pair_distances",
    "plot_pair_with_distance",
    "plot_trajectories",
    "propagate_many",
    "propagate_positions",
    "save_html",
    "screen_pairs",
    "screen_pairs_fast",
    "time_grid",
    "verify_claim",
]

__version__ = "0.1.0"
