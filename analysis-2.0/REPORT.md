# Analysis 2.0 Report

## Purpose

Analysis 2.0 validates the first embedding evidence map without collecting new data and without making new API calls.

The central question is:

> Are the embedding clusters and anomaly rankings stable and useful, or are they mostly artifacts of agency, modality, and document format?

This folder answers that question using the 159 completed document-level embeddings from `analysis/embeddings/document_embeddings.npz`.

## What Was Executed

The full run was performed with:

```bash
python3 scripts/ufo_analysis2_validation.py
```

The script created:

- cluster stability benchmarks
- agency/modality residual analysis
- cluster purity and representative-file tables
- nearest-neighbor retrieval tables
- k-nearest-neighbor graph communities
- anomaly-method validation
- a human review packet
- a metadata-based scientific usefulness proxy

No external data was fetched.

No new embeddings were generated.

## 1. Cluster Stability

Folder:

```text
analysis-2.0/cluster_stability/
```

Files:

```text
cluster_metrics.csv
cluster_stability_pairs.csv
consensus_clusters.csv
consensus_matrix.npy
```

Figures:

```text
figures/cluster_metrics_overview.png
figures/cluster_stability_heatmap.png
figures/consensus_matrix.png
```

Mean clustering results by method:

| Method | Silhouette | Agency Purity | Modality Purity | Davies-Bouldin |
|---|---:|---:|---:|---:|
| Agglomerative | 0.426 | 0.824 | 0.799 | 1.264 |
| Gaussian Mixture | 0.352 | 0.818 | 0.869 | 1.833 |
| KMeans | 0.355 | 0.822 | 0.869 | 1.826 |
| Spectral | 0.366 | 0.780 | 0.855 | 1.961 |

Interpretation:

The clustering is not random. Multiple algorithms recover structure. However, the clusters have high agency and modality purity, meaning a large part of the structure is related to where the file came from and what type of file it is.

This supports the main criticism:

> Some clusters may reflect archive structure rather than UAP phenomenology.

That is not a failure. It is an important result.

## 2. Residual Agency/Modality Analysis

Folder:

```text
analysis-2.0/residual_analysis/
```

Files:

```text
residual_cluster_comparison.csv
residual_clusters.csv
residual_projections.csv
```

Figure:

```text
figures/residual_validation_overview.png
```

Results:

| Variant | Silhouette | Agency Purity | Modality Purity |
|---|---:|---:|---:|
| Raw embeddings | 0.414 | 0.862 | 0.792 |
| Agency controlled | 0.230 | 0.635 | 0.755 |
| Modality controlled | 0.297 | 0.830 | 0.755 |
| Agency + modality controlled | 0.186 | 0.635 | 0.755 |

Interpretation:

Once agency and modality are mathematically controlled, cluster separability becomes much weaker.

This is one of the most important findings in Analysis 2.0:

> The embedding space contains strong structure, but much of the strongest structure is explained by agency and file modality.

For a paper, this is a defensible and honest result. It prevents overclaiming.

## 3. Cluster Interpretation

Folder:

```text
analysis-2.0/cluster_interpretation/
```

Files:

```text
baseline_kmeans_clusters.csv
cluster_purity.csv
cluster_representatives.csv
```

Figure:

```text
figures/cluster_purity_overview.png
```

Purpose:

This identifies what each cluster is made of and which files are closest to each cluster center.

The `cluster_representatives.csv` file is especially useful for manual review because it gives representative files rather than only unusual files.

## 4. Nearest-Neighbor Retrieval

Folder:

```text
analysis-2.0/nearest_neighbors/
```

Files:

```text
nearest_neighbors.csv
top_anomaly_neighbors.csv
```

Figure:

```text
figures/nearest_neighbor_distance_distribution.png
```

Purpose:

For every file, this table lists the most similar files in the embedding space.

This is useful for:

- validating whether embeddings retrieve meaningfully related records
- finding near-duplicates
- explaining anomaly scores
- building a future search interface

## 5. kNN Graph Analysis

Folder:

```text
analysis-2.0/graph_analysis/
```

Files:

```text
file_knn_edges.csv
file_graph_nodes.csv
bridge_files.csv
```

Figure:

```text
figures/embedding_knn_graph.png
```

The graph analysis found 6 graph communities:

| Community | Files |
|---:|---:|
| 0 | 53 |
| 1 | 49 |
| 2 | 25 |
| 3 | 13 |
| 4 | 11 |
| 5 | 8 |

Interpretation:

The archive separates into several neighborhoods. Some files act as bridge files between neighborhoods. These bridge files are good candidates for manual review because they may connect otherwise distinct subgroups.

## 6. Anomaly Validation

Folder:

```text
analysis-2.0/anomaly_validation/
```

Files:

```text
anomaly_method_comparison.csv
anomaly_rank_correlation.csv
top25_ensemble_anomalies.csv
```

Figures:

```text
figures/anomaly_rank_correlation.png
figures/top_anomaly_method_agreement.png
```

This analysis compares several anomaly signals:

- global centroid distance
- nearest-neighbor distance
- Isolation Forest
- Local Outlier Factor
- cluster residual distance
- modality residual distance

Top 10 ensemble anomalies:

| Rank | Title | Agency | Type | Score |
|---:|---|---|---|---:|
| 1 | FBI September 2023 Sighting - Composite Sketch | FBI | PDF | 0.9853 |
| 2 | 255-t-763-r1b-excerpt | NASA | VID | 0.9801 |
| 3 | 65_HS1-101634279_100-DE-18221_Serial_844 | FBI | PDF | 0.9570 |
| 4 | 341_110677_Numerical_File,_5-2500 | Department of War | PDF | 0.9319 |
| 5 | NASA-UAP-D5, Apollo 17 Crew Debriefing for Science, 1973 | NASA | PDF | 0.9245 |
| 6 | 65_HS1-834228961_62-HQ-83894_Serial_403 | FBI | PDF | 0.9130 |
| 7 | State Department UAP Cable 1, Papua New Guinea, January 28, 1985 | Department of State | PDF | 0.8742 |
| 8 | 255_t_763_r1b_transcripts | NASA | PDF | 0.8695 |
| 9 | 255_413270_UFO's_and_Defense_What_Should_we_Prepare_For | NASA | PDF | 0.8627 |
| 10 | State Department UAP Cable 4, Ashgabat, Turkmenistan, November 5, 2004 | Department of State | PDF | 0.8590 |

Interpretation:

The top anomaly list changed slightly from Analysis 1.0 because this version compares multiple anomaly methods instead of using only the first ensemble formula.

That is useful. It means the anomaly ranking should be treated as a triage list, not as a fixed truth.

## 7. Manual Review Packet

Folder:

```text
analysis-2.0/review_packet/
```

Files:

```text
review_sample.csv
top_anomalies.csv
cluster_centers.csv
random_baseline.csv
```

Figure:

```text
figures/review_groups_embedding_map.png
```

The review packet contains:

| Group | Count |
|---|---:|
| Top anomalies | 25 |
| Cluster centers | 25 |
| Random baseline | 25 |

Purpose:

This is the bridge from algorithmic analysis to scientific interpretation.

The next human-coding step should review these 75 files and ask:

- Is the file scientifically useful?
- Is the file unusual because of content or format?
- Does it contain event date/location/sensor details?
- Could it be externally verified?
- Does the algorithmic ranking match human judgment?

## 8. Scientific Usefulness Proxy

Folder:

```text
analysis-2.0/usefulness_proxy/
```

Files:

```text
scientific_usefulness_proxy.csv
usefulness_by_agency_modality.csv
```

Figure:

```text
figures/usefulness_proxy_overview.png
```

Purpose:

This creates a first-pass automatic score for whether a file is useful for scientific follow-up.

It uses available metadata and processing facts such as:

- agency known
- file type known
- incident date available
- incident location available
- raw media available
- PDF page count known
- video duration known
- image dimensions known
- source path known

This is not a final scientific usefulness score. It is a proxy that should be improved with manual coding.

## Main Conclusion

Analysis 2.0 strengthens the evidence map by showing both value and limitations.

The embeddings produce stable, non-random structure. But much of the structure is explained by agency and modality. After controlling for those factors, cluster separability drops substantially.

This supports a cautious scientific claim:

> The May 8 UAP release can be organized into a reproducible multimodal evidence map. Embedding methods are useful for triage, retrieval, and prioritization, but clusters and anomalies must be interpreted in light of agency, modality, and archival-format effects.

## What Should Move to Analysis 3.0

The following require new data, OCR, captioning, external corpora, or manual coding:

- OCR/text extraction from PDFs
- descriptor extraction for object shapes, motion, sensors, and witness terms
- metadata-only/text-only/media-only embedding ablations
- non-UAP government control corpus
- satellite/weather/lunar/solar/geopolitical covariates
- manual case-level table
- human-coded scientific usefulness score

