import json
from shapely.geometry import shape

geojson_path = "../KG_file/NewYork7+NewJersey6_small.geojson"
with open(geojson_path, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

min_lat = min_lon = float("inf")
max_lat = max_lon = float("-inf")

for feature in geojson_data["features"]:
    geom = shape(feature["geometry"])
    bounds = geom.bounds
    min_lon = min(min_lon, bounds[0])
    min_lat = min(min_lat, bounds[1])
    max_lon = max(max_lon, bounds[2])
    max_lat = max(max_lat, bounds[3])

print(f"lat scope: {min_lat:.6f} ~ {max_lat:.6f}")
print(f"lon scope: {min_lon:.6f} ~ {max_lon:.6f}")
