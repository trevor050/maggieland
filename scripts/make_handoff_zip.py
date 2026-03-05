from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

FILES_TO_INCLUDE = [
    "run_music_cleanup.bat",
    "cleanup.config.example.yml",
    "README_QUICKSTART.md",
    "LICENSE",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble handoff zip for Windows users")
    parser.add_argument("--exe", type=Path, required=True, help="Path to built music-cleanup.exe")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("dist") / "windows_package",
        help="Output folder for package",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exe_path = args.exe
    out_dir = args.out_dir

    if not exe_path.exists():
        raise FileNotFoundError(f"Exe not found: {exe_path}")

    package_dir = out_dir / "music-cleanup-windows"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(exe_path, package_dir / "music-cleanup.exe")

    for relative in FILES_TO_INCLUDE:
        src = Path(relative)
        if not src.exists():
            raise FileNotFoundError(f"Required file missing: {src}")
        shutil.copy2(src, package_dir / src.name)

    zip_path = out_dir / "music-cleanup-windows.zip"
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        for file in package_dir.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(package_dir))

    print(f"Package folder: {package_dir}")
    print(f"Package zip: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
