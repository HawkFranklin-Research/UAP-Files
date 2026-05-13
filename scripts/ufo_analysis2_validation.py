"""Second-stage validation analyses for the UAP embedding evidence map.

This script uses only existing local data:
  - analysis/embeddings/document_embeddings.npz
  - analysis/embeddings/document_index.csv
  - analysis/anomaly/ufo_anomaly_scores.csv, if present
  - analysis/inventory_documents.csv, if present

It does not call external APIs and does not fetch new data.
"""

from __future__ import annotations

import json
import math
import random
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import AgglomerativeClustering, KMeans, SpectralClustering
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    normalized_mutual_info_score,
    pairwise_distances,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
from sklearn.preprocessing import OneHotEncoder

from ufo_common import ANALYSIS_DIR, PROJECT_ROOT, GROUP_COLORS, PALETTE, ensure_dirs, l2_normalize, save_json


OUT = PROJECT_ROOT / "analysis-2.0"
FIG = OUT / "figures"


def setup_style() -> None:
    sns.set_theme(
        style="whitegrid",
        context="talk",
        rc={
            "axes.facecolor": "#F7F3EA",
            "figure.facecolor": "#F7F3EA",
            "grid.color": "#D8D0BF",
            "axes.edgecolor": PALETTE["ink"],
            "text.color": PALETTE["ink"],
        },
    )


def mkdirs() -> None:
    ensure_dirs()
    for path in [
        OUT,
        FIG,
        OUT / "cluster_stability",
        OUT / "residual_analysis",
        OUT / "cluster_interpretation",
        OUT / "nearest_neighbors",
        OUT / "graph_analysis",
        OUT / "anomaly_validation",
        OUT / "review_packet",
        OUT / "usefulness_proxy",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_index(index: pd.DataFrame) -> pd.DataFrame:
    index = index.copy()
    rename = {
        "agency": "Agency",
        "file_group": "File Group",
        "title": "Title",
        "output_path": "Output Path",
        "source_filename": "Source Filename",
    }
    index = index.rename(columns={old: new for old, new in rename.items() if old in index.columns})
    return index


def load_data() -> tuple[pd.DataFrame, np.ndarray]:
    emb = np.load(ANALYSIS_DIR / "embeddings" / "document_embeddings.npz", allow_pickle=False)
    ids = [str(x) for x in emb["ids"]]
    matrix = l2_normalize(emb["embeddings"].astype(np.float32))
    index = normalize_index(pd.read_csv(ANALYSIS_DIR / "embeddings" / "document_index.csv").fillna(""))
    index = index.set_index("document_id").loc[ids].reset_index()
    pca = PCA(n_components=2, random_state=42).fit_transform(matrix)
    index["pca_1"] = pca[:, 0]
    index["pca_2"] = pca[:, 1]
    return index, matrix


def purity(labels: np.ndarray, groups: pd.Series) -> float:
    total = 0
    for label in np.unique(labels):
        values = groups.to_numpy()[labels == label]
        if len(values):
            total += pd.Series(values).value_counts().max()
    return float(total / len(labels))


def metrics_for(labels: np.ndarray, matrix: np.ndarray, index: pd.DataFrame, method: str, seed: int | None) -> dict:
    n_clusters = len(set(labels))
    row = {
        "method": method,
        "seed": "" if seed is None else seed,
        "n_clusters": n_clusters,
        "agency_purity": purity(labels, index["Agency"]),
        "modality_purity": purity(labels, index["File Group"]),
        "cluster_size_min": int(pd.Series(labels).value_counts().min()),
        "cluster_size_max": int(pd.Series(labels).value_counts().max()),
    }
    if n_clusters > 1 and n_clusters < len(labels):
        row.update(
            {
                "silhouette": float(silhouette_score(matrix, labels, metric="cosine")),
                "davies_bouldin": float(davies_bouldin_score(matrix, labels)),
                "calinski_harabasz": float(calinski_harabasz_score(matrix, labels)),
            }
        )
    else:
        row.update({"silhouette": np.nan, "davies_bouldin": np.nan, "calinski_harabasz": np.nan})
    return row


def cluster_runs(matrix: np.ndarray, k: int = 5, seeds: list[int] | None = None) -> list[dict]:
    seeds = seeds or list(range(30))
    runs = []
    for seed in seeds:
        runs.append(
            {
                "run_id": f"kmeans_s{seed}",
                "method": "KMeans",
                "seed": seed,
                "labels": KMeans(n_clusters=k, random_state=seed, n_init="auto").fit_predict(matrix),
            }
        )
        runs.append(
            {
                "run_id": f"gmm_s{seed}",
                "method": "GaussianMixture",
                "seed": seed,
                "labels": GaussianMixture(n_components=k, covariance_type="diag", random_state=seed).fit_predict(matrix),
            }
        )
        if seed < 15:
            runs.append(
                {
                    "run_id": f"spectral_s{seed}",
                    "method": "Spectral",
                    "seed": seed,
                    "labels": SpectralClustering(
                        n_clusters=k,
                        affinity="nearest_neighbors",
                        n_neighbors=12,
                        random_state=seed,
                    ).fit_predict(matrix),
                }
            )
    runs.append(
        {
            "run_id": "agglomerative_average",
            "method": "Agglomerative",
            "seed": None,
            "labels": AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average").fit_predict(matrix),
        }
    )
    return runs


def consensus_matrix(runs: list[dict], n: int) -> np.ndarray:
    consensus = np.zeros((n, n), dtype=np.float32)
    for run in runs:
        labels = run["labels"]
        consensus += labels[:, None] == labels[None, :]
    return consensus / len(runs)


def run_cluster_stability(index: pd.DataFrame, matrix: np.ndarray) -> None:
    out = OUT / "cluster_stability"
    runs = cluster_runs(matrix, k=5)
    rows = [metrics_for(run["labels"], matrix, index, run["method"], run["seed"]) | {"run_id": run["run_id"]} for run in runs]
    metrics = pd.DataFrame(rows)
    metrics.to_csv(out / "cluster_metrics.csv", index=False)

    pair_rows = []
    for a, b in combinations(runs, 2):
        pair_rows.append(
            {
                "run_a": a["run_id"],
                "run_b": b["run_id"],
                "method_a": a["method"],
                "method_b": b["method"],
                "ari": adjusted_rand_score(a["labels"], b["labels"]),
                "nmi": normalized_mutual_info_score(a["labels"], b["labels"]),
            }
        )
    pairs = pd.DataFrame(pair_rows)
    pairs.to_csv(out / "cluster_stability_pairs.csv", index=False)

    consensus = consensus_matrix(runs, len(index))
    np.save(out / "consensus_matrix.npy", consensus)
    consensus_labels = AgglomerativeClustering(n_clusters=5, metric="precomputed", linkage="average").fit_predict(1 - consensus)
    consensus_df = index[["document_id", "Title", "Agency", "File Group", "Output Path"]].copy()
    consensus_df["consensus_cluster"] = consensus_labels
    consensus_df.to_csv(out / "consensus_clusters.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(22, 6))
    sns.boxplot(data=metrics, x="method", y="silhouette", color=PALETTE["ion"], ax=axes[0])
    sns.boxplot(data=metrics, x="method", y="agency_purity", color=PALETTE["signal"], ax=axes[1])
    sns.boxplot(data=metrics, x="method", y="modality_purity", color=PALETTE["radar"], ax=axes[2])
    for ax in axes:
        ax.tick_params(axis="x", rotation=25)
        ax.title.set_fontweight("bold")
    axes[0].set_title("Silhouette by Method")
    axes[1].set_title("Agency Purity")
    axes[2].set_title("Modality Purity")
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "cluster_metrics_overview.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    method_ari = pairs.pivot_table(index="method_a", columns="method_b", values="ari", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(method_ari, annot=True, fmt=".2f", cmap="crest", ax=ax)
    ax.set_title("Mean Pairwise ARI Across Cluster Runs", fontweight="bold")
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "cluster_stability_heatmap.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    order = np.argsort(consensus_labels)
    fig, ax = plt.subplots(figsize=(10, 9))
    sns.heatmap(consensus[order][:, order], cmap="mako", cbar_kws={"label": "Same-cluster frequency"}, ax=ax)
    ax.set_title("Consensus Matrix Across Clustering Methods", fontweight="bold")
    ax.set_xlabel("Files sorted by consensus cluster")
    ax.set_ylabel("Files sorted by consensus cluster")
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "consensus_matrix.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def residualize(matrix: np.ndarray, index: pd.DataFrame, controls: list[str]) -> np.ndarray:
    if not controls:
        return matrix.copy()
    enc = OneHotEncoder(drop=None, sparse_output=False)
    design = enc.fit_transform(index[controls])
    design = np.column_stack([np.ones(len(index)), design])
    beta, *_ = np.linalg.lstsq(design, matrix, rcond=None)
    fitted = design @ beta
    return l2_normalize((matrix - fitted).astype(np.float32))


def run_residual_analysis(index: pd.DataFrame, matrix: np.ndarray) -> None:
    out = OUT / "residual_analysis"
    variants = {
        "raw": [],
        "agency_controlled": ["Agency"],
        "modality_controlled": ["File Group"],
        "agency_modality_controlled": ["Agency", "File Group"],
    }
    rows = []
    cluster_frames = []
    projection_frames = []
    for name, controls in variants.items():
        mat = residualize(matrix, index, controls)
        labels = KMeans(n_clusters=5, random_state=42, n_init="auto").fit_predict(mat)
        rows.append(metrics_for(labels, mat, index, "KMeans", 42) | {"variant": name, "controls": ",".join(controls)})
        part = index[["document_id", "Title", "Agency", "File Group", "Output Path"]].copy()
        part["variant"] = name
        part["cluster"] = labels
        cluster_frames.append(part)
        pca = PCA(n_components=2, random_state=42).fit_transform(mat)
        projection = part.copy()
        projection["pca_1"] = pca[:, 0]
        projection["pca_2"] = pca[:, 1]
        projection_frames.append(projection)

    comparison = pd.DataFrame(rows)
    comparison.to_csv(out / "residual_cluster_comparison.csv", index=False)
    clusters = pd.concat(cluster_frames, ignore_index=True)
    clusters.to_csv(out / "residual_clusters.csv", index=False)
    projections = pd.concat(projection_frames, ignore_index=True)
    projections.to_csv(out / "residual_projections.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    melt = comparison.melt(
        id_vars="variant",
        value_vars=["agency_purity", "modality_purity", "silhouette"],
        var_name="metric",
        value_name="value",
    )
    sns.barplot(data=melt, x="variant", y="value", hue="metric", palette="crest", ax=axes[0])
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].set_title("Purity and Separability After Residualization", fontweight="bold")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Score")
    subset = projections[projections["variant"].isin(["raw", "agency_modality_controlled"])]
    sns.scatterplot(
        data=subset,
        x="pca_1",
        y="pca_2",
        hue="File Group",
        style="variant",
        palette=GROUP_COLORS,
        s=80,
        alpha=0.85,
        ax=axes[1],
    )
    axes[1].set_title("Raw vs Agency+Modality Residual PCA", fontweight="bold")
    axes[1].legend(frameon=False, fontsize=9)
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "residual_validation_overview.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def run_cluster_interpretation(index: pd.DataFrame, matrix: np.ndarray) -> np.ndarray:
    out = OUT / "cluster_interpretation"
    labels = KMeans(n_clusters=5, random_state=42, n_init="auto").fit_predict(matrix)
    df = index[["document_id", "Title", "Agency", "File Group", "Output Path", "pca_1", "pca_2"]].copy()
    df["cluster"] = labels
    df.to_csv(out / "baseline_kmeans_clusters.csv", index=False)

    purity_rows = []
    for cluster, group in df.groupby("cluster"):
        purity_rows.append(
            {
                "cluster": cluster,
                "size": len(group),
                "dominant_agency": group["Agency"].value_counts().idxmax(),
                "agency_purity": group["Agency"].value_counts(normalize=True).max(),
                "dominant_modality": group["File Group"].value_counts().idxmax(),
                "modality_purity": group["File Group"].value_counts(normalize=True).max(),
            }
        )
    pd.DataFrame(purity_rows).to_csv(out / "cluster_purity.csv", index=False)

    reps = []
    for cluster in sorted(df["cluster"].unique()):
        idx = np.where(labels == cluster)[0]
        centroid = matrix[idx].mean(axis=0)
        dist = pairwise_distances(matrix[idx], centroid.reshape(1, -1), metric="cosine").ravel()
        order = np.argsort(dist)
        for rank, local_i in enumerate(order[:5], start=1):
            row = df.iloc[idx[local_i]].to_dict()
            row["representative_rank"] = rank
            row["centroid_cosine_distance"] = float(dist[local_i])
            reps.append(row)
    pd.DataFrame(reps).to_csv(out / "cluster_representatives.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    agency = pd.crosstab(df["cluster"], df["Agency"], normalize="index")
    agency.plot(kind="bar", stacked=True, colormap="crest", ax=axes[0])
    axes[0].set_title("Agency Composition by Cluster", fontweight="bold")
    axes[0].set_ylabel("Share")
    axes[0].legend(frameon=False, fontsize=8)
    modality = pd.crosstab(df["cluster"], df["File Group"], normalize="index")
    modality.plot(kind="bar", stacked=True, color=[GROUP_COLORS.get(c, PALETTE["lunar"]) for c in modality.columns], ax=axes[1])
    axes[1].set_title("Modality Composition by Cluster", fontweight="bold")
    axes[1].set_ylabel("Share")
    axes[1].legend(frameon=False, fontsize=8)
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "cluster_purity_overview.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return labels


def run_nearest_neighbors(index: pd.DataFrame, matrix: np.ndarray) -> None:
    out = OUT / "nearest_neighbors"
    k = 8
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine").fit(matrix)
    dist, ind = nn.kneighbors(matrix)
    rows = []
    for i, doc_id in enumerate(index["document_id"]):
        for rank in range(1, k + 1):
            j = ind[i, rank]
            rows.append(
                {
                    "document_id": doc_id,
                    "title": index.iloc[i]["Title"],
                    "agency": index.iloc[i]["Agency"],
                    "file_group": index.iloc[i]["File Group"],
                    "neighbor_rank": rank,
                    "neighbor_document_id": index.iloc[j]["document_id"],
                    "neighbor_title": index.iloc[j]["Title"],
                    "neighbor_agency": index.iloc[j]["Agency"],
                    "neighbor_file_group": index.iloc[j]["File Group"],
                    "cosine_distance": float(dist[i, rank]),
                    "cosine_similarity": float(1 - dist[i, rank]),
                }
            )
    neighbors = pd.DataFrame(rows)
    neighbors.to_csv(out / "nearest_neighbors.csv", index=False)

    anomaly_path = ANALYSIS_DIR / "anomaly" / "top_unique.csv"
    if anomaly_path.exists():
        top_ids = normalize_index(pd.read_csv(anomaly_path)).head(25)["document_id"].tolist()
        neighbors[neighbors["document_id"].isin(top_ids)].to_csv(out / "top_anomaly_neighbors.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(neighbors[neighbors["neighbor_rank"] == 1]["cosine_distance"], bins=28, color=PALETTE["ion"], ax=ax)
    ax.set_title("Nearest-Neighbor Distance Distribution", fontweight="bold")
    ax.set_xlabel("Cosine distance to nearest file")
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "nearest_neighbor_distance_distribution.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def run_graph_analysis(index: pd.DataFrame, matrix: np.ndarray) -> None:
    out = OUT / "graph_analysis"
    k = 8
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine").fit(matrix)
    dist, ind = nn.kneighbors(matrix)
    graph = nx.Graph()
    for i, row in index.iterrows():
        graph.add_node(row["document_id"], title=row["Title"], agency=row["Agency"], file_group=row["File Group"])
    edge_rows = []
    for i, source in enumerate(index["document_id"]):
        for rank in range(1, k + 1):
            j = ind[i, rank]
            target = index.iloc[j]["document_id"]
            weight = float(1 - dist[i, rank])
            graph.add_edge(source, target, weight=weight, distance=float(dist[i, rank]))
            edge_rows.append(
                {
                    "source": source,
                    "target": target,
                    "rank": rank,
                    "cosine_distance": float(dist[i, rank]),
                    "cosine_similarity": weight,
                }
            )
    pd.DataFrame(edge_rows).to_csv(out / "file_knn_edges.csv", index=False)

    communities = list(nx.algorithms.community.greedy_modularity_communities(graph, weight="weight"))
    community_map = {node: cid for cid, nodes in enumerate(communities) for node in nodes}
    degree = dict(graph.degree())
    weighted_degree = dict(graph.degree(weight="weight"))
    betweenness = nx.betweenness_centrality(graph, weight="distance")
    node_rows = []
    for _, row in index.iterrows():
        doc_id = row["document_id"]
        node_rows.append(
            {
                "document_id": doc_id,
                "title": row["Title"],
                "agency": row["Agency"],
                "file_group": row["File Group"],
                "graph_community": community_map[doc_id],
                "degree": degree[doc_id],
                "weighted_degree": weighted_degree[doc_id],
                "betweenness": betweenness[doc_id],
                "pca_1": row["pca_1"],
                "pca_2": row["pca_2"],
            }
        )
    nodes = pd.DataFrame(node_rows)
    nodes.to_csv(out / "file_graph_nodes.csv", index=False)
    nodes.sort_values("betweenness", ascending=False).head(25).to_csv(out / "bridge_files.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 9))
    for _, edge in pd.DataFrame(edge_rows).iterrows():
        a = index[index["document_id"] == edge["source"]].iloc[0]
        b = index[index["document_id"] == edge["target"]].iloc[0]
        if edge["rank"] <= 3:
            ax.plot([a["pca_1"], b["pca_1"]], [a["pca_2"], b["pca_2"]], color="#B8C4D9", alpha=0.16, linewidth=0.6)
    sns.scatterplot(
        data=nodes,
        x="pca_1",
        y="pca_2",
        hue="graph_community",
        size="betweenness",
        sizes=(40, 220),
        palette="viridis",
        edgecolor=PALETTE["ink"],
        linewidth=0.3,
        ax=ax,
    )
    ax.set_title("kNN Graph Communities on Embedding PCA", fontweight="bold")
    ax.legend(frameon=False, fontsize=8)
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "embedding_knn_graph.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def percentile(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(pct=True).to_numpy()


def run_anomaly_validation(index: pd.DataFrame, matrix: np.ndarray, labels: np.ndarray) -> None:
    out = OUT / "anomaly_validation"
    centroid = matrix.mean(axis=0)
    global_dist = pairwise_distances(matrix, centroid.reshape(1, -1), metric="cosine").ravel()
    nn = NearestNeighbors(n_neighbors=2, metric="cosine").fit(matrix)
    nn_dist = nn.kneighbors(matrix)[0][:, 1]
    iso = -IsolationForest(n_estimators=500, random_state=42, contamination="auto").fit(matrix).score_samples(matrix)
    lof = -LocalOutlierFactor(n_neighbors=15, metric="cosine").fit_predict(matrix)
    lof_scores = -LocalOutlierFactor(n_neighbors=15, metric="cosine").fit(matrix).negative_outlier_factor_
    cluster_resid = np.zeros(len(index))
    for label in np.unique(labels):
        idx = np.where(labels == label)[0]
        c = matrix[idx].mean(axis=0)
        cluster_resid[idx] = pairwise_distances(matrix[idx], c.reshape(1, -1), metric="cosine").ravel()
    modality_resid = np.zeros(len(index))
    for value in index["File Group"].unique():
        idx = np.where(index["File Group"].to_numpy() == value)[0]
        c = matrix[idx].mean(axis=0)
        modality_resid[idx] = pairwise_distances(matrix[idx], c.reshape(1, -1), metric="cosine").ravel()

    scores = index[["document_id", "Title", "Agency", "File Group", "Output Path"]].copy()
    scores["global_centroid_cosine"] = global_dist
    scores["nearest_neighbor_cosine"] = nn_dist
    scores["isolation_forest"] = iso
    scores["local_outlier_factor"] = lof_scores
    scores["cluster_residual_cosine"] = cluster_resid
    scores["modality_residual_cosine"] = modality_resid
    method_cols = [
        "global_centroid_cosine",
        "nearest_neighbor_cosine",
        "isolation_forest",
        "local_outlier_factor",
        "cluster_residual_cosine",
        "modality_residual_cosine",
    ]
    for col in method_cols:
        scores[f"{col}_pct"] = percentile(scores[col].to_numpy())
    scores["ensemble_uniqueness"] = scores[[f"{col}_pct" for col in method_cols]].mean(axis=1)
    scores["ensemble_rank"] = scores["ensemble_uniqueness"].rank(ascending=False, method="first").astype(int)
    scores = scores.sort_values("ensemble_rank")
    scores.to_csv(out / "anomaly_method_comparison.csv", index=False)
    scores.head(25).to_csv(out / "top25_ensemble_anomalies.csv", index=False)

    rank_cols = [f"{col}_pct" for col in method_cols] + ["ensemble_uniqueness"]
    corr = scores[rank_cols].corr(method="spearman")
    corr.to_csv(out / "anomaly_rank_correlation.csv")
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", center=0, ax=ax)
    ax.set_title("Anomaly Method Rank Correlation", fontweight="bold")
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "anomaly_rank_correlation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    top = scores.head(15).copy()
    top["short_title"] = top["Title"].str.slice(0, 50)
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.barplot(data=top, x="ensemble_uniqueness", y="short_title", hue="File Group", palette=GROUP_COLORS, dodge=False, ax=ax)
    ax.set_title("Top Ensemble Anomalies", fontweight="bold")
    ax.set_xlabel("Ensemble uniqueness")
    ax.set_ylabel("")
    ax.legend(frameon=False)
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "top_anomaly_method_agreement.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def run_review_packet(index: pd.DataFrame, matrix: np.ndarray, labels: np.ndarray) -> None:
    out = OUT / "review_packet"
    anomaly_path = OUT / "anomaly_validation" / "anomaly_method_comparison.csv"
    anomaly = pd.read_csv(anomaly_path)
    top = anomaly.head(25).copy()
    top["review_group"] = "top_anomaly"

    centers = []
    for label in np.unique(labels):
        idx = np.where(labels == label)[0]
        c = matrix[idx].mean(axis=0)
        dist = pairwise_distances(matrix[idx], c.reshape(1, -1), metric="cosine").ravel()
        for local_i in np.argsort(dist)[:5]:
            centers.append(index.iloc[idx[local_i]].to_dict() | {"review_group": "cluster_center"})
    centers = pd.DataFrame(centers).head(25)

    random.seed(42)
    exclude = set(top["document_id"]) | set(centers["document_id"])
    candidates = [doc_id for doc_id in index["document_id"] if doc_id not in exclude]
    random_ids = set(random.sample(candidates, min(25, len(candidates))))
    random_df = index[index["document_id"].isin(random_ids)].copy()
    random_df["review_group"] = "random_baseline"

    cols = ["document_id", "Title", "Agency", "File Group", "Output Path", "review_group"]
    packet = pd.concat(
        [
            top.rename(columns={"title": "Title"})[cols],
            centers.rename(columns={"title": "Title"})[cols],
            random_df[cols],
        ],
        ignore_index=True,
    )
    packet.to_csv(out / "review_sample.csv", index=False)
    top.to_csv(out / "top_anomalies.csv", index=False)
    centers.to_csv(out / "cluster_centers.csv", index=False)
    random_df.to_csv(out / "random_baseline.csv", index=False)

    plot_df = index.merge(packet[["document_id", "review_group"]], on="document_id", how="left")
    plot_df["review_group"] = plot_df["review_group"].fillna("not_selected")
    fig, ax = plt.subplots(figsize=(12, 9))
    sns.scatterplot(data=plot_df, x="pca_1", y="pca_2", color="#C9C4B5", s=35, alpha=0.45, ax=ax)
    sns.scatterplot(
        data=plot_df[plot_df["review_group"] != "not_selected"],
        x="pca_1",
        y="pca_2",
        hue="review_group",
        palette={"top_anomaly": PALETTE["flare"], "cluster_center": PALETTE["radar"], "random_baseline": PALETTE["ion"]},
        s=110,
        edgecolor=PALETTE["ink"],
        linewidth=0.4,
        ax=ax,
    )
    ax.set_title("Manual Review Packet: Anomalies, Centers, Random Baseline", fontweight="bold")
    ax.legend(frameon=False)
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "review_groups_embedding_map.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def run_usefulness_proxy(index: pd.DataFrame) -> None:
    out = OUT / "usefulness_proxy"
    inv_path = ANALYSIS_DIR / "inventory_documents.csv"
    inv = pd.read_csv(inv_path).fillna("") if inv_path.exists() else pd.DataFrame()
    df = index.copy()
    if not inv.empty and "Output Path" in inv.columns:
        keep = ["Output Path", "pdf_pages", "video_duration_sec", "image_width", "image_height", "metadata_missing_fields"]
        df = df.merge(inv[[c for c in keep if c in inv.columns]], on="Output Path", how="left")
    for col in ["pdf_pages", "video_duration_sec", "image_width", "image_height", "metadata_missing_fields"]:
        if col not in df.columns:
            df[col] = ""

    def score_row(row: pd.Series) -> dict:
        metadata_text = str(row.get("metadata_text", ""))
        has_incident_date = "Incident date: missing" not in metadata_text
        has_location = "Incident location: missing" not in metadata_text
        is_raw_media = row["File Group"] in {"IMG", "VID"}
        has_pages = str(row.get("pdf_pages", "")).strip() not in {"", "0", "nan"}
        has_video_duration = str(row.get("video_duration_sec", "")).strip() not in {"", "0", "nan"}
        has_visual_dimensions = str(row.get("image_width", "")).strip() not in {"", "0", "nan"}
        components = {
            "agency_known": bool(row["Agency"]),
            "file_type_known": bool(row["File Group"]),
            "incident_date_known": has_incident_date,
            "incident_location_known": has_location,
            "raw_media_available": is_raw_media,
            "pdf_page_count_known": has_pages if row["File Group"] == "PDF" else False,
            "video_duration_known": has_video_duration if row["File Group"] == "VID" else False,
            "image_dimensions_known": has_visual_dimensions if row["File Group"] == "IMG" else False,
            "chunked_or_processed": int(row.get("chunk_count", 0) or 0) > 0,
            "source_path_known": bool(row.get("Output Path", "")),
        }
        return {"usefulness_proxy_score": sum(components.values()), **components}

    scored = pd.concat([df, pd.DataFrame([score_row(row) for _, row in df.iterrows()])], axis=1)
    anomaly_path = OUT / "anomaly_validation" / "anomaly_method_comparison.csv"
    if anomaly_path.exists():
        anomaly = pd.read_csv(anomaly_path)[["document_id", "ensemble_uniqueness", "ensemble_rank"]]
        scored = scored.merge(anomaly, on="document_id", how="left")
    scored.to_csv(out / "scientific_usefulness_proxy.csv", index=False)
    scored.groupby(["Agency", "File Group"])["usefulness_proxy_score"].agg(["count", "mean", "median"]).reset_index().to_csv(
        out / "usefulness_by_agency_modality.csv", index=False
    )

    fig, axes = plt.subplots(1, 2, figsize=(17, 6))
    sns.boxplot(data=scored, x="File Group", y="usefulness_proxy_score", hue="File Group", palette=GROUP_COLORS, legend=False, ax=axes[0])
    axes[0].set_title("Usefulness Proxy by Modality", fontweight="bold")
    if "ensemble_uniqueness" in scored.columns:
        sns.scatterplot(
            data=scored,
            x="usefulness_proxy_score",
            y="ensemble_uniqueness",
            hue="File Group",
            palette=GROUP_COLORS,
            s=90,
            edgecolor=PALETTE["ink"],
            linewidth=0.4,
            ax=axes[1],
        )
        axes[1].set_title("Usefulness Proxy vs Embedding Uniqueness", fontweight="bold")
        axes[1].legend(frameon=False)
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "usefulness_proxy_overview.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_report() -> None:
    summary = {
        "cluster_metrics": str(OUT / "cluster_stability" / "cluster_metrics.csv"),
        "residual_comparison": str(OUT / "residual_analysis" / "residual_cluster_comparison.csv"),
        "nearest_neighbors": str(OUT / "nearest_neighbors" / "nearest_neighbors.csv"),
        "graph_nodes": str(OUT / "graph_analysis" / "file_graph_nodes.csv"),
        "anomaly_validation": str(OUT / "anomaly_validation" / "anomaly_method_comparison.csv"),
        "review_packet": str(OUT / "review_packet" / "review_sample.csv"),
        "usefulness_proxy": str(OUT / "usefulness_proxy" / "scientific_usefulness_proxy.csv"),
    }
    save_json(OUT / "analysis2_manifest.json", summary)
    text = """# Analysis 2.0: Embedding Validation Layer

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
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    setup_style()
    mkdirs()
    index, matrix = load_data()
    run_cluster_stability(index, matrix)
    run_residual_analysis(index, matrix)
    labels = run_cluster_interpretation(index, matrix)
    run_nearest_neighbors(index, matrix)
    run_graph_analysis(index, matrix)
    run_anomaly_validation(index, matrix, labels)
    run_review_packet(index, matrix, labels)
    run_usefulness_proxy(index)
    write_report()
    print(f"Analysis 2.0 complete: {OUT}")


if __name__ == "__main__":
    main()
