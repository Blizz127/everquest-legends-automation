"""Diagnostic model of the retained client's BSP *tree* point lookup.

EQGraphics.dll SHA below, RVA 0x2bc69e..0x2bc705. The loader at RVA
0x2c0860 expands one-based WLD child references into pointers; RVA 0x2bc750
installs them at runtime +0xa8. Missing child => -1, nonzero region => ref-1,
and a zero plane result takes the first child. See FINDINGS for byte evidence.

This models the tree suffix AFTER the native bounds gate, not a full client
query. Scalar arithmetic assumes binary32 round-to-nearest/ties-to-even;
live MXCSR and the caller's position/height have not been measured. Subnormal
and overflowing arithmetic are unsupported. Nothing here authorizes input or
changes the conservative closed-volume checks. A region ID is not dry-space
or collision evidence; the native label consumer returns NULL for -1.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from struct import pack, unpack


ENGINE_SHA256 = '4f5f18ee9821b3e15ff25980dda7def1b2cfcdfd72a5d359ac02d0b546163168'
QUERY_RVA = 0x2bc5f0
ARITHMETIC = 'binary32_nearest_even_normal_values; live_MXCSR_unverified'


def _f32(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Client BSP model needs finite real numbers')
    # Do not guess the live FTZ/DAZ flags or overflow behavior.
    if value and abs(value) < 2.0 ** -126:
        raise ValueError('Subnormal arithmetic is outside the model')
    try:
        result = unpack('<f', pack('<f', value))[0]
    except (OverflowError, ValueError) as error:
        raise ValueError('Binary32 overflow is outside the model') from error
    if not math.isfinite(result):
        raise ValueError('Binary32 overflow is outside the model')
    return result


@dataclass(frozen=True)
class ClientTreeProbe:
    native_return: int | None
    region_id: int | None
    reason: str
    node_path: tuple[int, ...]
    plane_results: tuple[float, ...]
    wld_sha256: str
    engine_sha256: str = ENGINE_SHA256
    arithmetic: str = ARITHMETIC
    scope: str = 'tree_suffix_after_native_bounds_gate'
    bounds_checked: bool = False
    dry_verified: bool = False
    collision_verified: bool = False
    real_client_accepted: bool = False
    input_authorized: bool = False


class ClientBspTreeView:
    """Immutable copied nodes; labels and full-body policy remain separate."""

    def __init__(self, nodes, *, region_count, wld_sha256):
        if (type(region_count) is not int or not 1 <= region_count <= 1_000_000
                or not isinstance(wld_sha256, str)
                or re.fullmatch('[0-9a-f]{64}', wld_sha256) is None):
            raise ValueError('Audited region count and WLD identity are required')
        copied = tuple(tuple(node) for node in nodes)
        if len(copied) > 2_000_000:
            raise ValueError('BSP node inventory exceeds the model budget')
        normalized = []
        for node in copied:
            if (len(node) != 7 or any(type(n) is not int for n in node[4:])
                    or not 0 <= node[4] <= region_count
                    or any(not 0 <= n <= len(copied) for n in node[5:])):
                raise ValueError('Invalid BSP node references')
            normalized.append(tuple(_f32(n) for n in node[:4]) + node[4:])
        self.nodes = tuple(normalized)
        self.wld_sha256 = wld_sha256

    @classmethod
    def from_wld(cls, wld):
        from .bsp_probe import BspPointLookup
        lookup = BspPointLookup(wld)  # Includes the existing WLD/reference audit.
        return cls(lookup.nodes, region_count=wld.bsp_region_count,
                   wld_sha256=wld.sha256)

    def probe_tree(self, x, y, z, *, max_visits=4096):
        if type(max_visits) is not int or not 1 <= max_visits <= 4096:
            raise ValueError('Invalid client BSP model visit budget')
        x, y, z = (_f32(value) for value in (x, y, z))
        path, distances, seen = [], [], set()

        def result(value, region, reason):
            return ClientTreeProbe(value, region, reason, tuple(path),
                                   tuple(distances), self.wld_sha256)

        if not self.nodes:
            # The native special case returns 1, not ref-1. Do not promote it
            # into a resolved region, nor confuse it with a missing child.
            return result(1, None, 'null_root_special_return')
        number = 1
        while len(path) < max_visits:
            if number in seen:
                return result(None, None, 'model_cycle_refusal')
            seen.add(number)
            path.append(number)
            nx, ny, nz, split, region, positive, negative = self.nodes[number - 1]
            # Native tests region BEFORE evaluating the plane/children.
            if region:
                return result(region - 1, region - 1, 'region_reference')
            try:
                # MULSS for each axis, ADDSS y+x, then z, then split. Keeping
                # separate roundings matters near copied source boundaries.
                xp, yp, zp = _f32(x * nx), _f32(y * ny), _f32(z * nz)
                distance = _f32(_f32(_f32(yp + xp) + zp) + split)
            except ValueError:
                return result(None, None, 'unsupported_arithmetic')
            distances.append(distance)
            number = positive if distance >= 0 else negative
            if number == 0:
                return result(-1, None, 'missing_child')
        return result(None, None, 'model_visit_budget')
