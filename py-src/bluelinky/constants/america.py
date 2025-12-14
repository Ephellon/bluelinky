from __future__ import annotations

from dataclasses import dataclass

from ..interfaces.common_interfaces import Brand


@dataclass(frozen=True)
class AmericaBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   clientId: str
   clientSecret: str


def getHyundaiEnvironment() -> AmericaBrandEnvironment:
   host = "api.telematics.hyundaiusa.com"
   baseUrl = f"https://{host}"
   return AmericaBrandEnvironment(
      brand="hyundai",
      host=host,
      baseUrl=baseUrl,
      clientId="m66129Bb-em93-SPAHYN-bZ91-am4540zp19920",
      clientSecret="v558o935-6nne-423i-baa8",
   )


def getKiaEnvironment() -> AmericaBrandEnvironment:
   host = "api.owners.kia.com"
   path = "/apigw/v1/"
   baseUrl = f"https://{host}{path}"
   return AmericaBrandEnvironment(
      brand="kia",
      host=host,
      baseUrl=baseUrl,
      clientId="MWAMOBILE",
      clientSecret="98er-w34rf-ibf3-3f6h",
   )


def getBrandEnvironment(brand: Brand) -> AmericaBrandEnvironment:
   if brand == "hyundai":
      return getHyundaiEnvironment()
   if brand == "kia":
      return getKiaEnvironment()
   raise Exception(f"Constructor {brand} is not managed.")