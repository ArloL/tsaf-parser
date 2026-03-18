# DJAY TSAF Binary Format

TSAF is a binary format used by the DJ-ing macOS application
[djay](https://www.algoriddim.com/djay-pro-mac). This documents the
format based on reverse-engineering exploration.

## Sample data

Extracted binary blobs are in two directories:

- `/data` — hand-picked reference tracks (4 songs, used for hardcoded tests)
- `/data/bin` — bulk export (~8,000 tracks, each with a `.json` metadata file
  and one or more `.bin` column files; used for dynamic data-driven tests)

File naming convention: `{key}-{column}.bin` and `{key}.json`, where `key` is
a hex hash and `column` is one of `localMediaItemLocations`,
`mediaItemAnalyzedData`, `mediaItemTitleIDs`, or `mediaItemUserData`.

Reference tracks in `/data`:

1. d8a452ad23698cb4076d1baed024844b
   * Artist: Gui Boratto
   * Track: Arquipelago (Original Mix)
   * Apple Music ID: 8986230555104447322
   * Duration: ~367.5s (~6:07.5)
   * Automix Start: ~17.475s (~0:17.5)
   * Automix End: ~272.826s (~4:32.8)
   * BPM: ~125.0
   * Key Index: 15
2. f6fa142fbda6a56deb6dfa71dbef389e
   * Artist: Imogen Heap
   * Title: The Happy Song
   * Apple Music ID: 15276055944141716431
   * Duration: ~158.0s (~2:38)
   * Automix Start: none
   * Automix End: none
   * BPM: ~82.0
   * Key Index: 6
3. dc11bf9b77216b8c5f295030613d72f1
   * Artist: Bicep
   * Title: Just (Original Mix)
   * Apple Music ID: 14110461239496945263
   * Duration: ~372.6s (~6:12.6)
   * Automix Start: none
   * Automix End: none
   * BPM: ~120.0
   * Key Index: 11
4. df6376b59fbc6e4fd56d55f3e64b5d2e
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
- Entity body ends with an explicit `0x00` terminator, after which optional
  parent cross-reference pairs `0x05 id` (id `< 0x10`) may appear
- A `0x2B` byte encountered inside a verbose entity body (before the `0x00`
  terminator) introduces an **inline sub-entity** — a child entity whose
  cross-reference IDs map it to a field of the parent.
  The parent's body continues after all inline sub-entities and ends with
  its own `0x00` terminator

**Compact form** (subsequent occurrences of a type already seen in verbose form):
```
2B 05 FieldID TypeTag Value [05 FieldID TypeTag Value]...  [00]
```

- Form byte: `0x05` (compact)
- The first field's ID byte follows immediately (no `0x05` separator)
- Each subsequent field is preceded by a `0x05` separator byte
- Field ID: `0x10` + field_index — maps to the schema declared by the
  most recent verbose entity of that type
- Field IDs `< 0x10` are parent cross-references, not data fields; skip them
- Entity body ends with an explicit `0x00` terminator (after which optional
  parent cross-reference pairs `0x05 id` with id `< 0x10` may appear),
  **or** implicitly when the next `0x2B` entity marker is encountered
  (compact entities inside a parent can terminate this way)

#### Field encoding: VALUE before FIELD_NAME

Verbose entities encode fields as:
```
TYPE_TAG  [padding]  VALUE  0x08  FIELD_NAME  0x00
```

The type tag byte comes first, then optional alignment-padding zero bytes,
then the value, then `0x08 + field name + 0x00`.

#### Numeric alignment padding

Numeric values (float32, int32, uint32 = 4 bytes; float64 = 8 bytes) are
stored at absolute file offsets that are aligned to their byte width.
Zero-padding bytes appear between the type tag byte and the value to
satisfy this alignment.

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
| `0x00` | absent/null sentinel | `00` — no value bytes; value = 0 |
| `0x05` | int32 little-endian (sign unconfirmed — all observed values are non-negative; verbose-entity parser uses signed, compact-entity parser uses unsigned) | `05 [pad] [4 bytes]` |
| `0x08` | null-terminated string | `08 [string] 00` |
| `0x0B` | collection | `0B [pad] [4B count]` followed by collection body |
| `0x0D` | boolean flag | `0D` — implicit true; no value bytes |
| `0x0F` | uint8 | `0F [1 byte]` — no alignment |
| `0x13` | float32 little-endian | `13 [pad] [4 bytes]` |
| `0x15` | raw data block | `15 [pad] [4B length] [length bytes]` |
| `0x1A` | collection (variant) | `1A [pad] [4B count]` — same structure as `0x0B`; observed in some `ADCMediaItemUserData` schema blocks instead of `0x0B` (best guess: equivalent semantics, unknown why the tag differs) |
| `0x21` | Apple ID string | `21 08 [string] 00` — 2-byte prefix before cstring |
| `0x2D` | compact integer 1 | `2D` — no value bytes; value = 1 (best guess based on `keySignatureIndex` = 1 tracks) |
| `0x2E` | compact integer 0 | `2E` — no value bytes; value = 0 (best guess — confirmed across ~280 tracks where `keySignatureIndex` = 0) |
| `0x30` | float64 little-endian | `30 [pad] [8 bytes]` |

**Compact integer encoding (best guess):** Small integer values may use
dedicated type tags that encode the value with no additional data bytes.
The known cases are `0x00` (value 0, also serves as absent/null sentinel),
`0x2D` (value 1), and `0x2E` (value 0). The relationship between `0x00`
and `0x2E` — both representing 0 — is unclear; `0x00` may carry "absent"
semantics while `0x2E` carries "explicit zero" semantics. More data points
are needed to confirm whether additional tags in this range encode other
small integers.

#### Schema declarations vs data entities

Verbose entities serve two roles: schema-only declarations and data entities.

**Schema-only** (no field values — lists field names for subsequent compact encoding):

When multiple field names are declared, they are wrapped in a `0x0B`
(or `0x1A`) collection (see Collections below). A single trailing field
name may appear as a standalone `0x08 + cstring` after the collection
(as seen in `ADCMediaItemUserData`). The simplified form below only
applies when a single field name is present:
```
2B 08 EntityTypeName 00
  08 fieldName 00
  00
```
Identified by: after reading `0x08 + string`, the next byte is NOT `0x08`.
The string is a field name, not a string value. (When multiple schema names
are needed, they appear inside a `0x0B` collection, avoiding the ambiguity
of consecutive `0x08` strings.)

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

The first occurrence of each entity type establishes the field name list as
the schema for that type, enabling compact encoding in later occurrences.

#### Collections

`0x0B [count]` (or `0x1A [count]`) introduces a collection of `count` items.
The item type is determined by the first byte after the count:

- `0x2B` → sub-entities; each starts with `0x2B` + form byte (recursive
  structure)
- `0x08` → schema field-name strings; `count` × (`0x08` + cstring);
  declares field names for the current entity type
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
`ADCCuePoint` in guiboratto declares `(time, number)` but in luvmaschine
declares `(time, endTime, number)`. The guiboratto schema does not include
`endTime` — compact entities in that file reference field `0x12` (index 2)
which is out of the declared schema range and receives no name. This shifts
all field IDs beyond the first field.

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
| `ADCMediaItemTitleID` | all files (nested or top-level) | `uuid` (str), `title` (str), `artist` (str, may be absent for tracks without artist metadata e.g. YouTube imports), `duration` (float32, seconds) |
| `ADCMediaItemAnalyzedData` | mediaItemAnalyzedData | `uuid` (str), `titleIDs` (collection → `ADCMediaItemTitleID`), `bpm` (float32), `keySignatureIndex` (uint8 `0x0F` or compact integer `0x2D`/`0x2E`), `isStraightGrid` (boolean, not always present) |
| `ADCMediaItemUserData` | mediaItemUserData | schema block declares field names (varies per file); `titleIDs` (anonymous collection → `ADCMediaItemTitleID`); `automixStartPoint`, `automixEndPoint`, `endPoint` (float32, only when cues present); `playCount`, `colorIndex`, `audioAlignmentFingerprint`, `userChangedCloudKeys`; inline children: `ADCCuePoint`, `ADCAudioAlignmentFingerprint` |
| `ADCCuePoint` | mediaItemUserData (inline child of `ADCMediaItemUserData`) | cross-ref encodes `xref−2 = parent schema index` identifying which `ADCMediaItemUserData` field this entity provides; `time` (float32, seconds), `endTime` (float32, -1.0 = absent; declared in luvmaschine schema only), `number` (compact integer 0 via `0x2E` in guiboratto at field `0x11`; float32 = -1.0 in luvmaschine at field `0x12` — the named `number` field at schema index 2; the unnamed extra fields beyond the schema are `0x13` and `0x14`); field order and schema vary per file |
| `ADCAudioAlignmentFingerprint` | mediaItemUserData (inline child of `ADCMediaItemUserData`) | anonymous raw data block (0x15, zlib-compressed) |

All entity types carry a `uuid` field (hex string, 32 chars) that identifies
the track consistently across files.

#### ADCMediaItemUserData inline children

`ADCMediaItemUserData` contains inline sub-entities (`ADCCuePoint`,
`ADCAudioAlignmentFingerprint`) within its body. After the `titleIDs`
collection, inline children appear as `0x2B`-prefixed entities before the
parent's final `0x00` terminator.

The field names present in the schema block vary per file. Most files
use `0x0B` for the schema collection, but some use `0x1A` instead
(with fewer fields declared in the collection and more as standalone
`0x08 + cstring` entries after it):

| Field name | guiboratto | luvmaschine | just | happysong |
|---|---|---|---|---|
| `automixStartPoint` | ✓ | ✓ | — | — |
| `automixEndPoint` | ✓ | ✓ | — | — |
| `endPoint` | ✓ | ✓ | — | — |
| `playCount` | ✓ | ✓ | ✓ | — |
| `colorIndex` | — | ✓ | ✓ | — |
| `audioAlignmentFingerprint` | ✓ | ✓ | ✓ | — |
| `titleIDs` | ✓ | ✓ | ✓ | — |
| `userChangedCloudKeys` | ✓ | ✓ | ✓ | — |

The `titleIDs` collection in this entity is **anonymous** (no field name
follows the collection in the binary). The `ADCMediaItemTitleID` inside it
carries a cross-ref where `xref − 2` resolves to the `titleIDs` schema
index, confirming it provides the `titleIDs` field (see Cross-reference IDs).

#### Cross-reference IDs

Entities that logically belong to a parent entity carry cross-reference bytes
(`0x05 id`, id < 0x10). The ID encodes which **field of the parent** this
child entity provides, using the formula:

```
parent_field_index = xref_id - 2
```

where `parent_field_index` is the 0-based index into the parent entity's
schema name list. The IDs vary per file because the **schema name order**
varies per file — but `xref - 2` always resolves to the correct field name.

**Why subtract 2?** Best-guess interpretation based on observed data: the
cross-ref ID space reserves two slots before the schema field indices:

| Cross-ref ID | Meaning (best guess) | Evidence |
|---|---|---|
| 0 | Reserved / null | Never observed in any file |
| 1 | Collection membership marker? | Always present (pre-field) on `ADCMediaItemTitleID` sub-entities inside collections; never on inline children (`ADCCuePoint`) or top-level entities. Purpose unclear |
| 2 | UUID inheritance marker (pre-field only in observed data) | Always present as a **pre-field** xref on `ADCMediaItemTitleID` sub-entities. Applying the `xref − 2` formula gives schema index 0 = `uuid`, but in the pre-field position this is best understood as entity-level metadata (UUID inheritance), not as a parent field binding — consistent with the fact that pre-field xrefs 1 and 2 are described in the structural-positions section as metadata rather than bindings. Sub-entities that carry this xref omit their own `uuid` field; the xref likely signals that they share the parent's UUID |
| 3+ | Subsequent schema fields | Used for parent field binding (e.g. `titleIDs`, `automixStartPoint`, `endPoint`) |

Cross-refs also appear in **two structural positions** within an entity,
which may have different semantics (best guess — this is not confirmed):

- **Pre-field** (right after the type name, before data fields): IDs 1
  and 2 — found on collection sub-entities (`ADCMediaItemTitleID`).
  These are entity-level metadata, not parent field bindings. Pre-field
  xref=2 specifically serves as a UUID inheritance marker (see table above);
  pre-field xref=1 marks collection membership. Neither encodes a parent
  field assignment.
- **Post-terminator** (after the `0x00` body terminator): IDs 2+ — found on
  both collection sub-entities and inline children. These encode parent
  field bindings (using `xref − 2 = schema_index`).

When resolving a sub-entity's parent field, only cross-ref IDs that fall
within the parent's schema range (i.e. `0 <= xref - 2 < schema_length`)
identify a parent field. Pre-field xrefs 1 and 2 on collection sub-entities
do not resolve to a parent field binding for inline children (which only
have post-terminator xrefs), and xref 1 always falls outside the schema
range (index −1).

Supporting evidence for UUID inheritance:
- Top-level `ADCMediaItemTitleID` (in mediaItemTitleIDs): has its own `uuid`
  field, **no cross-refs**
- Sub-entity `ADCMediaItemTitleID` (inside any parent): **omits** `uuid`
  field, has pre-field `xref=2` → parent's `schema[0]` = `uuid`
- The same UUID is shared across all entity types for a given track

Example (guiboratto `ADCMediaItemUserData` schema):

```
index 0: uuid              (+ 2 = xref 2) ← ADCMediaItemTitleID pre-field ref
index 1: automixStartPoint (+ 2 = xref 3) ← compact ADCCuePoint provides this
index 2: playCount         (+ 2 = xref 4)
index 3: audioAlignmentFingerprint (+ 2 = xref 5)
index 4: titleIDs          (+ 2 = xref 6) ← ADCMediaItemTitleID post-term ref
index 5: automixEndPoint   (+ 2 = xref 7) ← compact ADCCuePoint provides this
index 6: endPoint          (+ 2 = xref 8) ← verbose ADCCuePoint provides this
index 7: userChangedCloudKeys (+ 2 = xref 9)
```

Cross-refs on verbose entities appear **after** the `0x00` body terminator
(for parent field binding) and optionally **before** data fields (for
entity-level metadata like IDs 1 and 2).
Cross-refs on compact entities appear **inside** the field list as `0x05 id`
where id < 0x10, interleaved with normal `0x05` field-separator bytes
(which have id ≥ 0x10).

`ADCAudioAlignmentFingerprint` does not carry an observed cross-ref; it may
terminate differently or its cross-ref is not yet located.

#### Automix cue times

`ADCCuePoint` entities appear as inline children of `ADCMediaItemUserData`.
Each carries a cross-reference ID that encodes which field of the parent
it provides (via `xref - 2 = schema_index`). The cross-ref — not whether
the entity is verbose or compact — determines which field it maps to.

The three cue-related fields (`automixStartPoint`, `automixEndPoint`,
`endPoint`) are declared in the `ADCMediaItemUserData` schema block for tracks
that have automix set. Tracks without automix (happysong, just) have no
`ADCCuePoint` entities and these fields are absent from the schema.

The `ADCCuePoint` schema varies per file:
- guiboratto: `(time, number)` — IDs `0x10`, `0x11`; field `0x12` (index 2) is out of schema range
- luvmaschine: `(time, endTime, number)` — IDs `0x10`, `0x11`, `0x12`

#### ADCCuePoint compact encoding example — guiboratto

Schema order: `(time, number)` → IDs `0x10`, `0x11`; index 2 (`0x12`) unnamed

Compact entity providing `automixStartPoint` (xref 3 → schema index 1):
```
2B 05                    -- entity marker + compact form
   10 13 [pad] [4B]      -- field 0x10 (time):    float32 = 17.475
   05 11 2E              -- field 0x11 (number):   compact integer 0
   05 12 00              -- field 0x12 (unnamed):  type 0x00 = 0 (absent)
   05 03                 -- cross-ref id=3 (3-2=1 → automixStartPoint)
                         -- terminates on 0x2B (next inline sibling)
```

#### ADCCuePoint compact encoding example — luvmaschine

Schema order: `(time, endTime, number)` → IDs `0x10`, `0x11`, `0x12`; indices 3+ unnamed

Compact entity providing `automixStartPoint` (xref 8 → schema index 6):
```
2B 05                    -- entity marker + compact form
   11 13 [pad] [4B]      -- field 0x11 (endTime):  float32 = 54.735
   05 12 13 [pad] [4B]   -- field 0x12 (number):   float32 = -1.0
   05 13 2E              -- field 0x13 (unnamed):   compact integer 0
   05 14 00              -- field 0x14 (unnamed):   type 0x00 = 0
   05 08                 -- cross-ref id=8 (8-2=6 → automixStartPoint)
                         -- terminates on 0x2B (next inline sibling)
```

In luvmaschine, compact `ADCCuePoint` entities store the cue time in `endTime`
(field `0x11`) and leave `time` (field `0x10`) absent. The verbose `ADCCuePoint`
(which provides `endPoint`) is the opposite: it stores its time in `time` and
has `endTime = -1.0` (absent sentinel). The reason for this asymmetry is unknown
— possibly `time` and `endTime` carry different semantics in the app (e.g. loop
start vs loop end, or in-cue vs out-cue), but no negative evidence has been
found to confirm this.

#### Observations from bulk data (~8,000 tracks)

Testing against a large export revealed several format variations not
visible in the original 4 reference tracks:

- **Compact integer tags `0x2D` and `0x2E`**: Small integer values can
  be encoded as single-byte type tags with no additional data bytes.
  `0x2D` = 1 (seen in `keySignatureIndex` for one track); `0x2E` = 0
  (seen in ~280 tracks with `keySignatureIndex` = 0, and in compact
  `ADCCuePoint` `number` fields). Previously `0x2E` was misinterpreted
  as a self-referencing marker with value 46.

- **Collection variant `0x1A`**: Some `ADCMediaItemUserData` entities
  use type tag `0x1A` instead of `0x0B` for their schema collection.
  The structure is identical (uint32 count + items), but the collection
  count is smaller (e.g. 3 instead of 6) with additional field names
  declared as standalone `0x08 + cstring` entries after the collection.
  Seen in ~60 tracks. The reason for the different tag is unknown.

- **Missing `artist` field**: Tracks imported from non-Apple-Music
  sources (e.g. YouTube, local files) may omit the `artist` field
  entirely from `ADCMediaItemTitleID`.

- **Missing Apple Music ID**: Tracks that exist only as local files
  (with `file://` URIs) have no `com.apple.iTunes:` string in the
  anonymous collection of `ADCMediaItemLocation`.

- **Duration precision**: The `duration` field is stored as float32
  in TSAF, which provides ~7 significant digits. Metadata from other
  sources (e.g. Apple Music API) may report float64 precision, leading
  to small discrepancies (typically < 1.0s).
