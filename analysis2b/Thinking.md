# Scientific Interpretation and Strategy Memo

*Analysis 2b / Grounded Interpretation Planning*  
*Date: May 10, 2026*

This memo records the current scientific interpretation of the UAP embedding work and the decision logic for turning it into a defensible research paper.

It is not a results table. It is the reasoning layer: what we can conclude, what we cannot conclude, what should be delayed, and what the next grounded interpretation phase should do.

## 1. Core Scientific Result So Far

The strongest result is not that the analysis found "types of UAP."

The strongest result is:

> The embedding space is real and stable enough to be useful, but the strongest structure reflects archive provenance, file format, and institutional language more than confirmed UAP phenomenology.

Analysis 2.0 showed that multiple clustering methods recovered structure. KMeans, Gaussian Mixture, Agglomerative, and Spectral clustering all found broad organization in the 159-file document-level embedding space.

However, the residual analysis is the key scientific result:

```text
Raw clustering silhouette:                    ~0.414
Agency + modality controlled silhouette:      ~0.186
```

This means the archive has structure, but much of its separability is explained by agency and modality. Files cluster partly because they are FBI documents, NASA mission materials, Department of War operational reports, State Department cables, PDFs, images, or videos.

Therefore:

> The current clusters should be interpreted as archive/evidence neighborhoods, not physical categories of UAP.

This prevents the central overclaim:

```text
Bad claim:
Cluster 3 represents a physical UAP subtype.

Good claim:
Cluster 3 is a region of files sharing agency, modality, format, vocabulary, and possibly content style. Human review is required before making any phenomenological interpretation.
```

This is a strong result because it makes the study methodologically honest.

## 2. Paper Direction

The strongest paper is not:

> Can embeddings prove UAP are real?

The strongest paper is:

> Can a heterogeneous government UAP archive be converted into a reproducible multimodal evidence map, and can unsupervised methods identify stable evidence families, confounds, bridge records, and priority files for human review?

Working paper title:

> A Validated Multimodal Evidence Map of a Government UAP Archive: What Unsupervised Embeddings Reveal, What They Confound, and How They Prioritize Human Review

Core paper claim:

> Embedding-based evidence maps can organize heterogeneous UAP archives and prioritize manual review, but unsupervised clusters must be corrected for agency and modality before any phenomenological interpretation is attempted.

This frames the project as a methods + evidence-triage study.

## 3. What the Main Figures Mean

### Cluster Metrics

The clustering methods agree enough to show that the archive has structure. The exact boundaries vary across algorithms, which is expected for mixed historical documents, images, and videos.

Interpretation:

> The archive has stable families, but the borders between families are fuzzy.

This is enough for evidence mapping. It is not enough for physical classification.

### Cluster Purity

Cluster purity is one of the most important validation results.

The clusters are heavily shaped by agency and file modality. This is not a failure. It tells us that the archive has institutional and format structure that must be named and controlled.

Interpretation:

> The clusters currently look more like evidence/archive families than UAP phenomenology families.

### Consensus Matrix

The consensus matrix shows stable blocks of files that repeatedly group together across algorithms and seeds.

Interpretation:

> Dense blocks are archive families. Fuzzy off-block connections are possible bridge records.

The bridge records may be more scientifically interesting than the most anomalous records because they explain how different archive neighborhoods connect.

### kNN Graph

The k-nearest-neighbor graph is currently one of the most useful interpretability tools.

Read it as:

- dense lumps = families of similar records
- isolated lumps = distinct agency/modality groups
- high-betweenness files = conceptual or structural bridge records
- peripheral files = special-case records, rare formats, or outliers

The kNN graph supports a paper claim that the archive can be navigated as connected evidence neighborhoods rather than as a flat file dump.

### Anomaly Rank Correlation

The anomaly methods do not all measure the same kind of unusualness.

Anomaly should be split into several concepts:

| Anomaly type | Meaning |
|---|---|
| Global anomaly | Unusual compared with the whole archive |
| Within-modality anomaly | Unusual compared with files of the same type |
| Within-agency anomaly | Unusual compared with files from the same agency |
| Bridge anomaly | Unusual because it connects communities |
| Usefulness anomaly | Unusual because it is unusually useful for verification |

The ensemble anomaly score is useful for triage, not for declaring a file physically extraordinary.

### Usefulness Proxy

The usefulness-proxy figure supports another important result:

> Embedding uniqueness is not the same thing as scientific usefulness.

Some unusual files are not scientifically useful. Some ordinary-looking files may be highly useful.

Future interpretation should use a two-dimensional view:

| Dimension | Question |
|---|---|
| Uniqueness | Is this file different from the rest of the archive? |
| Scientific usefulness | Can this file support follow-up, verification, or human coding? |

The most valuable files are high in both.

## 4. Provisional Cluster Labels

These are working labels for interpretation. They are not final scientific labels.

They must be verified by opening representative files and coding the actual content.

| Cluster | Provisional label | Reason |
|---:|---|---|
| 0 | Department of War modern operational mission reports | Central files are DOW mission reports around Persian Gulf, Arabian Gulf, Gulf of Oman, Strait of Hormuz, Iran, Djibouti, and related operational regions |
| 1 | FBI late-2025 photo / visual evidence packet | Central files are FBI Photo B-series records from Western United States, Late 2025 |
| 2 | State Department diplomatic cable / geopolitical sighting family | Central files are State Department UAP cables from Kazakhstan, Georgia, Turkmenistan, Mexico, Papua New Guinea, plus related geopolitical reports |
| 3 | FBI historical HQ archive sections | Central files are `65_HS1-834228961_62-HQ-83894_Section_*` and related serials |
| 4 | NASA lunar / space visual material | Central files are NASA Apollo visual materials and space-domain records, with Gemini materials nearby |

These should be described as evidence families, not UAP types.

Correct language:

> Cluster 0 appears to be a modern operational Department of War reporting family.

Incorrect language:

> Cluster 0 is a military UAP subtype.

## 5. Cluster-Specific Interpretation Questions

### Cluster 0: Department of War Modern Operational Mission Reports

Likely meaning:

> A modern operational/military-region evidence family, probably shaped by Department of War report templates and airspace/maritime operational context.

Questions:

- Are these single-incident reports or repeated reporting templates?
- Are the videos and PDFs paired to the same events?
- What sensors appear: EO/IR, radar, visual, shipboard, aircraft, drone?
- Do the files mention altitude, speed, bearing, distance, range, or duration?
- Are locations precise enough for external checking?
- Are repeated object descriptors present?
- Are these operational safety/range-fouler-style records?
- Do Gulf / Strait / Middle East reports represent a reporting environment rather than a phenomenon?

### Cluster 1: FBI Late-2025 Photo / Visual Evidence Packet

Likely meaning:

> A tight visual-evidence packet, probably driven by shared image-like content and FBI packet structure.

Questions:

- Are these all images from one event?
- Are they near-duplicates or different viewpoints?
- Are they photos converted into PDFs?
- Is the composite sketch part of the same broader FBI visual family?
- Is the cluster scientifically useful, or mostly visual without precise location/time metadata?
- Do the photos contain metadata or attached witness statements?

### Cluster 2: State Department Diplomatic Cable / Geopolitical Sighting Family

Likely meaning:

> International/diplomatic UAP reporting, mediated through embassy, diplomatic, or intelligence-reporting language.

Questions:

- Are these first-hand reports, second-hand reports, embassy relays, or newspaper summaries?
- Do they include precise dates and locations?
- Who are the witnesses?
- Why does the Department of War 1955 Azerbaijan file join this family?
- Is the commonality diplomatic language, foreign geography, or actual content?
- Are these more useful for external historical/astronomical checking than average files?

### Cluster 3: FBI Historical HQ Archive Sections

Likely meaning:

> A historical FBI archive-family cluster, probably driven by a large HQ file split into sections.

Questions:

- Is this one large historical FBI UFO file divided into sections?
- Are the sections mostly administrative correspondence or case-rich material?
- Do the PDFs contain many subcases?
- Are the sections central because of repeated headers, layout, and archival language?
- Which serials inside the cluster are event-specific?
- Should this cluster be broken into case-level subrecords?

Important note:

> Some PDFs are containers, not cases.

This is one reason file-level embeddings are not enough for final scientific interpretation.

### Cluster 4: NASA Lunar / Space Visual Material

Likely meaning:

> A space-domain evidence family mixing visual mission materials, transcripts, crew debriefings, and mission-context artifacts.

Questions:

- Are the Apollo image files actual UAP-related observations or mission-context images?
- Are the images selected because of visible objects, reflections, artifacts, or documentation context?
- Is the Gemini video part of the same evidence family or a bridge between transcript and video neighborhoods?
- Are NASA records more externally verifiable because timing/orbit/mission logs exist?
- Should NASA records be split into visual artifacts, transcripts, and crew debriefings?

## 6. Bridge Files May Be More Important Than Anomalies

Anomalies are exciting, but bridge files may be more scientifically valuable.

Bridge files explain how different archive neighborhoods connect.

Interpretation:

> Cluster centers are typical files. Anomalies are unusual files. Bridge files are conceptual connectors.

Bridge-file questions:

- Which communities does the file connect?
- Is it a mixed-media record?
- Is it a summary document?
- Does it mention multiple agencies?
- Does it bridge historical and modern records?
- Does it bridge NASA/space-domain and military-domain records?
- Does it bridge diplomatic reporting and military reporting?
- Is it scientifically useful, or only structurally central?
- What would be lost if this file were removed?
- Is it a good case-study file for the paper?

Promising bridge files include:

- `DOW-UAP-D8, Mission Report, Djibouti, 2025`
- `DOW-UAP-PR43, Unresolved UAP Report, Africa, 2025`
- `DOW-UAP-D48, Department of the Air Force Report, 1996`
- `342_HS1-416511228_319.1 Flying Discs 1949`
- `65_HS1-834228961_62-HQ-83894_Section_9`
- `FBI September 2023 Sighting - Serial 5`
- `DOW-UAP-PR46, Unresolved UAP Report, INDOPACOM, 2024`
- `255-t-763-r1b-excerpt`

## 7. Top Anomalies: Correct Interpretation

The top anomaly list is not a list of the "most extraordinary UAP events."

It is a list of files that are unusual under the embedding geometry.

For each anomaly, ask:

- Is this unusual because of content?
- Is this unusual because of format?
- Is this unusual because it belongs to a rare agency or modality?
- Is this a true case or a weird document type?
- Are its nearest neighbors human-meaningful?
- Does it have high scientific usefulness?
- Should it be included in a follow-up case study?
- Is it part of a larger case pack?
- Does its anomaly score survive within-agency comparison?
- Would a human have selected it without the algorithm?

The best anomaly is:

> high uniqueness + high usefulness + interpretable reason.

## 8. Pilot Manual Coding Status

The manual review infrastructure exists, but it is not complete.

Current status:

```text
Manual review rows:         75
Coded rows:                  5
Uncoded rows:               70
```

The 5 coded rows are pilot examples, not a finished manual review.

They should be described as:

> model-assisted draft coding of five top-anomaly files

not:

> completed human-coded review

The pilot examples suggest a useful distinction:

- some anomalies are format anomalies
- some anomalies are content-rich cases
- some top anomalies are related to the same underlying case family

Example case-family warning:

> `255-t-763-r1b-excerpt`, `255_t_763_r1b_transcripts`, and related Gemini transcript files may represent the same broader Gemini 7 case family.

This means file-level analysis is not enough. The next scientific unit should be the case pack.

## 9. Why File-Level Is Not Enough

The current embedding dataset has 159 file-level records.

Science needs case-level units.

Examples:

- NASA Gemini 7 video/transcript records may belong to one case family.
- FBI Photo B-series files may be one event packet.
- DOW mission report PDFs and PR videos may pair together.
- FBI HQ sections may contain many separate subcases.
- State Department cables may be one case per cable.
- Apollo visual files may cluster by mission, not necessarily independent event.

Therefore, the next phase should move from:

```text
file-level archive mapping
```

to:

```text
case-level evidence mapping
```

## 10. What to Slash for Now

Do not pursue these yet:

1. Prediction of the next sighting or "visit."
2. Solar/lunar/tithi/oil/geopolitical correlations.
3. More clustering algorithms.
4. Quantum experiments.
5. Calling clusters UAP types.
6. Treating model-assisted coding as completed human coding.
7. Publishing only embedding plots without source-file interpretation.

Why:

- Prediction requires a real event stream, not a selected release archive.
- External covariates require a clean case-level table with reliable dates and locations.
- More clustering does not solve the interpretation problem.
- Quantum methods would be decorative at this stage.
- The current clusters are evidence families, not physical categories.

## 11. Analysis 3.0 Direction

Analysis 3.0 should be:

> Grounded Interpretation of the Embedding Map

No new embeddings.

No external covariates.

No solar/lunar/weather/geopolitical analysis yet.

The goal is to connect machine outputs back to actual source files.

## 12. Analysis 3.0 Deliverables

### A. Repaired Review Packet

Create:

```text
analysis-3.0/review_packet/review_sample_repaired.csv
```

Use `document_id` as the primary key and include:

- cluster
- graph_community
- anomaly_rank
- usefulness_proxy_score
- output_path
- nearest_neighbor_1
- nearest_neighbor_2
- nearest_neighbor_3, where available

### B. Candidate Case Packs

Create:

```text
analysis-3.0/case_packs/candidate_case_packs.csv
```

Columns:

```text
case_pack_id
case_pack_label
member_document_ids
member_titles
agency_set
file_group_set
incident_date_set
incident_location_set
basis_for_grouping
confidence
```

Candidate grouping logic:

- same/similar titles
- same incident date/location
- NASA transcript/video pairs
- FBI photo/serial groups
- DOW mission report / unresolved report pairs
- nearest-neighbor relationships

### C. Manual Coding Batches

Create:

```text
batch_01_top_anomalies.csv
batch_02_bridge_files.csv
batch_03_cluster_centers.csv
batch_04_random_baseline.csv
```

Preserve the 30-column manual-review schema.

Existing 5 coded rows should be marked as:

```text
model_assisted_draft = true
```

Uncoded rows should remain blank, not hallucinated.

### D. Interpretation Templates

Create:

```text
cluster_cards_interpretation_template.md
anomaly_cards_interpretation_template.md
bridge_cards_interpretation_template.md
```

These should make interpretation systematic and auditable.

## 13. Key Tests After Manual Coding

Once the 75-file packet is coded, run:

| Review group | Mean human usefulness score |
|---|---:|
| Top anomalies | ? |
| Bridge files | ? |
| Cluster centers | ? |
| Random baseline | ? |

Main empirical question:

> Does algorithmic triage select more scientifically useful files than random sampling?

Also test:

| Review group | % content anomaly | % format anomaly |
|---|---:|---:|
| Top anomalies | ? | ? |
| Bridge files | ? | ? |
| Cluster centers | ? | ? |
| Random baseline | ? | ? |

This answers:

> Are embedding anomalies driven by content or format?

## 14. Allowed and Disallowed Conclusions

Allowed:

> The archive has stable multimodal embedding structure.

Allowed:

> Much of that structure is explained by agency, modality, archive format, and institutional language.

Allowed:

> Embeddings are useful for triage, retrieval, bridge-file discovery, and manual-review prioritization.

Allowed after manual review:

> Algorithmic triage does or does not enrich for scientifically useful files compared with random baseline.

Not allowed:

> The clusters are physical UAP types.

Not allowed:

> A high anomaly score means a file is more real, more unexplained, or extraterrestrial.

Not allowed:

> The archive can predict future sightings or visits.

Not allowed yet:

> Solar/lunar/oil/geopolitical variables are related to UAP events.

## 15. Final Working Conclusion

The research is in a good position.

The correct next move is disciplined interpretation, not more unsupervised-learning experimentation.

Current best conclusion:

> The May 8 UAP archive can be converted into a reproducible multimodal evidence map. The embedding space has stable and useful structure, but much of that structure reflects agency, modality, and archival format. Therefore, the correct scientific use of the model is triage, retrieval, case-pack construction, and manual-review prioritization, not direct interpretation of clusters as UAP types.

Next decisive question:

> Did the algorithm actually help identify scientifically useful UAP records, or did it mostly find unusual document formats?

That answer requires the remaining 70 review rows to be coded and compared against the anomaly, bridge, cluster-center, and random-baseline groups.

