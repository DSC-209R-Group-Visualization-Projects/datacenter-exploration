"""Write the small JSON files the D3 site (web/) reads.

Numbers match prototype.ipynb. Run from the repo root:
    PYTHONPATH=.pylibs python3 scripts/build_site_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "web" / "data"
OUT.mkdir(parents=True, exist_ok=True)

dc = pd.read_csv(CLEAN / "datacenters.csv")
operating = dc[dc.status_group == "operating"]
planned = dc[dc.status_group == "pipeline"]

# --- Backstory: US data center electricity (EPA 2007 report; LBNL 2024 report), same values as notebook Visual A
electricity = [
    {"year": 2000, "twh": 28.2, "pct_us": None},
    {"year": 2006, "twh": 61.4, "pct_us": 1.5},
    {"year": 2014, "twh": 58, "pct_us": None},
    {"year": 2016, "twh": 60, "pct_us": None},
    {"year": 2018, "twh": 76, "pct_us": 1.9},
    {"year": 2023, "twh": 176, "pct_us": 4.4},
]
projection = {"year": 2028, "low_twh": 325, "high_twh": 580, "low_pct": 6.7, "high_pct": 12}
eras = [
    {"id": "early", "start": 1950, "end": 1970, "name": "Mainframes & Apollo"},
    {"id": "super", "start": 1970, "end": 1990, "name": "Supercomputers"},
    {"id": "internet", "start": 1990, "end": 2006, "name": "Internet era"},
    {"id": "cloud", "start": 2006, "end": 2012, "name": "Hyperscale & cloud"},
    {"id": "deep", "start": 2012, "end": 2020, "name": "Deep learning"},
    {"id": "genai", "start": 2020, "end": 2028.5, "name": "Generative AI"},
]
milestones = [
    {"year": 1958, "label": "SAGE air-defense computer", "short": "SAGE"},
    {"year": 1969, "label": "Apollo 11 (IBM System/360 at Mission Control)", "short": "Apollo 11"},
    {"year": 1986, "label": "NSFNET links the supercomputer centers", "short": "NSFNET"},
    {"year": 1993, "label": "Mosaic web browser (NCSA)", "short": "Mosaic"},
    {"year": 2006, "label": "Amazon Web Services launches", "short": "AWS"},
    {"year": 2012, "label": "Deep learning resurgence on GPUs", "short": "Deep learning"},
    {"year": 2022.9, "label": "ChatGPT (Nov 2022)", "short": "ChatGPT"},
]

# --- Backstory: power drawn by one facility vs. Memphis (notebook Visual B and the Memphis cell). "short" labels are for phones
u = pd.read_csv(CLEAN / "eia861_utility_sales.csv")
mem = u[(u.utility_name == "City of Memphis - (TN)") & (u.year == 2025) & (u.part == "A")].iloc[0]
HOURS = 8760
homes_mw, city_mw = mem.res_mwh / HOURS, mem.total_mwh / HOURS
facilities = [
    {"label": "SAGE air-defense computer", "short": "SAGE", "when": "1958", "mw": 3, "kind": "facility",
     "source": "AN/FSQ-7: up to 3 MW (Wikipedia)"},
    {"label": "Typical operating data center", "short": "Typical today", "when": "today", "mw": float(operating.mw.median()), "kind": "facility",
     "source": f"median of {operating.mw.notna().sum()} operating sites with reported capacity, Data Centers Database"},
    {"label": "xAI Colossus 1, Memphis", "short": "Colossus 1", "when": "2024", "mw": 150, "kind": "facility",
     "source": "grid supply upgraded toward ~150 MW (Wikipedia)"},
    {"label": "Typical planned data center", "short": "Typical planned", "when": "pipeline", "mw": float(planned.mw.median()), "kind": "facility",
     "source": f"median of {planned.mw.notna().sum()} planned sites with reported capacity, Data Centers Database"},
    {"label": "xAI Colossus sites, Memphis–Southaven", "short": "All Colossus sites", "when": "2026", "mw": 1000, "kind": "facility",
     "source": "~1 GW combined by mid-2026 (Wikipedia, citing Epoch AI)"},
    {"label": "All Memphis homes", "when": "average draw, 2025", "mw": round(homes_mw), "kind": "city",
     "source": "MLGW residential sales / 8,760 h (EIA-861, 2025)"},
    {"label": "All of Memphis", "when": "homes, business, industry", "mw": round(city_mw), "kind": "city",
     "source": "MLGW total sales / 8,760 h (EIA-861, 2025)"},
]

backstory = {"electricity": electricity, "projection": projection, "eras": eras, "milestones": milestones,
             "facilities": facilities,
             "memphis": {"homes_mw": round(homes_mw), "city_mw": round(city_mw), "customers": int(mem.res_customers),
                         "gw_vs_homes": round(1000 / homes_mw, 1), "gw_vs_city": round(1000 / city_mw, 2)}}
(OUT / "backstory.json").write_text(json.dumps(backstory, indent=1))
print("wrote", OUT / "backstory.json")

# --- Hero background: every operating and planned site as [lon, lat, 1 = operating / 0 = planned]
sites = pd.concat([operating, planned]).query("coord_ok")
points = [[round(r.lon, 3), round(r.lat, 3), int(r.status_group == "operating")] for r in sites.itertuples()]
(OUT / "sites.json").write_text(json.dumps({"operating": len(operating), "planned": len(planned), "points": points},
                                           separators=(",", ":")))
print("wrote", OUT / "sites.json", len(points), "points")
print(json.dumps(backstory["memphis"]), [round(f["mw"]) for f in facilities])

# --- Chapter 1, the build-out (notebook cells 10-15): state and Virginia-county counts, plus every site for tooltips
def rounded(geom, nd=3):
    """Round GeoJSON coordinates to nd decimals (about 100 m) to keep the file small."""
    def r(c): return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], (int, float)) else [r(x) for x in c]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}

op_state, pl_state = operating.groupby("state").size(), planned.groupby("state").size()
states_geo = json.load(open(CLEAN / "states_simplified.geojson"))
states = [{"type": "Feature", "geometry": rounded(f["geometry"]),
           "properties": {"state": f["properties"]["state"], "name": f["properties"]["name"],
                          "op": int(op_state.get(f["properties"]["state"], 0)),
                          "pl": int(pl_state.get(f["properties"]["state"], 0))}} for f in states_geo["features"]]
op_county = operating.assign(geoid=operating.county_geoid.astype("Int64").astype(str).str.zfill(5)).groupby("geoid").size()
counties_geo = json.load(open(CLEAN / "counties_simplified.geojson"))
va_counties = [{"type": "Feature", "geometry": rounded(f["geometry"]),
                "properties": {"geoid": f["properties"]["geoid"], "name": f["properties"]["name"],
                               "op": int(op_county.get(f["properties"]["geoid"], 0))}}
               for f in counties_geo["features"] if f["properties"]["geoid"].startswith("51")]
site_rows = [[round(r.lon, 3), round(r.lat, 3), int(r.status_group == "operating"),
              r.facility_name if isinstance(r.facility_name, str) else "(unnamed)",
              r.city if isinstance(r.city, str) else "", r.state, r.status]
             for r in pd.concat([operating, planned]).query("coord_ok").itertuples()]
buildout = {"operating": len(operating), "planned": len(planned), "n_states": int(operating.state.nunique()),
            "growth_pct": round(len(planned) / len(operating) * 100),
            "states": states, "va_counties": va_counties, "sites": site_rows}
(OUT / "buildout.json").write_text(json.dumps(buildout, separators=(",", ":")))
print("wrote", OUT / "buildout.json", "top states:", op_state.sort_values().tail(3).to_dict(),
      "growth", buildout["growth_pct"], "%")

# --- Chapter 2, communities push back (notebook cells 16-24): every moratorium, monthly counts, outcomes and reasons
REASON_NAMES = {"regulatory_gap": "need time to write rules", "grid_energy": "grid and energy", "water": "water",
                "land_use_compatibility": "land use fit", "infrastructure_capacity": "roads, sewer, capacity",
                "specific_project": "a specific project", "noise": "noise", "environmental": "environment",
                "fire_safety": "fire safety", "property_values": "property values",
                "agricultural_preservation": "farmland", "legal_or_litigation": "legal", "other": "other"}
m = pd.read_csv(CLEAN / "moratoria_local.csv", dtype={"county_geoid": str}, parse_dates=["date_enacted"])
adopted = m[m.adopted]
m["reasons"] = m[[f"reason_{k}" for k in REASON_NAMES]].apply(
    lambda r: ", ".join(REASON_NAMES[c[7:]] for c, v in r.items() if v) or "none coded", axis=1)
shown = m[m.adopted | (m.enacted_status == "pending")]
# kind: 2 = adopted and in force, 1 = adopted but no longer in force, 0 = proposed
moratoria = [[round(r.lon, 3), round(r.lat, 3), 2 if r.adopted and r.in_force else 1 if r.adopted else 0,
              r.jurisdiction, r.state, r.enacted_status,
              r.date_enacted.strftime("%Y-%m") if pd.notna(r.date_enacted) else "", r.reasons]
             for r in shown.itertuples()]
monthly = adopted.set_index("date_enacted").resample("MS").size()
mor_state = adopted.groupby("state").size()
status_order = [("operating", "Operating"), ("pipeline", "Planned"), ("stalled", "Stalled"), ("cancelled", "Cancelled")]
outcomes = [{"group": g, "label": lab, "n": int((dc[dc.status_group == g].pushback_documented == True).sum()),
             "of": int((dc.status_group == g).sum())} for g, lab in status_order]
harms = [k for k in REASON_NAMES if k not in ("regulatory_gap", "other")]
concerns = sorted([{"key": k, "label": REASON_NAMES[k], "pct": round(adopted[f"reason_{k}"].mean() * 100, 1)} for k in harms],
                  key=lambda d: -d["pct"])
pushback = {"adopted": len(adopted), "n_states": int(adopted.state.nunique()), "in_force": int(adopted.in_force.sum()),
            "proposed": int((m.enacted_status == "pending").sum()),
            "monthly": [[d.strftime("%Y-%m"), int(v)] for d, v in monthly[monthly.index >= "2025-01-01"].items()],
            "before_2025": int((adopted.date_enacted < "2025-01-01").sum()), "undated": int(adopted.date_enacted.isna().sum()),
            "states": {s: {"mor": int(mor_state.get(s, 0)), "op": int(op_state.get(s, 0))}
                       for s in sorted(set(mor_state.index) | set(op_state.index))},
            "outcomes": outcomes, "concerns": concerns,
            "rules_pct": round(adopted.reason_regulatory_gap.mean() * 100),
            # "at least one specific harm" in cell 23 = any reason other than needing time to write rules
            "any_harm_pct": round(adopted[[f"reason_{k}" for k in REASON_NAMES if k != "regulatory_gap"]].any(axis=1).mean() * 100),
            "moratoria": moratoria}
(OUT / "pushback.json").write_text(json.dumps(pushback, separators=(",", ":")))
print("wrote", OUT / "pushback.json", len(moratoria), "moratoria;", {k: pushback[k] for k in
      ("adopted", "in_force", "proposed", "before_2025", "undated", "rules_pct", "any_harm_pct")},
      "FL+KS+ME:", int(mor_state[["FL", "KS", "ME"]].sum()), "outcomes:", [(o["label"], o["n"], o["of"]) for o in outcomes],
      "concerns:", [(c["label"], c["pct"]) for c in concerns[:3]])

# --- Chapter 3, is the grid under strain (notebook cells 26-30): grid regions with NERC risk by year, sites by risk
nerc = pd.read_csv(CLEAN / "nerc_ltra_risk.csv")
county_ba = pd.read_csv(CLEAN / "county_ba.csv", dtype={"county_geoid": str})
NERC_YEARS = [2026, 2027, 2028, 2029, 2030]
site_risk = (pd.concat([operating, planned]).assign(county_geoid=lambda d: d.county_geoid.astype("Int64").astype(str).str.zfill(5))
             .merge(county_ba[["county_geoid", "ba_code"]], on="county_geoid", how="left").merge(nerc, on="ba_code", how="left"))
area_sites = site_risk.groupby("nerc_area").status_group.value_counts().unstack(fill_value=0)
nerc_by_ba = nerc.set_index("ba_code")
ba_geo = json.load(open(CLEAN / "ba_regions.geojson"))
regions = []
for f in ba_geo["features"]:
    p = f["properties"]; ba = p["ba_code"]; row = nerc_by_ba.loc[ba] if ba in nerc_by_ba.index else None
    area = row.nerc_area if row is not None else None
    regions.append({"type": "Feature", "geometry": rounded(f["geometry"], 2), "properties": {
        "ba": ba, "name": p["ba_name"], "area": area,
        "risk": [row[f"risk_{y}"] for y in NERC_YEARS] if row is not None else None,
        "op": int(area_sites.loc[area, "operating"]) if area in area_sites.index else 0,
        "pl": int(area_sites.loc[area, "pipeline"]) if area in area_sites.index else 0}})
by_year = {y: {g: site_risk[site_risk.status_group == g][f"risk_{y}"].fillna("not assessed").value_counts().to_dict()
               for g in ("operating", "pipeline")} for y in NERC_YEARS}
RISK_LEVELS = ["Normal", "Elevated", "High"]   # sites: [lon, lat, 1 = operating, risk index per year (-1 = not assessed)]
grid_sites = [[round(r.lon, 3), round(r.lat, 3), int(r.status_group == "operating")]
              + [RISK_LEVELS.index(getattr(r, f"risk_{y}")) if isinstance(getattr(r, f"risk_{y}"), str) else -1 for y in NERC_YEARS]
              for r in site_risk.query("coord_ok").itertuples()]
# One outline per NERC assessment area: its utility regions merged (a small buffer closes slivers between neighbours),
# specks and pinholes dropped (rounded, they collapse and d3-geo reads them as the whole globe), exteriors clockwise
from shapely import union_all
from shapely.geometry import shape, mapping, Polygon
from shapely.geometry.polygon import orient
area_outlines = []
for area, fs in pd.Series(regions).groupby([f["properties"]["area"] for f in regions]):
    u = union_all([shape(f["geometry"]).buffer(0.02) for f in fs]).buffer(-0.02).simplify(0.02)
    polys = [orient(Polygon(q.exterior, [h for h in q.interiors if Polygon(h).area > 0.01]), sign=-1.0)
             for q in getattr(u, "geoms", [u]) if q.area > 0.01]
    geom = mapping(polys[0] if len(polys) == 1 else type(u)(polys))
    area_outlines.append({"type": "Feature", "geometry": rounded(json.loads(json.dumps(geom)), 2), "properties": {"area": area}})
grid = {"years": NERC_YEARS, "regions": regions, "by_year": by_year, "operating": len(operating), "planned": len(planned),
        "sites": grid_sites, "area_outlines": area_outlines}
(OUT / "grid.json").write_text(json.dumps(grid, separators=(",", ":")))
print("wrote", OUT / "grid.json", {y: by_year[y]["operating"] for y in (2026, 2030)})

# --- Chapter 4, electric bills (notebook cells 31-38): state price change vs datacenters, then the PJM capacity auction
res = pd.read_csv(CLEAN / "eia861_state_residential.csv")
u = pd.read_csv(CLEAN / "eia861_utility_sales.csv")
county_pop = pd.read_csv(CLEAN / "counties.csv", dtype={"geoid": str})
PRICE_BASE, PRICE_END = 2019, 2025
real_price = res.pivot(index="state", columns="year", values="res_price_cents_kwh_real2025")
sales_2025 = u[u.year == PRICE_END]
pjm_share = (sales_2025[sales_2025.ba_code == "PJM"].groupby("state").res_customers.sum()
             / sales_2025.groupby("state").res_customers.sum())
st_price = pd.DataFrame({
    "state_name": county_pop.drop_duplicates("state").set_index("state").state_name,
    "pop_m": county_pop.groupby("state").pop_2025.sum() / 1e6,
    "dc_live": pd.concat([operating, planned]).groupby("state").size(),
    "price_base": real_price[PRICE_BASE], "price_end": real_price[PRICE_END],
    "pjm_share": pjm_share}).loc[real_price.index]
st_price[["dc_live", "pjm_share"]] = st_price[["dc_live", "pjm_share"]].fillna(0)
st_price["dc_per_m"] = st_price.dc_live / st_price.pop_m
st_price["change_pct"] = (st_price.price_end / st_price.price_base - 1) * 100
st_price["pjm"] = st_price.pjm_share > 0.5
MARKET = {"PJM": "PJM", "MISO": "capacity", "NYIS": "capacity", "ISNE": "capacity", "CISO": "regional", "ERCO": "regional", "SWPP": "regional"}
market_share = (sales_2025.assign(market=sales_2025.ba_code.map(MARKET).fillna("utility"))
                .groupby(["state", "market"]).res_customers.sum().unstack(fill_value=0))
st_price["market"] = market_share.idxmax(axis=1)
us_res = res.groupby("year")[["res_revenue_kusd", "res_mwh"]].sum()
cpi = pd.read_csv(CLEAN / "cpi_annual.csv").set_index("year").deflator_to_2025
us_price = us_res.res_revenue_kusd / us_res.res_mwh * 100 * us_res.index.map(cpi)
us_change = (us_price[PRICE_END] / us_price[PRICE_BASE] - 1) * 100
rho = st_price.dc_per_m.corr(st_price.change_pct, method="spearman")
bill_states = [{"st": s, "name": r.state_name, "dc": int(r.dc_live), "per_m": round(r.dc_per_m, 2),
                "p0": round(r.price_base, 2), "p1": round(r.price_end, 2), "chg": round(r.change_pct, 1),
                "pjm": bool(r.pjm), "market": r.market} for s, r in st_price.iterrows()]
medians = {"pjm": round(st_price[st_price.pjm].change_pct.median(), 1), "other": round(st_price[~st_price.pjm].change_pct.median(), 1),
           "market": st_price.groupby("market").change_pct.median().round(1).to_dict()}

# PJM capacity auction (Visual G): published clearing prices, costs in 2025 dollars, rough monthly add for a typical household
bra = pd.read_csv(CLEAN / "pjm_bra_rto_prices.csv")
deflator = cpi.copy()
deflator[2017] = 321.943 / 245.120   # 2025 CPI-U over the BLS 2017 annual average, as in the notebook
bra["cost_real_b"] = bra.cleared_cost_usd_billion * bra.delivery_year_start.clip(upper=2025).map(deflator)
pjm_load = pd.read_csv(CLEAN / "eia930_ba_annual.csv").query("ba == 'PJM' and complete_year").set_index("year")
bra["load_gwh"] = bra.delivery_year_start.clip(pjm_load.index.min(), pjm_load.index.max()).map(pjm_load.total_gwh_scaled)
bra["cents_per_kwh"] = bra.cost_real_b * 1e9 / (bra.load_gwh * 1e6) * 100
pjm_res = u[(u.ba_code == "PJM") & (u.year == 2025)]
TYPICAL_KWH = pjm_res.res_mwh.sum() * 1000 / pjm_res.res_customers.sum() / 12
bra["usd_month"] = bra.cents_per_kwh * TYPICAL_KWH / 100
IMM_ACTUAL, IMM_NO_DC, IMM_NO_NEW_DC = 14.687, 5.355, 6.944   # IMM Part G re-run of 2025/26, $B
dc_part = bra.set_index("delivery_year").usd_month["2025/26"] * (1 - IMM_NO_DC / IMM_ACTUAL)
auctions = [{"year": r.delivery_year, "start": int(r.delivery_year_start), "price": r.rto_clearing_price_usd_per_mw_day,
             "cost": r.cleared_cost_usd_billion, "cost_real": round(r.cost_real_b, 2), "month": round(r.usd_month, 2),
             "margin": r.rpm_reserve_margin_pct} for r in bra.itertuples()]
bills = {"base": PRICE_BASE, "end": PRICE_END, "us_change": round(us_change, 1), "rho": round(rho, 2), "medians": medians,
         "states": bill_states, "auctions": auctions, "typical_kwh": round(TYPICAL_KWH), "dc_part": round(dc_part, 2),
         "imm": {"prior": round(bra.set_index("delivery_year").cost_real_b["2024/25"], 2), "no_dc": IMM_NO_DC,
                 "no_new_dc": IMM_NO_NEW_DC, "actual": IMM_ACTUAL}}
(OUT / "bills.json").write_text(json.dumps(bills, separators=(",", ":")))
print("wrote", OUT / "bills.json", {"us": bills["us_change"], "rho": bills["rho"], "medians": medians, "dc_part": bills["dc_part"]})

# --- Chapter 5, water (notebook cells 39-43): county water stress, every site's basin stress, shares by stress level
water = pd.read_csv(CLEAN / "aqueduct_county.csv", dtype={"county_geoid": str}).set_index("county_geoid")
county_names = county_pop.set_index("geoid")
w_sites = (pd.concat([operating, planned]).query("coord_ok")
           .merge(pd.read_csv(CLEAN / "datacenters_basin.csv")[["facility_id", "stress_group"]], on="facility_id", how="left"))
w_sites["no_basin"] = w_sites.stress_group.isna() | w_sites.stress_group.eq("No data")
STRESS = ["Extremely high", "High", "Medium-high", "Low-medium", "Low", "Arid, low use"]   # most stressed first, as Visual H
HIGH_STRESS = STRESS[:2]
known = w_sites[~w_sites.no_basin]
w_counts = pd.crosstab(known.status_group, known.stress_group).reindex(index=["operating", "pipeline"], columns=STRESS, fill_value=0)
# Only counties with some high-stress area are drawn, as in the notebook map; the rest show the state fill underneath
w_counties = [{"type": "Feature", "geometry": rounded(f["geometry"], 2),   # about 1 km, plenty for a national map
               "properties": {"name": f"{county_names.county_name[g]}, {county_names.state[g]}" if g in county_names.index else f["properties"]["name"],
                              "share": round(water.share_high_or_extreme[g], 3)}}
              for f in counties_geo["features"] if (g := f["properties"]["geoid"]) in water.index and water.share_high_or_extreme[g] > 0.005]
basin_base = pd.read_csv(CLEAN / "basin_population.csv").set_index("stress_group")
w_high = known[known.stress_group.isin(HIGH_STRESS)]
water_out = {"stress": STRESS,
             "counts": {g: [int(n) for n in w_counts.loc[g]] for g in w_counts.index},
             "pop_share": [round(basin_base.population_share.get(s, 0) * 100, 1) for s in STRESS],
             "pop_high": round(basin_base.population_share[HIGH_STRESS].sum() * 100, 1),
             "no_basin": int(w_sites.no_basin.sum()), "no_basin_states": w_sites[w_sites.no_basin].state.value_counts().head(2).to_dict(),
             "top_states": w_high.state.value_counts().head(5).to_dict(),
             "counties": w_counties,
             # sites: [lon, lat, 1 = operating, stress index (-1 = no water data at the site)]
             "sites": [[round(r.lon, 3), round(r.lat, 3), int(r.status_group == "operating"),
                        -1 if r.no_basin else STRESS.index(r.stress_group)] for r in w_sites.itertuples()]}
(OUT / "water.json").write_text(json.dumps(water_out, separators=(",", ":")))
print("wrote", OUT / "water.json", water_out["counts"], "high:", len(w_high), water_out["top_states"],
      "pop high", water_out["pop_high"], "no basin", water_out["no_basin"], water_out["no_basin_states"],
      "counties", len(w_counties))
