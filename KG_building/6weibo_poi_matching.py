import pandas as pd
from shapely.geometry import Point, Polygon
from math import radians, sin, cos, sqrt, atan2
from tqdm import tqdm
from scipy.spatial import KDTree
import json

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def load_data(nodes_file, ways_file, relations_file, json_file):
    nodes = pd.read_csv(nodes_file, dtype={"lat": float, "lon": float})
    ways = pd.read_csv(ways_file, dtype={"centroid_lat": float, "centroid_lon": float, "nodes": str})
    relations = pd.read_csv(relations_file)
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    return nodes, ways, relations, json_data

def get_polygon_coords(members, nodes_dict, ways_dict):
    coords = []
    for member in members:
        if member["type"] == "n" and member["ref"] in nodes_dict:
            coords.append(nodes_dict[member["ref"]])
        elif member["type"] == "w" and member["ref"] in ways_dict:
            way_nodes = ways_dict[member["ref"]]
            for node_id in way_nodes:
                if node_id in nodes_dict:
                    coords.append(nodes_dict[node_id])
    return coords

def build_polygon_data(json_data):
    print("Building polygons from JSON data...")
    polygons = {}

    nodes_dict = {node["id"]: (node["lon"], node["lat"]) for node in json_data.get("nodes", [])}
    ways_dict = {way["id"]: way["nodes"] for way in json_data.get("ways", [])}
    print(f"Total nodes loaded: {len(nodes_dict)}")
    print(f"Total ways loaded: {len(ways_dict)}")

    for item in json_data.get("ways", []) + json_data.get("relations", []):
        if item.get("element_type") == "area":
            if "nodes" in item:
                coords = [nodes_dict[node_id] for node_id in item["nodes"] if node_id in nodes_dict]
                if len(coords) >= 4:
                    try:
                        polygons[item["id"]] = Polygon(coords)
                    except ValueError as e:
                        print(f"Error creating polygon for area ID {item['id']}: {e}")
                continue
        if item.get("element_type") == "area":
            print(f"Processing area ID: {item.get('id')} with members: {item.get('members')}")
            coords = get_polygon_coords(item.get("members", []), nodes_dict, ways_dict)
            if len(coords) >= 4:
                try:
                    polygons[item["id"]] = Polygon(coords)
                except ValueError as e:
                    print(f"Error creating polygon for area ID {item['id']}: {e}")

    print(f"Total polygons created: {len(polygons)}")
    return polygons

def build_kd_tree(points):
    return KDTree(points)

def match_weibo_poi(foursquare_data, nodes_tree, nodes_ids, ways_tree, ways_ids, polygons, nodes, ways):
    matches = []
    matched_items = []

    for _, weibo_poi in tqdm(foursquare_data.iterrows(), total=foursquare_data.shape[0], desc="Matching POIs"):
        user_id = weibo_poi["user_id"]
        try:
            poi_lat = float(weibo_poi["poi_lat"])
            poi_lon = float(weibo_poi["poi_lon"])
        except ValueError:
            matches.append({
                "user_id": user_id,
                "poi_lat": weibo_poi["poi_lat"],
                "poi_lon": weibo_poi["poi_lon"],
                "matched_id": None,
                "matched_type": None,
                "distance": None
            })
            continue

        poi_point = Point(poi_lon, poi_lat)
        best_match = None
        best_distance = float("inf")

        dist_node, idx_node = nodes_tree.query((poi_lon, poi_lat))
        dist_node_m = dist_node * 111139
        if idx_node < len(nodes) and pd.notna(nodes.iloc[idx_node]["element_type"]):
            best_match = {
                "user_id": user_id,
                "poi_lat": poi_lat,
                "poi_lon": poi_lon,
                "matched_id": nodes_ids[idx_node],
                "matched_type": "node",
                "matched_lat": nodes.iloc[idx_node]["lat"],
                "matched_lon": nodes.iloc[idx_node]["lon"],
                "distance": dist_node_m
            }
            best_distance = dist_node_m

        for area_id, polygon in polygons.items():
            if polygon.contains(poi_point):
                best_match = {
                    "user_id": user_id,
                    "poi_lat": poi_lat,
                    "poi_lon": poi_lon,
                    "matched_id": area_id,
                    "matched_type": "area",
                    "matched_lat": polygon.centroid.y,
                    "matched_lon": polygon.centroid.x,
                    "distance": 0
                }
                best_distance = 0
                break

        dist_road, idx_road = ways_tree.query((poi_lon, poi_lat))
        dist_road_m = dist_road * 111139
        if idx_road < len(ways) and pd.notna(ways.iloc[idx_road]["element_type"]):
            if dist_road_m < best_distance:
                best_match = {
                    "user_id": user_id,
                    "poi_lat": poi_lat,
                    "poi_lon": poi_lon,
                    "matched_id": ways_ids[idx_road],
                    "matched_type": "road",
                    "matched_lat": ways.iloc[idx_road]["centroid_lat"],
                    "matched_lon": ways.iloc[idx_road]["centroid_lon"],
                    "distance": dist_road_m
                }
                best_distance = dist_road_m

        if best_match:
            matched_items.append(best_match["matched_id"])
            matches.append(best_match)
        else:
            matches.append({
                "user_id": user_id,
                "poi_lat": poi_lat,
                "poi_lon": poi_lon,
                "matched_id": None,
                "matched_type": None,
                "distance": None
            })

    return pd.DataFrame(matches), matched_items


def main():
    foursquare_data = pd.read_csv("../KG_file/Foursquare_NewYork.csv")
    nodes, ways, relations, json_data = load_data("../KG_file/nodes_unfold.csv",
                                                  "../KG_file/way_unfold.csv",
                                                  "../KG_file/relation_unfold.csv",
                                                  "../KG_file/new-york_filtered_level67.json")

    nodes_dict = {node["id"]: (node["lon"], node["lat"]) for node in json_data.get("nodes", [])}

    nodes_tree = build_kd_tree(nodes[["lon", "lat"]].values)

    way_nodes_coords = []
    way_ids = []
    for way in json_data.get("ways", []):
        if "nodes" not in way:
            continue
        for node_id in way["nodes"]:
            if node_id in nodes_dict:
                way_nodes_coords.append(nodes_dict[node_id])
                way_ids.append(way["id"])
    ways_tree = build_kd_tree(way_nodes_coords)

    polygons = build_polygon_data(json_data)


    matches, matched_items = match_weibo_poi(
        foursquare_data, nodes_tree, nodes["id"].values, ways_tree, way_ids, polygons, nodes=nodes, ways=ways
    )

    nodes_filtered = nodes[nodes["id"].isin(matched_items)]
    ways_filtered = ways[ways["id"].isin(matched_items)]
    relations_filtered = relations[relations["id"].isin(matched_items)]

    item_relationships = pd.read_csv("../KG_file/item_relationships_with_distance.csv")
    filtered_item_relationships = item_relationships[item_relationships["id_1"].isin(matched_items) &
                                                     item_relationships["id_2"].isin(matched_items)]

    nodes_filtered.to_csv("../KG_file/nodes_filtered.csv", index=False)
    ways_filtered.to_csv("../KG_file/ways_filtered.csv", index=False)
    relations_filtered.to_csv("../KG_file/relations_filtered.csv", index=False)
    filtered_item_relationships.to_csv("../KG_file/filtered_item_relationships.csv", index=False)

    matches.to_csv("../KG_file/foursquare_newyork_poi_matches_OSM_location.csv", index=False, encoding="utf-8-sig")

    print("Matching completed. Results saved to weibo_poi_matches.csv and filtered data saved.")

if __name__ == "__main__":
    main()
