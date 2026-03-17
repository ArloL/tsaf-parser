"""TSAF binary format parser — public API.

High-level extraction functions that delegate to the structural parser in
:mod:`djay_tsaf_parser.tsaf`.
"""

from dataclasses import dataclass

from djay_tsaf_parser.tsaf import (
    CompactEntity,
    VerboseEntity,
    find_all_entities,
    find_field,
    parse_tsaf,
)

APPLE_MUSIC_ID_PREFIX = b"\x21\x08com.apple.iTunes:"


class TSAFParseError(Exception):
    """Raised when TSAF data cannot be parsed."""

    pass


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

    title: str
    artist: str
    duration: float
    bpm: float
    key_signature_index: int


@dataclass
class MediaItemUserData:
    """Parsed fields from a mediaItemUserData TSAF blob."""

    title: str
    artist: str
    duration: float
    automix_start_point: float | None
    automix_end_point: float | None


# ---------------------------------------------------------------------------
# Public extraction functions
# ---------------------------------------------------------------------------


def extract_apple_music_id(data: bytes) -> int:
    """Extract the Apple Music ID from a localMediaItemLocations TSAF blob.

    Searches for the ``com.apple.iTunes:`` field (type tag ``21 08``) and
    returns the decimal integer that follows.

    Args:
        data: Raw binary content of a localMediaItemLocations TSAF file.

    Returns:
        Apple Music ID as an integer.

    Raises:
        TSAFParseError: If the Apple Music ID field is not found or malformed.
    """
    offset = data.find(APPLE_MUSIC_ID_PREFIX)
    if offset == -1:
        raise TSAFParseError("Apple Music ID field not found in data")

    start = offset + len(APPLE_MUSIC_ID_PREFIX)
    end = data.index(b"\x00", start)
    digits = data[start:end].decode("ascii")

    if not digits.isdigit():
        raise TSAFParseError(f"Expected decimal digits, got: {digits!r}")

    return int(digits)


def extract_title(data: bytes) -> str:
    """Extract the track title.

    Args:
        data: Raw TSAF binary data.

    Returns:
        Track title as a string.

    Raises:
        TSAFParseError: If the title field is not found.
    """
    try:
        doc = parse_tsaf(data)
    except TSAFParseError:
        raise TSAFParseError("Field 'title' not found in data")
    value = find_field(doc.entities, "TitleID", "title")
    if not isinstance(value, str):
        raise TSAFParseError("Field 'title' not found in data")
    return value


def extract_artist(data: bytes) -> str:
    """Extract the artist name.

    Args:
        data: Raw TSAF binary data.

    Returns:
        Artist name as a string.

    Raises:
        TSAFParseError: If the artist field is not found.
    """
    try:
        doc = parse_tsaf(data)
    except TSAFParseError:
        raise TSAFParseError("Field 'artist' not found in data")
    value = find_field(doc.entities, "TitleID", "artist")
    if not isinstance(value, str):
        raise TSAFParseError("Field 'artist' not found in data")
    return value


def extract_duration(data: bytes) -> float:
    """Extract the track duration in seconds.

    Args:
        data: Raw TSAF binary data.

    Returns:
        Duration in seconds as a float.

    Raises:
        TSAFParseError: If the duration field is not found.
    """
    doc = parse_tsaf(data)
    value = find_field(doc.entities, "TitleID", "duration")
    if not isinstance(value, (int, float)):
        raise TSAFParseError("Field 'duration' not found in data")
    return float(value)


def extract_bpm(data: bytes) -> float:
    """Extract the BPM from a mediaItemAnalyzedData TSAF blob.

    Args:
        data: Raw binary content of a mediaItemAnalyzedData TSAF file.

    Returns:
        BPM as a float.

    Raises:
        TSAFParseError: If the bpm field is not found.
    """
    doc = parse_tsaf(data)
    value = find_field(doc.entities, "AnalyzedData", "bpm")
    if not isinstance(value, (int, float)):
        raise TSAFParseError("Field 'bpm' not found in data")
    return float(value)


def extract_key_signature_index(data: bytes) -> int:
    """Extract the key signature index from a mediaItemAnalyzedData TSAF blob.

    Args:
        data: Raw binary content of a mediaItemAnalyzedData TSAF file.

    Returns:
        Key signature index as an integer (0–255).

    Raises:
        TSAFParseError: If the keySignatureIndex field is not found.
    """
    doc = parse_tsaf(data)
    value = find_field(doc.entities, "AnalyzedData", "keySignatureIndex")
    if not isinstance(value, int):
        raise TSAFParseError("Field 'keySignatureIndex' not found in data")
    return value


# ---------------------------------------------------------------------------
# Convenience parsers
# ---------------------------------------------------------------------------


def parse_local_media_item_location(data: bytes) -> LocalMediaItemLocation:
    """Parse all known fields from a localMediaItemLocations TSAF blob.

    Args:
        data: Raw binary content of a localMediaItemLocations TSAF file.

    Returns:
        :class:`LocalMediaItemLocation` with all extracted fields.

    Raises:
        TSAFParseError: If any required field is missing or malformed.
    """
    return LocalMediaItemLocation(
        apple_music_id=extract_apple_music_id(data),
        title=extract_title(data),
        artist=extract_artist(data),
        duration=extract_duration(data),
    )


def parse_media_item_title_id(data: bytes) -> MediaItemTitleID:
    """Parse all known fields from a mediaItemTitleIDs TSAF blob.

    Args:
        data: Raw binary content of a mediaItemTitleIDs TSAF file.

    Returns:
        :class:`MediaItemTitleID` with all extracted fields.

    Raises:
        TSAFParseError: If any required field is missing or malformed.
    """
    return MediaItemTitleID(
        title=extract_title(data),
        artist=extract_artist(data),
        duration=extract_duration(data),
    )


def parse_media_item_analyzed_data(data: bytes) -> MediaItemAnalyzedData:
    """Parse all known fields from a mediaItemAnalyzedData TSAF blob.

    Args:
        data: Raw binary content of a mediaItemAnalyzedData TSAF file.

    Returns:
        :class:`MediaItemAnalyzedData` with all extracted fields.

    Raises:
        TSAFParseError: If any required field is missing or malformed.
    """
    return MediaItemAnalyzedData(
        title=extract_title(data),
        artist=extract_artist(data),
        duration=extract_duration(data),
        bpm=extract_bpm(data),
        key_signature_index=extract_key_signature_index(data),
    )


def parse_media_item_user_data(data: bytes) -> MediaItemUserData:
    """Parse all known fields from a mediaItemUserData TSAF blob.

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

    verbose_times: list[float] = []
    compact_times: list[float] = []

    for entity in find_all_entities(doc.entities, "CuePoint"):
        if isinstance(entity, VerboseEntity):
            for f in entity.fields:
                if f.name == "time" and isinstance(f.value, float):
                    verbose_times.append(f.value)
        elif isinstance(entity, CompactEntity):
            # Take the first float32 field from each compact cue entity
            for f in entity.fields:
                if isinstance(f.value, float):
                    compact_times.append(f.value)
                    break

    automix_start_point: float | None = compact_times[0] if compact_times else None
    all_times = verbose_times + compact_times
    automix_end_point: float | None = max(all_times) if all_times else None

    return MediaItemUserData(
        title=extract_title(data),
        artist=extract_artist(data),
        duration=extract_duration(data),
        automix_start_point=automix_start_point,
        automix_end_point=automix_end_point,
    )
