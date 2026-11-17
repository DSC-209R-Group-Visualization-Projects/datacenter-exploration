"""Generate the energy bill prototype notebooks in sgarimella/ (run from the repo root: python3 scripts/make_energy_prototypes.py).

E: data centers vs residential price change by state, brushed to price lines   F: PJM capacity prices and what they add to a bill
Both read data/clean/ only. Figures go to images/, interactive pages to sgarimella/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".pylibs"))
import nbformat as nbf  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sgarimella"
OUT.mkdir(exist_ok=True)
SETUP = '''import sys, warnings
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name in ("data", "jppolizzi", "pnidadavolu", "sgarimella") else Path.cwd()
sys.path[:0] = [str(ROOT / ".pylibs"), str(ROOT / "scripts")]
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
CLEAN = ROOT / "data" / "clean"

# Same palette as prototypes C and D.
INK, INK2, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE, ORANGE, AQUA, YELLOW, NEUTRAL = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#a9a89f"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlecolor": INK, "figure.facecolor": SURF, "axes.facecolor": SURF})
'''


def nb(cells, path):
    n = nbf.v4.new_notebook()
    n.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1]) for c in cells]
    n.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbf.write(n, path)


# ---------------------------------------------------------------- Prototype E: data centers vs price change
E = [
("md", """# Prototype E: do states with more data centers have faster rising electricity prices?
**Question:** Residents often say data centers will raise their electric bills. At the state level, did residential prices rise faster where there are more data centers?

**Data:** EIA Form 861 residential revenue and sales by state, 2018 to 2025, in 2025 dollars (BLS CPI-U). Data centers from the project database, counted per million residents (Census PEP 2025).

**Design:** a scatter of states (data centers per million residents vs. real price change, 2019 to 2025), linked to a line chart of each state's price over time. Brushing states on the scatter draws their price lines next to the U.S. average. Orange marks states where most residential customers are served by utilities in the PJM grid, which links this chart to prototype F.

**What this can show:** whether high data center states stand out on price, and which states drive any pattern.
**What it can't:** cause. State prices move with fuel costs, wildfire and storm costs, transmission spending and rate cases, so a state can rank high on both without one causing the other.

Caveats carried onto the page:
- The database has no build date for most facilities, so the x axis is how many data centers a state has now (operating plus planned), not growth over time.
- Facility counts treat a small server room and a 1 GW campus the same. MW is reported for only 40% of rows, too few to use here.
- Prices are annual averages (revenue divided by kWh). The PJM capacity jump reached bills in June 2025, so 2025 only partly shows it.
- Planned facilities count toward the x axis even though they cannot have affected past prices; the operating-only count is in the table below."""),
("code", SETUP + '''s = pd.read_csv(CLEAN / "eia861_state_residential.csv")
d = pd.read_csv(CLEAN / "datacenters.csv")
c = pd.read_csv(CLEAN / "counties.csv", dtype={"geoid": str})
u = pd.read_csv(CLEAN / "eia861_utility_sales.csv")
cpi = pd.read_csv(CLEAN / "cpi_annual.csv").set_index("year")["deflator_to_2025"]
BASE, END = 2019, 2025

pop = c.groupby("state")["pop_2025"].sum()
names = c.drop_duplicates("state").set_index("state")["state_name"]
live = d[d.status_group.isin(["operating", "pipeline"])]
n_all = live.groupby("state").size()
n_op = d[d.status_group == "operating"].groupby("state").size()

# PJM share: share of a state's residential customers whose utility sits in the PJM balancing authority (2025).
r25 = u[u.year == END]
pjm_share = r25[r25.ba_code == "PJM"].groupby("state")["res_customers"].sum() / r25.groupby("state")["res_customers"].sum()

w = s.pivot(index="state", columns="year", values="res_price_cents_kwh_real2025")
t = pd.DataFrame({
    "state_name": names,
    "pop_m": pop / 1e6,
    "dc_live": n_all, "dc_operating": n_op,
    "price_2019": w[BASE], "price_2025": w[END],
    "pjm_share": pjm_share,
}).loc[w.index]
t[["dc_live", "dc_operating", "pjm_share"]] = t[["dc_live", "dc_operating", "pjm_share"]].fillna(0)
t["dc_per_m"] = t.dc_live / t.pop_m
t["dc_op_per_m"] = t.dc_operating / t.pop_m
t["price_change_pct"] = (t.price_2025 / t.price_2019 - 1) * 100
t["pjm"] = t.pjm_share > 0.5
print(len(t), "states (incl. DC);", int((t.dc_live == 0).sum()), "with no operating or planned data centers in the database")
print("PJM states:", ", ".join(t.index[t.pjm]))'''),
("md", "## The table behind the scatter"),
("code", '''cols = ["dc_live", "dc_operating", "dc_per_m", "dc_op_per_m", "price_2019", "price_2025", "price_change_pct", "pjm"]
display(t.sort_values("dc_per_m", ascending=False)[cols].round(1).head(12))
rho_all = t.dc_per_m.corr(t.price_change_pct, method="spearman")
rho_op = t.dc_op_per_m.corr(t.price_change_pct, method="spearman")
rho_x = t.drop(index="VA").dc_per_m.corr(t.drop(index="VA").price_change_pct, method="spearman")
print(f"Spearman rank correlation, data centers per million vs real price change 2019-25: {rho_all:.2f} "
      f"(operating only {rho_op:.2f}; without VA {rho_x:.2f})")
print(f"Median real change: PJM states {t[t.pjm].price_change_pct.median():.1f}%, others {t[~t.pjm].price_change_pct.median():.1f}%")'''),
("md", """## U.S. average and the price index
The U.S. line is total residential revenue over total residential kWh across all states, deflated the same way. The line chart shows each state's real price as an index (2019 = 100) so a cheap state and an expensive state can be compared on change."""),
("code", '''us = s.groupby("year")[["res_revenue_kusd", "res_mwh"]].sum()
us["price"] = us.res_revenue_kusd / us.res_mwh * 100 * us.index.map(cpi)   # kUSD/MWh = $/kWh*... -> cents/kWh, then 2025 dollars
idx = w.div(w[BASE], axis=0) * 100
us_idx = us.price / us.price[BASE] * 100
print(f"U.S. real residential price: {us.price[BASE]:.2f} cents/kWh in {BASE}, {us.price[END]:.2f} in {END} ({us_idx[END] - 100:+.1f}%)")
display(idx.loc[["VA", "MD", "NJ", "CA", "TX", "IA"]].round(0))'''),
("md", "## Static figure for the proposal (saved as an image)"),
("code", '''ZERO = 0.2                      # where states with no data centers sit on the log axis
TICKS = [ZERO, 0.5, 1, 2, 5, 10, 20, 50]
TICKL = ["0", "0.5", "1", "2", "5", "10", "20", "50"]
t["x"] = t.dc_per_m.where(t.dc_per_m > 0, ZERO)
LABEL = ["VA", "DC", "CA", "MD", "NJ", "ME", "OR", "NY", "PA", "OH", "GA", "TX", "IA", "NV", "NE", "AZ"]

fig, (ax, bx) = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw=dict(width_ratios=[1.15, 1], wspace=0.18))
for flag, col, lab in [(False, BLUE, "other states"), (True, ORANGE, "mostly PJM customers")]:
    g = t[t.pjm == flag]
    ax.scatter(g.x, g.price_change_pct, s=46, color=col, edgecolors=SURF, linewidths=1, label=f"{lab} ({len(g)})", zorder=3)
for st in LABEL:
    r = t.loc[st]
    ax.annotate(st, (r.x, r.price_change_pct), xytext=(5, 3), textcoords="offset points", fontsize=8.5, color=INK)
ax.set_xscale("log"); ax.set_xticks(TICKS, TICKL); ax.minorticks_off()
ax.axhline(0, color=AXIS, lw=1); ax.axhline(us_idx[END] - 100, color=INK2, lw=1, ls="--")
ax.text(60, us_idx[END] - 100 + 0.8, f"U.S. {us_idx[END] - 100:+.0f}%", ha="right", fontsize=8.5, color=INK2)
ax.set_xlim(0.15, 75)
ax.set_xlabel("operating and planned data centers per million residents (log scale)")
ax.set_ylabel(f"change in residential price, {BASE} to {END} (%, after inflation)")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_title("More data centers, not faster price rises; PJM states rose more", loc="left", fontsize=12, fontweight="bold", pad=24)
ax.text(0, 1.01, f"Rank correlation {rho_all:.2f}. Median change: PJM states {t[t.pjm].price_change_pct.median():+.0f}%, others {t[~t.pjm].price_change_pct.median():+.0f}%.",
        transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")

HL = {"VA": ORANGE, "MD": ORANGE, "CA": BLUE, "TX": BLUE}
yrs = idx.columns.values
for st in idx.index:
    if st not in HL: bx.plot(yrs, idx.loc[st], color=GRID, lw=0.9, zorder=1)
bx.plot(yrs, us_idx.loc[yrs], color=INK, lw=2.4, zorder=3)
bx.annotate("U.S.", (yrs[-1], us_idx[END]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, fontweight="bold")
ends = {}
for st, col in HL.items():
    bx.plot(yrs, idx.loc[st], color=col, lw=2, zorder=2); ends[st] = idx.loc[st, END]
pos = {}
for st, v in sorted(ends.items(), key=lambda kv: kv[1]):
    pos[st] = max(v, max(pos.values(), default=-99) + 3.5)
for st, v in ends.items():
    bx.annotate(names[st], (yrs[-1], v), xytext=(yrs[-1] + 0.15, pos[st]), textcoords="data", va="center", fontsize=9, color=HL[st])
bx.axhline(100, color=AXIS, lw=1)
bx.set_xlim(yrs[0], yrs[-1] + 1.4); bx.set_xticks(yrs)
bx.set_ylabel(f"real residential price, index ({BASE} = 100)")
bx.grid(axis="y", color=GRID, lw=0.8); bx.set_axisbelow(True)
for sp in ["top", "right"]: bx.spines[sp].set_visible(False)
bx.set_title("Price paths for selected states", loc="left", fontsize=12, fontweight="bold", pad=24)
bx.text(0, 1.01, "Grey: every other state. In the interactive version the selected states replace these four.",
        transform=bx.transAxes, fontsize=9, color=INK2, va="bottom")
fig.text(0.01, 0.0, "Source: EIA Form 861 (residential revenue and sales by state), BLS CPI-U, Census PEP 2025, project data center database. "
         "Counts are facilities, not MW. PJM: over half of the state's residential customers are served by utilities in the PJM balancing authority.",
         fontsize=8, color=INK2)
fig.savefig(ROOT / "images" / "prototype_e_price_scatter.png", dpi=160, bbox_inches="tight")
plt.show()'''),
("md", """## Interactive prototype (brush the scatter, see the price lines)
Drag a box or lasso on the scatter to select states; their price lines are drawn on the right next to the U.S. average. Click a single dot to add or remove it. Double click the scatter to clear.
The linking runs in JavaScript, so open `sgarimella/prototype_e_price_scatter.html` in a browser. The copy shown in the notebook is not linked."""),
("code", '''import json, plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(rows=1, cols=2, column_widths=[0.52, 0.48], horizontal_spacing=0.09,
                    subplot_titles=("States: data centers vs price change", "Real residential price, 2019 = 100"))
order = list(idx.index)
for flag, col, lab in [(False, BLUE, "other states"), (True, ORANGE, "mostly PJM customers")]:
    g = t[t.pjm == flag]
    fig.add_trace(go.Scatter(x=g.x, y=g.price_change_pct, mode="markers+text", name=lab, text=g.index, textposition="top center",
        textfont=dict(size=9, color=INK2), customdata=g.reset_index()[["state", "state_name", "dc_live", "dc_operating", "price_2019", "price_2025"]].values.tolist(),
        marker=dict(size=10, color=col, line=dict(width=1, color=SURF)),
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.25)),
        hovertemplate="<b>%{customdata[1]}</b><br>%{customdata[2]} data centers (%{customdata[3]} operating)<br>"
                      "%{x:.1f} per million residents<br>%{customdata[4]:.1f} to %{customdata[5]:.1f} cents/kWh (2025 $)<br>"
                      "%{y:+.1f}% after inflation<extra></extra>"), 1, 1)
fig.add_hline(y=us_idx[END] - 100, line=dict(color=INK2, dash="dash", width=1), row=1, col=1,
              annotation_text=f"U.S. {us_idx[END] - 100:+.0f}%", annotation_position="bottom right", annotation_font_color=INK2)
yrs = [int(y) for y in idx.columns]
for st in order:   # grey context lines
    fig.add_trace(go.Scatter(x=yrs, y=idx.loc[st].round(1).tolist(), mode="lines", name=st, showlegend=False,
        line=dict(color=GRID, width=1), hovertemplate=f"<b>{names[st]}</b> %{{x}}: %{{y:.0f}}<extra></extra>"), 1, 2)
HI0 = len(fig.data)
for st in order:   # highlight layer, shown only for brushed states
    col = ORANGE if t.loc[st, "pjm"] else BLUE
    fig.add_trace(go.Scatter(x=yrs, y=idx.loc[st].round(1).tolist(), mode="lines+text", name=st + " (selected)", showlegend=False,
        visible=False, line=dict(color=col, width=2.5), text=[""] * (len(yrs) - 1) + [st], textposition="middle right",
        textfont=dict(color=col, size=11), hovertemplate=f"<b>{names[st]}</b> %{{x}}: %{{y:.0f}}<extra></extra>"), 1, 2)
fig.add_trace(go.Scatter(x=yrs, y=us_idx.loc[yrs].round(1).tolist(), mode="lines", name="U.S. average", line=dict(color=INK, width=3),
                         hovertemplate="<b>U.S.</b> %{x}: %{y:.0f}<extra></extra>"), 1, 2)
fig.update_xaxes(type="log", tickvals=TICKS, ticktext=TICKL, title="operating and planned data centers per million residents (log)",
                 gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="price change 2019-2025 (%, after inflation)", gridcolor=GRID, zeroline=True, zerolinecolor=AXIS, row=1, col=1)
fig.update_xaxes(dtick=1, range=[2017.7, 2025.8], gridcolor=GRID, row=1, col=2)
fig.update_yaxes(gridcolor=GRID, row=1, col=2)
fig.update_layout(height=600, paper_bgcolor=SURF, plot_bgcolor=SURF, dragmode="select", clickmode="event",
                  margin=dict(l=60, r=30, t=90, b=60), legend=dict(x=0.5, xanchor="right", y=1.0, bgcolor="rgba(252,252,251,0.85)"),
                  title=dict(text="Brush states to compare their price paths with the U.S. average", x=0.01))
fig.add_annotation(text=f"Rank correlation {rho_all:.2f}. Drag a box to select states, click a dot to add or remove it, double click to clear. "
                        "Sources: EIA-861, BLS CPI-U, Census PEP 2025, project data center database.",
                   xref="paper", yref="paper", x=0, y=-0.13, showarrow=False, font=dict(size=10, color=INK2), xanchor="left")

# Brushing: show the highlight line for each selected state. Only restyles visibility, so the selection itself is untouched.
post = """
var gd = document.getElementById('{plot_id}');
var HI0 = %d, ORDER = %s;
var HI = ORDER.map(function (_, k) { return HI0 + k; });
var cur = new Set();
function show(states) {
  cur = states;
  Plotly.restyle(gd, {visible: ORDER.map(function (s) { return states.has(s); })}, HI);
}
function scatterStates(points) {
  return points.filter(function (p) { return p.data.xaxis === 'x'; }).map(function (p) { return p.customdata[0]; });
}
gd.on('plotly_selected', function (ev) {
  if (!ev || !ev.points) return;
  show(new Set(scatterStates(ev.points)));
});
var lastClick = 0;
gd.on('plotly_click', function (ev) {   // click a dot to add or remove that state
  var hit = scatterStates(ev.points); if (!hit.length) return;
  lastClick = Date.now();
  var next = new Set(cur); if (next.has(hit[0])) next.delete(hit[0]); else next.add(hit[0]);
  show(next);
});
// A click on a dot also clears the box, so only clear the lines when no dot click came with it (double click on empty space).
gd.on('plotly_deselect', function () {
  setTimeout(function () { if (Date.now() - lastClick > 400) show(new Set()); }, 200);
});
""" % (HI0, json.dumps(order))
fig.write_html(ROOT / "sgarimella" / "prototype_e_price_scatter.html", include_plotlyjs=True, post_script=post,
               config={"displayModeBar": False})
fig.show()'''),
("md", """## Reading so far
- At the state level the relationship runs the other way from the worry: the rank correlation is about -0.35. Many of the states with the most data centers per resident (Iowa, North Dakota, Nebraska, Texas, Georgia) have cheap power and flat or falling real prices, which may be part of why developers build there. The biggest increases (DC, California, Maine, Maryland, New York) are in states with few data centers.
- Virginia, with by far the most data centers per resident, is flat after inflation (+0.6%).
- What does stand out is the grid: states mostly served by PJM utilities had a median real increase of about +9%, against about -1% for the rest. That points to a region-wide cost more than a local one, which is what prototype F looks at.

Next steps: swap the x axis to MW where coverage allows, try utility-level prices (`proto_data.utility_price_table`) to see whether utilities that serve data center counties differ from neighbors in the same state, and add 2026 once EIA posts it."""),
]

# ---------------------------------------------------------------- Prototype F: PJM capacity prices and the bill
F = [
("md", """# Prototype F: PJM capacity prices and what they add to a monthly bill
**Question:** Grid strain is abstract. PJM, the grid operator for 13 states and DC, runs a yearly auction to buy enough power plant capacity for future peak demand. When forecast demand (much of it from data centers) grows faster than supply, the auction price rises and every utility in the region pays it. How big was the jump, and what does it mean for a household?

**Data:** PJM Base Residual Auction results for delivery years 2017/18 to 2027/28 (clearing price in $/MW-day, total cost, reserve margin), transcribed from the 2027/28 BRA report. PJM annual load and peak from EIA Form 930. Typical household usage from EIA Form 861.

**Design:** a step chart of the clearing price (each delivery year runs June to May, so the price is flat across it), with notes on key events, and a slider where you set your monthly kWh to see roughly what capacity costs add to your bill in each year.

**What this can show:** the size and timing of the jump, how close the grid is running to its reserve target, and a rough dollar figure for a household.
**What it can't:** an exact bill. The estimate is a simple average and real bills differ by utility (see caveats).

How the bill estimate works:
1. Capacity cost per kWh = total auction cost for the delivery year / PJM annual load (EIA-930, nearest complete year).
2. Monthly add = that cost per kWh x your monthly kWh.

Caveats carried onto the page:
- This spreads capacity cost evenly over every kWh used by every customer class. Households use more of their power at peak times than factories do, so their true share is likely higher.
- Utilities pass capacity costs through with lags and hedges, and some PJM utilities buy capacity outside the auction, so not every PJM customer saw the change on the same date or at the same size.
- 2026/27 and 2027/28 use 2025 load, the latest complete year.
- Event notes come from PJM reports and need a final source check before they go on the page (listed at the end)."""),
("code", SETUP + '''p = pd.read_csv(CLEAN / "pjm_bra_rto_prices.csv")
e = pd.read_csv(CLEAN / "eia930_ba_annual.csv").query("ba == 'PJM' and complete_year").set_index("year")
u = pd.read_csv(CLEAN / "eia861_utility_sales.csv")

y0 = p.delivery_year_start
p["load_year"] = y0.clip(e.index.min(), e.index.max())
p["load_gwh"] = p.load_year.map(e.total_gwh_scaled)
p["cents_per_kwh"] = p.cleared_cost_usd_billion * 1e9 / (p.load_gwh * 1e6) * 100
r = u[(u.ba_code == "PJM") & (u.year == 2025)]
TYPICAL = r.res_mwh.sum() * 1000 / r.res_customers.sum() / 12
print(f"Typical PJM household (2025): {TYPICAL:.0f} kWh/month")
p["usd_month_typical"] = p.cents_per_kwh * TYPICAL / 100
display(p[["delivery_year", "rto_clearing_price_usd_per_mw_day", "cleared_cost_usd_billion", "rpm_reserve_margin_pct",
           "load_gwh", "cents_per_kwh", "usd_month_typical"]].round(2))
print("PJM peak load (EIA-930):", e.peak_mw.astype(int).to_dict())'''),
("md", "## Key numbers"),
("code", '''a, b = p.set_index("delivery_year").loc["2024/25"], p.set_index("delivery_year").loc["2025/26"]
last = p.iloc[-1]
print(f"2024/25 to 2025/26: {a.rto_clearing_price_usd_per_mw_day:.2f} to {b.rto_clearing_price_usd_per_mw_day:.2f} $/MW-day "
      f"({b.rto_clearing_price_usd_per_mw_day / a.rto_clearing_price_usd_per_mw_day:.1f}x), total cost {a.cleared_cost_usd_billion} to {b.cleared_cost_usd_billion} $B")
print(f"Typical household: about ${a.usd_month_typical:.2f} to ${b.usd_month_typical:.2f} a month ({b.usd_month_typical - a.usd_month_typical:+.2f})")
print(f"Reserve margin: {p.rpm_reserve_margin_pct.max():.1f}% at its high, {last.rpm_reserve_margin_pct:.1f}% for {last.delivery_year}")
print(f"PJM peak load rose from {e.peak_mw.min():,.0f} MW ({e.peak_mw.idxmin()}) to {e.peak_mw.iloc[-1]:,.0f} MW ({e.index[-1]})")'''),
("md", "## Static figure for the proposal (saved as an image)"),
("code", '''x = p.delivery_year_start.values
fig, (ax, bx) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw=dict(height_ratios=[1.35, 1], hspace=0.32))
xs = np.append(x, x[-1] + 1); ys = np.append(p.rto_clearing_price_usd_per_mw_day.values, p.rto_clearing_price_usd_per_mw_day.values[-1])
ax.step(xs, ys, where="post", color=ORANGE, lw=2.4)
ax.fill_between(xs, ys, step="post", color=ORANGE, alpha=0.08)
for xi, v in zip(x, p.rto_clearing_price_usd_per_mw_day):
    ax.text(xi + 0.5, v + 8, f"${v:,.0f}", ha="center", fontsize=8.5, color=INK)
ax.annotate("2025/26 auction (July 2024):\\nprice rose about 9x", (2025.05, 230), xytext=(2020.6, 245), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(2026.05, 150, "price cap and floor\\nset by a 2025 settlement", fontsize=8.5, color=INK2)
ax.text(2022.2, 85, "three years at $50 or less", fontsize=9, color=INK2)
ax.set_ylim(0, 380); ax.set_ylabel("clearing price ($/MW-day)")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
ax.set_title("PJM capacity prices jumped ninefold in one auction and kept rising", loc="left", fontsize=12, fontweight="bold", pad=24)
ax.text(0, 1.01, f"Base Residual Auction clearing price, RTO zone. Reserve margin fell from {p.rpm_reserve_margin_pct.max():.0f}% "
        f"to {p.rpm_reserve_margin_pct.iloc[-1]:.0f}% as peak load climbed.", transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")

bx.bar(x + 0.5, p.usd_month_typical, width=0.7, color=[NEUTRAL if v < 2025 else ORANGE for v in x])
for xi, v in zip(x, p.usd_month_typical):
    bx.text(xi + 0.5, v + 0.4, f"${v:.0f}", ha="center", fontsize=8.5, color=INK)
bx.set_ylabel("$ per month")
bx.set_xticks(x + 0.5, p.delivery_year, rotation=0, fontsize=8.5)
bx.grid(axis="y", color=GRID, lw=0.8); bx.set_axisbelow(True)
for sp in ["top", "right"]: bx.spines[sp].set_visible(False)
bx.set_title(f"Rough capacity cost in a {TYPICAL:.0f} kWh/month household bill", loc="left", fontsize=12, fontweight="bold", pad=18)
bx.text(0, 1.01, "Total auction cost spread evenly over PJM load. In the interactive version a slider sets the kWh.",
        transform=bx.transAxes, fontsize=9, color=INK2, va="bottom")
fig.text(0.01, 0.01, "Source: PJM 2027/28 BRA report (Table 2), EIA Form 930 (PJM load), EIA Form 861 (household usage). "
         "Estimate, not a tariff: actual pass-through varies by utility and households likely carry a larger share.", fontsize=8, color=INK2)
fig.savefig(ROOT / "images" / "prototype_f_capacity_bill.png", dpi=160, bbox_inches="tight")
plt.show()'''),
("md", """## Interactive prototype (usage slider)
Drag the slider to set your monthly usage. The bars and the headline update to show roughly what capacity costs add to a bill at that usage in each delivery year. Hover the step chart for reserve margin and cleared capacity.
Saved as `sgarimella/prototype_f_capacity_bill.html`."""),
("code", '''import plotly.graph_objects as go
from plotly.subplots import make_subplots

lab = p.delivery_year.tolist()
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.58, 0.42], vertical_spacing=0.1,
                    subplot_titles=("Capacity auction clearing price ($/MW-day)", "What it adds to your monthly bill (rough estimate)"))
fig.add_trace(go.Scatter(x=list(xs), y=list(ys), mode="lines", line=dict(color=ORANGE, width=3, shape="hv"),
                         fill="tozeroy", fillcolor="rgba(235,104,52,0.08)", hoverinfo="skip", showlegend=False), 1, 1)
fig.add_trace(go.Scatter(x=(x + 0.5).tolist(), y=p.rto_clearing_price_usd_per_mw_day.tolist(), mode="markers+text",
    text=[f"${v:,.0f}" for v in p.rto_clearing_price_usd_per_mw_day], textposition="top center", marker=dict(size=7, color=ORANGE),
    customdata=p[["delivery_year", "rpm_reserve_margin_pct", "cleared_ucap_mw", "cleared_cost_usd_billion"]].values.tolist(),
    hovertemplate="<b>%{customdata[0]}</b><br>$%{y:,.2f}/MW-day<br>reserve margin %{customdata[1]}%<br>"
                  "%{customdata[2]:,.0f} MW cleared, $%{customdata[3]}B total<extra></extra>", showlegend=False), 1, 1)

def month(kwh):
    return (p.cents_per_kwh * kwh / 100).round(2).tolist()
def headline(kwh):
    m = p.cents_per_kwh * kwh / 100
    return (f"At {kwh:,} kWh a month, capacity costs went from about ${m.iloc[7]:.0f} (2024/25) "
            f"to ${m.iloc[8]:.0f} (2025/26) and ${m.iloc[-1]:.0f} (2027/28) a month")
start = int(round(TYPICAL / 50) * 50)
fig.add_trace(go.Bar(x=(x + 0.5).tolist(), y=month(start), text=[f"${v:.0f}" for v in month(start)], textposition="outside",
                     marker_color=[NEUTRAL if v < 2025 else ORANGE for v in x], hovertemplate="%{x}: $%{y:.2f}/month<extra></extra>",
                     showlegend=False), 2, 1)
BAR = len(fig.data) - 1
steps = []
for kwh in range(200, 2050, 50):
    steps.append(dict(label=f"{kwh}", method="update",
                      args=[{"y": [month(kwh)], "text": [[f"${v:.0f}" for v in month(kwh)]]}, {"title.text": headline(kwh)}, [BAR]]))
fig.add_annotation(x=2027.95, y=150, text="price cap and floor set by a 2025 settlement", showarrow=False, xanchor="right", font=dict(size=10, color=INK2), row=1, col=1)
fig.add_annotation(x=2025.05, y=250, ax=-120, ay=-10, text="2025/26 auction (July 2024): about 9x", font=dict(size=11), row=1, col=1)
fig.add_annotation(x=2023.5, y=95, text="three years at $50 or less", showarrow=False, font=dict(size=10, color=INK2), row=1, col=1)
fig.update_xaxes(tickvals=(x + 0.5).tolist(), ticktext=lab, range=[2017, 2028], gridcolor=GRID)
fig.update_yaxes(range=[0, 390], gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="$ per month", gridcolor=GRID, rangemode="tozero", row=2, col=1)
fig.update_layout(height=720, paper_bgcolor=SURF, plot_bgcolor=SURF, margin=dict(l=60, r=30, t=90, b=170),
                  title=dict(text=headline(start), x=0.01, font=dict(size=15)),
                  sliders=[dict(active=[s["label"] for s in steps].index(str(start)), y=-0.06, x=0.0, len=1.0,
                                currentvalue=dict(prefix="Your monthly usage (kWh): "), steps=steps)])
fig.add_annotation(text=f"Typical PJM household uses about {TYPICAL:.0f} kWh/month (EIA-861, 2025). Estimate spreads total auction cost "
                        "over all PJM load; real pass-through varies by utility.",
                   xref="paper", yref="paper", x=0, y=-0.3, showarrow=False, font=dict(size=10, color=INK2), xanchor="left")
fig.write_html(ROOT / "sgarimella" / "prototype_f_capacity_bill.html", include_plotlyjs=True, config={"displayModeBar": False})
fig.show()'''),
("md", """## Reading so far
- Capacity prices sat at $50/MW-day or less for three years, then jumped about ninefold (from $28.92 to $269.92) in the 2025/26 auction and rose again to about $330 in the next two.
- The reserve margin in the auction results fell from the low 20s to about 14% for 2027/28 while PJM peak load rose. That is the grid strain residents describe, in the grid operator's own numbers.
- For a typical PJM household (about 850 kWh a month) the rough estimate goes from about $2 a month in 2024/25 to about $15 in 2025/26, roughly $12 more. Part of the jump is a return from unusually low years: before 2022/23 the same estimate ran $7 to $12 a month.

Event notes to source-check before the final page:
- The 2025/26 auction was held in July 2024 (PJM BRA report).
- The cap and floor come from a settlement approved by FERC in 2025; the repo's source note gives $325 and $175 for 2026/27 to 2028/29. The cleared prices in the table ($329.17, $333.44) are slightly above $325, so check which basis each number is quoted in before putting the cap value on the chart.
- Why the price rose: PJM and its Independent Market Monitor attributed it to load forecast growth (largely data centers), plant retirements and market rule changes. Quote their reports directly rather than our summary.

Next steps: show the data center share of PJM's load forecast if we can get the forecast tables, and compare a few utilities' actual capacity line items against this estimate."""),
]

nb(E, OUT / "prototype_e_price_scatter.ipynb")
nb(F, OUT / "prototype_f_capacity_bill.ipynb")
print("wrote", OUT / "prototype_e_price_scatter.ipynb", "and", OUT / "prototype_f_capacity_bill.ipynb")
