"""Shared data models for the conjunction toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, Iterator, List, Optional, Sequence


@dataclass(frozen=True)
class OrbitalElements:
    """Normalized orbital elements shared by SpaceTrack JSON and classic TLE loaders."""

    norad_cat_id: int
    object_name: str
    epoch_utc: datetime
    mean_motion_rev_per_day: float
    eccentricity: float
    inclination_deg: float
    ra_of_asc_node_deg: float
    arg_of_pericenter_deg: float
    mean_anomaly_deg: float
    bstar: float = 0.0
    mean_motion_dot: float = 0.0
    mean_motion_ddot: float = 0.0
    object_id: Optional[str] = None
    classification: str = "U"
    element_set_no: int = 0
    rev_at_epoch: int = 0
    # Present when loaded from classic TLE lines
    line1: Optional[str] = None
    line2: Optional[str] = None

    def __post_init__(self) -> None:
        if self.epoch_utc.tzinfo is None:
            object.__setattr__(
                self, "epoch_utc", self.epoch_utc.replace(tzinfo=timezone.utc)
            )


@dataclass
class Catalog:
    """NORAD-ID-keyed collection of orbital elements."""

    objects: Dict[int, OrbitalElements] = field(default_factory=dict)
    source_path: Optional[str] = None

    def __len__(self) -> int:
        return len(self.objects)

    def __contains__(self, norad_id: int) -> bool:
        return norad_id in self.objects

    def __getitem__(self, norad_id: int) -> OrbitalElements:
        return self.objects[norad_id]

    def __iter__(self) -> Iterator[OrbitalElements]:
        return iter(self.objects.values())

    def get(self, norad_id: int) -> Optional[OrbitalElements]:
        return self.objects.get(norad_id)

    def ids(self) -> List[int]:
        return list(self.objects.keys())

    def filter_by_ids(self, norad_ids: Sequence[int]) -> "Catalog":
        selected = {
            nid: self.objects[nid] for nid in norad_ids if nid in self.objects
        }
        return Catalog(objects=selected, source_path=self.source_path)

    def filter_by_name(self, substring: str, *, case_sensitive: bool = False) -> "Catalog":
        needle = substring if case_sensitive else substring.lower()
        selected: Dict[int, OrbitalElements] = {}
        for el in self.objects.values():
            hay = el.object_name if case_sensitive else el.object_name.lower()
            if needle in hay:
                selected[el.norad_cat_id] = el
        return Catalog(objects=selected, source_path=self.source_path)

    def add(self, elements: OrbitalElements) -> None:
        self.objects[elements.norad_cat_id] = elements

    def extend(self, elements: Iterable[OrbitalElements]) -> None:
        for el in elements:
            self.add(el)


@dataclass(frozen=True)
class ConjunctionClaim:
    """A claimed close approach between two objects."""

    norad_a: int
    norad_b: int
    tca_utc: datetime
    min_distance_km: float
    algorithm_id: Optional[str] = None

    def __post_init__(self) -> None:
        a, b = sorted((self.norad_a, self.norad_b))
        object.__setattr__(self, "norad_a", a)
        object.__setattr__(self, "norad_b", b)
        if self.tca_utc.tzinfo is None:
            object.__setattr__(
                self, "tca_utc", self.tca_utc.replace(tzinfo=timezone.utc)
            )


@dataclass
class VerificationResult:
    """Outcome of independently re-checking a ConjunctionClaim."""

    ok: bool
    recomputed_distance_km: float
    recomputed_tca_utc: Optional[datetime]
    distance_error_km: float
    tca_error_seconds: Optional[float]
    messages: List[str] = field(default_factory=list)
