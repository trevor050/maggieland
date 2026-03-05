from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["matched_song", "unresolved_non_song", "error", "skipped"]


@dataclass(slots=True)
class FileInfo:
    source_path: Path
    relative_path: Path
    file_hash: str
    duration_sec: float | None
    existing_artist: str | None
    existing_title: str | None


@dataclass(slots=True)
class MatchMetadata:
    confidence: float
    artist: str | None
    title: str | None
    album: str | None = None
    year: str | None = None
    track: str | None = None


@dataclass(slots=True)
class FileResult:
    source_path: Path
    file_hash: str
    duration_sec: float | None
    status: Status
    confidence: float | None = None
    artist: str | None = None
    title: str | None = None
    album: str | None = None
    year: str | None = None
    track: str | None = None
    dest_path: Path | None = None
    error_message: str | None = None

    def as_csv_row(self) -> dict[str, str]:
        return {
            "source_path": str(self.source_path),
            "file_hash": self.file_hash,
            "duration_sec": "" if self.duration_sec is None else f"{self.duration_sec:.2f}",
            "status": self.status,
            "confidence": "" if self.confidence is None else f"{self.confidence:.4f}",
            "artist": self.artist or "",
            "title": self.title or "",
            "album": self.album or "",
            "year": self.year or "",
            "track": self.track or "",
            "dest_path": "" if self.dest_path is None else str(self.dest_path),
            "error_message": self.error_message or "",
        }
