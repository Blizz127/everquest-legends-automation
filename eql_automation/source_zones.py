"""Catalog identities supported by source travel; no cross-zone movement."""
from types import MappingProxyType

# IDs checked against the retained client Resources/ZoneNames.txt. Production
# loaders also require the current installed catalog's exact file hash/name.
SOURCE_ZONE_IDS = MappingProxyType({'crushbone': 58, 'butcher': 68})


def source_zone_id(zone):
    if type(zone) is not str or zone not in SOURCE_ZONE_IDS:
        raise ValueError('Unsupported source-travel zone')
    return SOURCE_ZONE_IDS[zone]
