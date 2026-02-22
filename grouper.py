import os
import json
import torch
import torchvision.transforms as T
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
import ssl
import cairosvg
import io
import numpy as np

ssl._create_default_https_context = ssl._create_unverified_context

LOGOS_DIR = 'downloaded_logos'
SIMILARITY_THRESHOLD = 0.92
BATCH_SIZE = 32

device = torch.device('mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu')
print(f"Device: {device}")

print("Loading DINOv2...")
model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vits14').to(device)
model.eval()

transform = T.Compose([
    T.Resize(224, interpolation=T.InterpolationMode.BICUBIC),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
])


def process_image(path):
    try:
        if path.lower().endswith('.svg'):
            png_data = cairosvg.svg2png(url=path, output_width=400, output_height=400)
            img = Image.open(io.BytesIO(png_data)).convert('RGBA')
        else:
            img = Image.open(path).convert('RGBA')

        # Composite onto white background to handle transparency
        canvas = Image.new('RGB', img.size, (255, 255, 255))
        canvas.paste(img, mask=img.split()[3])
        return transform(canvas)
    except Exception:
        return None


print("Embedding logos...")
embeddings = {}
image_paths = [
    os.path.join(LOGOS_DIR, f) for f in os.listdir(LOGOS_DIR)
    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.ico', '.svg'))
]

for i in range(0, len(image_paths), BATCH_SIZE):
    batch_paths = image_paths[i:i + BATCH_SIZE]
    batch_tensors = []
    batch_domains = []

    for path in batch_paths:
        tensor = process_image(path)
        if tensor is not None:
            batch_tensors.append(tensor)
            domain = os.path.basename(path).rsplit('.', 1)[0].replace('_', '.')
            batch_domains.append(domain)

    if batch_tensors:
        input_batch = torch.stack(batch_tensors).to(device)
        with torch.no_grad():
            features = model(input_batch).cpu().numpy()

        for domain, vec in zip(batch_domains, features):
            embeddings[domain] = vec

        print(f"  Processed: {i + len(batch_tensors)} / {len(image_paths)}")

print("Grouping by cosine similarity...")
domains = list(embeddings.keys())
vectors = np.array(list(embeddings.values()))

if len(vectors) == 0:
    print("No valid images found.")
    exit()

sim_matrix = cosine_similarity(vectors)

groups = []
visited = set()

for i in range(len(domains)):
    if domains[i] not in visited:
        current_group = [domains[i]]
        visited.add(domains[i])
        for j in range(i + 1, len(domains)):
            if domains[j] not in visited and sim_matrix[i][j] >= SIMILARITY_THRESHOLD:
                current_group.append(domains[j])
                visited.add(domains[j])
        groups.append(current_group)

print(f"Done. {len(groups)} groups found.")

with open('results.json', 'w') as f:
    json.dump(groups, f, indent=4)

print("Results saved to results.json.")