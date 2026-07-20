#!/usr/bin/env python3
"""Parse spacetrack_data.json and print catalog stats."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conjunction_toolkit import load_default_catalog


def main() -> None:
    catalog = load_default_catalog()
    print(f"Source: {catalog.source_path}")
    print(f"Objects: {len(catalog)}")
    epochs = [el.epoch_utc for el in catalog]
    print(f"Epoch range: {min(epochs).isoformat()} → {max(epochs).isoformat()}")

    sample_ids = catalog.ids()[:5]
    print("\nSample objects:")
    for nid in sample_ids:
        el = catalog[nid]
        print(
            f"  NORAD {el.norad_cat_id:>6}  {el.object_name:<24}  "
            f"i={el.inclination_deg:6.2f}°  n={el.mean_motion_rev_per_day:.6f} rev/day  "
            f"epoch={el.epoch_utc.isoformat()}"
        )

    iss = catalog.filter_by_name("ISS (ZARYA)")
    print(f"\nExact name 'ISS (ZARYA)': {len(iss)} object(s)")
    for el in iss:
        print(
            f"  NORAD {el.norad_cat_id}: {el.object_name} "
            f"epoch={el.epoch_utc.isoformat()}"
        )


if __name__ == "__main__":
    main()
