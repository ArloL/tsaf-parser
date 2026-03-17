"""Tests for the TSAF parser."""

import pytest

from djay_tsaf_parser.parser import (
    TSAFParseError,
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


def test_parse_local_media_item_location_luvmaschine():
    data = _load("luvmaschine-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 16256298393022529679
    assert result.title == "Luvmaschine Original Mix"
    assert result.artist == "Luvless"
    assert result.duration == pytest.approx(414.8, abs=0.1)


def test_parse_local_media_item_location_just():
    data = _load("just-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 14110461239496945263
    assert result.title == "Just (Original Mix)"
    assert result.artist == "Bicep"
    assert result.duration == pytest.approx(372.6, abs=0.1)


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


def test_parse_media_item_title_id_luvmaschine():
    data = _load("luvmaschine-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "Luvmaschine Original Mix"
    assert result.artist == "Luvless"
    assert result.duration == pytest.approx(414.8, abs=0.1)


def test_parse_media_item_title_id_just():
    data = _load("just-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "Just (Original Mix)"
    assert result.artist == "Bicep"
    assert result.duration == pytest.approx(372.6, abs=0.1)


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


def test_parse_media_item_analyzed_data_luvmaschine():
    data = _load("luvmaschine-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert result.title == "Luvmaschine Original Mix"
    assert result.artist == "Luvless"
    assert result.duration == pytest.approx(414.8, abs=0.1)
    assert result.bpm == pytest.approx(114.0, abs=0.1)
    assert result.key_signature_index == 3


def test_parse_media_item_analyzed_data_just():
    data = _load("just-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert result.title == "Just (Original Mix)"
    assert result.artist == "Bicep"
    assert result.duration == pytest.approx(372.6, abs=0.1)
    assert result.bpm == pytest.approx(120.0, abs=0.1)
    assert result.key_signature_index == 11


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


def test_parse_media_item_user_data_luvmaschine_end_only():
    data = _load("luvmaschine-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert result.title == "Luvmaschine Original Mix"
    assert result.artist == "Luvless"
    assert result.duration == pytest.approx(414.8, abs=0.1)
    assert result.automix_start_point == pytest.approx(54.8, abs=0.1)
    assert result.automix_end_point == pytest.approx(378.9, abs=0.1)


def test_parse_media_item_user_data_just_no_automix():
    data = _load("just-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert result.title == "Just (Original Mix)"
    assert result.artist == "Bicep"
    assert result.duration == pytest.approx(372.6, abs=0.1)
    assert result.automix_start_point is None
    assert result.automix_end_point is None
