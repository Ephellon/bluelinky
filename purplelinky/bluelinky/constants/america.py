from dataclasses import dataclass

from bluelinky.interfaces.common import Brand


@dataclass(frozen=True)
class AmericaBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   clientId: str
   clientSecret: str


def _get_hyundai_environment() -> AmericaBrandEnvironment:
   host = "api.telematics.hyundaiusa.com"
   base_url = f"https://{host}"
   return AmericaBrandEnvironment(
      brand="hyundai",
      host=host,
      baseUrl=base_url,
      clientId="m66129Bb-em93-SPAHYN-bZ91-am4540zp19920",
      clientSecret="v558o935-6nne-423i-baa8",
   )


def _get_kia_environment() -> AmericaBrandEnvironment:
   host = "api.owners.kia.com"
   path = "/apigw/v1/"
   base_url = f"https://{host}{path}"
   return AmericaBrandEnvironment(
      brand="kia",
      host=host,
      baseUrl=base_url,
      clientId="MWAMOBILE",
      clientSecret="98er-w34rf-ibf3-3f6h",
   )


def getBrandEnvironment(brand: Brand) -> AmericaBrandEnvironment:
   if brand == "hyundai":
      return _get_hyundai_environment()
   if brand == "kia":
      return _get_kia_environment()
   raise ValueError(f"Constructor {brand} is not managed.")

