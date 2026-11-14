"""Copied-data model of the installed client's region-label callback.

eqgame.exe SHA below, RVA 0x1c3170..0x1c34a2; registered at RVA 0x1b2056.
This returns raw bits, not inferred dry/water, collision or movement approval.
Native transition-name writes are described but never executed. Unknown and
missing labels preserve caller input; they are not evidence of a dry region.
"""
from dataclasses import dataclass
from struct import unpack_from


CLIENT_SHA256 = 'fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'
CALLBACK_RVA = 0x1c3170
TRANSITION_FORMAT = 'DRNTP00255%05d000000000000000'


@dataclass(frozen=True)
class ClientRegionFlags:
    flags: int
    low_byte: int
    matched_prefix: str | None
    label_present: bool
    transition_write_kind: str | None = None
    transition_source: str | None = None
    client_sha256: str = CLIENT_SHA256
    enum_meaning_verified: bool = False
    dry_verified: bool = False
    real_client_accepted: bool = False
    input_authorized: bool = False


def decode_client_region_label(label, *, initial_flags=0):
    """Model case-sensitive ASCII-prefix/position tests on a bounded C string.

``transition_source`` records the copied string or numeric-parse input. The
ATP numeric conversion/formatting and native global write are outside scope.
Passing no label preserves initial flags exactly, even if low_byte is zero.
    """
    if type(initial_flags) is not int or not 0 <= initial_flags <= 0xffffffff:
        raise ValueError('Caller flags must be an unsigned DWORD')
    if label is None:
        raw = None
    else:
        if isinstance(label, str):
            try:
                raw = label.encode('latin-1')
            except UnicodeEncodeError as error:
                raise ValueError('Copied WLD labels must be single-byte strings') from error
        elif isinstance(label, bytes):
            raw = label
        else:
            raise ValueError('Expected a copied label or None')
        if len(raw) > 4096:
            raise ValueError('Copied region label exceeds the model bound')
        raw = raw.split(b'\x00', 1)[0]
    flags, prefix, kind, source = initial_flags, None, None, None

    def result():
        return ClientRegionFlags(flags, flags & 255, prefix, raw is not None, kind, source)

    if raw is None or len(raw) < 4:
        return result()
    if raw[:1] == b'A':
        tag = raw[:3]
        codes = {b'AWT': 5, b'ALV': 7, b'AVW': 8}
        markers = {b'APK': 30, b'ATP': 31, b'ASL': 28}
        if tag in codes:
            prefix = tag.decode('ascii')
            flags = (flags & 0xffffff00) | codes[tag]
        elif tag in markers:
            prefix = tag.decode('ascii')
            flags |= 1 << markers[tag]
            if tag == b'ATP':
                kind, source = 'format_numeric_suffix_at_4', raw[4:].decode('latin-1')
        return result()  # All A* paths skip the positional suffix tests.

    codes = {b'DR': 0, b'WT': 5, b'LA': 7, b'SL': 6,
             b'VW': 8, b'W2': 9, b'W3': 10}
    tag = raw[:2]
    if tag in codes:
        prefix = tag.decode('ascii')
        flags = (flags & 0xffffff00) | codes[tag]
    # Native applies these markers even to an unrecognized non-A prefix.
    if raw[2:3] == b'P':
        flags |= 1 << 30
    if raw[3:5] == b'TP':
        flags |= 1 << 31
        kind, source = 'copy_complete_label', raw.decode('latin-1')
    if len(raw) > 32:
        if raw[31:32] == b'M':
            flags |= 1 << 29
        if raw[32:33] == b'S':
            flags |= 1 << 28
        if raw[33:34] == b'P':
            flags |= 1 << 27
        elif raw[33:34] == b'F':
            flags |= 1 << 26
    return result()


class ClientRegionMap:
    """Native record precedence over the existing structurally audited subset.

The native converter indexes records relative to the first 0x29 fragment.
Require contiguous 0x29 fragments, as observed in the retained three zones;
do not silently compress gaps into a different runtime index. The existing
WLD audit's stricter malformed/empty-label refusals remain in force.
    """

    def __init__(self, wld):
        from .region_audit import audit_bsp_regions
        from .wld_inventory import XOR_KEY
        audit_bsp_regions(wld)
        fragments = tuple(f for f in wld.fragments if f.type_code == 0x29)
        if fragments and tuple(f.index for f in fragments) != tuple(
                range(fragments[0].index, fragments[0].index + len(fragments))):
            raise ValueError('Noncontiguous native region-type record indices')
        records, mapping, overwrites = [], [-1] * wld.bsp_region_count, []
        for record_index, fragment in enumerate(fragments):
            body = wld.body(fragment)
            count = unpack_from('<I', body, 4)[0]
            ids = unpack_from(f'<{count}I', body, 8)
            size = unpack_from('<I', body, 8 + 4 * count)[0]
            start = 12 + 4 * count
            text = bytes(value ^ XOR_KEY[i % len(XOR_KEY)]
                         for i, value in enumerate(body[start:start + size]))
            text = text.split(b'\x00', 1)[0].decode('latin-1')
            # 2ba670 copies optional decoded text only when it is nonempty;
            # 2bc510 otherwise falls back to the fragment's name pointer.
            label = text or fragment.name
            records.append((fragment.index, label, tuple(ids)))
            for region in ids:
                if mapping[region] != -1:
                    overwrites.append((region, mapping[region], record_index))
                mapping[region] = record_index
        self.records = tuple(records)
        self.region_to_record = tuple(mapping)
        self.overwrites = tuple(overwrites)
        self.wld_sha256 = wld.sha256

    def flags_for_region(self, region, *, initial_flags=0):
        if type(region) is not int or not 0 <= region < len(self.region_to_record):
            raise ValueError('Expected a resolved zero-based region ID')
        record = self.region_to_record[region]
        label = None if record == -1 else self.records[record][1]
        return decode_client_region_label(label, initial_flags=initial_flags)
