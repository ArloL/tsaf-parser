"""Dynamic data-driven tests for the TSAF parser.

Each track with a *.json metadata file in data/ is automatically discovered
and tested against every parser that has a matching .bin file.
"""

import pytest

from djay_tsaf_parser.parser import (
    parse_local_media_item_location,
    parse_media_item_analyzed_data,
    parse_media_item_title_id,
    parse_media_item_user_data,
)


# ---------------------------------------------------------------------------
# parse_media_item_title_id
# ---------------------------------------------------------------------------


def test_title_id_fields(track_with_title_ids):
    data = track_with_title_ids.load_bin("mediaItemTitleIDs")
    result = parse_media_item_title_id(data)
    assert result.title == track_with_title_ids.title
    assert result.artist == track_with_title_ids.artist
    assert result.duration == pytest.approx(track_with_title_ids.duration, rel=0.003)


# ---------------------------------------------------------------------------
# parse_local_media_item_location
# ---------------------------------------------------------------------------


def test_location_fields(track_with_location):
    data = track_with_location.load_bin("localMediaItemLocations")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == track_with_location.apple_music_id
    assert result.title == track_with_location.title
    assert result.artist == track_with_location.artist
    assert result.duration == pytest.approx(track_with_location.duration, rel=0.003)


# ---------------------------------------------------------------------------
# parse_media_item_analyzed_data
# ---------------------------------------------------------------------------


def test_analyzed_data_fields(track_with_analyzed_data):
    data = track_with_analyzed_data.load_bin("mediaItemAnalyzedData")
    result = parse_media_item_analyzed_data(data)
    assert len(result.title_ids) >= 1
    assert result.title_ids[0].title == track_with_analyzed_data.title
    assert result.title_ids[0].artist == track_with_analyzed_data.artist
    assert result.title_ids[0].duration == pytest.approx(
        track_with_analyzed_data.duration, rel=0.003
    )
    assert result.bpm == pytest.approx(track_with_analyzed_data.bpm, rel=0.003)
    if result.key_signature_index is not None:
        assert result.key_signature_index == track_with_analyzed_data.key_signature_index


# ---------------------------------------------------------------------------
# parse_media_item_user_data
# ---------------------------------------------------------------------------


def test_user_data_title_ids(track_with_user_data):
    data = track_with_user_data.load_bin("mediaItemUserData")
    result = parse_media_item_user_data(data)
    assert len(result.title_ids) >= 1
    assert result.title_ids[0].title == track_with_user_data.title
    assert result.title_ids[0].artist == track_with_user_data.artist
    assert result.title_ids[0].duration == pytest.approx(
        track_with_user_data.duration, rel=0.003
    )
