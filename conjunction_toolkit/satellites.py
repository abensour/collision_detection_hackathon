"""Build Skyfield EarthSatellite objects from a Catalog.

``catalog_to_satellites`` is the usual entry point for the notebook:
turn selected catalog rows into objects you can propagate with SGP4.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

from sgp4.api import WGS72, Satrec
from sgp4.conveniences import sat_epoch_datetime
from skyfield.api import EarthSatellite, load
from skyfield.timelib import Timescale

from conjunction_toolkit.models import Catalog, OrbitalElements

# Days from 1949-12-31 00:00 UTC used by SGP4 epoch field
_SGP4_EPOCH_JD = 2433281.5  # Julian date of 1949-12-31 00:00 TT≈UTC for this purpose


def get_timescale(ts: Optional[Timescale] = None) -> Timescale:
    return ts if ts is not None else load.timescale()


def _datetime_to_sgp4_epoch_days(dt: datetime) -> float:
    """Convert UTC datetime to SGP4 epoch (days since 1949-12-31 00:00 UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # Julian date via Skyfield for consistency
    ts = load.timescale()
    t = ts.from_datetime(dt)
    return t.ut1 - _SGP4_EPOCH_JD


def elements_to_satrec(elements: OrbitalElements) -> Satrec:
    """Initialize an sgp4 Satrec from normalized OrbitalElements."""
    satrec = Satrec()
    # Mean motion: rev/day → radians/minute
    no_kozai = elements.mean_motion_rev_per_day * 2.0 * math.pi / 1440.0
    # ndot in TLE is rev/day²; sgp4init expects rad/min²
    # Skyfield/sgp4 convention: ndot is already in rad/min² when using sgp4init
    # SpaceTrack MEAN_MOTION_DOT is in rev/day² (same as TLE ndot field after decoding)
    # sgp4init expects: ndot in radians/minute²
    ndot = elements.mean_motion_dot * 2.0 * math.pi / (1440.0 ** 2)
    # nddot: SpaceTrack is rev/day³ → rad/min³
    nddot = elements.mean_motion_ddot * 2.0 * math.pi / (1440.0 ** 3)

    satrec.sgp4init(
        WGS72,
        "i",
        elements.norad_cat_id,
        _datetime_to_sgp4_epoch_days(elements.epoch_utc),
        elements.bstar,
        ndot,
        nddot,
        elements.eccentricity,
        math.radians(elements.arg_of_pericenter_deg),
        math.radians(elements.inclination_deg),
        math.radians(elements.mean_anomaly_deg),
        no_kozai,
        math.radians(elements.ra_of_asc_node_deg),
    )
    return satrec


def elements_to_satellite(
    elements: OrbitalElements,
    *,
    ts: Optional[Timescale] = None,
) -> EarthSatellite:
    """Create a Skyfield EarthSatellite from OrbitalElements.

    Prefers classic TLE lines when present (hackathon TLE path);
    otherwise builds via ``Satrec.sgp4init`` from element fields.
    """
    ts = get_timescale(ts)
    if elements.line1 and elements.line2:
        return EarthSatellite(
            elements.line1,
            elements.line2,
            elements.object_name,
            ts,
        )
    satrec = elements_to_satrec(elements)
    return EarthSatellite.from_satrec(satrec, ts)


def catalog_to_satellites(
    catalog: Catalog,
    *,
    norad_ids: Optional[Sequence[int]] = None,
    ts: Optional[Timescale] = None,
) -> Dict[int, EarthSatellite]:
    """Turn catalog rows into satellites you can propagate.

    Parameters
    ----------
    catalog:
        Loaded catalog.
    norad_ids:
        If given, only build these object ids; otherwise build all.

    Returns
    -------
    dict
        ``{object_id: EarthSatellite}`` ready for ``propagate_positions``.
    """
    ts = get_timescale(ts)
    ids = list(norad_ids) if norad_ids is not None else catalog.ids()
    out: Dict[int, EarthSatellite] = {}
    for nid in ids:
        el = catalog.get(nid)
        if el is None:
            continue
        sat = elements_to_satellite(el, ts=ts)
        # Ensure name is set for plotting
        if not sat.name:
            sat.name = el.object_name
        out[nid] = sat
    return out


def satellite_epoch_utc(sat: EarthSatellite) -> datetime:
    """Return the satellite element epoch as an aware UTC datetime."""
    return sat_epoch_datetime(sat.model).replace(tzinfo=timezone.utc)
