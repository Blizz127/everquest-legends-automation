"""A measured camp height correspondence, separate from old travel calibration."""
from dataclasses import asdict, dataclass, field

from .location_log import RawLocationFix


@dataclass(frozen=True)
class CampSourceHeight:
    first: RawLocationFix
    second: RawLocationFix
    owner_binding: tuple
    measured_height_sha256: str
    preparation_sha256: str
    itinerary_sha256: str
    source_archive_sha256: str
    source_wld_sha256: str
    raw_z_minus_source_z: float
    residual_limit: float
    last_calibration_log_line_seq: int
    valid_from_monotonic: float
    valid_until_monotonic: float
    measured_pair_expires_at: float
    live_verified: bool = field(default=False, init=False)

    def record(self):
        value = asdict(self)
        for key in ('first', 'second'):
            value[key]['log_local_time'] = value[key]['log_local_time'].isoformat()
        return dict(format='eql-camp-source-height-v1', **value,
                    input_authorized=False, real_client_accepted=False)
