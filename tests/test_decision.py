from pathlib import Path

from music_cleanup.decision import is_confident_match, should_skip_existing
from music_cleanup.models import FileInfo, MatchMetadata


def test_should_skip_existing_true_when_both_present():
    item = FileInfo(
        source_path=Path("x.mp3"),
        relative_path=Path("x.mp3"),
        file_hash="h",
        duration_sec=12.0,
        existing_artist="A",
        existing_title="T",
    )
    assert should_skip_existing(item, skip_if_tagged=True)


def test_should_skip_existing_false_without_flag():
    item = FileInfo(
        source_path=Path("x.mp3"),
        relative_path=Path("x.mp3"),
        file_hash="h",
        duration_sec=12.0,
        existing_artist="A",
        existing_title="T",
    )
    assert not should_skip_existing(item, skip_if_tagged=False)


def test_is_confident_match_requires_metadata():
    assert not is_confident_match(None, 0.85)
    match = MatchMetadata(confidence=0.9, artist=None, title="Song")
    assert not is_confident_match(match, 0.85)


def test_is_confident_match_threshold():
    match = MatchMetadata(confidence=0.9, artist="Artist", title="Song")
    assert is_confident_match(match, 0.85)
