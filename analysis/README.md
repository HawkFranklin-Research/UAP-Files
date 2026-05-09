# Analysis 1.0: Embedding Exploration

This folder captures the first-stage analysis of the May 8 UAP/UFO file release.

The goal of this stage was to turn the public archive into a structured research workspace:

- build a document inventory
- generate multimodal embeddings
- inspect clustering and anomaly behavior
- produce a first-pass evidence map

The heavier operational artifacts used to build the analysis are kept out of GitHub. The public-facing report and summary figures in this folder are the main entry points.

## Key Outputs

- `REPORT.md`: narrative summary of the first-stage analysis
- `inventory_summary.json`: compact inventory metadata
- `figures/`: overview plots for the release

## Related Datasets

- Raw archive on Hugging Face: `HawkFranklin-Research/UAP-May8`
- Derived embeddings on Hugging Face: `HawkFranklin-Research/UAP-May8-Embeddings`

## What This Stage Is For

Use this folder when you want to understand:

- what kinds of files are in the release
- how the archive breaks down by agency and modality
- what the first embedding pass suggests about structure and outliers

For deeper validation, see `analysis-2.0/`.
