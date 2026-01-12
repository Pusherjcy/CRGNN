import osmium
import json
import time

class OSMToJSONHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.ways = []
        self.relations = []

        self.node_ids = set()
        self.way_ids = set()
        self.relation_ids = set()

        self.node_count = 0
        self.way_count = 0
        self.relation_count = 0

    def node(self, n):
        self.node_ids.add(n.id)
        self.node_count += 1
        if self.node_count % 10000 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Parsed {self.node_count} nodes")

        self.nodes.append({
            "id": n.id,
            "lat": n.location.lat,
            "lon": n.location.lon,
            "tags": dict(n.tags)
        })

    def way(self, w):
        self.way_ids.add(w.id)
        self.way_count += 1
        if self.way_count % 10000 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Parsed {self.way_count} ways")

        valid_node_refs = [n.ref for n in w.nodes]
        if valid_node_refs:
            self.ways.append({
                "id": w.id,
                "nodes": valid_node_refs,
                "tags": dict(w.tags)
            })

    def relation(self, r):
        self.relation_ids.add(r.id)
        self.relation_count += 1
        if self.relation_count % 1000 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Parsed {self.relation_count} relations")

        valid_members = [
            {"type": m.type, "ref": m.ref, "role": m.role}
            for m in r.members
            if (m.type == 'n' and m.ref in self.node_ids) or
               (m.type == 'w' and m.ref in self.way_ids) or
               (m.type == 'r' and m.ref in self.relation_ids)
        ]
        if valid_members:
            self.relations.append({
                "id": r.id,
                "members": valid_members,
                "tags": dict(r.tags)
            })

    def save_to_jsonl_files(self, output_prefix):
        print(f"[{time.strftime('%H:%M:%S')}] Writing JSONL files...")

        def write_jsonl(path, items):
            with open(path, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

        write_jsonl(f"{output_prefix}_nodes.jsonl", self.nodes)
        write_jsonl(f"{output_prefix}_ways.jsonl", self.ways)
        write_jsonl(f"{output_prefix}_relations.jsonl", self.relations)

        print(f"[{time.strftime('%H:%M:%S')}] Finished writing JSONL files.")

    def merge_jsonl_to_json(self, output_prefix):
        print(f"[{time.strftime('%H:%M:%S')}] Merging JSONL files to single JSON...")

        def read_jsonl(path):
            data = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    data.append(json.loads(line.strip()))
            return data

        result = {
            "nodes": read_jsonl(f"{output_prefix}_nodes.jsonl"),
            "ways": read_jsonl(f"{output_prefix}_ways.jsonl"),
            "relations": read_jsonl(f"{output_prefix}_relations.jsonl")
        }

        with open(f"{output_prefix}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"[{time.strftime('%H:%M:%S')}] Saved final merged JSON to {output_prefix}.json")

if __name__ == '__main__':
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"Start time: {start_time}")

    input_file = "../KG_file/new-york.osm"
    output_prefix = "../KG_file/new-york"

    handler = OSMToJSONHandler()
    handler.apply_file(input_file)

    handler.save_to_jsonl_files(output_prefix)
    handler.merge_jsonl_to_json(output_prefix)

    end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"End time: {end_time}")
