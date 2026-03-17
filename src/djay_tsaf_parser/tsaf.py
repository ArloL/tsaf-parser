"""Structural TSAF binary format parser.

Walks the byte stream forward, building a typed entity tree. No field-name
searches, no regular expressions.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TSAFParseError(Exception):
    """Raised when TSAF data cannot be parsed."""

    pass


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TSAFHeader:
    """Parsed 16-byte TSAF file header."""

    magic: bytes
    version: int
    entity_count: int
    unknown: bytes


@dataclass
class TSAFField:
    """A single typed field within an entity."""

    name: str | None  # None for anonymous items (e.g. collection schema blocks)
    value: str | float | int | list | bytes | None
    type_tag: int  # raw type tag byte


@dataclass
class VerboseEntity:
    """An entity decoded from the verbose (0x08) form.

    Schema-only entities (field-name declarations with no values) appear as
    VerboseEntity instances whose fields list is empty; their names are
    registered in the schema registry as a side-effect of parsing.
    """

    type_name: str
    fields: list[TSAFField] = field(default_factory=list)


@dataclass
class CompactEntity:
    """An entity decoded from the compact (0x05) form.

    Field names are resolved from the schema registry at parse time.
    """

    type_name: str
    fields: list[TSAFField] = field(default_factory=list)


@dataclass
class RawEntity:
    """An entity with an unrecognised form byte — stored as opaque bytes."""

    form_byte: int
    data: bytes


TSAFEntity = VerboseEntity | CompactEntity | RawEntity


@dataclass
class TSAFDocument:
    """A fully-parsed TSAF file."""

    header: TSAFHeader
    entities: list[TSAFEntity]


# ---------------------------------------------------------------------------
# Low-level cursor reader
# ---------------------------------------------------------------------------


class _Reader:
    """Cursor-based reader over a raw bytes buffer.

    The absolute cursor position is used to calculate alignment padding for
    numeric values (float32, uint32, float64).
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    @property
    def pos(self) -> int:
        return self._pos

    @property
    def remaining(self) -> int:
        return len(self._data) - self._pos

    def peek(self, n: int = 1) -> bytes:
        """Return next n bytes without advancing the cursor."""
        return self._data[self._pos : self._pos + n]

    def read(self, n: int) -> bytes:
        """Read exactly n bytes and advance the cursor."""
        if self._pos + n > len(self._data):
            raise TSAFParseError(
                f"Unexpected end of data at offset {self._pos:#x}: "
                f"need {n} bytes, {self.remaining} available"
            )
        chunk = self._data[self._pos : self._pos + n]
        self._pos += n
        return chunk

    def read_byte(self) -> int:
        """Read and return a single byte."""
        return self.read(1)[0]

    def read_cstring(self) -> str:
        """Read bytes up to and including the null terminator; return decoded UTF-8."""
        end = self._data.index(0x00, self._pos)
        s = self._data[self._pos : end]
        self._pos = end + 1
        return s.decode("utf-8")

    def read_numeric(self, byte_size: int) -> bytes:
        """Read a numerically-typed value with alignment padding.

        Numeric values (4-byte: float32, uint32/int32; 8-byte: float64) are
        always stored at an absolute offset aligned to their byte size.
        This method skips the zero-padding bytes that precede the value and
        returns exactly byte_size bytes.

        For byte_size == 1 (uint8) no alignment is applied.
        """
        if byte_size > 1:
            pad = (byte_size - (self._pos % byte_size)) % byte_size
            self._pos += pad  # skip alignment-padding zeros
        return self.read(byte_size)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _skip_cross_refs(r: _Reader) -> None:
    """Skip any parent cross-reference pairs (0x05, id<0x10) at current position."""
    while r.remaining >= 2 and r.peek(2)[0] == 0x05 and r.peek(2)[1] < 0x10:
        r.read(2)


def _parse_header(r: _Reader) -> TSAFHeader:
    magic = r.read(4)
    if magic != b"TSAF":
        raise TSAFParseError(f"Invalid magic bytes: {magic!r}")
    version = struct.unpack("<I", r.read(4))[0]
    entity_count = struct.unpack("<I", r.read(4))[0]
    unknown = r.read(4)
    # 4 extra bytes after the documented 16-byte header precede the entity stream
    r.read(4)
    return TSAFHeader(magic=magic, version=version, entity_count=entity_count, unknown=unknown)


def _parse_sub_entity(r: _Reader, schema_registry: dict[str, list[str]]) -> TSAFEntity:
    """Parse one entity that starts with 0x2B inside a collection field."""
    marker = r.read_byte()
    if marker != 0x2B:
        raise TSAFParseError(f"Expected entity marker 0x2B, got {marker:#04x}")
    form = r.read_byte()
    if form == 0x08:
        return _parse_verbose_entity(r, schema_registry)
    elif form == 0x05:
        # Compact sub-entity: type resolved from registry with empty fallback
        return _parse_compact_entity_body(r, schema_registry, "")
    else:
        return _parse_raw_entity(r, form)


def _parse_collection_body(
    r: _Reader,
    count: int,
    schema_registry: dict[str, list[str]],
) -> tuple[list, list[str]]:
    """Parse the items of a 0x0B collection.

    Returns (sub_entities, schema_names).  Exactly one will be non-empty
    (unless count == 0).
    """
    if count == 0 or r.remaining == 0:
        return [], []

    first = r.peek()[0]

    if first == 0x08:
        # Schema field-name declarations
        names: list[str] = []
        for _ in range(count):
            if r.remaining == 0 or r.peek()[0] != 0x08:
                break
            r.read_byte()  # consume 0x08
            names.append(r.read_cstring())
        return [], names

    if first == 0x2B:
        # Sub-entities
        sub: list[TSAFEntity] = []
        for _ in range(count):
            if r.remaining == 0 or r.peek()[0] != 0x2B:
                break
            sub.append(_parse_sub_entity(r, schema_registry))
        return sub, []

    if first == 0x21:
        # Apple ID values — stored as plain strings
        values: list[str] = []
        for _ in range(count):
            if r.remaining == 0 or r.peek()[0] != 0x21:
                break
            r.read_byte()  # 0x21
            r.read_byte()  # 0x08 sub-tag
            values.append(r.read_cstring())
        return values, []

    # Unknown collection content — skip gracefully
    return [], []


def _read_field_name(r: _Reader) -> str | None:
    """Read optional field name (0x08 + cstring); returns None if not present."""
    if r.remaining > 0 and r.peek()[0] == 0x08:
        r.read_byte()
        return r.read_cstring()
    return None


_UNRECOGNISED = object()  # sentinel returned by _read_typed_value for unknown tags


def _read_typed_value(r: _Reader, type_tag: int) -> str | float | int | bytes | object:
    """Read the value bytes for a given type tag.

    Returns the decoded value, or *_UNRECOGNISED* for unknown type tags.
    Callers must handle 0x08 (string, needs disambiguation), 0x0B
    (collection), and 0x05 (cross-ref / int32) themselves.
    """
    if type_tag == 0x13:
        return struct.unpack("<f", r.read_numeric(4))[0]
    if type_tag == 0x30:
        return struct.unpack("<d", r.read_numeric(8))[0]
    if type_tag == 0x0F:
        return r.read_byte()
    if type_tag == 0x2E:
        return 0x2E  # self-value; no further bytes
    if type_tag == 0x0D:
        return True  # boolean flag; no further bytes
    if type_tag == 0x00:
        return 0  # zero sentinel; no further bytes
    if type_tag == 0x15:
        size = struct.unpack("<I", r.read_numeric(4))[0]
        return r.read(size)
    return _UNRECOGNISED


def _parse_verbose_entity(
    r: _Reader,
    schema_registry: dict[str, list[str]],
) -> VerboseEntity:
    """Parse a verbose (0x08) entity body.

    Handles both schema-declaration entities (field names only, no values) and
    data entities (type-tag + value + field-name triples).

    Disambiguation rule for strings (type tag 0x08): after reading the string S,
    peek at the next byte:
      • next == 0x08  →  S is a field VALUE; the following 0x08+cstring is the name.
      • next != 0x08  →  S is a field NAME in a schema declaration (no preceding value).
    """
    type_name = r.read_cstring()
    fields: list[TSAFField] = []
    schema_names: list[str] = []

    while r.remaining > 0:
        b = r.peek()[0]

        if b == 0x2B:
            break  # next entity starts here

        if b == 0x00:
            r.read_byte()
            _skip_cross_refs(r)
            break

        # Parent cross-reference: 0x05 followed by id < 0x10
        if b == 0x05 and r.remaining >= 2 and r.peek(2)[1] < 0x10:
            r.read(2)
            continue

        type_tag = r.read_byte()

        if type_tag == 0x08:
            # String disambiguation: S is a value when followed by 0x08 (field name marker)
            s = r.read_cstring()
            if r.remaining > 0 and r.peek()[0] == 0x08:
                r.read_byte()
                field_name = r.read_cstring()
                fields.append(TSAFField(name=field_name, value=s, type_tag=0x08))
                schema_names.append(field_name)
            else:
                schema_names.append(s)  # schema declaration; no value

        elif type_tag == 0x0B:
            count = struct.unpack("<I", r.read_numeric(4))[0]
            sub, names = _parse_collection_body(r, count, schema_registry)
            if names:
                schema_names.extend(names)
            else:
                field_name = _read_field_name(r)
                fields.append(TSAFField(name=field_name, value=sub, type_tag=0x0B))
                if field_name:
                    schema_names.append(field_name)

        elif type_tag == 0x05:
            # Stray cross-ref (already consumed 0x05; skip ref_id) or int32 data field
            next_b = r.peek()[0] if r.remaining > 0 else 0x00
            if next_b < 0x10:
                r.read_byte()
                continue
            value = struct.unpack("<i", r.read_numeric(4))[0]
            field_name = _read_field_name(r)
            fields.append(TSAFField(name=field_name, value=value, type_tag=0x05))
            if field_name:
                schema_names.append(field_name)

        else:
            value = _read_typed_value(r, type_tag)
            if value is _UNRECOGNISED:
                break
            field_name = _read_field_name(r)
            fields.append(TSAFField(name=field_name, value=value, type_tag=type_tag))
            if field_name:
                schema_names.append(field_name)

    if schema_names and type_name not in schema_registry:
        schema_registry[type_name] = schema_names

    return VerboseEntity(type_name=type_name, fields=fields)


def _parse_compact_entity_body(
    r: _Reader,
    schema_registry: dict[str, list[str]],
    type_name: str,
) -> CompactEntity:
    """Parse a compact-entity body.

    Called after 0x2B 0x05 have been consumed. The next byte is the first
    field ID directly (no leading 0x05 separator for the very first field).
    Subsequent fields are each preceded by a 0x05 separator byte.
    """
    schema_fields = schema_registry.get(type_name, [])
    fields: list[TSAFField] = []

    def _read_value(type_tag: int) -> str | float | int | bytes | None:
        if type_tag in (0x05, 0x0B):
            return struct.unpack("<I", r.read_numeric(4))[0]
        v = _read_typed_value(r, type_tag)
        return None if v is _UNRECOGNISED else v

    def _field_name(field_id: int) -> str | None:
        idx = field_id - 0x10
        return schema_fields[idx] if 0 <= idx < len(schema_fields) else None

    if r.remaining == 0:
        return CompactEntity(type_name=type_name, fields=fields)

    # First field ID is read directly (no preceding 0x05 separator)
    first_id = r.read_byte()
    if first_id >= 0x10:
        type_tag = r.read_byte()
        fields.append(TSAFField(name=_field_name(first_id), value=_read_value(type_tag), type_tag=type_tag))

    # Subsequent fields: each preceded by 0x05 + field_id
    while r.remaining > 0:
        b = r.peek()[0]
        if b == 0x2B:
            break
        if b == 0x00:
            r.read_byte()
            _skip_cross_refs(r)
            break
        if b != 0x05:
            break
        r.read_byte()  # consume 0x05
        if r.remaining == 0:
            break
        field_id = r.read_byte()
        if field_id < 0x10:
            continue  # cross-reference to parent entity; skip
        if r.remaining == 0:
            break
        type_tag = r.read_byte()
        fields.append(TSAFField(name=_field_name(field_id), value=_read_value(type_tag), type_tag=type_tag))

    return CompactEntity(type_name=type_name, fields=fields)


def _parse_raw_entity(r: _Reader, form_byte: int) -> RawEntity:
    """Consume bytes until the next 0x2B entity marker or EOF."""
    start = r.pos
    while r.remaining > 0:
        if r.peek()[0] == 0x2B:
            break
        r.read_byte()
    return RawEntity(form_byte=form_byte, data=r._data[start : r.pos])


# ---------------------------------------------------------------------------
# Top-level parse entry point
# ---------------------------------------------------------------------------


def parse_tsaf(data: bytes) -> TSAFDocument:
    """Parse a TSAF binary blob into a structured document.

    Args:
        data: Raw TSAF binary content.

    Returns:
        :class:`TSAFDocument` containing the header and all top-level entities.

    Raises:
        TSAFParseError: If the magic bytes are invalid or the data is truncated.
    """
    r = _Reader(data)
    header = _parse_header(r)

    schema_registry: dict[str, list[str]] = {}
    last_verbose_type = ""
    entities: list[TSAFEntity] = []

    while r.remaining > 0:
        if r.peek()[0] != 0x2B:
            break
        r.read_byte()  # consume 0x2B entity marker
        if r.remaining == 0:
            break
        form = r.read_byte()

        if form == 0x08:
            entity = _parse_verbose_entity(r, schema_registry)
            last_verbose_type = entity.type_name
            entities.append(entity)
        elif form == 0x05:
            entity = _parse_compact_entity_body(r, schema_registry, last_verbose_type)
            entities.append(entity)
        else:
            entity = _parse_raw_entity(r, form)
            entities.append(entity)

    return TSAFDocument(header=header, entities=entities)


