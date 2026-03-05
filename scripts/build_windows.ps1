Param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Installing dependencies..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

Write-Host "[2/4] Building one-file exe with PyInstaller..."
& $Python -m PyInstaller --noconfirm --clean --onefile --name music-cleanup --paths src src/music_cleanup/cli.py

Write-Host "[3/4] Assembling Windows package folder..."
& $Python scripts/make_handoff_zip.py --exe dist/music-cleanup.exe

Write-Host "[4/4] Done. Package is under dist/windows_package"
