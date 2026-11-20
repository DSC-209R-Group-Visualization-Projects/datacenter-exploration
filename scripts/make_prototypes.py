"""Generate the two prototype notebooks in data/ (run: PYTHONPATH=.pylibs python3 scripts/make_prototypes.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".pylibs"))
import nbformat as nbf  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "jppolizzi"
SETUP = '''import sys, warnings
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name in ("data", "jppolizzi") else Path.cwd()
sys.path[:0] = [str(ROOT / ".pylibs"), str(ROOT / "scripts")]
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import proto_data as pdx
CLEAN = ROOT / "data" / "clean"
'''


def nb(cells, path):
    n = nbf.v4.new_notebook()
    n.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1]) for c in cells]
    n.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbf.write(n, path)


# ---------------------------------------------------------------- Prototype A: map (kept simple on purpose)
A = [
("md", """# Prototype A: data centers and water stress
Step 1 of the map, kept small on purpose: every data center in the database, over county water stress.
More layers (price change, restrictions, planned capacity) get added one at a time once this reads well.

- **Dots:** every facility with usable coordinates, all statuses (operating, planned, stalled, cancelled). Hover for name, city, status and MW.
- **Shading:** share of the county's area in High or Extremely High baseline water stress (WRI Aqueduct 4.0, one 2023 snapshot, not a trend).
- Water stress shows where water is scarce, not whether data centers caused it."""),
("code", SETUP + '''import plotly.graph_objects as go, geopandas as gpd, json

c = pdx.county_frame()
geo = gpd.read_file(CLEAN / "counties_simplified.geojson")
d = pd.read_csv(CLEAN / "datacenters.csv")
d = d[d.coord_ok]
print(len(d), "data centers plotted;", len(c), "counties shaded")'''),
("code", '''fig = go.Figure()
fig.add_trace(go.Choropleth(geojson=json.loads(geo.to_json()), locations=c["geoid"], featureidkey="properties.geoid", z=c["share_high_or_extreme"] * 100,
    colorscale=[[0, "#f7fbff"], [1, "#2171b5"]], zmin=0, zmax=100, marker_line_width=0, showscale=True,
    colorbar=dict(title="% of county in<br>high/extreme<br>water stress", len=0.5),
    text=c["county_name"] + ", " + c["state"], hovertemplate="%{text}<br>%{z:.0f}% high/extreme stress<extra></extra>"))
fig.add_trace(go.Scattergeo(lon=d["lon"], lat=d["lat"], mode="markers", name="data center (any status)",
    marker=dict(size=5, color="#d94801", opacity=0.75, line=dict(width=0)),
    text=d["facility_name"].fillna("(unnamed)") + "<br>" + d["city"].fillna("") + ", " + d["state"] + " | " + d["status"].fillna("status unknown") +
         "<br>" + d["mw"].map(lambda v: "MW not reported" if pd.isna(v) else f"{v:,.0f} MW"), hovertemplate="%{text}<extra></extra>"))
fig.update_layout(height=620, margin=dict(l=0, r=0, t=50, b=0), showlegend=True, legend=dict(x=0.02, y=0.08, bgcolor="rgba(255,255,255,0.8)"),
    title=dict(text="Data center locations over county water stress (WRI Aqueduct 4.0 baseline)", x=0.02, font=dict(size=16)),
    geo=dict(scope="usa", projection=dict(type="albers usa"), showland=False, showlakes=False, showframe=False))
fig.write_html(ROOT / "jppolizzi" / "prototype_a_map.html", include_plotlyjs=True, config={"displayModeBar": False})
fig.show()'''),
("md", "Saved as `jppolizzi/prototype_a_map.html`. Facilities without coordinates are skipped. Next layer to add (one at a time): planned capacity, then restrictions."),
("md", """## Grid strain: balancing authority regions
The grid is run by **balancing authorities** (BAs), which balance supply and demand hour by hour (PJM, MISO, ERCOT, ...). EIA-930 reports hourly demand for each, so this is the unit for grid strain.

- **Regions** are approximate: built from the counties each BA's utilities serve (EIA-861, `scripts/build_ba_regions.py`). A county served by several BAs goes to the one whose utility has the most residential customers, so small BAs mostly disappear into their neighbours.
- **Shading:** growth in annual peak demand, 2019 to 2025 (EIA-930). Grey = no complete 2019 and 2025 data.
- **Dots:** operating (blue) and planned (orange) data centers.
- Peak growth also reflects weather, population and electrification, so this map does not separate the data center share."""),
("code", '''g = pdx.ba_grid_table().set_index("ba")
regions = gpd.read_file(CLEAN / "ba_regions.geojson").merge(g[["peak_base_mw", "peak_end_mw", "peak_growth_pct", "dc_operating"]], left_on="ba_code", right_index=True, how="left")
regions["dc_operating"] = regions["dc_operating"].fillna(0)
regions["label"] = (regions["ba_name"].fillna(regions["ba_code"]) + " (" + regions["ba_code"] + ")<br>" +
    regions.apply(lambda r: "no complete 2019/2025 data" if pd.isna(r.peak_growth_pct) else
                  f"peak {r.peak_base_mw / 1000:,.1f} GW (2019) to {r.peak_end_mw / 1000:,.1f} GW (2025), {r.peak_growth_pct:+.1f}%", axis=1) +
    "<br>operating data centers in served counties: " + regions["dc_operating"].astype(int).astype(str))
has = regions[regions.peak_growth_pct.notna()]; none = regions[regions.peak_growth_pct.isna()]

fig = go.Figure()
fig.add_trace(go.Choropleth(geojson=json.loads(none.to_json()), locations=none["ba_code"], featureidkey="properties.ba_code", z=[0] * len(none),
    colorscale=[[0, "#e0e0e0"], [1, "#e0e0e0"]], showscale=False, marker_line_color="white", marker_line_width=0.8, text=none["label"], hovertemplate="%{text}<extra></extra>"))
fig.add_trace(go.Choropleth(geojson=json.loads(has.to_json()), locations=has["ba_code"], featureidkey="properties.ba_code", z=has["peak_growth_pct"],
    colorscale=[[0, "#fcd9c8"], [0.5, "#ef6548"], [1, "#7f0000"]], zmin=0, zmax=20, marker_line_color="white", marker_line_width=0.8,
    colorbar=dict(title="peak demand<br>growth 2019-25 (%)", len=0.5, ticksuffix="%", tickvals=[0, 5, 10, 15, 20], ticktext=["0% or less", "5%", "10%", "15%", "20%+"]), text=has["label"], hovertemplate="%{text}<extra></extra>"))
d2 = d[d.status_group.isin(["operating", "pipeline"])]
for grp, color, name in (("pipeline", "#e8833a", "planned data center"), ("operating", "#1f5fa8", "operating data center")):
    s_ = d2[d2.status_group == grp]
    fig.add_trace(go.Scattergeo(lon=s_["lon"], lat=s_["lat"], mode="markers", name=name, marker=dict(size=4, color=color, opacity=0.8, line=dict(width=0)),
        text=s_["facility_name"].fillna("(unnamed)") + "<br>" + s_["city"].fillna("") + ", " + s_["state"], hovertemplate="%{text}<extra></extra>"))
big = regions.nlargest(10, "n_counties").copy()
pt = big.to_crs("EPSG:5070").geometry.representative_point().to_crs("EPSG:4326")
fig.add_trace(go.Scattergeo(lon=pt.x, lat=pt.y, mode="text", text=big["ba_code"], textfont=dict(size=12, color="#111", family="Arial Black"), hoverinfo="skip", showlegend=False))
fig.update_layout(height=620, margin=dict(l=0, r=0, t=50, b=0), legend=dict(x=0.02, y=0.08, bgcolor="rgba(255,255,255,0.8)"),
    title=dict(text="Grid regions (balancing authorities): peak demand growth 2019-2025 and data center locations", x=0.02, font=dict(size=16)),
    geo=dict(scope="usa", projection=dict(type="albers usa"), showland=True, landcolor="#e6e6e6", showlakes=False, showframe=False,
             showsubunits=True, subunitcolor="#ffffff", subunitwidth=0.4))
fig.add_annotation(text="grey = no region assigned or no complete 2019/2025 data", x=0.02, y=0.0, xref="paper", yref="paper", showarrow=False, font=dict(size=11, color="#555"), xanchor="left")
fig.write_html(ROOT / "jppolizzi" / "prototype_a_grid_map.html", include_plotlyjs=True, config={"displayModeBar": False})
fig.show()
display(g.sort_values("dc_operating", ascending=False).head(10)[["peak_base_mw", "peak_end_mw", "peak_growth_pct", "dc_operating"]].round(1))'''),
("md", "Saved as `jppolizzi/prototype_a_grid_map.html`. Next: test whether BAs with more data centers grew faster (Prototype B), and add PJM capacity prices."),
]

# ---------------------------------------------------------------- Prototype B: water-only scorecard (facility-in-basin)
B = [
("md", """# Prototype B: water stress scorecard
**Research question:** Do data centers stress water, and where is the build-out landing?

Water only for now. Each data center is placed in its river basin from its coordinates (`scripts/assign_basins.py`), so no county or zip step sits between the facility and the water data.

**Data:** WRI Aqueduct 4.0 baseline water stress (one 2023 snapshot); the project data center database; county population split across basins by overlap area (baseline for "where people live").
**What this can show:** whether data centers sit in more water-stressed basins than the country's population does (*siting*). **What it can't:** whether they changed water stress, or how much water they use (mostly unreported).
**Rating scale:** supported / not supported / mixed / can't tell. Correlation, not causation."""),
("code", SETUP + '''import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportion_confint

ORDER = ["Low", "Low-medium", "Medium-high", "High", "Extremely high", "Arid, low use"]
HIGH = ["High", "Extremely high"]
d = pd.read_csv(CLEAN / "datacenters.csv").merge(pd.read_csv(CLEAN / "datacenters_basin.csv"), on="facility_id")
base = pd.read_csv(CLEAN / "basin_population.csv").set_index("stress_group")
d = d[d.coord_ok & d.status_group.isin(["operating", "pipeline"])]
no_basin = d.stress_group.isna() | d.stress_group.eq("No data")
print(f"{len(d)} operating or planned facilities with coordinates; {int(no_basin.sum())} have no basin data "
      f"(mostly metro Atlanta and parts of Virginia, where Aqueduct has gaps) and are left out")
d = d[~no_basin]
op = d[d.status_group == "operating"]; pl = d[d.status_group == "pipeline"]'''),
("md", "## Where do facilities sit, compared with where people live?"),
("code", '''pct = lambda s: s.value_counts(normalize=True).reindex(ORDER).fillna(0) * 100
tab = pd.DataFrame({"operating facilities": pct(op.stress_group), "planned facilities": pct(pl.stress_group),
                    "US population": base["population_share"].reindex(ORDER) * 100, "US land area": base["land_share"].reindex(ORDER) * 100})
display(tab.round(1))

def high_share(df): return (df.stress_group.isin(HIGH)).sum(), len(df)
k, n = high_share(op); lo_, hi_ = proportion_confint(k, n, method="wilson")
pop_high = base.loc[HIGH, "population_share"].sum() * 100
print(f"Operating: {k / n * 100:.0f}% of facilities (95% CI {lo_ * 100:.0f}-{hi_ * 100:.0f}%, n={n}) are in High/Extremely high basins vs {pop_high:.0f}% of the US population")
k2, n2 = high_share(pl); lo2, hi2 = proportion_confint(k2, n2, method="wilson")
print(f"Planned:   {k2 / n2 * 100:.0f}% (95% CI {lo2 * 100:.0f}-{hi2 * 100:.0f}%, n={n2})")
mw = d.groupby(["stress_group", "status_group"])["mw"].sum().unstack().reindex(ORDER).fillna(0)
mw_pct = mw / mw.sum() * 100
display(mw.round(0))
print(f"Reported MW in High/Extremely high basins: operating {mw_pct.loc[HIGH, 'operating'].sum():.0f}%, planned {mw_pct.loc[HIGH, 'pipeline'].sum():.0f}%  (MW reported for {d.mw.notna().mean() * 100:.0f}% of facilities)")'''),
("md", "## Scorecard figure (saved as an image)"),
("code", '''import textwrap
LAB = ["Low", "Low-\\nmedium", "Medium-\\nhigh", "High", "Extremely\\nhigh", "Arid,\\nlow use"]
fig = plt.figure(figsize=(13, 8.8))
gs = fig.add_gridspec(2, 2, height_ratios=[1.6, 0.8], hspace=0.55, wspace=0.25)
fig.suptitle("Do data centers stress water? Where is the build-out landing?  Prototype scorecard (water only)", fontsize=14, fontweight="bold", y=0.99)
x = np.arange(len(ORDER)); w = 0.27
ax = fig.add_subplot(gs[0, 0])
ax.bar(x - w, tab["US population"], w, color="#9ecae1", label="US population")
ax.bar(x, tab["operating facilities"], w, color="#1f5fa8", label=f"operating data centers (n={len(op)})")
ax.bar(x + w, tab["planned facilities"], w, color="#e8833a", label=f"planned data centers (n={len(pl)})")
ax.set_xticks(x); ax.set_xticklabels(LAB, fontsize=8.5); ax.set_ylabel("% of total"); ax.legend(fontsize=8, frameon=False)
ax.set_xlabel("baseline water stress of the river basin"); ax.set_title("1. Siting: data centers vs. where people live", fontsize=11)
ax = fig.add_subplot(gs[0, 1])
ax.bar(x - w / 2, mw_pct["operating"], w * 1.2, color="#1f5fa8", label=f"operating ({mw.operating.sum() / 1000:.0f} GW reported)")
ax.bar(x + w / 2, mw_pct["pipeline"], w * 1.2, color="#e8833a", label=f"planned ({mw.pipeline.sum() / 1000:.0f} GW reported)")
ax.set_xticks(x); ax.set_xticklabels(LAB, fontsize=8.5); ax.set_ylabel("% of reported MW"); ax.legend(fontsize=8, frameon=False)
ax.set_xlabel("baseline water stress of the river basin"); ax.set_title("2. Capacity: where the reported MW sits", fontsize=11)
ax = fig.add_subplot(gs[1, :]); ax.axis("off")
row = [["Water stress", f"facility in river basin\\n(n={len(op)} operating,\\n{len(pl)} planned)", f"{k / n * 100:.0f}% of operating data centers in\\nHigh/Extremely high basins\\n[{lo_ * 100:.0f}-{hi_ * 100:.0f}%] vs {pop_high:.0f}% of US population",
        "CAN'T TELL", "\\n".join(textwrap.wrap("Snapshot shows siting, not change. Actual data center water use is mostly unreported; cooling type is known for few facilities. MW reported for under half of facilities.", 42))]]
t = ax.table(cellText=row, colLabels=["Concern", "Unit and n", "Estimate", "Rating", "Main caveat"], cellLoc="left", loc="upper center", colWidths=[0.1, 0.19, 0.27, 0.1, 0.34])
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 5.2)
for (i, j), cell in t.get_celld().items():
    if i == 0: cell.set_facecolor("#333"); cell.get_text().set_color("white"); cell.get_text().set_fontweight("bold")
    elif j == 3: cell.set_facecolor("#dddddd"); cell.get_text().set_fontweight("bold")
fig.text(0.5, 0.01, f"Correlation, not causation. Operating = status in database today (no build dates). {int(no_basin.sum())} facilities without basin data excluded. Source: WRI Aqueduct 4.0 (2023), project data center database.", ha="center", fontsize=8, style="italic")
(ROOT / "images").mkdir(exist_ok=True)
fig.savefig(ROOT / "images" / "prototype_b_scorecard.png", dpi=150, bbox_inches="tight", facecolor="white")
pd.DataFrame(row, columns=["concern", "unit and n", "estimate", "rating", "main caveat"]).to_csv(ROOT / "jppolizzi" / "prototype_b_scorecard.csv", index=False)
plt.show()'''),
("md", "Next, one at a time: energy bills, then grid strain. Open decisions: whether to find build dates so growth can be measured; filling the Aqueduct gaps around Atlanta."),
]

nb(A, DATA / "prototype_a_map.ipynb")
nb(B, DATA / "prototype_b_scorecard.ipynb")
print("wrote notebooks")
