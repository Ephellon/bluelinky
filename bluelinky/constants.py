"""Constants and enums for the Python port of Bluelinky."""
from __future__ import annotations

from enum import Enum
from typing import Final


class Region(str, Enum):
    """Supported Hyundai Bluelink regions."""

    EU = "EU"
    US = "US"
    CA = "CA"
    CN = "CN"
    AU = "AU"


DEFAULT_VEHICLE_STATUS_OPTIONS: Final = {
    "refresh": True,
    "parsed": True,
    "use_cache": True,
}


DEFAULT_CONFIG: Final = {
    "username": "",
    "password": "",
    "region": Region.US,
    "brand": "hyundai",
    "auto_login": True,
    "pin": "1234",
    "vin": "",
    "vehicle_id": None,
}
