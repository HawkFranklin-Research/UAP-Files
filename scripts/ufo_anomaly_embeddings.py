"""Rank the most unique UFO release documents from multimodal embeddings.

Run after embeddings exist:
  python3 scripts/ufo_anomaly_embeddings.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.manifold import TSNE
from sklearn.metrics import pairwise_distances
from sklearn.neighbors import NearestNeighbors

from ufo_common import ANALYSIS_DIR, FIGURES_DIR, GROUP_COLORS, PALETTE, ensure_dirs, l2_normalize, save_json


DEFAULT_EMBEDDING_DIR = ANALYSIS_DIR / "embeddings"
DEFAULT_OUTPUT_DIR = ANALYSIS_DIR / "anomaly"


def normalize_index_columns(index: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "agency": "Agency",
        "file_group": "File Group",
        "title": "title",
        "Title": "title",
        "output_path": "Output Path",
        "source_filename": "Source Filename",
    }
    return index.rename(columns={old: new for old, new in rename.items() if old in index.columns})


def percentile_rank(values: np.ndarray) -> np.ndarray:
    series = pd.Series(values)
    return series.rank(pct=True).to_numpy()


def group_centroid_distance(matrix: np.ndarray, labels: pd.Series) -> np.ndarray:
    distances = np.zeros(len(matrix), dtype=np.float32)
    global_centroid = matrix.mean(axis=0)
    for label in labels.unique():
        idx = np.where(labels.to_numpy() == label)[0]
        centroid = matrix[idx].mean(axis=0) if len(idx) >= 2 else global_centroid
        distances[idx] = np.linalg.norm(matrix[idx] - centroid, axis=1)
    return distances


def compute_projection(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pca_xy = PCA(n_components=2, random_state=42).fit_transform(matrix)
    perplexity = max(5, min(30, (len(matrix) - 1) // 3))
    tsne_xy = TSNE(
        n_components=2,
        perplexity=perplexity,
        init="pca",
        learning_rate="auto",
        random_state=42,
    ).fit_transform(matrix)
    return pca_xy, tsne_xy


def score_anomalies(matrix: np.ndarray, index: pd.DataFrame) -> pd.DataFrame:
    global_centroid = matrix.mean(axis=0)
    global_dist = np.linalg.norm(matrix - global_centroid, axis=1)
    modality_dist = group_centroid_distance(matrix, index["File Group"])
    agency_dist = group_centroid_distance(matrix, index["Agency"])

    nn = NearestNeighbors(n_neighbors=min(2, len(matrix)), metric="cosine")
    nn.fit(matrix)
    nn_dist, _ = nn.kneighbors(matrix)
    nearest_neighbor_dist = nn_dist[:, 1] if nn_dist.shape[1] > 1 else np.zeros(len(matrix))

    iso = IsolationForest(n_estimators=400, contamination="auto", random_state=42)
    isolation_uniqueness = -iso.fit(matrix).score_samples(matrix)

    cosine_centroid = pairwise_distances(matrix, global_centroid.reshape(1, -1), metric="cosine").ravel()

    result = index.copy()
    result["global_centroid_distance"] = global_dist
    result["modality_centroid_distance"] = modality_dist
    result["agency_centroid_distance"] = agency_dist
    result["nearest_neighbor_cosine_distance"] = nearest_neighbor_dist
    result["global_centroid_cosine_distance"] = cosine_centroid
    result["isolation_uniqueness"] = isolation_uniqueness

    components = [
        "global_centroid_distance",
        "modality_centroid_distance",
        "agency_centroid_distance",
        "nearest_neighbor_cosine_distance",
        "global_centroid_cosine_distance",
        "isolation_uniqueness",
    ]
    for col in components:
        result[f"{col}_pct"] = percentile_rank(result[col].to_numpy())
    result["uniqueness_score"] = result[[f"{col}_pct" for col in components]].mean(axis=1)
    result = result.sort_values("uniqueness_score", ascending=False).reset_index(drop=True)
    result["uniqueness_rank"] = np.arange(1, len(result) + 1)
    return result


def plot_anomalies(df: pd.DataFrame, output_path: Path) -> None:
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

    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    fig.suptitle("UAP/UFO Embedding Uniqueness", fontsize=28, fontweight="bold", y=0.98)

    scatter = axes[0, 0].scatter(
        df["pca_1"],
        df["pca_2"],
        c=df["uniqueness_score"],
        s=90,
        cmap=sns.blend_palette([PALETTE["lunar"], PALETTE["ion"], PALETTE["signal"], PALETTE["flare"]], as_cmap=True),
        edgecolor=PALETTE["ink"],
        linewidth=0.4,
    )
    axes[0, 0].set_title("PCA Colored by Uniqueness")
    fig.colorbar(scatter, ax=axes[0, 0], label="Uniqueness score")

    sns.scatterplot(
        data=df,
        x="tsne_1",
        y="tsne_2",
        hue="File Group",
        size="uniqueness_score",
        sizes=(45, 180),
        palette=GROUP_COLORS,
        alpha=0.9,
        edgecolor=PALETTE["ink"],
        linewidth=0.4,
        ax=axes[0, 1],
    )
    axes[0, 1].set_title("t-SNE by Modality")
    axes[0, 1].legend(frameon=False, fontsize=10, title_fontsize=10)

    top = df.nsmallest(15, "uniqueness_rank").copy()
    top["short_title"] = top["title"].str.slice(0, 44)
    sns.barplot(
        data=top,
        x="uniqueness_score",
        y="short_title",
        hue="File Group",
        palette=GROUP_COLORS,
        dodge=False,
        ax=axes[1, 0],
    )
    axes[1, 0].set_title("Top 15 Most Unique Files")
    axes[1, 0].set_xlabel("Uniqueness score")
    axes[1, 0].set_ylabel("")
    axes[1, 0].legend(frameon=False, fontsize=10)

    heat = df.pivot_table(
        index="Agency",
        columns="File Group",
        values="uniqueness_score",
        aggfunc="mean",
        fill_value=0,
    )
    sns.heatmap(
        heat,
        annot=True,
        fmt=".2f",
        cmap=sns.blend_palette([PALETTE["lunar"], PALETTE["signal"], PALETTE["flare"]], as_cmap=True),
        linewidths=1,
        linecolor="#F7F3EA",
        cbar=False,
        ax=axes[1, 1],
    )
    axes[1, 1].set_title("Mean Uniqueness by Agency and Modality")
    axes[1, 1].set_xlabel("")
    axes[1, 1].set_ylabel("")

    for ax in axes.flat:
        ax.title.set_fontweight("bold")
    import string
    for i, a in enumerate([ax for ax in fig.axes if ax.get_title() or ax.get_xlabel() or ax.get_ylabel()]):
        a.text(-0.05, 1.05, string.ascii_uppercase[i], transform=a.transAxes, fontsize=24, fontweight="bold", va="bottom", ha="right")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-dir", type=Path, default=DEFAULT_EMBEDDING_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    ensure_dirs()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    embedding_path = args.embedding_dir / "document_embeddings.npz"
    index_path = args.embedding_dir / "document_index.csv"
    if not embedding_path.exists() or not index_path.exists():
        raise SystemExit("Document embeddings not found. Run scripts/ufo_embed_multimodal.py first.")

    data = np.load(embedding_path, allow_pickle=False)
    ids = [str(x) for x in data["ids"]]
    matrix = l2_normalize(data["embeddings"].astype(np.float32))
    index = normalize_index_columns(pd.read_csv(index_path).fillna(""))
    index = index.set_index("document_id").loc[ids].reset_index()

    scores = score_anomalies(matrix, index)
    pca_xy, tsne_xy = compute_projection(matrix)
    position = {doc_id: i for i, doc_id in enumerate(ids)}
    order = scores["document_id"].map(position).to_numpy()
    scores["pca_1"] = pca_xy[order, 0]
    scores["pca_2"] = pca_xy[order, 1]
    scores["tsne_1"] = tsne_xy[order, 0]
    scores["tsne_2"] = tsne_xy[order, 1]

    scores.to_csv(args.output_dir / "ufo_anomaly_scores.csv", index=False)
    scores.head(args.top).to_csv(args.output_dir / "top_unique.csv", index=False)
    save_json(
        args.output_dir / "anomaly_summary.json",
        {
            "n_documents": int(len(scores)),
            "top_n_path": str(args.output_dir / "top_unique.csv"),
            "score_components": [
                "global_centroid_distance",
                "modality_centroid_distance",
                "agency_centroid_distance",
                "nearest_neighbor_cosine_distance",
                "global_centroid_cosine_distance",
                "isolation_uniqueness",
            ],
        },
    )
    plot_anomalies(scores, FIGURES_DIR / "ufo_anomaly_overview.png")

    print(f"Scored {len(scores)} documents")
    print(f"Anomaly scores: {args.output_dir / 'ufo_anomaly_scores.csv'}")
    print(f"Top unique: {args.output_dir / 'top_unique.csv'}")
    print(f"Figure: {FIGURES_DIR / 'ufo_anomaly_overview.png'}")
    print(scores[["uniqueness_rank", "title", "Agency", "File Group", "uniqueness_score"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
