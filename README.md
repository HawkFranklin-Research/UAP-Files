# UAP-Files

This repository is the GitHub control plane for the May 8 UAP/UFO release analysis.

The heavy source archive and the derived dataset mirrors live on Hugging Face. GitHub here is for:

- analysis code
- analysis reports
- small derived tables
- figures
- repo-level documentation

## Layout

- [`DATASET.md`](DATASET.md): source archive inventory and metadata profile
- [`analysis/`](analysis): first-pass multimodal embedding analysis
- [`analysis-2.0/`](analysis-2.0): second-pass validation layer
- [`scripts/`](scripts): reproducibility and analysis scripts
- [`hf-usa-gov/README.md`](hf-usa-gov/README.md): raw archive dataset card for Hugging Face
- [`hf-usa-gov-embeddings/README.md`](hf-usa-gov-embeddings/README.md): embedding dataset card for Hugging Face

## Published Datasets

- Raw archive: `HawkFranklin-Research/UAP-May8`
- Embeddings and derived analysis package: `HawkFranklin-Research/UAP-May8-Embeddings`

## Analysis Phases

### Analysis 1

[`analysis/`](analysis) contains the first embedding pass:

- inventory
- multimodal embeddings
- clustering
- anomaly scoring
- figures
- report

### Analysis 2.0

[`analysis-2.0/`](analysis-2.0) contains the validation layer:

- cluster stability checks
- residual analysis
- nearest-neighbor review
- graph analysis
- anomaly agreement checks
- scientific usefulness proxy
- review packet

## Scope

This project is a structured effort to analyze the May 8 release and extend the analysis if additional files appear later.

The repository intentionally excludes the full raw archive from GitHub. Large PDFs, videos, page-image caches, and extraction caches are hosted or staged elsewhere to keep this repo manageable.

## Starting Points

- Read [`analysis/REPORT.md`](analysis/REPORT.md) for the first-pass embedding analysis.
- Read [`analysis-2.0/REPORT.md`](analysis-2.0/REPORT.md) for the validation layer.
- Read [`DATASET.md`](DATASET.md) for the source archive breakdown.
