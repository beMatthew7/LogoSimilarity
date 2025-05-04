import os
from PIL import Image
import imagehash

from tqdm import tqdm

def list_logo_files(logo_dir='data/logos'):
    files = [f for f in os.listdir(logo_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))]
    return [os.path.join(logo_dir, f) for f in files]

def compute_hashes(logo_files, hash_func='phash'):
    """
    hash_func: 'phash', 'ahash', 'dhash'
    """
    hash_map = {}
    for file in tqdm(logo_files, desc='Hashing logos'):
        try:
            img = Image.open(file).convert('RGB')
            if hash_func == 'phash':
                h = imagehash.phash(img)
            elif hash_func == 'ahash':
                h = imagehash.average_hash(img)
            elif hash_func == 'dhash':
                h = imagehash.dhash(img)
            else:
                raise ValueError('Unknown hash function')
            hash_map[file] = h
        except Exception:
            continue
    return hash_map

def hamming_distance(hash1, hash2):
    return (hash1 - hash2)

def build_similarity_graph(hash_map, threshold=5):
    """
    threshold: maximum Hamming distance for logos to be considered similar
    """
    import networkx as nx
    files = list(hash_map.keys())
    G = nx.Graph()
    G.add_nodes_from(files)
    for i in range(len(files)):
        for j in range(i+1, len(files)):
            d = hamming_distance(hash_map[files[i]], hash_map[files[j]])
            if d <= threshold:
                G.add_edge(files[i], files[j])
    return G

def get_groups_from_graph(G):
    import networkx as nx
    return list(nx.connected_components(G))
