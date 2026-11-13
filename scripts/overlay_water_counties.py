"""Overlay WRI Aqueduct 4.0 baseline basins on Census counties -> data/clean/aqueduct_county.csv.

Needs geopandas (installed into .pylibs/ from public PyPI; see requirements.txt).
Each county gets area-weighted shares of its area in each baseline water stress level.
"""
import glob
import sys

from common import CLEAN, RAW, ROOT

sys.path.insert(0, str(ROOT / ".pylibs"))
import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

CRS = "EPSG:5070"  # CONUS Albers equal area; Alaska/Hawaii are distorted but shares stay usable


def main():
    gdb = glob.glob(str(RAW / "aqueduct40/**/*.gdb"), recursive=True)[0]
    # The SQL `where` filter returns nothing on this FileGDB, so pick US rows by position first.
    ids = gpd.read_file(gdb, layer="baseline_annual", columns=["gid_0"], ignore_geometry=True)
    us = ids.index[ids["gid_0"].str.strip().eq("USA")].tolist()
    b = gpd.read_file(gdb, layer="baseline_annual", columns=["pfaf_id", "gid_1", "bws_cat", "bws_label", "bws_score"], fids=us)
    b["bws_cat"] = b["bws_cat"].where(b["bws_cat"] > -9000)
    b["no_data"] = b["bws_label"].eq("No Data")
    b["arid"] = b["bws_label"].eq("Arid and Low Water Use")
    b = b.to_crs(CRS)
    b["geometry"] = b.geometry.make_valid()

    shp = RAW / "census_cb/county_5m/cb_2025_us_county_5m.shp"
    c = gpd.read_file(shp)[["GEOID", "STATEFP", "geometry"]]
    c = c[c["STATEFP"] <= "56"].to_crs(CRS)
    c["county_area"] = c.geometry.area

    x = gpd.overlay(c, b[["pfaf_id", "bws_cat", "bws_score", "no_data", "arid", "geometry"]], how="intersection", keep_geom_type=False)
    x["a"] = x.geometry.area
    rows = []
    for geoid, g in x.groupby("GEOID"):
        tot = g["a"].sum()
        valid = g[~g["no_data"] & ~g["arid"] & g["bws_cat"].notna()]
        va = valid["a"].sum()
        r = {"county_geoid": geoid, "basin_overlap_share": tot / c.loc[c.GEOID == geoid, "county_area"].iloc[0],
             "share_no_data": g.loc[g["no_data"], "a"].sum() / tot, "share_arid_low_use": g.loc[g["arid"], "a"].sum() / tot,
             "n_basins": g["pfaf_id"].nunique()}
        for lvl, name in enumerate(["low", "low_medium", "medium_high", "high", "extreme"]):
            r[f"share_{name}"] = g.loc[g["bws_cat"] == lvl, "a"].sum() / tot
        r["share_high_or_extreme"] = r["share_high"] + r["share_extreme"]
        r["mean_bws_score"] = np.average(valid["bws_score"], weights=valid["a"]) if va > 0 else np.nan
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(CLEAN / "aqueduct_county.csv", index=False)
    print(f"aqueduct_county: {len(out)} counties of {len(c)}; low basin overlap (<0.9): {int((out.basin_overlap_share < 0.9).sum())}")
    print(out[["share_high_or_extreme", "share_arid_low_use", "share_no_data", "mean_bws_score"]].describe().round(2).to_string())


if __name__ == "__main__":
    main()
