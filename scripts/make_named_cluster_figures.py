"""Create renamed evidence-family cluster figures for Analysis 2b."""

from __future__ import annotations

from textwrap import wrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ufo_common import PALETTE, PROJECT_ROOT


OUT = PROJECT_ROOT / "analysis2b" / "figures"

CLUSTER_LABELS = {
    0: "DOW modern operational\nmission reports",
    1: "FBI late-2025 photo /\nvisual evidence packet",
    2: "State Dept diplomatic\ncable family",
    3: "FBI historical HQ\narchive sections",
    4: "NASA lunar / space\nvisual material",
}

SHORT_LABELS = {
    0: "C0 DOW Ops",
    1: "C1 FBI Visual",
    2: "C2 State Cables",
    3: "C3 FBI HQ",
    4: "C4 NASA Space",
}

CLUSTER_COLORS = {
    0: "#D95D39",  # flare
    1: "#4FB3BF",  # ion
    2: "#F2AA4C",  # signal
    3: "#536976",  # steel
    4: "#79C99E",  # radar
}

AGENCY_COLORS = {
    "Department of War": "#D95D39",
    "FBI": "#4FB3BF",
    "Department of State": "#F2AA4C",
    "NASA": "#79C99E",
}

MODALITY_COLORS = {
    "PDF": "#F2AA4C",
    "IMG": "#79C99E",
    "VID": "#4FB3BF",
}


def setup() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sns.set_theme(
        style="whitegrid",
        context="talk",
        rc={
            "figure.facecolor": "#F7F3EA",
            "axes.facecolor": "#F7F3EA",
            "axes.edgecolor": PALETTE["ink"],
            "grid.color": "#D8D0BF",
            "text.color": PALETTE["ink"],
        },
    )


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    clusters = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "cluster_interpretation" / "baseline_kmeans_clusters.csv")
    composition = pd.read_csv(PROJECT_ROOT / "analysis2b" / "cluster_cards" / "cluster_composition_summary.csv")
    reps = pd.read_csv(PROJECT_ROOT / "analysis2b" / "cluster_cards" / "cluster_cards.csv")
    residual = pd.read_csv(PROJECT_ROOT / "analysis-2.0" / "residual_analysis" / "residual_cluster_comparison.csv")
    clusters["cluster_label"] = clusters["cluster"].map(CLUSTER_LABELS)
    clusters["short_label"] = clusters["cluster"].map(SHORT_LABELS)
    composition["cluster_label"] = composition["cluster"].map(CLUSTER_LABELS)
    composition["short_label"] = composition["cluster"].map(SHORT_LABELS)
    reps["cluster_label"] = reps["cluster"].map(CLUSTER_LABELS)
    reps["short_label"] = reps["cluster"].map(SHORT_LABELS)
    return clusters, composition, reps, residual


def plot_embedding_map(clusters: pd.DataFrame, composition: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(24, 18))
    fig.suptitle(
        "Named Evidence Families in the UAP Multimodal Embedding Map",
        fontsize=30,
        fontweight="bold",
        y=0.98,
    )

    ax = axes[0, 0]
    sns.scatterplot(
        data=clusters,
        x="pca_1",
        y="pca_2",
        hue="cluster",
        palette=CLUSTER_COLORS,
        s=115,
        alpha=0.9,
        edgecolor=PALETTE["ink"],
        linewidth=0.35,
        ax=ax,
        legend=False,
    )
    centers = clusters.groupby("cluster")[["pca_1", "pca_2"]].mean()
    for cluster, row in centers.iterrows():
        ax.scatter(row["pca_1"], row["pca_2"], s=620, marker="*", color=CLUSTER_COLORS[cluster], edgecolor="black", linewidth=1.4)
        ax.text(
            row["pca_1"],
            row["pca_2"],
            f" {SHORT_LABELS[cluster]}",
            fontsize=13,
            fontweight="bold",
            va="center",
            ha="left",
            bbox={"boxstyle": "round,pad=0.28", "facecolor": "#FFF9E8", "edgecolor": CLUSTER_COLORS[cluster], "alpha": 0.92},
        )
    ax.set_title("PCA Map with Human Evidence-Family Labels", fontweight="bold")
    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")

    ax = axes[0, 1]
    sns.scatterplot(
        data=clusters,
        x="pca_1",
        y="pca_2",
        hue="Agency",
        style="File Group",
        palette=AGENCY_COLORS,
        s=95,
        alpha=0.88,
        edgecolor=PALETTE["ink"],
        linewidth=0.3,
        ax=ax,
    )
    ax.set_title("Same Map Colored by Agency, Styled by Modality", fontweight="bold")
    ax.legend(frameon=False, fontsize=9, title_fontsize=10, loc="best")

    ax = axes[1, 0]
    size_df = composition.sort_values("cluster")
    sns.barplot(data=size_df, y="short_label", x="size", hue="cluster", palette=CLUSTER_COLORS, dodge=False, legend=False, ax=ax)
    ax.set_title("Evidence-Family Sizes", fontweight="bold")
    ax.set_xlabel("Files")
    ax.set_ylabel("")
    for container in ax.containers:
        ax.bar_label(container, fontsize=11, padding=3)

    ax = axes[1, 1]
    purity = composition.melt(
        id_vars=["short_label"],
        value_vars=["agency_purity", "modality_purity"],
        var_name="purity_type",
        value_name="purity",
    )
    purity["purity_type"] = purity["purity_type"].map({"agency_purity": "Agency purity", "modality_purity": "Modality purity"})
    sns.barplot(data=purity, y="short_label", x="purity", hue="purity_type", palette=[PALETTE["flare"], PALETTE["ion"]], ax=ax)
    ax.set_title("How Much Each Family Is Driven by Agency or Modality", fontweight="bold")
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Purity")
    ax.set_ylabel("")
    ax.legend(frameon=False)

    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(OUT / "named_cluster_embedding_map.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_composition_dashboard(clusters: pd.DataFrame, composition: pd.DataFrame, residual: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(30, 18))
    fig.suptitle("Evidence-Family Composition and Confounding Checks", fontsize=30, fontweight="bold", y=0.98)

    agency = pd.crosstab(clusters["short_label"], clusters["Agency"], normalize="index").loc[[SHORT_LABELS[i] for i in sorted(SHORT_LABELS)]]
    agency.plot(kind="barh", stacked=True, color=[AGENCY_COLORS.get(c, "#999999") for c in agency.columns], ax=axes[0, 0])
    axes[0, 0].set_title("Agency Composition", fontweight="bold")
    axes[0, 0].set_xlabel("Share within family")
    axes[0, 0].set_ylabel("")
    axes[0, 0].legend(frameon=False, fontsize=9)

    modality = pd.crosstab(clusters["short_label"], clusters["File Group"], normalize="index").loc[[SHORT_LABELS[i] for i in sorted(SHORT_LABELS)]]
    modality.plot(kind="barh", stacked=True, color=[MODALITY_COLORS.get(c, "#999999") for c in modality.columns], ax=axes[0, 1])
    axes[0, 1].set_title("Modality Composition", fontweight="bold")
    axes[0, 1].set_xlabel("Share within family")
    axes[0, 1].set_ylabel("")
    axes[0, 1].legend(frameon=False, fontsize=9)

    ax = axes[0, 2]
    heat = pd.crosstab(clusters["Agency"], clusters["short_label"]).loc[:, [SHORT_LABELS[i] for i in sorted(SHORT_LABELS)]]
    sns.heatmap(heat, annot=True, fmt="d", cmap=sns.blend_palette(["#F7F3EA", PALETTE["ion"], PALETTE["night"]], as_cmap=True), cbar=False, linewidths=1, linecolor="#F7F3EA", ax=ax)
    ax.set_title("Agency x Evidence Family Counts", fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")

    ax = axes[1, 0]
    residual_plot = residual[["variant", "silhouette", "agency_purity", "modality_purity"]].melt(id_vars="variant", var_name="metric", value_name="value")
    residual_plot["variant"] = residual_plot["variant"].str.replace("_", " ").str.title()
    residual_plot["metric"] = residual_plot["metric"].map({"silhouette": "Silhouette", "agency_purity": "Agency purity", "modality_purity": "Modality purity"})
    sns.barplot(data=residual_plot, x="variant", y="value", hue="metric", palette=[PALETTE["radar"], PALETTE["flare"], PALETTE["ion"]], ax=ax)
    ax.set_title("Confounding Check: Raw vs Controlled Embeddings", fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Score")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(frameon=False, fontsize=9)

    ax = axes[1, 1]
    sns.scatterplot(
        data=clusters,
        x="pca_1",
        y="pca_2",
        hue="cluster",
        size="File Group",
        palette=CLUSTER_COLORS,
        sizes={"PDF": 70, "IMG": 130, "VID": 170},
        alpha=0.86,
        edgecolor=PALETTE["ink"],
        linewidth=0.35,
        legend=False,
        ax=ax,
    )
    ax.set_title("Modality-Weighted PCA View", fontweight="bold")

    ax = axes[1, 2]
    ax.axis("off")
    text = (
        "Interpretation rule:\n\n"
        "These clusters are evidence families, not UAP types.\n\n"
        "Analysis 2.0 result:\n"
        "Raw silhouette ~= 0.414\n"
        "Agency + modality controlled silhouette ~= 0.186\n\n"
        "Meaning:\n"
        "The archive has stable structure, but much of that structure is institutional and format-driven.\n\n"
        "Use these labels for triage, retrieval, and manual review prioritization."
    )
    ax.text(0, 1, text, va="top", ha="left", fontsize=16, linespacing=1.35, bbox={"facecolor": "#FFF9E8", "edgecolor": PALETTE["signal"], "boxstyle": "round,pad=0.75"})

    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(OUT / "named_cluster_composition_dashboard.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_representative_dashboard(clusters: pd.DataFrame, reps: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(28, 16), gridspec_kw={"width_ratios": [1.05, 1.25]})
    fig.suptitle("Representative Files Behind the Evidence-Family Labels", fontsize=30, fontweight="bold", y=0.98)

    ax = axes[0]
    sns.scatterplot(
        data=clusters,
        x="pca_1",
        y="pca_2",
        hue="cluster",
        palette=CLUSTER_COLORS,
        s=90,
        alpha=0.72,
        edgecolor=PALETTE["ink"],
        linewidth=0.25,
        legend=False,
        ax=ax,
    )
    first_reps = reps[reps["rank_within_cluster"] <= 3].merge(
        clusters[["document_id", "pca_1", "pca_2"]], on="document_id", how="left"
    )
    sns.scatterplot(
        data=first_reps,
        x="pca_1",
        y="pca_2",
        hue="cluster",
        palette=CLUSTER_COLORS,
        s=230,
        marker="D",
        edgecolor="black",
        linewidth=0.8,
        legend=False,
        ax=ax,
    )
    for _, row in first_reps.iterrows():
        ax.text(row["pca_1"], row["pca_2"], f" {SHORT_LABELS[int(row['cluster'])]} R{int(row['rank_within_cluster'])}", fontsize=10, fontweight="bold")
    ax.set_title("Top 3 Representatives per Evidence Family", fontweight="bold")
    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")

    ax = axes[1]
    ax.axis("off")
    y = 1.0
    line_height = 0.048
    for cluster in sorted(CLUSTER_LABELS):
        label = CLUSTER_LABELS[cluster].replace("\n", " ")
        ax.text(0.0, y, f"{SHORT_LABELS[cluster]}: {label}", color=CLUSTER_COLORS[cluster], fontsize=16, fontweight="bold", va="top")
        y -= line_height * 0.9
        subset = reps[reps["cluster"] == cluster].sort_values("rank_within_cluster").head(5)
        for _, row in subset.iterrows():
            title = "\n    ".join(wrap(str(row["title"]), width=74))
            ax.text(0.03, y, f"{int(row['rank_within_cluster'])}. {title}", fontsize=11.5, va="top", color=PALETTE["ink"])
            y -= line_height * (1.0 + title.count("\n") * 0.42)
        y -= line_height * 0.35
    ax.set_title("Representative Files Used to Humanize the Clusters", fontweight="bold", loc="left")

    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(OUT / "named_cluster_representative_files.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    setup()
    clusters, composition, reps, residual = load()
    plot_embedding_map(clusters, composition)
    plot_composition_dashboard(clusters, composition, residual)
    plot_representative_dashboard(clusters, reps)
    print(f"Wrote named cluster figures to {OUT}")


if __name__ == "__main__":
    main()
