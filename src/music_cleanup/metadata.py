from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import acoustid
import musicbrainzngs

from .models import MatchMetadata

musicbrainzngs.set_useragent("music-cleanup", "0.1.0", "https://example.invalid")


class FingerprintError(RuntimeError):
    """Raised when fingerprinting or lookup fails."""


class RateLimiter:
    """Thread-safe rate limiter shared across worker threads."""

    def __init__(
        self,
        requests_per_second: float,
        *,
        now_fn=time.monotonic,
        sleep_fn=time.sleep,
    ) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be > 0")
        self._interval = 1.0 / requests_per_second
        self._now = now_fn
        self._sleep = sleep_fn
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = self._now()
            wait_for = self._next_allowed_at - now
            if wait_for > 0:
                self._sleep(wait_for)
                now = self._now()
            self._next_allowed_at = max(self._next_allowed_at, now) + self._interval


_acoustid_limiter = RateLimiter(3.0)
_musicbrainz_limiter = RateLimiter(1.0)


def configure_rate_limits(acoustid_rps: float, musicbrainz_rps: float) -> None:
    global _acoustid_limiter, _musicbrainz_limiter
    _acoustid_limiter = RateLimiter(acoustid_rps)
    _musicbrainz_limiter = RateLimiter(musicbrainz_rps)


def identify_track(
    mp3_path: Path,
    api_key: str,
    confidence_threshold: float,
    fpcalc_path: str | None,
) -> MatchMetadata | None:
    if fpcalc_path:
        os.environ["FPCALC"] = fpcalc_path

    try:
        _acoustid_limiter.acquire()
        matches = acoustid.match(api_key, str(mp3_path), parse=False)
    except Exception as exc:
        raise FingerprintError(str(exc)) from exc

    if not isinstance(matches, dict) or matches.get("status") != "ok":
        return None

    best = _extract_best_candidate(matches)
    if not best:
        return None

    score, recording_id, title_hint, artist_hint = best
    if score < confidence_threshold:
        return None

    return enrich_metadata(
        recording_id=recording_id,
        confidence=score,
        title_hint=title_hint,
        artist_hint=artist_hint,
    )


def _extract_best_candidate(payload: dict) -> tuple[float, str, str | None, str | None] | None:
    best: tuple[float, str, str | None, str | None] | None = None
    for result in payload.get("results", []):
        score = float(result.get("score", 0.0))
        for recording in result.get("recordings", []):
            recording_id = recording.get("id")
            if not recording_id:
                continue
            title = recording.get("title")
            artists = recording.get("artists") or []
            artist = artists[0].get("name") if artists else None
            candidate = (score, recording_id, title, artist)
            if best is None or candidate[0] > best[0]:
                best = candidate
    return best


def enrich_metadata(
    recording_id: str,
    confidence: float,
    title_hint: str | None,
    artist_hint: str | None,
) -> MatchMetadata:
    try:
        _musicbrainz_limiter.acquire()
        data = musicbrainzngs.get_recording_by_id(
            recording_id,
            includes=["artists", "releases"],
        )
        recording = data.get("recording", {})
    except Exception:
        recording = {}

    title = _clean_value(recording.get("title")) or _clean_value(title_hint)
    artist_credit = recording.get("artist-credit") or []
    artist = _artist_from_credit(artist_credit) or _clean_value(artist_hint)

    album = None
    year = None
    track = None
    releases = recording.get("release-list") or []
    if releases:
        first_release = releases[0]
        album = _clean_value(first_release.get("title"))
        date = _clean_value(first_release.get("date"))
        if date:
            year = date.split("-")[0]
        medium_list = first_release.get("medium-list") or []
        if medium_list:
            track_count = medium_list[0].get("track-count")
            if track_count is not None:
                track = str(track_count)

    return MatchMetadata(
        confidence=confidence,
        artist=artist,
        title=title,
        album=album,
        year=year,
        track=track,
    )


def _artist_from_credit(artist_credit: list[dict]) -> str | None:
    for chunk in artist_credit:
        artist = chunk.get("artist")
        if isinstance(artist, dict) and artist.get("name"):
            return _clean_value(artist["name"])
    return None


def _clean_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned if cleaned else None
