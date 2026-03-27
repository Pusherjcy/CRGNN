import os
import random
from collections import defaultdict

def split_by_user(input_path, ratios=[0.2, 0.4, 0.6, 0.8, 1.0], seed=42):
    random.seed(seed)

    user_data = defaultdict(list)

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 1:
                continue
            user_id = parts[0]
            user_data[user_id].append(line)

    user_ids = list(user_data.keys())
    total_users = len(user_ids)

    print(f"Total users: {total_users}")

    random.shuffle(user_ids)

    base_name, ext = os.path.splitext(input_path)

    for ratio in ratios:
        k = int(total_users * ratio)

        selected_users = set(user_ids[:k])

        output_path = f"{base_name}_{int(ratio*100)}%{ext}"

        with open(output_path, "w", encoding="utf-8") as out:
            for user_id in selected_users:
                out.writelines(user_data[user_id])

        print(f"{int(ratio*100)}% -> users: {k}, file: {output_path}")


if __name__ == "__main__":
    input_file = "../KG_file/dataset_TSMC2014_NYC.txt"
    split_by_user(input_file)