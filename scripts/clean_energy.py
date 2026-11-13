"""Clean EIA-861 (utility sales, service territories, balancing authorities) and BLS CPI.

Inputs:  data/interim/eia861_csv/<year>/*.csv  (converted from the EIA .xlsx files with LibreOffice)
         data/raw/cpi/bls_CUUR0000SA0_2018_2025.json
Outputs: data/clean/cpi_annual.csv
         data/clean/eia861_utility_sales.csv      one row per utility x state x part x year
         data/clean/eia861_state_residential.csv  state x year residential price / bill (EIA's method)
         data/clean/eia861_utility_counties.csv   utility x county x year, with county GEOID
         data/clean/eia861_ba_codes.csv           balancing authority code -> name
"""
import json

import numpy as np
import pandas as pd

from common import CLEAN, INTERIM, RAW, norm_county, num

YEARS = range(2018, 2026)
SECTORS = ["res", "com", "ind", "trans", "total"]
PART_NAME = {"A": "bundled", "B": "energy_only", "C": "delivery_only", "D": "behind_the_meter"}


def cpi():
    d = json.load(open(RAW / "cpi/bls_CUUR0000SA0_2018_2025.json"))
    rows = [(int(x["year"]), float(x["value"])) for x in d["Results"]["series"][0]["data"] if x["value"] != "-"]
    m = pd.DataFrame(rows, columns=["year", "cpi"])
    a = m.groupby("year").agg(cpi_u=("cpi", "mean"), months=("cpi", "size")).reset_index()
    a["deflator_to_2025"] = a.loc[a.year == 2025, "cpi_u"].iloc[0] / a["cpi_u"]
    return a


def read_sales(year):
    raw = pd.read_csv(INTERIM / f"eia861_csv/{year}/Sales_Ult_Cust_{year}.csv", header=None, dtype=str)
    hdr = [str(h).replace("\n", " ") for h in raw.iloc[2]]
    body = raw.iloc[3:].reset_index(drop=True)
    col = {name: i for i, name in enumerate(hdr)}
    first_val = hdr.index("Thousand Dollars")  # 2019 has an extra "Short Form" column before this
    out = pd.DataFrame({
        "year": num(body[col["Data Year"]]),
        "utility_id": num(body[col["Utility Number"]]),
        "utility_name": body[col["Utility Name"]].str.strip(),
        "part": body[col["Part"]].str.strip(),
        "state": body[col["State"]].str.strip(),
        "ownership": body[col["Ownership"]].str.strip(),
        "ba_code": body[col["BA Code"]].str.strip(),
        "imputed": body[col["Data Type O = Observed I = Imputed"]].str.strip().eq("I")
        if "Data Type O = Observed I = Imputed" in col else body[5].str.strip().eq("I"),
    })
    for k, sec in enumerate(SECTORS):
        i = first_val + 3 * k
        out[f"{sec}_revenue_kusd"] = num(body[i])
        out[f"{sec}_mwh"] = num(body[i + 1])
        out[f"{sec}_customers"] = num(body[i + 2])
    out = out[out["part"].isin(PART_NAME) & out["year"].notna() & out["utility_id"].notna()].copy()
    out["year"] = out["year"].astype(int)
    out["utility_id"] = out["utility_id"].astype(int)
    out["part_name"] = out["part"].map(PART_NAME)
    return out


def utility_sales():
    s = pd.concat([read_sales(y) for y in YEARS], ignore_index=True)
    s = s.merge(cpi()[["year", "deflator_to_2025"]], on="year", how="left")
    r_rev, r_mwh, r_cust = s["res_revenue_kusd"], s["res_mwh"], s["res_customers"]
    # Price in cents/kWh = (thousand $ * 1000 * 100) / (MWh * 1000) = kusd / MWh * 100.
    s["res_price_cents_kwh"] = np.where(r_mwh > 0, r_rev / r_mwh * 100, np.nan)
    s["res_bill_usd_month"] = np.where(r_cust > 0, r_rev * 1000 / r_cust / 12, np.nan)
    s["res_kwh_per_customer_month"] = np.where(r_cust > 0, r_mwh * 1000 / r_cust / 12, np.nan)
    s["res_price_cents_kwh_real2025"] = s["res_price_cents_kwh"] * s["deflator_to_2025"]
    s["res_bill_usd_month_real2025"] = s["res_bill_usd_month"] * s["deflator_to_2025"]
    s = s.drop(columns="deflator_to_2025")
    # Prices are only comparable for bundled utilities; energy-only and delivery-only rows are each one slice of a bill.
    s["price_comparable"] = s["part"].eq("A") & (r_mwh > 0) & (r_rev > 0)
    return s


def state_residential(s):
    """EIA's method: revenue = bundled + energy-only + delivery-only; sales & customers = bundled + energy-only.

    Delivery-only rows would double count kWh and customers that the energy-only rows already carry.
    """
    s = s[s["part"].isin(["A", "B", "C"])].copy()
    s["rev"] = s["res_revenue_kusd"]
    s["mwh"] = np.where(s["part"].isin(["A", "B"]), s["res_mwh"], 0.0)
    s["cust"] = np.where(s["part"].isin(["A", "B"]), s["res_customers"], 0.0)
    g = s.groupby(["state", "year"]).agg(rev=("rev", "sum"), mwh=("mwh", "sum"), cust=("cust", "sum"),
                                         n_utilities=("utility_id", "nunique")).reset_index()
    g = g.merge(cpi()[["year", "deflator_to_2025"]], on="year")
    g["res_price_cents_kwh"] = g["rev"] / g["mwh"] * 100
    g["res_bill_usd_month"] = g["rev"] * 1000 / g["cust"] / 12
    g["res_kwh_per_customer_month"] = g["mwh"] * 1000 / g["cust"] / 12
    g["res_price_cents_kwh_real2025"] = g["res_price_cents_kwh"] * g["deflator_to_2025"]
    g["res_bill_usd_month_real2025"] = g["res_bill_usd_month"] * g["deflator_to_2025"]
    g = g.rename(columns={"rev": "res_revenue_kusd", "mwh": "res_mwh", "cust": "res_customers"}).drop(columns="deflator_to_2025")
    return g


def territories():
    ref = pd.read_csv(CLEAN / "counties.csv", dtype={"geoid": str})
    keys = ref[["geoid", "state", "name_key"]].drop_duplicates(["state", "name_key"])
    frames = []
    for y in YEARS:
        t = pd.read_csv(INTERIM / f"eia861_csv/{y}/Service_Territory_{y}.csv", dtype=str)
        t = t.rename(columns={"Data Year": "year", "Utility Number": "utility_id", "Utility Name": "utility_name",
                              "State": "state", "County": "county"})
        t["year"] = int(y)
        frames.append(t[["year", "utility_id", "utility_name", "state", "county"]])
    t = pd.concat(frames, ignore_index=True).dropna(subset=["utility_id", "county"])
    t["utility_id"] = t["utility_id"].astype(int)
    t["name_key"] = [norm_county(c, st) for c, st in zip(t["county"], t["state"])]
    t = t.merge(keys, on=["state", "name_key"], how="left").rename(columns={"geoid": "county_geoid"})
    # Independent cities (VA, MD, MO, NV) are sometimes listed bare; retry with " city".
    miss = t["county_geoid"].isna()
    retry = t.loc[miss, ["state", "name_key"]].assign(name_key=lambda x: x["name_key"] + "city")
    t.loc[miss, "county_geoid"] = retry.merge(keys, on=["state", "name_key"], how="left")["geoid"].values
    return t.drop(columns="name_key")


def ba_codes():
    frames = []
    for y in YEARS:
        b = pd.read_csv(INTERIM / f"eia861_csv/{y}/Balancing_Authority_{y}.csv", dtype=str)
        b["year"] = int(y)
        frames.append(b)
    b = pd.concat(frames)
    b = b.rename(columns={"BA ID": "ba_id", "BA Code": "ba_code", "Balancing Authority Name": "ba_name"})
    return b.sort_values("year").drop_duplicates("ba_code", keep="last")[["ba_code", "ba_id", "ba_name"]]


def main():
    c = cpi()
    c.to_csv(CLEAN / "cpi_annual.csv", index=False)
    s = utility_sales()
    s.to_csv(CLEAN / "eia861_utility_sales.csv", index=False)
    st = state_residential(s)
    st.to_csv(CLEAN / "eia861_state_residential.csv", index=False)
    t = territories()
    t.to_csv(CLEAN / "eia861_utility_counties.csv", index=False)
    ba_codes().to_csv(CLEAN / "eia861_ba_codes.csv", index=False)

    print("cpi:", c.round(3).to_dict("records")[-2:])
    print(f"utility_sales: {len(s)} rows; parts: {s.part_name.value_counts().to_dict()}; years: {sorted(s.year.unique())}")
    tot = st.groupby("year")[["res_revenue_kusd", "res_mwh", "res_customers"]].sum()
    us = pd.DataFrame({"price": tot.res_revenue_kusd / tot.res_mwh * 100, "bill": tot.res_revenue_kusd * 1000 / tot.res_customers / 12})
    print("US residential avg (nominal) by year:\n", us.round(2).T.to_string())
    print("states per year:", st.groupby("year").state.nunique().to_dict())
    print("territories:", len(t), "| county matched:", t.county_geoid.notna().sum(), "| unmatched:", t.county_geoid.isna().sum())
    print(t[t.county_geoid.isna()][["state", "county"]].value_counts().head(15).to_string())


if __name__ == "__main__":
    main()
