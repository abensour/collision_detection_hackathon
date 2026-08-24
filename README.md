# Conjunction Hackathon Toolkit

Python toolkit built on [Skyfield](https://rhodesmill.org/skyfield/) (SGP4) for loading satellite catalogs, propagating orbits, visualizing trajectories, and checking close approaches (conjunctions).

---

## Satellite basics

### Gravity and circular orbits

A satellite stays in orbit when its sideways speed matches Earth’s gravity at that altitude. For a **circular** orbit around Earth (two-body approximation):

\[
v = \sqrt{\frac{GM}{r}}
\qquad
T = 2\pi\sqrt{\frac{r^{3}}{GM}}
\]

| Symbol | Meaning |
|--------|---------|
| \(v\) | Orbital speed |
| \(T\) | Orbital period (one full revolution) |
| \(r\) | Distance from Earth’s **center** (not height above the surface) |
| \(GM\) | Earth’s gravitational parameter ≈ \(3.986 \times 10^{5}\,\mathrm{km}^{3}/\mathrm{s}^{2}\) |

Height above the surface is \(h = r - R_E\), with Earth radius \(R_E \approx 6371\,\mathrm{km}\).

So higher orbits are slower and take longer to go around once.

### Typical regimes

| Regime | Approx. altitude | Rough speed | Rough period |
|--------|------------------|-------------|--------------|
| LEO (low Earth orbit) | 200–2000 km | ~7.8–6.9 km/s | ~90–130 min |
| MEO | ~20 000 km (e.g. GPS) | ~3.9 km/s | ~12 h |
| GEO | ~35 786 km | ~3.1 km/s | ~24 h (matches Earth’s rotation) |

Most catalog objects in SpaceTrack-style dumps are in **LEO**: they move fast, complete a revolution in about 1.5 hours, and relative geometry between two objects can change quickly.

### How satellites move (Keplerian elements)

Catalog data (TLE / SpaceTrack GP) describes each object with classical orbital elements, including:

| Element | What it controls |
|---------|------------------|
| **Inclination** | Tilt of the orbital plane vs. Earth’s equator |
| **RAAN** (right ascension of ascending node) | Orientation of the plane in space |
| **Argument of perigee** | Where the closest point sits in the plane |
| **Eccentricity** | How elongated the ellipse is (`0` ≈ circular) |
| **Mean anomaly** | Where the satellite is along the orbit at epoch |
| **Mean motion** | Revolutions per day → related to semi-major axis / period |

The toolkit does **not** integrate Newton’s laws from scratch. It uses **SGP4**: a standard propagator that turns those elements into positions over time, including simplified drag and other perturbations via fields like `BSTAR`.

### Positions in this toolkit

All positions and miss distances are in Skyfield **GCRS** coordinates, in **kilometers**. Use the same frame everywhere so distances stay comparable.

### Conjunction vocabulary

| Term | Meaning |
|------|---------|
| **Conjunction** | Two objects coming close in space (and usually near the same time) |
| **TCA** | Time of closest approach |
| **Miss distance** | Minimum separation at TCA |

A claimed conjunction is a pair of NORAD IDs, a TCA, and a miss distance. The verifier re-propagates both objects independently and checks that claim.

---

## Finding your way around the code

```
conjections_hackaton/
├── conjunction_toolkit/     # library package
│   ├── models.py            # Catalog, OrbitalElements, ConjunctionClaim, …
│   ├── parse.py             # load SpaceTrack JSON / TLE → Catalog
│   ├── satellites.py        # Catalog → Skyfield EarthSatellite
│   ├── propagate.py         # time grids, positions, pair distances
│   ├── visualize.py         # Plotly 3D / distance plots
│   ├── baseline.py          # simple all-pairs screener
│   ├── screener.py          # fast altitude-band + spatial-hash screener
│   ├── verify.py            # independent check of a claim
│   └── __init__.py          # public API re-exports
├── examples/                # runnable scripts
├── spacetrack_data.json     # catalog dump (when present)
└── requirements.txt
```

### Suggested reading order

1. **`models.py`** — data shapes (`Catalog`, `OrbitalElements`, `ConjunctionClaim`).
2. **`parse.py`** — how files become a `Catalog`.
3. **`satellites.py`** — how elements become propagatable satellites.
4. **`propagate.py`** — time grids and GCRS positions / distances.
5. **`visualize.py`** / **`verify.py`** / **`baseline.py`** / **`screener.py`** — plotting, checking claims, brute-force vs fast screening.

### Module map

| Module | Responsibility | Start here if you want to… |
|--------|----------------|----------------------------|
| `parse` | Load SpaceTrack JSON or classic `.tle` into `Catalog` | Change input formats or inspect catalog fields |
| `satellites` | Build `EarthSatellite` objects (SGP4) | Understand how elements become orbits |
| `propagate` | `time_grid`, `propagate_positions`, `pair_distances`, closest approach on a grid | Compute where objects are and how far apart |
| `visualize` | Plotly trajectories and pair close-approach views | Debug geometry visually |
| `baseline` | Brute-force screen of unique pairs on a time grid | See a straightforward “check everything” loop |
| `screener` | Altitude-band + spatial-hash screen (`screen_pairs_fast`) | Run a faster geometric conjunction search |
| `verify` | Re-propagate + refine TCA; accept/reject a `ConjunctionClaim` | Validate a reported close approach |
| `models` | Shared dataclasses | Extend or serialize toolkit data |

Public entry points are re-exported from `conjunction_toolkit` (see `__init__.py`). Prefer importing from the package root:

```python
from conjunction_toolkit import load_default_catalog, catalog_to_satellites, time_grid
```

### Typical data flow

```
catalog file
    → parse (Catalog / OrbitalElements)
    → satellites (EarthSatellite)
    → propagate (positions in km, GCRS)
    → visualize  and/or  screen pairs  and/or  verify_claim
```

### Examples

| Script | What it shows |
|--------|----------------|
| `examples/parse_demo.py` | Loading and inspecting the catalog |
| `examples/plot_trajectories.py` | 3D orbits → `examples/output/trajectories.html` |
| `examples/run_baseline_small.py` | Small LEO subset screen + verify |
| `examples/run_fast_screen.py` | Fast screener vs baseline timing / pair coverage |
| `examples/verify_claim.py` | CLI for checking a claim (`--demo` or explicit args) |

---

## Setup

```bash
cd conjections_hackaton
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data

- **Now:** `spacetrack_data.json` — SpaceTrack GP element fields (large catalog when present).
- **Hackathon day:** classic `.tle` file via `load_tle_file()`.

```python
from conjunction_toolkit import load_tle_file, load_spacetrack_json

catalog = load_spacetrack_json("spacetrack_data.json")
# catalog = load_tle_file("catalog.tle")
```

Downstream APIs (`catalog_to_satellites`, propagation, verify, Plotly) stay the same.

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

```bash
python examples/parse_demo.py
python examples/plot_trajectories.py
python examples/run_baseline_small.py
python examples/run_fast_screen.py       # optional N: python examples/run_fast_screen.py 200
python examples/verify_claim.py --demo
python examples/verify_claim.py --a 1 --b 5 --tca 2026-05-13T12:00:00+00:00 --d 5000
```
## Claiming a conjunction

Submit a `ConjunctionClaim(norad_a, norad_b, tca_utc, min_distance_km)`. Organizers run `verify_claim()`, which:

1. Re-propagates both objects from the shared catalog
2. Refines TCA around the claimed time (coarse → fine grid; expands if the min is near a window edge)
3. Accepts only if distance and TCA match within tolerances (default: 100 m, 5 s)

Refine your TCA before submitting — a coarse time grid alone often fails those tolerances. Optional `VerifyConfig.max_miss_distance_km` can also require the true miss distance to be under a threshold.
