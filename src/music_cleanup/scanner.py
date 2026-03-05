from __future__ import annotations

import hashlib
from pathlib import Path

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from .models import FileInfo


def scan_mp3_files(input_dir: Path) -> list[FileInfo]:
    files = sorted(input_dir.rglob("*.mp3"))
    out: list[FileInfo] = []
    for path in files:
        rel = path.relative_to(input_dir)
        file_hash = sha1_file(path)
        duration, artist, title = extract_existing_info(path)
        out.append(
            FileInfo(
                source_path=path,
                relative_path=rel,
                file_hash=file_hash,
                duration_sec=duration,
                existing_artist=artist,
                existing_title=title,
            )
        )
    return out


def sha1_file(path: Path) -> str:
    hasher = hashlib.sha1()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_existing_info(path: Path) -> tuple[float | None, str | None, str | None]:
    duration: float | None = None
    artist: str | None = None
    title: str | None = None

    try:
        audio = MP3(path)
        duration = float(audio.info.length)
    except Exception:
        duration = None

    try:
        tags = EasyID3(path)
        artist_vals = tags.get("artist")
        title_vals = tags.get("title")
        artist = artist_vals[0].strip() if artist_vals else None
        title = title_vals[0].strip() if title_vals else None
    except Exception:
        pass

    return duration, artist, title
