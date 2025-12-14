from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, TypedDict, cast

from typing import TYPE_CHECKING

from ..interfaces.common_interfaces import Brand

if TYPE_CHECKING:  # pragma: no cover - type checking only
   from ..controllers.chinese_controller import ChineseBlueLinkConfig


class ChineseBrandEnvironmentEndpoints(TypedDict):
   integration: str
   silentSignIn: str
   session: str
   login: str
   language: str
   redirectUri: str
   token: str


@dataclass(frozen=True)
class ChineseBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   clientId: str
   appId: str
   endpoints: ChineseBrandEnvironmentEndpoints
   basicToken: str
   GCMSenderID: str
   providerDeviceId: str
   pushRegId: str


def getEndpoints(baseUrl: str, clientId: str) -> ChineseBrandEnvironmentEndpoints:
   return {
      "session": f"{baseUrl}/api/v1/user/oauth2/authorize?response_type=code&state=test&client_id={clientId}&redirect_uri={baseUrl}:443/api/v1/user/oauth2/redirect",
      "login": f"{baseUrl}/api/v1/user/signin",
      "language": f"{baseUrl}/api/v1/user/language",
      "redirectUri": f"{baseUrl}:443/api/v1/user/oauth2/redirect",
      "token": f"{baseUrl}/api/v1/user/oauth2/token",
      "integration": f"{baseUrl}/api/v1/user/integrationinfo",
      "silentSignIn": f"{baseUrl}/api/v1/user/silentsignin",
   }


BrandEnvironmentConfig = Dict[Literal["brand"], cast(str, "Brand")]


def getHyundaiEnvironment() -> ChineseBrandEnvironment:
   host = "prd.cn-ccapi.hyundai.com"
   baseUrl = f"https://{host}"
   clientId = "72b3d019-5bc7-443d-a437-08f307cf06e2"
   appId = "ed01581a-380f-48cd-83d4-ed1490c272d0"
   return ChineseBrandEnvironment(
      brand="hyundai",
      host=host,
      baseUrl=baseUrl,
      clientId=clientId,
      appId=appId,
      endpoints=getEndpoints(baseUrl, clientId),
      basicToken="Basic NzJiM2QwMTktNWJjNy00NDNkLWE0MzctMDhmMzA3Y2YwNmUyOnNlY3JldA==",
      GCMSenderID="414998006775",
      providerDeviceId="59af09e554a9442ab8589c9500d04d2e",
      pushRegId="1",
   )


def getKiaEnvironment() -> ChineseBrandEnvironment:
   host = "prd.cn-ccapi.kia.com"
   baseUrl = f"https://{host}"
   clientId = "9d5df92a-06ae-435f-b459-8304f2efcc67"
   appId = "eea8762c-adfc-4ee4-8d7a-6e2452ddf342"
   return ChineseBrandEnvironment(
      brand="kia",
      host=host,
      baseUrl=baseUrl,
      clientId=clientId,
      appId=appId,
      endpoints=getEndpoints(baseUrl, clientId),
      basicToken="Basic OWQ1ZGY5MmEtMDZhZS00MzVmLWI0NTktODMwNGYyZWZjYzY3OnRzWGRrVWcwOEF2MlpaelhPZ1d6Snl4VVQ2eWVTbk5OUWtYWFBSZEtXRUFOd2wxcA==",
      GCMSenderID="345127537656",
      providerDeviceId="32dedba78045415b92db816e805ed47b",
      pushRegId="ogc+GB5gom7zDEQjPhb3lP+bjjM=DG2rQ9Zuq0otwOU7n9y08LKjYpo=",
   )


def getBrandEnvironment(config: "ChineseBlueLinkConfig") -> ChineseBrandEnvironment:
   brand = config["brand"] if isinstance(config, dict) else getattr(config, "brand")
   if brand == "hyundai":
      return getHyundaiEnvironment()
   if brand == "kia":
      return getKiaEnvironment()
   raise Exception(f"Constructor {brand} is not managed.")