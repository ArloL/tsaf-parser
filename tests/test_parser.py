"""Tests for the TSAF parser."""

import pytest

from djay_tsaf_parser.parser import TSAFParseError, extract_apple_music_id

DATA_DIR = "data"


def _load(filename: str) -> bytes:
    with open(f"{DATA_DIR}/{filename}", "rb") as f:
        return f.read()


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
