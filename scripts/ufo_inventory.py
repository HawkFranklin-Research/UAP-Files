"""Map the UFO release dataset and create inventory figures.

Outputs:
  analysis/inventory_documents.csv
  analysis/inventory_summary.json
  analysis/figures/ufo_inventory_overview.png
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from PIL import Image

from ufo_common import (
    FIGURES_DIR,
    GROUP_COLORS,
    PALETTE,
    canonical_documents,
    clean_missing,
    ensure_dirs,
    load_metadata,
    pdf_page_count,
    save_json,
    video_duration_seconds,
)


def image_size(path):
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None, None


def enrich_documents(docs: pd.DataFrame) -> pd.DataFrame:
    docs = docs.copy()
    docs["pdf_pages"] = None
    docs["video_duration_sec"] = None
    docs["image_width"] = None
    docs["image_height"] = None

    for idx, row in docs.iterrows():
        path = row["abs_path"]
        group = row["File Group"]
        if group == "PDF":
            docs.at[idx, "pdf_pages"] = pdf_page_count(path)
        elif group == "VID":
            docs.at[idx, "video_duration_sec"] = video_duration_seconds(path)
        elif group == "IMG":
            width, height = image_size(path)
            docs.at[idx, "image_width"] = width
            docs.at[idx, "image_height"] = height

    docs["size_mib"] = docs["file_size_bytes"] / (1024 * 1024)
    docs["metadata_missing_fields"] = docs.apply(
        lambda row: sum(
            not clean_missing(row.get(col, ""))
            for col in ["Incident Date", "Incident Location", "Agency", "Release Date"]
        ),
        axis=1,
    )
    return docs


def build_summary(raw: pd.DataFrame, docs: pd.DataFrame) -> dict:
    duplicate_paths = raw[raw["exists"]]["Output Path"].value_counts()
    duplicate_paths = duplicate_paths[duplicate_paths > 1].to_dict()
    return {
        "raw_metadata_rows": int(len(raw)),
        "existing_metadata_rows": int(raw["exists"].sum()),
        "distinct_physical_files": int(len(docs)),
        "raw_rows_by_file_group": raw["File Group"].value_counts().to_dict(),
        "distinct_files_by_file_group": docs["File Group"].value_counts().to_dict(),
        "distinct_files_by_extension": docs["suffix"].value_counts().to_dict(),
        "raw_rows_by_agency": raw["Agency"].value_counts().to_dict(),
        "distinct_files_by_agency": docs["Agency"].value_counts().to_dict(),
        "duplicate_output_paths": duplicate_paths,
        "total_size_mib": round(float(docs["size_mib"].sum()), 3),
        "size_mib_by_file_group": {
            key: round(float(value), 3)
            for key, value in docs.groupby("File Group")["size_mib"].sum().items()
        },
        "pdf_pages": {
            "known_count": int(docs["pdf_pages"].notna().sum()),
            "total_pages": int(pd.to_numeric(docs["pdf_pages"], errors="coerce").fillna(0).sum()),
            "max_pages": int(pd.to_numeric(docs["pdf_pages"], errors="coerce").fillna(0).max()),
        },
        "video_duration_sec": {
            "known_count": int(docs["video_duration_sec"].notna().sum()),
            "total_sec": round(
                float(pd.to_numeric(docs["video_duration_sec"], errors="coerce").fillna(0).sum()), 2
            ),
            "max_sec": round(
                float(pd.to_numeric(docs["video_duration_sec"], errors="coerce").fillna(0).max()), 2
            ),
        },
    }


def plot_inventory(docs: pd.DataFrame, raw: pd.DataFrame, output_path) -> None:
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

    fig, axes = plt.subplots(2, 3, figsize=(22, 12))
    fig.suptitle("UAP/UFO Release Inventory", fontsize=28, fontweight="bold", y=0.98)

    group_counts = docs["File Group"].value_counts().rename_axis("file_group").reset_index(name="count")
    sns.barplot(
        data=group_counts,
        x="file_group",
        y="count",
        hue="file_group",
        palette=GROUP_COLORS,
        legend=False,
        ax=axes[0, 0],
    )
    axes[0, 0].set_title("Distinct Files by Modality")
    axes[0, 0].set_xlabel("")
    axes[0, 0].set_ylabel("Files")

    agency_group = pd.crosstab(docs["Agency"], docs["File Group"])
    sns.heatmap(
        agency_group,
        annot=True,
        fmt="d",
        cmap=sns.blend_palette([PALETTE["lunar"], PALETTE["ion"], PALETTE["night"]], as_cmap=True),
        cbar=False,
        linewidths=1,
        linecolor="#F7F3EA",
        ax=axes[0, 1],
    )
    axes[0, 1].set_title("Agency x Modality")
    axes[0, 1].set_xlabel("")
    axes[0, 1].set_ylabel("")

    sns.boxenplot(
        data=docs,
        x="File Group",
        y="size_mib",
        hue="File Group",
        palette=GROUP_COLORS,
        legend=False,
        ax=axes[0, 2],
    )
    axes[0, 2].set_title("File Size Distribution")
    axes[0, 2].set_xlabel("")
    axes[0, 2].set_ylabel("MiB")
    axes[0, 2].set_yscale("symlog")

    missing = (
        raw[["Agency", "Release Date", "Incident Date", "Incident Location", "Output Path"]]
        .eq("")
        .sum()
        .rename_axis("field")
        .reset_index(name="missing_rows")
    )
    sns.barplot(data=missing, y="field", x="missing_rows", color=PALETTE["flare"], ax=axes[1, 0])
    axes[1, 0].set_title("Metadata Missingness")
    axes[1, 0].set_xlabel("Rows missing")
    axes[1, 0].set_ylabel("")

    pdf_pages = pd.to_numeric(docs.loc[docs["File Group"] == "PDF", "pdf_pages"], errors="coerce").dropna()
    sns.histplot(pdf_pages, bins=20, color=PALETTE["signal"], edgecolor=PALETTE["ink"], ax=axes[1, 1])
    axes[1, 1].axvline(6, color=PALETTE["flare"], linestyle="--", linewidth=2, label="Gemini PDF limit")
    axes[1, 1].set_title("PDF Page Counts")
    axes[1, 1].set_xlabel("Pages")
    axes[1, 1].set_ylabel("PDFs")
    axes[1, 1].legend(frameon=False)

    video_duration = pd.to_numeric(
        docs.loc[docs["File Group"] == "VID", "video_duration_sec"], errors="coerce"
    ).dropna()
    sns.histplot(video_duration, bins=16, color=PALETTE["ion"], edgecolor=PALETTE["ink"], ax=axes[1, 2])
    axes[1, 2].axvline(120, color=PALETTE["flare"], linestyle="--", linewidth=2, label="Gemini video limit")
    axes[1, 2].set_title("Video Durations")
    axes[1, 2].set_xlabel("Seconds")
    axes[1, 2].set_ylabel("Videos")
    axes[1, 2].legend(frameon=False)

    for ax in axes.flat:
        ax.title.set_fontweight("bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", default="ufo_release_metadata.csv")
    args = parser.parse_args()

    ensure_dirs()
    raw = load_metadata(Path(args.metadata))
    docs = enrich_documents(canonical_documents(raw))

    inventory_path = FIGURES_DIR.parent / "inventory_documents.csv"
    docs_for_csv = docs.copy()
    docs_for_csv["abs_path"] = docs_for_csv["abs_path"].map(str)
    docs_for_csv.to_csv(inventory_path, index=False)

    summary = build_summary(raw, docs)
    save_json(FIGURES_DIR.parent / "inventory_summary.json", summary)
    plot_inventory(docs, raw, FIGURES_DIR / "ufo_inventory_overview.png")

    print("Inventory complete")
    print(f"Raw metadata rows: {summary['raw_metadata_rows']}")
    print(f"Distinct physical files: {summary['distinct_physical_files']}")
    print(f"By modality: {summary['distinct_files_by_file_group']}")
    print(f"Figure: {FIGURES_DIR / 'ufo_inventory_overview.png'}")


if __name__ == "__main__":
    main()
