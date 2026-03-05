from __future__ import annotations

from .models import FileInfo, MatchMetadata


def should_skip_existing(file_info: FileInfo, skip_if_tagged: bool) -> bool:
    if not skip_if_tagged:
        return False
    return bool(file_info.existing_artist and file_info.existing_title)


def is_confident_match(match: MatchMetadata | None, threshold: float) -> bool:
    if not match:
        return False
    if not match.artist or not match.title:
        return False
    return match.confidence >= threshold
