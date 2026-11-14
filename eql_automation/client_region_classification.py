"""Audited native region metadata, separate from collision and movement policy.

The Scene slot-40 BSP path supplies fallback flags 0. The native bounds gate
and alternate-volume path are outside this model. Point lookup retains the
existing binary32 model. Volume lookup encloses every scalar operation over
the original vertex AABB, with no exact-plane branch pruning. It assumes
nearest-even rounding, masked SIMD exceptions and no exception-handler
intervention; it includes either subnormal flush setting.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction
from hashlib import sha256
import json

from .bsp_volume import rational_number
from .client_bsp_probe import ClientBspTreeView, ClientTreeProbe, ENGINE_SHA256
from .client_region_labels import ClientRegionMap, CLIENT_SHA256, decode_client_region_label

MODEL = 'scene_slot40_bsp_fallback0_v1'
ARITHMETIC = ('binary32_nearest_even; masked_SIMD_exceptions; '
              'DAZ_FTZ_either_pre_round_tininess; original_AABB_each_node')
MIN_NORMAL = Fraction(1, 1 << 126)
MIN_SUBNORMAL = Fraction(1, 1 << 149)
MAX_FINITE = Fraction((1 << 24)-1) * (1 << 104)


def _rn32(value):
    """Exact nearest-even binary32 value; never double-round through float64."""
    value = Fraction(value)
    if not value: return Fraction(0)
    sign = 1 if value > 0 else -1
    n, d = abs(value).numerator, value.denominator
    exponent = n.bit_length()-d.bit_length()
    below_power = (n < d << exponent) if exponent >= 0 else (n << -exponent < d)
    if below_power:
        exponent -= 1
    if exponent > 127:
        raise ValueError('Binary32 overflow is outside the classification model')
    spacing = max(exponent-23, -149)
    num, den = (n, d << spacing) if spacing >= 0 else (n << -spacing, d)
    quotient, remainder = divmod(num, den)
    if 2*remainder > den or (2*remainder == den and quotient & 1):
        quotient += 1
    rounded = Fraction(quotient << spacing) if spacing >= 0 else Fraction(quotient, 1 << -spacing)
    if rounded > MAX_FINITE:
        raise ValueError('Binary32 overflow is outside the classification model')
    return sign*rounded


def _flush(interval):
    low, high = interval
    maximum_subnormal = MIN_NORMAL-MIN_SUBNORMAL
    if (low <= maximum_subnormal and high >= MIN_SUBNORMAL
            or low <= -MIN_SUBNORMAL and high >= -maximum_subnormal):
        return min(low, Fraction(0)), max(high, Fraction(0))
    return interval


def _rounded_interval(low, high):
    if low > high: raise ValueError('Reversed arithmetic interval')
    rounded = _flush((_rn32(low), _rn32(high)))
    # A tiny exact result can round to minimum-normal under gradual underflow
    # yet flush to zero under FTZ. Include the pre-round alternative too (Intel
    # SDM Vol.1 4.9.1.5 and 11.5.2.5); singleton +/-MIN_NORMAL is not tiny.
    if low < MIN_NORMAL and high > 0 or low < 0 and high > -MIN_NORMAL:
        rounded = (min(rounded[0], Fraction(0)), max(rounded[1], Fraction(0)))
    return rounded


def _mul(interval, coefficient):
    low, high = _flush(interval)
    a, b = low*coefficient, high*coefficient
    return _rounded_interval(min(a, b), max(a, b))


def _add(first, second):
    a, b = _flush(first), _flush(second)
    return _rounded_interval(a[0]+b[0], a[1]+b[1])


def _plane_range(box, plane):
    nx, ny, nz, split = map(Fraction, plane)
    xp, yp, zp = (_mul(box[i], c) for i, c in enumerate((nx, ny, nz)))
    return _add(_add(_add(yp, xp), zp), (split, split))


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


@dataclass(frozen=True)
class NativeRegionClass:
    origin: str
    flags: int
    class_id: int
    region_id: int | None = None
    record_index: int | None = None
    fragment_index: int | None = None
    raw_label: str | None = None
    matched_prefix: str | None = None
    callback_invoked: bool = False
    transition_write_kind: str | None = None
    transition_source: str | None = None


@dataclass(frozen=True)
class NativePointClassification:
    complete: bool
    reason: str
    tree_probe: ClientTreeProbe
    classification: NativeRegionClass | None
    inventory_sha256: str
    query_scope: str = MODEL
    bounds_checked: bool = False
    collision_verified: bool = False
    real_client_accepted: bool = False
    input_authorized: bool = False


@dataclass(frozen=True)
class NativeVolumeClassification:
    complete: bool
    reason: str
    visits: int
    possible_classes: tuple[NativeRegionClass, ...]
    inventory_sha256: str
    wld_sha256: str
    volume_sha256: str
    trace_sha256: str
    coordinate_bounds: tuple
    arithmetic: str = ARITHMETIC
    query_scope: str = MODEL
    ancestor_clipping_used: bool = False
    bounds_checked: bool = False
    collision_verified: bool = False
    real_client_accepted: bool = False
    input_authorized: bool = False


class ClientBspClassificationView:
    """Copied nodes and native last-record-wins labels with distinct provenance."""
    def __init__(self, tree, labels):
        if (not isinstance(tree, ClientBspTreeView) or not isinstance(labels, ClientRegionMap)
                or tree.wld_sha256 != labels.wld_sha256):
            raise ValueError('Matching audited native tree and region labels required')
        self.records = tuple((fragment, label, tuple(ids)) for fragment, label, ids in labels.records)
        self.mapping = tuple(labels.region_to_record)
        if (not 1 <= len(self.mapping) <= 1_000_000
                or any(type(i) is not int or not -1 <= i < len(self.records) for i in self.mapping)
                or any(not isinstance(label, str) or not label for _, label, _ in self.records)):
            raise ValueError('Invalid copied native record mapping')
        self.tree = ClientBspTreeView(tree.nodes, region_count=len(self.mapping), wld_sha256=tree.wld_sha256)
        self.nodes, self.wld_sha256 = self.tree.nodes, self.tree.wld_sha256
        self._decoded = tuple(decode_client_region_label(label, initial_flags=0) for _, label, _ in self.records)
        self.inventory_sha256 = sha256(_encoded(dict(model=MODEL, volume_arithmetic=ARITHMETIC,
            wld_sha256=self.wld_sha256, engine_sha256=ENGINE_SHA256, client_sha256=CLIENT_SHA256,
            scene_query_rva='0xf78c0', fallback_wrapper_rva='0x1b0ba0',
            nodes=self.nodes, records=self.records, region_to_record=self.mapping))).hexdigest()
        self._binding = (self.tree, self.nodes, self.records, self.mapping, self._decoded,
                         self.wld_sha256, self.inventory_sha256)

    @classmethod
    def from_wld(cls, wld):
        return cls(ClientBspTreeView.from_wld(wld), ClientRegionMap(wld))

    def _check(self):
        current = (self.tree, self.nodes, self.records, self.mapping, self._decoded,
                   self.wld_sha256, self.inventory_sha256)
        if (any(a is not b for a, b in zip(current[:5], self._binding[:5]))
                or current[5:] != self._binding[5:] or self.tree.nodes is not self.nodes
                or self.tree.wld_sha256 != self.wld_sha256):
            raise ValueError('Native classification snapshot changed')

    def _region(self, region):
        index = self.mapping[region]
        if index == -1:
            return NativeRegionClass('untyped_region', 0, 0, region)
        fragment, label, _ = self.records[index]
        decoded = self._decoded[index]
        return NativeRegionClass('typed_region', decoded.flags, decoded.low_byte, region,
            index, fragment, label, decoded.matched_prefix, True,
            decoded.transition_write_kind, decoded.transition_source)

    def classify_point_after_bounds(self, x, y, z, *, max_visits=4096):
        self._check()
        probe = self.tree.probe_tree(x, y, z, max_visits=max_visits)
        value = None
        if probe.reason == 'missing_child' and probe.native_return == -1:
            value = NativeRegionClass('missing_child', 0, 0)
        elif probe.reason == 'region_reference' and probe.region_id is not None:
            value = self._region(probe.region_id)
        self._check()
        return NativePointClassification(value is not None,
            'native_classification_only' if value is not None else probe.reason,
            probe, value, self.inventory_sha256)

    def classify_convex_enclosure_after_bounds(self, vertices_wld, *, max_visits=4096, max_depth=256):
        """Enclose all float32 query outcomes over the supplied convex hull.

        Each node receives the whole original AABB, so extra classifications
        can occur. No sampled vertex/centroid or exact plane prunes a branch.
        Incomplete results cannot establish a complete set of classifications.
        """
        self._check()
        if (not isinstance(vertices_wld, tuple) or not 4 <= len(vertices_wld) <= 256
                or any(not isinstance(p, tuple) or len(p) != 3 for p in vertices_wld)
                or type(max_visits) is not int or not 1 <= max_visits <= 4096
                or type(max_depth) is not int or not 1 <= max_depth <= 256):
            raise ValueError('Bounded native classification volume required')
        vertices = tuple(tuple(rational_number(v) for v in p) for p in vertices_wld)
        if any(v.numerator.bit_length() > 16384 or v.denominator.bit_length() > 16384
               for p in vertices for v in p):
            raise ValueError('Native volume coordinate arithmetic budget exceeded')
        volume_pin = sha256(_encoded([[str(v) for v in p] for p in vertices])).hexdigest()
        trace = sha256(); visits = 0; outcomes = {}
        bounds = tuple((min(p[i] for p in vertices), max(p[i] for p in vertices)) for i in range(3))
        shown_bounds = tuple(tuple(str(v) for v in interval) for interval in bounds)
        def finish(complete, reason):
            self._check()
            return NativeVolumeClassification(complete, reason, visits,
                tuple(outcomes[k] for k in sorted(outcomes)), self.inventory_sha256,
                self.wld_sha256, volume_pin, trace.hexdigest(), shown_bounds)
        def remember(value):
            outcomes[_encoded(asdict(value))] = value
        if not self.nodes:
            return finish(False, 'null_root_special_return')
        try:
            box = tuple(_rounded_interval(*interval) for interval in bounds)
            stack = [(1, frozenset())]
            while stack:
                if visits >= max_visits: return finish(False, 'model_visit_budget')
                number, ancestry = stack.pop(); visits += 1
                trace.update(_encoded(dict(node=number)))
                if number == 0:
                    remember(NativeRegionClass('missing_child', 0, 0)); continue
                if number in ancestry: return finish(False, 'model_cycle_refusal')
                if len(ancestry) >= max_depth: return finish(False, 'model_depth_budget')
                nx, ny, nz, split, region, positive, negative = self.nodes[number-1]
                if region:
                    remember(self._region(region-1)); continue
                low, high = _plane_range(box, (nx, ny, nz, split))
                trace.update(_encoded(dict(range=(str(low), str(high)))))
                seen = ancestry | {number}
                if low >= 0: stack.append((positive, seen))
                elif high < 0: stack.append((negative, seen))
                else:
                    stack.append((negative, seen)); stack.append((positive, seen))
            return finish(True, 'native_classification_enclosure_only')
        except (ValueError, OverflowError):
            return finish(False, 'unsupported_arithmetic')
