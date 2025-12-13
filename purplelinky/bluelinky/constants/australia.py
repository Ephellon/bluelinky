from dataclasses import dataclass
from typing import Any, Dict

from bluelinky.interfaces.common import Brand


@dataclass(frozen=True)
class AustraliaBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   endpoints: Dict[str, str]


def getBrandEnvironment(config: Dict[str, Any]) -> AustraliaBrandEnvironment:
   brand: Brand = config.get("brand", "hyundai")
   host = "api.au.bluelink"
   base_url = f"https://{host}"
   return AustraliaBrandEnvironment(brand=brand, host=host, baseUrl=base_url, endpoints={})

