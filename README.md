# DJAY TSAF Encoding Parser

This is a python research project. The goal is to understand the TSAF binary
format as much as reasonable. TSAF is a binary format used by the dj-ing macOS
application [djay](https://www.algoriddim.com/djay-pro-mac).

## Tools

This project uses [uv](https://docs.astral.sh/uv/) to manage the Python version, virtualenv, and dependencies.

Tests are written in pytest.

## Test data

For easier exploration this project contains extracted binary blobs in `/data`.
There is data for two songs (prefix: guiboratto and happysong) for four
different columns (suffix: localMediaItemLocations, mediaItemAnalyzedData,
mediaItemTitleIDs and mediaItemUserData).

1. guiboratto
  * Artist: Gui Boratto
  * Track: Arquipelago (Original Mix)
  * Apple Music ID: 8986230555104447322
  * Duration: 367.5s (6:07.5)
  * Automix Start: 17.475s (0:17.5)
  * Automix End: 272.826s (4:32.8)
2. happysong
  * Artist: Imogen Heap
  * Title: The Happy Song
  * Apple Music ID: 15276055944141716431
  * Duration: 158.0s (2:38)
  * Automix Start: none
  * Automix End: none

## Format description

**Overview**: TSAF is a binary format. It contains object structures.
Everything in this description is the result of exploration. That means
it might be misinterpreting something and mislead further exploration.
Sometimes the solution is that this description is wrong.
**If you realize something here is not quite correct, mark it as such**

#### Header (16 bytes)

```
Offset 0-3:   "TSAF" magic
Offset 4-7:   version (0x00030003 = 196611)
Offset 8-11:  entity count (uint32 LE)
Offset 12-15: unknown (often 0x00000000, sometimes other values)
```

Body starts at offset 16.

#### Entity structure

**Verbose form** (first occurrence of each entity type):
```
2B 08 EntityTypeName 00 [TYPE_TAG VALUE]... 08 FieldName 00 [TYPE_TAG VALUE] 08 FieldName 00...
```

- Entity marker: `0x2B`
- Type indicator: `0x08` (verbose)
- Entity type name: UTF-8 string, null-terminated

**Compact form** (subsequent occurrences, references verbose schema):
```
2B 05 FieldID [TYPE_TAG VALUE]... [05 FieldID [TYPE_TAG VALUE]]...
```

- Type indicator: `0x05` (compact)
- Field ID: 0x10 + field_index (0x10 = first field, 0x11 = second, etc.)

#### Field order: VALUE before FIELD_NAME

The structure is: `TYPE_TAG + VALUE + 0x08 + FIELD_NAME + 0x00`

Field name markers are always `08 FieldName 00`. Type tag precedes the value directly.

#### Type tags

| type tag | type | format |
|---|---|---|
| `0x08` | null-terminated string | `08 [string] 00` |
| `0x05` | int32 little-endian | `05 [4 bytes]` |
| `0x0B` | uint32 little-endian | `0B [4 bytes]` — often collection count |
| `0x13` | float32 little-endian | `13 [4 bytes]` |
| `0x13 0x00` | float32 with flag | `13 00 [4 bytes]` — flag byte 0x00 |
| `0x21 0x08` | Apple ID string | `21 08 [string] 00` — special 2-byte prefix |
| `0x2E` | cue number | value IS the type byte itself (=46) |
| `0x0F` | uint8 | single byte value |
| `0x30` | float64 | `30 [8 bytes LE]` |

#### The 0x00 escape byte

Type tags have two forms:
- **5-byte:** `TAG [4B value]` — normal case
- **6-byte:** `TAG 0x00 [4B value]` — when value bytes contain `0x08` or start with `0x00`

This escape mechanism ensures field boundaries are unambiguous.

#### Schema declarations

First entity of each type declares available fields without values. Example from `mediaItemUserData`:
```
2B 08 ADCMediaItemUserData 00
  08 automixStartPoint 00
  08 playCount 00
  08 audioAlignmentFingerprint 00
  08 titleIDs 00
  08 automixEndPoint 00
  08 endPoint 00
  08 userChangedCloudKeys 00
```

#### Collections

`0x0B [count]` declares a collection with count nested entities. Each entity starts with `0x2B`.

#### Compact encoding

Compact entities reference the verbose schema by field ID:
- Field ID 0x10 = first field from verbose definition
- Field ID 0x11 = second field, etc.
- Field ID < 0x10 = cross-reference to parent entity (not a data field)

**"Take last N bytes" strategy:** strip the type tag byte, take the last N bytes (4 for float32/uint32, 1 for uint8, 8 for float64) as the value. This handles variable padding without needing to understand the padding rules.

Example from ADCCuePoint compact entity:
```
2B 05 10 13 00 00 50 cc 8b 41  -- entity start + field 0 (time): float
    05 11 2e                       -- field 1 (number): 0x2e = 46
    05 12 00                       -- field 2 (endTime): 0
```

#### Apple ID extraction

Search for `com.apple.iTunes:` prefix. The format is:
```
21 08 63 6f 6d 2e 61 70 70 6c 65 2e 69 54 75 6e 65 73 3a [digits] 00
```
Extract digits as decimal string, convert to int64.

#### Automix cue times

Times are stored in `ADCCuePoint` entities in `mediaItemUserData`:

1. Extract `time` values from `ADCCuePoint` entities (both verbose and compact)
2. First compact ADCCuePoint → automix start time (e.g., 17.475s = 0:17.5)
3. Largest `time` value → automix end time (e.g., 272.826s = 4:32.8)

For tracks without automix, no ADCCuePoint entities exist or no times are found.
