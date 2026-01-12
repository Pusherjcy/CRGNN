import json
from shapely.geometry import Point, shape
from shapely.ops import nearest_points
from tqdm import tqdm

def calculate_centroid(coords):
    if not coords:
        return None
    lat_sum = sum(coord[0] for coord in coords)
    lon_sum = sum(coord[1] for coord in coords)
    return lat_sum / len(coords), lon_sum / len(coords)

def is_closed_loop(coords):
    if not coords:
        return False
    return coords[0] == coords[-1]

def filter_tags(data, required_tags, regions, distance_threshold):
    nodes_dict = {node["id"]: (node["lat"], node["lon"]) for node in data.get("nodes", [])}
    ways_dict = {way["id"]: way for way in data.get("ways", [])}

    for item_type in ["nodes", "ways", "relations"]:
        filtered_items = []
        print(f"Processing {item_type}...")
        for item in tqdm(data[item_type]):
            tags = item.get("tags", {})

            if item_type in ["nodes", "ways"]:
                item["tags"] = {k: v for k, v in tags.items() if k == "name" or k in required_tags[item_type]}

            if item_type == "nodes":
                if "name" in tags:
                    item["element_type"] = "significant_node"

                    lat, lon = item["lat"], item["lon"]
                    node_point = Point(lon, lat)
                    assigned_region = None
                    nearby_regions = []

                    for region in regions:
                        region_shape = shape(region["geometry"])
                        region_name = region["properties"].get("name")

                        if region_shape.contains(node_point):
                            assigned_region = region_name
                        else:
                            nearest_point = nearest_points(node_point, region_shape)[1]
                            distance = node_point.distance(nearest_point) * 111139
                            if distance < distance_threshold:
                                nearby_regions.append(region_name)

                    item["assigned_region"] = assigned_region
                    item["nearby_regions"] = nearby_regions if nearby_regions else None

                filtered_items.append(item)

            elif item_type == "ways":
                if "name" in tags:
                    is_closed = item["nodes"][0] == item["nodes"][-1]
                    coords = [nodes_dict.get(node_id) for node_id in item["nodes"] if node_id in nodes_dict]
                    coords = [coord for coord in coords if coord is not None]
                    centroid = calculate_centroid(coords)

                    if is_closed:
                        item["element_type"] = "area"
                    else:
                        item["element_type"] = "road"

                    if centroid:
                        item["centroid_lat"], item["centroid_lon"] = centroid

                filtered_items.append(item)

            elif item_type == "relations":
                if "name" not in tags:
                    continue

                relation_type = tags.get("type", "")
                route_type = tags.get("route", "")

                if relation_type in {"watershed", "boundary"} and route_type not in {"subway", "bus"}:
                    continue
                if route_type in {"railway"}:
                    continue
                if relation_type not in {"multipolygon", "boundary"} and route_type not in {"subway", "bus"}:
                    continue

                item["tags"] = {k: v for k, v in tags.items() if k == "name" or k in required_tags[item_type]}

                coords = []
                for member in item.get("members", []):
                    if member["type"] == "n":
                        if member["ref"] in nodes_dict:
                            coords.append(nodes_dict[member["ref"]])
                    elif member["type"] == "w":
                        if member["ref"] in ways_dict:
                            way_coords = [nodes_dict.get(node_id) for node_id in ways_dict[member["ref"]]["nodes"] if node_id in nodes_dict]
                            coords.extend([coord for coord in way_coords if coord is not None])

                centroid = calculate_centroid(coords)

                if tags.get("type") == "route" or tags.get("route") in {"road", "bus", "subway"}:
                    item["element_type"] = "road"
                else:
                    item["element_type"] = "area"

                if centroid:
                    item["centroid_lat"], item["centroid_lon"] = centroid

                filtered_items.append(item)

            if item_type != "nodes" and "centroid_lat" in item and "centroid_lon" in item:
                centroid_point = Point(item["centroid_lon"], item["centroid_lat"])
                assigned_region = None
                nearby_regions = []

                for region in regions:
                    region_shape = shape(region["geometry"])
                    region_name = region["properties"].get("name")

                    if region_shape.contains(centroid_point):
                        assigned_region = region_name
                    else:
                        nearest_point = nearest_points(centroid_point, region_shape)[1]
                        distance = centroid_point.distance(nearest_point) * 111139
                        if distance < distance_threshold:
                            nearby_regions.append(region_name)

                item["assigned_region"] = assigned_region
                item["nearby_regions"] = nearby_regions if nearby_regions else None

        data[item_type] = filtered_items
    return data

if __name__ == "__main__":
    input_file = "../KG_file/new-york.json"
    output_file = "../KG_file/new-york_filtered_level67.json"
    region_file = "../KG_file/NewYork7+NewJersey6_small.geojson"

    required_tags = {
        "nodes": {"place", "highway", "railway", "public_transport", "amenity", "shop", "building", "tourism"},
        "ways": {"highway", "building", "landuse", "boundary"},
        "relations": {"type", "route"}
    }

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(region_file, "r", encoding="utf-8") as f:
        regions = json.load(f)["features"]

    filtered_data = filter_tags(data, required_tags, regions, distance_threshold=500)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"Filtered data with region assignments has been saved to {output_file}")
