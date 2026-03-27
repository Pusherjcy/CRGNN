import os
import pandas as pd
import numpy as np
import pickle as pkl
import random
from tqdm import tqdm
from scipy.sparse import dok_matrix
from scipy.sparse import save_npz


def load_csv_files():
    nodes = pd.read_csv('../KG_file/nodes_filtered.csv')
    ways = pd.read_csv('../KG_file/ways_filtered.csv')
    relations = pd.read_csv('../KG_file/relations_filtered.csv')
    item_relationships = pd.read_csv('../KG_file/filtered_item_relationships.csv')
    weibo_matches = pd.read_csv('../KG_file/foursquare_newyork_poi_matches_OSM_location.csv')
    return nodes, ways, relations, item_relationships, weibo_matches


def build_id_mapping(nodes, ways, relations):
    id_mapping = {}
    index = 0

    for node_id in nodes['id']:
        if node_id not in id_mapping:
            id_mapping[node_id] = index
            index += 1

    for way_id in ways['id']:
        if way_id not in id_mapping:
            id_mapping[way_id] = index
            index += 1

    for relation_id in relations['id']:
        if relation_id not in id_mapping:
            id_mapping[relation_id] = index
            index += 1

    print(f"id_mapping length: {len(id_mapping)}")
    print(f"max index: {index - 1}")
    return id_mapping


def build_geospatial_knowledge_graph(nodes, ways, relations, item_relationships, id_mapping):
    print("building dist_edges...")
    dist_edges = []

    for _, row in item_relationships.iterrows():
        src_idx = id_mapping.get(row['id_1'])
        dst_idx = id_mapping.get(row['id_2'])
        if src_idx is not None and dst_idx is not None:
            relationship = row['relationship']
            dist_edges.append([src_idx, dst_idx, relationship])
            dist_edges.append([dst_idx, src_idx, relationship])
        else:
            print(f"Warning: id_1={row['id_1']} or id_2={row['id_2']} not found in id_mapping")

    dist_edges = np.array(dist_edges, dtype=object).T
    dist_edges[0] = dist_edges[0].astype(int)
    dist_edges[1] = dist_edges[1].astype(int)

    dist_dict = {idx: [] for idx in range(len(id_mapping))}
    for src, dst, relationship in dist_edges.T:
        if src not in dist_dict:
            print(f"Error: src={src} not in dist_dict")
        if dst not in dist_dict:
            print(f"Error: dst={dst} not in dist_dict")
        dist_dict[src].append((dst, relationship))
        dist_dict[dst].append((src, relationship))

    print("building dist_mat...")
    num_pois = len(id_mapping)
    dist_mat = dok_matrix((num_pois, num_pois), dtype=np.float32)

    relationship_dict = item_relationships.set_index(['id_1', 'id_2'])['distance'].to_dict()
    for (src_id, dst_id), distance in tqdm(relationship_dict.items()):
        src_idx = id_mapping.get(src_id)
        dst_idx = id_mapping.get(dst_id)
        if src_idx is not None and dst_idx is not None:
            dist_mat[src_idx, dst_idx] = distance

    output_dir = '../processed/'
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'dist_graph.pkl'), 'wb') as f:
        pkl.dump({'edges': dist_edges.tolist(), 'dict': dist_dict}, f, pkl.HIGHEST_PROTOCOL)

    print("saving dist_on_graph.npy...")
    dist_on_graph = dist_mat[dist_edges[0].astype(int), dist_edges[1].astype(int)]
    dist_on_graph_csr = dist_on_graph.tocsr()
    save_npz(os.path.join(output_dir, 'dist_on_graph.npz'), dist_on_graph_csr)


def filter_weibo_data(weibo_matches):
    weibo_matches = weibo_matches.dropna(subset=['matched_id'])
    weibo_matches = weibo_matches.drop_duplicates()
    weibo_matches = weibo_matches.drop_duplicates(subset=['user_id', 'matched_id'])
    return weibo_matches


def remap(weibo_matches, n_user, id_mapping):
    uid_dict = dict(zip(pd.unique(weibo_matches['user_id']), range(n_user)))
    weibo_matches['user_id'] = weibo_matches['user_id'].map(uid_dict)

    weibo_matches['matched_id'] = weibo_matches['matched_id'].map(id_mapping)

    unmatched_ids = weibo_matches[weibo_matches['matched_id'].isna()]

    if not unmatched_ids.empty:
        print(f"unmatched POI IDs：")
        print(unmatched_ids[['user_id', 'matched_id']])

    weibo_matches = weibo_matches.dropna(subset=['matched_id'])

    weibo_matches['matched_id'] = weibo_matches['matched_id'].astype(int)

    return weibo_matches

def generate_train_val_test(weibo_matches, n_user, n_poi):
    train_set, val_test_set = [], []

    lat_lon_dict = weibo_matches[['matched_id', 'matched_lat', 'matched_lon']].drop_duplicates(
        subset=['matched_id']).set_index('matched_id').to_dict('index')

    for uid, item in weibo_matches.groupby('user_id'):
        pos_list = item['matched_id'].tolist()

        def gen_neg(pos_list):
            neg = random.choice(pos_list)
            return neg

        neg_list = [gen_neg(pos_list) for _ in pos_list]

        for i in range(1, len(pos_list)):
            pos_poi = pos_list[i]
            neg_poi = neg_list[i]

            pos_coords = lat_lon_dict.get(pos_poi)
            neg_coords = lat_lon_dict.get(neg_poi)

            if pos_coords is None or neg_coords is None:
                continue

            if i != len(pos_list) - 1:
                train_set.append(
                    (uid, pos_poi, pos_list[:i], (pos_coords['matched_lat'], pos_coords['matched_lon']), 1))
                train_set.append(
                    (uid, neg_poi, pos_list[:i], (neg_coords['matched_lat'], neg_coords['matched_lon']), 0))
            else:
                val_test_set.append(
                    (uid, pos_poi, pos_list[:i], (pos_coords['matched_lat'], pos_coords['matched_lon']), 1))
                val_test_set.append(
                    (uid, neg_poi, pos_list[:i], (neg_coords['matched_lat'], neg_coords['matched_lon']), 0))

    random.shuffle(train_set)
    random.shuffle(val_test_set)

    pivot = len(val_test_set) // 2
    val_set, test_set = val_test_set[:pivot], val_test_set[pivot:]

    return train_set, val_set, test_set


def save_data(train_set, val_set, test_set, output_dir, n_user, n_poi):
    with open(f'{output_dir}/train.pkl', 'wb') as f:
        pkl.dump(train_set, f)
        pkl.dump((n_user, n_poi), f)
    with open(f'{output_dir}/val.pkl', 'wb') as f:
        pkl.dump(val_set, f)
        pkl.dump((n_user, n_poi), f)
    with open(f'{output_dir}/test.pkl', 'wb') as f:
        pkl.dump(test_set, f)
        pkl.dump((n_user, n_poi), f)


def build_user_poi_interaction_graph_from_file(weibo_data_file, output_dir, id_mapping):
    weibo_matches = filter_weibo_data(weibo_data_file)

    n_user, n_poi = len(weibo_matches['user_id'].unique()), len(weibo_matches['matched_id'].unique())

    weibo_matches = remap(weibo_matches, n_user, id_mapping)

    output_csv_path = '../processed/foursquare_matches.csv'
    weibo_matches.to_csv(output_csv_path, index=False)
    print(f"foursquare_matches saved to {output_csv_path}")


    train_set, val_set, test_set = generate_train_val_test(weibo_matches, n_user, n_poi)

    save_data(train_set, val_set, test_set, output_dir, n_user, n_poi)


def main():
    nodes, ways, relations, item_relationships, weibo_matches = load_csv_files()
    id_mapping = build_id_mapping(nodes, ways, relations)

    build_geospatial_knowledge_graph(nodes, ways, relations, item_relationships, id_mapping)
    build_user_poi_interaction_graph_from_file(weibo_matches, '../processed', id_mapping)

if __name__ == "__main__":
    main()
