import random
import math
from collections import defaultdict, Counter
from tqdm import tqdm
from datetime import datetime

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def read_user_checkins(filepath):
    user_checkins = defaultdict(list)
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 8:
                user_id = parts[0]
                lat = float(parts[4])
                lon = float(parts[5])
                utc_time_str = parts[7]
                try:
                    utc_time = datetime.strptime(utc_time_str, "%a %b %d %H:%M:%S %z %Y")
                except Exception:
                    continue
                user_checkins[user_id].append((utc_time, lat, lon))
    return user_checkins

# 分析轨迹上的相邻签到点距离分布
def analyze_user_trajectories(user_checkins, sample_user_count=1000):
    all_distances = []

    user_ids = list(user_checkins.keys())
    if len(user_ids) < sample_user_count:
        print(f"Warning: only {len(user_ids)} users, less than {sample_user_count}")
        sample_users = user_ids
    else:
        sample_users = random.sample(user_ids, sample_user_count)

    for user_id in tqdm(sample_users, desc="Processing user trajectories", ncols=80):
        checkins = user_checkins[user_id]
        if len(checkins) < 2:
            continue

        checkins.sort(key=lambda x: x[0])

        for i in range(len(checkins) - 1):
            _, lat1, lon1 = checkins[i]
            _, lat2, lon2 = checkins[i+1]
            dist = haversine(lat1, lon1, lat2, lon2)
            all_distances.append(dist)

    # 分组
    bins = [i / 10.0 for i in range(0, 50)] + [float('inf')]
    bin_labels = [f"{int(bins[i]*1000)}-{int(bins[i+1]*1000)}m" for i in range(len(bins) - 2)] + [">=5000m"]

    def categorize_distance(d):
        for i in range(len(bins) - 1):
            if bins[i] <= d < bins[i+1]:
                return bin_labels[i]
        return ">=5000m"

    categories = [categorize_distance(d) for d in all_distances]
    distribution = Counter(categories)

    print("Distribution of distances between adjacent check-in points:")
    for label in bin_labels:
        print(f"{label}: {distribution[label]} 对")

if __name__ == "__main__":
    filepath = "../KG_file/dataset_TSMC2014_NYC.txt"
    user_checkins = read_user_checkins(filepath)
    analyze_user_trajectories(user_checkins, sample_user_count=1000)
