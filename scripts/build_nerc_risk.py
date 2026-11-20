"""NERC resource adequacy risk by balancing authority: data/clean/nerc_ltra_risk.csv.

Source: NERC 2025 Long-Term Reliability Assessment (published January 2026), Table 1 "Capacity and Energy Risk Assessment
Area Summary" and Figure 1 (data/raw/nerc/NERC_LTRA_2025.pdf, pages 7-8). The yearly ratings are colored cells in the PDF,
so they are transcribed here by hand. Each balancing authority in ba_regions.geojson is assigned to the NERC assessment
area that contains it (Alaska and Hawaii are not assessed).
"""
import pandas as pd

from common import CLEAN

YEARS = [2026, 2027, 2028, 2029, 2030]
# N = normal, E = elevated, H = high risk; one letter per year 2026-2030 (US assessment areas only)
RISK = {
    "MISO": "NEHHH", "SPP": "EEEEE", "PJM": "EEEHH", "ERCOT": "EEEHH",
    "New England": "NNNEE", "New York": "EEEEE",
    "SERC-East": "NEEEE", "SERC-Central": "NNNNN", "SERC-Southeast": "NNNNN", "SERC-Florida": "NNNNN",
    "WECC-Northwest": "NNNHH", "WECC-Basin": "EEEHH", "WECC-Rocky Mountain": "NNNNN",
    "WECC-Southwest": "NNNNN", "WECC-California": "NNNNN",
}
AREA = {
    "MISO": "MISO", "SWPP": "SPP", "PJM": "PJM", "ERCO": "ERCOT", "ISNE": "New England", "NYIS": "New York",
    "DUK": "SERC-East", "CPLE": "SERC-East", "SC": "SERC-East", "SCEG": "SERC-East",
    "TVA": "SERC-Central", "LGEE": "SERC-Central", "AECI": "SERC-Central",
    "SOCO": "SERC-Southeast", "FPL": "SERC-Florida", "FPC": "SERC-Florida", "SEC": "SERC-Florida",
    "BPAT": "WECC-Northwest", "AVA": "WECC-Northwest", "PACW": "WECC-Northwest", "PGE": "WECC-Northwest",
    "PSEI": "WECC-Northwest", "TPWR": "WECC-Northwest", "CHPD": "WECC-Northwest", "GCPD": "WECC-Northwest",
    "NWMT": "WECC-Northwest", "WAUW": "WECC-Northwest",
    "IPCO": "WECC-Basin", "PACE": "WECC-Basin",
    "PSCO": "WECC-Rocky Mountain", "WACM": "WECC-Rocky Mountain",
    "AZPS": "WECC-Southwest", "EPE": "WECC-Southwest", "PNM": "WECC-Southwest", "NEVP": "WECC-Southwest", "WALC": "WECC-Southwest",
    "CISO": "WECC-California",
}
NAMES = {"N": "Normal", "E": "Elevated", "H": "High"}

rows = [{"ba_code": ba, "nerc_area": area, **{f"risk_{y}": NAMES[RISK[area][i]] for i, y in enumerate(YEARS)}}
        for ba, area in AREA.items()]
out = pd.DataFrame(rows)
out.to_csv(CLEAN / "nerc_ltra_risk.csv", index=False)
print(out.groupby("nerc_area").size().to_dict())
