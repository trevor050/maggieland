from pathlib import Path

import pytest

from music_cleanup.cli import ensure_input_dir, ensure_valid_api_key, run_pipeline
from music_cleanup.config import AppConfig
from music_cleanup.metadata import FingerprintError
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


def test_move_mode_keeps_error_source_file_by_copying(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    source = input_dir / "broken.mp3"
    source.write_bytes(b"fake")

    cfg = AppConfig(
        acoustid_api_key="test",
        input_dir=input_dir,
        output_dir=output_dir,
        mode="move",
        confidence_threshold=0.85,
        workers=1,
        skip_if_tagged=False,
    )

    file_info = FileInfo(
        source_path=source,
        relative_path=Path("broken.mp3"),
        file_hash="hash2",
        duration_sec=3.0,
        existing_artist=None,
        existing_title=None,
    )

    monkeypatch.setattr("music_cleanup.cli.scan_mp3_files", lambda _p: [file_info])
    monkeypatch.setattr("music_cleanup.cli.load_completed_hashes", lambda _p: set())
    monkeypatch.setattr(
        "music_cleanup.cli.classify_file",
        lambda _file_info, _cfg: FileResult(
            source_path=source,
            file_hash="hash2",
            duration_sec=3.0,
            status="error",
            error_message="Fingerprint error: test",
        ),
    )

    transfer_calls: list[str] = []

    def fake_transfer(src, dst, mode, dry_run):
        assert src == source
        assert not dry_run
        transfer_calls.append(mode)
        return dst

    monkeypatch.setattr("music_cleanup.cli.transfer_file", fake_transfer)

    results = run_pipeline(cfg, dry_run=False, resume=False)

    assert len(results) == 1
    assert transfer_calls == ["copy"]


def test_ensure_valid_api_key_prompts_and_persists_when_missing(tmp_path: Path, monkeypatch):
    cfg = AppConfig(
        acoustid_api_key="",
        input_dir=tmp_path,
        output_dir=tmp_path / "out",
    )
    config_path = tmp_path / "cleanup.config.yml"
    config_path.write_text("acoustid_api_key: \"\"\n", encoding="utf-8")

    prompts = iter(["GOODKEY"])
    monkeypatch.setattr("music_cleanup.cli._prompt_text", lambda _msg: next(prompts))
    monkeypatch.setattr("music_cleanup.cli.validate_acoustid_api_key", lambda _key: None)
    persisted: list[dict[str, object]] = []
    monkeypatch.setattr("music_cleanup.cli.persist_config_values", lambda _p, d: persisted.append(d))

    assert ensure_valid_api_key(cfg, config_path)
    assert cfg.acoustid_api_key == "GOODKEY"
    assert persisted == [{"acoustid_api_key": "GOODKEY"}]


def test_ensure_valid_api_key_retries_on_invalid(tmp_path: Path, monkeypatch):
    cfg = AppConfig(
        acoustid_api_key="BAD",
        input_dir=tmp_path,
        output_dir=tmp_path / "out",
    )
    config_path = tmp_path / "cleanup.config.yml"
    config_path.write_text("acoustid_api_key: \"BAD\"\n", encoding="utf-8")

    prompts = iter(["GOOD"])
    monkeypatch.setattr("music_cleanup.cli._prompt_text", lambda _msg: next(prompts))

    seen: list[str] = []

    def fake_validate(key: str):
        seen.append(key)
        if key == "BAD":
            raise FingerprintError("AcoustID API key is invalid.")

    monkeypatch.setattr("music_cleanup.cli.validate_acoustid_api_key", fake_validate)
    monkeypatch.setattr("music_cleanup.cli.persist_config_values", lambda _p, _d: None)

    assert ensure_valid_api_key(cfg, config_path)
    assert seen == ["BAD", "GOOD"]


def test_ensure_input_dir_prompts_for_recovery(tmp_path: Path, monkeypatch):
    missing = tmp_path / "missing"
    recovered = tmp_path / "real"
    recovered.mkdir()
    config_path = tmp_path / "cleanup.config.yml"
    config_path.write_text("input_dir: \"x\"\n", encoding="utf-8")

    prompts = iter([str(recovered)])
    monkeypatch.setattr("music_cleanup.cli._prompt_text", lambda _msg: next(prompts))
    persisted: list[dict[str, object]] = []
    monkeypatch.setattr("music_cleanup.cli.persist_config_values", lambda _p, d: persisted.append(d))

    final_dir = ensure_input_dir(missing, config_path)
    assert final_dir == recovered
    assert persisted == [{"input_dir": str(recovered)}]
