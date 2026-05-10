"""Repair non-review Analysis 2b card tables.

This script intentionally does not read or write analysis2b/manual_review/.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances

from ufo_common import ANALYSIS_DIR, PROJECT_ROOT, l2_normalize


ANALYSIS2 = PROJECT_ROOT / "analysis2b"
ANALYSIS20 = PROJECT_ROOT / "analysis-2.0"


def normalize_index(index: pd.DataFrame) -> pd.DataFrame:
    return index.rename(
        columns={
            "title": "Title",
            "agency": "Agency",
            "file_group": "File Group",
            "output_path": "Output Path",
            "source_filename": "Source Filename",
        }
    )


def load_document_embeddings() -> tuple[pd.DataFrame, np.ndarray]:
    emb = np.load(ANALYSIS_DIR / "embeddings" / "document_embeddings.npz", allow_pickle=False)
    ids = [str(x) for x in emb["ids"]]
    matrix = l2_normalize(emb["embeddings"].astype(np.float32))
    index = normalize_index(pd.read_csv(ANALYSIS_DIR / "embeddings" / "document_index.csv").fillna(""))
    index = index.set_index("document_id").loc[ids].reset_index()
    return index, matrix


def repair_cluster_cards() -> None:
    index, matrix = load_document_embeddings()
    clusters = pd.read_csv(ANALYSIS20 / "cluster_interpretation" / "baseline_kmeans_clusters.csv").fillna("")
    meta = pd.read_csv(PROJECT_ROOT / "ufo_release_metadata.csv").fillna("")
    meta = meta.drop_duplicates("Output Path")

    cluster_labels = clusters.set_index("document_id").loc[index["document_id"], "cluster"].to_numpy()
    rows = []
    for cluster in sorted(np.unique(cluster_labels)):
        idx = np.where(cluster_labels == cluster)[0]
        centroid = matrix[idx].mean(axis=0)
        distances = pairwise_distances(matrix[idx], centroid.reshape(1, -1), metric="cosine").ravel()
        order = np.argsort(distances)[:10]
        for rank, local_i in enumerate(order, start=1):
            pos = idx[local_i]
            row = index.iloc[pos]
            meta_row = meta[meta["Output Path"] == row["Output Path"]]
            incident_date = ""
            incident_location = ""
            if not meta_row.empty:
                incident_date = meta_row.iloc[0].get("Incident Date", "")
                incident_location = meta_row.iloc[0].get("Incident Location", "")
            rows.append(
                {
                    "cluster": int(cluster),
                    "rank_within_cluster": rank,
                    "title": row["Title"],
                    "agency": row["Agency"],
                    "file_group": row["File Group"],
                    "incident_date": incident_date,
                    "incident_location": incident_location,
                    "distance_to_cluster_center": float(distances[local_i]),
                    "output_path": row["Output Path"],
                    "document_id": row["document_id"],
                }
            )

    out = ANALYSIS2 / "cluster_cards" / "cluster_cards.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)


def repair_bridge_cards() -> None:
    nodes = pd.read_csv(ANALYSIS20 / "graph_analysis" / "file_graph_nodes.csv").fillna("")
    edges = pd.read_csv(ANALYSIS20 / "graph_analysis" / "file_knn_edges.csv").fillna("")
    bridge = pd.read_csv(ANALYSIS20 / "graph_analysis" / "bridge_files.csv").fillna("")

    node_by_id = nodes.set_index("document_id")
    title_to_id = nodes.set_index("title")["document_id"].to_dict()
    community_by_id = node_by_id["graph_community"].to_dict()
    title_by_id = node_by_id["title"].to_dict()

    rows = []
    for _, row in bridge.sort_values("betweenness", ascending=False).head(15).iterrows():
        doc_id = row.get("document_id") or title_to_id.get(row["title"], "")
        incident_edges = edges[(edges["source"] == doc_id) | (edges["target"] == doc_id)].copy()
        neighbor_ids = []
        for _, edge in incident_edges.iterrows():
            other = edge["target"] if edge["source"] == doc_id else edge["source"]
            if other != doc_id:
                neighbor_ids.append(other)
        counts = Counter(community_by_id.get(neighbor) for neighbor in neighbor_ids)
        counts.pop("", None)
        counts.pop(None, None)
        nearest_communities = "; ".join(f"{int(comm)}:{count}" for comm, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])))
        top_neighbor_titles = []
        seen = set()
        for neighbor in neighbor_ids:
            if neighbor not in seen:
                top_neighbor_titles.append(title_by_id.get(neighbor, neighbor))
                seen.add(neighbor)
            if len(top_neighbor_titles) == 5:
                break
        rows.append(
            {
                "title": row["title"],
                "agency": row["agency"],
                "file_group": row["file_group"],
                "graph_community": row["graph_community"],
                "betweenness": row["betweenness"],
                "degree": row["degree"],
                "nearest_communities": nearest_communities,
                "neighbor_community_count": len(counts),
                "cross_community_neighbor_count": sum(
                    count for comm, count in counts.items() if int(comm) != int(row["graph_community"])
                ),
                "top_neighbor_titles": " | ".join(top_neighbor_titles),
                "output_path": row.get("output_path", ""),
                "document_id": doc_id,
            }
        )

    out = ANALYSIS2 / "bridge_cards" / "bridge_file_cards.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)


def repair_anomaly_cards() -> None:
    anomalies = pd.read_csv(ANALYSIS20 / "anomaly_validation" / "top25_ensemble_anomalies.csv").fillna("")
    neighbors = pd.read_csv(ANALYSIS20 / "nearest_neighbors" / "nearest_neighbors.csv").fillna("")

    rows = []
    for _, row in anomalies.sort_values("ensemble_rank").head(25).iterrows():
        doc_id = row["document_id"]
        nn = neighbors[neighbors["document_id"] == doc_id].sort_values("neighbor_rank").head(3)
        neighbor_titles = nn["neighbor_title"].tolist()
        distances = [round(float(x), 4) for x in nn["cosine_distance"].tolist()]
        while len(neighbor_titles) < 3:
            neighbor_titles.append("")
        rows.append(
            {
                "rank": int(row["ensemble_rank"]),
                "document_id": doc_id,
                "title": row["Title"],
                "agency": row["Agency"],
                "file_group": row["File Group"],
                "ensemble_uniqueness": row["ensemble_uniqueness"],
                "nearest_neighbor_1": neighbor_titles[0],
                "nearest_neighbor_2": neighbor_titles[1],
                "nearest_neighbor_3": neighbor_titles[2],
                "distances": distances,
                "output_path": row.get("Output Path", ""),
            }
        )

    out = ANALYSIS2 / "anomaly_cards" / "anomaly_contrast_cards.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)


def main() -> None:
    repair_cluster_cards()
    repair_bridge_cards()
    repair_anomaly_cards()
    print("Repaired Analysis 2b non-review tables.")


if __name__ == "__main__":
    main()
