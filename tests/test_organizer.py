from pathlib import Path

from music_cleanup.organizer import unique_destination


def test_unique_destination_suffixes(tmp_path: Path):
    base = tmp_path / "track.mp3"
    base.write_text("a", encoding="utf-8")
    second = unique_destination(base)
    assert second.name == "track (1).mp3"

    second.write_text("b", encoding="utf-8")
    third = unique_destination(base)
    assert third.name == "track (2).mp3"
