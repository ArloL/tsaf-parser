APPLE_ID_PREFIX = b"com.apple.iTunes:"
APPLE_ID_TYPE_TAG = b"\x21\x08"


def extract_apple_music_id(data: bytes) -> int | None:
    idx = 0
    while idx < len(data) - len(APPLE_ID_TYPE_TAG) - len(APPLE_ID_PREFIX) - 4:
        if data[idx : idx + 2] == APPLE_ID_TYPE_TAG:
            prefix_start = idx + 2
            if (
                data[prefix_start : prefix_start + len(APPLE_ID_PREFIX)]
                == APPLE_ID_PREFIX
            ):
                digits_start = prefix_start + len(APPLE_ID_PREFIX)
                digits_end = data.index(b"\x00", digits_start)
                digits = data[digits_start:digits_end].decode("ascii")
                return int(digits)
        idx += 1
    return None


def parse_tsaf_file(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        data = f.read()

    if len(data) < 16:
        raise ValueError("File too small to be valid TSAF")

    magic = data[:4]
    if magic != b"TSAF":
        raise ValueError(f"Invalid magic: {magic}")

    apple_id = extract_apple_music_id(data)

    return {
        "apple_music_id": apple_id,
    }
