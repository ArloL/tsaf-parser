"""TSAF binary format parser."""

APPLE_MUSIC_ID_PREFIX = b"\x21\x08com.apple.iTunes:"


class TSAFParseError(Exception):
    """Raised when TSAF data cannot be parsed."""

    pass


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
