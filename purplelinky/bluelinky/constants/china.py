from dataclasses import dataclass
from typing import Any, Dict

from bluelinky.interfaces.common import Brand


@dataclass(frozen=True)
class ChineseBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   endpoints: Dict[str, str]


def getBrandEnvironment(config: Dict[str, Any]) -> ChineseBrandEnvironment:
   brand: Brand = config.get("brand", "hyundai")
   host = "api.china.bluelink"
   base_url = f"https://{host}"
   return ChineseBrandEnvironment(brand=brand, host=host, baseUrl=base_url, endpoints={})

