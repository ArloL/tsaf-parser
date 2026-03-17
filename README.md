# DJAY TSAF Encoding Parser

This is a python research project. The goal is to understand the TSAF binary
format as much as reasonable. TSAF is a binary format used by the dj-ing macOS
application [djay](https://www.algoriddim.com/djay-pro-mac).

## Tools

This project uses [uv](https://docs.astral.sh/uv/) to manage the Python version, virtualenv, and dependencies.

Tests are written in pytest.

## Test data

For easier exploration this project contains extracted binary blobs in `/data`.
There is data for four songs (prefix: guiboratto, happysong, just and
luvmaschine) for four different columns (suffix: localMediaItemLocations,
mediaItemAnalyzedData, mediaItemTitleIDs and mediaItemUserData).

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
  * Duration: ~372.6s (~6:12.6)
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

#### Header (20 bytes)

```
Offset 0-3:   "TSAF" magic
Offset 4-7:   version (0x00030003 = 196611)
Offset 8-11:  entity count (uint32 LE) — semantics unclear; does not match
              a simple count of top-level or all-depth entities in the body
Offset 12-15: unknown (always 0x00000000 in observed files)
Offset 16-19: unknown uint32 LE — varies per file (e.g. 8, 12, 13, 23, 25);
              may be a total field count or schema-element count
```

Entity stream starts at offset **20**. Every entity begins with `0x2B`.

#### Entity structure

**Verbose form** (first occurrence of each entity type, or schema-only declaration):
```
2B 08 EntityTypeName 00  ...fields...  00
```

- Entity marker: `0x2B`
- Form byte: `0x08` (verbose)
- Entity type name: UTF-8 string, null-terminated
- Fields follow immediately (see Field encoding below)
- Entity body ends at `0x00` terminator, after which optional parent
  cross-reference pairs (`0x05 id`) with id `< 0x10` may appear before the
  next `0x2B` entity marker

**Compact form** (subsequent occurrences of a type already seen in verbose form):
```
2B 05 FieldID TypeTag Value [05 FieldID TypeTag Value]...  00
```

- Form byte: `0x05` (compact)
- The first field's ID byte follows immediately (no `0x05` separator)
- Each subsequent field is preceded by a `0x05` separator byte
- Field ID: `0x10` + field_index — maps to the schema declared by the
  most recent verbose entity of that type
- Field IDs `< 0x10` are parent cross-references, not data fields; skip them

#### Field encoding: VALUE before FIELD_NAME

Verbose entities encode fields as:
```
TYPE_TAG  [padding]  VALUE  0x08  FIELD_NAME  0x00
```

The type tag byte comes first, then optional alignment-padding zero bytes,
then the value, then `0x08 + field name + 0x00`.

#### Numeric alignment padding

Numeric values (float32, int32, uint32 = 4 bytes; float64 = 8 bytes) are
stored at absolute file offsets that are aligned to their byte width. The
parser inserts zero-padding bytes between the type tag byte and the value
to satisfy this alignment.

Padding byte count for a value at cursor position `pos` (immediately after
the type tag byte):

```
pad = (byte_width - (pos % byte_width)) % byte_width
```

For example: if the type tag `0x13` (float32) is at absolute offset 22,
the value bytes start at offset 23. Since 23 % 4 = 3, padding =
(4 − 3) % 4 = 1 zero byte before the 4 value bytes.

This is **not** an escape mechanism — the zeros are purely alignment padding.

#### Type tags

| type tag | type | format |
|---|---|---|
| `0x08` | null-terminated string | `08 [string] 00` |
| `0x05` | int32 little-endian | `05 [pad] [4 bytes]` |
| `0x0B` | collection | `0B [pad] [4B count]` followed by collection body |
| `0x0D` | boolean flag | `0D` — implicit true; no value bytes |
| `0x0F` | uint8 | `0F [1 byte]` — no alignment |
| `0x13` | float32 little-endian | `13 [pad] [4 bytes]` |
| `0x15` | raw data block | `15 [pad] [4B length] [length bytes]` |
| `0x21` | Apple ID string | `21 08 [string] 00` — 2-byte prefix before cstring |
| `0x2E` | cue number marker | value IS the type byte itself (= 46); no further bytes |
| `0x30` | float64 little-endian | `30 [pad] [8 bytes]` |

#### Schema declarations vs data entities

Verbose entities serve two roles: schema-only declarations and data entities.

**Schema-only** (no field values — lists field names for subsequent compact encoding):
```
2B 08 EntityTypeName 00
  08 fieldName1 00
  08 fieldName2 00
  ...
  00
```
Identified by: after reading `0x08 + string`, the next byte is NOT `0x08`.
The string is a field name, not a string value.

**Data entity** (has actual field values):
```
2B 08 EntityTypeName 00
  TYPE_TAG [pad] VALUE  08 fieldName1 00
  TYPE_TAG [pad] VALUE  08 fieldName2 00
  ...
  00
```
Identified by: after reading a string value `0x08 + S + 0x00`, the next byte
IS `0x08` (beginning of the field name marker).

The first occurrence of each entity type registers its field name list as the
schema for that type, enabling compact encoding in later occurrences.

#### Collections

`0x0B [count]` introduces a collection of `count` items. The item type is
determined by the first byte after the count:

- `0x2B` → sub-entities; each starts with `0x2B` + form byte, parsed
  recursively
- `0x08` → schema field-name strings; read `count` × (`0x08` + cstring);
  registers field names for the current entity type
- `0x21` → Apple ID values; each is `0x21 0x08` + cstring (the Apple Music
  ID prefixed by `com.apple.iTunes:`)

After a collection field whose items are sub-entities, an optional `0x08 +
field-name + 0x00` follows to name the collection field itself.

#### Compact encoding — schema resolution

Compact entities reference their verbose schema by field index:
- Field ID `0x10` = first field from the verbose schema
- Field ID `0x11` = second field, etc.
- Field ID `< 0x10` = cross-reference to a parent entity; skip

The schema field order is fixed by the order in which field names appear in
the first verbose occurrence (or schema-only declaration) of each entity type.
This ordering can differ between files for the same entity type — for example,
`ADCCuePoint` in guiboratto declares `(time, number, endTime)` but in
luvmaschine declares `(time, endTime, number)`. This shifts all field IDs
beyond the first field.

#### Apple ID extraction

The Apple Music ID is stored inside an anonymous collection field of
`ADCMediaItemLocation`. Each item is an Apple ID string in the form:
```
21 08 63 6f 6d 2e 61 70 70 6c 65 2e 69 54 75 6e 65 73 3a [digits] 00
     \___________________________ com.apple.iTunes: ___________________/
```
Extract the decimal digit string after `com.apple.iTunes:` and convert to
uint64.

#### Known entity types

| Entity type | Appears in | Key fields |
|---|---|---|
| `ADCMediaItemLocation` | localMediaItemLocations | `uuid` (str), `titleIDs` (collection → `ADCMediaItemTitleID`), anonymous collection (Apple ID strings) |
| `ADCMediaItemTitleID` | all files (nested or top-level) | `uuid` (str), `title` (str), `artist` (str), `duration` (float32, seconds) |
| `ADCMediaItemAnalyzedData` | mediaItemAnalyzedData | `uuid` (str), `titleIDs` (collection → `ADCMediaItemTitleID`), `bpm` (float32), `keySignatureIndex` (uint8), `isStraightGrid` (boolean, not always present) |
| `ADCMediaItemUserData` | mediaItemUserData | `uuid` (str), anonymous collection (→ `ADCMediaItemTitleID`); cue points appear as top-level entities |
| `ADCCuePoint` | mediaItemUserData | `time` (float32, seconds), `endTime` (float32, -1.0 = absent), `number` (0x2E marker = 46) |
| `ADCAudioAlignmentFingerprint` | mediaItemUserData | anonymous raw data block (0x15, zlib-compressed) |

All entity types carry a `uuid` field (hex string, 32 chars) that identifies
the track consistently across files.

#### Automix cue times

Cue times are stored in `ADCCuePoint` entities in `mediaItemUserData`.

The verbose `ADCCuePoint` entity always contains the end-of-automix time in
its `time` field. Compact `ADCCuePoint` entities omit the first field of
the schema (`time` in guiboratto, `endTime` in luvmaschine) when it is the
same as the automix end time, and store the automix start time in the first
field that is present.

Extraction algorithm:
1. Collect `time` field values from verbose `ADCCuePoint` entities →
   `verbose_times`
2. Collect the first float value from each compact `ADCCuePoint` entity →
   `compact_times`
3. `automix_start_point` = `compact_times[0]` if any compact cue exists,
   else `None`
4. `automix_end_point` = `max(verbose_times + compact_times)` if any times
   exist, else `None`

The compact time field ID varies with schema order:
- guiboratto schema `(time, number, endTime)` → automix start is field `0x10`
  (`time`)
- luvmaschine schema `(time, endTime, number)` → automix start is field `0x11`
  (`endTime`, because `time` = end-of-automix is omitted from compact form)

For tracks without automix (happysong, just), no `ADCCuePoint` entities are
present in the file at all.

#### ADCCuePoint compact encoding example — guiboratto

Schema order: `(time, number, endTime)` → IDs `0x10`, `0x11`, `0x12`

Compact entity encoding the automix start time 17.475s:
```
2B 05                    -- entity marker + compact form
   10 13 [pad] [4B]      -- field 0x10 (time):   float32 = 17.475
   05 11 2E              -- field 0x11 (number):  0x2E = 46
   05 12 00              -- field 0x12 (endTime): 0 (absent)
   00                    -- entity terminator
```

#### ADCCuePoint compact encoding example — luvmaschine

Schema order: `(time, endTime, number)` → IDs `0x10`, `0x11`, `0x12`

Compact entity encoding the automix start time 54.735s:
```
2B 05                    -- entity marker + compact form
   11 13 [pad] [4B]      -- field 0x11 (endTime): float32 = 54.735
   05 12 13 [pad] [4B]   -- field 0x12 (number):  float32 = -1.0
   05 00                 -- cross-ref (id < 0x10), skipped
   2E                    -- 0x2E type tag (value = 46, no bytes)
   00                    -- entity terminator
```

Note that `time` (field `0x10`) is absent from the compact form entirely —
the verbose entity for this file's end-of-automix stores the same value.
