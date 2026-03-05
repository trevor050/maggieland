from pathlib import Path

from music_cleanup.cli import run_pipeline
from music_cleanup.config import AppConfig
from music_cleanup.models import FileInfo, FileResult


def test_copy_mode_tags_destination_not_source(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    source = input_dir / "song.mp3"
    source.write_bytes(b"fake")

    cfg = AppConfig(
        acoustid_api_key="test",
        input_dir=input_dir,
        output_dir=output_dir,
        mode="copy",
        confidence_threshold=0.85,
        workers=1,
        skip_if_tagged=False,
    )

    file_info = FileInfo(
        source_path=source,
        relative_path=Path("song.mp3"),
        file_hash="hash1",
        duration_sec=3.0,
        existing_artist=None,
        existing_title=None,
    )

    monkeypatch.setattr("music_cleanup.cli.scan_mp3_files", lambda _p: [file_info])
    monkeypatch.setattr("music_cleanup.cli.load_completed_hashes", lambda _p: set())

    def fake_classify(_file_info, _cfg):
        return FileResult(
            source_path=source,
            file_hash="hash1",
            duration_sec=3.0,
            status="matched_song",
            confidence=0.99,
            artist="Artist",
            title="Track",
        )

    monkeypatch.setattr("music_cleanup.cli.classify_file", fake_classify)

    copied_to = output_dir / "songs" / "Track - Artist.mp3"

    def fake_transfer(src, dst, mode, dry_run):
        assert src == source
        assert mode == "copy"
        assert not dry_run
        return copied_to

    monkeypatch.setattr("music_cleanup.cli.transfer_file", fake_transfer)

    tagged_paths: list[Path] = []

    def fake_write_tags(path, metadata):
        tagged_paths.append(path)
        assert metadata.artist == "Artist"

    monkeypatch.setattr("music_cleanup.cli.write_tags", fake_write_tags)

    results = run_pipeline(cfg, dry_run=False, resume=False)

    assert len(results) == 1
    assert results[0].dest_path == copied_to
    assert tagged_paths == [copied_to]
