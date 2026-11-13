"""Bounded, read-only inventory of copied EverQuest PFS/S3D archives.

Layout reference: https://github.com/martinlindhe/eqformat_pfs/blob/master/format_pfs.md
Only file names and per-member hashes are emitted by the CLI; client data
stays under the untracked local store. This is not a collision decoder.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
import zlib


DIRECTORY_CRC = 0x61580AC9
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_MEMBERS = 10000
MAX_MEMBER = 128 * 1024 * 1024
MAX_TOTAL_EXPANDED = 512 * 1024 * 1024
MAX_BLOCK = 1024 * 1024


@dataclass(frozen=True)
class PFSMember:
    name: str
    offset: int
    expanded_size: int
    crc_field: int
    sha256: str
    first_bytes_hex: str


class PFSArchive:
    def __init__(self, path: Path) -> None:
        if not path.is_file() or path.stat().st_size > MAX_ARCHIVE:
            raise ValueError("PFS archive missing or too large")
        self.path = path
        self.raw = path.read_bytes()
        self.sha256 = sha256(self.raw).hexdigest()
        if len(self.raw) < 16 or self.raw[4:8] != b"PFS ":
            raise ValueError("Unsupported PFS archive header")
        directory_offset = self._u32(0)
        if directory_offset < 12 or directory_offset + 4 > len(self.raw):
            raise ValueError("PFS directory offset is outside the archive")
        count = self._u32(directory_offset)
        if count < 2 or count > MAX_MEMBERS + 1 or directory_offset + 4 + count * 12 > len(self.raw):
            raise ValueError("PFS member table is invalid")
        entries = []
        directory = None
        expanded_total = 0
        for index in range(count):
            crc, offset, size = unpack_from("<III", self.raw,
                                            directory_offset + 4 + index * 12)
            if size > MAX_MEMBER or offset < 12 or offset >= directory_offset:
                raise ValueError("PFS member bounds are invalid")
            expanded_total += size
            if expanded_total > MAX_TOTAL_EXPANDED:
                raise ValueError("PFS expanded data exceeds the safety limit")
            content = self._read_blocks(offset, size, directory_offset)
            if crc == DIRECTORY_CRC:
                if directory is not None:
                    raise ValueError("PFS has duplicate name directories")
                directory = content
            else:
                entries.append((crc, offset, size, content))
        if directory is None:
            raise ValueError("PFS filename directory is missing")
        entries.sort(key=lambda item: item[1])
        names = self._read_names(directory, len(entries))
        if len(set(names)) != len(names):
            raise ValueError("PFS has duplicate member names")
        self._contents = {name: content for name, (_, _, _, content)
                          in zip(names, entries)}
        self.members = tuple(PFSMember(
            name, offset, size, crc, sha256(content).hexdigest(),
            content[:16].hex())
            for name, (crc, offset, size, content) in zip(names, entries))

    def _u32(self, offset: int) -> int:
        if offset < 0 or offset + 4 > len(self.raw):
            raise ValueError("PFS read exceeds the archive")
        return unpack_from("<I", self.raw, offset)[0]

    def _read_blocks(self, offset: int, size: int, table_start: int) -> bytes:
        result = bytearray()
        cursor = offset
        while len(result) < size:
            if cursor + 8 > table_start:
                raise ValueError("PFS compressed block header is truncated")
            compressed_len = self._u32(cursor)
            expanded_len = self._u32(cursor + 4)
            cursor += 8
            if (compressed_len == 0 or compressed_len > MAX_BLOCK or
                    expanded_len == 0 or expanded_len > MAX_BLOCK or
                    len(result) + expanded_len > size or
                    cursor + compressed_len > table_start):
                raise ValueError("PFS compressed block bounds are invalid")
            compressed = self.raw[cursor:cursor + compressed_len]
            inflater = zlib.decompressobj()
            block = inflater.decompress(compressed, expanded_len + 1)
            if (len(block) != expanded_len or not inflater.eof or
                    inflater.unused_data or inflater.unconsumed_tail):
                raise ValueError("PFS zlib block length is invalid")
            result.extend(block)
            cursor += compressed_len
        return bytes(result)

    @staticmethod
    def _read_names(directory: bytes, expected: int) -> list[str]:
        if len(directory) < 4 or unpack_from("<I", directory)[0] != expected:
            raise ValueError("PFS filename count does not match member table")
        cursor = 4
        names = []
        for _ in range(expected):
            if cursor + 4 > len(directory):
                raise ValueError("PFS filename length is truncated")
            length = unpack_from("<I", directory, cursor)[0]
            cursor += 4
            if length < 2 or length > 512 or cursor + length > len(directory):
                raise ValueError("PFS filename length is invalid")
            data = directory[cursor:cursor + length]
            cursor += length
            if data[-1] != 0:
                raise ValueError("PFS filename is not NUL terminated")
            name = data[:-1].decode("utf-8")
            if not name or "/" in name or "\\" in name or name in {".", ".."}:
                raise ValueError("Unsafe PFS member name")
            names.append(name)
        if cursor != len(directory):
            raise ValueError("PFS filename directory has trailing bytes")
        return names

    def read_member(self, name: str) -> bytes:
        return self._contents[name]
