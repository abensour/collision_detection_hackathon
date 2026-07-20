#!/usr/bin/env python3
"""Run the slow baseline screener on a small Starlink subset."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conjunction_toolkit import (
    ConjunctionClaim,
    VerifyConfig,
    catalog_to_satellites,
    load_default_catalog,
    plot_pair_with_distance,
    refine_closest_approach,
    save_html,
    screen_pairs,
    time_grid,
    verify_claim,
)


def main() -> None:
    catalog = load_default_catalog()

    # Dense constellation slice — more likely to show close approaches in a short demo
    min_epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pool = [
        el
        for el in catalog
        if el.epoch_utc >= min_epoch and "STARLINK" in el.object_name.upper()
    ]
    pool.sort(key=lambda el: el.norad_cat_id)
    subset = pool[:50]
    ids = [el.norad_cat_id for el in subset]
    print(f"Screening {len(ids)} Starlink objects (baseline brute-force)...")

    sats = catalog_to_satellites(catalog, norad_ids=ids)
    epochs = sorted(el.epoch_utc for el in subset)
    t0 = epochs[len(epochs) // 2]
    t1 = t0 + timedelta(hours=6)

    threshold_km = 100.0
    raw_claims = screen_pairs(
        sats,
        t0,
        t1,
        step_seconds=60.0,
        threshold_km=threshold_km,
    )
    print(f"Window: {t0.isoformat()} → {t1.isoformat()}")
    print(f"Raw grid claims within {threshold_km} km: {len(raw_claims)}")

    # Refine before verifying (coarse grid TCA is only approximate)
    config = VerifyConfig(max_miss_distance_km=threshold_km)
    claims: list[ConjunctionClaim] = []
    for raw in raw_claims:
        tca, dmin = refine_closest_approach(
            sats[raw.norad_a], sats[raw.norad_b], raw.tca_utc
        )
        claims.append(
            ConjunctionClaim(
                norad_a=raw.norad_a,
                norad_b=raw.norad_b,
                tca_utc=tca,
                min_distance_km=dmin,
                algorithm_id="baseline_bruteforce_refined",
            )
        )
    claims.sort(key=lambda c: c.min_distance_km)

    for claim in claims[:10]:
        result = verify_claim(claim, sats, config=config)
        status = "OK" if result.ok else "FAIL"
        print(
            f"  [{status}] {claim.norad_a}–{claim.norad_b}  "
            f"claimed {claim.min_distance_km:.3f} km @ {claim.tca_utc.isoformat()}  "
            f"→ recomputed {result.recomputed_distance_km:.3f} km"
        )
        for msg in result.messages:
            print(f"       {msg}")

    if claims:
        best = claims[0]
        sat_a, sat_b = sats[best.norad_a], sats[best.norad_b]
        t = time_grid(
            best.tca_utc - timedelta(minutes=30),
            best.tca_utc + timedelta(minutes=30),
            step_seconds=30.0,
        )
        fig = plot_pair_with_distance(
            sat_a,
            sat_b,
            t,
            tca=best.tca_utc,
            norad_a=best.norad_a,
            norad_b=best.norad_b,
            threshold_km=threshold_km,
            title=f"Baseline hit {best.norad_a}–{best.norad_b}",
        )
        out = ROOT / "examples" / "output" / "baseline_pair.html"
        save_html(fig, out)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
