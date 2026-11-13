# Cleaned data

Rebuild with `python3 scripts/<script>.py` from the repo root. Order: `clean_counties`, `clean_datacenters`, `clean_energy`, `clean_grid_water`, `clean_policy`. Raw downloads live in `data/raw/` and are not cleaned in place.

| File | Grain | Source | Notes |
|---|---|---|---|
| counties.csv | county (GEOID) | Census CB 2025, PEP 2025, ACS 2024, USDA RUCC 2023 | Join spine. CT uses 2025 planning regions. |
| datacenters.csv | facility | Data_Centers_Database.csv | MW ranges use the midpoint. County is spatial, falling back to name. `pushback_documented=False` means no evidence found, not no pushback. |
| cpi_annual.csv | year | BLS CPI-U | `deflator_to_2025` converts to 2025 dollars. |
| eia861_utility_sales.csv | utility x state x part x year | EIA-861 | Compare prices only where `price_comparable`. |
| eia861_state_residential.csv | state x year | EIA-861 | EIA method: revenue A+B+C, sales and customers A+B. |
| eia861_utility_counties.csv | utility x county x year | EIA-861 | `county_geoid` null for old AK areas and old CT counties. |
| eia861_ba_codes.csv | BA | EIA-861 | Code to name. |
| eia930_ba_annual.csv | BA x year | EIA-930 hourly | Use `complete_year`. 2026 is partial. Isolated spikes are removed (25% and 100 MW from a 7-hour rolling median). `peak_suspect` flags SEC 2021, a multi-hour glitch. |
| pjm_bra_rto_prices.csv | delivery year | PJM BRA reports | $/MW-day. |
| aqueduct_us_basins.csv | basin x state | WRI Aqueduct 4.0 | A single baseline snapshot, with 2030/2050 BAU columns. No basin-to-county overlay yet. |
| aqueduct_state_summary.csv | state | derived | Area shares by stress level. |
| policy_states.csv / policy_state_bills.csv | state / bill | datacenterbans.com | `outcome` is derived from free text. |
| policy_local_actions.csv | local action | datacenterbans.com | `in_force`, `is_restrictive`, `ballot_related` are derived. 4 CT rows have old county FIPS. |
| policy_county_summary.csv | county | derived | |

Caveats: correlation is not causation. Units differ (utility, balancing authority, basin, county), so analyze each concern at its native unit. Ballot measures (Ballotpedia) are not collected yet.
