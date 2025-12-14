from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, List, Literal

from bluelinky.interfaces.common_interfaces import Brand, VehicleStatusOptions

from .australia import AustraliaBrandEnvironment, getBrandEnvironment as getAUBrandEnvironment
from .canada import CanadianBrandEnvironment, getBrandEnvironment as getCABrandEnvironment
from .china import ChineseBrandEnvironment, getBrandEnvironment as getCNBrandEnvironment
from .europe import EuropeanBrandEnvironment, getBrandEnvironment as getEUBrandEnvironment


def _all_endpoints_ca(brand: Brand) -> Dict:
   return getCABrandEnvironment(brand).endpoints


def _all_endpoints_eu(brand: Brand) -> Dict:
   return getEUBrandEnvironment({"brand": brand}).endpoints


def _all_endpoints_cn(brand: Brand) -> Dict:
   return getCNBrandEnvironment({"brand": brand}).endpoints


def _all_endpoints_au(brand: Brand) -> Dict:
   return getAUBrandEnvironment({"brand": brand}).endpoints


ALL_ENDPOINTS: Dict[str, Callable[[Brand], Dict]] = {
   "CA": _all_endpoints_ca,
   "EU": _all_endpoints_eu,
   "CN": _all_endpoints_cn,
   "AU": _all_endpoints_au,
}

REGION = Literal["US", "CA", "EU", "CN", "AU"]


class REGIONS(str, Enum):
   US = "US"
   CA = "CA"
   EU = "EU"
   CN = "CN"
   AU = "AU"


# Backwards compatibility alias used by CLI and __main__ entrypoint
Region = REGIONS


ChargeTarget = Literal[50, 60, 70, 80, 90, 100]
POSSIBLE_CHARGE_LIMIT_VALUES: List[int] = [50, 60, 70, 80, 90, 100]

DEFAULT_VEHICLE_STATUS_OPTIONS: VehicleStatusOptions = VehicleStatusOptions(
   refresh=False,
   parsed=False,
)

__all__ = [
   "ALL_ENDPOINTS",
   "REGION",
   "REGIONS",
   "Region",
   "ChargeTarget",
   "POSSIBLE_CHARGE_LIMIT_VALUES",
   "DEFAULT_VEHICLE_STATUS_OPTIONS",
   "AustraliaBrandEnvironment",
   "CanadianBrandEnvironment",
   "ChineseBrandEnvironment",
   "EuropeanBrandEnvironment",
]
