"""TSAF binary format parser — public API.

Convenience parsers that delegate to the structural parser in
:mod:`djay_tsaf_parser.tsaf`.
"""

from dataclasses import dataclass

from djay_tsaf_parser.tsaf import (
    CompactEntity,
    TSAFParseError,
    VerboseEntity,
    parse_tsaf,
)

APPLE_MUSIC_ID_PREFIX = "com.apple.iTunes:"


@dataclass
class LocalMediaItemLocation:
    """Parsed fields from a localMediaItemLocations TSAF blob."""

    apple_music_id: int
    title: str
    artist: str
    duration: float


@dataclass
class MediaItemTitleID:
    """Parsed fields from a mediaItemTitleIDs TSAF blob."""

    title: str
    artist: str
    duration: float


@dataclass
class MediaItemAnalyzedData:
    """Parsed fields from a mediaItemAnalyzedData TSAF blob."""

    title_ids: list[MediaItemTitleID]
    bpm: float
    key_signature_index: int


@dataclass
class MediaItemUserData:
    """Parsed fields from a mediaItemUserData TSAF blob."""

    title_ids: list[MediaItemTitleID]
    automix_start_point: float | None
    automix_end_point: float | None
    end_point: float | None


# ---------------------------------------------------------------------------
# Convenience parsers
# ---------------------------------------------------------------------------


def parse_local_media_item_location(data: bytes) -> LocalMediaItemLocation:
    """Parse all known fields from a localMediaItemLocations TSAF blob.

    Structure: ADCMediaItemLocation
      titleIDs collection → ADCMediaItemTitleID (title, artist, duration)
      anonymous collection → "com.apple.iTunes:DIGITS" strings

    Args:
        data: Raw binary content of a localMediaItemLocations TSAF file.

    Returns:
        :class:`LocalMediaItemLocation` with all extracted fields.

    Raises:
        TSAFParseError: If any required field is missing or malformed.
    """
    doc = parse_tsaf(data)
    location = doc.entities[0]
    if not isinstance(location, VerboseEntity):
        raise TSAFParseError("Expected ADCMediaItemLocation as top-level entity")

    title_ids_field = next((f for f in location.fields if f.name == "titleIDs"), None)
    if not title_ids_field or not isinstance(title_ids_field.value, list):
        raise TSAFParseError("titleIDs field not found")
    title_id = title_ids_field.value[0]
    tid = {f.name: f.value for f in title_id.fields}

    apple_id_collection = next(
        (f.value for f in location.fields if f.name is None and isinstance(f.value, list)),
        None,
    )
    if not apple_id_collection:
        raise TSAFParseError("Apple Music ID field not found in data")
    apple_id_str = next(
        (s for s in apple_id_collection if isinstance(s, str) and s.startswith(APPLE_MUSIC_ID_PREFIX)),
        None,
    )
    if not apple_id_str:
        raise TSAFParseError("Apple Music ID field not found in data")
    digits = apple_id_str[len(APPLE_MUSIC_ID_PREFIX):]
    if not digits.isdigit():
        raise TSAFParseError(f"Expected decimal digits, got: {digits!r}")

    return LocalMediaItemLocation(
        apple_music_id=int(digits),
        title=tid["title"],
        artist=tid["artist"],
        duration=float(tid["duration"]),
    )


def parse_media_item_title_id(data: bytes) -> MediaItemTitleID:
    """Parse all known fields from a mediaItemTitleIDs TSAF blob.

    Structure: ADCMediaItemTitleID (title, artist, duration)

    Args:
        data: Raw binary content of a mediaItemTitleIDs TSAF file.

    Returns:
        :class:`MediaItemTitleID` with all extracted fields.

    Raises:
        TSAFParseError: If any required field is missing or malformed.
    """
    doc = parse_tsaf(data)
    title_id = doc.entities[0]
    if not isinstance(title_id, VerboseEntity):
        raise TSAFParseError("Expected ADCMediaItemTitleID as top-level entity")
    tid = {f.name: f.value for f in title_id.fields}
    return MediaItemTitleID(
        title=tid["title"],
        artist=tid["artist"],
        duration=float(tid["duration"]),
    )


def parse_media_item_analyzed_data(data: bytes) -> MediaItemAnalyzedData:
    """Parse all known fields from a mediaItemAnalyzedData TSAF blob.

    Structure: ADCMediaItemAnalyzedData (uuid, titleIDs, bpm, keySignatureIndex, ...)
      titleIDs collection → ADCMediaItemTitleID (title, artist, duration)

    Args:
        data: Raw binary content of a mediaItemAnalyzedData TSAF file.

    Returns:
        :class:`MediaItemAnalyzedData` with all extracted fields.

    Raises:
        TSAFParseError: If any required field is missing or malformed.
    """
    doc = parse_tsaf(data)
    analyzed = doc.entities[0]
    if not isinstance(analyzed, VerboseEntity):
        raise TSAFParseError("Expected ADCMediaItemAnalyzedData as top-level entity")

    title_ids_field = next((f for f in analyzed.fields if f.name == "titleIDs"), None)
    if not title_ids_field or not isinstance(title_ids_field.value, list):
        raise TSAFParseError("titleIDs field not found")

    ad = {f.name: f.value for f in analyzed.fields}
    return MediaItemAnalyzedData(
        title_ids=[
            MediaItemTitleID(
                title=tid["title"],
                artist=tid["artist"],
                duration=float(tid["duration"]),
            )
            for e in title_ids_field.value
            if isinstance(e, (VerboseEntity, CompactEntity))
            for tid in [{f.name: f.value for f in e.fields}]
        ],
        bpm=float(ad["bpm"]),
        key_signature_index=ad["keySignatureIndex"],
    )


def parse_media_item_user_data(data: bytes) -> MediaItemUserData:
    """Parse all known fields from a mediaItemUserData TSAF blob.

    Structure: ADCMediaItemUserData (uuid, anonymous collection → ADCMediaItemTitleID)
      Top-level ADCCuePoint entities carry automix times.

    Automix cue times are extracted from ``ADCCuePoint`` entities:

    - ``automix_start_point``: first float value from the first compact
      ``ADCCuePoint``
    - ``automix_end_point``: largest float value across all ``ADCCuePoint``
      entities

    Both are ``None`` when no cue points are present.

    Args:
        data: Raw binary content of a mediaItemUserData TSAF file.

    Returns:
        :class:`MediaItemUserData` with all extracted fields.

    Raises:
        TSAFParseError: If any required field is missing or malformed.
    """
    doc = parse_tsaf(data)
    user_data = doc.entities[0]
    if not isinstance(user_data, VerboseEntity):
        raise TSAFParseError("Expected ADCMediaItemUserData as top-level entity")

    title_id_collection = next(
        (f.value for f in user_data.fields if isinstance(f.value, list)),
        None,
    )
    if not title_id_collection:
        raise TSAFParseError("titleIDs collection not found in ADCMediaItemUserData")

    fm = {f.name: f.value for f in user_data.fields}

    return MediaItemUserData(
        title_ids=[
            MediaItemTitleID(
                title=tid["title"],
                artist=tid["artist"],
                duration=float(tid["duration"]),
            )
            for e in title_id_collection
            if isinstance(e, (VerboseEntity, CompactEntity))
            for tid in [{f.name: f.value for f in e.fields}]
        ],
        automix_start_point=fm.get("automixStartPoint"),
        automix_end_point=fm.get("automixEndPoint"),
        end_point=fm.get("endPoint"),
    )
