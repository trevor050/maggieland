from music_cleanup.tagger import build_song_filename, sanitize_component


def test_sanitize_component_windows_chars():
    assert sanitize_component('bad<>:"/\\|?*name') == "bad_________name"


def test_sanitize_component_empty_fallback():
    assert sanitize_component("   ") == "unknown"


def test_build_song_filename():
    assert build_song_filename("Track", "Artist") == "Track - Artist.mp3"
