---
license: other
pretty_name: UFO Government Files
language:
  - en
size_categories:
  - 100<n<1K
tags:
  - uap
  - ufo
  - government-records
  - archive
---

# UFO Government Files

This dataset is a local staging copy of the publicly released U.S. government UFO/UAP files from the May 8, 2026 release.

It is organized for direct upload to Hugging Face Datasets and is intended for archive analysis, metadata review, and reproducible document inspection.

## Context

> Based on the tremendous interest shown, I will be directing the Secretary of War, and other relevant Departments and Agencies, to begin the process of identifying and releasing Government files related to alien and extraterrestrial life, unidentified aerial phenomena (UAP), and unidentified flying objects (UFOs), and any and all other information connected to these highly complex, but extremely interesting and important, matters. GOD BLESS AMERICA!

## Contents

- `metadata.parquet`: cleaned canonical metadata table
- `metadata.csv`: cleaned canonical metadata table in CSV form
- `metadata_raw.csv`: exact export of the source metadata
- `files/`: mirrored PDFs, videos, and images organized by agency

## Dataset Snapshot

| Metric | Value |
|---|---:|
| Raw metadata rows | 162 |
| Distinct documents | 159 |
| Agencies | 4 |
| File groups | 3 |
| PDFs | 120 |
| Videos | 25 distinct / 28 raw rows |
| Images | 14 |

## Folder Layout

```text
hf-usa-gov/
├── README.md
├── metadata.csv
├── metadata.parquet
├── metadata_raw.csv
└── files/
    ├── Department of State/
    ├── Department of War/
    ├── FBI/
    └── NASA/
```

## Metadata Fields

| Column | Description |
|---|---|
| `Title` | Record title from the release table |
| `Agency` | Source agency or collection label |
| `Release Date` | Release date for the public file set |
| `Incident Date` | Date associated with the underlying incident, if present |
| `Incident Location` | Location associated with the underlying incident, if present |
| `PDF | Image Link` | Original source or local mirror link |
| `Type` | Source file type label |
| `Document Link` | Canonical link used in the local mirror |
| `Source Filename` | Sanitized source filename |
| `File Group` | Normalized storage group, such as `PDF`, `VID`, or `IMG` |
| `Output Path` | Relative path to the mirrored file |

## Notes

- The source release contains 162 metadata rows, but two video items are duplicated, leaving 159 distinct documents.
- `metadata.csv` and `metadata.parquet` are deduplicated on `Output Path`.
- `metadata_raw.csv` preserves the exact exported table before deduplication.
- Missingness is concentrated in `Incident Date` and `Incident Location`, so the dataset is best suited for descriptive and archival analysis rather than direct quantitative inference.
- The local file tree preserves the source agency structure so documents remain easy to trace.

## Source

Public release page:

https://www.war.gov/ufo/

## Suggested Use

This dataset is a good fit for:

- metadata analysis
- document classification
- archive mapping
- agency comparisons
- descriptive evidence review

It is not, by itself, a basis for claims about physical origin or provenance beyond what the source records state.
