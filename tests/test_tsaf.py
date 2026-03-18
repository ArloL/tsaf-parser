"""Tests for the structural TSAF parser (tsaf.py)."""

import pytest

from djay_tsaf_parser.tsaf import (
    CompactEntity,
    TSAFDocument,
    TSAFParseError,
    VerboseEntity,
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
    data = _load("guiboratto-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    assert isinstance(doc, TSAFDocument)
    assert doc.header.magic == b"TSAF"
    assert doc.header.version == 0x00030003
    assert doc.header.entity_count == 1


def test_parse_tsaf_invalid_magic_raises():
    with pytest.raises(TSAFParseError, match="magic"):
        parse_tsaf(b"XXXX" + b"\x03\x00\x03\x00" + b"\x01\x00\x00\x00" + b"\x00" * 8)


# ---------------------------------------------------------------------------
# mediaItemTitleIDs
# ---------------------------------------------------------------------------


def test_parse_tsaf_mediaItemTitleIDs_single_verbose_entity():
    data = _load("guiboratto-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    assert len(doc.entities) == 1
    entity = doc.entities[0]
    assert isinstance(entity, VerboseEntity)
    assert entity.type_name == "ADCMediaItemTitleID"


def test_parse_tsaf_mediaItemTitleIDs_field_names_and_tags():
    data = _load("guiboratto-mediaItemTitleIDs.bin")
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
    data = _load("guiboratto-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    entity = doc.entities[0]
    assert isinstance(entity, VerboseEntity)
    field_map = {f.name: f.value for f in entity.fields}
    assert field_map["title"] == "Arquipelago (Original Mix)"
    assert field_map["artist"] == "Gui Boratto"
    assert field_map["duration"] == pytest.approx(367.5, abs=0.1)


# ---------------------------------------------------------------------------
# localMediaItemLocations
# ---------------------------------------------------------------------------


def test_parse_tsaf_localMediaItemLocations_nested_titleid():
    """ADCMediaItemLocation embeds an ADCMediaItemTitleID inside a titleIDs collection."""
    data = _load("guiboratto-localMediaItemLocations.bin")
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
    data = _load("guiboratto-localMediaItemLocations.bin")
    doc = parse_tsaf(data)
    location = doc.entities[0]
    assert isinstance(location, VerboseEntity)

    # Find the anonymous collection field that contains the Apple ID string
    apple_id_field = next(
        f for f in location.fields if f.name is None and isinstance(f.value, list)
    )
    assert any("8986230555104447322" in str(item) for item in apple_id_field.value)


# ---------------------------------------------------------------------------
# mediaItemAnalyzedData
# ---------------------------------------------------------------------------


def test_parse_tsaf_mediaItemAnalyzedData_entity_types():
    data = _load("guiboratto-mediaItemAnalyzedData.bin")
    doc = parse_tsaf(data)
    analyzed = doc.entities[0]
    assert isinstance(analyzed, VerboseEntity)
    assert analyzed.type_name == "ADCMediaItemAnalyzedData"
    title_ids_field = next(f for f in analyzed.fields if f.name == "titleIDs")
    assert len(title_ids_field.value) == 1
    assert isinstance(title_ids_field.value[0], VerboseEntity)
    assert title_ids_field.value[0].type_name == "ADCMediaItemTitleID"


def test_parse_tsaf_mediaItemAnalyzedData_bpm_and_key():
    data = _load("guiboratto-mediaItemAnalyzedData.bin")
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
# mediaItemUserData — cue points
# ---------------------------------------------------------------------------


def test_parse_tsaf_mediaItemUserData_cue_fields():
    """ADCCuePoint entities are resolved into named float fields on ADCMediaItemUserData."""
    data = _load("guiboratto-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    user_data = doc.entities[0]
    assert isinstance(user_data, VerboseEntity)
    fm = {f.name: f for f in user_data.fields}
    assert "automixStartPoint" in fm
    assert "automixEndPoint" in fm
    assert "endPoint" in fm
    assert fm["automixStartPoint"].type_tag == 0x13
    assert fm["automixStartPoint"].value == pytest.approx(17.475, abs=0.01)
    assert fm["automixEndPoint"].value == pytest.approx(272.826, abs=0.01)
    assert fm["endPoint"].value == pytest.approx(272.826, abs=0.01)


def test_parse_tsaf_luvmaschine_cue_fields():
    """luvmaschine has a different schema order but cue fields resolve to correct values."""
    data = _load("luvmaschine-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    user_data = doc.entities[0]
    fm = {f.name: f.value for f in user_data.fields}
    assert fm["automixStartPoint"] == pytest.approx(54.735, abs=0.01)
    assert fm["automixEndPoint"] == pytest.approx(378.944, abs=0.01)
    assert fm["endPoint"] == pytest.approx(378.944, abs=0.01)


