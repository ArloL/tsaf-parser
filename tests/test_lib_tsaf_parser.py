"""Tests for lib_tsaf_parser — structural parser and convenience parsers."""

import pytest

from djay_tsaf_parser.lib_tsaf_parser import (
    CompactEntity,
    TSAFDocument,
    TSAFParseError,
    VerboseEntity,
    parse_local_media_item_location,
    parse_media_item_analyzed_data,
    parse_media_item_title_id,
    parse_media_item_user_data,
    parse_tsaf,
)

DATA_DIR = "data"


def _load(filename: str) -> bytes:
    with open(f"{DATA_DIR}/{filename}", "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def test_parse_tsaf_header_fields():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    assert isinstance(doc, TSAFDocument)
    assert doc.header.magic == b"TSAF"
    assert doc.header.version == 0x00030003
    assert doc.header.entity_count == 1


def test_parse_tsaf_invalid_magic_raises():
    with pytest.raises(TSAFParseError, match="magic"):
        parse_tsaf(b"XXXX" + b"\x03\x00\x03\x00" + b"\x01\x00\x00\x00" + b"\x00" * 8)


# ---------------------------------------------------------------------------
# mediaItemTitleIDs — structural
# ---------------------------------------------------------------------------


def test_parse_tsaf_mediaItemTitleIDs_single_verbose_entity():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    assert len(doc.entities) == 1
    entity = doc.entities[0]
    assert isinstance(entity, VerboseEntity)
    assert entity.type_name == "ADCMediaItemTitleID"


def test_parse_tsaf_mediaItemTitleIDs_field_names_and_tags():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    entity = doc.entities[0]
    assert isinstance(entity, VerboseEntity)
    field_map = {f.name: f for f in entity.fields}
    assert "title" in field_map
    assert "artist" in field_map
    assert "duration" in field_map
    assert field_map["title"].type_tag == 0x08
    assert field_map["artist"].type_tag == 0x08
    assert field_map["duration"].type_tag == 0x13


def test_parse_tsaf_mediaItemTitleIDs_field_values():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    entity = doc.entities[0]
    assert isinstance(entity, VerboseEntity)
    field_map = {f.name: f.value for f in entity.fields}
    assert field_map["title"] == "Arquipelago (Original Mix)"
    assert field_map["artist"] == "Gui Boratto"
    assert field_map["duration"] == pytest.approx(367.5, abs=0.1)


# ---------------------------------------------------------------------------
# localMediaItemLocations — structural
# ---------------------------------------------------------------------------


def test_parse_tsaf_localMediaItemLocations_nested_titleid():
    """ADCMediaItemLocation embeds an ADCMediaItemTitleID inside a titleIDs collection."""
    data = _load("d8a452ad23698cb4076d1baed024844b-localMediaItemLocations.bin")
    doc = parse_tsaf(data)
    location = doc.entities[0]
    assert isinstance(location, VerboseEntity)
    assert location.type_name == "ADCMediaItemLocation"

    # titleIDs field holds a list containing one VerboseEntity
    title_ids_field = next(f for f in location.fields if f.name == "titleIDs")
    assert isinstance(title_ids_field.value, list)
    assert len(title_ids_field.value) == 1
    nested = title_ids_field.value[0]
    assert isinstance(nested, VerboseEntity)
    assert nested.type_name == "ADCMediaItemTitleID"
    field_map = {f.name: f.value for f in nested.fields}
    assert field_map["title"] == "Arquipelago (Original Mix)"
    assert field_map["artist"] == "Gui Boratto"


def test_parse_tsaf_localMediaItemLocations_apple_id_in_collection():
    """Apple Music ID is stored as a string in a sourceURIs collection."""
    data = _load("d8a452ad23698cb4076d1baed024844b-localMediaItemLocations.bin")
    doc = parse_tsaf(data)
    location = doc.entities[0]
    assert isinstance(location, VerboseEntity)

    # Find the anonymous collection field that contains the Apple ID string
    apple_id_field = next(
        f for f in location.fields if f.name is None and isinstance(f.value, list)
    )
    assert any("8986230555104447322" in str(item) for item in apple_id_field.value)


# ---------------------------------------------------------------------------
# mediaItemAnalyzedData — structural
# ---------------------------------------------------------------------------


def test_parse_tsaf_mediaItemAnalyzedData_entity_types():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemAnalyzedData.bin")
    doc = parse_tsaf(data)
    analyzed = doc.entities[0]
    assert isinstance(analyzed, VerboseEntity)
    assert analyzed.type_name == "ADCMediaItemAnalyzedData"
    title_ids_field = next(f for f in analyzed.fields if f.name == "titleIDs")
    assert len(title_ids_field.value) == 1
    assert isinstance(title_ids_field.value[0], VerboseEntity)
    assert title_ids_field.value[0].type_name == "ADCMediaItemTitleID"


def test_parse_tsaf_mediaItemAnalyzedData_bpm_and_key():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemAnalyzedData.bin")
    doc = parse_tsaf(data)
    analyzed = next(
        e for e in doc.entities
        if isinstance(e, VerboseEntity) and e.type_name == "ADCMediaItemAnalyzedData"
    )
    field_map = {f.name: f for f in analyzed.fields}
    assert field_map["bpm"].type_tag == 0x13
    assert field_map["bpm"].value == pytest.approx(125.0, abs=0.1)
    assert field_map["keySignatureIndex"].type_tag == 0x0F
    assert field_map["keySignatureIndex"].value == 15


# ---------------------------------------------------------------------------
# mediaItemUserData — cue points (structural)
# ---------------------------------------------------------------------------


def test_parse_tsaf_mediaItemUserData_cue_fields():
    """ADCCuePoint entities are inline children of ADCMediaItemUserData, resolved by cross-ref."""
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    user_data = doc.entities[0]
    assert isinstance(user_data, VerboseEntity)
    fm = {f.name: f for f in user_data.fields}
    assert "automixStartPoint" in fm
    assert "automixEndPoint" in fm
    assert "endPoint" in fm
    # Cue fields are ADCCuePoint sub-entities
    assert fm["automixStartPoint"].type_tag == 0x2B
    cue = fm["automixStartPoint"].value
    assert isinstance(cue, (VerboseEntity, CompactEntity))
    assert cue.type_name == "ADCCuePoint"
    cue_fm = {f.name: f.value for f in cue.fields}
    assert cue_fm["time"] == pytest.approx(17.475, abs=0.01)


def test_parse_tsaf_luvmaschine_cue_fields():
    """luvmaschine has a different schema order but cue fields resolve by cross-ref."""
    data = _load("df6376b59fbc6e4fd56d55f3e64b5d2e-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    user_data = doc.entities[0]
    fm = {f.name: f.value for f in user_data.fields}
    cue = fm["automixStartPoint"]
    assert isinstance(cue, (VerboseEntity, CompactEntity))
    cue_fm = {f.name: f.value for f in cue.fields}
    assert cue_fm.get("time") or cue_fm.get("endTime") == pytest.approx(54.735, abs=0.01)


# ---------------------------------------------------------------------------
# parse_local_media_item_location
# ---------------------------------------------------------------------------


def test_parse_local_media_item_location_guiboratto():
    data = _load("d8a452ad23698cb4076d1baed024844b-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 8986230555104447322
    assert result.title == "Arquipelago (Original Mix)"
    assert result.artist == "Gui Boratto"
    assert result.duration == pytest.approx(367.5, abs=0.1)


def test_parse_local_media_item_location_happysong():
    data = _load("f6fa142fbda6a56deb6dfa71dbef389e-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 15276055944141716431
    assert result.title == "The Happy Song"
    assert result.artist == "Imogen Heap"
    assert result.duration == pytest.approx(158.0, abs=0.1)


def test_parse_local_media_item_location_luvmaschine():
    data = _load("df6376b59fbc6e4fd56d55f3e64b5d2e-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 16256298393022529679
    assert result.title == "Luvmaschine Original Mix"
    assert result.artist == "Luvless"
    assert result.duration == pytest.approx(414.8, abs=0.1)


def test_parse_local_media_item_location_just():
    data = _load("dc11bf9b77216b8c5f295030613d72f1-localMediaItemLocations.bin")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == 14110461239496945263
    assert result.title == "Just (Original Mix)"
    assert result.artist == "Bicep"
    assert result.duration == pytest.approx(372.6, abs=0.1)


# ---------------------------------------------------------------------------
# parse_media_item_title_id
# ---------------------------------------------------------------------------


def test_parse_media_item_title_id_guiboratto():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "Arquipelago (Original Mix)"
    assert result.artist == "Gui Boratto"
    assert result.duration == pytest.approx(367.5, abs=0.1)


def test_parse_media_item_title_id_happysong():
    data = _load("f6fa142fbda6a56deb6dfa71dbef389e-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "The Happy Song"
    assert result.artist == "Imogen Heap"
    assert result.duration == pytest.approx(158.0, abs=0.1)


def test_parse_media_item_title_id_luvmaschine():
    data = _load("df6376b59fbc6e4fd56d55f3e64b5d2e-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "Luvmaschine Original Mix"
    assert result.artist == "Luvless"
    assert result.duration == pytest.approx(414.8, abs=0.1)


def test_parse_media_item_title_id_just():
    data = _load("dc11bf9b77216b8c5f295030613d72f1-mediaItemTitleIDs.bin")
    result = parse_media_item_title_id(data)
    assert result.title == "Just (Original Mix)"
    assert result.artist == "Bicep"
    assert result.duration == pytest.approx(372.6, abs=0.1)


# ---------------------------------------------------------------------------
# parse_media_item_analyzed_data
# ---------------------------------------------------------------------------


def test_parse_media_item_analyzed_data_guiboratto():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert len(result.title_ids) == 1
    assert result.title_ids[0].title == "Arquipelago (Original Mix)"
    assert result.title_ids[0].artist == "Gui Boratto"
    assert result.title_ids[0].duration == pytest.approx(367.5, abs=0.1)
    assert result.bpm == pytest.approx(125.0, abs=0.1)
    assert result.key_signature_index == 15


def test_parse_media_item_analyzed_data_happysong():
    data = _load("f6fa142fbda6a56deb6dfa71dbef389e-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert result.title_ids[0].title == "The Happy Song"
    assert result.title_ids[0].artist == "Imogen Heap"
    assert result.title_ids[0].duration == pytest.approx(158.0, abs=0.1)
    assert result.bpm == pytest.approx(82.0, abs=0.1)
    assert result.key_signature_index == 6


def test_parse_media_item_analyzed_data_luvmaschine():
    data = _load("df6376b59fbc6e4fd56d55f3e64b5d2e-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert result.title_ids[0].title == "Luvmaschine Original Mix"
    assert result.title_ids[0].artist == "Luvless"
    assert result.title_ids[0].duration == pytest.approx(414.8, abs=0.1)
    assert result.bpm == pytest.approx(114.0, abs=0.1)
    assert result.key_signature_index == 3


def test_parse_media_item_analyzed_data_just():
    data = _load("dc11bf9b77216b8c5f295030613d72f1-mediaItemAnalyzedData.bin")
    result = parse_media_item_analyzed_data(data)
    assert result.title_ids[0].title == "Just (Original Mix)"
    assert result.title_ids[0].artist == "Bicep"
    assert result.title_ids[0].duration == pytest.approx(372.6, abs=0.1)
    assert result.bpm == pytest.approx(120.0, abs=0.1)
    assert result.key_signature_index == 11


# ---------------------------------------------------------------------------
# parse_media_item_user_data
# ---------------------------------------------------------------------------


def test_parse_media_item_user_data_guiboratto():
    data = _load("d8a452ad23698cb4076d1baed024844b-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert len(result.title_ids) == 1
    assert result.title_ids[0].title == "Arquipelago (Original Mix)"
    assert result.title_ids[0].artist == "Gui Boratto"
    assert result.title_ids[0].duration == pytest.approx(367.5, abs=0.1)
    assert result.automix_start_point == pytest.approx(17.475, abs=0.01)
    assert result.automix_end_point == pytest.approx(272.826, abs=0.01)
    assert result.end_point == pytest.approx(272.826, abs=0.01)


def test_parse_media_item_user_data_happysong_no_automix():
    data = _load("f6fa142fbda6a56deb6dfa71dbef389e-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert result.title_ids[0].title == "The Happy Song"
    assert result.title_ids[0].artist == "Imogen Heap"
    assert result.title_ids[0].duration == pytest.approx(158.0, abs=0.1)
    assert result.automix_start_point is None
    assert result.automix_end_point is None
    assert result.end_point is None


def test_parse_media_item_user_data_luvmaschine():
    data = _load("df6376b59fbc6e4fd56d55f3e64b5d2e-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert result.title_ids[0].title == "Luvmaschine Original Mix"
    assert result.title_ids[0].artist == "Luvless"
    assert result.title_ids[0].duration == pytest.approx(414.8, abs=0.1)
    assert result.automix_start_point == pytest.approx(54.8, abs=0.1)
    assert result.automix_end_point == pytest.approx(378.9, abs=0.1)
    assert result.end_point == pytest.approx(378.9, abs=0.1)


def test_parse_media_item_user_data_just_no_automix():
    data = _load("dc11bf9b77216b8c5f295030613d72f1-mediaItemUserData.bin")
    result = parse_media_item_user_data(data)
    assert result.title_ids[0].title == "Just (Original Mix)"
    assert result.title_ids[0].artist == "Bicep"
    assert result.title_ids[0].duration == pytest.approx(372.6, abs=0.1)
    assert result.automix_start_point is None
    assert result.automix_end_point is None
    assert result.end_point is None


# ---------------------------------------------------------------------------
# Dynamic data-driven tests (parametrized via conftest fixtures)
# ---------------------------------------------------------------------------


def test_title_id_fields(track_with_title_ids):
    data = track_with_title_ids.load_bin("mediaItemTitleIDs")
    result = parse_media_item_title_id(data)
    assert result.title == track_with_title_ids.title
    assert result.artist == track_with_title_ids.artist
    assert result.duration == pytest.approx(track_with_title_ids.duration, rel=0.003)


def test_location_fields(track_with_location):
    data = track_with_location.load_bin("localMediaItemLocations")
    result = parse_local_media_item_location(data)
    assert result.apple_music_id == track_with_location.apple_music_id
    assert result.title == track_with_location.title
    assert result.artist == track_with_location.artist
    assert result.duration == pytest.approx(track_with_location.duration, rel=0.003)


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


def test_user_data_title_ids(track_with_user_data):
    data = track_with_user_data.load_bin("mediaItemUserData")
    result = parse_media_item_user_data(data)
    assert len(result.title_ids) >= 1
    assert result.title_ids[0].title == track_with_user_data.title
    assert result.title_ids[0].artist == track_with_user_data.artist
    assert result.title_ids[0].duration == pytest.approx(
        track_with_user_data.duration, rel=0.003
    )
