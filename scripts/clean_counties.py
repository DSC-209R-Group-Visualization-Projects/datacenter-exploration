"""Build the county reference table (GEOID spine) and attach controls: RUCC, population, income, home value."""
import pandas as pd

from common import CLEAN, RAW, STATE_FIPS_MAX, norm_county, num, read_dbf


def counties():
    d = read_dbf(RAW / "census_cb/county_5m/cb_2025_us_county_5m.dbf")
    d = d[d["STATEFP"] <= STATE_FIPS_MAX].copy()
    d = d.rename(columns={"GEOID": "geoid", "STUSPS": "state", "STATE_NAME": "state_name", "NAMELSAD": "county_name"})
    d["land_sqmi"] = num(d["ALAND"]) / 2_589_988.11
    d["name_key"] = d["county_name"].map(norm_county)
    return d[["geoid", "state", "state_name", "county_name", "name_key", "land_sqmi"]]


def rucc():
    r = pd.read_csv(RAW / "usda_rucc/2023-rural-urban-continuum-codes.csv", dtype=str, encoding="latin-1")
    r = r.pivot_table(index="FIPS", columns="Attribute", values="Value", aggfunc="first").reset_index()
    out = pd.DataFrame({"geoid": r["FIPS"], "rucc_2023": num(r["RUCC_2023"]).astype("Int64")})
    return out


def pep():
    p = pd.read_csv(RAW / "census_pep/co-est2025-alldata.csv", dtype=str, encoding="latin-1")
    p = p[p["SUMLEV"] == "050"].copy()
    p["geoid"] = p["STATE"].str.zfill(2) + p["COUNTY"].str.zfill(3)
    out = p[["geoid"]].copy()
    for y in range(2020, 2026):
        out[f"pop_{y}"] = num(p[f"POPESTIMATE{y}"])
    out["pop_growth_2020_2025_pct"] = (out["pop_2025"] / out["pop_2020"] - 1) * 100
    return out


def acs(table, col, name):
    a = pd.read_csv(RAW / f"acs/acsdt5y2024-{table}.dat", sep="|", dtype=str)
    a = a[a["GEO_ID"].str.startswith("0500000US")].copy()
    a["geoid"] = a["GEO_ID"].str[-5:]
    # ACS uses negative sentinel codes (e.g. -666666666) for suppressed estimates.
    v = num(a[col])
    v = v.where(v > 0)
    return pd.DataFrame({"geoid": a["geoid"], name: v})


def main():
    c = counties()
    for part in (rucc(), pep(), acs("b01003", "B01003_E001", "pop_acs_2024"),
                 acs("b19013", "B19013_E001", "median_hh_income_2024"),
                 acs("b25077", "B25077_E001", "median_home_value_2024")):
        c = c.merge(part, on="geoid", how="left")
    c["pop_density_per_sqmi"] = c["pop_2025"] / c["land_sqmi"]
    c.to_csv(CLEAN / "counties.csv", index=False)
    print(f"counties.csv: {len(c)} rows")
    print(c.drop(columns=["name_key"]).isna().sum()[lambda s: s > 0].to_string())
    print("missing in some control:", c[c[["rucc_2023", "pop_2025", "median_hh_income_2024"]].isna().any(axis=1)][["geoid", "county_name"]].head(12).to_string())


if __name__ == "__main__":
    main()
