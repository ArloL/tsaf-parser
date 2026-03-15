from djay_tsaf_parser.apple_id_extractor import parse_tsaf_file


def test_extract_guiboratto_apple_id():
    result = parse_tsaf_file("data/guiboratto-localMediaItemLocations.bin")
    assert result["apple_music_id"] == 8986230555104447322


def test_extract_happysong_apple_id():
    result = parse_tsaf_file("data/happysong-localMediaItemLocations.bin")
    assert result["apple_music_id"] == 15276055944141716431


def test_invalid_magic_raises():
    from djay_tsaf_parser.apple_id_extractor import extract_apple_music_id

    result = extract_apple_music_id(b"XXXX" + b"\x00" * 100)
    assert result is None
