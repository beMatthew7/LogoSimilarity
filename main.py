import os
import json
from logo_similarity import list_logo_files, compute_hashes, build_similarity_graph, get_groups_from_graph

def logo_file_to_domain(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    return name.replace('_', '.')

def main():
    logo_files = list_logo_files('data/logos')
    print(f"Found {len(logo_files)} logos.")
    hash_map = compute_hashes(logo_files, hash_func='phash')
    print(f"Computed hashes for {len(hash_map)} logos.")
    G = build_similarity_graph(hash_map, threshold=5)
    groups = get_groups_from_graph(G)
    print(f"Found {len(groups)} groups.")

    groups_domains = []
    for group in groups:
        domains = [logo_file_to_domain(f) for f in group]
        groups_domains.append(domains)
    os.makedirs('output', exist_ok=True)
    with open('output/groups.json', 'w') as f:
        json.dump(groups_domains, f, indent=2)
    print("Results saved to output/groups.json")

if __name__ == '__main__':
    main()