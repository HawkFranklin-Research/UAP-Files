---
license: other
pretty_name: UAP May 8 Embeddings
language:
  - en
size_categories:
  - 100<n<1K
tags:
  - uap
  - ufo
  - embeddings
  - multimodal
  - archive
---

# UAP May 8 Embeddings

This dataset is a derived analysis package built from the public May 8 release of U.S. government UAP/UFO files.

It is meant for downstream search, clustering, anomaly review, and retrieval experiments. The raw archive is published separately; this repo contains the analysis outputs and vector representations.

## Source

Primary archive:

- `HawkFranklin-Research/UAP-May8`

Local analysis workspace used to generate this dataset:

- `analysis/`

## Contents

This repo contains two embedding views:

- `documents.csv` and `document_embeddings.parquet`
- `chunks.csv` and `chunk_embeddings.parquet`

It also includes:

- `document_embeddings.npz`
- `chunk_embeddings.npz`
- `REPORT.md`
- `inventory_summary.json`
- clustering outputs
- anomaly outputs
- figures

## Dataset Shape

| View | Rows | Vector size |
|---|---:|---:|
| Document embeddings | 159 | 3072 |
| Chunk embeddings | 801 | 3072 |

## What Was Removed For Public Release

The public tables keep the content and analysis fields, but they drop operational fields that are only useful inside the local workspace, including:

- absolute local file paths
- key-tracking fields
- attempt bookkeeping

That keeps the published dataset self-contained and avoids leaking local environment details.

## Recommended Files

For most use cases, start with:

- `document_embeddings.parquet`
- `chunk_embeddings.parquet`
- `REPORT.md`

Use the `.csv` files if you want quick inspection without loading parquet.
Use the `.npz` files if you want direct NumPy array access.

## Columns

### Document embeddings

The document table includes:

- document identity
- source agency
- file group
- release and incident metadata
- file size and media characteristics
- the 3072-dimensional embedding vector

### Chunk embeddings

The chunk table includes:

- document identity
- chunk identity
- page ranges or sampled-frame metadata
- media type
- chunk text metadata
- the 3072-dimensional embedding vector

## Loading

Document-level example:

```python
from datasets import load_dataset

docs = load_dataset(
    "HawkFranklin-Research/UAP-May8-Embeddings",
    data_files="document_embeddings.parquet",
    split="train",
)
```

Chunk-level example:

```python
from datasets import load_dataset

chunks = load_dataset(
    "HawkFranklin-Research/UAP-May8-Embeddings",
    data_files="chunk_embeddings.parquet",
    split="train",
)
```

## Notes

- This is a derived representation of the archive, not the original evidence.
- The embeddings are suitable for similarity search, clustering, and anomaly detection.
- The dataset should be interpreted alongside the original archive and report, not instead of them.
