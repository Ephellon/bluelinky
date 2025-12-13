from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, List, Literal

from bluelinky.constants.america import AmericaBrandEnvironment, getBrandEnvironment as getUSBrandEnvironment
from bluelinky.constants.canada import CanadianBrandEnvironment, getBrandEnvironment as getCABrandEnvironment
from bluelinky.constants.china import ChineseBrandEnvironment, getBrandEnvironment as getCNBrandEnvironment
from bluelinky.constants.australia import AustraliaBrandEnvironment, getBrandEnvironment as getAUBrandEnvironment
from bluelinky.constants.europe import EuropeanBrandEnvironment, getBrandEnvironment as getEUBrandEnvironment
from bluelinky.interfaces.common import Brand, VehicleStatusOptions


class REGIONS(str, Enum):
   US = "US"
   CA = "CA"
   EU = "EU"
   CN = "CN"
   AU = "AU"


REGION = Literal["US", "CA", "EU", "CN", "AU"]
ChargeTarget = Literal[50, 60, 70, 80, 90, 100]
POSSIBLE_CHARGE_LIMIT_VALUES: List[int] = [50, 60, 70, 80, 90, 100]
DEFAULT_VEHICLE_STATUS_OPTIONS: VehicleStatusOptions = {"refresh": False, "parsed": False}


ALL_ENDPOINTS: Dict[str, Callable[[Brand], Dict[str, str]]] = {
   "CA": lambda brand: getCABrandEnvironment(brand).endpoints,
   "EU": lambda brand: getEUBrandEnvironment({"brand": brand}).endpoints,
   "CN": lambda brand: getCNBrandEnvironment({"brand": brand}).endpoints,
   "AU": lambda brand: getAUBrandEnvironment({"brand": brand}).endpoints,
}

__all__ = [
   "AmericaBrandEnvironment",
   "CanadianBrandEnvironment",
   "ChineseBrandEnvironment",
   "AustraliaBrandEnvironment",
   "EuropeanBrandEnvironment",
   "REGIONS",
   "REGION",
   "ChargeTarget",
   "POSSIBLE_CHARGE_LIMIT_VALUES",
   "DEFAULT_VEHICLE_STATUS_OPTIONS",
   "ALL_ENDPOINTS",
]

