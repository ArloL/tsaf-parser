"""Tests for the TSAF parser."""

import pytest

from djay_tsaf_parser.parser import (
    TSAFParseError,
    extract_apple_music_id,
    extract_artist,
    extract_bpm,
    extract_duration,
    extract_key_signature_index,
    extract_title,
    parse_local_media_item_location,
    parse_media_item_analyzed_data,
    parse_media_item_title_id,
    parse_media_item_user_data,
)

DATA_DIR = "data"


def _load(filename: str) -> bytes:
    with open(f"{DATA_DIR}/{filename}", "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# extract_apple_music_id
# ---------------------------------------------------------------------------


def test_extract_apple_music_id_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_apple_music_id(data) == 8986230555104447322


def test_extract_apple_music_id_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_apple_music_id(data) == 15276055944141716431


# ---------------------------------------------------------------------------
# extract_title / extract_artist / extract_duration
# ---------------------------------------------------------------------------


def test_extract_title_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_title(data) == "Arquipelago (Original Mix)"


def test_extract_title_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_title(data) == "The Happy Song"


def test_extract_title_missing_raises():
    with pytest.raises(TSAFParseError, match="title"):
        extract_title(b"no title here")


def test_extract_artist_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_artist(data) == "Gui Boratto"


def test_extract_artist_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_artist(data) == "Imogen Heap"


def test_extract_artist_missing_raises():
    with pytest.raises(TSAFParseError, match="artist"):
        extract_artist(b"no artist here")


def test_extract_duration_guiboratto():
    data = _load("guiboratto-localMediaItemLocations.bin")
    assert extract_duration(data) == pytest.approx(367.5, abs=0.1)


def test_extract_duration_happysong():
    data = _load("happysong-localMediaItemLocations.bin")
    assert extract_duration(data) == pytest.approx(158.0, abs=0.1)


# ---------------------------------------------------------------------------
# extract_bpm / extract_key_signature_index
# ---------------------------------------------------------------------------


def test_extract_bpm_guiboratto():
    data = _load("guiboratto-mediaItemAnalyzedData.bin")
    assert extract_bpm(data) == pytest.approx(125.0, abs=0.1)


def test_extract_bpm_happysong():
    data = _load("happysong-mediaItemAnalyzedData.bin")
    assert extract_bpm(data) == pytest.approx(82.0, abs=0.1)


def test_extract_key_signature_index_guiboratto():
    data = _load("guiboratto-mediaItemAnalyzedData.bin")
    assert extract_key_signature_index(data) == 15


def test_extract_key_signature_index_happysong():
    data = _load("happysong-mediaItemAnalyzedData.bin")
    assert extract_key_signature_index(data) == 6


# ---------------------------------------------------------------------------
# parse_local_media_item_location
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# parse_media_item_title_id
# ---------------------------------------------------------------------------


def test_parse_media_item_title_id_guiboratto():
    data = _load("guiboratto-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "Arquipelago (Original Mix)"
    assert result.artist == "Gui Boratto"
    assert result.duration == pytest.approx(367.5, abs=0.1)


def test_parse_media_item_title_id_happysong():
    data = _load("happysong-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "The Happy Song"
    assert result.artist == "Imogen Heap"
    assert result.duration == pytest.approx(158.0, abs=0.1)


# ---------------------------------------------------------------------------
# parse_media_item_analyzed_data
# ---------------------------------------------------------------------------


def test_parse_media_item_analyzed_data_guiboratto():
    data = _load("guiboratto-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert result.title == "Arquipelago (Original Mix)"
    assert result.artist == "Gui Boratto"
    assert result.duration == pytest.approx(367.5, abs=0.1)
    assert result.bpm == pytest.approx(125.0, abs=0.1)
    assert result.key_signature_index == 15


def test_parse_media_item_analyzed_data_happysong():
    data = _load("happysong-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert result.title == "The Happy Song"
    assert result.artist == "Imogen Heap"
    assert result.duration == pytest.approx(158.0, abs=0.1)
    assert result.bpm == pytest.approx(82.0, abs=0.1)
    assert result.key_signature_index == 6


# ---------------------------------------------------------------------------
# parse_media_item_user_data
# ---------------------------------------------------------------------------


def test_parse_media_item_user_data_guiboratto():
    data = _load("guiboratto-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert result.title == "Arquipelago (Original Mix)"
    assert result.artist == "Gui Boratto"
    assert result.duration == pytest.approx(367.5, abs=0.1)
    assert result.automix_start_point == pytest.approx(17.475, abs=0.01)
    assert result.automix_end_point == pytest.approx(272.826, abs=0.01)


def test_parse_media_item_user_data_happysong_no_automix():
    data = _load("happysong-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert result.title == "The Happy Song"
    assert result.artist == "Imogen Heap"
    assert result.duration == pytest.approx(158.0, abs=0.1)
    assert result.automix_start_point is None
    assert result.automix_end_point is None
