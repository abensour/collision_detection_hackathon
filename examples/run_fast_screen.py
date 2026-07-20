#!/usr/bin/env python3
"""Compare fast spatial screener vs brute-force baseline."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conjunction_toolkit import (
    VerifyConfig,
    catalog_to_satellites,
    load_default_catalog,
    screen_pairs,
    screen_pairs_fast,
    verify_claim,
)


def _pair_set(claims) -> set[tuple[int, int]]:
    return {(c.norad_a, c.norad_b) for c in claims}


def main() -> None:
    catalog = load_default_catalog()
    min_epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pool = [
        el
        for el in catalog
        if el.epoch_utc >= min_epoch and "STARLINK" in el.object_name.upper()
    ]
    pool.sort(key=lambda el: el.norad_cat_id)

    n = 200
    threshold_km = 25.0
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    if len(sys.argv) > 2:
        threshold_km = float(sys.argv[2])

    subset = pool[:n]
    ids = [el.norad_cat_id for el in subset]
    sats = catalog_to_satellites(catalog, norad_ids=ids)

    epochs = sorted(el.epoch_utc for el in subset)
    t0 = epochs[len(epochs) // 2]
    t1 = t0 + timedelta(hours=6)
    step = 60.0

    print(f"Objects: {len(ids)}  window: {t0.isoformat()} → {t1.isoformat()}")
    print(f"threshold={threshold_km} km  step={step} s")

    t_a = time.perf_counter()
    baseline = screen_pairs(
        sats, t0, t1, step_seconds=step, threshold_km=threshold_km
    )
    baseline_s = time.perf_counter() - t_a

    t_b = time.perf_counter()
    fast_grid = screen_pairs_fast(
        sats,
        t0,
        t1,
        step_seconds=step,
        threshold_km=threshold_km,
        refine=False,
        algorithm_id="spatial_hash_grid",
    )
    fast_grid_s = time.perf_counter() - t_b

    t_c = time.perf_counter()
    fast = screen_pairs_fast(
        sats,
        t0,
        t1,
        step_seconds=step,
        threshold_km=threshold_km,
        refine=True,
        algorithm_id="spatial_hash",
    )
    fast_s = time.perf_counter() - t_c

    base_pairs = _pair_set(baseline)
    fast_pairs = _pair_set(fast_grid)
    missing = base_pairs - fast_pairs
    extra = fast_pairs - base_pairs

    print(f"\nBaseline brute-force: {len(baseline)} claims in {baseline_s:.3f}s")
    print(f"Fast (grid only):     {len(fast_grid)} claims in {fast_grid_s:.3f}s")
    print(f"Fast (with refine):   {len(fast)} claims in {fast_s:.3f}s")
    if baseline_s > 0:
        print(f"Speedup (grid vs baseline): {baseline_s / max(fast_grid_s, 1e-9):.1f}x")

    print(f"\nPair-set match (grid): missing={len(missing)} extra={len(extra)}")
    if missing:
        print(f"  missing examples: {list(missing)[:5]}")
    if extra:
        print(f"  extra examples: {list(extra)[:5]}")

    config = VerifyConfig(max_miss_distance_km=threshold_km)
    print("\nVerify refined fast claims (top 5):")
    for claim in fast[:5]:
        result = verify_claim(claim, sats, config=config)
        status = "OK" if result.ok else "FAIL"
        print(
            f"  [{status}] {claim.norad_a}–{claim.norad_b}  "
            f"{claim.min_distance_km:.3f} km @ {claim.tca_utc.isoformat()}"
        )
        for msg in result.messages:
            print(f"       {msg}")

    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
