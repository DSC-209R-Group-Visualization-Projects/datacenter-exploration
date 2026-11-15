# Pushback prototypes (C and D)

Where, when and why towns pause data centers, and what happens to those pauses afterward.
Same layout as `jppolizzi/`: notebooks here, scripts in `scripts/`, cleaned data in `data/clean/`, figures in `images/`. No existing file was changed.

| File | What it is |
|---|---|
| `../scripts/clean_moratoria.py` | Cleans the Moratorium Nation inventory to data center moratoria |
| `../scripts/make_pushback_prototypes.py` | Writes the two notebooks below |
| `../data/clean/moratoria_local.csv` | One row per local moratorium covering data centers |
| `prototype_c_pushback_wave.ipynb` | C: where, when, why (static figure + interactive slider map) |
| `prototype_c_pushback_wave.html` | C: interactive map with a time slider linked to the reasons chart |
| `prototype_d_what_next.ipynb` | D: status of pauses and upcoming end dates |
| `../images/prototype_c_pushback_wave.png`, `../images/prototype_d_what_next.png` | Static figures for the proposal |

## Data

Moratorium Nation (M. J. Bommarito), https://github.com/mjbommar/moratorium-data-2026, CC BY 4.0.
Download `data/moratorium_inventory.csv` from that repo into `data/raw/moratorium_nation/` (gitignored), pulled at upstream commit `3b6e904`.

`moratoria_local.csv` columns worth knowing:
- `adopted`: drops `pending` (proposals), `rejected` and `unknown`. `in_force`: `active` or `extended`.
- `reason_*`: the author's `trigger_categories` as booleans. One moratorium can cite several reasons.
- `county_geoid`: county containing the jurisdiction's reference point (a point, not a boundary).

Caveats: 72% of rows carry at least one `[VERIFY]` flag. Only May to July 2026 was searched state by state, so part of the 2026 rise may be search effort. Reasons are those cited by local governments, not a survey of residents.

## Rebuild (from the repo root)

```
python3 scripts/clean_moratoria.py
python3 scripts/make_pushback_prototypes.py
```
Then run the two notebooks from inside `pnidadavolu/`. Extra packages beyond `requirements.txt`: `plotly`, `matplotlib`, `nbformat`.
