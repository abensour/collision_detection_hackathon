#!/usr/bin/env python3
"""Propagate a few objects and write an interactive Plotly HTML figure."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conjunction_toolkit import (
    catalog_to_satellites,
    load_default_catalog,
    plot_trajectories,
    save_html,
    time_grid,
)


def main() -> None:
    catalog = load_default_catalog()

    # Prefer exact / primary names with recent epochs
    preferred: list[int] = []
    for name in ("ISS (ZARYA)", "HST", "CSS (TIANHE)"):
        hits = [
            el
            for el in catalog.filter_by_name(name)
            if el.object_name == name or el.object_name.startswith(name + " ")
        ]
        if not hits:
            hits = list(catalog.filter_by_name(name))
        if hits:
            # Newest epoch first
            hits.sort(key=lambda el: el.epoch_utc, reverse=True)
            preferred.append(hits[0].norad_cat_id)
    if len(preferred) < 2:
        # Fall back: recent LEO objects
        leo = sorted(
            (el for el in catalog if el.mean_motion_rev_per_day > 14),
            key=lambda el: el.epoch_utc,
            reverse=True,
        )
        preferred = [el.norad_cat_id for el in leo[:3]]
    preferred = preferred[:3]

    sats = catalog_to_satellites(catalog, norad_ids=preferred)
    # Propagate from the latest shared-ish epoch among selected
    epochs = [catalog[nid].epoch_utc for nid in preferred]
    t0 = max(epochs)
    t1 = t0 + timedelta(hours=6)
    t = time_grid(t0, t1, step_seconds=60.0)

    fig = plot_trajectories(sats, t, title="Sample trajectories (GCRS)")
    out = ROOT / "examples" / "output" / "trajectories.html"
    save_html(fig, out)
    print(f"Wrote {out}")
    print(f"Objects: {[(nid, sats[nid].name) for nid in preferred]}")
    print(f"Window: {t0.isoformat()} → {t1.isoformat()}")


if __name__ == "__main__":
    main()
