# AGENTS.md

## Project Summary
- Project: `music-cleanup`
- Goal: Batch-clean a large MP3 library by identifying tracks from audio fingerprints, writing core ID3 tags, and organizing output into two buckets.
- Primary user context: non-technical Windows user (Surface) who should run it via double-click launcher.

## Core Product Behavior
- Input: recursive scan of `.mp3` files.
- Identification: AcoustID fingerprint lookup, then MusicBrainz metadata enrichment.
- Conservative confidence default: `0.85`.
- Matched files:
  - Write tags: artist/title/album/year/track when available.
  - Rename to `Title - Artist.mp3` (sanitized for Windows paths).
  - Place into `songs/` folder.
- Unresolved files:
  - Preserve original filename.
  - Place into `non-songs/` folder.

## Operational Constraints
- Cost target: $0 (no paid audio recognition fallback in v1).
- Requires internet for lookup APIs.
- MP3 only in v1.
- Continue-on-error behavior is required.

## Packaging + Handoff
- Deliverable package for end users:
  - `music-cleanup.exe`
  - `run_music_cleanup.bat`
  - `cleanup.config.example.yml`
  - `README_QUICKSTART.md`
  - `LICENSE`
- Packaging preference: zip artifact (`music-cleanup-windows.zip`).
- UX requirement: double-click `.bat` launcher with minimal setup.

## Reporting Contract
- `report.csv` for all processed files.
- `review.csv` for unresolved + error items requiring manual follow-up.
- `run-summary.json` for totals and run metadata.

## Known Tricky Bits
- AcoustID confidence can be noisy with meme/low-quality clips.
- `fpcalc` dependency is external; if missing, recognition fails. Keep message explicit in errors.
- Runtime now preflights `fpcalc` (config/env/PATH/launcher directory) and fails fast with remediation guidance instead of per-file spam errors.
- Filename collisions must be deterministic (`(1)`, `(2)`, ...).
- Windows path sanitization and reserved characters must be enforced.
- CLI entrypoint can be launched as a script on Windows in some bundles; avoid package-relative imports in `cli.py` to prevent `ImportError: attempted relative import with no known parent package`.

## Future Improvements
- Optional paid fallback mode (strict budget cap).
- Album art embedding and additional tags.
- A tiny local UI wrapper for non-terminal users.
- Optional duplicate detection and dedupe report.

## Update Log
- 2026-02-19: Initial implementation scaffolded for Windows-first batch workflow, reports, launcher, docs, and packaging pipeline.
- 2026-02-20: Added thread-safe API rate limiting with configurable RPS for AcoustID and MusicBrainz to keep parallel workers within service limits.
- 2026-02-25: Final pre-handoff validation completed (tests + CLI smoke check). Created production-only distribution bundle flow that excludes test files.
- 2026-03-05: Fixed CLI import strategy for cross-invocation compatibility (module and direct script execution), resolving Windows `attempted relative import` startup failures.
- 2026-03-05: Added `fpcalc` resolution preflight and clearer fingerprint dependency errors; added regression tests for launcher-adjacent `fpcalc.exe` discovery.
