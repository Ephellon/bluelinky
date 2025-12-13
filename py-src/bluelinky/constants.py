from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:  # pragma: no cover
   from .interfaces import VehicleStatusOptions


class Region(str, Enum):
   US = "US"
   CA = "CA"
   EU = "EU"
   CN = "CN"
   AU = "AU"


POSSIBLE_CHARGE_LIMIT_VALUES = [50, 60, 70, 80, 90, 100]


@dataclass(frozen=True)
class _DefaultVehicleStatusOptions:
   refresh: bool
   parsed: bool


DEFAULT_VEHICLE_STATUS_OPTIONS = _DefaultVehicleStatusOptions(
   refresh=False,
   parsed=False,
)


DEFAULT_CONFIG: Dict[str, object] = {
   "username": "",
   "password": "",
   "region": Region.US,
   "brand": "hyundai",
   "auto_login": True,
   "pin": "1234",
   "vin": "",
   "vehicle_id": None,
}
