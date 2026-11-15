"""Clean the Moratorium Nation inventory down to local data center moratoria.

Source:  Moratorium Nation (M. J. Bommarito), https://github.com/mjbommar/moratorium-data-2026, CC BY 4.0
         Download data/moratorium_inventory.csv into data/raw/moratorium_nation/ (pulled at upstream commit 3b6e904).
         Column definitions: docs/codebook.md in the same repo.
Output:  data/clean/moratoria_local.csv   one row per local moratorium that covers data centers

Run from the repo root: python3 scripts/clean_moratoria.py

Why this and not policy_local_actions.csv: datacenterbans.com has no coded reasons. This inventory tags each
moratorium with why it was adopted (`trigger_categories`), its term, its expiry and a closed-vocab status.
Note: 74% of all rows carry at least one [VERIFY] flag, and only May-Jul 2026 was swept state by state.
"""
import json

import geopandas as gpd
import pandas as pd

from common import CLEAN, RAW

SRC = RAW / "moratorium_nation" / "moratorium_inventory.csv"
REASONS = ["specific_project", "regulatory_gap", "infrastructure_capacity", "environmental", "noise", "water",
           "grid_energy", "fire_safety", "land_use_compatibility", "property_values", "legal_or_litigation",
           "agricultural_preservation", "other"]
# Reasons that name a harm, as opposed to "we need time to write rules" or "a project showed up".
CONCRETE = ["water", "grid_energy", "noise", "land_use_compatibility", "environmental", "infrastructure_capacity",
            "property_values", "fire_safety", "agricultural_preservation"]


def tags(s):
    try:
        return json.loads(s) if isinstance(s, str) and s.strip() else []
    except json.JSONDecodeError:
        return []


def main():
    m = pd.read_csv(SRC, dtype=str)
    m = m[m["sectors"].map(tags).map(lambda t: "data_center" in t)].copy()

    out = pd.DataFrame({
        "moratorium_id": m["moratorium_id"],
        "state": m["state_abbrev"],
        "jurisdiction": m["jurisdiction"],
        "jurisdiction_type": m["jurisdiction_type"],
        "lat": pd.to_numeric(m["latitude"], errors="coerce"),
        "lon": pd.to_numeric(m["longitude"], errors="coerce"),
        # date_enacted_iso can be YYYY, YYYY-MM or YYYY-MM-DD; keep month precision or better for timelines.
        "date_enacted": pd.to_datetime(m["date_enacted_iso"].where(m["date_enacted_iso"].str.len() >= 7), errors="coerce"),
        "date_uncertainty": m["date_enacted_uncertainty"],
        "enacted_status": m["enacted_status"],
        "duration_kind": m["duration_kind"],
        "duration_text": m["duration"],
        "current_end_date": pd.to_datetime(m["current_end_date_iso"], errors="coerce"),
        "trigger_text": m["trigger"],
        "has_verify": m["has_verify_tags"].eq("True"),
        "verify_count": pd.to_numeric(m["verify_count"], errors="coerce").fillna(0).astype(int),
        "also_crypto": m["sectors"].map(tags).map(lambda t: "cryptocurrency_mining" in t),
    })
    # pending = proposal or not yet effective; rejected = proposal voted down; neither is an adopted pause.
    out["adopted"] = ~out["enacted_status"].isin(["pending", "rejected", "unknown"])
    out["in_force"] = out["enacted_status"].isin(["active", "extended"])
    out["year"] = out["date_enacted"].dt.year.astype("Int64")
    out["quarter"] = out["date_enacted"].dt.to_period("Q").astype(str).replace("NaT", pd.NA)

    t = m["trigger_categories"].map(tags)
    for r in REASONS:
        out[f"reason_{r}"] = t.map(lambda x, r=r: r in x).values
    out["n_reasons"] = t.map(len).values
    out["any_concrete_reason"] = out[[f"reason_{r}" for r in CONCRETE]].any(axis=1)

    # County from the jurisdiction reference point (a point, not a boundary; see codebook).
    geo = gpd.read_file(CLEAN / "counties_simplified.geojson")[["geoid", "geometry"]]
    pts = gpd.GeoDataFrame(out, geometry=gpd.points_from_xy(out["lon"], out["lat"]), crs="EPSG:4326")
    j = gpd.sjoin(pts, geo.to_crs("EPSG:4326"), how="left", predicate="within")
    out["county_geoid"] = j.loc[~j.index.duplicated(), "geoid"].values

    out = out.sort_values(["date_enacted", "state", "jurisdiction"], na_position="last")
    out.to_csv(CLEAN / "moratoria_local.csv", index=False)

    a = out[out.adopted]
    print(f"data center rows {len(out)}; adopted {len(a)}; in force {int(out.in_force.sum())}; "
          f"with month-or-better date {int(a.date_enacted.notna().sum())}; county matched {int(out.county_geoid.notna().sum())}")
    print("status", out.enacted_status.value_counts().to_dict())
    print("verify-flagged share", round(out.has_verify.mean(), 2))


if __name__ == "__main__":
    main()
