"""Export the data behind prototypes E and F as small JS files for the D3 versions (run from the repo root:
python3 scripts/export_energy_d3_data.py). Same definitions as sgarimella/prototype_e_price_scatter.ipynb and
prototype_f_capacity_bill.ipynb; writes sgarimella/d3/data_e.js and data_f.js.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "sgarimella" / "d3"
OUT.mkdir(parents=True, exist_ok=True)
BASE, END = 2019, 2025


def r(v, n=2):
    return None if pd.isna(v) else round(float(v), n)


# ---- E: state data center density vs real residential price change
s = pd.read_csv(CLEAN / "eia861_state_residential.csv")
d = pd.read_csv(CLEAN / "datacenters.csv")
c = pd.read_csv(CLEAN / "counties.csv", dtype={"geoid": str})
u = pd.read_csv(CLEAN / "eia861_utility_sales.csv")
cpi = pd.read_csv(CLEAN / "cpi_annual.csv").set_index("year")["deflator_to_2025"]

pop = c.groupby("state")["pop_2025"].sum() / 1e6
names = c.drop_duplicates("state").set_index("state")["state_name"]
live = d[d.status_group.isin(["operating", "pipeline"])].groupby("state").size()
op = d[d.status_group == "operating"].groupby("state").size()
r25 = u[u.year == END]
pjm = (r25[r25.ba_code == "PJM"].groupby("state")["res_customers"].sum() / r25.groupby("state")["res_customers"].sum())

w = s.pivot(index="state", columns="year", values="res_price_cents_kwh_real2025")
idx = w.div(w[BASE], axis=0) * 100
us = s.groupby("year")[["res_revenue_kusd", "res_mwh"]].sum()
us["price"] = us.res_revenue_kusd / us.res_mwh * 100 * us.index.map(cpi)
us_idx = us.price / us.price[BASE] * 100
years = [int(y) for y in w.columns]

states = []
for st in w.index:
    n_live = int(live.get(st, 0))
    states.append({
        "st": st, "name": names[st], "dc": n_live, "dcOp": int(op.get(st, 0)),
        "perM": r(n_live / pop[st], 2), "p19": r(w.loc[st, BASE]), "p25": r(w.loc[st, END]),
        "chg": r((w.loc[st, END] / w.loc[st, BASE] - 1) * 100, 1),
        "pjm": bool(pjm.get(st, 0) > 0.5), "idx": [r(v, 1) for v in idx.loc[st]],
    })
E = {"years": years, "us": [r(v, 1) for v in us_idx.loc[years]], "usChange": r(us_idx[END] - 100, 1), "states": states}
(OUT / "data_e.js").write_text("const DATA_E = " + json.dumps(E, separators=(",", ":")) + ";\n")

# ---- F: PJM capacity auction and the bill estimate
p = pd.read_csv(CLEAN / "pjm_bra_rto_prices.csv")
e = pd.read_csv(CLEAN / "eia930_ba_annual.csv").query("ba == 'PJM' and complete_year").set_index("year")
p["load_year"] = p.delivery_year_start.clip(e.index.min(), e.index.max())
p["load_gwh"] = p.load_year.map(e.total_gwh_scaled)
p["cents"] = p.cleared_cost_usd_billion * 1e9 / (p.load_gwh * 1e6) * 100
r_ = u[(u.ba_code == "PJM") & (u.year == 2025)]
typical = r_.res_mwh.sum() * 1000 / r_.res_customers.sum() / 12
F = {
    "typicalKwh": round(float(typical)),
    "rows": [{"dy": x.delivery_year, "start": int(x.delivery_year_start), "price": r(x.rto_clearing_price_usd_per_mw_day),
              "mw": r(x.cleared_ucap_mw, 0), "costB": r(x.cleared_cost_usd_billion, 1), "reserve": r(x.rpm_reserve_margin_pct, 1),
              "cents": r(x.cents, 4)} for x in p.itertuples()],
}
(OUT / "data_f.js").write_text("const DATA_F = " + json.dumps(F, separators=(",", ":")) + ";\n")
print("wrote", OUT / "data_e.js", "and", OUT / "data_f.js", "|", len(states), "states,", len(F["rows"]), "auctions, typical", F["typicalKwh"], "kWh")
