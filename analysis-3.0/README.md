# Analysis 3.0: Candidate Case-Level Evidence Mapping

This phase begins converting the archive from file-level mapping to case-level evidence mapping.

It does not fetch new data and does not run new embedding calls.

## Purpose

File-level analysis treats each PDF, image, or video as a separate unit. That is useful for archive mapping, but it is not enough for scientific interpretation because several files can describe the same underlying event, mission, visual packet, or historical compilation.

Case-level mapping asks:

> Which files should be reviewed together as one evidence object?

## Outputs

```text
case_packs/file_to_case_map.csv
case_packs/candidate_case_packs.csv
case_packs/case_neighbor_support.csv
case_packs/candidate_case_packs.md
case_packs/case_pack_summary.json
```

## Current Summary

```text
Files mapped: 159
Candidate case packs: 37
Multi-file packs: 16
Singleton packs: 21
Largest pack: 32 files
```

## Important Caveat

These are candidate case packs, not final human-verified cases.

The grouping is rule-based and uses:

- known title patterns
- agency and file naming conventions
- incident date/location metadata
- mission or archive series names
- nearest-neighbor support

Human review is still required before these become final case IDs.

