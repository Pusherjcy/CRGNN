import pandas as pd
import json
import os
from math import radians, cos, sin, sqrt, atan2
from tqdm import tqdm

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def build_relationships(data, distance_threshold_nei, distance_threshold_crs, output_file, region_file, weight_file):
    with open(region_file, "r", encoding="utf-8") as f:
        geo_regions = json.load(f)["features"]

    region_weights = {}
    if weight_file and os.path.exists(weight_file):
        df_weights = pd.read_csv(weight_file)
        for _, row in df_weights.iterrows():
            r1, r2 = str(row['region1']), str(row['region2'])
            weight = float(row['weight'])
            region_weights[(r1, r2)] = weight
            region_weights[(r2, r1)] = weight

    all_items = []
    for item_type in ["nodes", "ways", "relations"]:
        for item in data.get(item_type, []):
            if "element_type" in item:
                item["centroid_lat"] = item.get("centroid_lat", item.get("lat"))
                item["centroid_lon"] = item.get("centroid_lon", item.get("lon"))
                all_items.append({
                    "id": item.get("id"),
                    "type": item_type[0],
                    "lat": item["centroid_lat"],
                    "lon": item["centroid_lon"],
                    "assigned_region": item.get("assigned_region")
                })

    relationships = []
    for i, item1 in enumerate(tqdm(all_items, desc="Building relationships")):
        for j in range(i + 1, len(all_items)):
            item2 = all_items[j]
            if not item1["lat"] or not item1["lon"] or not item2["lat"] or not item2["lon"]:
                continue

            distance = haversine(item1["lat"], item1["lon"], item2["lat"], item2["lon"])
            region1 = item1["assigned_region"]
            region2 = item2["assigned_region"]

            if region1 == region2:
                threshold = distance_threshold_nei
                relationship_value = 1
            else:
                threshold = distance_threshold_crs
                relationship_value = region_weights.get((region1, region2), 0)

            if distance < threshold:
                relationships.append({
                    "id_1": item1["id"],
                    "type_1": item1["type"],
                    "id_2": item2["id"],
                    "type_2": item2["type"],
                    "relationship": relationship_value,
                    "distance": distance
                })

    pd.DataFrame(relationships).to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"[Done] {len(relationships)} relationships saved to: {output_file}")

def json_to_csv_expand(input_json, output_dir, region_file, weight_file):
    os.makedirs(output_dir, exist_ok=True)

    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = []
    for node in data.get("nodes", []):
        tags = node.get("tags", {})
        expanded_node = {
            "id": node.get("id", ""),
            "lat": node.get("lat", ""),
            "lon": node.get("lon", ""),
            "name": tags.get("name", ""),
            "place": tags.get("place", ""),
            "highway": tags.get("highway", ""),
            "railway": tags.get("railway", ""),
            "public_transport": tags.get("public_transport", ""),
            "amenity": tags.get("amenity", ""),
            "shop": tags.get("shop", ""),
            "building": tags.get("building", ""),
            "tourism": tags.get("tourism", ""),
            "element_type": node.get("element_type", ""),
            "assigned_region": node.get("assigned_region", ""),
            "nearby_regions": ", ".join([str(r) for r in node.get("nearby_regions", []) if r]) if node.get("nearby_regions") else None,
            "centroid_lat": node.get("centroid_lat", node.get("lat", "")) if node.get("element_type") else None,
            "centroid_lon": node.get("centroid_lon", node.get("lon", "")) if node.get("element_type") else None
        }
        nodes.append(expanded_node)
    pd.DataFrame(nodes).to_csv(os.path.join(output_dir, "nodes_unfold.csv"), index=False, encoding="utf-8-sig")

    ways = []
    way_node_relations = []
    for way in data.get("ways", []):
        tags = way.get("tags", {})
        expanded_way = {
            "id": way.get("id", ""),
            "name": tags.get("name", ""),
            "highway": tags.get("highway", ""),
            "building": tags.get("building", ""),
            "shop": tags.get("shop", ""),
            "landuse": tags.get("landuse", ""),
            "boundary": tags.get("boundary", ""),
            "tourism": tags.get("tourism", ""),
            "historic": tags.get("historic", ""),
            "leisure": tags.get("leisure", ""),
            "element_type": way.get("element_type", ""),
            "assigned_region": way.get("assigned_region", ""),
            "nearby_regions": ", ".join([str(r) for r in way.get("nearby_regions", []) if r]) if way.get("nearby_regions") else None,
            "centroid_lat": way.get("centroid_lat", None),
            "centroid_lon": way.get("centroid_lon", None)
        }
        ways.append(expanded_way)
        for node_id in way.get("nodes", []):
            way_node_relations.append({"way_id": way["id"], "node_id": node_id})
    pd.DataFrame(ways).to_csv(os.path.join(output_dir, "way_unfold.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(way_node_relations).to_csv(os.path.join(output_dir, "way_node_relations.csv"), index=False, encoding="utf-8-sig")

    relations = []
    relation_members = []
    for relation in data.get("relations", []):
        tags = relation.get("tags", {})
        expanded_relation = {
            "id": relation.get("id", ""),
            "name": tags.get("name", ""),
            "type": tags.get("type", ""),
            "route": tags.get("route", ""),
            "element_type": relation.get("element_type", ""),
            "assigned_region": relation.get("assigned_region", ""),
            "nearby_regions": ", ".join([str(r) for r in relation.get("nearby_regions", []) if r]) if relation.get("nearby_regions") else None,
            "centroid_lat": relation.get("centroid_lat", None),
            "centroid_lon": relation.get("centroid_lon", None)
        }
        relations.append(expanded_relation)
        for member in relation.get("members", []):
            relation_members.append({
                "relation_id": relation["id"],
                "member_type": member["type"],
                "member_id": member["ref"],
                "role": member.get("role", "")
            })
    pd.DataFrame(relations).to_csv(os.path.join(output_dir, "relation_unfold.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(relation_members).to_csv(os.path.join(output_dir, "relation_members.csv"), index=False, encoding="utf-8-sig")

    build_relationships(data, distance_threshold_nei=100, distance_threshold_crs=300,
                        output_file=os.path.join(output_dir, "item_relationships.csv"),
                        region_file=region_file, weight_file=weight_file)

    print("CSV files have been saved successfully.")


if __name__ == '__main__':
    json_to_csv_expand(
        input_json="../KG_file/new-york_filtered_level67.json",
        output_dir="../KG_file/",
        region_file="../KG_file/NewYork7+NewJersey6.geojson",
        weight_file="../KG_file/weight_df.csv"
    )
