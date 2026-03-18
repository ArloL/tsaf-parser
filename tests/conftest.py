"""Shared fixtures for dynamic test-data discovery."""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

DATA_DIR = Path("data/bin")


@dataclass
class TrackFixture:
    """Expected values loaded from a track's JSON metadata file."""

    key: str
    title: str
    artist: str
    duration: float
    apple_music_id: int
    bpm: float
    key_signature_index: int
    manual_bpm: float | None = None

    def bin_path(self, column: str) -> Path:
        return DATA_DIR / f"{self.key}-{column}.bin"

    def load_bin(self, column: str) -> bytes:
        return self.bin_path(column).read_bytes()


def _discover_tracks() -> list[TrackFixture]:
    """Find all *.json metadata files in data/ and build TrackFixture instances."""
    tracks = []
    for json_path in sorted(DATA_DIR.glob("*.json")):
        meta = json.loads(json_path.read_text())
        key = json_path.stem
        tracks.append(
            TrackFixture(
                key=key,
                title=meta["title"],
                artist=meta["artist"],
                duration=meta["duration"],
                apple_music_id=meta["appleMusicId"],
                bpm=meta["bpm"],
                key_signature_index=meta["keySignatureIndex"],
                manual_bpm=meta.get("manualBpm"),
            )
        )
    return tracks


_ALL_TRACKS = _discover_tracks()


def _has_bin(track: TrackFixture, column: str) -> bool:
    return track.bin_path(column).exists()


@pytest.fixture(params=_ALL_TRACKS, ids=lambda t: t.key)
def track(request: pytest.FixtureRequest) -> TrackFixture:
    """Parametrized fixture yielding every discovered track."""
    return request.param


@pytest.fixture(
    params=[t for t in _ALL_TRACKS if _has_bin(t, "mediaItemTitleIDs")],
    ids=lambda t: t.key,
)
def track_with_title_ids(request: pytest.FixtureRequest) -> TrackFixture:
    return request.param


@pytest.fixture(
    params=[t for t in _ALL_TRACKS if _has_bin(t, "localMediaItemLocations")],
    ids=lambda t: t.key,
)
def track_with_location(request: pytest.FixtureRequest) -> TrackFixture:
    return request.param


@pytest.fixture(
    params=[t for t in _ALL_TRACKS if _has_bin(t, "mediaItemAnalyzedData")],
    ids=lambda t: t.key,
)
def track_with_analyzed_data(request: pytest.FixtureRequest) -> TrackFixture:
    return request.param


@pytest.fixture(
    params=[t for t in _ALL_TRACKS if _has_bin(t, "mediaItemUserData")],
    ids=lambda t: t.key,
)
def track_with_user_data(request: pytest.FixtureRequest) -> TrackFixture:
    return request.param
