"""Shared helpers for UFO release embedding analysis scripts."""

from __future__ import annotations

import csv
import json
import mimetypes
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "ufo_release"
METADATA_PATH = PROJECT_ROOT / "ufo_release_metadata.csv"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
FIGURES_DIR = ANALYSIS_DIR / "figures"
CACHE_DIR = ANALYSIS_DIR / "cache"

PALETTE = {
    "ink": "#101820",
    "signal": "#F2AA4C",
    "radar": "#79C99E",
    "ion": "#4FB3BF",
    "flare": "#D95D39",
    "lunar": "#B8C4D9",
    "steel": "#536976",
    "night": "#1D3557",
}
GROUP_COLORS = {
    "PDF": PALETTE["signal"],
    "IMG": PALETTE["radar"],
    "VID": PALETTE["ion"],
    "Unknown": PALETTE["lunar"],
}


def ensure_dirs() -> None:
    for path in (ANALYSIS_DIR, FIGURES_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def clean_missing(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null", "n/a", "[n/a]"}:
        return ""
    return text


def slugify(value: str) -> str:
    value = clean_missing(value) or "unknown"
    value = re.sub(r"[^A-Za-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def resolve_output_path(value: str) -> Path | None:
    value = clean_missing(value)
    if not value:
        return None
    return (PROJECT_ROOT / value).resolve()


def load_metadata(metadata_path: Path = METADATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(metadata_path).fillna("")
    for col in df.columns:
        df[col] = df[col].map(clean_missing)
    df["abs_path"] = df["Output Path"].map(resolve_output_path)
    df["exists"] = df["abs_path"].map(lambda p: p is not None and p.exists())
    df["file_size_bytes"] = df["abs_path"].map(lambda p: p.stat().st_size if p is not None and p.exists() else 0)
    df["suffix"] = df["abs_path"].map(lambda p: p.suffix.lower() if p is not None and p.exists() else "")
    df["mime_type"] = df["abs_path"].map(detect_mime_type)
    df["record_id"] = [f"row_{i:03d}" for i in range(1, len(df) + 1)]
    return df


def detect_mime_type(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    suffix = path.suffix.lower()
    overrides = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    return overrides.get(suffix) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def canonical_documents(df: pd.DataFrame) -> pd.DataFrame:
    docs = (
        df[df["exists"]]
        .sort_values(["Output Path", "Title"])
        .drop_duplicates("Output Path")
        .copy()
        .reset_index(drop=True)
    )
    docs["document_id"] = [f"doc_{i:04d}" for i in range(1, len(docs) + 1)]
    docs["record_text"] = docs.apply(record_text, axis=1)
    return docs


def record_text(row: pd.Series) -> str:
    parts = [
        f"Title: {row.get('Title', '')}",
        f"Agency: {row.get('Agency', '')}",
        f"File group: {row.get('File Group', '')}",
        f"Release date: {row.get('Release Date', '')}",
        f"Incident date: {row.get('Incident Date', '') or 'missing'}",
        f"Incident location: {row.get('Incident Location', '') or 'missing'}",
        f"Filename: {row.get('Source Filename', '')}",
    ]
    return "\n".join(parts)


def pdf_page_count(path: Path) -> int | None:
    try:
        result = subprocess.run(
            ["pdfinfo", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def video_duration_seconds(path: Path) -> float | None:
    try:
        import cv2
    except Exception:
        return None
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    if fps <= 0 or frames <= 0:
        return None
    return float(frames / fps)


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    denom = np.linalg.norm(matrix, axis=1, keepdims=True)
    denom[denom == 0] = 1
    return matrix / denom


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_npz_embeddings(path: Path) -> tuple[np.ndarray, list[str]]:
    data = np.load(path, allow_pickle=False)
    return data["embeddings"], [str(x) for x in data["ids"]]


def write_rows(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def counter_to_records(counter: Counter) -> list[dict[str, object]]:
    return [{"name": key, "count": int(value)} for key, value in counter.items()]
