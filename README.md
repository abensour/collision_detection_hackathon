# Conjunction Hackathon Toolkit

Python toolkit (Skyfield / SGP4) for loading satellite catalogs, propagating orbits, plotting, and checking close approaches.

**Students:** open the Colab notebook — do not clone this repo.

Colab: https://colab.research.google.com/github/abensour/collision_detection_hackathon/blob/solve/conjunction_tutorial.ipynb

---

## How to run

1. Open the Colab link above.
2. **Runtime → Run all**. Setup downloads the `solve` branch zip into `/content/hackathon`.
3. Implement `find_close_approaches` in the notebook solution cell.

---

## Challenge (short)

Find pairs within **10 km** in **1 minute**. Verified True claims count; ties go to the faster run.

You receive **both**:

- `catalog: Catalog` — orbital **data** (inclination, eccentricity, …) for screening
- `satellites: Dict[int, EarthSatellite]` — same objects as **pre-built SGP4 propagators**

`satellites` is built once **before** the timer so conversion does not eat your minute.

```python
def find_close_approaches(
    catalog: Catalog,
    satellites: Dict[int, EarthSatellite],
    propagate_from_utc: datetime,
    propagate_until_utc: datetime,
    close_approach_threshold_km: float,   # default 10 km
    max_runtime_seconds: float,           # default 60 s
) -> List[ConjunctionClaim]:
    ...
```

Each claim needs `norad_a`, `norad_b`, and `tca_utc`.  
Optional: `min_distance_km`, `algorithm_id`.

---

## Toolkit API

| Function | Purpose |
|----------|---------|
| `load_default_catalog()` | Load `spacetrack_data.json` → `Catalog` |
| `catalog_to_satellites(catalog, norad_ids=...)` | Build `Dict[int, EarthSatellite]` |
| `time_grid(from, until, step_seconds)` | Sample times |
| `propagate_many(sats, times)` | Positions (km) |
| `closest_approach_on_grid(pos_a, pos_b, times)` | Nearest sample on a time grid |
| `plot_trajectories` / `plot_pair_with_distance` / `save_html` | Plots |

Types: `Catalog`, `OrbitalElements`, `ConjunctionClaim`, `EarthSatellite` (Skyfield).

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
