"""Build Analysis 3.0 grounded interpretation scaffolding.

This script does not modify analysis2b/manual_review/*. It creates repaired,
join-complete review/batch/template files under analysis-3.0/.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ufo_common import PROJECT_ROOT, clean_missing


OUT = PROJECT_ROOT / "analysis-3.0"
REVIEW_OUT = OUT / "review_packet"
MANUAL_OUT = OUT / "manual_review"
TEMPLATE_OUT = OUT / "interpretation_templates"

BASE_SCHEMA = [
    "file_id",
    "title",
    "review_group",
    "cluster",
    "graph_community",
    "agency",
    "file_group",
    "human_document_genre",
    "case_or_compilation",
    "single_event_or_multi_event",
    "event_date_precision",
    "event_location_precision",
    "primary_location",
    "witness_type",
    "sensor_type",
    "raw_media_present",
    "object_shape",
    "object_color",
    "motion_description",
    "duration_available",
    "altitude_speed_available",
    "official_explanation_present",
    "resolution_status",
    "external_verification_possible",
    "scientific_usefulness_score_0_10",
    "reason_for_scientific_usefulness",
    "why_algorithm_selected_this_file",
    "content_unique_or_format_unique",
    "reviewer_confidence_0_3",
    "short_human_summary",
]


def ensure_dirs() -> None:
    for path in [REVIEW_OUT, MANUAL_OUT, TEMPLATE_OUT]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_doc_index(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "document_id": "file_id",
            "Title": "title",
            "Agency": "agency",
            "File Group": "file_group",
            "Output Path": "output_path",
        }
    )


def load_reference_tables() -> dict[str, pd.DataFrame]:
    doc = pd.read_csv(PROJECT_ROOT / "analysis" / "embeddings" / "document_index.csv").fillna("")
    doc = doc.rename(
        columns={
            "document_id": "file_id",
            "title": "title",
            "agency": "agency",
            "file_group": "file_group",
            "output_path": "output_path",
        }
    )
    clusters = normalize_doc_index(
        pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "cluster_interpretation" / "baseline_kmeans_clusters.csv").fillna("")
    )
    graph = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "graph_analysis" / "file_graph_nodes.csv").fillna("")
    graph = graph.rename(columns={"document_id": "file_id"})
    anomaly = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "anomaly_validation" / "anomaly_method_comparison.csv").fillna("")
    anomaly = anomaly.rename(
        columns={
            "document_id": "file_id",
            "ensemble_rank": "anomaly_rank",
            "ensemble_uniqueness": "anomaly_uniqueness",
        }
    )
    usefulness = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "usefulness_proxy" / "scientific_usefulness_proxy.csv").fillna("")
    usefulness = usefulness.rename(columns={"document_id": "file_id"})
    neighbors = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "nearest_neighbors" / "nearest_neighbors.csv").fillna("")
    neighbors = neighbors.rename(columns={"document_id": "file_id"})
    case_map = pd.read_csv(OUT / "case_packs" / "file_to_case_map.csv").fillna("")
    case_map = case_map.rename(columns={"document_id": "file_id"})
    return {
        "doc": doc,
        "clusters": clusters,
        "graph": graph,
        "anomaly": anomaly,
        "usefulness": usefulness,
        "neighbors": neighbors,
        "case_map": case_map,
    }


def neighbor_wide(neighbors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for file_id, group in neighbors.sort_values("neighbor_rank").groupby("file_id"):
        group = group.head(3)
        row = {"file_id": file_id}
        for _, item in group.iterrows():
            rank = int(item["neighbor_rank"])
            row[f"nearest_neighbor_{rank}"] = item["neighbor_title"]
            row[f"nearest_neighbor_{rank}_id"] = item["neighbor_document_id"]
            row[f"nearest_neighbor_{rank}_distance"] = item["cosine_distance"]
        rows.append(row)
    return pd.DataFrame(rows)


def add_review_joins(base: pd.DataFrame, refs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    result = base.copy()
    result = result.rename(columns={"file_id": "file_id"})
    for col in BASE_SCHEMA:
        if col not in result.columns:
            result[col] = ""

    joins = [
        refs["doc"][["file_id", "title", "agency", "file_group", "output_path"]],
        refs["clusters"][["file_id", "cluster"]],
        refs["graph"][["file_id", "graph_community", "degree", "betweenness"]],
        refs["anomaly"][["file_id", "anomaly_rank", "anomaly_uniqueness"]],
        refs["usefulness"][["file_id", "usefulness_proxy_score"]],
        refs["case_map"][["file_id", "case_pack_id", "case_pack_label", "basis_for_grouping", "confidence"]],
        neighbor_wide(refs["neighbors"]),
    ]
    for join in joins:
        suffix_cols = [c for c in join.columns if c != "file_id" and c in result.columns]
        if suffix_cols:
            join = join.rename(columns={c: f"{c}__join" for c in suffix_cols})
        result = result.merge(join, on="file_id", how="left")
        for original in suffix_cols:
            joined = f"{original}__join"
            result[original] = result[original].where(result[original].astype(str).str.strip() != "", result[joined])
            result = result.drop(columns=[joined])

    result["model_assisted_draft"] = result["short_human_summary"].apply(lambda x: bool(clean_missing(x)))
    result["coding_status"] = result["model_assisted_draft"].map({True: "model_assisted_draft", False: "uncoded"})
    return result


def build_repaired_review(refs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base = pd.read_csv(PROJECT_ROOT / "analysis2b" / "manual_review" / "manual_review_template.csv").fillna("")
    repaired = add_review_joins(base, refs)
    metadata_cols = [
        "output_path",
        "anomaly_rank",
        "anomaly_uniqueness",
        "usefulness_proxy_score",
        "case_pack_id",
        "case_pack_label",
        "basis_for_grouping",
        "confidence",
        "nearest_neighbor_1",
        "nearest_neighbor_1_id",
        "nearest_neighbor_1_distance",
        "nearest_neighbor_2",
        "nearest_neighbor_2_id",
        "nearest_neighbor_2_distance",
        "nearest_neighbor_3",
        "nearest_neighbor_3_id",
        "nearest_neighbor_3_distance",
        "degree",
        "betweenness",
        "model_assisted_draft",
        "coding_status",
    ]
    ordered = [c for c in BASE_SCHEMA + metadata_cols if c in repaired.columns]
    repaired = repaired[ordered]
    repaired.to_csv(REVIEW_OUT / "review_sample_repaired.csv", index=False)
    return repaired


def empty_schema_rows(file_ids: list[str], review_group: str, refs: dict[str, pd.DataFrame], existing: pd.DataFrame) -> pd.DataFrame:
    existing_by_file = existing.drop_duplicates("file_id").set_index("file_id") if "file_id" in existing.columns else pd.DataFrame()
    rows = []
    for file_id in file_ids:
        if not existing_by_file.empty and file_id in existing_by_file.index:
            row = existing_by_file.loc[file_id].to_dict()
            row["file_id"] = file_id
            row["review_group"] = review_group
        else:
            row = {col: "" for col in BASE_SCHEMA}
            row["file_id"] = file_id
            row["review_group"] = review_group
        rows.append(row)
    return add_review_joins(pd.DataFrame(rows), refs)


def build_batches(repaired: pd.DataFrame, refs: dict[str, pd.DataFrame]) -> None:
    top_anomalies = repaired[repaired["review_group"] == "top_anomaly"].copy()
    cluster_centers = repaired[repaired["review_group"] == "cluster_center"].copy()
    random_baseline = repaired[repaired["review_group"] == "random_baseline"].copy()

    bridge = pd.read_csv(PROJECT_ROOT / "analysis2b" / "bridge_cards" / "bridge_file_cards.csv").fillna("")
    bridge_ids = bridge["document_id"].tolist()
    bridge_base = []
    for file_id in bridge_ids:
        row = {col: "" for col in BASE_SCHEMA}
        row["file_id"] = file_id
        row["review_group"] = "bridge_file"
        bridge_base.append(row)
    bridge_batch = add_review_joins(pd.DataFrame(bridge_base), refs)
    existing_by_file = repaired.drop_duplicates("file_id").set_index("file_id")
    human_cols = [
        "human_document_genre",
        "case_or_compilation",
        "single_event_or_multi_event",
        "event_date_precision",
        "event_location_precision",
        "primary_location",
        "witness_type",
        "sensor_type",
        "raw_media_present",
        "object_shape",
        "object_color",
        "motion_description",
        "duration_available",
        "altitude_speed_available",
        "official_explanation_present",
        "resolution_status",
        "external_verification_possible",
        "scientific_usefulness_score_0_10",
        "reason_for_scientific_usefulness",
        "why_algorithm_selected_this_file",
        "content_unique_or_format_unique",
        "reviewer_confidence_0_3",
        "short_human_summary",
    ]
    for idx, row in bridge_batch.iterrows():
        file_id = row["file_id"]
        if file_id in existing_by_file.index:
            existing = existing_by_file.loc[file_id]
            for col in human_cols:
                if clean_missing(existing.get(col, "")):
                    bridge_batch.at[idx, col] = existing[col]
            bridge_batch.at[idx, "model_assisted_draft"] = bool(clean_missing(existing.get("short_human_summary", "")))
            bridge_batch.at[idx, "coding_status"] = "model_assisted_draft" if bridge_batch.at[idx, "model_assisted_draft"] else "uncoded"
    bridge_batch = bridge_batch.merge(
        bridge[
            [
                "document_id",
                "nearest_communities",
                "neighbor_community_count",
                "cross_community_neighbor_count",
                "top_neighbor_titles",
            ]
        ].rename(columns={"document_id": "file_id"}),
        on="file_id",
        how="left",
    )

    top_anomalies.to_csv(MANUAL_OUT / "batch_01_top_anomalies.csv", index=False)
    bridge_batch.to_csv(MANUAL_OUT / "batch_02_bridge_files.csv", index=False)
    cluster_centers.to_csv(MANUAL_OUT / "batch_03_cluster_centers.csv", index=False)
    random_baseline.to_csv(MANUAL_OUT / "batch_04_random_baseline.csv", index=False)


def write_cluster_template() -> None:
    comp = pd.read_csv(PROJECT_ROOT / "analysis2b" / "cluster_cards" / "cluster_composition_summary.csv").fillna("")
    reps = pd.read_csv(PROJECT_ROOT / "analysis2b" / "cluster_cards" / "cluster_cards.csv").fillna("")
    anomaly = pd.read_csv(PROJECT_ROOT / "analysis2b" / "anomaly_cards" / "anomaly_contrast_cards.csv").fillna("")
    bridge = pd.read_csv(PROJECT_ROOT / "analysis2b" / "bridge_cards" / "bridge_file_cards.csv").fillna("")
    labels = {
        0: "Department of War modern operational mission reports",
        1: "FBI late-2025 photo / visual evidence packet",
        2: "State Department diplomatic cable / geopolitical sighting family",
        3: "FBI historical HQ archive sections",
        4: "NASA lunar / space visual material",
    }
    lines = ["# Cluster Cards Interpretation Template", ""]
    for _, row in comp.sort_values("cluster").iterrows():
        cluster = int(row["cluster"])
        lines.extend(
            [
                f"## Cluster {cluster}: {labels.get(cluster, 'Unlabeled')}",
                "",
                f"- Size: {row['size']}",
                f"- Dominant agency: {row['dominant_agency']} ({float(row['agency_purity']):.2f})",
                f"- Dominant modality: {row['dominant_modality']} ({float(row['modality_purity']):.2f})",
                "",
                "### Top Representatives",
                "",
            ]
        )
        for _, rep in reps[reps["cluster"] == cluster].sort_values("rank_within_cluster").head(10).iterrows():
            lines.append(f"- R{int(rep['rank_within_cluster'])}: {rep['title']} [{rep['agency']}, {rep['file_group']}]")
        lines.extend(["", "### Top Anomalies Inside Cluster", ""])
        for _, item in anomaly.merge(
            pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "cluster_interpretation" / "baseline_kmeans_clusters.csv")[["document_id", "cluster"]],
            on="document_id",
            how="left",
        ).query("cluster == @cluster").head(5).iterrows():
            lines.append(f"- Rank {int(item['rank'])}: {item['title']}")
        lines.extend(["", "### Bridge Files Inside Cluster", ""])
        for _, item in bridge[bridge["graph_community"].astype(str) == str(cluster)].head(5).iterrows():
            lines.append(f"- {item['title']} | neighbor communities: {item.get('nearest_communities', '')}")
        lines.extend(
            [
                "",
                "### Human Interpretation Fields",
                "",
                "- Final human label:",
                "- Evidence family:",
                "- Format-driven or content-driven:",
                "- Scientific usefulness:",
                "- Case packs inside cluster:",
                "- Notes from source-file review:",
                "",
            ]
        )
    (TEMPLATE_OUT / "cluster_cards_interpretation_template.md").write_text("\n".join(lines), encoding="utf-8")


def write_anomaly_template() -> None:
    anomaly = pd.read_csv(PROJECT_ROOT / "analysis2b" / "anomaly_cards" / "anomaly_contrast_cards.csv").fillna("")
    lines = ["# Anomaly Cards Interpretation Template", ""]
    for _, row in anomaly.sort_values("rank").iterrows():
        lines.extend(
            [
                f"## Rank {int(row['rank'])}: {row['title']}",
                "",
                f"- File ID: {row['document_id']}",
                f"- Agency: {row['agency']}",
                f"- Modality: {row['file_group']}",
                f"- Ensemble uniqueness: {row['ensemble_uniqueness']}",
                f"- Path: `{row['output_path']}`",
                f"- Nearest 1: {row['nearest_neighbor_1']}",
                f"- Nearest 2: {row['nearest_neighbor_2']}",
                f"- Nearest 3: {row['nearest_neighbor_3']}",
                f"- Distances: {row['distances']}",
                "",
                "### Human Interpretation Fields",
                "",
                "- Likely algorithmic reason:",
                "- Content anomaly or format anomaly:",
                "- Case or compilation:",
                "- Date/location/sensor available:",
                "- External verification possible:",
                "- Follow-up priority:",
                "- Human summary:",
                "",
            ]
        )
    (TEMPLATE_OUT / "anomaly_cards_interpretation_template.md").write_text("\n".join(lines), encoding="utf-8")


def write_bridge_template() -> None:
    bridge = pd.read_csv(PROJECT_ROOT / "analysis2b" / "bridge_cards" / "bridge_file_cards.csv").fillna("")
    lines = ["# Bridge File Cards Interpretation Template", ""]
    for _, row in bridge.sort_values("betweenness", ascending=False).iterrows():
        lines.extend(
            [
                f"## {row['title']}",
                "",
                f"- File ID: {row['document_id']}",
                f"- Agency: {row['agency']}",
                f"- Modality: {row['file_group']}",
                f"- Graph community: {row['graph_community']}",
                f"- Betweenness: {row['betweenness']}",
                f"- Degree: {row['degree']}",
                f"- Neighbor communities: {row['nearest_communities']}",
                f"- Cross-community neighbor count: {row['cross_community_neighbor_count']}",
                f"- Top neighbor titles: {row['top_neighbor_titles']}",
                f"- Path: `{row['output_path']}`",
                "",
                "### Human Interpretation Fields",
                "",
                "- Which communities does it connect:",
                "- Why it bridges:",
                "- Agency bridge or content bridge:",
                "- Summary/mixed record:",
                "- Scientific value:",
                "- Follow-up priority:",
                "",
            ]
        )
    (TEMPLATE_OUT / "bridge_cards_interpretation_template.md").write_text("\n".join(lines), encoding="utf-8")


def write_readme(repaired: pd.DataFrame) -> None:
    coded = int(repaired["model_assisted_draft"].sum())
    text = f"""# Analysis 3.0 Grounding Outputs

This folder contains the grounded interpretation scaffolding for moving from file-level archive mapping to case-level evidence review.

No external data was fetched.
No new embeddings were generated.
The active Analysis 2b manual-review files were not overwritten.

## Outputs

```text
review_packet/review_sample_repaired.csv
manual_review/batch_01_top_anomalies.csv
manual_review/batch_02_bridge_files.csv
manual_review/batch_03_cluster_centers.csv
manual_review/batch_04_random_baseline.csv
interpretation_templates/cluster_cards_interpretation_template.md
interpretation_templates/anomaly_cards_interpretation_template.md
interpretation_templates/bridge_cards_interpretation_template.md
```

## Current Coding Status

```text
Rows in repaired review packet: {len(repaired)}
Model-assisted draft coded rows: {coded}
Uncoded rows: {len(repaired) - coded}
```

The coded rows should be treated as model-assisted drafts until human verified.
"""
    (OUT / "GROUNDING_README.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    refs = load_reference_tables()
    repaired = build_repaired_review(refs)
    build_batches(repaired, refs)
    write_cluster_template()
    write_anomaly_template()
    write_bridge_template()
    write_readme(repaired)
    print(f"Wrote Analysis 3.0 grounding outputs to {OUT}")
    print(f"Rows: {len(repaired)}")
    print(f"Model-assisted draft rows: {int(repaired['model_assisted_draft'].sum())}")


if __name__ == "__main__":
    main()
