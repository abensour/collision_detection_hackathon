#!/usr/bin/env python3
"""Run the fast solution on the full catalog: 1 day ahead, then verify.

Usage (from project root, with venv):
    python run_hackathon.py
"""

from __future__ import annotations

import json
import time
from datetime import timedelta
from pathlib import Path

from conjunction_toolkit import (
    VerifyConfig,
    catalog_to_satellites,
    load_default_catalog,
    verify_claim,
)
from student_solution import find_close_approaches

# Contest-style settings: all objects, one day, 1-minute samples, 10 km
PROPAGATE_FOR_HOURS = 24
TIME_STEP_SECONDS = 60.0
CLOSE_APPROACH_THRESHOLD_KM = 10.0


def main() -> None:
    root = Path(__file__).resolve().parent
    out_dir = root / "output"
    out_dir.mkdir(exist_ok=True)

    catalog = load_default_catalog()
    ids = catalog.ids()
    print(f"Catalog objects: {len(ids)}")
    print(f"Source: {catalog.source_path}")

    satellites = catalog_to_satellites(catalog, norad_ids=ids)
    epochs = sorted(catalog[nid].epoch_utc for nid in ids)
    propagate_from_utc = min(epochs)
    propagate_until_utc = propagate_from_utc + timedelta(hours=PROPAGATE_FOR_HOURS)

    print(f"Propagate from : {propagate_from_utc.isoformat()}")
    print(f"Propagate until: {propagate_until_utc.isoformat()}  ({PROPAGATE_FOR_HOURS} h)")
    print(f"Time step      : {TIME_STEP_SECONDS:.0f} s")
    print(f"Threshold      : {CLOSE_APPROACH_THRESHOLD_KM} km")
    print("Running fast finder…")

    t0 = time.perf_counter()
    claims = find_close_approaches(
        satellites,
        propagate_from_utc,
        propagate_until_utc,
        TIME_STEP_SECONDS,
        CLOSE_APPROACH_THRESHOLD_KM,
    )
    find_s = time.perf_counter() - t0
    print(f"Detected {len(claims)} close approaches in {find_s:.1f} s")

    config = VerifyConfig(max_miss_distance_km=CLOSE_APPROACH_THRESHOLD_KM)
    ok_count = 0
    fail_count = 0
    fail_messages: list[str] = []

    t1 = time.perf_counter()
    for i, claim in enumerate(claims, start=1):
        result = verify_claim(claim, satellites, config=config)
        if result.ok:
            ok_count += 1
        else:
            fail_count += 1
            reason = result.messages[0] if result.messages else "verification failed"
            fail_messages.append(
                f"{claim.norad_a}–{claim.norad_b}: {claim.min_distance_km:.3f} km "
                f"@ {claim.tca_utc.isoformat()} ({reason})"
            )
        if i % 50 == 0 or i == len(claims):
            print(f"  verified {i}/{len(claims)}")
    verify_s = time.perf_counter() - t1

    print()
    print("=== Hackathon run (cloude_student fast) ===")
    print(f"  Close approaches detected : {len(claims)}")
    print(f"  Verified OK               : {ok_count}")
    print(f"  Failed verification       : {fail_count}")
    print(f"  Finder runtime            : {find_s:.1f} s")
    print(f"  Verify runtime            : {verify_s:.1f} s")
    for msg in fail_messages[:20]:
        print(f"  FAIL {msg}")
    if len(fail_messages) > 20:
        print(f"  … {len(fail_messages) - 20} more failures")

    payload = {
        "propagate_from_utc": propagate_from_utc.isoformat(),
        "propagate_until_utc": propagate_until_utc.isoformat(),
        "time_step_seconds": TIME_STEP_SECONDS,
        "close_approach_threshold_km": CLOSE_APPROACH_THRESHOLD_KM,
        "n_satellites": len(ids),
        "detected": len(claims),
        "verified_ok": ok_count,
        "failed": fail_count,
        "finder_seconds": find_s,
        "verify_seconds": verify_s,
        "claims": [
            {
                "norad_a": c.norad_a,
                "norad_b": c.norad_b,
                "tca_utc": c.tca_utc.isoformat(),
                "min_distance_km": c.min_distance_km,
                "algorithm_id": c.algorithm_id,
            }
            for c in claims
        ],
    }
    out_path = out_dir / "hackathon_claims.json"
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
