"""Cluster UFO release document embeddings and create PCA/t-SNE figures.

Run after embeddings exist:
  python3 scripts/ufo_cluster_embeddings.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score

from ufo_common import ANALYSIS_DIR, FIGURES_DIR, GROUP_COLORS, PALETTE, ensure_dirs, l2_normalize, save_json


DEFAULT_EMBEDDING_DIR = ANALYSIS_DIR / "embeddings"
DEFAULT_OUTPUT_DIR = ANALYSIS_DIR / "clustering"


def normalize_index_columns(index: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "agency": "Agency",
        "file_group": "File Group",
        "title": "Title",
        "output_path": "Output Path",
        "source_filename": "Source Filename",
    }
    return index.rename(columns={old: new for old, new in rename.items() if old in index.columns})


def choose_k(matrix: np.ndarray, requested: str) -> tuple[int, dict[str, float]]:
    n = len(matrix)
    if requested != "auto":
        return int(requested), {}
    scores: dict[str, float] = {}
    max_k = min(12, n - 1)
    best_k = 2
    best_score = -1.0
    for k in range(2, max_k + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init="auto").fit_predict(matrix)
        score = float(silhouette_score(matrix, labels))
        scores[str(k)] = score
        if score > best_score:
            best_score = score
            best_k = k
    return best_k, scores


def compute_projection(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[float]]:
    pca = PCA(n_components=2, random_state=42)
    pca_xy = pca.fit_transform(matrix)
    perplexity = max(5, min(30, (len(matrix) - 1) // 3))
    tsne = TSNE(
        n_components=2,
        perplexity=perplexity,
        init="pca",
        learning_rate="auto",
        random_state=42,
    )
    tsne_xy = tsne.fit_transform(matrix)
    return pca_xy, tsne_xy, [float(x) for x in pca.explained_variance_ratio_]


def plot_clusters(df: pd.DataFrame, output_path: Path) -> None:
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
    cluster_palette = sns.blend_palette(
        [PALETTE["night"], PALETTE["ion"], PALETTE["radar"], PALETTE["signal"], PALETTE["flare"]],
        n_colors=max(3, df["cluster"].nunique()),
    )

    fig, axes = plt.subplots(2, 2, figsize=(18, 15))
    fig.suptitle("UAP/UFO Embedding Clusters", fontsize=28, fontweight="bold", y=0.98)

    sns.scatterplot(
        data=df,
        x="pca_1",
        y="pca_2",
        hue="File Group",
        palette=GROUP_COLORS,
        s=90,
        alpha=0.9,
        edgecolor=PALETTE["ink"],
        linewidth=0.4,
        ax=axes[0, 0],
    )
    axes[0, 0].set_title("PCA by Modality")

    sns.scatterplot(
        data=df,
        x="tsne_1",
        y="tsne_2",
        hue="cluster",
        palette=cluster_palette,
        s=90,
        alpha=0.9,
        edgecolor=PALETTE["ink"],
        linewidth=0.4,
        ax=axes[0, 1],
    )
    axes[0, 1].set_title("t-SNE by Cluster")

    sns.scatterplot(
        data=df,
        x="pca_1",
        y="pca_2",
        hue="Agency",
        palette=sns.color_palette("crest", n_colors=df["Agency"].nunique()),
        s=90,
        alpha=0.9,
        edgecolor=PALETTE["ink"],
        linewidth=0.4,
        ax=axes[1, 0],
    )
    axes[1, 0].set_title("PCA by Agency")

    heat = pd.crosstab(df["Agency"], df["cluster"])
    sns.heatmap(
        heat,
        annot=True,
        fmt="d",
        cmap=sns.blend_palette([PALETTE["lunar"], PALETTE["radar"], PALETTE["night"]], as_cmap=True),
        cbar=False,
        linewidths=1,
        linecolor="#F7F3EA",
        ax=axes[1, 1],
    )
    axes[1, 1].set_title("Agency x Cluster")
    axes[1, 1].set_xlabel("Cluster")
    axes[1, 1].set_ylabel("")

    for ax in axes.flat:
        ax.title.set_fontweight("bold")
        if ax.get_legend():
            ax.legend(frameon=False, fontsize=10, title_fontsize=10)
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
    parser.add_argument("--clusters", default="auto", help="Use an integer or 'auto'.")
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

    pca_xy, tsne_xy, explained = compute_projection(matrix)
    k, scores = choose_k(matrix, args.clusters)
    labels = KMeans(n_clusters=k, random_state=42, n_init="auto").fit_predict(matrix)

    result = index.copy()
    result["cluster"] = labels
    result["pca_1"] = pca_xy[:, 0]
    result["pca_2"] = pca_xy[:, 1]
    result["tsne_1"] = tsne_xy[:, 0]
    result["tsne_2"] = tsne_xy[:, 1]
    result.to_csv(args.output_dir / "document_clusters.csv", index=False)

    summary = (
        result.groupby(["cluster", "Agency", "File Group"])
        .size()
        .reset_index(name="count")
        .sort_values(["cluster", "count"], ascending=[True, False])
    )
    summary.to_csv(args.output_dir / "cluster_summary.csv", index=False)
    save_json(
        args.output_dir / "cluster_model_summary.json",
        {
            "n_documents": int(len(result)),
            "n_clusters": int(k),
            "silhouette_scores": scores,
            "pca_explained_variance_ratio": explained,
        },
    )
    plot_clusters(result, FIGURES_DIR / "ufo_clustering_overview.png")

    print(f"Clustered {len(result)} documents into {k} clusters")
    print(f"Clusters: {args.output_dir / 'document_clusters.csv'}")
    print(f"Figure: {FIGURES_DIR / 'ufo_clustering_overview.png'}")


if __name__ == "__main__":
    main()
