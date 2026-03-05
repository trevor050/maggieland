from pathlib import Path

import pytest

from music_cleanup.cli import resolve_fpcalc_path


def test_resolve_fpcalc_prefers_config_path(tmp_path: Path, monkeypatch):
    fpcalc = tmp_path / "fpcalc.exe"
    fpcalc.write_text("stub", encoding="utf-8")

    monkeypatch.delenv("FPCALC", raising=False)
    monkeypatch.setattr("music_cleanup.cli.shutil.which", lambda _name: None)

    resolved = resolve_fpcalc_path(str(fpcalc))
    assert resolved == str(fpcalc)


def test_resolve_fpcalc_finds_binary_next_to_launcher(tmp_path: Path, monkeypatch):
    launcher = tmp_path / "run_music_cleanup.bat"
    launcher.write_text("@echo off", encoding="utf-8")
    fpcalc = tmp_path / "fpcalc.exe"
    fpcalc.write_text("stub", encoding="utf-8")

    monkeypatch.setattr("music_cleanup.cli.sys.argv", [str(launcher)])
    monkeypatch.delenv("FPCALC", raising=False)
    monkeypatch.setattr("music_cleanup.cli.shutil.which", lambda _name: None)

    resolved = resolve_fpcalc_path(None)
    assert resolved == str(fpcalc)


def test_resolve_fpcalc_raises_when_missing(monkeypatch, tmp_path: Path):
    launcher = tmp_path / "run_music_cleanup.bat"
    launcher.write_text("@echo off", encoding="utf-8")

    monkeypatch.setattr("music_cleanup.cli.sys.argv", [str(launcher)])
    monkeypatch.delenv("FPCALC", raising=False)
    monkeypatch.setattr("music_cleanup.cli.shutil.which", lambda _name: None)

    with pytest.raises(RuntimeError, match="fpcalc not found"):
        resolve_fpcalc_path(None)
