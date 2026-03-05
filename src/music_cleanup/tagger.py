from __future__ import annotations

from pathlib import Path

from mutagen.easyid3 import EasyID3

from .models import MatchMetadata

INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def write_tags(path: Path, metadata: MatchMetadata) -> None:
    try:
        tags = EasyID3(path)
    except Exception:
        tags = EasyID3()

    if metadata.artist:
        tags["artist"] = [metadata.artist]
    if metadata.title:
        tags["title"] = [metadata.title]
    if metadata.album:
        tags["album"] = [metadata.album]
    if metadata.year:
        tags["date"] = [metadata.year]
    if metadata.track:
        tags["tracknumber"] = [metadata.track]

    tags.save(path)


def build_song_filename(title: str, artist: str) -> str:
    safe_title = sanitize_component(title)
    safe_artist = sanitize_component(artist)
    return f"{safe_title} - {safe_artist}.mp3"


def sanitize_component(value: str) -> str:
    out = []
    for ch in value.strip():
        if ch in INVALID_FILENAME_CHARS or ord(ch) < 32:
            out.append("_")
        else:
            out.append(ch)
    normalized = "".join(out).strip().rstrip(".")
    return normalized or "unknown"
