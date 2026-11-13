"""Clean data/Data_Centers_Database.csv -> data/clean/datacenters.csv (one row per facility, joined to county GEOID)."""
import re

import numpy as np
import pandas as pd

from common import CLEAN, RAW, ROOT, locate_counties, norm_county, num

SRC = ROOT / "data" / "Data_Centers_Database.csv"

STATUS_GROUP = {
    "Operating": "operating",
    "Expanding": "operating",  # already running, adding capacity
    "Approved/Permitted/Under construction": "pipeline",
    "Proposed": "pipeline",
    "Pre-proposal": "pipeline",
    "Suspended": "stalled",
    "Cancelled": "cancelled",
}


def parse_mw(s):
    """Return (low, high, point). Ranges use the midpoint as the point estimate; missing stays missing."""
    if pd.isna(s):
        return (np.nan, np.nan, np.nan)
    t = str(s).replace(",", "").replace("?", "").strip()
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
    if not nums:
        return (np.nan, np.nan, np.nan)
    lo, hi = min(nums), max(nums)
    return (lo, hi, (lo + hi) / 2)


def parse_cost_musd(s):
    """Parse '$14.5 billion', '$2-3 billion', '5.7 million' to USD millions. Bare numbers have no unit -> missing."""
    if pd.isna(s):
        return np.nan
    t = str(s).lower().replace(",", "")
    m = re.search(r"(billion|million)", t)
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
    if not m or not nums:
        return np.nan
    return float(np.mean(nums[:2])) * (1000 if m.group(1) == "billion" else 1)


def parse_sqft(s):
    if pd.isna(s):
        return np.nan
    t = str(s).lower().replace(",", "").strip()
    m = re.match(r"([\d.]+)\s*(m|million)?", t)
    if not m:
        return np.nan
    v = float(m.group(1))
    return v * 1_000_000 if m.group(2) else v


YEAR_FIX = {"20027": 2027}


def parse_year(s):
    if pd.isna(s):
        return np.nan
    t = str(s).strip()
    if t in YEAR_FIX:
        return YEAR_FIX[t]
    ys = re.findall(r"\b(20[2-4]\d)\b", t)
    return float(ys[0]) if ys else np.nan


def purpose_group(s):
    if pd.isna(s):
        return np.nan
    t = str(s).lower()
    ai = bool(re.search(r"\bai\b|artificial|\bia\b|hpc|high-performance|high performance", t))
    crypto = bool(re.search(r"crypto|bitcoin", t))
    if ai and crypto:
        return "AI + crypto"
    if ai:
        return "AI"
    if crypto:
        return "Crypto"
    return "Cloud/colocation/other"


def yes_no(s):
    """'Yes' / anything starting with yes -> True; 'No' -> False; otherwise unknown."""
    if pd.isna(s):
        return pd.NA
    t = str(s).strip().lower()
    if t.startswith("yes"):
        return True
    if t.startswith("no"):
        return False
    return pd.NA


def main():
    d = pd.read_csv(SRC, dtype=str, encoding="utf-8-sig")
    d = d.rename(columns={"long": "lon", "facility_size_sqft": "size_sqft", "property_size_acres": "acres"})
    out = pd.DataFrame({"facility_id": [f"dc{i:04d}" for i in range(len(d))]})

    for c in ["facility_name", "address", "city", "state", "zip", "county", "operator_name", "tenant"]:
        out[c] = d[c].str.strip().replace({"": np.nan})
    out["state"] = out["state"].str.upper()
    out["zip"] = out["zip"].str.extract(r"(\d{5})")[0]
    out["lat"] = num(d["lat"])
    out["lon"] = num(d["lon"])

    out["status"] = d["status"].str.strip()
    out["status_group"] = out["status"].map(STATUS_GROUP)
    out["location_confidence"] = d["location_confidence"].str.strip().str.title()

    mw = d["mw"].map(parse_mw)
    out["mw_low"] = [x[0] for x in mw]
    out["mw_high"] = [x[1] for x in mw]
    out["mw"] = [x[2] for x in mw]
    out["mw_is_range"] = out["mw_low"] != out["mw_high"]
    out.loc[out["mw"].isna(), "mw_is_range"] = False
    out["size_class"] = d["sizerank"].str.title().str.replace(r"\(.*\)", "", regex=True).str.strip().replace({"Unknown": np.nan})
    out["size_class"] = out["size_class"].str.replace("Mega Campus", "Mega campus")

    out["purpose_raw"] = d["purpose"].str.replace("\n", " ", regex=False)
    out["purpose_group"] = d["purpose"].map(purpose_group)
    out["power_source"] = d["power_source"].str.replace("Natural Gas", "Natural gas").str.replace("solar", "Solar")
    out["dedicated_power_plant"] = d["dedicated_power_plant"].map(yes_no)
    out["cooling_source"] = d["cooling_source"]
    out["cooling_type"] = d["cooling_type"].str.capitalize().replace({"Closed loop": "Closed loop", "Open loop": "Open loop"})

    out["size_sqft"] = d["size_sqft"].map(parse_sqft)
    out["acres"] = num(d["acres"])
    out["project_cost_musd"] = d["project_cost"].map(parse_cost_musd)
    out["expected_online_year"] = d["expected_date_online"].map(parse_year)

    # Pushback: the source marks "Unknown" for most rows, which means "no evidence found", not "no pushback".
    pb = d["community_pushback"].str.strip().str.lower()
    out["pushback_documented"] = pb.eq("yes")
    out["resistance_status"] = d["resistance_status"].replace({"Unknown": np.nan})
    out["advocacy_info"] = d["advocacy_information"]
    out["nda_reported"] = d["nda"].map(yes_no).where(d["nda"].notna(), pd.NA)
    out["n_community_sites"] = d[["community_group_website_1", "community_group_website_2", "petition_url"]].notna().sum(axis=1)
    out["information_source"] = d["information_source"]
    src_cols = [f"info_source_{i}" for i in range(1, 9)]
    out["n_sources"] = d[src_cols].apply(lambda r: sum(isinstance(v, str) and v.startswith("http") for v in r), axis=1)
    out["first_source_url"] = d["info_source_1"].where(d["info_source_1"].fillna("").str.startswith("http"))
    out["date_created"] = pd.to_datetime(d["date_created"], format="%m/%d/%Y", errors="coerce")
    out["date_updated"] = pd.to_datetime(d["date_updated"], format="%m/%d/%Y", errors="coerce")

    # Coordinates must sit inside the US footprint (incl. AK/HI).
    out["coord_ok"] = out["lat"].between(18, 72) & out["lon"].between(-170, -66)

    # County assignment. Two independent signals:
    #   name:    state + county name from the CSV (typos, wrong counties, and independent cities collapse into counties)
    #   spatial: point-in-polygon on the Census county boundaries (also covers Connecticut's planning regions)
    # Spatial wins, except for Low-confidence coordinates where a name match exists. Points that fall in water
    # (San Francisco Bay, Maine coast) have no polygon and use the name match.
    ref = pd.read_csv(CLEAN / "counties.csv", dtype={"geoid": str})
    keys = ref[["geoid", "state", "name_key"]].drop_duplicates(["state", "name_key"])
    out["name_key"] = out["county"].map(lambda x: norm_county(x) if isinstance(x, str) else np.nan)
    out = out.merge(keys, on=["state", "name_key"], how="left").rename(columns={"geoid": "geoid_name"})
    miss = out["geoid_name"].isna() & out["name_key"].notna()
    retry = out.loc[miss, ["state", "name_key"]].assign(name_key=lambda x: x["name_key"] + "city")
    out.loc[miss, "geoid_name"] = retry.merge(keys, on=["state", "name_key"], how="left")["geoid"].values

    shp = RAW / "census_cb/county_500k"
    out["geoid_spatial"] = locate_counties(out["lon"].values, out["lat"].values,
                                           shp / "cb_2025_us_county_500k.shp", shp / "cb_2025_us_county_500k.dbf")
    use_name = out["geoid_spatial"].isna() | ((out["location_confidence"] == "Low") & out["geoid_name"].notna())
    out["county_geoid"] = np.where(use_name, out["geoid_name"], out["geoid_spatial"])
    out["county_source"] = np.where(out["county_geoid"].isna(), "unmatched", np.where(use_name, "name", "spatial"))
    out["county_conflict"] = out["geoid_name"].notna() & out["county_geoid"].notna() & (out["geoid_name"] != out["county_geoid"])

    # State: the CSV label is kept, but corrected when coordinates place the facility in another state.
    state_of = ref.drop_duplicates("geoid").set_index("geoid")["state"]
    out["state_csv"] = out["state"]
    geo_state = out["county_geoid"].map(state_of)
    out["state_corrected"] = geo_state.notna() & (geo_state != out["state"])
    out["state"] = geo_state.where(out["state_corrected"], out["state"])
    out["county_clean"] = out["county_geoid"].map(ref.drop_duplicates("geoid").set_index("geoid")["county_name"])
    out["dup_coords"] = out.duplicated(["lat", "lon"], keep=False)

    out = out.drop(columns=["name_key", "geoid_name", "geoid_spatial"])
    out.to_csv(CLEAN / "datacenters.csv", index=False)

    print(f"datacenters.csv: {len(out)} rows")
    print("status_group:", out["status_group"].value_counts().to_dict())
    print("county_source:", out["county_source"].value_counts().to_dict(), "| conflicts resolved:", out["county_conflict"].sum(),
          "| state corrected:", out["state_corrected"].sum())
    print("coord_ok false:", (~out["coord_ok"]).sum())
    print("mw present:", out["mw"].notna().sum(), "ranges:", out["mw_is_range"].sum(), "| cost parsed:", out["project_cost_musd"].notna().sum(),
          "| year parsed:", out["expected_online_year"].notna().sum(), "| sqft parsed:", out["size_sqft"].notna().sum())
    print("pushback_documented:", out["pushback_documented"].sum())


if __name__ == "__main__":
    main()
