"""Create Gemini multimodal embeddings for the UFO release.

Strategy:
  - One canonical document per distinct Output Path.
  - Every embedding request includes structured metadata text plus media bytes.
  - PDFs over 6 pages are split into 6-page chunks, embedded, then averaged.
  - Images are embedded directly.
  - Videos <=120s are embedded directly.
  - Videos >120s are represented by up to 6 sampled JPEG frames unless --video-mode direct.

Required for real embedding runs:
  export GEMINI_API_KEY=...
  python3 scripts/ufo_embed_multimodal.py --resume

Useful dry run:
  python3 scripts/ufo_embed_multimodal.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ufo_common import (
    ANALYSIS_DIR,
    CACHE_DIR,
    PROJECT_ROOT,
    canonical_documents,
    ensure_dirs,
    load_metadata,
    l2_normalize,
    pdf_page_count,
    record_text,
    slugify,
    video_duration_seconds,
)


EMBEDDING_DIR = ANALYSIS_DIR / "embeddings"
DEFAULT_USAGE_STATE = EMBEDDING_DIR / "gemini_key_usage_state.json"


@dataclass
class EmbeddingJob:
    embedding_id: str
    document_id: str
    chunk_id: str
    title: str
    agency: str
    file_group: str
    output_path: str
    source_filename: str
    source_path: str
    mime_type: str
    metadata_text: str
    chunk_kind: str
    page_start: int | None = None
    page_end: int | None = None
    video_duration_sec: float | None = None
    source_part_count: int = 1
    skip_reason: str = ""


@dataclass
class PdfChunk:
    source_path: str
    page_start: int
    page_end: int
    mime_type: str
    chunk_kind: str
    source_part_count: int


def key_fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def masked_key(key: str) -> str:
    if len(key) <= 10:
        return "***"
    return f"{key[:6]}...{key[-4:]}"


def load_api_keys(env_name: str, key_file: Path | None) -> list[str]:
    candidates: list[str] = []
    env_value = os.getenv(env_name) or os.getenv("GOOGLE_API_KEY") or ""
    if env_value:
        candidates.extend(re.findall(r"AIza[0-9A-Za-z_\-]+", env_value))
        if not candidates:
            candidates.extend(part.strip() for part in re.split(r"[\s,;]+", env_value) if part.strip())

    if key_file:
        text = key_file.read_text(encoding="utf-8")
        found = re.findall(r"AIza[0-9A-Za-z_\-]+", text)
        if found:
            candidates.extend(found)
        else:
            for line in text.splitlines():
                line = line.split("#", 1)[0].strip().strip("\"'")
                if line:
                    candidates.append(line)

    unique: list[str] = []
    seen: set[str] = set()
    for key in candidates:
        key = key.strip().strip("\"'")
        if key and key not in seen:
            unique.append(key)
            seen.add(key)
    return unique


class GeminiKeyPool:
    """Thread-safe multi-key limiter with local, non-secret usage state."""

    def __init__(
        self,
        keys: list[str],
        state_path: Path,
        rpm_per_key: int,
        rpd_per_key: int,
        tpm_per_key: int,
        estimated_tokens_per_job: int,
    ) -> None:
        self.keys = keys
        self.state_path = state_path
        self.rpm_per_key = rpm_per_key
        self.rpd_per_key = rpd_per_key
        self.tpm_per_key = tpm_per_key
        self.estimated_tokens_per_job = estimated_tokens_per_job
        self.pointer = 0
        self.lock = threading.Lock()
        self.in_flight: set[str] = set()
        self.state = self._load_state()
        self._reset_if_new_pacific_day()

    def _pacific_date(self) -> str:
        return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()

    def _load_state(self) -> dict[str, object]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"pacific_date": self._pacific_date(), "keys": {}}

    def _reset_if_new_pacific_day(self) -> None:
        today = self._pacific_date()
        if self.state.get("pacific_date") != today:
            self.state = {"pacific_date": today, "keys": {}}
        for key in self.keys:
            key_id = key_fingerprint(key)
            self.state.setdefault("keys", {}).setdefault(
                key_id,
                {
                    "requests_today": 0,
                    "request_timestamps": [],
                    "token_events": [],
                    "masked_key": masked_key(key),
                },
            )

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _entry(self, key: str) -> dict[str, object]:
        return self.state["keys"][key_fingerprint(key)]

    def _trim_minute(self, entry: dict[str, object], now: float) -> None:
        entry["request_timestamps"] = [ts for ts in entry.get("request_timestamps", []) if now - ts < 60]
        entry["token_events"] = [
            event for event in entry.get("token_events", []) if now - float(event[0]) < 60
        ]

    def _key_available(self, key: str, now: float) -> tuple[bool, float]:
        entry = self._entry(key)
        self._trim_minute(entry, now)
        requests_today = int(entry.get("requests_today", 0))
        if self.rpd_per_key > 0 and requests_today >= self.rpd_per_key:
            return False, float("inf")

        request_timestamps = entry.get("request_timestamps", [])
        if self.rpm_per_key > 0 and len(request_timestamps) >= self.rpm_per_key:
            return False, 60 - (now - min(request_timestamps))

        token_events = entry.get("token_events", [])
        tokens_this_minute = sum(int(event[1]) for event in token_events)
        if (
            self.tpm_per_key > 0
            and self.estimated_tokens_per_job > 0
            and tokens_this_minute + self.estimated_tokens_per_job > self.tpm_per_key
        ):
            oldest = min(float(event[0]) for event in token_events) if token_events else now
            return False, 60 - (now - oldest)

        return True, 0.0

    def acquire(self) -> tuple[str, str]:
        while True:
            with self.lock:
                self._reset_if_new_pacific_day()
                now = time.time()
                waits = []
                for offset in range(len(self.keys)):
                    idx = (self.pointer + offset) % len(self.keys)
                    key = self.keys[idx]
                    key_id = key_fingerprint(key)
                    if key_id in self.in_flight:
                        waits.append(1.0)
                        continue
                    available, wait_seconds = self._key_available(key, now)
                    if available:
                        self.pointer = (idx + 1) % len(self.keys)
                        entry = self._entry(key)
                        entry["requests_today"] = int(entry.get("requests_today", 0)) + 1
                        entry.setdefault("request_timestamps", []).append(now)
                        entry.setdefault("token_events", []).append([now, self.estimated_tokens_per_job])
                        entry["masked_key"] = masked_key(key)
                        self.in_flight.add(key_id)
                        self.save()
                        return key, key_id
                    waits.append(wait_seconds)

            finite_waits = [w for w in waits if w != float("inf")]
            if not finite_waits:
                raise RuntimeError("All configured API keys reached their local RPD limit for today.")
            sleep_for = max(1.0, min(finite_waits))
            print(f"All keys are at minute limits; sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)

    def release(self, key_id: str) -> None:
        with self.lock:
            self.in_flight.discard(key_id)

    def snapshot(self) -> list[dict[str, object]]:
        with self.lock:
            self._reset_if_new_pacific_day()
            now = time.time()
            rows = []
            for key in self.keys:
                entry = self._entry(key)
                self._trim_minute(entry, now)
                rows.append(
                    {
                        "key_id": key_fingerprint(key),
                        "masked_key": masked_key(key),
                        "requests_today": int(entry.get("requests_today", 0)),
                        "requests_last_minute": len(entry.get("request_timestamps", [])),
                        "estimated_tokens_last_minute": sum(int(event[1]) for event in entry.get("token_events", [])),
                        "in_flight": key_fingerprint(key) in self.in_flight,
                    }
                )
            return rows


def run_checked(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


def pdf_is_encrypted(path: Path) -> bool:
    try:
        result = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True, text=True)
    except Exception:
        return False
    for line in result.stdout.splitlines():
        if line.startswith("Encrypted:"):
            return "yes" in line.lower()
    return False


def rasterize_pdf_page_range(path: Path, document_id: str, start: int, end: int) -> list[Path]:
    slug = slugify(f"{document_id}_{path.stem}")
    image_dir = CACHE_DIR / "pdf_page_images" / slug / f"pages_{start:04d}_{end:04d}"
    image_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(image_dir.glob("page-*.jpg"))
    if len(existing) == end - start + 1:
        return existing

    for old in existing:
        old.unlink()
    prefix = image_dir / "page"
    run_checked(["pdftocairo", "-jpeg", "-f", str(start), "-l", str(end), "-r", "120", str(path), str(prefix)])
    return sorted(image_dir.glob("page-*.jpg"))


def image_chunks_for_pdf(path: Path, document_id: str, pages: int, max_pages: int) -> list[PdfChunk]:
    chunks: list[PdfChunk] = []
    for start in range(1, pages + 1, max_pages):
        end = min(start + max_pages - 1, pages)
        images = rasterize_pdf_page_range(path, document_id, start, end)
        chunks.append(
            PdfChunk(
                source_path="|".join(str(p) for p in images),
                page_start=start,
                page_end=end,
                mime_type="image/jpeg",
                chunk_kind="pdf_page_images",
                source_part_count=len(images),
            )
        )
    return chunks


def chunk_pdf(path: Path, document_id: str, max_pages: int) -> list[PdfChunk]:
    pages = pdf_page_count(path)
    if not pages:
        return []
    if pages <= max_pages:
        return [
            PdfChunk(
                source_path=str(path),
                page_start=1,
                page_end=pages,
                mime_type="application/pdf",
                chunk_kind="pdf_chunk",
                source_part_count=1,
            )
        ]
    if pdf_is_encrypted(path):
        return image_chunks_for_pdf(path, document_id, pages, max_pages)

    slug = slugify(f"{document_id}_{path.stem}")
    page_dir = CACHE_DIR / "pdf_pages" / slug
    chunk_dir = CACHE_DIR / "pdf_chunks" / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir.mkdir(parents=True, exist_ok=True)

    page_pattern = page_dir / "page-%04d.pdf"
    expected_last = page_dir / f"page-{pages:04d}.pdf"
    if not expected_last.exists():
        run_checked(["pdfseparate", str(path), str(page_pattern)])

    chunks: list[PdfChunk] = []
    for start in range(1, pages + 1, max_pages):
        end = min(start + max_pages - 1, pages)
        chunk_path = chunk_dir / f"pages_{start:04d}_{end:04d}.pdf"
        if not chunk_path.exists():
            inputs = [str(page_dir / f"page-{page_num:04d}.pdf") for page_num in range(start, end + 1)]
            try:
                run_checked(["pdfunite", *inputs, str(chunk_path)])
            except subprocess.CalledProcessError:
                if chunk_path.exists():
                    chunk_path.unlink()
                return image_chunks_for_pdf(path, document_id, pages, max_pages)
        chunks.append(
            PdfChunk(
                source_path=str(chunk_path),
                page_start=start,
                page_end=end,
                mime_type="application/pdf",
                chunk_kind="pdf_chunk",
                source_part_count=1,
            )
        )
    return chunks


def sample_video_frames(path: Path, document_id: str, max_frames: int) -> list[Path]:
    try:
        import cv2
    except Exception:
        return []

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return []
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count <= 0:
        cap.release()
        return []

    slug = slugify(f"{document_id}_{path.stem}")
    out_dir = CACHE_DIR / "video_frames" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    positions = np.linspace(0, max(frame_count - 1, 0), num=min(max_frames, frame_count), dtype=int)
    frame_paths: list[Path] = []
    for frame_index in positions:
        out_path = out_dir / f"frame_{int(frame_index):08d}.jpg"
        if not out_path.exists():
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ok, frame = cap.read()
            if ok:
                cv2.imwrite(str(out_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if out_path.exists():
            frame_paths.append(out_path)
    cap.release()
    return frame_paths


def build_jobs(
    docs: pd.DataFrame,
    pdf_max_pages: int,
    video_mode: str,
    max_video_seconds: int,
    max_video_frames: int,
    materialize_chunks: bool,
) -> tuple[list[EmbeddingJob], list[dict[str, object]]]:
    jobs: list[EmbeddingJob] = []
    skipped: list[dict[str, object]] = []

    for _, row in docs.iterrows():
        path = Path(row["abs_path"])
        base = {
            "document_id": row["document_id"],
            "title": row["Title"],
            "agency": row["Agency"],
            "file_group": row["File Group"],
            "output_path": row["Output Path"],
            "source_filename": row["Source Filename"],
            "metadata_text": record_text(row),
        }
        group = row["File Group"]

        if group == "PDF":
            pages = pdf_page_count(path)
            if not pages:
                skipped.append({**base, "source_path": str(path), "skip_reason": "pdf_page_count_failed"})
                continue
            if materialize_chunks:
                chunks = chunk_pdf(path, row["document_id"], pdf_max_pages)
            else:
                chunks = [
                    PdfChunk(
                        source_path=str(path),
                        page_start=start,
                        page_end=min(start + pdf_max_pages - 1, pages),
                        mime_type="application/pdf",
                        chunk_kind="pdf_chunk",
                        source_part_count=1,
                    )
                    for start in range(1, pages + 1, pdf_max_pages)
                ]
            for chunk in chunks:
                chunk_id = f"pdf_pages_{chunk.page_start:04d}_{chunk.page_end:04d}"
                jobs.append(
                    EmbeddingJob(
                        **base,
                        embedding_id=f"{row['document_id']}__{chunk_id}",
                        chunk_id=chunk_id,
                        source_path=chunk.source_path,
                        mime_type=chunk.mime_type,
                        chunk_kind=chunk.chunk_kind,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        source_part_count=chunk.source_part_count,
                    )
                )
            continue

        if group == "IMG":
            jobs.append(
                EmbeddingJob(
                    **base,
                    embedding_id=f"{row['document_id']}__image",
                    chunk_id="image",
                    source_path=str(path),
                    mime_type=row["mime_type"],
                    chunk_kind="image",
                )
            )
            continue

        if group == "VID":
            duration = video_duration_seconds(path)
            direct_video = video_mode in {"auto", "direct"} and duration is not None and duration <= max_video_seconds
            if direct_video:
                jobs.append(
                    EmbeddingJob(
                        **base,
                        embedding_id=f"{row['document_id']}__video_direct",
                        chunk_id="video_direct",
                        source_path=str(path),
                        mime_type=row["mime_type"] or "video/mp4",
                        chunk_kind="video_direct",
                        video_duration_sec=duration,
                    )
                )
                continue

            if video_mode == "direct":
                skipped.append(
                    {
                        **base,
                        "source_path": str(path),
                        "video_duration_sec": duration,
                        "skip_reason": "video_over_120s_or_unknown_duration",
                    }
                )
                continue

            frame_paths = sample_video_frames(path, row["document_id"], max_video_frames) if materialize_chunks else [path]
            if not frame_paths:
                skipped.append(
                    {
                        **base,
                        "source_path": str(path),
                        "video_duration_sec": duration,
                        "skip_reason": "video_frame_sampling_failed",
                    }
                )
                continue
            jobs.append(
                EmbeddingJob(
                    **base,
                    embedding_id=f"{row['document_id']}__video_frames",
                    chunk_id="video_frames",
                    source_path="|".join(str(p) for p in frame_paths),
                    mime_type="image/jpeg",
                    chunk_kind="video_sampled_frames",
                    video_duration_sec=duration,
                    source_part_count=len(frame_paths) if materialize_chunks else max_video_frames,
                )
            )
            continue

        skipped.append({**base, "source_path": str(path), "skip_reason": f"unsupported_file_group_{group}"})

    return jobs, skipped


def load_existing(index_path: Path, npz_path: Path) -> tuple[dict[str, np.ndarray], pd.DataFrame]:
    if not index_path.exists() or not npz_path.exists():
        return {}, pd.DataFrame()
    index = pd.read_csv(index_path).fillna("")
    data = np.load(npz_path, allow_pickle=False)
    ids = [str(x) for x in data["ids"]]
    matrix = data["embeddings"]
    return {embedding_id: matrix[i] for i, embedding_id in enumerate(ids)}, index


def embedding_values(result) -> list[float]:
    embeddings = getattr(result, "embeddings", None)
    if not embeddings:
        raise RuntimeError("Embedding response did not contain embeddings")
    values = getattr(embeddings[0], "values", None)
    if values is None:
        raise RuntimeError("Embedding response did not contain embedding values")
    return list(values)


def embed_job(client, types, model: str, job: EmbeddingJob) -> list[float]:
    contents = [job.metadata_text]
    paths = [Path(p) for p in job.source_path.split("|")]
    for path in paths:
        data = path.read_bytes()
        mime_type = job.mime_type
        if path.suffix.lower() == ".jpg":
            mime_type = "image/jpeg"
        elif path.suffix.lower() == ".png":
            mime_type = "image/png"
        elif path.suffix.lower() == ".pdf":
            mime_type = "application/pdf"
        elif path.suffix.lower() == ".mp4":
            mime_type = "video/mp4"
        contents.append(types.Part.from_bytes(data=data, mime_type=mime_type))
    result = client.models.embed_content(model=model, contents=contents)
    return embedding_values(result)


def save_chunk_outputs(vectors: dict[str, np.ndarray], rows: list[dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered_ids = [row["embedding_id"] for row in rows if row["embedding_id"] in vectors]
    matrix = np.array([vectors[embedding_id] for embedding_id in ordered_ids], dtype=np.float32)
    np.savez_compressed(output_dir / "chunk_embeddings.npz", ids=np.array(ordered_ids), embeddings=matrix)
    pd.DataFrame([row for row in rows if row["embedding_id"] in vectors]).to_csv(
        output_dir / "chunk_index.csv", index=False
    )


def save_document_outputs(output_dir: Path) -> None:
    chunk_index_path = output_dir / "chunk_index.csv"
    chunk_npz_path = output_dir / "chunk_embeddings.npz"
    if not chunk_index_path.exists() or not chunk_npz_path.exists():
        return

    chunk_index = pd.read_csv(chunk_index_path).fillna("")
    data = np.load(chunk_npz_path, allow_pickle=False)
    ids = [str(x) for x in data["ids"]]
    vectors = {embedding_id: data["embeddings"][i] for i, embedding_id in enumerate(ids)}

    doc_rows = []
    doc_vectors = []
    for document_id, group in chunk_index.groupby("document_id", sort=False):
        embedding_ids = [eid for eid in group["embedding_id"].tolist() if eid in vectors]
        if not embedding_ids:
            continue
        matrix = np.vstack([vectors[eid] for eid in embedding_ids])
        doc_vector = l2_normalize(matrix).mean(axis=0)
        doc_vectors.append(doc_vector)
        first = group.iloc[0].to_dict()
        first["chunk_count"] = len(embedding_ids)
        first["embedding_id"] = document_id
        doc_rows.append(first)

    if not doc_rows:
        return
    doc_ids = [row["document_id"] for row in doc_rows]
    np.savez_compressed(
        output_dir / "document_embeddings.npz",
        ids=np.array(doc_ids),
        embeddings=np.array(doc_vectors, dtype=np.float32),
    )
    pd.DataFrame(doc_rows).to_csv(output_dir / "document_index.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gemini-embedding-2")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument(
        "--api-key-file",
        type=Path,
        default=None,
        help="Optional text file containing one or more Gemini API keys. Raw keys are not stored in state.",
    )
    parser.add_argument("--output-dir", type=Path, default=EMBEDDING_DIR)
    parser.add_argument("--limit", type=int, default=0, help="Limit documents for testing. 0 means all.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument(
        "--parallelism",
        type=int,
        default=0,
        help="Concurrent embedding workers. 0 means one worker per API key.",
    )
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--usage-state-file", type=Path, default=DEFAULT_USAGE_STATE)
    parser.add_argument("--rpm-per-key", type=int, default=90, help="Local guard below the observed 100 RPM limit.")
    parser.add_argument("--rpd-per-key", type=int, default=950, help="Local guard below the observed 1000 RPD limit.")
    parser.add_argument("--tpm-per-key", type=int, default=30000)
    parser.add_argument(
        "--estimated-tokens-per-job",
        type=int,
        default=900,
        help="Conservative local TPM estimate; media token accounting is server-side.",
    )
    parser.add_argument("--pdf-max-pages", type=int, default=6)
    parser.add_argument("--video-mode", choices=["auto", "direct", "frames"], default="auto")
    parser.add_argument("--max-video-seconds", type=int, default=120)
    parser.add_argument("--max-video-frames", type=int, default=6)
    args = parser.parse_args()

    ensure_dirs()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = load_metadata()
    docs = canonical_documents(raw)
    if args.limit:
        docs = docs.head(args.limit).copy()

    api_keys = load_api_keys(args.api_key_env, args.api_key_file)
    if not args.dry_run and not api_keys:
        raise SystemExit(f"Set {args.api_key_env}, GOOGLE_API_KEY, or pass --api-key-file before running embeddings.")

    jobs, skipped = build_jobs(
        docs=docs,
        pdf_max_pages=args.pdf_max_pages,
        video_mode=args.video_mode,
        max_video_seconds=args.max_video_seconds,
        max_video_frames=args.max_video_frames,
        materialize_chunks=not args.dry_run,
    )
    pd.DataFrame([asdict(job) for job in jobs]).to_csv(args.output_dir / "embedding_plan.csv", index=False)
    pd.DataFrame(skipped).to_csv(args.output_dir / "skipped_embeddings.csv", index=False)

    print(f"Documents: {len(docs)}")
    print(f"Embedding jobs: {len(jobs)}")
    print(f"Skipped before embedding: {len(skipped)}")
    if args.dry_run:
        print(f"Dry run plan: {args.output_dir / 'embedding_plan.csv'}")
        if api_keys:
            print(f"Detected {len(api_keys)} API key(s); no API calls were made.")
        return

    from google import genai
    from google.genai import types

    key_pool = GeminiKeyPool(
        keys=api_keys,
        state_path=args.usage_state_file,
        rpm_per_key=args.rpm_per_key,
        rpd_per_key=args.rpd_per_key,
        tpm_per_key=args.tpm_per_key,
        estimated_tokens_per_job=args.estimated_tokens_per_job,
    )
    pd.DataFrame(key_pool.snapshot()).to_csv(args.output_dir / "key_usage_snapshot.csv", index=False)
    clients = {}
    clients_lock = threading.Lock()
    existing_vectors, existing_index = load_existing(
        args.output_dir / "chunk_index.csv", args.output_dir / "chunk_embeddings.npz"
    )
    completed = set(existing_vectors) if args.resume else set()
    rows = existing_index.to_dict("records") if args.resume and not existing_index.empty else []
    vectors = dict(existing_vectors) if args.resume else {}
    row_by_id = {row["embedding_id"]: row for row in rows}

    failures = []
    pending = [job for job in jobs if job.embedding_id not in completed]
    parallelism = args.parallelism or len(api_keys)
    parallelism = max(1, min(parallelism, len(api_keys), len(pending) or 1))
    print(f"Pending embedding jobs: {len(pending)}")
    print(f"Parallel workers: {parallelism}")

    def process_one(job: EmbeddingJob) -> tuple[bool, EmbeddingJob, np.ndarray | None, dict[str, object] | None, str | None]:
        success = False
        last_error = None
        for attempt in range(1, args.max_retries + 1):
            key, key_id = key_pool.acquire()
            try:
                with clients_lock:
                    client = clients.get(key_id)
                    if client is None:
                        client = genai.Client(api_key=key)
                        clients[key_id] = client
                vector = np.array(embed_job(client, types, args.model, job), dtype=np.float32)
                row = asdict(job)
                row["key_id"] = key_id
                row["attempt"] = attempt
                success = True
                return True, job, vector, row, None
            except Exception as exc:
                last_error = exc
                message = repr(exc)
                if "429" in message or "RESOURCE_EXHAUSTED" in message or "rate" in message.lower():
                    time.sleep(max(args.sleep, 2.0))
                else:
                    break
            finally:
                key_pool.release(key_id)
        if not success:
            failure = {**asdict(job), "error": repr(last_error)}
            return False, job, None, failure, repr(last_error)
        raise RuntimeError("unreachable")

    completed_count = 0
    if pending:
        with ThreadPoolExecutor(max_workers=parallelism) as executor:
            future_map = {executor.submit(process_one, job): job for job in pending}
            for future in as_completed(future_map):
                completed_count += 1
                job = future_map[future]
                try:
                    ok, _job, vector, row_or_failure, error = future.result()
                except Exception as exc:
                    ok = False
                    vector = None
                    row_or_failure = {**asdict(job), "error": repr(exc)}
                    error = repr(exc)

                if ok and vector is not None and row_or_failure is not None:
                    vectors[job.embedding_id] = vector
                    row_by_id[job.embedding_id] = row_or_failure
                    print(f"[{completed_count}/{len(pending)}] embedded {job.embedding_id}")
                else:
                    failures.append(row_or_failure or {**asdict(job), "error": error})
                    print(f"[{completed_count}/{len(pending)}] failed {job.embedding_id}: {error}")

                if completed_count % args.checkpoint_every == 0:
                    rows = list(row_by_id.values())
                    save_chunk_outputs(vectors, rows, args.output_dir)
                    pd.DataFrame([*skipped, *failures]).to_csv(args.output_dir / "skipped_embeddings.csv", index=False)
                    pd.DataFrame(key_pool.snapshot()).to_csv(args.output_dir / "key_usage_snapshot.csv", index=False)

    rows = list(row_by_id.values())
    save_chunk_outputs(vectors, rows, args.output_dir)
    save_document_outputs(args.output_dir)
    pd.DataFrame([*skipped, *failures]).to_csv(args.output_dir / "skipped_embeddings.csv", index=False)
    pd.DataFrame(key_pool.snapshot()).to_csv(args.output_dir / "key_usage_snapshot.csv", index=False)

    print(f"Chunk embeddings: {args.output_dir / 'chunk_embeddings.npz'}")
    print(f"Document embeddings: {args.output_dir / 'document_embeddings.npz'}")
    if failures:
        print(f"Failures recorded: {args.output_dir / 'skipped_embeddings.csv'}")


if __name__ == "__main__":
    main()
