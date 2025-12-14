from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Literal, Optional, Protocol, TypedDict

from ..constants import REGIONS
from ..controllers.european_controller import EuropeBlueLinkyConfig
from ..interfaces.common_interfaces import Brand
from .stamps import StampMode, getStampGenerator

EULanguages = Literal[
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

EU_LANGUAGES: list[EULanguages] = [
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

DEFAULT_LANGUAGE: EULanguages = "en"


class _EuropeanBrandEndpoints(TypedDict):
   integration: str
   silentSignIn: str
   session: str
   login: str
   language: str
   redirectUri: str
   token: str


class _BrandAuthUrlOptions(TypedDict):
   language: EULanguages
   serviceId: str
   userId: str


class _StampCallable(Protocol):
   def __call__(self) -> str: ...


@dataclass(frozen=True)
class EuropeanBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   clientId: str
   appId: str
   endpoints: _EuropeanBrandEndpoints
   basicToken: str
   GCMSenderID: str
   stamp: _StampCallable
   brandAuthUrl: Callable[[_BrandAuthUrlOptions], str]


def getEndpoints(baseUrl: str, clientId: str) -> _EuropeanBrandEndpoints:
   return {
      "session": f"{baseUrl}/api/v1/user/oauth2/authorize?response_type=code&state=test&client_id={clientId}&redirect_uri={baseUrl}/api/v1/user/oauth2/redirect",
      "login": f"{baseUrl}/api/v1/user/signin",
      "language": f"{baseUrl}/api/v1/user/language",
      "redirectUri": f"{baseUrl}/api/v1/user/oauth2/redirect",
      "token": f"{baseUrl}/api/v1/user/oauth2/token",
      "integration": f"{baseUrl}/api/v1/user/integrationinfo",
      "silentSignIn": f"{baseUrl}/api/v1/user/silentsignin",
   }


def getHyundaiEnvironment(
   *,
   stampMode: StampMode,
   stampsFile: Optional[str] = None,
) -> EuropeanBrandEnvironment:
   host = "prd.eu-ccapi.hyundai.com:8080"
   baseUrl = f"https://{host}"
   clientId = "6d477c38-3ca4-4cf3-9557-2a1929a94654"
   appId = "1eba27d2-9a5b-4eba-8ec7-97eb6c62fb51"

   def _brandAuthUrl(options: _BrandAuthUrlOptions) -> str:
      language = options["language"]
      serviceId = options["serviceId"]
      userId = options["userId"]
      newAuthClientId = "64621b96-0f0d-11ec-82a8-0242ac130003"
      return (
         "https://eu-account.hyundai.com/auth/realms/euhyundaiidm/protocol/openid-connect/auth"
         f"?client_id={newAuthClientId}"
         "&scope=openid%20profile%20email%20phone"
         "&response_type=code"
         "&hkid_session_reset=true"
         f"&redirect_uri={baseUrl}/api/v1/user/integration/redirect/login"
         f"&ui_locales={language}"
         f"&state={serviceId}:{userId}"
      )

   return EuropeanBrandEnvironment(
      brand="hyundai",
      host=host,
      baseUrl=baseUrl,
      clientId=clientId,
      appId=appId,
      endpoints=getEndpoints(baseUrl, clientId),
      basicToken="Basic NmQ0NzdjMzgtM2NhNC00Y2YzLTk1NTctMmExOTI5YTk0NjU0OktVeTQ5WHhQekxwTHVvSzB4aEJDNzdXNlZYaG10UVI5aVFobUlGampvWTRJcHhzVg==",
      GCMSenderID="414998006775",
      stamp=getStampGenerator(
         {
            "appId": appId,
            "brand": "hyundai",
            "mode": stampMode,
            "region": REGIONS.EU,
            "stampHost": "https://raw.githubusercontent.com/neoPix/bluelinky-stamps/master/",
            "stampsFile": stampsFile,
         }
      ),
      brandAuthUrl=_brandAuthUrl,
   )


def getKiaEnvironment(
   *,
   stampMode: StampMode,
   stampsFile: Optional[str] = None,
) -> EuropeanBrandEnvironment:
   host = "prd.eu-ccapi.kia.com:8080"
   baseUrl = f"https://{host}"
   clientId = "fdc85c00-0a2f-4c64-bcb4-2cfb1500730a"
   appId = "a2b8469b-30a3-4361-8e13-6fceea8fbe74"

   def _brandAuthUrl(options: _BrandAuthUrlOptions) -> str:
      language = options["language"]
      serviceId = options["serviceId"]
      userId = options["userId"]
      newAuthClientId = "572e0304-5f8d-4b4c-9dd5-41aa84eed160"
      return (
         "https://eu-account.kia.com/auth/realms/eukiaidm/protocol/openid-connect/auth"
         f"?client_id={newAuthClientId}"
         "&scope=openid%20profile%20email%20phone"
         "&response_type=code"
         "&hkid_session_reset=true"
         f"&redirect_uri={baseUrl}/api/v1/user/integration/redirect/login"
         f"&ui_locales={language}"
         f"&state={serviceId}:{userId}"
      )

   return EuropeanBrandEnvironment(
      brand="kia",
      host=host,
      baseUrl=baseUrl,
      clientId=clientId,
      appId=appId,
      endpoints=getEndpoints(baseUrl, clientId),
      basicToken="Basic ZmRjODVjMDAtMGEyZi00YzY0LWJjYjQtMmNmYjE1MDA3MzBhOnNlY3JldA==",
      GCMSenderID="345127537656",
      stamp=getStampGenerator(
         {
            "appId": appId,
            "brand": "kia",
            "mode": stampMode,
            "region": REGIONS.EU,
            "stampHost": "https://raw.githubusercontent.com/neoPix/bluelinky-stamps/master/",
            "stampsFile": stampsFile,
         }
      ),
      brandAuthUrl=_brandAuthUrl,
   )


def getBrandEnvironment(
   *,
   brand: Brand,
   stampMode: StampMode = StampMode.DISTANT,
   stampsFile: Optional[str] = None,
) -> EuropeanBrandEnvironment:
   if brand == "hyundai":
      return getHyundaiEnvironment(stampMode=stampMode, stampsFile=stampsFile)
   if brand == "kia":
      return getKiaEnvironment(stampMode=stampMode, stampsFile=stampsFile)
   raise Exception(f"Constructor {brand} is not managed.")