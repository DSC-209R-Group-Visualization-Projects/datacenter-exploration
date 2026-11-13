"""Shared paths and helpers for the cleaning scripts (run with python3 -I from the repo root)."""
import re
import struct
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
CLEAN = ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

# 50 states + DC (FIPS 01-56 minus the unused gaps); territories are dropped.
STATE_FIPS_MAX = "56"


def read_dbf(path):
    """Minimal dBase reader so we can use shapefile attribute tables without geopandas."""
    with open(path, "rb") as f:
        head = f.read(32)
        n, header_len, rec_len = struct.unpack("<IHH", head[4:12])
        fields = []
        while True:
            d = f.read(32)
            if d[0] == 0x0D:
                break
            fields.append((d[:11].split(b"\0")[0].decode(), d[16]))
        f.seek(header_len)
        rows = []
        for _ in range(n):
            rec = f.read(rec_len)[1:]
            off, row = 0, {}
            for name, length in fields:
                row[name] = rec[off:off + length].decode("utf-8", "replace").strip()
                off += length
            rows.append(row)
    return pd.DataFrame(rows)


# Counties renamed after the older sources were published: (state, normalized old name) -> normalized new name.
COUNTY_ALIASES = {("SD", "shannon"): "oglalalakota"}


def norm_county(name, state=None):
    """Normalize a county name for matching across sources (EIA, data center CSV, Census).

    Accents are stripped and spaces removed so "La Salle"/"LaSalle" and "Doña Ana"/"Dona Ana" agree.
    "city" is kept: Virginia/Maryland/Missouri/Nevada independent cities are distinct from counties.
    """
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower().strip()
    s = s.replace("&", "and").replace(".", "").replace("'", "")
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\s+(county|parish|borough|census area|municipality|planning region)$", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return COUNTY_ALIASES.get((state, s), s)


def num(series):
    """Coerce to numeric, treating thousands separators and placeholder strings as missing."""
    s = series.astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.strip()
    return pd.to_numeric(s, errors="coerce")


def read_shp_polygons(path):
    """Read polygon shapefile records as (bbox, rings) without geopandas. Rings are Nx2 numpy arrays.

    Record order matches the .dbf, so rows can be zipped with read_dbf(). Null shapes yield (None, []).
    """
    import numpy as np

    data = Path(path).read_bytes()
    pos, out = 100, []
    while pos < len(data):
        content_len = struct.unpack(">i", data[pos + 4:pos + 8])[0] * 2
        rec = data[pos + 8:pos + 8 + content_len]
        pos += 8 + content_len
        stype = struct.unpack("<i", rec[:4])[0]
        if stype == 0:
            out.append((None, []))
            continue
        bbox = struct.unpack("<4d", rec[4:36])
        nparts, npts = struct.unpack("<2i", rec[36:44])
        parts = list(struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])) + [npts]
        pts = np.frombuffer(rec, dtype="<f8", count=2 * npts, offset=44 + 4 * nparts).reshape(npts, 2)
        out.append((bbox, [pts[parts[i]:parts[i + 1]] for i in range(nparts)]))
    return out


def point_in_rings(x, y, rings):
    """Even-odd ray casting across all rings (handles holes and multipart polygons)."""
    import numpy as np

    inside = False
    for r in rings:
        x0, y0 = r[:-1, 0], r[:-1, 1]
        x1, y1 = r[1:, 0], r[1:, 1]
        cond = (y0 > y) != (y1 > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (x1 - x0) * (y - y0) / (y1 - y0) + x0
        if np.count_nonzero(cond & (x < xint)) % 2 == 1:
            inside = not inside
    return inside


def locate_counties(lons, lats, shp_path, dbf_path):
    """Return a GEOID (or None) for each point by testing it against county polygons."""
    import numpy as np

    attrs = read_dbf(dbf_path)
    polys = read_shp_polygons(shp_path)
    boxes = np.array([b if b else (1e9, 1e9, -1e9, -1e9) for b, _ in polys])
    geoids = attrs["GEOID"].values
    res = []
    for x, y in zip(lons, lats):
        if np.isnan(x) or np.isnan(y):
            res.append(None)
            continue
        cand = np.where((boxes[:, 0] <= x) & (x <= boxes[:, 2]) & (boxes[:, 1] <= y) & (y <= boxes[:, 3]))[0]
        hit = next((geoids[i] for i in cand if point_in_rings(x, y, polys[i][1])), None)
        res.append(hit)
    return res
