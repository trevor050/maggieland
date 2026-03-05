from pathlib import Path

import pytest

from music_cleanup.config import load_config


def _write_config(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_skip_if_tagged_parses_string_false(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    config = _write_config(
        tmp_path / "cleanup.config.yml",
        f"""
acoustid_api_key: "test-key"
input_dir: "{input_dir.as_posix()}"
output_dir: "{output_dir.as_posix()}"
skip_if_tagged: "false"
""".strip(),
    )

    cfg = load_config(config)
    assert cfg.skip_if_tagged is False


def test_invalid_yaml_gives_windows_path_hint(tmp_path: Path):
    config = _write_config(
        tmp_path / "cleanup.config.yml",
        'acoustid_api_key: "abc"\ninput_dir: "C:\\bad\\path\\\n',
    )

    with pytest.raises(ValueError, match="forward slashes in Windows paths"):
        load_config(config)
