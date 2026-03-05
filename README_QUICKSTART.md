# Quickstart (Windows)

## 1. Unzip
Unzip `music-cleanup-windows.zip` to any folder.

## 2. Add your API key
Open `cleanup.config.example.yml` in Notepad.
Set `acoustid_api_key` to your key from https://acoustid.org/api-key.

## 3. Set folders
In the same file, set:
- `input_dir`: folder with messy MP3 files
- `output_dir`: destination folder for organized output

Save the file as `cleanup.config.yml` in the same folder as `music-cleanup.exe`.

## 4. Run
Double-click `run_music_cleanup.bat`.

## 5. Check results
In `output_dir`:
- `songs/`: auto-tagged and renamed tracks
- `non-songs/`: unresolved files with original filenames
- `review.csv`: files you may want to handle manually
- `report.csv`: full processing report

## Notes
- Internet is required during matching.
- Tool is conservative by default to avoid bad tags.
- Use copy mode first so your originals stay untouched.
- API calls are rate-limited by default (`AcoustID: 3/sec`, `MusicBrainz: 1/sec`).

## Troubleshooting
- `No module named ...`: use the packaged `.exe`, not source scripts.
- `fpcalc not found`: put `fpcalc.exe` next to `music-cleanup.exe` or install Chromaprint.
- Permission denied: choose an `output_dir` where you have write access.
- Too many unresolved: lower confidence slightly (for example from `0.85` to `0.80`) in config and rerun.
