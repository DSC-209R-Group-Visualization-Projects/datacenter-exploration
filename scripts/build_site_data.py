"""Write the small JSON files the D3 site (site/) reads.

Numbers match prototype.ipynb. Run from the repo root:
    PYTHONPATH=.pylibs python3 scripts/build_site_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "site" / "data"
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
