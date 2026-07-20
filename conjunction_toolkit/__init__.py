"""Skyfield-based toolkit for SpaceTrack/TLE parsing, propagation, and conjunctions."""

from conjunction_toolkit.baseline import screen_catalog_subset, screen_pairs
from conjunction_toolkit.models import (
    Catalog,
    ConjunctionClaim,
    OrbitalElements,
    VerificationResult,
)
from conjunction_toolkit.parse import (
    default_catalog_path,
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
from conjunction_toolkit.satellites import (
    catalog_to_satellites,
    elements_to_satellite,
    get_timescale,
)
from conjunction_toolkit.verify import VerifyConfig, refine_closest_approach, verify_claim
from conjunction_toolkit.visualize import (
    plot_distance_vs_time,
    plot_pair_close_approach,
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
    "default_catalog_path",
    "distance_at",
    "elements_to_satellite",
    "get_timescale",
    "load_default_catalog",
    "load_spacetrack_json",
    "load_tle_file",
    "pair_distances",
    "plot_distance_vs_time",
    "plot_pair_close_approach",
    "plot_pair_with_distance",
    "plot_trajectories",
    "propagate_many",
    "propagate_positions",
    "refine_closest_approach",
    "save_html",
    "screen_catalog_subset",
    "screen_pairs",
    "time_grid",
    "verify_claim",
]

__version__ = "0.1.0"
