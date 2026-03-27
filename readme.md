# CRGNN: Cross-Region Graph Neural Network for Next-POI Recommendation

## 1. Environment

The codebase has been tested under the following environment:

* Python == 3.8.13
* pytorch == 1.11.0
* torch_geometric == 2.0.4
* pandas == 1.4.1
* scikit-learn == 0.23.2


It is recommended to use a virtual environment (e.g., `conda` or `venv`) to ensure compatibility.

---

## 2. Knowledge Graph Construction

The knowledge graph (KG) is constructed through a multi-step preprocessing pipeline.  
Please execute the following scripts **in order**:

* 1get_place.py
* 2osm2json.py
* 3clean_tags.py
* 4json2csv.py
* 5txt2csv.py
* 6foursquare_poi_matching.py
* 7getHotMetrix.py


### Important Notes

#### (1) `1_get_place.py`
- Requires downloading the OpenStreetMap data file in advance: us-northeast-latest.osm.pbf
- The file can be obtained from:  
https://download.geofabrik.de/

---

#### (2) `3_clean_tags.py`
- Requires a pre-downloaded `.geojson` file for administrative boundaries.
- The GeoJSON can be generated via **Overpass Turbo**:  
https://overpass-turbo.eu/

##### Query for New York (level 7) + New Jersey (level 6):

```shell
[out:json][timeout:25];
area["name"="New Jersey"]->.a;
area["name"="New York"]->.b;
relation(area.a)["boundary"="administrative"]["admin_level"="6"]->.nj;
relation(area.b)["boundary"="administrative"]["admin_level"="7"]->.ny;
(.nj; .ny;);
out body;
>;
out skel qt;
```

##### Query for Tokyo:
```shell
[out:json][timeout:25];

area["name"="東京都"]->.tokyo;
area["name"="神奈川県"]->.kanagawa;
area["name"="埼玉県"]->.saitama;
area["name"="千葉県"]->.chiba;

(
  relation(area.tokyo)["boundary"="administrative"]["admin_level"="7"];
  relation(area.kanagawa)["boundary"="administrative"]["admin_level"="7"];
  relation(area.saitama)["boundary"="administrative"]["admin_level"="7"];
  relation(area.chiba)["boundary"="administrative"]["admin_level"="7"];
);
out body;
>;
out skel qt;
```

---

## 3. Visualization

### Figure 5

Figure 5 is generated using **Kepler.gl**:

- Upload the following files:
  - `Foursquare_xxx.csv`
  - Corresponding `.geojson` file
- Visualization tool:  
https://kepler.gl/

---

## 4. Experimental Reproduction

### Table 1
[get_maxmin_lonlat.py](KG_building/get_maxmin_lonlat.py)

---

### Figure 6 (Global Distance Distribution)
[Figure6_data.py](KG_building/Figure6_data.py)

---

### Figure 7 (Adjacent Check-in Distance Distribution)
[Figure7_data.py](KG_building/Figure7_data.py)

Then run:
[Figure67.ipynb](KG_building/Figure67.ipynb)


---

### Table 2
[process_data.py](Next_POI/process_data.py)


---

### Figure 8 (Cold-start Study)

[split_dataset.py](Next_POI/split_dataset.py)

Then re-run:

[process_data.py](Next_POI/process_data.py)


---

## 5. Ablation Study

We implement three model variants for ablation analysis:

### (1) CRGNN (Full Model)
- Includes:
  - LLM-based semantic initialization
  - Cross-region relation modeling

---

### (2) CRGNN w/o LLM (`wo_llm`)
- Removes LLM-based semantic enhancement
- POI representations are initialized using default trainable ID embeddings
- This variant evaluates the contribution of semantic initialization

---

### (3) CRGNN w/o Cross (`wo_cross`)
- Removes cross-region relation modeling during graph construction
- Only intra-region spatial relations are retained
- LLM-based initialization remains unchanged
- This variant evaluates the impact of cross-region spatial modeling
