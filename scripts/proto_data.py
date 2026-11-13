"""Analysis tables shared by the prototype notebooks (all built from data/clean/).

Run notebooks with PYTHONPATH=.pylibs (see requirements.txt); this module only needs pandas/numpy.
"""
import numpy as np
import pandas as pd

from common import CLEAN

BASE_YEAR, END_YEAR = 2019, 2025


def _read(name, **kw):
    return pd.read_csv(CLEAN / name, **kw)


def county_frame():
    """County spine + data center aggregates + water stress + local policy."""
    c = _read("counties.csv", dtype={"geoid": str}).drop(columns="name_key")
    d = _read("datacenters.csv", dtype={"county_geoid": str})
    g = d.groupby("county_geoid")
    agg = pd.DataFrame({
        "dc_operating": d[d.status_group == "operating"].groupby("county_geoid").size(),
        "dc_operating_mw": d[d.status_group == "operating"].groupby("county_geoid")["mw"].sum(),
        "dc_pipeline": d[d.status_group == "pipeline"].groupby("county_geoid").size(),
        "dc_pipeline_mw": d[d.status_group == "pipeline"].groupby("county_geoid")["mw"].sum(),
        "dc_pushback_documented": g["pushback_documented"].sum(),
    }).fillna(0)
    c = c.merge(agg, left_on="geoid", right_index=True, how="left").fillna({k: 0 for k in agg.columns})
    w = _read("aqueduct_county.csv", dtype={"county_geoid": str})
    c = c.merge(w, left_on="geoid", right_on="county_geoid", how="left").drop(columns="county_geoid")
    p = _read("policy_county_summary.csv", dtype={"county_geoid": str})
    c = c.merge(p, left_on="geoid", right_on="county_geoid", how="left").drop(columns="county_geoid")
    for k in ("n_actions", "n_restrictive_in_force"):
        c[k] = c[k].fillna(0)
    c["any_restriction_in_force"] = c["any_restriction_in_force"].fillna(False).astype(bool)
    c["dc_operating_mw_per_1k_pop"] = c["dc_operating_mw"] / c["pop_2025"] * 1000
    return c


def utility_price_table(min_customers=1000):
    """One row per bundled utility x state with real residential price change and data center exposure.

    Exposure = number of operating data centers in counties the utility serves (2025 territories).
    A utility serves whole counties only roughly, so exposure is an upper bound on what its customers share.
    """
    d = _read("datacenters.csv", dtype={"county_geoid": str})
    op = d[d.status_group == "operating"].groupby("county_geoid").size().rename("n_op")
    t = _read("eia861_utility_counties.csv", dtype={"county_geoid": str}).query(f"year=={END_YEAR}")
    t = t.merge(op, left_on="county_geoid", right_index=True, how="left").fillna({"n_op": 0})
    ex = t.groupby(["utility_id", "state"]).agg(n_counties=("county_geoid", "size"), dc_operating=("n_op", "sum")).reset_index()
    u = _read("eia861_utility_sales.csv").query("price_comparable and not imputed")
    w = u.pivot_table(index=["utility_id", "state"], columns="year", values="res_price_cents_kwh_real2025").reset_index()
    w = w.dropna(subset=[BASE_YEAR, END_YEAR])
    w["price_change_pct"] = (w[END_YEAR] / w[BASE_YEAR] - 1) * 100
    name = u.drop_duplicates(["utility_id", "state"], keep="last").set_index(["utility_id", "state"])[["utility_name", "ba_code"]]
    cust = u[u.year == END_YEAR].groupby(["utility_id", "state"])["res_customers"].sum().rename("customers")
    w = w.merge(name, on=["utility_id", "state"]).merge(cust, on=["utility_id", "state"]).merge(ex, on=["utility_id", "state"], how="left")
    w = w.dropna(subset=["dc_operating"])
    w = w[w["customers"] >= min_customers]
    w = w[w["price_change_pct"].between(-50, 100)]  # drops a handful of data-entry outliers
    w["exposed"] = (w["dc_operating"] > 0).astype(int)
    w["log_customers"] = np.log(w["customers"])
    return w.rename(columns={BASE_YEAR: f"price_{BASE_YEAR}", END_YEAR: f"price_{END_YEAR}"})


def ba_grid_table():
    """Balancing authority peak-demand growth vs data center exposure (operating facilities in served counties)."""
    a = _read("eia930_ba_annual.csv").query("complete_year and not peak_suspect")
    pk = a.pivot(index="ba", columns="year", values="peak_mw")
    pk = pk[[BASE_YEAR, END_YEAR]].dropna()
    out = pd.DataFrame({"peak_base_mw": pk[BASE_YEAR], "peak_end_mw": pk[END_YEAR]})
    out["peak_growth_pct"] = (out["peak_end_mw"] / out["peak_base_mw"] - 1) * 100
    out["mean_mw_end"] = a[a.year == END_YEAR].set_index("ba")["mean_mw"]
    u = _read("eia861_utility_sales.csv").query(f"year=={END_YEAR}")[["utility_id", "state", "ba_code"]].drop_duplicates()
    t = _read("eia861_utility_counties.csv", dtype={"county_geoid": str}).query(f"year=={END_YEAR}")
    t = t.merge(u, on=["utility_id", "state"]).dropna(subset=["ba_code", "county_geoid"])
    d = _read("datacenters.csv", dtype={"county_geoid": str})
    d = d[d.status_group == "operating"]
    cnt = d.groupby("county_geoid").agg(n=("facility_id", "size"), mw=("mw", "sum"))
    ba_c = t.drop_duplicates(["ba_code", "county_geoid"]).merge(cnt, left_on="county_geoid", right_index=True, how="left").fillna({"n": 0, "mw": 0})
    e = ba_c.groupby("ba_code").agg(dc_operating=("n", "sum"), dc_operating_mw=("mw", "sum"), n_counties=("county_geoid", "size"))
    out = out.join(e, how="inner")
    out["dc_per_gw_demand"] = out["dc_operating"] / (out["mean_mw_end"] / 1000)
    return out.reset_index().rename(columns={"index": "ba"})


def county_price_change():
    """Customer-weighted mean real residential price change (2019-2025) of bundled utilities serving each county.

    Approximate: EIA-861 lists which counties a utility serves, not how many customers it has in each.
    """
    w = utility_price_table(min_customers=1000)[["utility_id", "state", "price_change_pct", "customers"]]
    t = _read("eia861_utility_counties.csv", dtype={"county_geoid": str}).query(f"year=={END_YEAR}")
    t = t.dropna(subset=["county_geoid"]).drop_duplicates(["utility_id", "state", "county_geoid"]).merge(w, on=["utility_id", "state"])
    t["wp"] = t["price_change_pct"] * t["customers"]
    g = t.groupby("county_geoid").agg(wp=("wp", "sum"), cust=("customers", "sum"), n_utilities=("utility_id", "nunique"))
    return (g["wp"] / g["cust"]).rename("price_change_pct").reset_index()
