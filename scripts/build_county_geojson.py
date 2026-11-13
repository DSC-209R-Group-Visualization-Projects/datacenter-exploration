"""Simplified county polygons (WGS84) for the web map: data/clean/counties_simplified.geojson. Needs geopandas (.pylibs)."""
import sys

from common import CLEAN, RAW, ROOT

sys.path.insert(0, str(ROOT / ".pylibs"))
import geopandas as gpd  # noqa: E402

g = gpd.read_file(RAW / "census_cb/county_5m/cb_2025_us_county_5m.shp")[["GEOID", "STATEFP", "NAMELSAD", "geometry"]]
g = g[g["STATEFP"] <= "56"].rename(columns={"GEOID": "geoid", "NAMELSAD": "name"})
g["geometry"] = g.geometry.simplify(0.01, preserve_topology=True)
g[["geoid", "name", "geometry"]].to_file(CLEAN / "counties_simplified.geojson", driver="GeoJSON", COORDINATE_PRECISION=3)
print(len(g), round((CLEAN / "counties_simplified.geojson").stat().st_size / 1e6, 1), "MB")
