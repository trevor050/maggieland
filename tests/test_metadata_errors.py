from pathlib import Path

import pytest

from music_cleanup.metadata import FingerprintError, identify_track


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
            confidence_threshold=0.85,
            fpcalc_path=None,
        )
