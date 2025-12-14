from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, List, Literal, TypedDict

from bluelinky.constants.australia import (
   AustraliaBrandEnvironment,
   getBrandEnvironment as getAUBrandEnvironment,
)
from bluelinky.constants.canada import (
   CanadianBrandEnvironment,
   getBrandEnvironment as getCABrandEnvironment,
)
from bluelinky.constants.china import (
   ChineseBrandEnvironment,
   getBrandEnvironment as getCNBrandEnvironment,
)
from bluelinky.constants.europe import (
   EuropeanBrandEnvironment,
   getBrandEnvironment as getEUBrandEnvironment,
)
from bluelinky.interfaces.common_interfaces import Brand, VehicleStatusOptions


class _AllEndpoints(TypedDict):
   CA: Callable[[Brand], CanadianBrandEnvironment["endpoints"]]
   EU: Callable[[Brand], EuropeanBrandEnvironment["endpoints"]]
   CN: Callable[[Brand], ChineseBrandEnvironment["endpoints"]]
   AU: Callable[[Brand], AustraliaBrandEnvironment["endpoints"]]


ALL_ENDPOINTS: _AllEndpoints = {
   "CA": lambda brand: getCABrandEnvironment(brand).endpoints,
   "EU": lambda brand: getEUBrandEnvironment({"brand": brand}).endpoints,
   "CN": lambda brand: getCNBrandEnvironment({"brand": brand}).endpoints,
   "AU": lambda brand: getAUBrandEnvironment({"brand": brand}).endpoints,
}

REGION = Literal["US", "CA", "EU", "CN", "AU"]


class REGIONS(str, Enum):
   US = "US"
   CA = "CA"
   EU = "EU"
   CN = "CN"
   AU = "AU"


ChargeTarget = Literal[50, 60, 70, 80, 90, 100]
POSSIBLE_CHARGE_LIMIT_VALUES: List[int] = [50, 60, 70, 80, 90, 100]

DEFAULT_VEHICLE_STATUS_OPTIONS: VehicleStatusOptions = VehicleStatusOptions(
   refresh=False,
   parsed=False,
)