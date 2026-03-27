import pandas as pd
import json
from shapely.geometry import Point, shape
import numpy as np
from tqdm import tqdm

def load_checkins(file_path):
    return pd.read_csv(file_path, sep='\t', encoding='ISO-8859-1', header=None, names=[
        'user_id', 'venue_id', 'category_id', 'category_name',
        'latitude', 'longitude', 'timezone', 'timestamp'
    ])


def load_regions(region_file):
    with open(region_file, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    features = geojson["features"]
    return [(feature["properties"].get("@id", str(i)), shape(feature["geometry"]))
            for i, feature in enumerate(features)]


def match_points_to_regions(df, region_list):
    region_ids = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="匹配区域"):
        point = Point(row["longitude"], row["latitude"])
        matched = None
        for region_id, polygon in region_list:
            if polygon.contains(point):
                matched = region_id
                break
        region_ids.append(matched)
    df["region_id"] = region_ids
    return df[df["region_id"].notnull()]


def build_transition_matrix(df):
    df_sorted = df.sort_values(by=["user_id", "timestamp"])
    region_ids = sorted(df["region_id"].unique())
    region_id_to_index = {rid: idx for idx, rid in enumerate(region_ids)}
    n = len(region_ids)
    H = np.zeros((n, n), dtype=int)

    for user_id, group in df_sorted.groupby("user_id"):
        region_seq = group["region_id"].tolist()
        for i in range(1, len(region_seq)):
            r1, r2 = region_seq[i - 1], region_seq[i]
            if r1 != r2:
                i1 = region_id_to_index[r1]
                i2 = region_id_to_index[r2]
                H[i1][i2] += 1

    return pd.DataFrame(H, index=region_ids, columns=region_ids)


def compute_weight_matrix_method_three(heat_df, matched_df):
    region_visit_counts = matched_df["region_id"].value_counts().to_dict()
    max_visit_count = max(region_visit_counts.values())
    weight_df = pd.DataFrame(0.0, index=heat_df.index, columns=heat_df.columns)

    for i in heat_df.index:
        alpha_i = region_visit_counts.get(i, 0) / max_visit_count if max_visit_count > 0 else 0
        max_outgoing = heat_df.loc[i].max()
        if max_outgoing == 0:
            continue
        for j in heat_df.columns:
            hij = heat_df.at[i, j]
            weight_df.at[i, j] = alpha_i * hij / max_outgoing

    return weight_df


def main():
    checkin_file = '../KG_file/dataset_TSMC2014_NYC.txt'
    region_file = '../KG_file/NewYork7+NewJersey6.geojson'

    print("Loading data...")
    checkins = load_checkins(checkin_file)
    regions = load_regions(region_file)

    print("Matching POI to region...")
    matched = match_points_to_regions(checkins, regions)
    print(f"The number of matching POI: {len(matched)}")

    print("Building hot metrix...")
    heat_df = build_transition_matrix(matched)
    print(f"The number of regions: {heat_df.shape[0]}，the dimensionality of hot metrix: {heat_df.shape}")

    weight_df = compute_weight_matrix_method_three(heat_df, matched)
    print(weight_df)

    output_path = '../KG_file/weight_df2.csv'
    weight_df.to_csv(output_path)
    print(f"Hot metrix is saves to {output_path}")


if __name__ == '__main__':
    main()
