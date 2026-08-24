# Conjunction Hackathon Toolkit

Python toolkit (Skyfield / SGP4) for loading satellite catalogs, propagating orbits, plotting, and checking close approaches.

**Students:** open the Colab notebook — do not clone this repo.

Colab: https://colab.research.google.com/github/abensour/collision_detection_hackathon/blob/solve/conjunction_tutorial.ipynb

---

## How to run

1. Open the Colab link above.
2. **Runtime → Run all**. Setup downloads the `solve` branch zip (`catalog` + `conjunction_toolkit/`) into `/content/hackathon`.
3. Implement `find_close_approaches` in the notebook solution cell.

---

## Challenge (short)

Find pairs of satellites that come within **10 km** while propagating orbits forward. You have **1 minute**. Claims that are True at the reported time count; tied teams are ranked by speed.

Your function receives the **full catalog** (all orbital data for every object), not a pre-trimmed satellite list.

```python
def find_close_approaches(
    catalog,                       # Catalog: full orbital data for all objects
    propagate_from_utc,
    propagate_until_utc,
    close_approach_threshold_km,   # default 10 km
    max_runtime_seconds,           # default 60 s
) -> list[ConjunctionClaim]:
    ...
```

Each claim needs `norad_a`, `norad_b`, and `tca_utc`.  
Optional: `min_distance_km`, `algorithm_id`.

To propagate, call `catalog_to_satellites(catalog)`.

---

## Toolkit API

| Function | Purpose |
|----------|---------|
| `load_default_catalog()` | Load `spacetrack_data.json` |
| `catalog_to_satellites(catalog, norad_ids=...)` | Build Skyfield satellites for propagation |
| `time_grid(from, until, step_seconds)` | Sample times |
| `propagate_many(sats, times)` | Positions (km) |
| `closest_approach_on_grid(pos_a, pos_b, times)` | Nearest sample on a time grid |
| `plot_trajectories` / `plot_pair_with_distance` / `save_html` | Plots |

Types: `Catalog`, `OrbitalElements`, `ConjunctionClaim`.

---

## Layout (after Colab setup)

```
/content/hackathon/
├── spacetrack_data.json
├── conjunction_toolkit/
├── requirements.txt
└── README.md
```

The notebook stays in Colab; your algorithm is edited in a notebook cell.
