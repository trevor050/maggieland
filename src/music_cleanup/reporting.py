from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import FileResult

REPORT_HEADERS = [
    "source_path",
    "file_hash",
    "duration_sec",
    "status",
    "confidence",
    "artist",
    "title",
    "album",
    "year",
    "track",
    "dest_path",
    "error_message",
]


def write_report(report_path: Path, results: list[FileResult]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_HEADERS)
        writer.writeheader()
        for item in results:
            writer.writerow(item.as_csv_row())


def write_review_csv(review_path: Path, results: list[FileResult]) -> None:
    review_items = [r for r in results if r.status in {"unresolved_non_song", "error"}]
    with review_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_HEADERS)
        writer.writeheader()
        for item in review_items:
            writer.writerow(item.as_csv_row())


def write_summary(summary_path: Path, results: list[FileResult], dry_run: bool, elapsed_sec: float) -> None:
    totals = {
        "total": len(results),
        "matched_song": 0,
        "unresolved_non_song": 0,
        "error": 0,
        "skipped": 0,
    }
    for item in results:
        totals[item.status] += 1

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "elapsed_sec": round(elapsed_sec, 2),
        "totals": totals,
    }

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
