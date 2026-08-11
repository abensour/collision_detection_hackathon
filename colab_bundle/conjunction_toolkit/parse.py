"""Catalog loaders: SpaceTrack JSON (now) and classic TLE files (hackathon day)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Union

from skyfield.api import load
from skyfield.iokit import parse_tle_file

from conjunction_toolkit.models import Catalog, OrbitalElements

PathLike = Union[str, Path]


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    return int(float(value))


def _parse_epoch(value: str) -> datetime:
    """Parse SpaceTrack EPOCH strings into timezone-aware UTC datetimes."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # SpaceTrack often uses "YYYY-MM-DDTHH:MM:SS.ffffff" without offset
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Unrecognized EPOCH format: {value!r}") from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _record_to_elements(record: Dict[str, Any]) -> OrbitalElements:
    return OrbitalElements(
        norad_cat_id=_as_int(record["NORAD_CAT_ID"]),
        object_name=str(record.get("OBJECT_NAME") or f"NORAD {_as_int(record['NORAD_CAT_ID'])}"),
        object_id=record.get("OBJECT_ID"),
        epoch_utc=_parse_epoch(str(record["EPOCH"])),
        mean_motion_rev_per_day=_as_float(record["MEAN_MOTION"]),
        eccentricity=_as_float(record["ECCENTRICITY"]),
        inclination_deg=_as_float(record["INCLINATION"]),
        ra_of_asc_node_deg=_as_float(record["RA_OF_ASC_NODE"]),
        arg_of_pericenter_deg=_as_float(record["ARG_OF_PERICENTER"]),
        mean_anomaly_deg=_as_float(record["MEAN_ANOMALY"]),
        bstar=_as_float(record.get("BSTAR")),
        mean_motion_dot=_as_float(record.get("MEAN_MOTION_DOT")),
        mean_motion_ddot=_as_float(record.get("MEAN_MOTION_DDOT")),
        classification=str(record.get("CLASSIFICATION_TYPE") or "U"),
        element_set_no=_as_int(record.get("ELEMENT_SET_NO")),
        rev_at_epoch=_as_int(record.get("REV_AT_EPOCH")),
    )


def load_spacetrack_json(path: PathLike) -> Catalog:
    """Load a SpaceTrack GP JSON array dump into a Catalog.

    Expected fields match the local ``spacetrack_data.json`` schema
    (NORAD_CAT_ID, EPOCH, MEAN_MOTION, ECCENTRICITY, ...).
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("SpaceTrack JSON must be an array of GP records")

    catalog = Catalog(source_path=str(path.resolve()))
    for record in data:
        if not isinstance(record, dict) or "NORAD_CAT_ID" not in record:
            continue
        catalog.add(_record_to_elements(record))
    return catalog


def load_tle_file(path: PathLike, *, ts=None) -> Catalog:
    """Load a classic TLE text file into the same Catalog type.

    Supports 2-line and 3-line (name + L1 + L2) formats via Skyfield.
    Use this on hackathon day when the real catalog is a ``.tle`` file.
    """
    path = Path(path)
    if ts is None:
        ts = load.timescale()

    catalog = Catalog(source_path=str(path.resolve()))
    with path.open("rb") as fh:
        for sat in parse_tle_file(fh, ts):
            model = sat.model
            epoch_utc = sat.epoch.utc_datetime().replace(tzinfo=timezone.utc)
            mean_motion = model.no_kozai * 1440.0 / (2.0 * math.pi)
            # Store original TLE lines when Skyfield exposes them
            line1 = getattr(sat, "line1", None)
            line2 = getattr(sat, "line2", None)
            elements = OrbitalElements(
                norad_cat_id=int(model.satnum),
                object_name=sat.name or f"NORAD {int(model.satnum)}",
                epoch_utc=epoch_utc,
                mean_motion_rev_per_day=mean_motion,
                eccentricity=float(model.ecco),
                inclination_deg=float(math.degrees(model.inclo)),
                ra_of_asc_node_deg=float(math.degrees(model.nodeo)),
                arg_of_pericenter_deg=float(math.degrees(model.argpo)),
                mean_anomaly_deg=float(math.degrees(model.mo)),
                bstar=float(model.bstar),
                mean_motion_dot=float(getattr(model, "ndot", 0.0)),
                mean_motion_ddot=float(getattr(model, "nddot", 0.0)),
                line1=line1,
                line2=line2,
            )
            catalog.add(elements)
    return catalog


def default_catalog_path() -> Path:
    """Path to the bundled SpaceTrack JSON next to the project root."""
    return Path(__file__).resolve().parent.parent / "spacetrack_data.json"


def load_default_catalog() -> Catalog:
    """Load ``spacetrack_data.json`` from the project root."""
    return load_spacetrack_json(default_catalog_path())
