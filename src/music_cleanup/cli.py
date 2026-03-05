from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from music_cleanup.config import AppConfig, load_config, persist_config_values
from music_cleanup.decision import is_confident_match, should_skip_existing
from music_cleanup.metadata import (
    FingerprintError,
    configure_rate_limits,
    identify_track,
    validate_acoustid_api_key,
)
from music_cleanup.models import FileInfo, FileResult, MatchMetadata
from music_cleanup.organizer import ensure_dir, transfer_file
from music_cleanup.reporting import write_report, write_review_csv, write_summary
from music_cleanup.scanner import scan_mp3_files
from music_cleanup.tagger import build_song_filename, sanitize_component, write_tags


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch cleanup MP3 metadata and filenames")
    parser.add_argument("--config", required=True, type=Path, help="Path to cleanup config yml")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without writing tags/files")
    parser.add_argument("--resume", action="store_true", help="Skip files already recorded in report.csv")
    parser.add_argument("--workers", type=int, default=None, help="Override worker count")
    parser.add_argument(
        "--confidence", type=float, default=None, help="Override confidence threshold (0.0-1.0)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    start = time.perf_counter()

    try:
        cfg = load_config(args.config)
        if args.workers is not None:
            cfg.workers = max(1, args.workers)
        if args.confidence is not None:
            if not 0 <= args.confidence <= 1:
                raise ValueError("--confidence must be between 0.0 and 1.0")
            cfg.confidence_threshold = args.confidence

        cfg.input_dir = ensure_input_dir(cfg.input_dir, args.config)
        cfg.fpcalc_path = ensure_fpcalc_path(cfg.fpcalc_path, args.config)
        os.environ["FPCALC"] = cfg.fpcalc_path

        configure_rate_limits(
            acoustid_rps=cfg.acoustid_requests_per_second,
            musicbrainz_rps=cfg.musicbrainz_requests_per_second,
        )
        if not ensure_valid_api_key(cfg, args.config):
            print("No valid AcoustID key entered. Exiting.")
            return 2
        print("AcoustID preflight: OK")

        results = run_pipeline(cfg, dry_run=args.dry_run, resume=args.resume)
        elapsed = time.perf_counter() - start

        output_dir = cfg.output_dir
        write_report(output_dir / "report.csv", results)
        write_review_csv(output_dir / "review.csv", results)
        write_summary(output_dir / "run-summary.json", results, dry_run=args.dry_run, elapsed_sec=elapsed)

        errors = sum(1 for r in results if r.status == "error")
        unresolved = sum(1 for r in results if r.status == "unresolved_non_song")
        matched = sum(1 for r in results if r.status == "matched_song")
        print(
            f"Completed: matched={matched}, unresolved={unresolved}, errors={errors}. "
            f"Reports written to {output_dir}"
        )
        return 0 if errors == 0 else 1
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 2


def ensure_valid_api_key(cfg: AppConfig, config_path: Path) -> bool:
    key = (cfg.acoustid_api_key or "").strip()
    if not key or key == "YOUR_ACOUSTID_API_KEY":
        print("AcoustID key is missing.")
        key = _prompt_text(
            "Enter AcoustID application key from https://acoustid.org/my-applications "
            "(blank to cancel): "
        )
        if not key:
            return False
        cfg.acoustid_api_key = key
        persist_config_values(config_path, {"acoustid_api_key": key})

    while True:
        try:
            validate_acoustid_api_key(cfg.acoustid_api_key)
            return True
        except FingerprintError as exc:
            message = str(exc)
            if "API key is invalid" not in message:
                raise
            print(message)
            key = _prompt_text(
                "Enter a new AcoustID application key (blank to cancel): "
            )
            if not key:
                return False
            cfg.acoustid_api_key = key
            persist_config_values(config_path, {"acoustid_api_key": key})


def ensure_input_dir(input_dir: Path, config_path: Path) -> Path:
    current = input_dir.expanduser()
    while not current.exists() or not current.is_dir():
        print(f"Input folder does not exist: {current}")
        entered = _prompt_text("Enter a valid input folder path (blank to cancel): ")
        if not entered:
            raise RuntimeError("Input folder is required.")
        current = Path(entered).expanduser()
        persist_config_values(config_path, {"input_dir": str(current)})
    return current


def ensure_fpcalc_path(config_path_value: str | None, config_path: Path) -> str:
    candidate = config_path_value
    while True:
        try:
            resolved = resolve_fpcalc_path(candidate)
            if candidate and candidate != resolved:
                persist_config_values(config_path, {"fpcalc_path": resolved})
            return resolved
        except RuntimeError as exc:
            print(str(exc))
            entered = _prompt_text(
                "Enter full path to fpcalc/fpcalc.exe (blank to cancel): "
            )
            if not entered:
                raise RuntimeError("fpcalc is required to continue.") from exc
            candidate = entered
            persist_config_values(config_path, {"fpcalc_path": entered})


def resolve_fpcalc_path(config_path: str | None) -> str:
    """Resolve fpcalc location from config, env, PATH, or app directory."""
    candidate_strings: list[str] = []
    if config_path:
        candidate_strings.append(config_path)
    env_path = os.environ.get("FPCALC")
    if env_path:
        candidate_strings.append(env_path)

    script_dir = Path(sys.argv[0]).resolve().parent
    for name in ("fpcalc", "fpcalc.exe"):
        which_path = shutil.which(name)
        if which_path:
            candidate_strings.append(which_path)
        candidate_strings.append(str(script_dir / name))
        candidate_strings.append(str(Path.cwd() / name))

    seen: set[str] = set()
    for candidate in candidate_strings:
        normalized = str(Path(candidate).expanduser())
        if normalized in seen:
            continue
        seen.add(normalized)
        if Path(normalized).is_file():
            return normalized

    raise RuntimeError(
        "fpcalc not found. Install Chromaprint/fpcalc and either set fpcalc_path in cleanup.config.yml, "
        "put fpcalc.exe next to the launcher, or add fpcalc to PATH."
    )


def _prompt_text(prompt: str) -> str:
    if not sys.stdin or not sys.stdin.isatty():
        return ""
    return input(prompt).strip()


def run_pipeline(cfg: AppConfig, dry_run: bool, resume: bool) -> list[FileResult]:
    output_dir = cfg.output_dir
    ensure_dir(output_dir)
    songs_dir = output_dir / cfg.songs_dir
    nonsongs_dir = output_dir / cfg.nonsongs_dir
    ensure_dir(songs_dir)
    ensure_dir(nonsongs_dir)

    already_done_hashes = load_completed_hashes(output_dir / "report.csv") if resume else set()
    all_files = scan_mp3_files(cfg.input_dir)
    queued_files = [f for f in all_files if f.file_hash not in already_done_hashes]

    classified: dict[str, FileResult] = {}
    with ThreadPoolExecutor(max_workers=cfg.workers) as pool:
        futures = {
            pool.submit(classify_file, item, cfg): item
            for item in queued_files
        }
        for fut in as_completed(futures):
            result = fut.result()
            classified[result.file_hash] = result

    final_results: list[FileResult] = []
    for item in queued_files:
        result = classified[item.file_hash]

        if result.status == "matched_song" and result.artist and result.title:
            filename = build_song_filename(result.title, result.artist)
            destination = songs_dir / filename
            result.dest_path = transfer_file(item.source_path, destination, cfg.mode, dry_run=dry_run)
            if not dry_run and result.dest_path is not None:
                write_tags(
                    result.dest_path,
                    MatchMetadata(
                        confidence=result.confidence or 0.0,
                        artist=result.artist,
                        title=result.title,
                        album=result.album,
                        year=result.year,
                        track=result.track,
                    ),
                )
        elif result.status in {"unresolved_non_song", "error"}:
            kept_name = sanitize_component(item.source_path.name)
            if not kept_name.lower().endswith(".mp3"):
                kept_name = f"{Path(kept_name).stem}.mp3"
            destination = nonsongs_dir / kept_name
            # Safety: never move unresolved/error files out of source.
            # Copy keeps originals available for manual review/retry.
            fallback_mode = "copy" if cfg.mode == "move" else cfg.mode
            result.dest_path = transfer_file(item.source_path, destination, fallback_mode, dry_run=dry_run)

        final_results.append(result)

    if resume and already_done_hashes:
        historical = load_report_results(output_dir / "report.csv")
        final_results = historical + final_results

    return final_results


def classify_file(file_info: FileInfo, cfg: AppConfig) -> FileResult:
    if should_skip_existing(file_info, cfg.skip_if_tagged):
        return FileResult(
            source_path=file_info.source_path,
            file_hash=file_info.file_hash,
            duration_sec=file_info.duration_sec,
            status="skipped",
            artist=file_info.existing_artist,
            title=file_info.existing_title,
        )

    try:
        match = identify_track(
            mp3_path=file_info.source_path,
            api_key=cfg.acoustid_api_key,
            fpcalc_path=cfg.fpcalc_path,
        )

        if not is_confident_match(match, cfg.confidence_threshold):
            return FileResult(
                source_path=file_info.source_path,
                file_hash=file_info.file_hash,
                duration_sec=file_info.duration_sec,
                status="unresolved_non_song",
                error_message=(
                    "No confident match from AcoustID/MusicBrainz. "
                    f"Try lowering confidence_threshold (current: {cfg.confidence_threshold:.2f})."
                ),
            )

        return FileResult(
            source_path=file_info.source_path,
            file_hash=file_info.file_hash,
            duration_sec=file_info.duration_sec,
            status="matched_song",
            confidence=match.confidence,
            artist=match.artist,
            title=match.title,
            album=match.album,
            year=match.year,
            track=match.track,
        )
    except FingerprintError as exc:
        return FileResult(
            source_path=file_info.source_path,
            file_hash=file_info.file_hash,
            duration_sec=file_info.duration_sec,
            status="error",
            error_message=f"Fingerprint error: {exc}",
        )
    except Exception as exc:
        return FileResult(
            source_path=file_info.source_path,
            file_hash=file_info.file_hash,
            duration_sec=file_info.duration_sec,
            status="error",
            error_message=str(exc),
        )


def load_completed_hashes(report_path: Path) -> set[str]:
    if not report_path.exists():
        return set()
    hashes: set[str] = set()
    with report_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            file_hash = (row.get("file_hash") or "").strip()
            status = (row.get("status") or "").strip()
            if file_hash and status:
                hashes.add(file_hash)
    return hashes


def load_report_results(report_path: Path) -> list[FileResult]:
    if not report_path.exists():
        return []
    rows: list[FileResult] = []
    with report_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                FileResult(
                    source_path=Path(row.get("source_path", "")),
                    file_hash=row.get("file_hash", ""),
                    duration_sec=_to_float(row.get("duration_sec", "")),
                    status=(row.get("status") or "unresolved_non_song"),
                    confidence=_to_float(row.get("confidence", "")),
                    artist=row.get("artist") or None,
                    title=row.get("title") or None,
                    album=row.get("album") or None,
                    year=row.get("year") or None,
                    track=row.get("track") or None,
                    dest_path=Path(row["dest_path"]) if row.get("dest_path") else None,
                    error_message=row.get("error_message") or None,
                )
            )
    return rows


def _to_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
