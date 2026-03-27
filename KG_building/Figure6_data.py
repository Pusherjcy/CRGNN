import random
import math
from tqdm import tqdm
from collections import Counter

def read_checkins(filepath):
    checkins = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 6:
                lat = float(parts[4])
                lon = float(parts[5])
                checkins.append((lat, lon))
    return checkins

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def analyze_distances(checkins, sample_size=100):
    from tqdm import tqdm

    samples = random.sample(checkins, sample_size)

    distances = []
    total_pairs = sample_size * (sample_size - 1) // 2

    pbar = tqdm(total=total_pairs, desc="calculating...", ncols=80)
    for i in range(len(samples)):
        for j in range(i+1, len(samples)):
            lat1, lon1 = samples[i]
            lat2, lon2 = samples[j]
            dist = haversine(lat1, lon1, lat2, lon2)
            distances.append(dist)
            pbar.update(1)
    pbar.close()

    bins = [i / 10.0 for i in range(0, 50)] + [float('inf')]
    bin_labels = [f"{int(bins[i]*1000)}-{int(bins[i+1]*1000)}m" for i in range(len(bins) - 2)] + [">=5000m"]

    def categorize_distance(d):
        for i in range(len(bins) - 1):
            if bins[i] <= d < bins[i+1]:
                return bin_labels[i]
        return ">=5000m"

    categories = [categorize_distance(d) for d in distances]
    distribution = Counter(categories)

    print("The distribution of distances:")
    for label in bin_labels:
        print(f"{label}: {distribution[label]} pairs")


if __name__ == "__main__":
    filepath = "../KG_file/dataset_TSMC2014_NYC.txt"
    checkins = read_checkins(filepath)
    analyze_distances(checkins, sample_size=10000)
