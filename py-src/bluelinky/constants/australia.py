from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, TypedDict, Union

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
   from ..controllers.australia_controller import AustraliaBlueLinkyConfig
from ..interfaces.common_interfaces import Brand

REGION_CODE = "AU"
from .stamps import StampMode, getStampGenerator


class AustraliaBrandEnvironmentEndpoints(TypedDict):
   integration: str
   silentSignIn: str
   session: str
   login: str
   language: str
   redirectUri: str
   token: str


@dataclass(frozen=True)
class AustraliaBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   clientId: str
   appId: str
   endpoints: AustraliaBrandEnvironmentEndpoints
   basicToken: str
   stamp: Callable[[], str]


def getEndpoints(baseUrl: str, clientId: str) -> AustraliaBrandEnvironmentEndpoints:
   from urllib.parse import quote

   redirect_uri = f"{baseUrl}/api/v1/user/oauth2/redirect"
   return {
      "session": (
         f"{baseUrl}/api/v1/user/oauth2/authorize?response_type=code&client_id={clientId}"
         f"&redirect_uri={quote(redirect_uri, safe='')}&lang=en"
      ),
      "login": f"{baseUrl}/api/v1/user/signin",
      "language": f"{baseUrl}/api/v1/user/language",
      "redirectUri": f"{baseUrl}/api/v1/user/oauth2/redirect",
      "token": f"{baseUrl}/api/v1/user/oauth2/token",
      "integration": f"{baseUrl}/api/v1/user/integrationinfo",
      "silentSignIn": f"{baseUrl}/api/v1/user/silentsignin",
   }


@dataclass(frozen=True)
class EnvironmentConfig:
   stampMode: StampMode
   stampsFile: Optional[str] = None


@dataclass(frozen=True)
class BrandEnvironmentConfig:
   brand: Brand
   stampMode: StampMode = StampMode.LOCAL
   stampsFile: Optional[str] = None


def getHyundaiEnvironment(*, stampMode: StampMode, stampsFile: Optional[str] = None) -> AustraliaBrandEnvironment:
   host = "au-apigw.ccs.hyundai.com.au:8080"
   baseUrl = f"https://{host}"
   clientId = "855c72df-dfd7-4230-ab03-67cbf902bb1c"
   appId = "f9ccfdac-a48d-4c57-bd32-9116963c24ed"  # Android app ID
   return AustraliaBrandEnvironment(
      brand="hyundai",
      host=host,
      baseUrl=baseUrl,
      clientId=clientId,
      appId=appId,
      endpoints=getEndpoints(baseUrl, clientId),
      basicToken=(
         "Basic ODU1YzcyZGYtZGZkNy00MjMwLWFiMDMtNjdjYmY5MDJiYjFjOmU2ZmJ3SE0zMllOYmhRbDBwdmlh"
         "UHAzcmY0dDNTNms5MWVjZUEzTUpMZGJkVGhDTw=="
      ),
      stamp=getStampGenerator(
         appId=appId,
         brand="hyundai",
         mode=stampMode,
         region=REGION_CODE,
         stampHost="https://raw.githubusercontent.com/neoPix/bluelinky-stamps/master/",
         stampsFile=stampsFile,
      ),
   )


def getKiaEnvironment(*, stampMode: StampMode, stampsFile: Optional[str] = None) -> AustraliaBrandEnvironment:
   host = "au-apigw.ccs.kia.com.au:8082"
   baseUrl = f"https://{host}"
   clientId = "8acb778a-b918-4a8d-8624-73a0beb64289"
   appId = "4ad4dcde-be23-48a8-bc1c-91b94f5c06f8"  # Android app ID
   return AustraliaBrandEnvironment(
      brand="hyundai",
      host=host,
      baseUrl=baseUrl,
      clientId=clientId,
      appId=appId,
      endpoints=getEndpoints(baseUrl, clientId),
      basicToken=(
         "Basic OGFjYjc3OGEtYjkxOC00YThkLTg2MjQtNzNhMGJlYjY0Mjg5OjdTY01NbTZmRVlYZGlFUEN4YVBh"
         "UW1nZVlkbFVyZndvaDRBZlhHT3pZSVMyQ3U5VA=="
      ),
      stamp=getStampGenerator(
         appId=appId,
         brand="kia",
         mode=stampMode,
         region=REGION_CODE,
         stampHost="https://raw.githubusercontent.com/neoPix/bluelinky-stamps/master/",
         stampsFile=stampsFile,
      ),
   )


def getBrandEnvironment(
   *,
   brand: Brand,
   stampMode: StampMode = StampMode.LOCAL,
   stampsFile: Optional[str] = None,
) -> AustraliaBrandEnvironment:
   if brand == "hyundai":
      return getHyundaiEnvironment(stampMode=stampMode, stampsFile=stampsFile)
   if brand == "kia":
      return getKiaEnvironment(stampMode=stampMode, stampsFile=stampsFile)
   raise Exception(f"Constructor {brand} is not managed.")