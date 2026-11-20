"""Approximate balancing authority (BA) service regions from EIA-861, built from counties.

Outputs: data/clean/county_ba.csv          county GEOID -> BA code (2025)
         data/clean/ba_regions.geojson     one simplified polygon per BA (counties dissolved)
A county served by utilities in several BAs goes to the BA of the utility with the most residential customers
(EIA-861 lists the counties a utility serves, not its customers per county). Needs geopandas (.pylibs).
"""
import sys

import pandas as pd

from common import CLEAN, RAW, ROOT

sys.path.insert(0, str(ROOT / ".pylibs"))
import geopandas as gpd  # noqa: E402

YEAR = 2025


def main():
    u = pd.read_csv(CLEAN / "eia861_utility_sales.csv").query(f"year=={YEAR}").dropna(subset=["ba_code"])
    cust = u.groupby(["utility_id", "state", "ba_code"])["res_customers"].sum().reset_index()
    t = pd.read_csv(CLEAN / "eia861_utility_counties.csv", dtype={"county_geoid": str}).query(f"year=={YEAR}").dropna(subset=["county_geoid"])
    t = t.drop_duplicates(["utility_id", "state", "county_geoid"]).merge(cust, on=["utility_id", "state"])
    n_ba = t.groupby("county_geoid")["ba_code"].nunique().rename("n_bas_serving")
    pick = t.sort_values("res_customers", ascending=False).drop_duplicates("county_geoid")[["county_geoid", "ba_code"]]
    pick = pick.merge(n_ba, on="county_geoid")
    names = pd.read_csv(CLEAN / "eia861_ba_codes.csv").set_index("ba_code")["ba_name"]
    pick["ba_name"] = pick["ba_code"].map(names)
    pick.to_csv(CLEAN / "county_ba.csv", index=False)

    # Dissolve full-resolution counties first; dissolving pre-simplified ones leaves slivers along shared edges.
    g = gpd.read_file(RAW / "census_cb/county_5m/cb_2025_us_county_5m.shp")[["GEOID", "geometry"]]
    g = g.merge(pick, left_on="GEOID", right_on="county_geoid")
    g["geometry"] = g.geometry.buffer(0)
    r = g.dissolve(by="ba_code", as_index=False)[["ba_code", "geometry"]]
    r["ba_name"] = r["ba_code"].map(names)
    r["n_counties"] = r["ba_code"].map(pick["ba_code"].value_counts())
    r["geometry"] = r.geometry.simplify(0.02, preserve_topology=True)
    r.to_file(CLEAN / "ba_regions.geojson", driver="GeoJSON", COORDINATE_PRECISION=3)
    print(f"county_ba: {len(pick)} counties, {pick.ba_code.nunique()} BAs, {int((pick.n_bas_serving > 1).sum())} counties served by >1 BA")
    print(f"ba_regions: {len(r)} regions, {round((CLEAN / 'ba_regions.geojson').stat().st_size / 1e6, 2)} MB")


if __name__ == "__main__":
    main()
