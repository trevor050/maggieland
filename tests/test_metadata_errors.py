from pathlib import Path

import pytest

from music_cleanup.metadata import FingerprintError, identify_track, validate_acoustid_api_key


def test_identify_track_raises_on_acoustid_api_error(monkeypatch):
    def fake_match(*_args, **_kwargs):
        return {
            "status": "error",
            "error": {"code": 4, "message": "invalid API key"},
        }

    monkeypatch.setattr("music_cleanup.metadata.acoustid.match", fake_match)

    with pytest.raises(FingerprintError, match="invalid API key"):
        identify_track(
            mp3_path=Path("x.mp3"),
            api_key="bad-key",
            fpcalc_path=None,
        )


def test_validate_api_key_raises_on_invalid_key(monkeypatch):
    monkeypatch.setattr(
        "music_cleanup.metadata.acoustid.lookup",
        lambda *_args, **_kwargs: {
            "status": "error",
            "error": {"code": 4, "message": "invalid API key"},
        },
    )

    with pytest.raises(FingerprintError, match="API key is invalid"):
        validate_acoustid_api_key("bad-key")


def test_validate_api_key_allows_non_key_errors(monkeypatch):
    monkeypatch.setattr(
        "music_cleanup.metadata.acoustid.lookup",
        lambda *_args, **_kwargs: {
            "status": "error",
            "error": {"code": 7, "message": "invalid fingerprint"},
        },
    )

    validate_acoustid_api_key("good-key")
