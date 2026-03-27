import json
import math
import pandas as pd
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from pyproj import Transformer, CRS

geojson_path = "../KG_file/NewYork7+NewJersey6.geojson"
Foursquare_path = "../KG_file/Foursquare_NewYork.csv"

with open(geojson_path, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

crs_wgs84 = CRS.from_epsg(4326)

crs_equal_area = CRS.from_epsg(6933)

transformer = Transformer.from_crs(crs_wgs84, crs_equal_area, always_xy=True)

min_lat = min_lon = float("inf")
max_lat = max_lon = float("-inf")

region_geoms_projected = []

for feature in geojson_data["features"]:
    geom = shape(feature["geometry"])

    bounds = geom.bounds
    min_lon = min(min_lon, bounds[0])
    min_lat = min(min_lat, bounds[1])
    max_lon = max(max_lon, bounds[2])
    max_lat = max(max_lat, bounds[3])

    projected_geom = transform(transformer.transform, geom)
    region_geoms_projected.append(projected_geom)

region_union = unary_union(region_geoms_projected)
total_area_m2 = region_union.area
total_area_km2 = total_area_m2 / 1e6

df = pd.read_csv(Foursquare_path)

lat_col = "poi_lat"
lon_col = "poi_lon"

df = df[[lat_col, lon_col]].dropna().drop_duplicates()

points = [
    transformer.transform(lon, lat)
    for lon, lat in zip(df[lon_col], df[lat_col])
]

points = list(set(points))

if len(points) < 2:
    raise ValueError("The number of POIs is less than 2")

def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

def convex_hull(points):
    pts = sorted(points)
    if len(pts) <= 1:
        return pts

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]

hull = convex_hull(points)

def dist2(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2

def polygon_area2(a, b, c):
    return abs(cross(a, b, c))

def farthest_pair(points):
    n = len(points)

    if n == 1:
        return points[0], points[0], 0.0
    if n == 2:
        d2 = dist2(points[0], points[1])
        return points[0], points[1], math.sqrt(d2)

    j = 1
    max_d2 = 0
    best_pair = (points[0], points[0])

    for i in range(n):
        ni = (i + 1) % n
        while True:
            nj = (j + 1) % n
            cur = polygon_area2(points[i], points[ni], points[j])
            nxt = polygon_area2(points[i], points[ni], points[nj])
            if nxt > cur:
                j = nj
            else:
                break

        d2_1 = dist2(points[i], points[j])
        if d2_1 > max_d2:
            max_d2 = d2_1
            best_pair = (points[i], points[j])

        d2_2 = dist2(points[ni], points[j])
        if d2_2 > max_d2:
            max_d2 = d2_2
            best_pair = (points[ni], points[j])

    return best_pair[0], best_pair[1], math.sqrt(max_d2)

p1, p2, diameter_m = farthest_pair(hull)

radius_m = diameter_m / 2
circle_area_m2 = math.pi * (radius_m ** 2)
circle_area_km2 = circle_area_m2 / 1e6

coverage_ratio = 0 if total_area_km2 == 0 else (circle_area_km2 / total_area_km2) * 100

print(f"lat scope: {min_lat:.6f} ~ {max_lat:.6f}")
print(f"lon scope: {min_lon:.6f} ~ {max_lon:.6f}")
print(f"number of regions: {len(geojson_data.get('features', []))}")
print(f"total area: {total_area_km2:.2f} km²")
print(f"circle-like area: {circle_area_km2:.2f} km²")
print(f"coverage ratio: {coverage_ratio:.2f}%")