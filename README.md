# UAP-Files

This repository is the GitHub control plane for the May 8 UAP/UFO release analysis.

The goal is not to claim a final answer about UAPs. The goal is to do a careful first-pass computational study of the released files, turn them into a reproducible multimodal evidence map, and identify a publishable research direction from the archive itself.

As of **May 10, 2026**, this project is in the **preliminary analysis stage**:

- the public archive has been downloaded and organized
- the files have been inventoried and embedded
- clustering and anomaly experiments have been run
- a second validation pass has been created
- the current task is to refine the scientific narrative and triage the most useful records for human review

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

## Project Agenda

The central research agenda is simple:

1. Convert the heterogeneous May 8 release into a clean, reproducible dataset.
2. Use embeddings and unsupervised methods to discover stable structure in the archive.
3. Measure how much of that structure comes from agency, modality, and document format.
4. Rank unusual or representative files for manual review.
5. Build a defensible narrative for a small, publishable research paper.

This repo is therefore a methods-and-evidence workspace, not a claims-first repository.

## Analysis Phases

### Analysis 1

[`analysis/`](analysis) contains the first embedding pass:

- inventory
- multimodal embeddings
- clustering
- anomaly scoring
- figures
- report

This is the discovery layer. It answers what is in the archive and what the first embeddings reveal.

### Analysis 2.0

[`analysis-2.0/`](analysis-2.0) contains the validation layer:

- cluster stability checks
- residual analysis
- nearest-neighbor review
- graph analysis
- anomaly agreement checks
- scientific usefulness proxy
- review packet

This is the sanity-check layer. It asks whether the first-stage structure is stable, whether it is driven by archive mechanics, and which files are worth human attention.

### Analysis 2b

[`analysis2b/`](analysis2b) contains the interpretation and evidence-coding layer:

- cluster humanization
- bridge-file review
- anomaly contrast cards
- manual review packets
- cluster cards

This is the interpretation layer. It translates technical structure into evidence families that can be read by humans and used for case-level coding.

### Analysis 3.0

[`analysis-3.0/`](analysis-3.0) contains the case-level grounding layer:

- candidate case packs
- file-to-case mapping
- review templates
- case-pack summaries
- grounded interpretation scaffolding

This is the review-planning layer. It shifts the work from file-level triage into candidate case-level evidence packs that a human can validate.

## Scope

This project is a structured effort to analyze the May 8 release and extend the analysis if additional files appear later.

The intended paper direction is:

> A multimodal evidence map of the May 8 UAP/UFO file release using embeddings, clustering, anomaly triage, and metadata analysis.

That framing keeps the work scientifically defensible. It focuses on reproducible structure, metadata completeness, and review prioritization rather than unsupported causal claims.

The repository intentionally excludes the full raw archive from GitHub. Large PDFs, videos, page-image caches, and extraction caches are hosted or staged elsewhere to keep this repo manageable.

## Starting Points

- Read [`analysis/REPORT.md`](analysis/REPORT.md) for the first-pass embedding analysis.
- Read [`analysis-2.0/REPORT.md`](analysis-2.0/REPORT.md) for the validation layer.
- Read [`DATASET.md`](DATASET.md) for the source archive breakdown.
- Read [`hf-usa-gov/README.md`](hf-usa-gov/README.md) and [`hf-usa-gov-embeddings/README.md`](hf-usa-gov-embeddings/README.md) for the Hugging Face dataset cards.
