# Conjunction Hackathon Toolkit

Python toolkit built on [Skyfield](https://rhodesmill.org/skyfield/) (SGP4) for loading satellite catalogs, propagating orbits, visualizing trajectories, and checking close approaches.

**Students:** open `conjunction_tutorial.ipynb` in Google Colab (not this git repo). Run **Setup**, then **Run all**. That download is the full student package.

Colab notebook: https://colab.research.google.com/github/abensour/collision_detection_hackathon/blob/solve/conjunction_tutorial.ipynb

---

## Aim

Given a catalog of satellites, find pairs that come close while you propagate their orbits forward in time. Submit **claims** (two object ids + time of closest approach + miss distance) that pass independent verification.

## What Colab gives you

| Item | Role |
|------|------|
| `spacetrack_data.json` | Catalog (~17k objects, epoch on **1 June 2026**) |
| `conjunction_toolkit/` | Load, propagate, naive baseline, plot, verify |
| `student_solution.py` | Your algorithm (`find_close_approaches`) — empty stub |
| `conjunction_tutorial.ipynb` | Step-by-step notebook + verifier |

---

## Setup (Google Colab)

1. Open the notebook link above (or upload `conjunction_tutorial.ipynb`).
2. Runtime → **Run all**. Setup downloads the `solve` branch zip into `/content/hackathon`.
3. Your code lives in `/content/hackathon/student_solution.py`.

You do not clone this repository. Everything except the notebook comes from that zip.

---

## Naive baseline

The reference algorithm is `naive_baseline_find_close_approaches` in the notebook (check every pair on a time grid). Students replace it with `student_solution.py`. Both take `max_runtime_seconds` (notebook default **300** = 5 minutes).

## Student interface

```python
def find_close_approaches(
    satellites,
    propagate_from_utc,            # start searching / propagating here
    propagate_until_utc,           # stop here (e.g. start + 6 hours)
    time_step_seconds,             # e.g. 30 * 60 for every 30 minutes
    close_approach_threshold_km,
    max_runtime_seconds,           # e.g. 300 for 5 minutes; change MAX_RUNTIME_SECONDS
) -> list[ConjunctionClaim]:
    ...
```

Example:

```python
claims = find_close_approaches(
    satellites,
    propagate_from_utc,
    propagate_until_utc,
    30 * 60,   # check every 30 minutes
    100.0,     # keep pairs closer than 100 km
    300,       # stop after 5 minutes
)
```

Each `ConjunctionClaim` needs `norad_a`, `norad_b`, `tca_utc` (time of closest approach in UTC), and `min_distance_km`.

Verification defaults: distance within **0.1 km**, closest time within **5 s**.

---

## Toolkit API (public)

| Function | Purpose |
|----------|---------|
| `load_default_catalog()` | Load `spacetrack_data.json` |
| `load_spacetrack_json(path)` / `load_tle_file(path)` | Other catalog formats |
| `catalog_to_satellites(catalog, norad_ids=...)` | Build propagatable satellites |
| `time_grid(from, until, step_seconds)` | Evenly spaced sample times |
| `propagate_positions(sat, times)` | Positions in km (GCRS) |
| `propagate_many(sats, times)` | Many satellites at once |
| `pair_distances(pos_a, pos_b)` | Distances between two position arrays |
| `closest_approach_on_grid(pos_a, pos_b, times)` | Nearest approach **among samples only** |
| `improve_closest_approach_estimate(a, b, rough_time)` | Zoom in around a rough closest time |
| `distance_at(a, b, when)` | Distance at one instant |
| `verify_claim(claim, satellites)` | Independent accept/reject |
| `plot_trajectories` / `plot_pair_with_distance` / `save_html` | Plots |

```python
from conjunction_toolkit import (
    load_default_catalog,
    catalog_to_satellites,
    time_grid,
    improve_closest_approach_estimate,
    verify_claim,
)
```

### Coarse sample vs improved closest time

- `closest_approach_on_grid` only looks at the times you sampled (e.g. every 30 minutes).
- `improve_closest_approach_estimate` re-propagates nearby on a finer grid so verification can pass.

---

## Layout

```
/content/hackathon/              # after Colab Setup
├── student_solution.py          # student code (stub)
├── spacetrack_data.json         # catalog (1 June 2026)
├── conjunction_toolkit/         # library
│   ├── models.py
│   ├── parse.py
│   ├── satellites.py
│   ├── propagate.py
│   ├── baseline.py              # naive all-pairs baseline
│   ├── verify.py
│   ├── visualize.py
│   └── __init__.py
├── requirements.txt
└── README.md
```

The notebook stays in Colab; it is not required inside that folder.

---

## Satellite basics (short)

For a circular orbit: \(v = \sqrt{GM/r}\), \(T = 2\pi\sqrt{r^3/GM}\).  
Most catalog objects here are LEO (~90–130 min periods). Positions in this toolkit are **GCRS kilometers**.

| Term | Meaning |
|------|---------|
| Close approach | Two objects come near each other |
| Time of closest approach | When they were nearest (`tca_utc` on a claim) |
| Miss distance | How close they got (km) |
