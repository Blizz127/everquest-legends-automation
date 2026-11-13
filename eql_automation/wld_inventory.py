"""Bounded structural inventory of copied EverQuest WLD members.

The header, XOR string table, and fragment framing follow the independent
VisualEQ loader: https://github.com/alimalkhalifa/VisualEQ/blob/master/src/server/loaders/s3d.js
This module does not interpret mesh collision, transforms, or walkability.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from struct import unpack_from


WLD_MAGIC = 0x54503D02
XOR_KEY = b"\x95\x3a\xc5\x2a\x95\x7a\x95\x6a"
MAX_WLD_SIZE = 128 * 1024 * 1024
MAX_FRAGMENTS = 200_000
MAX_STRING_TABLE = 16 * 1024 * 1024


@dataclass(frozen=True)
class WLDFragment:
    index: int
    type_code: int
    offset: int
    size: int
    name_ref: int
    name: str | None

    @property
    def body_offset(self) -> int:
        return self.offset + 12

    @property
    def body_size(self) -> int:
        return self.size - 4


class WLDInventory:
    def __init__(self, raw: bytes) -> None:
        if len(raw) < 32 or len(raw) > MAX_WLD_SIZE:
            raise ValueError("WLD size is outside the safety limit")
        self.raw = raw
        self.sha256 = sha256(raw).hexdigest()
        (magic, version, count, bsp_regions, unknown1,
         string_size, unknown2) = unpack_from("<7I", raw)
        if magic != WLD_MAGIC:
            raise ValueError("Unsupported WLD magic")
        if count > MAX_FRAGMENTS or string_size > MAX_STRING_TABLE or 28 + string_size > len(raw):
            raise ValueError("WLD header exceeds the safety limit")
        self.version = version
        self.fragment_count = count
        self.bsp_region_count = bsp_regions
        self.unknown_header_fields = (unknown1, unknown2)
        self.string_table_bytes = string_size
        encoded = raw[28:28 + string_size]
        self._strings = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                              for index, value in enumerate(encoded))
        cursor = 28 + string_size
        fragments = []
        for index in range(count):
            if cursor + 12 > len(raw):
                raise ValueError("WLD fragment header is truncated")
            size, type_code, name_ref = unpack_from("<IIi", raw, cursor)
            end = cursor + size + 8
            if size < 4 or end > len(raw):
                raise ValueError("WLD fragment bounds are invalid")
            fragments.append(WLDFragment(index, type_code, cursor, size,
                                         name_ref, self.resolve_name(name_ref)))
            cursor = end
        if len(raw) - cursor > 16:
            raise ValueError("WLD has unexpected trailing data")
        self.trailing_bytes_hex = raw[cursor:].hex()
        self.fragments = tuple(fragments)
        self.type_counts = dict(sorted(Counter(fragment.type_code for fragment in fragments).items()))
        self.unresolved_fragment_name_refs = sum(
            fragment.name_ref < 0 and fragment.name is None for fragment in fragments)

    def resolve_name(self, reference: int, *, strict: bool = False) -> str | None:
        if reference >= 0:
            return None
        start = -reference
        if start >= len(self._strings):
            if strict:
                raise ValueError("WLD string reference is outside the table")
            return None
        end = self._strings.find(b"\x00", start)
        if end < 0 or end - start > 4096:
            if strict:
                raise ValueError("WLD string is unterminated or too long")
            return None
        return self._strings[start:end].decode("latin-1")

    def body(self, fragment: WLDFragment) -> bytes:
        return self.raw[fragment.body_offset:fragment.body_offset + fragment.body_size]

    def placement_references(self) -> tuple[tuple[str | None, int], ...]:
        """Read only the name reference and flags in 0x15 fragments.

        The remaining placement transform is deliberately left uninterpreted.
        """
        result = []
        for fragment in self.fragments:
            if fragment.type_code != 0x15:
                continue
            if fragment.body_size < 8:
                raise ValueError("WLD 0x15 fragment is too short")
            object_ref, flags = unpack_from("<iI", self.raw, fragment.body_offset)
            result.append((self.resolve_name(object_ref, strict=True), flags))
        return tuple(result)
