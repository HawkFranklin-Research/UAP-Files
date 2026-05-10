"""Build draft case-level evidence packs from file-level UAP archive records.

This is a conservative first pass. It does not fetch external data, does not
call APIs, and does not claim final case identity. It creates candidate case
packs for human review.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ufo_common import PROJECT_ROOT, clean_missing, save_json, slugify


OUT = PROJECT_ROOT / "analysis-3.0" / "case_packs"


def norm(value: object) -> str:
    return clean_missing(value).lower()


def case_label_from_title(title: str) -> str:
    title = clean_missing(title)
    patterns = [
        (r"255[-_ ]?t[-_ ]?763[-_ ]?r1b|gemini 7", "NASA Gemini 7 / 255-t-763-r1b case family"),
        (r"apollo 17", "NASA Apollo 17 case family"),
        (r"apollo 12", "NASA Apollo 12 visual-material packet"),
        (r"apollo 11", "NASA Apollo 11 debriefing/context packet"),
        (r"skylab", "NASA Skylab technical debriefing packet"),
        (r"FBI Photo [AB]\d+", "FBI late-2025 photo packet"),
        (r"FBI September 2023 Sighting", "FBI September 2023 sighting packet"),
        (r"65_HS1-834228961_62-HQ-83894", "FBI 62-HQ-83894 historical archive family"),
        (r"65_HS1-101634279_100-DE", "FBI 100-DE Detroit/Germany historical serial family"),
        (r"State Department UAP Cable", "State Department diplomatic cable family"),
        (r"DOW-UAP-D48|Department of the Air Force Report", "Department of War Air Force 1996 technical report"),
        (r"342_HS1-416511228|Flying Discs 1949", "Department of War Flying Discs 1949 historical report"),
        (r"341_110677|341_110448|Records_Relating", "Department of War Cold War intelligence/historical files"),
        (r"255_413270_UFO", "NASA defense-preparedness historical document"),
        (r"Vandenberg|Launch Summary", "Vandenberg launch summary / technical event packet"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return label
    return ""


def dow_region_label(title: str, location: str) -> str:
    text = f"{title} {location}".lower()
    if not re.search(r"DOW-UAP|Mission Report|Unresolved UAP Report", title, flags=re.IGNORECASE):
        return ""
    regions = [
        ("Persian Gulf", ["persian gulf"]),
        ("Gulf of Oman / Strait of Hormuz", ["gulf of oman", "strait of hormuz"]),
        ("Arabian Gulf", ["arabian gulf"]),
        ("Gulf of Aden / Djibouti", ["gulf of aden", "djibouti"]),
        ("Middle East / Iraq / Syria", ["middle east", "iraq", "syria"]),
        ("Africa", ["africa"]),
        ("INDOPACOM", ["indopacom", "east china sea", "pacific"]),
        ("United Arab Emirates", ["united arab emirates", "uae"]),
    ]
    for label, keys in regions:
        if any(key in text for key in keys):
            return f"Department of War operational reports: {label}"
    return "Department of War operational reports: other/unspecified region"


def state_cable_label(title: str) -> str:
    match = re.search(r"State Department UAP Cable\s+\d+,\s*([^,]+)", title, flags=re.IGNORECASE)
    if match:
        return f"State Department cable: {match.group(1).strip()}"
    return ""


def determine_case(row: pd.Series) -> tuple[str, str, str]:
    title = clean_missing(row.get("title", row.get("Title", "")))
    agency = clean_missing(row.get("agency", row.get("Agency", "")))
    file_group = clean_missing(row.get("file_group", row.get("File Group", "")))
    incident_date = clean_missing(row.get("Incident Date", ""))
    incident_location = clean_missing(row.get("Incident Location", ""))

    state_label = state_cable_label(title)
    if state_label:
        return state_label, "title_pattern:state_department_cable", "high"

    label = case_label_from_title(title)
    if label:
        return label, "title_pattern:known_series_or_mission", "high"

    dow_label = dow_region_label(title, incident_location)
    if dow_label:
        return dow_label, "title_location_pattern:dow_operational_region", "medium"

    if incident_date and incident_location:
        return (
            f"{agency} {incident_location} {incident_date} case candidate",
            "shared_metadata:incident_date_location",
            "medium",
        )

    if agency and file_group:
        return (
            f"{agency} {file_group} singleton/uncertain case candidate: {title}",
            "fallback:agency_modality_singleton",
            "low",
        )

    return "Unclassified singleton/uncertain case candidate", "fallback:unclassified", "low"


def load_source() -> pd.DataFrame:
    docs = pd.read_csv(PROJECT_ROOT / "analysis" / "embeddings" / "document_index.csv").fillna("")
    docs = docs.rename(
        columns={
            "title": "Title",
            "agency": "Agency",
            "file_group": "File Group",
            "output_path": "Output Path",
            "source_filename": "Source Filename",
        }
    )
    meta = pd.read_csv(PROJECT_ROOT / "ufo_release_metadata.csv").fillna("")
    meta = meta.drop_duplicates("Output Path")
    meta_cols = ["Output Path", "Release Date", "Incident Date", "Incident Location", "Type"]
    docs = docs.merge(meta[meta_cols], on="Output Path", how="left")

    clusters = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "cluster_interpretation" / "baseline_kmeans_clusters.csv").fillna("")
    docs = docs.merge(clusters[["document_id", "cluster"]], on="document_id", how="left")

    graph = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "graph_analysis" / "file_graph_nodes.csv").fillna("")
    docs = docs.merge(graph[["document_id", "graph_community", "betweenness", "degree"]], on="document_id", how="left")

    anomaly = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "anomaly_validation" / "anomaly_method_comparison.csv").fillna("")
    docs = docs.merge(anomaly[["document_id", "ensemble_rank", "ensemble_uniqueness"]], on="document_id", how="left")

    usefulness = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "usefulness_proxy" / "scientific_usefulness_proxy.csv").fillna("")
    docs = docs.merge(usefulness[["document_id", "usefulness_proxy_score"]], on="document_id", how="left")
    return docs


def build_file_map(docs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in docs.iterrows():
        label, basis, confidence = determine_case(row)
        rows.append(
            {
                "document_id": row["document_id"],
                "title": row["Title"],
                "agency": row["Agency"],
                "file_group": row["File Group"],
                "incident_date": row.get("Incident Date", ""),
                "incident_location": row.get("Incident Location", ""),
                "cluster": row.get("cluster", ""),
                "graph_community": row.get("graph_community", ""),
                "anomaly_rank": row.get("ensemble_rank", ""),
                "usefulness_proxy_score": row.get("usefulness_proxy_score", ""),
                "output_path": row["Output Path"],
                "case_pack_label": label,
                "basis_for_grouping": basis,
                "confidence": confidence,
            }
        )
    file_map = pd.DataFrame(rows)
    label_to_id = {
        label: f"case_pack_{i:04d}_{slugify(label)[:60]}"
        for i, label in enumerate(sorted(file_map["case_pack_label"].unique()), start=1)
    }
    file_map["case_pack_id"] = file_map["case_pack_label"].map(label_to_id)
    return file_map[
        [
            "case_pack_id",
            "case_pack_label",
            "document_id",
            "title",
            "agency",
            "file_group",
            "incident_date",
            "incident_location",
            "cluster",
            "graph_community",
            "anomaly_rank",
            "usefulness_proxy_score",
            "basis_for_grouping",
            "confidence",
            "output_path",
        ]
    ]


def combine_unique(values: pd.Series) -> str:
    items = sorted({clean_missing(v) for v in values if clean_missing(v)})
    return " | ".join(items)


def summarize_case_packs(file_map: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (case_id, label), group in file_map.groupby(["case_pack_id", "case_pack_label"], sort=True):
        basis_counts = group["basis_for_grouping"].value_counts().to_dict()
        confidence_values = group["confidence"].tolist()
        if "high" in confidence_values:
            confidence = "high"
        elif "medium" in confidence_values:
            confidence = "medium"
        else:
            confidence = "low"
        rows.append(
            {
                "case_pack_id": case_id,
                "case_pack_label": label,
                "file_count": len(group),
                "member_document_ids": " | ".join(group["document_id"].tolist()),
                "member_titles": " | ".join(group["title"].tolist()),
                "agency_set": combine_unique(group["agency"]),
                "file_group_set": combine_unique(group["file_group"]),
                "incident_date_set": combine_unique(group["incident_date"]),
                "incident_location_set": combine_unique(group["incident_location"]),
                "cluster_set": combine_unique(group["cluster"]),
                "graph_community_set": combine_unique(group["graph_community"]),
                "basis_for_grouping": "; ".join(f"{k}:{v}" for k, v in basis_counts.items()),
                "confidence": confidence,
                "case_pack_type": infer_case_type(label, group),
                "needs_human_review": True,
            }
        )
    return pd.DataFrame(rows).sort_values(["file_count", "case_pack_label"], ascending=[False, True])


def infer_case_type(label: str, group: pd.DataFrame) -> str:
    lower = label.lower()
    if "archive" in lower or "historical files" in lower:
        return "archive_compilation_or_series"
    if "photo packet" in lower or "visual-material packet" in lower:
        return "visual_evidence_packet"
    if "operational reports" in lower:
        return "operational_report_family"
    if "cable:" in lower:
        return "single_diplomatic_case_candidate"
    if len(group) == 1:
        return "single_file_case_candidate"
    return "multi_file_case_candidate"


def add_neighbor_support(file_map: pd.DataFrame) -> pd.DataFrame:
    nn = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "nearest_neighbors" / "nearest_neighbors.csv").fillna("")
    doc_to_case = file_map.set_index("document_id")["case_pack_id"].to_dict()
    rows = []
    for _, row in nn[nn["neighbor_rank"] <= 5].iterrows():
        source_case = doc_to_case.get(row["document_id"], "")
        neighbor_case = doc_to_case.get(row["neighbor_document_id"], "")
        rows.append(
            {
                "document_id": row["document_id"],
                "neighbor_document_id": row["neighbor_document_id"],
                "neighbor_rank": row["neighbor_rank"],
                "cosine_distance": row["cosine_distance"],
                "source_case_pack_id": source_case,
                "neighbor_case_pack_id": neighbor_case,
                "same_case_pack": source_case == neighbor_case,
                "source_title": row["title"],
                "neighbor_title": row["neighbor_title"],
            }
        )
    return pd.DataFrame(rows)


def write_markdown_summary(case_packs: pd.DataFrame) -> None:
    lines = [
        "# Candidate Case Packs",
        "",
        "This is a draft case-level evidence map generated from existing file-level metadata, titles, known archive patterns, cluster outputs, and nearest-neighbor relationships.",
        "",
        "It is not a final human-verified case ontology.",
        "",
        "## Largest Candidate Case Packs",
        "",
    ]
    for _, row in case_packs.head(20).iterrows():
        lines.extend(
            [
                f"### {row['case_pack_id']}",
                "",
                f"**Label:** {row['case_pack_label']}",
                "",
                f"**Files:** {row['file_count']}",
                "",
                f"**Agencies:** {row['agency_set']}",
                "",
                f"**Modalities:** {row['file_group_set']}",
                "",
                f"**Incident dates:** {row['incident_date_set'] or 'missing/mixed'}",
                "",
                f"**Incident locations:** {row['incident_location_set'] or 'missing/mixed'}",
                "",
                f"**Basis:** {row['basis_for_grouping']}",
                "",
                f"**Confidence:** {row['confidence']}",
                "",
                f"**Type:** {row['case_pack_type']}",
                "",
            ]
        )
    (OUT / "candidate_case_packs.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    docs = load_source()
    file_map = build_file_map(docs)
    case_packs = summarize_case_packs(file_map)
    neighbor_support = add_neighbor_support(file_map)

    file_map.to_csv(OUT / "file_to_case_map.csv", index=False)
    case_packs.to_csv(OUT / "candidate_case_packs.csv", index=False)
    neighbor_support.to_csv(OUT / "case_neighbor_support.csv", index=False)
    write_markdown_summary(case_packs)

    save_json(
        OUT / "case_pack_summary.json",
        {
            "n_files": int(len(file_map)),
            "n_case_packs": int(len(case_packs)),
            "multi_file_case_packs": int((case_packs["file_count"] > 1).sum()),
            "singleton_case_packs": int((case_packs["file_count"] == 1).sum()),
            "largest_case_pack_file_count": int(case_packs["file_count"].max()),
            "outputs": [
                str(OUT / "file_to_case_map.csv"),
                str(OUT / "candidate_case_packs.csv"),
                str(OUT / "case_neighbor_support.csv"),
                str(OUT / "candidate_case_packs.md"),
            ],
        },
    )
    print(f"Wrote candidate case packs to {OUT}")
    print(f"Files mapped: {len(file_map)}")
    print(f"Candidate case packs: {len(case_packs)}")
    print(f"Multi-file packs: {(case_packs['file_count'] > 1).sum()}")


if __name__ == "__main__":
    main()
