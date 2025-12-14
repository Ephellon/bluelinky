from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
   from ..index import BlueLinky


@dataclass
class HyundaiResponse:
   status: str
   result: Any
   errorMessage: str


@dataclass
class TokenResponse:
   access_token: str
   refresh_token: str
   expires_in: str
   username: str


@dataclass
class VehicleConfig:
   vin: Optional[str]
   pin: Optional[str]
   token: Optional[str]
   bluelinky: "BlueLinky"


@dataclass
class AmericanEndpoints:
   getToken: str
   validateToken: str
   auth: str
   remoteAction: str
   usageStats: str
   health: str
   messageCenter: str
   myAccount: str
   status: str
   enrollmentStatus: str
   subscriptions: str


@dataclass
class RequestHeaders:
   access_token: Optional[str]
   client_id: str
   Host: str
   User_Agent: str
   registrationId: str
   gen: str
   username: Optional[str]
   vin: str
   APPCLOUD_VIN: str
   Language: str
   to: str
   encryptFlag: str
   from_: str
   brandIndicator: str
   bluelinkservicepin: Optional[str]
   offset: str

   def to_dict(self) -> dict[str, Any]:
      return {
         "access_token": self.access_token,
         "client_id": self.client_id,
         "Host": self.Host,
         "User-Agent": self.User_Agent,
         "registrationId": self.registrationId,
         "gen": self.gen,
         "username": self.username,
         "vin": self.vin,
         "APPCLOUD-VIN": self.APPCLOUD_VIN,
         "Language": self.Language,
         "to": self.to,
         "encryptFlag": self.encryptFlag,
         "from": self.from_,
         "brandIndicator": self.brandIndicator,
         "bluelinkservicepin": self.bluelinkservicepin,
         "offset": self.offset,
      }