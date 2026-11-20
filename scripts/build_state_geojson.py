"""Simplified state polygons (WGS84) for the web maps: data/clean/states_simplified.geojson. Needs geopandas (.pylibs)."""
import sys

from common import CLEAN, RAW, ROOT

sys.path.insert(0, str(ROOT / ".pylibs"))
import geopandas as gpd  # noqa: E402

g = gpd.read_file(RAW / "census_cb/state_5m/cb_2025_us_state_5m.shp")[["STATEFP", "STUSPS", "NAME", "geometry"]]
g = g[g["STATEFP"] <= "56"].rename(columns={"STATEFP": "fips", "STUSPS": "state", "NAME": "name"})
g["geometry"] = g.geometry.simplify(0.01, preserve_topology=True)
g.to_file(CLEAN / "states_simplified.geojson", driver="GeoJSON", COORDINATE_PRECISION=3)
print(len(g), round((CLEAN / "states_simplified.geojson").stat().st_size / 1e6, 2), "MB")
