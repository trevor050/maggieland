from pathlib import Path

from music_cleanup.models import FileResult
from music_cleanup.reporting import write_report, write_review_csv


def test_reporting_outputs(tmp_path: Path):
    report = tmp_path / "report.csv"
    review = tmp_path / "review.csv"
    rows = [
        FileResult(source_path=Path("a.mp3"), file_hash="1", duration_sec=1.0, status="matched_song"),
        FileResult(source_path=Path("b.mp3"), file_hash="2", duration_sec=2.0, status="error", error_message="oops"),
    ]
    write_report(report, rows)
    write_review_csv(review, rows)

    report_text = report.read_text(encoding="utf-8")
    review_text = review.read_text(encoding="utf-8")
    assert "matched_song" in report_text
    assert "error" in report_text
    assert "matched_song" not in review_text
    assert "error" in review_text
