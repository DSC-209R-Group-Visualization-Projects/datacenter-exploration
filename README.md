# Data Center Exploration

**DSC 209R Final Project · UC San Diego**

Data centers are being built across the United States at a record pace, and a growing number of communities are pushing back. This project maps where the build-out is happening, where towns are pausing or restricting it, and whether the concerns residents raise most often (electricity bills, grid strain and water) are supported by public data.

## Research questions

1. **Build-out:** Where are data centers operating and planned?
2. **Pushback:** Where, when and why are local governments pausing data center development, and what happens to those pauses?
3. **Concerns:** Do data centers sit in water-stressed basins, raise residential electricity prices, or strain the grid?

Each concern is analyzed at its own geographic unit (river basin, utility, balancing authority) rather than forced down to counties.

## Prototypes

| | Topic | Notebook | Static figure |
|---|---|---|---|
| A | Data centers over county water stress | `jppolizzi/prototype_a_map.ipynb` | `images/prototype_a_map.png` |
| B | Water stress scorecard | `jppolizzi/prototype_b_scorecard.ipynb` | `images/prototype_b_scorecard.png` |
| C | Moratoria: where, when and why | `pnidadavolu/prototype_c_pushback_wave.ipynb` | `images/prototype_c_pushback_wave.png` |
| D | Moratoria: what happened next | `pnidadavolu/prototype_d_what_next.ipynb` | `images/prototype_d_what_next.png` |

Interactive versions: `jppolizzi/prototype_a_map.html` and `pnidadavolu/prototype_c_pushback_wave.html` (open in a browser).

## Data sources

| Topic | Source | Unit |
|---|---|---|
| Data center locations, status, capacity | Data Centers Database (`data/Data_Centers_Database.csv`) | facility |
| Local moratoria and their stated reasons | [Moratorium Nation](https://github.com/mjbommar/moratorium-data-2026) (M. J. Bommarito, CC BY 4.0) | local government |
| State bills and local restrictions | datacenterbans.com | state, local action |
| Residential electricity prices, service territories | EIA Form 861 | utility × year |
| Hourly electricity demand | EIA Form 930 | balancing authority × year |
| Capacity auction prices | PJM Base Residual Auction reports | delivery year |
| Baseline water stress | WRI Aqueduct 4.0 | river basin |
| Counties, population, income | U.S. Census Bureau (CB 2025, PEP 2025, ACS 2024), USDA RUCC 2023 | county |
| Inflation adjustment | BLS CPI-U | year |

Field-level notes for every cleaned table are in [`data/clean/README.md`](data/clean/README.md).

## Repository structure

```
├── data/
│   ├── Data_Centers_Database.csv   source data center database
│   ├── clean/                      cleaned tables used by all notebooks
│   └── raw/                        raw downloads (not committed)
├── scripts/                        cleaning scripts, shared helpers, notebook generators
├── images/                         static figures
├── jppolizzi/                      prototypes A and B
└── pnidadavolu/                    prototypes C and D
```
