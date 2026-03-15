"""TSAF binary format parser."""

import struct
from dataclasses import dataclass

APPLE_MUSIC_ID_PREFIX = b"\x21\x08com.apple.iTunes:"
STRING_TYPE_TAG = b"\x08"


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


def _extract_string_field(data: bytes, field_name: str) -> str:
    """Extract a string value for the given field name.

    Scans backwards from the ``\\x08<field_name>\\x00`` marker to find the
    preceding null-terminated string value.

    Args:
        data: Raw TSAF binary data.
        field_name: Name of the field to extract.

    Returns:
        Decoded UTF-8 string value.

    Raises:
        TSAFParseError: If the field is not found or malformed.
    """
    marker = STRING_TYPE_TAG + field_name.encode() + b"\x00"
    marker_offset = data.find(marker)
    if marker_offset == -1:
        raise TSAFParseError(f"Field '{field_name}' not found in data")

    # The byte immediately before the marker is the null terminator of the value.
    null_offset = marker_offset - 1
    if null_offset < 1 or data[null_offset] != 0x00:
        raise TSAFParseError(f"Expected null terminator before field '{field_name}'")

    # Scan back to find the string type tag (0x08) that opens the value.
    tag_offset = data.rindex(STRING_TYPE_TAG, 0, null_offset)
    return data[tag_offset + 1 : null_offset].decode("utf-8")


def _extract_float32_field(data: bytes, field_name: str) -> float:
    """Extract a float32 value for the given field name.

    Uses the "take last 4 bytes" strategy: the 4 bytes immediately before
    ``\\x08<field_name>\\x00`` are the little-endian float32 value, regardless
    of whether the optional escape byte (``0x00``) is present.

    Args:
        data: Raw TSAF binary data.
        field_name: Name of the field to extract.

    Returns:
        Float32 value.

    Raises:
        TSAFParseError: If the field is not found.
    """
    marker = STRING_TYPE_TAG + field_name.encode() + b"\x00"
    marker_offset = data.find(marker)
    if marker_offset == -1:
        raise TSAFParseError(f"Field '{field_name}' not found in data")

    value_bytes = data[marker_offset - 4 : marker_offset]
    (value,) = struct.unpack("<f", value_bytes)
    return value


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
    """Extract the track title from a localMediaItemLocations TSAF blob.

    Args:
        data: Raw binary content of a localMediaItemLocations TSAF file.

    Returns:
        Track title as a string.

    Raises:
        TSAFParseError: If the title field is not found.
    """
    return _extract_string_field(data, "title")


def extract_artist(data: bytes) -> str:
    """Extract the artist name from a localMediaItemLocations TSAF blob.

    Args:
        data: Raw binary content of a localMediaItemLocations TSAF file.

    Returns:
        Artist name as a string.

    Raises:
        TSAFParseError: If the artist field is not found.
    """
    return _extract_string_field(data, "artist")


def extract_duration(data: bytes) -> float:
    """Extract the track duration (seconds) from a localMediaItemLocations TSAF blob.

    Args:
        data: Raw binary content of a localMediaItemLocations TSAF file.

    Returns:
        Duration in seconds as a float.

    Raises:
        TSAFParseError: If the duration field is not found.
    """
    return _extract_float32_field(data, "duration")


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
