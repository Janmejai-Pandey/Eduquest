#!/usr/bin/env python3
"""
retry_failed_downloads.py
Reads download_results.json → finds all failed downloads →
retries them with longer timeouts, retries & exponential backoff.

Run: python retry_failed_downloads.py
"""

import os
import re
import io
import time
import json
import logging
import random
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import gdown
from tqdm import tqdm

# ═══════════════════════════════════════════════════════════════════════════════
#                              CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG = {
    "RESULTS_FILE"    : "jiit_downloads/download_results.json",
    "OUTPUT_DIR"      : "/jiit_downloads",

    # Retry-specific settings — much more resilient than the main scraper
    "MAX_RETRIES"     : 5,          # per file, tries this many times
    "TIMEOUT"         : 120,        # 2 minutes per request (was 30)
    "MAX_WORKERS"     : 2,          # LOW concurrency to avoid rate-limiting
    "CHUNK_SIZE"      : 8192,
    "RETRY_DELAY_MIN" : 3,          # min seconds between retries
    "RETRY_DELAY_MAX" : 8,          # max seconds (random jitter)
    "BACKOFF_FACTOR"  : 2,          # exponential: 3s, 6s, 12s, 24s, 48s
}

# ═══════════════════════════════════════════════════════════════════════════════
#                              LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler("retry_downloads.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("Retry")

# ═══════════════════════════════════════════════════════════════════════════════
#                              DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RetryResult:
    file_id      : str
    filename     : str  = ""
    filepath     : str  = ""
    size_bytes   : int  = 0
    success      : bool = False
    skipped      : bool = False
    error        : str  = ""
    subject      : str  = ""
    category     : str  = ""
    attempts     : int  = 0
    method_used  : str  = ""     # "gdown" or "http" or "skipped"

    def to_dict(self):
        d = asdict(self)
        d["size_mb"] = round(self.size_bytes / 1024 / 1024, 2)
        return d


# ═══════════════════════════════════════════════════════════════════════════════
#                        RETRY DOWNLOADER
# ═══════════════════════════════════════════════════════════════════════════════

class RetryDownloader:
    def __init__(self):
        self.out_dir = Path(CONFIG["OUTPUT_DIR"])
        self.results: List[RetryResult] = []

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

        # Configure aggressive retry adapter for the session
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ── Folder helpers ────────────────────────────────────────────────────────

    def _dest_dir(self, subject: str, category: str) -> Path:
        clean_sub = re.sub(r'[<>:"/\\|?*]', "_", subject or "Uncategorized").strip()
        clean_cat = re.sub(r'[<>:"/\\|?*]', "_", category or "General").strip()
        d = self.out_dir / clean_sub / clean_cat
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _check_already_downloaded(self, entry: dict) -> Optional[RetryResult]:
        """
        Before retrying, check if the file was actually downloaded already
        (maybe by a previous retry run).
        """
        subject  = entry.get("subject", "")
        category = entry.get("category", "")
        file_id  = entry.get("file_id", "")
        dest_dir = self._dest_dir(subject, category)

        # Look for any real file matching this ID
        for f in dest_dir.iterdir():
            if not f.is_file():
                continue
            if f.name.endswith(".bin"):
                continue  # placeholder — treat as not-downloaded
            # Real file with content?
            if f.stat().st_size > 0:
                # Try to correlate: does its name look consistent?
                # Since we can't be 100% sure without file_id in name,
                # check if there's ANY complete PDF/DOCX/etc. in this folder
                # that wasn't in the original list.
                # Safer: skip only if there's a file whose name contains file_id
                if file_id in f.name:
                    return RetryResult(
                        file_id  = file_id,
                        filename = f.name,
                        filepath = str(f),
                        size_bytes = f.stat().st_size,
                        skipped  = True,
                        subject  = subject,
                        category = category,
                        method_used = "already_exists",
                    )
        return None

    # ── HTTP confirm token bypass ─────────────────────────────────────────────

    @staticmethod
    def _confirm_token(r: requests.Response) -> Optional[str]:
        for k, v in r.cookies.items():
            if k.startswith("download_warning"):
                return v
        for pat in [r'confirm=([0-9A-Za-z_\-]+)', r'"confirm"\s*:\s*"([^"]+)"']:
            m = re.search(pat, r.text)
            if m:
                return m.group(1)
        return None

    # ── Filename from response headers ────────────────────────────────────────

    @staticmethod
    def _filename_from_response(r: requests.Response, fallback: str) -> str:
        cd = r.headers.get("Content-Disposition", "")
        m  = re.findall(r'filename[^;=\n]*=(["\']?)([^\n"\']+)\1', cd)
        return m[0][1].strip() if m else fallback

    # ── Stream to disk with progress bar ──────────────────────────────────────

    def _stream_to_disk(self, r, filepath: Path, label: str) -> int:
        total = int(r.headers.get("Content-Length", 0))
        written = 0
        try:
            with open(filepath, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True,
                unit_divisor=1024, desc=f"↓ {label[:35]}",
                leave=False, position=1,
            ) as bar:
                for chunk in r.iter_content(CONFIG["CHUNK_SIZE"]):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
                        written += len(chunk)
        except Exception as e:
            # Clean up partial file
            if filepath.exists() and filepath.stat().st_size == 0:
                filepath.unlink()
            raise e
        return written

    # ── Try gdown ─────────────────────────────────────────────────────────────

    def _try_gdown(self, entry: dict) -> RetryResult:
        result = RetryResult(
            file_id  = entry["file_id"],
            subject  = entry.get("subject", ""),
            category = entry.get("category", ""),
            method_used = "gdown",
        )
        dest_dir = self._dest_dir(result.subject, result.category)
        try:
            path = gdown.download(
                f"https://drive.google.com/uc?id={result.file_id}",
                output=str(dest_dir) + "/",
                quiet=True,
                fuzzy=True,
                resume=True,
            )
            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                result.success    = True
                result.filepath   = path
                result.filename   = os.path.basename(path)
                result.size_bytes = os.path.getsize(path)
            else:
                result.error = "gdown returned no file / empty file"
        except Exception as e:
            result.error = f"gdown: {str(e)[:150]}"
        return result

    # ── Try direct HTTP ───────────────────────────────────────────────────────

    def _try_http(self, entry: dict) -> RetryResult:
        result = RetryResult(
            file_id  = entry["file_id"],
            subject  = entry.get("subject", ""),
            category = entry.get("category", ""),
            method_used = "http",
        )
        dest_dir = self._dest_dir(result.subject, result.category)
        url = f"https://drive.google.com/uc?export=download&id={result.file_id}"

        try:
            # First request — may need confirm token
            r = self.session.get(
                url, stream=True,
                timeout=(30, CONFIG["TIMEOUT"]),  # (connect, read) timeouts
            )
            token = self._confirm_token(r)
            if token:
                r = self.session.get(
                    f"{url}&confirm={token}",
                    stream=True,
                    timeout=(30, CONFIG["TIMEOUT"]),
                )

            # Determine filename
            filename = self._filename_from_response(r, f"{result.file_id}.bin")
            filepath = dest_dir / filename

            # If .bin fallback filename, use file_id in name
            if filename.endswith(".bin"):
                filepath = dest_dir / f"{result.file_id}.bin"

            written = self._stream_to_disk(r, filepath, filename)

            if written > 0:
                result.success    = True
                result.filename   = filename
                result.filepath   = str(filepath)
                result.size_bytes = written
            else:
                result.error = "HTTP: downloaded 0 bytes"

        except requests.exceptions.Timeout:
            result.error = "HTTP: timeout"
        except requests.exceptions.ConnectionError as e:
            result.error = f"HTTP: connection - {str(e)[:100]}"
        except requests.exceptions.SSLError as e:
            result.error = f"HTTP: SSL - {str(e)[:100]}"
        except Exception as e:
            result.error = f"HTTP: {str(e)[:150]}"

        return result

    # ── One file with all retry logic ────────────────────────────────────────

    def download_with_retries(self, entry: dict) -> RetryResult:
        """
        Try to download one file with:
        - Skip if already exists
        - Multiple attempts (MAX_RETRIES)
        - Exponential backoff between attempts
        - Alternating gdown ↔ HTTP methods
        """
        file_id  = entry["file_id"]
        subject  = entry.get("subject", "Unknown")
        category = entry.get("category", "General")

        log.info(f"▶ [{subject}/{category}] {file_id}")

        # ── Check if already downloaded ──
        already = self._check_already_downloaded(entry)
        if already:
            log.info(f"  ⊘ Already exists — skipping")
            return already

        # ── Retry loop with exponential backoff ──
        final_result = None
        for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
            log.info(f"  ▷ Attempt {attempt}/{CONFIG['MAX_RETRIES']}")

            # Alternate methods: odd attempts = gdown, even = http
            # (except attempt 1 which uses HTTP since that's what usually failed)
            if attempt % 2 == 1:
                result = self._try_http(entry)
                if not result.success:
                    log.warning(f"    ✗ HTTP failed: {result.error[:80]}")
                    log.info(f"    ↻ Fallback to gdown ...")
                    result = self._try_gdown(entry)
            else:
                result = self._try_gdown(entry)
                if not result.success:
                    log.warning(f"    ✗ gdown failed: {result.error[:80]}")
                    log.info(f"    ↻ Fallback to HTTP ...")
                    result = self._try_http(entry)

            result.attempts = attempt

            if result.success:
                log.info(
                    f"  ✓ SUCCESS via {result.method_used} — "
                    f"{result.filename} ({result.size_bytes / 1024 / 1024:.2f} MB)"
                )
                return result

            final_result = result
            log.warning(f"    ✗ Attempt {attempt} failed: {result.error[:80]}")

            # Backoff before next attempt
            if attempt < CONFIG["MAX_RETRIES"]:
                delay = min(
                    CONFIG["RETRY_DELAY_MIN"] * (CONFIG["BACKOFF_FACTOR"] ** (attempt - 1)),
                    60,   # cap at 60s
                )
                jitter = random.uniform(0, CONFIG["RETRY_DELAY_MAX"])
                wait = delay + jitter
                log.info(f"    ⏳ Waiting {wait:.1f}s before retry ...")
                time.sleep(wait)

        log.error(f"  ✗ ALL {CONFIG['MAX_RETRIES']} ATTEMPTS FAILED")
        return final_result

    # ── Batch: retry all failed files ─────────────────────────────────────────

    def retry_all(self, failed_entries: List[dict]) -> List[RetryResult]:
        if not failed_entries:
            log.warning("No failed entries to retry")
            return []

        log.info(f"\nRetrying {len(failed_entries)} failed download(s)")
        log.info(f"Workers: {CONFIG['MAX_WORKERS']} | "
                 f"Retries: {CONFIG['MAX_RETRIES']} | "
                 f"Timeout: {CONFIG['TIMEOUT']}s")

        all_results = []
        with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as pool:
            futures = {
                pool.submit(self.download_with_retries, entry): entry
                for entry in failed_entries
            }
            with tqdm(
                total=len(failed_entries),
                desc="Retry Progress",
                unit="file",
                position=0,
            ) as bar:
                for fut in as_completed(futures):
                    try:
                        result = fut.result()
                        all_results.append(result)
                    except Exception as e:
                        entry = futures[fut]
                        log.error(f"Unexpected error: {e}")
                        all_results.append(RetryResult(
                            file_id  = entry["file_id"],
                            subject  = entry.get("subject", ""),
                            category = entry.get("category", ""),
                            error    = f"Unexpected: {str(e)[:100]}",
                        ))
                    finally:
                        bar.update(1)

        self.results = all_results
        return all_results

    # ── Summary ───────────────────────────────────────────────────────────────

    def print_summary(self):
        ok   = [r for r in self.results if r.success]
        skip = [r for r in self.results if r.skipped]
        fail = [r for r in self.results if not r.success and not r.skipped]
        size_mb = sum(r.size_bytes for r in ok) / 1024 / 1024

        # Group failures by subject
        fails_by_subject = {}
        for r in fail:
            key = f"{r.subject} / {r.category}"
            fails_by_subject.setdefault(key, []).append(r)

        print("\n" + "═" * 75)
        print("  RETRY DOWNLOAD SUMMARY")
        print("═" * 75)
        print(f"  Total attempted     : {len(self.results)}")
        print(f"  ✓ Now succeeded     : {len(ok)}")
        print(f"  ⊘ Already existed   : {len(skip)}")
        print(f"  ✗ Still failed      : {len(fail)}")
        print(f"  Downloaded size     : {size_mb:.2f} MB")
        print(f"  Output folder       : {self.out_dir.resolve()}")

        if ok:
            print("\n  ✓ Successfully retried:")
            for r in ok:
                print(f"    ✓ [{r.subject}/{r.category}] "
                      f"{r.filename} ({r.size_bytes / 1024 / 1024:.2f} MB) "
                      f"via {r.method_used} after {r.attempts} attempt(s)")

        if fail:
            print("\n  ✗ Still failing (network/permanent issues):")
            for key, files in fails_by_subject.items():
                print(f"    📁 {key}")
                for r in files:
                    print(f"        ✗ {r.file_id}: {r.error[:80]}")

        print("═" * 75 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
#                              JSON MERGE HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def merge_results_back(
    original_file: str,
    retry_results: List[RetryResult],
) -> None:
    """
    Update the original download_results.json:
    - Replace failed entries that now succeeded with the new successful data
    - Keep entries that are still failing (mark them as retried)
    """
    try:
        with open(original_file, "r", encoding="utf-8") as f:
            original = json.load(f)
    except Exception as e:
        log.error(f"Could not read original file: {e}")
        return

    # Build lookup of retry results by file_id
    retry_lookup = {r.file_id: r for r in retry_results}

    updated = []
    for entry in original:
        fid = entry.get("file_id", "")
        if fid in retry_lookup:
            retry = retry_lookup[fid]
            if retry.success or retry.skipped:
                # Replace with new successful data
                updated.append({
                    "file_id"    : retry.file_id,
                    "filename"   : retry.filename,
                    "filepath"   : retry.filepath,
                    "size_bytes" : retry.size_bytes,
                    "success"    : retry.success,
                    "skipped"    : retry.skipped,
                    "error"      : "",
                    "subject"    : retry.subject,
                    "category"   : retry.category,
                    "size_mb"    : round(retry.size_bytes / 1024 / 1024, 2),
                })
            else:
                # Still failing — keep original but update error
                entry["error"] = retry.error
                updated.append(entry)
        else:
            # Not retried — keep original
            updated.append(entry)

    # Save updated version
    backup_path = original_file + ".backup"
    try:
        # Backup the original first
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(original, f, indent=2, ensure_ascii=False)
        log.info(f"Original backed up → {backup_path}")

        # Write updated
        with open(original_file, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2, ensure_ascii=False)
        log.info(f"Updated results saved → {original_file}")
    except Exception as e:
        log.error(f"Could not save updated file: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#                              MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def load_failed_downloads(filepath: str) -> List[dict]:
    """Read download_results.json and extract only failed entries."""
    p = Path(filepath)
    if not p.exists():
        log.error(f"File not found: {filepath}")
        return []

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.error(f"Could not parse JSON: {e}")
        return []

    if not isinstance(data, list):
        log.error("JSON is not a list")
        return []

    failed = [
        entry for entry in data
        if not entry.get("success", False) and not entry.get("skipped", False)
    ]

    log.info(f"Loaded {len(data)} total entries")
    log.info(f"Found {len(failed)} failed download(s) to retry")
    return failed


def save_retry_results(results: List[RetryResult]):
    """Save the retry results to a separate JSON file for tracking."""
    out_path = Path(CONFIG["OUTPUT_DIR"]) / "retry_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, indent=2, ensure_ascii=False)
        log.info(f"Retry results saved → {out_path}")
    except Exception as e:
        log.error(f"Could not save retry results: {e}")


def run():
    print("═" * 75)
    print("  RETRY FAILED DOWNLOADS")
    print("  (reads download_results.json → retries failed files)")
    print("═" * 75)
    print(f"  Input file      : {CONFIG['RESULTS_FILE']}")
    print(f"  Output folder   : {CONFIG['OUTPUT_DIR']}")
    print(f"  Max retries     : {CONFIG['MAX_RETRIES']} per file")
    print(f"  Timeout         : {CONFIG['TIMEOUT']}s per request")
    print(f"  Workers         : {CONFIG['MAX_WORKERS']} (low to avoid rate limits)")
    print("═" * 75 + "\n")

    # ── Load failed entries ──
    failed = load_failed_downloads(CONFIG["RESULTS_FILE"])
    if not failed:
        print("  🎉 No failed downloads to retry!")
        return

    print(f"\n  Failed downloads to retry:")
    by_subject = {}
    for entry in failed:
        key = f"{entry.get('subject', '?')} / {entry.get('category', '?')}"
        by_subject.setdefault(key, 0)
        by_subject[key] += 1

    for k, v in sorted(by_subject.items()):
        print(f"    📁 {k}: {v} file(s)")

    print(f"\n  Starting retry ...\n")

    # ── Run retry ──
    downloader = RetryDownloader()
    results = downloader.retry_all(failed)

    # ── Save results ──
    save_retry_results(results)

    # ── Update original results file ──
    print("\n  Updating original download_results.json ...")
    merge_results_back(CONFIG["RESULTS_FILE"], results)

    # ── Print summary ──
    downloader.print_summary()

    # ── Actionable next steps ──
    still_failing = [r for r in results if not r.success and not r.skipped]
    if still_failing:
        print("  💡 To retry the remaining failures, just run this script again.")
        print("     Files that succeeded won't be re-downloaded.\n")


if __name__ == "__main__":
    run()