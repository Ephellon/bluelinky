from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from bluelinky.interfaces.common import Brand

EULanguages = List[str]
EU_LANGUAGES: List[str] = [
   "cs",
   "da",
   "nl",
   "en",
   "fi",
   "fr",
   "de",
   "it",
   "pl",
   "hu",
   "no",
   "sk",
   "es",
   "sv",
]
DEFAULT_LANGUAGE = "en"


@dataclass(frozen=True)
class EuropeanBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   clientId: str
   appId: str
   endpoints: Dict[str, str]
   basicToken: str = ""
   GCMSenderID: str = ""
   stamp: Callable[[], str] | None = None

   def brandAuthUrl(self, options: Dict[str, Any]) -> str:
      return ""


def getBrandEnvironment(config: Dict[str, Any]) -> EuropeanBrandEnvironment:
   brand: Brand = config.get("brand", "hyundai")
   host = "prd.eu-ccapi.hyundai.com:8080" if brand == "hyundai" else "prd.eu-ccapi.kia.com:8080"
   base_url = f"https://{host}"
   client_id = "6d477c38-3ca4-4cf3-9557-2a1929a94654"
   app_id = "1eba27d2-9a5b-4eba-8ec7-97eb6c62fb51"
   return EuropeanBrandEnvironment(
      brand=brand,
      host=host,
      baseUrl=base_url,
      clientId=client_id,
      appId=app_id,
      endpoints={},
   )

