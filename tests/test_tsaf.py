"""Tests for the structural TSAF parser (tsaf.py)."""

import pytest

from djay_tsaf_parser.parser import TSAFParseError
from djay_tsaf_parser.tsaf import (
    CompactEntity,
    TSAFDocument,
    VerboseEntity,
    find_all_entities,
    find_field,
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
    # ADCMediaItemTitleID is nested inside a collection field of ADCMediaItemAnalyzedData
    assert len(find_all_entities(doc.entities, "ADCMediaItemAnalyzedData")) == 1
    assert len(find_all_entities(doc.entities, "ADCMediaItemTitleID")) == 1


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


def test_parse_tsaf_mediaItemUserData_cue_entity_types():
    """guiboratto user data has one verbose and two compact ADCCuePoint entities."""
    data = _load("guiboratto-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    cue_entities = find_all_entities(doc.entities, "CuePoint")
    assert len(cue_entities) == 3
    assert isinstance(cue_entities[0], VerboseEntity)
    assert isinstance(cue_entities[1], CompactEntity)
    assert isinstance(cue_entities[2], CompactEntity)


def test_parse_tsaf_mediaItemUserData_verbose_cue_fields():
    data = _load("guiboratto-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    verbose_cue = next(
        e for e in find_all_entities(doc.entities, "CuePoint")
        if isinstance(e, VerboseEntity)
    )
    field_map = {f.name: f for f in verbose_cue.fields}
    assert "time" in field_map
    assert field_map["time"].type_tag == 0x13
    assert field_map["time"].value == pytest.approx(272.826, abs=0.01)


def test_parse_tsaf_mediaItemUserData_compact_cue_time_field():
    """First compact ADCCuePoint has a resolved 'time' field name from schema registry."""
    data = _load("guiboratto-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    compact_cues = [
        e for e in find_all_entities(doc.entities, "CuePoint")
        if isinstance(e, CompactEntity)
    ]
    assert len(compact_cues) >= 1
    first_compact = compact_cues[0]
    time_field = next(f for f in first_compact.fields if f.name == "time")
    assert time_field.type_tag == 0x13
    assert time_field.value == pytest.approx(17.475, abs=0.01)


def test_parse_tsaf_luvmaschine_cue_schema_order():
    """luvmaschine ADCCuePoint schema declares (time, endTime, number) — different from guiboratto."""
    data = _load("luvmaschine-mediaItemUserData.bin")
    doc = parse_tsaf(data)
    verbose_cue = next(
        e for e in find_all_entities(doc.entities, "CuePoint")
        if isinstance(e, VerboseEntity)
    )
    field_names = [f.name for f in verbose_cue.fields if f.name is not None]
    assert field_names[0] == "time"
    assert "endTime" in field_names


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def test_find_field_helper():
    data = _load("guiboratto-mediaItemTitleIDs.bin")
    doc = parse_tsaf(data)
    assert find_field(doc.entities, "TitleID", "title") == "Arquipelago (Original Mix)"
    assert find_field(doc.entities, "TitleID", "artist") == "Gui Boratto"
    assert find_field(doc.entities, "TitleID", "nonexistent") is None


def test_find_field_nested():
    """find_field descends into nested entities inside collection fields."""
    data = _load("guiboratto-localMediaItemLocations.bin")
    doc = parse_tsaf(data)
    title = find_field(doc.entities, "TitleID", "title")
    assert title == "Arquipelago (Original Mix)"


def test_find_all_entities_returns_all_depths():
    """find_all_entities finds entities nested inside collection fields."""
    data = _load("guiboratto-localMediaItemLocations.bin")
    doc = parse_tsaf(data)
    title_ids = find_all_entities(doc.entities, "TitleID")
    assert len(title_ids) >= 1
    assert all("TitleID" in e.type_name for e in title_ids)
