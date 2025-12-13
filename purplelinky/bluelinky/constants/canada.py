from dataclasses import dataclass
from typing import Dict

from bluelinky.interfaces.common import Brand


@dataclass(frozen=True)
class CanadianBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   origin: str
   endpoints: Dict[str, str]


def _get_endpoints(base_url: str) -> Dict[str, str]:
   return {
      "login": f"{base_url}/tods/api/lgn",
      "logout": f"{base_url}/tods/api/lgout",
      "vehicleList": f"{base_url}/tods/api/vhcllst",
      "vehicleInfo": f"{base_url}/tods/api/sltvhcl",
      "status": f"{base_url}/tods/api/lstvhclsts",
      "remoteStatus": f"{base_url}/tods/api/rltmvhclsts",
      "lock": f"{base_url}/tods/api/drlck",
      "unlock": f"{base_url}/tods/api/drulck",
      "start": f"{base_url}/tods/api/evc/rfon",
      "stop": f"{base_url}/tods/api/evc/rfoff",
      "startCharge": f"{base_url}/tods/api/evc/rcstrt",
      "stopCharge": f"{base_url}/tods/api/evc/rcstp",
      "setChargeTarget": f"{base_url}/tods/api/evc/setsoc",
      "locate": f"{base_url}/tods/api/fndmcr",
      "hornlight": f"{base_url}/tods/api/hornlight",
      "verifyAccountToken": f"{base_url}/tods/api/vrfyacctkn",
      "verifyPin": f"{base_url}/tods/api/vrfypin",
      "verifyToken": f"{base_url}/tods/api/vrfytnc",
   }


def _get_environment(host: str) -> Dict[str, object]:
   base_url = f"https://{host}"
   return {
      "host": host,
      "baseUrl": base_url,
      "origin": "SPA",
      "endpoints": _get_endpoints(base_url),
   }


def _get_hyundai_environment() -> CanadianBrandEnvironment:
   return CanadianBrandEnvironment(brand="hyundai", **_get_environment("mybluelink.ca"))


def _get_kia_environment() -> CanadianBrandEnvironment:
   return CanadianBrandEnvironment(brand="hyundai", **_get_environment("kiaconnect.ca"))


def getBrandEnvironment(brand: Brand) -> CanadianBrandEnvironment:
   if brand == "hyundai":
      return _get_hyundai_environment()
   if brand == "kia":
      return _get_kia_environment()
   raise ValueError(f"Constructor {brand} is not managed.")

