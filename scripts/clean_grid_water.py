"""Clean grid strain (EIA-930 hourly demand, PJM capacity auctions) and water stress (WRI Aqueduct 4.0).

Outputs: data/clean/eia930_ba_annual.csv     balancing authority x year demand statistics
         data/clean/pjm_bra_rto_prices.csv   PJM capacity auction prices by delivery year
         data/clean/aqueduct_us_basins.csv   US basin-in-state rows with baseline and future water stress
         data/clean/aqueduct_state_summary.csv  area-weighted stress shares per state
"""
import calendar
import shutil

import numpy as np
import pandas as pd

from common import CLEAN, RAW

AQ = RAW / "aqueduct40/extracted/Aqueduct40_waterrisk_download_Y2023M07D05/CVS"


def eia930():
    want = {"Balancing Authority", "Data Date", "Hour Number", "Demand (MW)", "Demand (MW) (Adjusted)", "Region"}
    frames = []
    for f in sorted((RAW / "eia930").glob("EIA930_BALANCE_*.csv")):
        d = pd.read_csv(f, usecols=lambda c: c in want, dtype=str)
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d = d.rename(columns={"Balancing Authority": "ba", "Data Date": "date", "Hour Number": "hour",
                          "Demand (MW)": "demand_raw", "Demand (MW) (Adjusted)": "demand_adj", "Region": "region"})
    n0 = len(d)
    d = d.drop_duplicates(["ba", "date", "hour"], keep="last")
    d["date"] = pd.to_datetime(d["date"], format="%m/%d/%Y")
    for c in ("demand_raw", "demand_adj"):
        d[c] = pd.to_numeric(d[c].str.replace(",", ""), errors="coerce")
    # EIA's adjusted series fills gaps and fixes obvious errors; fall back to the raw value where it is blank.
    d["demand"] = d["demand_adj"].fillna(d["demand_raw"])
    d.loc[d["demand"] <= 0, "demand"] = np.nan
    # Reporting glitches show up as isolated hours far from their neighbors (e.g. PJM at 224 GW against a ~85 GW norm).
    # Compare each hour with the centered 7-hour rolling median of the same balancing authority.
    d = d.sort_values(["ba", "date", "hour"], key=lambda c: c if c.name != "hour" else pd.to_numeric(c)).reset_index(drop=True)
    local = d.groupby("ba")["demand"].transform(lambda x: x.rolling(7, center=True, min_periods=3).median())
    # Require an absolute gap too, so tiny noisy authorities (SPA averages ~70 MW) are not clipped by percentages alone.
    spikes = ((d["demand"] > 1.25 * local) | (d["demand"] < 0.75 * local)) & ((d["demand"] - local).abs() > 100)
    d.loc[spikes, "demand"] = np.nan
    print(f"eia930: {n0} hourly rows ({n0 - len(d)} duplicates dropped), {int(spikes.sum())} glitch hours removed "
          f"({spikes.mean() * 100:.3f}%), {d['ba'].nunique()} balancing authorities")
    print("  most affected:", d.loc[spikes, "ba"].value_counts().head(5).to_dict())

    d["year"] = d["date"].dt.year
    d["summer"] = d["date"].dt.month.between(6, 9)
    rows = []
    for (ba, y), g in d.groupby(["ba", "year"]):
        if g["demand"].notna().sum() == 0:
            continue
        peak_i = g["demand"].idxmax()
        expected = 24 * (366 if calendar.isleap(y) else 365)
        n = int(g["demand"].notna().sum())
        rows.append({
            "ba": ba, "year": y, "region": g["region"].dropna().iloc[0] if g["region"].notna().any() else np.nan,
            "peak_mw": g["demand"].max(), "peak_date": g.loc[peak_i, "date"].date(),
            "summer_peak_mw": g.loc[g["summer"], "demand"].max(),
            "mean_mw": g["demand"].mean(), "hours_reported": n, "hours_expected": expected,
            "coverage": n / expected, "last_date": g["date"].max().date(),
            "total_gwh_scaled": g["demand"].mean() * expected / 1000,
        })
    a = pd.DataFrame(rows)
    # 2026 is partial (data through mid-November); flag it so analyses can exclude it.
    a["complete_year"] = (a["year"] < 2026) & (a["coverage"] >= 0.9)
    # Multi-hour glitches survive the spike filter (e.g. SEC 2021 at 2.5x its usual peak); flag instead of guessing.
    a["peak_suspect"] = a["peak_mw"] > 1.75 * a.groupby("ba")["peak_mw"].transform("median")
    return a


def pjm():
    p = pd.read_csv(RAW / "pjm_bra/pjm_bra_rto_prices.csv")
    p["delivery_year_start"] = p["delivery_year"].str[:4].astype(int)
    p["price_vs_prior_pct"] = p["rto_clearing_price_usd_per_mw_day"].pct_change() * 100
    return p


def aqueduct():
    cols = ["string_id", "pfaf_id", "gid_1", "name_1", "gid_0", "area_km2",
            "bws_raw", "bws_score", "bws_cat", "bws_label", "bwd_raw", "bwd_score", "bwd_label",
            "w_awr_def_tot_score", "w_awr_def_tot_label"]
    b = pd.read_csv(AQ / "Aqueduct40_baseline_annual_y2023m07d05.csv", usecols=cols)
    b = b[b["gid_0"] == "USA"].drop(columns="gid_0").copy()

    # Aqueduct codes "No Data" as -9999 and "Arid and Low Water Use" with category -1 (and the maximum score 5).
    for c in ("bws_score", "bws_cat", "bwd_score", "w_awr_def_tot_score"):
        b.loc[b[c] <= -9000, c] = np.nan
    b["no_data"] = b["bws_label"].eq("No Data")
    b["arid_low_use"] = b["bws_label"].eq("Arid and Low Water Use")
    b.loc[b["no_data"], ["bws_raw", "bwd_raw"]] = np.nan
    b["bws_level"] = b["bws_cat"].where(b["bws_cat"] >= 0)  # 0 Low .. 4 Extremely high; NaN for arid / no data
    b["bws_high"] = b["bws_level"] >= 3                     # High (40-80%) or Extremely high (>80%)

    f = pd.read_csv(AQ / "Aqueduct40_future_annual_y2023m07d05.csv",
                    usecols=["pfaf_id", "bau30_ws_x_r", "bau30_ws_x_l", "bau50_ws_x_r", "bau50_ws_x_l"])
    f = f.rename(columns={"bau30_ws_x_r": "bws_2030_bau_raw", "bau30_ws_x_l": "bws_2030_bau_label",
                          "bau50_ws_x_r": "bws_2050_bau_raw", "bau50_ws_x_l": "bws_2050_bau_label"})
    b = b.merge(f, on="pfaf_id", how="left")

    states = pd.read_csv(CLEAN / "counties.csv", usecols=["state", "state_name"]).drop_duplicates()
    b = b.merge(states, left_on="name_1", right_on="state_name", how="left").drop(columns="state_name")
    b = b.rename(columns={"name_1": "state_name"})
    return b


def aqueduct_state(b):
    g = b[~b["no_data"]].copy()
    g["w"] = g["area_km2"]
    rows = []
    for st, x in g.groupby("state"):
        tot = x["w"].sum()
        row = {"state": st, "area_km2": tot,
               "share_high_or_extreme": x.loc[x["bws_high"], "w"].sum() / tot,
               "share_arid_low_use": x.loc[x["arid_low_use"], "w"].sum() / tot}
        for lvl, name in enumerate(["low", "low_medium", "medium_high", "high", "extreme"]):
            row[f"share_{name}"] = x.loc[x["bws_level"] == lvl, "w"].sum() / tot
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    a = eia930()
    a.to_csv(CLEAN / "eia930_ba_annual.csv", index=False)
    print(f"eia930_ba_annual: {len(a)} rows; complete BA-years: {int(a.complete_year.sum())}")
    print(a[a.ba.isin(["PJM", "ERCO", "MISO", "DUK"])].pivot(index="ba", columns="year", values="peak_mw").round(0).to_string())

    p = pjm()
    p.to_csv(CLEAN / "pjm_bra_rto_prices.csv", index=False)
    shutil.copy(RAW / "pjm_bra/pjm_bra_rto_prices_SOURCE.txt", CLEAN / "pjm_bra_rto_prices_SOURCE.txt")

    b = aqueduct()
    b.to_csv(CLEAN / "aqueduct_us_basins.csv", index=False)
    s = aqueduct_state(b)
    s.to_csv(CLEAN / "aqueduct_state_summary.csv", index=False)
    print(f"aqueduct_us_basins: {len(b)} rows; states: {b.state.nunique()}; no_data {int(b.no_data.sum())}, arid {int(b.arid_low_use.sum())}, "
          f"high+extreme {int(b.bws_high.sum())}; state missing: {int(b.state.isna().sum())}; future matched: {int(b.bws_2030_bau_raw.notna().sum())}")
    print(s.sort_values("share_high_or_extreme", ascending=False).head(6).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
