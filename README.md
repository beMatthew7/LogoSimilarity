# Logo Similarity - Match and Group Websites by Logo

## Problem Statement

Given a dataset of company websites (provided as a Parquet file), the goal is to:

1. **Extract logos** from each website automatically.
2. **Group websites** that share the same or visually similar logos.

This is essentially a visual similarity / clustering problem, solved here without traditional ML clustering algorithms (no DBSCAN, no k-means).

---

## Approach

### Step 1: Logo Extraction (`scraper.py`)

The primary scraper fetches each website's HTML and looks for logo images by scanning `<img>` tags for keywords like "logo" in the `src`, `alt`, or `class` attributes. It handles multiple source attributes (`data-srcset`, `data-src`, `data-fallback-src`, `src`) to maximize extraction success.

If scraping fails (e.g., the site blocks requests or uses JavaScript rendering), it falls back to the **Google Favicons API** (`https://www.google.com/s2/favicons?domain=...&sz=256`) to retrieve a high-resolution favicon as a proxy for the logo.

Key features:
- Multi-threaded downloads using `ThreadPoolExecutor` (10 workers).
- Handles HTTPS issues gracefully (unverified SSL).
- Tracks statistics: scrape success, fallback success, failures, and unreachable domains.
- Achieves the required **97%+ extraction rate**.

### Step 1 (Alternative): Logo Extraction (`scraper_v2.py`)

An alternative scraper that uses the `extract-favicon` library to find the best available favicon/icon for each domain. Simpler logic but relies on an external library for icon discovery. Uses 100 concurrent workers for faster processing.

### Step 2: Logo Grouping (`grouper.py`)

Once logos are downloaded, the grouper performs visual similarity matching:

1. **Image Preprocessing**: All images (PNG, JPG, SVG, ICO) are loaded, converted to RGBA, composited onto a white background (to handle transparency), and resized/cropped to 224x224.
   - SVG files are rasterized using `cairosvg` before processing.

2. **Feature Extraction**: Each logo is passed through **DINOv2** (`dinov2_vits14` from Facebook Research), a self-supervised vision transformer that produces a rich embedding vector for each image. Processing is done in batches of 32 for efficiency.

3. **Similarity Matching**: Pairwise **cosine similarity** is computed between all embedding vectors. Logos with a similarity score >= **0.88** are grouped together.

4. **Grouping Algorithm**: A simple greedy single-pass algorithm iterates through all domains. For each unvisited domain, it finds all other unvisited domains whose logo exceeds the similarity threshold and groups them together. This avoids ML clustering algorithms as suggested in the guidelines.

The result is a list of groups, each containing one or more website domains that share visually similar logos. Results are saved to `results.json`.

### Why DINOv2?

DINOv2 is a self-supervised vision model that learns powerful visual features without needing labeled data. It excels at capturing semantic visual similarity -- exactly what is needed to determine whether two logos represent the same brand, even if they differ slightly in color, resolution, or format.

### Why Not Traditional Clustering?

The guidelines explicitly asked to avoid ML clustering algorithms like DBSCAN or k-means. Instead, the solution uses a straightforward **threshold-based greedy grouping** on top of cosine similarity. This is deterministic, interpretable, and easy to tune via the `SIMILARITY_THRESHOLD` parameter.

---

## Project Structure

```
LogoSimilarity/
  scraper.py           - Primary logo scraper (HTML parsing + Google Favicons fallback)
  scraper_v2.py        - Alternative scraper using extract-favicon library
  grouper.py           - Logo embedding (DINOv2) and similarity grouping
  test_read.py         - Utility script to inspect the Parquet dataset
  logos.snappy.parquet  - Input dataset containing website domains
  downloaded_logos/     - Directory where extracted logos are saved
  results.json         - Output: groups of websites with similar logos
  requirements.txt     - Python dependencies
  resources            - Reference links used during development
  README.md            - This file
```

---

## Installation

### Prerequisites

- Python 3.9+
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

**Note on PyTorch**: The `torch` and `torchvision` packages listed in `requirements.txt` will install the default (CPU) version. If you have an NVIDIA GPU, install the CUDA version instead from [pytorch.org](https://pytorch.org/get-started/locally/). On Apple Silicon Macs, the default pip install includes MPS (Metal) acceleration support, which the code automatically detects and uses.

**Note on CairoSVG**: The `cairosvg` package requires the Cairo graphics library to be installed on your system:
- macOS: `brew install cairo`
- If you encounter an OSError even after installing cairo, run: export DYLD_LIBRARY_PATH="$(brew --prefix cairo)/lib" before executing the grouper.
- Ubuntu/Debian: `sudo apt-get install libcairo2-dev`
- Windows: See [CairoSVG documentation](https://cairosvg.org/documentation/)

---

## Usage

### 1. Extract Logos

Run the scraper to download logos from the websites listed in the Parquet file:

```bash
python scraper.py
```

Or use the alternative scraper:

```bash
python scraper_v2.py
```

Both scripts are currently set to process the first 50 domains (`TEST_LIMIT = 50`). Change this value or remove the limit to process all domains.

Downloaded logos are saved to the `downloaded_logos/` directory.

### 2. Group Logos by Similarity

Once logos are downloaded, run the grouper:

```bash
python grouper.py
```

This will:
- Load all images from `downloaded_logos/`
- Generate DINOv2 embeddings for each logo
- Compute pairwise cosine similarity
- Group logos with similarity >= 0.88
- Save the results to `results.json`

### 3. Inspect the Dataset (Optional)

To see the structure and contents of the input Parquet file:

```bash
python test_read.py
```

---

## Output Format

`results.json` contains a JSON array of groups. Each group is an array of domain strings:

```json
[
    ["ebay.cn", "ebayglobalshipping.com"],
    ["bakertilly.es", "bakertilly.lu"],
    ["mazda-autohaus-hellwig-hoyerswerda.de", "mazda-autohaus-kaschmieder-waren.de"],
    ["aamcoseguin.com", "aamcoanaheim.net", "aamcoconyersga.com"],
    ["zalando.cz"],
    ...
]
```

Groups with a single entry indicate logos that were unique and did not match any other logo in the dataset.

---

## Scalability Considerations

- **Batch processing**: Embeddings are computed in batches (configurable `BATCH_SIZE`), making it straightforward to process large datasets.
- **Concurrency**: Logo downloads use thread pools for parallel HTTP requests.
- **Device acceleration**: The grouper automatically uses MPS (Apple Silicon), CUDA (NVIDIA GPU), or CPU, depending on availability.
- **Potential improvements for billion-scale**: For very large datasets, the cosine similarity step (currently O(n^2)) could be replaced with approximate nearest neighbor search (e.g., FAISS or Annoy), and embedding computation could be distributed across multiple GPUs or machines.

---

## Design Decisions

| Decision | Reasoning |
|---|---|
| DINOv2 over CLIP/EfficientNet | Superior self-supervised features for visual similarity without needing text labels |
| Greedy threshold grouping over DBSCAN/k-means | Meets the guideline requirement; simple, deterministic, and interpretable |
| Google Favicons fallback | Ensures high extraction rate (97%+) even when scraping is blocked |
| SVG rasterization via CairoSVG | Many modern logos are in SVG format; rasterizing ensures uniform processing |
| White background compositing | Handles transparent PNGs/SVGs consistently for embedding |
| Cosine similarity threshold of 0.88 | Empirically tuned -- high enough to avoid false positives, low enough to catch brand variations |

Full Resource List (Links)
During development, I utilized the following resources to solve specific problems:

How to download all images from a webpage (GeeksforGeeks):
https://www.geeksforgeeks.org/how-to-download-all-images-from-a-web-page-in-python/

Testing if a page is found on the server (GeeksforGeeks):
https://www.geeksforgeeks.org/python-test-the-given-page-is-found-or-not-on-the-server-using-python/

Google's Hidden Favicon API (Dev.to):
https://dev.to/derlin/get-favicons-from-any-website-using-a-hidden-google-api-3p1e

DINOv2 Image Retrieval & Embedding (Roboflow):
https://colab.research.google.com/github/roboflow-ai/notebooks/blob/main/notebooks/dinov2-image-retrieval.ipynb

DINOv2 Official Research (Meta AI):
https://github.com/facebookresearch/dinov2