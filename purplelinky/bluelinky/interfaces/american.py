from typing import Any, TypedDict

from bluelinky.interfaces.common import BlueLinkyConfig


class HyundaiResponse(TypedDict, total=False):
   status: str
   result: Any
   errorMessage: str


class TokenResponse(TypedDict, total=False):
   access_token: str
   refresh_token: str
   expires_in: str
   username: str


class VehicleConfig(TypedDict, total=False):
   vin: str | None
   pin: str | None
   token: str | None
   bluelinky: Any


class AmericanEndpoints(TypedDict, total=False):
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


class RequestHeaders(TypedDict, total=False):
   access_token: str | None
   client_id: str
   Host: str
   User_Agent: str
   registrationId: str
   gen: str
   username: str | None
   vin: str
   APPCLOUD_VIN: str
   Language: str
   to: str
   encryptFlag: str
   from_: str
   brandIndicator: str
   bluelinkservicepin: str | None
   offset: str


class AmericanBlueLinkyConfig(BlueLinkyConfig):
   region: str

