from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class AppConfig:
    acoustid_api_key: str
    input_dir: Path
    output_dir: Path
    mode: str = "copy"
    confidence_threshold: float = 0.85
    workers: int = 4
    skip_if_tagged: bool = False
    songs_dir: str = "songs"
    nonsongs_dir: str = "non-songs"
    fpcalc_path: str | None = None
    acoustid_requests_per_second: float = 3.0
    musicbrainz_requests_per_second: float = 1.0


def load_config(path: Path) -> AppConfig:
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML in {path}. "
            "Tip: use forward slashes in Windows paths (C:/...) or escape backslashes (C:\\\\...)."
        ) from exc

    cfg = AppConfig(
        acoustid_api_key=str(raw.get("acoustid_api_key", "")).strip(),
        input_dir=Path(str(raw.get("input_dir", ""))).expanduser(),
        output_dir=Path(str(raw.get("output_dir", ""))).expanduser(),
        mode=str(raw.get("mode", "copy")).lower(),
        confidence_threshold=float(raw.get("confidence_threshold", 0.85)),
        workers=max(1, int(raw.get("workers", 4))),
        skip_if_tagged=_parse_bool(raw.get("skip_if_tagged", False)),
        songs_dir=str(raw.get("songs_dir", "songs")),
        nonsongs_dir=str(raw.get("nonsongs_dir", "non-songs")),
        fpcalc_path=(str(raw.get("fpcalc_path", "")).strip() or None),
        acoustid_requests_per_second=float(raw.get("acoustid_requests_per_second", 3.0)),
        musicbrainz_requests_per_second=float(raw.get("musicbrainz_requests_per_second", 1.0)),
    )

    _validate_config(cfg, path)
    return cfg


def _validate_config(cfg: AppConfig, config_path: Path) -> None:
    if not cfg.acoustid_api_key or cfg.acoustid_api_key == "YOUR_ACOUSTID_API_KEY":
        raise ValueError(
            f"Missing acoustid_api_key in {config_path}. "
            "Create one at https://acoustid.org/api-key"
        )
    if not cfg.input_dir.exists() or not cfg.input_dir.is_dir():
        raise ValueError(f"Input directory does not exist: {cfg.input_dir}")
    if cfg.mode not in {"copy", "move"}:
        raise ValueError("mode must be either 'copy' or 'move'")
    if not 0.0 <= cfg.confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0.0 and 1.0")
    if cfg.acoustid_requests_per_second <= 0:
        raise ValueError("acoustid_requests_per_second must be > 0")
    if cfg.musicbrainz_requests_per_second <= 0:
        raise ValueError("musicbrainz_requests_per_second must be > 0")


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off", ""}:
            return False
        raise ValueError(f"skip_if_tagged must be a boolean, got: {value!r}")
    return bool(value)
