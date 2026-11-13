"""Place each data center in its WRI Aqueduct basin and build a population baseline by basin stress level.

Outputs: data/clean/datacenters_basin.csv   facility_id -> basin id, stress category/label/score (point-in-polygon)
         data/clean/basin_population.csv    US population and land area by baseline stress level (county pop split by overlap area)
Needs geopandas (.pylibs).
"""
import glob
import sys

from common import CLEAN, RAW, ROOT

sys.path.insert(0, str(ROOT / ".pylibs"))
import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402

CRS = "EPSG:5070"
SNAP_M = 10_000  # points in coastal water or on a basin edge snap to the nearest basin within 10 km


def group(cat, label):
    if label == "No Data":
        return "No data"
    if label == "Arid and Low Water Use":
        return "Arid, low use"
    return {0: "Low", 1: "Low-medium", 2: "Medium-high", 3: "High", 4: "Extremely high"}.get(cat, "No data")


def main():
    gdb = glob.glob(str(RAW / "aqueduct40/**/*.gdb"), recursive=True)[0]
    ids = gpd.read_file(gdb, layer="baseline_annual", columns=["gid_0"], ignore_geometry=True)
    us = ids.index[ids["gid_0"].str.strip().eq("USA")].tolist()
    b = gpd.read_file(gdb, layer="baseline_annual", columns=["pfaf_id", "name_1", "bws_cat", "bws_label", "bws_score", "area_km2"], fids=us)
    b["stress_group"] = [group(c, l) for c, l in zip(b["bws_cat"], b["bws_label"])]
    b["basin_id"] = b["pfaf_id"].astype(str) + "|" + b["name_1"]
    b = b.to_crs(CRS)
    b["geometry"] = b.geometry.make_valid()

    d = pd.read_csv(CLEAN / "datacenters.csv")
    d = d[d.coord_ok].copy()
    pts = gpd.GeoDataFrame(d[["facility_id"]], geometry=gpd.points_from_xy(d["lon"], d["lat"]), crs="EPSG:4326").to_crs(CRS)
    cols = ["basin_id", "name_1", "bws_cat", "bws_label", "bws_score", "stress_group", "geometry"]
    j = gpd.sjoin(pts, b[cols], how="left", predicate="within").drop_duplicates("facility_id")
    miss = j["basin_id"].isna()
    if miss.any():
        near = gpd.sjoin_nearest(pts[pts.facility_id.isin(j.loc[miss, "facility_id"])], b[cols], how="left", max_distance=SNAP_M).drop_duplicates("facility_id")
        j = pd.concat([j[~miss], near])
    j["matched_by"] = ["within" if f not in set(near["facility_id"]) else "nearest<=10km" for f in j["facility_id"]] if miss.any() else "within"
    out = j[["facility_id", "basin_id", "name_1", "bws_cat", "bws_label", "bws_score", "stress_group", "matched_by"]].rename(columns={"name_1": "basin_state"})
    out = d[["facility_id"]].merge(out, on="facility_id", how="left")
    out.to_csv(CLEAN / "datacenters_basin.csv", index=False)
    print(f"{len(out)} facilities; matched {int(out.basin_id.notna().sum())} ({out.matched_by.value_counts().to_dict()}); no basin: {int(out.basin_id.isna().sum())}")
    print(out.stress_group.value_counts(dropna=False).to_dict())

    # Baseline: split each county's 2025 population across basins by area overlap.
    c = gpd.read_file(RAW / "census_cb/county_5m/cb_2025_us_county_5m.shp")[["GEOID", "STATEFP", "geometry"]]
    c = c[c["STATEFP"] <= "56"].to_crs(CRS)
    pop = pd.read_csv(CLEAN / "counties.csv", dtype={"geoid": str}).set_index("geoid")["pop_2025"]
    x = gpd.overlay(c, b[["basin_id", "stress_group", "geometry"]], how="intersection", keep_geom_type=False)
    x["a"] = x.geometry.area
    x["pop"] = x["GEOID"].map(pop) * x["a"] / x.groupby("GEOID")["a"].transform("sum")
    base = x.groupby("stress_group").agg(population=("pop", "sum"), land_km2=("a", lambda s: s.sum() / 1e6)).reset_index()
    base["population_share"] = base["population"] / base["population"].sum()
    base["land_share"] = base["land_km2"] / base["land_km2"].sum()
    base.to_csv(CLEAN / "basin_population.csv", index=False)
    print(base.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
