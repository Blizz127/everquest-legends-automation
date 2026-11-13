from hashlib import sha256
from pathlib import Path
from struct import pack
import zlib

import pytest

from eql_automation.pfs_archive import DIRECTORY_CRC, PFSArchive


def synthetic_archive(files: list[tuple[str, bytes]]) -> bytes:
    blocks = bytearray()
    records = []
    for index, (_, content) in enumerate(files, 1):
        offset = 12 + len(blocks)
        compressed = zlib.compress(content)
        blocks.extend(pack("<II", len(compressed), len(content)))
        blocks.extend(compressed)
        records.append((index, offset, len(content)))
    names = bytearray(pack("<I", len(files)))
    for name, _ in files:
        encoded = name.encode() + b"\0"
        names.extend(pack("<I", len(encoded)))
        names.extend(encoded)
    directory_offset = 12 + len(blocks)
    compressed = zlib.compress(names)
    blocks.extend(pack("<II", len(compressed), len(names)))
    blocks.extend(compressed)
    records.append((DIRECTORY_CRC, directory_offset, len(names)))
    table_offset = 12 + len(blocks)
    table = pack("<I", len(records))
    for record in reversed(records):  # Names must match sorted data offsets.
        table += pack("<III", *record)
    return pack("<I4sI", table_offset, b"PFS ", 0x20000) + blocks + table


def test_pfs_inventory_reads_named_members_in_offset_order(tmp_path: Path):
    path = tmp_path / "synthetic.s3d"
    path.write_bytes(synthetic_archive([
        ("butcher.wld", b"synthetic terrain"),
        ("objects.wld", b"synthetic placements"),
    ]))
    archive = PFSArchive(path)
    assert [member.name for member in archive.members] == ["butcher.wld", "objects.wld"]
    assert archive.read_member("objects.wld") == b"synthetic placements"
    assert archive.members[0].sha256 == sha256(b"synthetic terrain").hexdigest()


def test_pfs_rejects_bad_header_and_duplicate_names(tmp_path: Path):
    path = tmp_path / "bad.s3d"
    path.write_bytes(b"bad")
    with pytest.raises(ValueError, match="header"):
        PFSArchive(path)
    path.write_bytes(synthetic_archive([("same.wld", b"one"),
                                        ("same.wld", b"two")]))
    with pytest.raises(ValueError, match="duplicate member names"):
        PFSArchive(path)
