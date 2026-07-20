# Conjunction Hackathon Toolkit

Python toolkit built on [Skyfield](https://rhodesmill.org/skyfield/) (SGP4) for a hackathon focused on **fastest conjunction-finding algorithms**.

## What you get

| Module | Role |
|--------|------|
| `parse` | Load SpaceTrack JSON **now**; `load_tle_file()` ready for classic TLE on hackathon day |
| `satellites` / `propagate` | Build `EarthSatellite` objects and propagate positions (**km, GCRS**) |
| `visualize` | Interactive **Plotly** 3D trajectories and pair close-approach views |
| `baseline` | Deliberately slow **O(N²×T)** brute-force screener to beat |
| `verify` | Independent check of a claimed TCA / miss distance |

## Setup

```bash
cd conjections_hackaton
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data

- **Now:** [`spacetrack_data.json`](spacetrack_data.json) — SpaceTrack GP element fields (~67k objects).
- **Hackathon day:** swap to a classic `.tle` file:

```python
from conjunction_toolkit import load_tle_file, load_spacetrack_json

catalog = load_spacetrack_json("spacetrack_data.json")  # today
# catalog = load_tle_file("catalog.tle")                # hackathon day
```

Downstream APIs (`catalog_to_satellites`, screening, verify, Plotly) stay the same.

## Quick start

```python
from datetime import timedelta
from conjunction_toolkit import (
    load_default_catalog,
    catalog_to_satellites,
    time_grid,
    plot_trajectories,
    save_html,
)

catalog = load_default_catalog()
ids = catalog.ids()[:3]
sats = catalog_to_satellites(catalog, norad_ids=ids)
t0 = catalog[ids[0]].epoch_utc
t = time_grid(t0, t0 + timedelta(hours=2), step_seconds=60)
fig = plot_trajectories(sats, t)
save_html(fig, "orbits.html")
```

### Examples

```bash
python examples/parse_demo.py
python examples/plot_trajectories.py          # → examples/output/trajectories.html
python examples/run_baseline_small.py         # small LEO subset + verify
python examples/verify_claim.py --demo
python examples/verify_claim.py --a 1 --b 5 --tca 2026-05-13T12:00:00+00:00 --d 5000
```

## Reference frame

All positions and miss distances use Skyfield **GCRS** coordinates in **kilometers**. Team algorithms and the verifier must use the same frame for fair comparison.

## Claiming a conjunction

Submit a `ConjunctionClaim(norad_a, norad_b, tca_utc, min_distance_km)`. Organizers run `verify_claim()` which:

1. Re-propagates both objects from the shared catalog
2. Refines TCA around the claimed time (coarse → fine grid, expanding if the min is near a window edge)
3. Accepts only if distance and TCA match within tolerances (default: 100 m, 5 s)

Refine your TCA before submitting — a coarse time grid alone will usually fail the distance/TCA tolerances. Optional `VerifyConfig.max_miss_distance_km` also requires the true miss distance to be under a threshold.

## Baseline (to beat)

`screen_pairs()` checks every unique pair at every time step. It is correct but slow — replace it with your algorithm, then pass claims through `verify_claim`.
