# UFO Multimodal Embedding Analysis

## Notebook Logic Reused

The sample clustering notebook embeds documents, projects embeddings with t-SNE, clusters them with KMeans, and compares clusters visually.

The sample anomaly notebook embeds documents, projects embeddings with t-SNE, calculates each item distance from its class centroid, and marks high-distance records as outliers.

The scripts here adapt that logic to the UFO release with multimodal Gemini embeddings.

## Dataset Mapping

Run:

```bash
python3 scripts/ufo_inventory.py
```

Outputs:

```text
analysis/inventory_documents.csv
analysis/inventory_summary.json
analysis/figures/ufo_inventory_overview.png
```

Current inventory:

```text
162 metadata rows
159 distinct physical files
120 PDFs
25 videos
14 images
```

The row/file mismatch is caused by duplicate metadata rows pointing to the same physical video files.

## Embedding Strategy

Every embedding request includes metadata text plus the media payload. This keeps the case context paired with the file content.

PDFs:

```text
Gemini limit: 6 pages per PDF request.
PDFs <=6 pages are embedded directly.
PDFs >6 pages are split into 6-page PDF chunks.
Chunk embeddings are averaged into one document-level embedding.
```

Images:

```text
PNG/JPEG files are embedded directly with metadata text.
```

Videos:

```text
Videos <=120 seconds are embedded directly.
Videos >120 seconds are represented by up to 6 sampled JPEG frames.
This avoids needing ffmpeg on this machine.
```

## Execution Order

Dry-run the embedding plan:

```bash
python3 scripts/ufo_embed_multimodal.py --dry-run
```

Run real embeddings:

```bash
export GEMINI_API_KEY="your_key_here"
python3 scripts/ufo_embed_multimodal.py --resume
```

Or rotate through multiple free-tier keys from a local key file:

```bash
python3 scripts/ufo_embed_multimodal.py \
  --api-key-file /path/to/gemini-free-tier.keys.txt \
  --resume
```

The runner stores only hashed key IDs and counters in:

```text
analysis/embeddings/gemini_key_usage_state.json
analysis/embeddings/key_usage_snapshot.csv
```

Default local guards are conservative:

```text
90 RPM per key
30,000 estimated TPM per key
950 RPD per key
```

Run clustering:

```bash
python3 scripts/ufo_cluster_embeddings.py
```

Run anomaly/uniqueness scoring:

```bash
python3 scripts/ufo_anomaly_embeddings.py
```

## Main Outputs

```text
analysis/embeddings/embedding_plan.csv
analysis/embeddings/chunk_embeddings.npz
analysis/embeddings/chunk_index.csv
analysis/embeddings/document_embeddings.npz
analysis/embeddings/document_index.csv
analysis/clustering/document_clusters.csv
analysis/clustering/cluster_summary.csv
analysis/anomaly/ufo_anomaly_scores.csv
analysis/anomaly/top_unique.csv
analysis/figures/ufo_clustering_overview.png
analysis/figures/ufo_anomaly_overview.png
```
