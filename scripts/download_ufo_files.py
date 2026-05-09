"""
Script to download UAP/UFO files from the Department of War's PURSUE release.

This script uses the metadata CSV published on the PURSUE website to locate
all available document/image links and download them locally.  It also
produces a simplified metadata table with useful columns for further
analysis.

Usage:
    python download_ufo_files.py [--csv-url <url>] [--output-dir <dir>] [--metadata-file <file>]

If no ``--csv-url`` is provided the script falls back to the same
CSV used by the PURSUE web page (``uap-csv.csv`` in the current
working directory).  You can download this file manually by
visiting

    https://www.war.gov/Portals/1/Interactive/2026/UFO/uap-csv.csv

in your browser and saving it locally.  The website may block
programmatic downloads, so using your browser to fetch the file is
recommended.  Once you have the CSV, place it in the same folder
as this script or specify its path with ``--csv-url`` pointing to
``file:///path/to/uap-csv.csv``.

Example:
    # Download all files into a directory called 'uap_files'
    python download_ufo_files.py --output-dir uap_files

The resulting directory will contain subdirectories for each agency
with the downloaded PDFs/images inside.  A ``metadata.csv`` (or a
custom path if ``--metadata-file`` is supplied) will also be written.

Notes:
  - Some links point to image files rather than PDFs.  The script
    downloads them as-is.
  - The server may reject automated downloads.  If you encounter
    repeated HTTP 403 responses you may need to download the files
    manually via a browser.

Author: OpenAI ChatGPT
"""

import argparse
import csv
import os
import sys
import shutil
from io import StringIO
from urllib.parse import urlparse

try:
    import pandas as pd
    import requests
except ImportError as exc:
    sys.stderr.write("Missing required packages. Install pandas and requests.\n")
    raise


def load_metadata(csv_url: str) -> pd.DataFrame:
    """Load the UAP metadata CSV from a URL or local file.

    If the URL uses the ``file://`` scheme the file will be read from
    the local filesystem.  Otherwise an HTTP GET request is performed.

    Parameters
    ----------
    csv_url : str
        URL or local path to the CSV file.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the parsed metadata.
    """
    parsed = urlparse(csv_url)
    if parsed.scheme in ("", "file"):
        # local file
        path = parsed.path if parsed.scheme == "file" else csv_url
        if not os.path.isfile(path):
            raise FileNotFoundError(f"CSV file not found: {path}")
        df = pd.read_csv(path)
    else:
        # remote file
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(csv_url, headers=headers)
        resp.raise_for_status()
        # Use csv module to handle potential BOM and embedded commas
        content = resp.text
        df = pd.read_csv(StringIO(content))
    return df


def sanitize_title(title: str) -> str:
    """Sanitize the title for use as a filename.

    Removes leading/trailing whitespace and replaces spaces with
    underscores.  Strips any characters that are problematic on
    common filesystems.
    """
    # Some titles in the CSV include stray newline/whitespace
    name = (title or "").strip()
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove characters that are invalid or problematic on most OSes
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "_")
    return name


def source_filename(url: str, fallback_title: str) -> str:
    """Return a stable filename for the source link.

    Prefer the filename embedded in the source URL/path so PDFs, images,
    and videos keep their original names. Fall back to the sanitized title
    if the URL path does not include a usable basename.
    """
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if name and "." in name:
        return name

    title = sanitize_title(fallback_title)
    ext = os.path.splitext(parsed.path)[-1]
    return f"{title}{ext}" if ext else title


def clean_text(value: object, default: str = "Unknown") -> str:
    """Normalize missing or placeholder text values."""
    text = "" if value is None else str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return default
    return text


def file_group_for_name(filename: str, fallback: str = "Unknown") -> str:
    """Classify a file into a high-level group by extension."""
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        return "PDF"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff"}:
        return "IMG"
    if ext in {".mp4", ".mov", ".m4v", ".webm", ".avi"}:
        return "VID"
    return clean_text(fallback, "Unknown")


def infer_agency(title: str, agency: str) -> str:
    """Fill obvious agency blanks from the record title."""
    cleaned = clean_text(agency, "Unknown")
    if cleaned != "Unknown":
        return cleaned

    upper = (title or "").upper()
    if upper.startswith("NASA"):
        return "NASA"
    if upper.startswith("FBI"):
        return "FBI"
    if upper.startswith("STATE_DEPARTMENT") or upper.startswith("USPER"):
        return "Department of State"
    return cleaned


def download_file(url: str, dest_path: str, session: requests.Session) -> bool:
    """Download a file from ``url`` to ``dest_path``.

    Uses a shared ``requests.Session`` with a browser-like
    User-Agent to reduce the chance of blocking.  Returns True on
    success and False on failure.
    """
    parsed = urlparse(url)
    if parsed.scheme in ("", "file"):
        source_path = parsed.path if parsed.scheme == "file" else url
        if not os.path.isfile(source_path):
            print(f"Error downloading {url}: local file not found")
            return False
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            if os.path.lexists(dest_path):
                os.remove(dest_path)
            os.symlink(os.path.abspath(source_path), dest_path)
            return True
        except Exception as exc:
            try:
                shutil.copy2(source_path, dest_path)
                return True
            except Exception as copy_exc:
                print(f"Error linking/copying {source_path} -> {dest_path}: {exc}; {copy_exc}")
                return False

    try:
        response = session.get(url, stream=True, timeout=30)
        if response.status_code != 200:
            print(f"Warning: HTTP {response.status_code} for {url}")
            return False
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as exc:
        print(f"Error downloading {url}: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download UAP release files using metadata CSV.")
    parser.add_argument(
        "--csv-url",
        default="uap-csv.csv",
        help=(
            "URL or local path to the metadata CSV.  "
            "If omitted, expects 'uap-csv.csv' to exist in the current directory."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="uap_files",
        help="Directory in which to save downloaded files (defaults to 'uap_files').",
    )
    parser.add_argument(
        "--metadata-file",
        default="metadata.csv",
        help="Path to write simplified metadata CSV (defaults to 'metadata.csv').",
    )
    args = parser.parse_args()

    # Load the metadata
    try:
        df = load_metadata(args.csv_url)
    except Exception as e:
        print(f"Failed to load metadata CSV: {e}")
        sys.exit(1)

    # Trim and select relevant columns
    df = df[
        [
            "Title",
            "Agency",
            "Release Date",
            "Incident Date",
            "Incident Location",
            "PDF | Image Link",
            "Type",
        ]
    ].copy()
    df["Title"] = df["Title"].astype(str).str.strip()
    df["Agency"] = df.apply(lambda row: infer_agency(row["Title"], row["Agency"]), axis=1)
    df["Type"] = df["Type"].apply(lambda value: clean_text(value, "Unknown"))
    df["Document Link"] = df["PDF | Image Link"].astype(str).str.strip()
    df["Source Filename"] = df["Document Link"].apply(lambda link: source_filename(link, "") if isinstance(link, str) else "")
    df["File Group"] = df.apply(
        lambda row: file_group_for_name(row["Source Filename"], row["Type"]),
        axis=1,
    )
    df["Output Path"] = ""

    # Set up a requests session
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
    )

    # Iterate through records and download documents
    failed_downloads = []
    for idx, row in df.iterrows():
        link = row["Document Link"]
        if not isinstance(link, str) or not link.startswith(("http", "file")):
            print(f"Skipping row {idx+1}: no valid document URL")
            continue

        agency = infer_agency(row["Title"], row["Agency"])
        title = sanitize_title(row["Title"])
        filename = source_filename(link, title)
        file_group = file_group_for_name(filename, row["Type"])
        # Build destination path (agency/group/<source filename>)
        dest_dir = os.path.join(args.output_dir, agency, file_group)
        dest_path = os.path.join(dest_dir, filename)
        df.at[idx, "Output Path"] = dest_path
        if os.path.exists(dest_path):
            print(f"Already exists: {dest_path}; skipping")
            continue
        print(f"Downloading {filename} to {dest_path}")
        ok = download_file(link, dest_path, session)
        if not ok:
            failed_downloads.append((idx, link))

    # Save metadata to CSV with resolved output paths
    try:
        df.to_csv(args.metadata_file, index=False)
        print(f"Wrote simplified metadata to {args.metadata_file} ({len(df)} records)")
    except Exception as exc:
        print(f"Failed to write metadata CSV: {exc}")

    if failed_downloads:
        print("\nFinished with some errors. The following downloads failed:")
        for idx, url in failed_downloads:
            print(f"  Row {idx+1}: {url}")
    else:
        print("\nAll downloads completed successfully.")


if __name__ == "__main__":
    main()
