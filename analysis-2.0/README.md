# Analysis 2.0: Embedding Validation Layer

This folder contains second-stage validation analyses using the already generated UAP multimodal embeddings.

No new external data was fetched, and no new Gemini embedding calls were made.

## Objectives

1. Test whether clustering is stable across algorithms and random seeds.
2. Measure whether clusters are dominated by agency or file modality.
3. Remove agency/modality effects and test whether structure remains.
4. Build nearest-neighbor tables for retrieval validation.
5. Build a k-nearest-neighbor graph and graph communities.
6. Compare multiple anomaly scoring methods.
7. Create a manual review packet with anomalies, cluster centers, and random baseline files.
8. Create a first-pass scientific usefulness proxy from available metadata.

## Main Subfolders

- `cluster_stability/`: algorithm comparison, stability scores, consensus clusters.
- `residual_analysis/`: raw vs agency/modality-controlled clustering.
- `cluster_interpretation/`: cluster purity and representative files.
- `nearest_neighbors/`: most similar files for every document.
- `graph_analysis/`: kNN graph edges, communities, and bridge files.
- `anomaly_validation/`: anomaly-method comparison and rank agreement.
- `review_packet/`: files selected for human coding.
- `usefulness_proxy/`: automatic metadata-based usefulness scores.
- `figures/`: all generated plots.

## What Moves to Analysis 3.0

The following require new data, OCR/captioning, external corpora, or new API calls, so they are intentionally not part of this folder:

- OCR and descriptor extraction.
- Text-only, metadata-only, and media-only embedding ablations.
- Non-UAP government control corpora.
- Solar/lunar/weather/satellite/military external covariates.
- Case-level manual reconciliation.
