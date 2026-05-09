# UFO Release Dataset

This project mirrors the May 8, 2026 UAP/UFO file release into a local, analyzable dataset.

The canonical local artifacts are:

- [`ufo_release_metadata.csv`](ufo_release_metadata.csv)
- [`ufo_release/`](ufo_release)
- [`scripts/download_ufo_files.py`](scripts/download_ufo_files.py)
- [`scripts/recover_missing_ufo_file.py`](scripts/recover_missing_ufo_file.py)

## What This Dataset Is

This is a structured mirror of the released UFO/UAP documents and media files published on the public release page.
It is not a claim dataset and it is not a validated scientific corpus.
Its value is in transparency, reproducibility, and downstream content analysis.

The dataset contains:

- Documents
- Videos
- Images
- Per-record metadata
- Local file paths for the downloaded mirror

## Dataset Snapshot

| Metric | Value |
|---|---:|
| Raw metadata rows | 162 |
| Distinct documents on disk | 159 |
| Physical files in `ufo_release/` | 159 |
| Agencies | 4 |
| File groups | 3 |
| Release dates represented | 1 |

Important note:

- The raw metadata table contains 162 rows.
- Two video items are repeated in the metadata, so there are 159 distinct documents.
- The local mirror on disk also contains 159 files.

## Column Guide

The metadata table has these fields:

| Column | Meaning |
|---|---|
| `Title` | Human-readable title from the release table |
| `Agency` | Source agency or collection label |
| `Release Date` | Date the file appeared in the public release |
| `Incident Date` | Date associated with the underlying incident, if provided |
| `Incident Location` | Location associated with the incident, if provided |
| `PDF | Image Link` | Original download link or local mirror link |
| `Type` | File type label from the release table |
| `Document Link` | Link used for the local/downloaded document |
| `Source Filename` | Sanitized filename used in the local mirror |
| `File Group` | Normalized storage group such as `PDF`, `VID`, or `IMG` |
| `Output Path` | Relative path inside `ufo_release/` |

## Storage Layout

The local mirror is organized by agency and file group:

```text
ufo_release/
  Department of State/
    PDF/
  Department of War/
    PDF/
    VID/
  FBI/
    PDF/
    IMG/
  NASA/
    PDF/
    IMG/
    VID/
```

This is a useful structure for later analysis because it preserves both the source agency and the media type.

## Document-Type Breakdown

### Raw rows

| File group | Rows |
|---|---:|
| `PDF` | 120 |
| `VID` | 28 |
| `IMG` | 14 |

### Distinct documents

| File group | Distinct documents |
|---|---:|
| `PDF` | 120 |
| `VID` | 25 |
| `IMG` | 14 |

The duplicate rows are in the video set, so the raw row count overstates the number of unique videos.

## Agency Breakdown

### Raw rows by agency

| Agency | Rows |
|---|---:|
| Department of War | 82 |
| FBI | 56 |
| NASA | 16 |
| Department of State | 8 |

### Distinct documents by agency

| Agency | Distinct documents |
|---|---:|
| Department of War | 79 |
| FBI | 56 |
| NASA | 16 |
| Department of State | 8 |

### Agency by file group

| Agency | PDF | VID | IMG |
|---|---:|---:|---:|
| Department of State | 8 | 0 | 0 |
| Department of War | 55 | 24 | 0 |
| FBI | 48 | 0 | 8 |
| NASA | 9 | 1 | 6 |

## Missing Data Profile

### Raw metadata

| Field | Missing |
|---|---:|
| `Incident Date` | 61 |
| `Incident Location` | 47 |
| `Release Date` | 0 |
| `Type` | 0 |
| `Document Link` | 0 |
| `Output Path` | 0 |

### Distinct documents

| Field | Missing |
|---|---:|
| `Incident Date` | 61 |
| `Incident Location` | 47 |

The missingness is not random across media types:

- Videos have the best location completeness.
- PDFs carry most of the missing incident dates.
- Images usually have a location or a limited visual caption, but not always both.

### Missingness by file group

| File group | Has incident date | Missing incident date | Has location | Missing location |
|---|---:|---:|---:|---:|
| `PDF` | 74 | 46 | 81 | 39 |
| `VID` | 13 | 15 | 28 | 0 |
| `IMG` | 14 | 0 | 6 | 8 |

## Incident Date Profile

The `Incident Date` field is heterogeneous. It contains exact dates, approximate dates, single years, and free-text labels such as `Late 2025`.

### Distinct-document distribution by date form

| Date form | Count |
|---|---:|
| Missing/NA | 61 |
| 2020s | 35 |
| Late 2025 | 33 |
| 1960s (1969) | 6 |
| 1950s | 5 |
| 1940s | 4 |
| 2000s | 4 |
| 1960s | 3 |
| 1990s | 2 |
| 1970s (1972) | 2 |
| 2010s | 1 |
| 1960s (1965) | 1 |
| 1980s | 1 |
| Other text/date | 1 |

### Interpretation

This means the dataset is not ready for naive time-series analysis without cleaning.
For example:

- `12/5/65` and `1965` both refer to the 1960s, but they are encoded differently.
- `Late 2025` is an approximate period, not a precise date.
- `10/28/2001-10/29/2001` is a date range, not a single incident date.

If you need a consistent chronology, normalize these values into:

- exact date
- month/year
- year
- approximate period
- missing

## Location Profile

There are 36 distinct non-missing incident locations.

Top locations:

| Location | Count |
|---|---:|
| Missing | 47 |
| Western United States | 25 |
| Syria | 12 |
| Moon | 9 |
| Iraq | 8 |
| Arabian Gulf | 7 |
| Persian Gulf | 6 |
| United States | 5 |
| Mediterranean Sea | 4 |
| Greece | 3 |
| Middle East | 3 |

### Interpretation

The location field mixes:

- Geographic places
- Regional theater labels
- Orbit/space labels
- Broad catch-all categories

That means location is useful for descriptive grouping, but it is not yet a standardized geospatial variable.

## Content Pattern by Agency

### Department of War

This is the largest and most operationally focused subset.
It contains:

- Mission reports
- Unresolved UAP reports
- Range fouler debriefs
- Reporting forms
- Email correspondence
- Historical intelligence and incident summaries

The video set is concentrated here, and it is the most likely subset for structured content analysis.

### FBI

The FBI subset is mostly PDFs plus a smaller image set.
It includes:

- Section files
- Serial files
- Photo series `A` and `B`
- A September 2023 sighting package

This part of the corpus is better suited to document classification, record linkage, and case-based review than to event-scale statistical analysis.

### NASA

The NASA subset is small but mixed:

- Apollo transcripts
- Crew debriefings
- Skylab material
- Images from Apollo missions
- One video excerpt

This subset is especially useful for historical archival analysis and for tracing how UAP-related mentions appear in mission records.

### Department of State

All Department of State records are PDFs.
They are mostly cables and statements from overseas posts.

This subset is good for diplomatic-history style reading and for comparing how UAP incidents were documented outside the defense and law-enforcement channels.

## Data Quality Notes

1. The metadata has duplicate rows for two video items.
2. Most `Document Link` values are local `file://` mirrors.
3. One recovered file still points to the original `https://` source URL.
4. The `Type` and `File Group` fields are aligned, so the table is already normalized enough for basic analysis.
5. The release date is constant across the dataset, so it is not an analytic variable.

## Recommended Cleaning Steps

If you are building analysis notebooks on top of this dataset, do this first:

1. Deduplicate on `Output Path` or `Document Link`.
2. Normalize `Incident Date` into structured date buckets.
3. Standardize location names.
4. Add a derived `year` column where possible.
5. Keep a second field for approximate dates such as `Late 2025`.
6. Preserve the raw values in case you need to audit the transformation later.

## Best Uses

This dataset is strong for:

- Descriptive statistics
- Content analysis
- Archive mapping
- Agency-by-agency comparison
- Media-type comparison
- Metadata completeness scoring
- Document retrieval experiments

This dataset is weak for:

- Causal claims
- Physical inference from the files alone
- Any conclusion that depends on complete chain-of-custody data
- Any unverified claim about non-human origin

## Suggested Analysis Questions

- Which agency contributes the most complete incident metadata?
- Which file types are most likely to omit incident location?
- Which locations recur most often across the release?
- Which records are only approximate in time?
- Which files are best candidates for manual case review?
- How much of the corpus is historical archival material versus modern operational reporting?

## Provenance

The local mirror was created from the public release page and then organized into a file system structure.
The download logic lives in [`scripts/download_ufo_files.py`](scripts/download_ufo_files.py).
The missing item recovery logic lives in [`scripts/recover_missing_ufo_file.py`](scripts/recover_missing_ufo_file.py).

If you want this dataset to support a paper, the next useful step is to generate a cleaned analysis table from `ufo_release_metadata.csv` and keep the raw metadata untouched.
