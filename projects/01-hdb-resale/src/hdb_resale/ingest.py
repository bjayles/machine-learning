"""Ingestion: download a full, unmodified snapshot of the HDB resale dataset.

What: every HDB resale transaction registered since Jan 2017, published by HDB on
data.gov.sg as one CSV ("Resale flat prices based on registration date from Jan-2017
onwards"). This is the raw input of the whole project.

Why the full file every time: past months keep filling in (late registrations) and
may be corrected, so we never append; we re-download everything and keep each
download as a separate, DVC-versioned snapshot (project ADR-0002). Cleaning happens
in later stages, never here.

How: data.gov.sg prepares the file on request (initiate-download), we poll until it
is ready (poll-download), then download it. Output, in `out_dir` (default data/raw):
    resale.csv      the snapshot, byte-for-byte as published (tracked by DVC)
    snapshot.json   its "ID card": access date, source date, fingerprint, size (in git)
"""

import csv
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

DATASET_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
DATASET_PAGE = f"https://data.gov.sg/datasets/{DATASET_ID}/view"
API_BASE = f"https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}"

SNAPSHOT_FILE = "resale.csv"
METADATA_FILE = "snapshot.json"

# Unauthenticated quota is 5 requests/minute: poll well under it
POLL_SECONDS = 15
MAX_POLLS = 20
RATE_LIMIT_WAIT = 60
MAX_RATE_RETRIES = 3


def _call_api(client: httpx.Client, endpoint: str) -> dict:
    """GET an API endpoint, waiting out rate limits, and return its `data` field."""
    for _ in range(MAX_RATE_RETRIES + 1):
        response = client.get(f"{API_BASE}/{endpoint}")
        if response.status_code != 429:
            break
        print(f"Rate limited, waiting {RATE_LIMIT_WAIT}s...")
        time.sleep(RATE_LIMIT_WAIT)
    response.raise_for_status()

    body = response.json()
    if body.get("code") != 0:
        raise RuntimeError(f"{endpoint} failed: {body.get('errorMsg') or body}")
    return body["data"]


def _get_download_url(client: httpx.Client) -> str:
    """Ask data.gov.sg to prepare the file, then poll until its download link is ready."""
    _call_api(client, "initiate-download")

    for _ in range(MAX_POLLS):
        time.sleep(POLL_SECONDS)
        data = _call_api(client, "poll-download")
        status = data.get("status", "")
        print(f"Download status: {status}")
        if status == "DOWNLOAD_SUCCESS":
            return data["url"]
        if "FAIL" in status:
            raise RuntimeError(f"data.gov.sg could not prepare the file: {data}")

    raise TimeoutError(f"File not ready after {MAX_POLLS * POLL_SECONDS}s")


def _download(
    client: httpx.Client, url: str, dest: Path
) -> tuple[str, int, str | None]:
    """Stream the file to `dest`, returning its sha256, size and source Last-Modified date."""
    # Write to a temporary file first, so a failed download never leaves a half-written snapshot
    tmp = dest.with_name(dest.name + ".part")
    sha256 = hashlib.sha256()
    size = 0

    with client.stream("GET", url) as response:
        response.raise_for_status()
        last_modified = response.headers.get("Last-Modified")
        with tmp.open("wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
                sha256.update(chunk)
                size += len(chunk)

    os.replace(tmp, dest)

    # HTTP dates ("Mon, 12 Oct 2026 19:06:44 GMT") become ISO 8601, like our access date
    if last_modified:
        last_modified = parsedate_to_datetime(last_modified).isoformat()
    return sha256.hexdigest(), size, last_modified


def ingest(out_dir: Path) -> dict:
    """Download the full dataset into `out_dir` and record where and when it came from."""
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = out_dir / SNAPSHOT_FILE
    accessed_at = datetime.now(UTC).isoformat(timespec="seconds")

    with httpx.Client(timeout=60) as client:
        url = _get_download_url(client)
        print("Downloading...")
        sha256, size, source_last_modified = _download(client, url, snapshot_path)

    # Read back the header and row count, to spot schema changes between snapshots
    with snapshot_path.open(newline="") as f:
        reader = csv.reader(f)
        columns = next(reader)
        rows = sum(1 for _ in reader)

    metadata = {
        "dataset_id": DATASET_ID,
        "source": DATASET_PAGE,
        "accessed_at": accessed_at,
        "source_last_modified": source_last_modified,
        "file": SNAPSHOT_FILE,
        "sha256": sha256,
        "size_bytes": size,
        "rows": rows,
        "columns": columns,
    }
    (out_dir / METADATA_FILE).write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata
