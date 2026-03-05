from __future__ import annotations

import shutil
from pathlib import Path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def transfer_file(source: Path, destination: Path, mode: str, dry_run: bool) -> Path:
    target = unique_destination(destination)
    if dry_run:
        return target
    ensure_dir(target.parent)
    if mode == "copy":
        shutil.copy2(source, target)
    else:
        shutil.move(str(source), str(target))
    return target
