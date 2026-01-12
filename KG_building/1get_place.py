import osmium

class FilterHandler(osmium.SimpleHandler):
    def __init__(self, output_file):
        super().__init__()
        self.writer = osmium.SimpleWriter(output_file)
        self.nodes = set()
        self.ways = {}
        self.relations = {}
        print("Handler initialized.")

    def __del__(self):
        self.writer.close()
        print("Writer closed.")

    def is_in_place(self, lat, lon):
        return 40.476578 <= lat <= 41.203285 and -74.503212 <= lon <= -73.464762

    def node(self, n):
        if n.location:
            lat, lon = n.location.lat, n.location.lon
            if self.is_in_place(lat, lon):
                self.nodes.add(n.id)
                print(f"Node {n.id} is in place and will be added.")
                self.writer.add_node(n)
            else:
                print(f"Node {n.id} is outside place and will not be added.")
        else:
            print(f"Node {n.id} has no location and will not be added.")

    def way(self, w):
        valid_nodes = [n.ref for n in w.nodes if n.ref in self.nodes]
        if valid_nodes:
            self.ways[w.id] = valid_nodes
            print(f"Way {w.id} has valid nodes and will be added.")
            self.writer.add_way(w)
        else:
            print(f"Way {w.id} has no valid nodes and will not be added.")

    def relation(self, r):
        valid_members = []
        for member in r.members:
            if member.type == 'n' and member.ref in self.nodes:
                valid_members.append({"type": member.type, "ref": member.ref, "role": member.role})
            elif member.type == 'w' and member.ref in self.ways:
                valid_members.append({"type": member.type, "ref": member.ref, "role": member.role})
            elif member.type == 'r' and member.ref in self.relations:
                valid_members.append({"type": member.type, "ref": member.ref, "role": member.role})

        if valid_members:
            self.relations[r.id] = valid_members
            print(f"Relation {r.id} has valid members and will be added.")
            self.writer.add_relation(r)
        else:
            print(f"Relation {r.id} has no valid members and will not be added.")

    def second_pass(self):
        for way_id, node_refs in self.ways.items():
            for node_id in node_refs:
                if node_id not in self.nodes:
                    print(f"Node {node_id} referenced by way {way_id} will be added.")
                    self.nodes.add(node_id)

        for relation_id, members in self.relations.items():
            for member in members:
                if member['type'] == 'n' and member['ref'] not in self.nodes:
                    print(f"Node {member['ref']} referenced by relation {relation_id} will be added.")
                    self.nodes.add(member['ref'])
                elif member['type'] == 'w' and member['ref'] not in self.ways:
                    print(f"Way {member['ref']} referenced by relation {relation_id} will be added.")
                    self.ways[member['ref']] = []
                elif member['type'] == 'r' and member['ref'] not in self.relations:
                    print(f"Relation {member['ref']} referenced by relation {relation_id} will be added.")
                    self.relations[member['ref']] = []

if __name__ == '__main__':
    input_file = "../KG_file/us-northeast-latest.osm.pbf"
    output_file = "../KG_file/new-york.osm"

    handler = FilterHandler(output_file)
    print("Processing input file...")
    handler.apply_file(input_file, locations=True)

    print("Performing second pass to include all referenced elements...")
    handler.second_pass()

    print(f"NewYork data has been saved to {output_file}")
