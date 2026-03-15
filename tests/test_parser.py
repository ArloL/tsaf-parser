"""Tests for the TSAF parser."""

import pytest

from djay_tsaf_parser.parser import (
    TSAFParseError,
    extract_apple_music_id,
    extract_artist,
    extract_duration,
    extract_title,
    parse_local_media_item_location,
)

DATA_DIR = "data"


def _load(filename: str) -> bytes:
    with open(f"{DATA_DIR}/{filename}", "rb") as f:
        return f.read()


# --- apple_music_id ---


def test_extract_apple_music_id_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_apple_music_id(data) == 8986230555104447322


def test_extract_apple_music_id_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_apple_music_id(data) == 15276055944141716431


def test_extract_apple_music_id_missing_raises():
    with pytest.raises(TSAFParseError, match="not found"):
        extract_apple_music_id(b"TSAF\x00\x03\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00")


def test_extract_apple_music_id_malformed_raises():
    bad = b"\x21\x08com.apple.iTunes:not_digits\x00"
    with pytest.raises(TSAFParseError, match="decimal digits"):
        extract_apple_music_id(bad)


# --- title ---


def test_extract_title_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_title(data) == "Arquipelago (Original Mix)"


def test_extract_title_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_title(data) == "The Happy Song"


def test_extract_title_missing_raises():
    with pytest.raises(TSAFParseError, match="title"):
        extract_title(b"no title here")


# --- artist ---


def test_extract_artist_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_artist(data) == "Gui Boratto"


def test_extract_artist_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_artist(data) == "Imogen Heap"


def test_extract_artist_missing_raises():
    with pytest.raises(TSAFParseError, match="artist"):
        extract_artist(b"no artist here")


# --- duration ---


def test_extract_duration_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_duration(data) == pytest.approx(367.5, abs=0.1)


def test_extract_duration_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_duration(data) == pytest.approx(158.0, abs=0.1)


def test_extract_duration_missing_raises():
    with pytest.raises(TSAFParseError, match="duration"):
        extract_duration(b"no duration here")


# --- parse_local_media_item_location ---


def test_parse_local_media_item_location_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 8986230555104447322
    assert result.title == "Arquipelago (Original Mix)"
    assert result.artist == "Gui Boratto"
    assert result.duration == pytest.approx(367.5, abs=0.1)


def test_parse_local_media_item_location_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 15276055944141716431
    assert result.title == "The Happy Song"
    assert result.artist == "Imogen Heap"
    assert result.duration == pytest.approx(158.0, abs=0.1)
