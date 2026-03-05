from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


RUNTIME_REQUIREMENTS = """pyacoustid>=1.3.0
musicbrainzngs>=0.7.1
mutagen>=1.47.0
PyYAML>=6.0.1
"""

README = """MUSIC CLEANUP - WINDOWS QUICK START

1) Install Python 3.11+ one time:
   https://www.python.org/downloads/windows/

2) Open cleanup.config.yml and fill in:
   - acoustid_api_key: https://acoustid.org/api-key
   - input_dir
   - output_dir

3) Double-click run_music_cleanup.bat

Output:
- songs/ for matched tracks
- non-songs/ for unresolved files
- report.csv, review.csv, run-summary.json in output_dir

Notes:
- Internet required for metadata lookup.
- Conservative confidence default is 0.85.
- API limits are enforced by default.
"""

BATCH = r"""@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "CONFIG=%SCRIPT_DIR%cleanup.config.yml"
set "VENV_DIR=%SCRIPT_DIR%.venv"

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python is not installed or not in PATH.
  echo Install Python 3.11+ from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

if not exist "%CONFIG%" (
  echo [ERROR] cleanup.config.yml not found.
  pause
  exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install -r "%SCRIPT_DIR%requirements-runtime.txt"

set "PYTHONPATH=%SCRIPT_DIR%src"
python -m music_cleanup.cli --config "%CONFIG%"
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
  echo Done. Check songs/, non-songs/, report.csv, and review.csv in your output folder.
) else (
  echo Completed with errors. Check report.csv and review.csv for details.
)

echo.
pause
exit /b %ERR%
"""

CONFIG = """acoustid_api_key: "YOUR_ACOUSTID_API_KEY"

input_dir: "C:/Users/YourName/Music/messy_mp3s"
output_dir: "C:/Users/YourName/Music/clean_output"

mode: "copy"
confidence_threshold: 0.85
workers: 4
skip_if_tagged: false

songs_dir: "songs"
nonsongs_dir: "non-songs"

fpcalc_path: ""

acoustid_requests_per_second: 3.0
musicbrainz_requests_per_second: 1.0
"""


def create_release(out_dir: Path, version: str) -> Path:
    package_root = out_dir / f"music-cleanup-windows-runtime-{version}"
    if package_root.exists():
        shutil.rmtree(package_root)
    (package_root / "src").mkdir(parents=True, exist_ok=True)

    src_pkg = Path("src") / "music_cleanup"
    shutil.copytree(src_pkg, package_root / "src" / "music_cleanup", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    (package_root / "requirements-runtime.txt").write_text(RUNTIME_REQUIREMENTS, encoding="utf-8")
    (package_root / "run_music_cleanup.bat").write_text(BATCH, encoding="utf-8")
    (package_root / "cleanup.config.yml").write_text(CONFIG, encoding="utf-8")
    (package_root / "README_START_HERE.txt").write_text(README, encoding="utf-8")
    shutil.copy2("LICENSE", package_root / "LICENSE")

    zip_path = out_dir / f"music-cleanup-windows-runtime-{version}.zip"
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for file in sorted(package_root.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(package_root.parent))

    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--out-dir", default="dist/releases", type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = create_release(args.out_dir, args.version)
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
