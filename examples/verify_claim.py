#!/usr/bin/env python3
"""Verify a claimed conjunction from CLI args (or a demo self-check)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conjunction_toolkit import (
    ConjunctionClaim,
    VerifyConfig,
    catalog_to_satellites,
    load_default_catalog,
    refine_closest_approach,
    verify_claim,
)


def _parse_utc(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a conjunction claim")
    parser.add_argument("--a", type=int, help="NORAD ID A")
    parser.add_argument("--b", type=int, help="NORAD ID B")
    parser.add_argument("--tca", type=str, help="Claimed TCA (ISO-8601 UTC)")
    parser.add_argument("--d", type=float, help="Claimed min distance (km)")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Self-check: refine a nearby pair and verify the honest claim",
    )
    parser.add_argument(
        "--distance-tol",
        type=float,
        default=0.1,
        help="Distance tolerance km (default 0.1)",
    )
    parser.add_argument(
        "--tca-tol",
        type=float,
        default=5.0,
        help="TCA tolerance seconds (default 5)",
    )
    args = parser.parse_args()

    catalog = load_default_catalog()
    config = VerifyConfig(
        distance_tolerance_km=args.distance_tol,
        tca_tolerance_seconds=args.tca_tol,
        max_miss_distance_km=None,  # CLI: only check claim consistency unless set
    )

    if args.demo:
        # Pick two LEO objects and refine around a shared epoch, then verify
        # the honest claim (should pass). Also reject a tampered distance.
        leo = [
            el
            for el in catalog
            if el.mean_motion_rev_per_day > 14.0 and el.eccentricity < 0.02
        ][:30]
        sats = catalog_to_satellites(catalog, norad_ids=[el.norad_cat_id for el in leo])
        a_id, b_id = leo[0].norad_cat_id, leo[1].norad_cat_id
        approx = max(leo[0].epoch_utc, leo[1].epoch_utc)
        tca, dmin = refine_closest_approach(sats[a_id], sats[b_id], approx)
        claim = ConjunctionClaim(
            norad_a=a_id,
            norad_b=b_id,
            tca_utc=tca,
            min_distance_km=dmin,
            algorithm_id="demo_honest",
        )
        print(
            f"Demo honest claim: {a_id}–{b_id}  {dmin:.6f} km @ {tca.isoformat()}"
        )
        result = verify_claim(claim, sats, config=config)
        print(f"ok={result.ok}")
        print(f"recomputed_distance_km={result.recomputed_distance_km:.6f}")
        print(f"recomputed_tca_utc={result.recomputed_tca_utc}")
        print(f"distance_error_km={result.distance_error_km:.6f}")
        print(f"tca_error_seconds={result.tca_error_seconds}")
        for msg in result.messages:
            print(f"  - {msg}")
        if not result.ok:
            sys.exit(1)

        fake = ConjunctionClaim(
            norad_a=a_id,
            norad_b=b_id,
            tca_utc=tca,
            min_distance_km=0.001,
            algorithm_id="demo_fake",
        )
        fake_result = verify_claim(fake, sats, config=config)
        print("\nDemo fake claim (should FAIL):")
        print(f"ok={fake_result.ok}")
        for msg in fake_result.messages:
            print(f"  - {msg}")
        sys.exit(0 if (result.ok and not fake_result.ok) else 1)

    if None in (args.a, args.b, args.tca, args.d):
        parser.error("Provide --a --b --tca --d, or use --demo")

    claim = ConjunctionClaim(
        norad_a=args.a,
        norad_b=args.b,
        tca_utc=_parse_utc(args.tca),
        min_distance_km=args.d,
        algorithm_id="cli",
    )
    sats = catalog_to_satellites(
        catalog, norad_ids=[claim.norad_a, claim.norad_b]
    )
    result = verify_claim(claim, sats, config=config)
    print(f"ok={result.ok}")
    print(f"recomputed_distance_km={result.recomputed_distance_km:.6f}")
    print(f"recomputed_tca_utc={result.recomputed_tca_utc}")
    print(f"distance_error_km={result.distance_error_km:.6f}")
    print(f"tca_error_seconds={result.tca_error_seconds}")
    for msg in result.messages:
        print(f"  - {msg}")
    sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
