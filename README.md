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
  * Duration: ~367.5s (~6:07.5)
  * Automix Start: ~17.475s (~0:17.5)
  * Automix End: ~272.826s (~4:32.8)
  * BPM: ~125.0
  * Key Index: 15
2. happysong
  * Artist: Imogen Heap
  * Title: The Happy Song
  * Apple Music ID: 15276055944141716431
  * Duration: ~158.0s (~2:38)
  * Automix Start: none
  * Automix End: none
  * BPM: ~82.0
  * Key Index: 6
3. just
  * Artist: Bicep
  * Title: Just (Original Mix)
  * Apple Music ID: 14110461239496945263
  * Duration: ~372.5s (~6:12.5)
  * Automix Start: none
  * Automix End: none
  * BPM: ~120.0
  * Key Index: 11
4. luvmaschine
  * Artist: Luvless
  * Title: Luvmaschine Original Mix
  * Apple Music ID: 16256298393022529679
  * Duration: ~414.8s (~6:54.8)
  * Automix Start: ~54.8s (~0:54.8)
  * Automix End: ~378.9s (~6:18.9)
  * BPM: ~114.0
  * Key Index: 3

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

Example from ADCCuePoint compact entity (guiboratto — schema order: time, number, endTime):
```
2B 05 10 13 00 00 50 cc 8b 41  -- entity start + field 0 (time): float
    05 11 2e                       -- field 1 (number): 0x2e = 46
    05 12 00                       -- field 2 (endTime): 0
```

Example from ADCCuePoint compact entity (luvmaschine — schema order: time, endTime, number):
```
2B 05 11 13 00 00 00 b4 f0 5a 42  -- entity start + field 1 (endTime): float
    05 12 13 00 00 00 80 bf        -- field 2 (number): float
```

**Note:** The field ordering in the verbose schema declaration determines compact field IDs and can vary between files for the same entity type. For ADCCuePoint, some files declare `(time, number, endTime)` while others declare `(time, endTime, number)`, shifting the compact IDs of subsequent fields.

#### Apple ID extraction

Search for `com.apple.iTunes:` prefix. The format is:
```
21 08 63 6f 6d 2e 61 70 70 6c 65 2e 69 54 75 6e 65 73 3a [digits] 00
```
Extract digits as decimal string, convert to int64.

#### Automix cue times

Times are stored in `ADCCuePoint` entities in `mediaItemUserData`:

1. Extract `time` values from verbose `ADCCuePoint` entities (scanning for `\x08time\x00`)
2. Extract float32 values from compact `ADCCuePoint` entities (scanning for `\x2b\x05\x{N}\x13`)
3. First compact ADCCuePoint float → automix start time (e.g., 17.475s = 0:17.5)
4. Largest float across all cue point entities → automix end time (e.g., 272.826s = 4:32.8)

The compact time field ID (`N`) is `0x10` when time is the first declared field in the schema, or `0x11` when a different field precedes it (e.g., luvmaschine, where endTime is declared before number). The "take last 4 bytes" strategy handles both with or without the escape byte.

For tracks without automix, no ADCCuePoint entities exist or no times are found.
