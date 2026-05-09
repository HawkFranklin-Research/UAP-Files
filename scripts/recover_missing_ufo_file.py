"""Recover missing PURSUE release files through Scrapling's browser context.

The war.gov media endpoints reject plain HTTP clients from this environment,
but an in-page browser fetch from the live PURSUE page returns the raw bytes.
This script targets the missing Serial_153 PDF and updates the canonical
metadata after writing it into ufo_release.
"""

from __future__ import annotations

import base64
import csv
from pathlib import Path

from scrapling.fetchers import StealthyFetcher


ROOT = Path(__file__).resolve().parent
METADATA_PATH = ROOT / "ufo_release_metadata.csv"
OUTPUT_PATH = ROOT / "ufo_release" / "FBI" / "PDF" / "65_HS1-834228961_62-HQ-83894_Serial_153.pdf"
SOURCE_URL = "https://www.war.gov/medialink/ufo/release_1/65_hs1-834228961_62-hq-83894_serial_153.pdf"
PAGE_URL = "https://www.war.gov/ufo/#65_HS1-834228961_62-HQ-83894_Serial_153"
TITLE = "65_HS1-834228961_62-HQ-83894_Serial_153"


def fetch_pdf_bytes(url: str) -> bytes:
    """Fetch PDF bytes from inside the loaded war.gov page session."""
    result: dict[str, object] = {}

    def page_action(page) -> None:
        nonlocal result
        result = page.evaluate(
            """
            async (url) => {
              const response = await fetch(url, { credentials: 'include' });
              const buffer = await response.arrayBuffer();
              const bytes = new Uint8Array(buffer);
              let binary = "";
              const chunkSize = 0x8000;
              for (let i = 0; i < bytes.length; i += chunkSize) {
                binary += String.fromCharCode(...bytes.slice(i, i + chunkSize));
              }
              return {
                status: response.status,
                contentType: response.headers.get("content-type") || "",
                bodyBase64: btoa(binary),
                byteLength: buffer.byteLength
              };
            }
            """,
            url,
        )

    StealthyFetcher.fetch(
        PAGE_URL,
        headless=True,
        network_idle=True,
        solve_cloudflare=True,
        real_chrome=True,
        timeout=120000,
        page_action=page_action,
    )

    status = int(result.get("status", 0))
    content_type = str(result.get("contentType", ""))
    if status != 200:
        raise RuntimeError(f"Expected HTTP 200 for {url}, got {status}")
    if "pdf" not in content_type.lower():
        raise RuntimeError(f"Expected PDF content for {url}, got {content_type!r}")

    data = base64.b64decode(str(result["bodyBase64"]))
    if not data.startswith(b"%PDF-"):
        raise RuntimeError(f"Fetched content does not look like a PDF: {data[:16]!r}")
    return data


def update_metadata() -> None:
    rows: list[dict[str, str]]
    with METADATA_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    rel_output = OUTPUT_PATH.relative_to(ROOT).as_posix()
    updated = False
    for row in rows:
        if row.get("Title") == TITLE:
            row["PDF | Image Link"] = SOURCE_URL
            row["Document Link"] = SOURCE_URL
            row["Source Filename"] = OUTPUT_PATH.name
            row["File Group"] = "PDF"
            row["Output Path"] = rel_output
            updated = True
            break

    if not updated:
        raise RuntimeError(f"Metadata row not found for {TITLE}")

    with METADATA_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = fetch_pdf_bytes(SOURCE_URL)
    OUTPUT_PATH.write_bytes(pdf_bytes)
    update_metadata()
    print(f"Recovered {OUTPUT_PATH.relative_to(ROOT)} ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    main()
