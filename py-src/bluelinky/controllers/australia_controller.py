import json
import math
import random
import string
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from ..constants.australia import AustraliaBrandEnvironment, getBrandEnvironment
from ..constants.stamps import StampMode
from ..interfaces.common_interfaces import BlueLinkyConfig, Session, VehicleRegisterOptions
from ..logger import logger
from ..tools.common_tools import asyncMap, manageBluelinkyError, uuidV4
from ..vehicles.australia_vehicle import AustraliaVehicle
from ..vehicles.vehicle import Vehicle
from .authStrategies.australia_authStrategy import AustraliaAuthStrategy
from .authStrategies.authStrategy import Code
from .controller import SessionController


@dataclass
class AustraliaBlueLinkyConfig(BlueLinkyConfig):
   region: str = "AU"
   stampMode: Optional[StampMode] = None
   stampsFile: Optional[str] = None


class AustraliaController(SessionController[AustraliaBlueLinkyConfig]):
   def __init__(self, userConfig: AustraliaBlueLinkyConfig):
      super().__init__(userConfig)
      self.session.deviceId = uuidV4()
      self._environment: AustraliaBrandEnvironment = getBrandEnvironment(userConfig)
      self.authStrategy: AustraliaAuthStrategy = AustraliaAuthStrategy(self._environment)
      logger.debug("AU Controller created")

      self.vehicles: List[AustraliaVehicle] = []

   @property
   def environment(self) -> AustraliaBrandEnvironment:
      return self._environment

   session: Session = Session(
      accessToken=None,
      refreshToken=None,
      controlToken=None,
      deviceId=uuidV4(),
      tokenExpiresAt=0,
      controlTokenExpiresAt=0,
   )

   def refreshAccessToken(self) -> str:
      shouldRefreshToken = math.floor(time.time() - self.session.tokenExpiresAt) >= -10

      if not self.session.refreshToken:
         logger.debug("Need refresh token to refresh access token. Use login()")
         return "Need refresh token to refresh access token. Use login()"

      if not shouldRefreshToken:
         logger.debug("Token not expired, no need to refresh")
         return "Token not expired, no need to refresh"

      form_data = {
         "grant_type": "refresh_token",
         "redirect_uri": "https://www.getpostman.com/oauth2/callback",  # Oversight from Hyundai developers
         "refresh_token": self.session.refreshToken,
      }

      try:
         response = requests.post(
            self.environment.endpoints.token,
            headers={
               "Authorization": self.environment.basicToken,
               "Content-Type": "application/x-www-form-urlencoded",
               "Host": self.environment.host,
               "Connection": "Keep-Alive",
               "Accept-Encoding": "gzip",
               "User-Agent": "okhttp/3.10.0",
            },
            data=form_data,
         )

         if response.status_code != 200:
            logger.debug(f"Refresh token failed: {response.text}")
            return f"Refresh token failed: {response.text}"

         responseBody = response.json()
         self.session.accessToken = "Bearer " + responseBody["access_token"]
         self.session.tokenExpiresAt = math.floor(time.time() + responseBody["expires_in"])
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaController.refreshAccessToken")

      logger.debug("Token refreshed")
      return "Token refreshed"

   def enterPin(self) -> str:
      if self.session.accessToken == "":
         raise "Token not set"

      try:
         response = requests.put(
            f"{self.environment.baseUrl}/api/v1/user/pin",
            headers={
               "Authorization": self.session.accessToken,
               "Content-Type": "application/json",
            },
            json={
               "deviceId": self.session.deviceId,
               "pin": self.userConfig.pin,
            },
         )
         response.raise_for_status()
         body = response.json()

         self.session.controlToken = "Bearer " + body["controlToken"]
         self.session.controlTokenExpiresAt = math.floor(time.time() + body["expiresTime"])
         return "PIN entered OK, The pin is valid for 10 minutes"
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaController.pin")

   def login(self) -> str:
      try:
         if not getattr(self.userConfig, "password", None) or not getattr(self.userConfig, "username", None):
            raise Exception("@AustraliaController.login: username and password must be defined.")

         authResult: Optional[Dict[str, Any]] = None
         try:
            logger.debug(f"@AustraliaController.login: Trying to sign in with {self.authStrategy.name}")
            authResult = self.authStrategy.login(
               {
                  "password": self.userConfig.password,
                  "username": self.userConfig.username,
               }
            )
         except Exception as e:
            raise Exception(
               f"@AustraliaController.login: sign in with {self.authStrategy.name} failed with error {str(e)}"
            )

         logger.debug("@AustraliaController.login: Authenticated properly with user and password")

         def genRanHex(size: int) -> str:
            return "".join(random.choice("0123456789abcdef") for _ in range(size))

         notificationReponse = requests.post(
            f"{self.environment.baseUrl}/api/v1/spa/notifications/register",
            headers={
               "ccsp-service-id": self.environment.clientId,
               "Content-Type": "application/json;charset=UTF-8",
               "Host": self.environment.host,
               "Connection": "Keep-Alive",
               "Accept-Encoding": "gzip",
               "User-Agent": "okhttp/3.10.0",
               "ccsp-application-id": self.environment.appId,
               "Stamp": self.environment.stamp(),
            },
            json={
               "pushRegId": genRanHex(64),
               "pushType": "GCM",
               "uuid": self.session.deviceId,
            },
         )
         notificationReponse.raise_for_status()

         if notificationReponse is not None:
            nb = notificationReponse.json()
            self.session.deviceId = nb["resMsg"]["deviceId"]

         logger.debug("@AustraliaController.login: Device registered")

         form_data = {
            "grant_type": "authorization_code",
            "redirect_uri": self.environment.endpoints.redirectUri,
            "code": authResult["code"] if isinstance(authResult, dict) else None,
         }

         cookies = None
         if isinstance(authResult, dict):
            cookies = authResult.get("cookies")
         session = requests.Session()
         if cookies is not None:
            # tough-cookie CookieJar equivalent behavior is handled by auth strategy in Python;
            # if it returns a requests-compatible cookie jar, attach it.
            try:
               session.cookies = cookies
            except Exception:
               pass

         response = session.post(
            self.environment.endpoints.token,
            headers={
               "Authorization": self.environment.basicToken,
               "Content-Type": "application/x-www-form-urlencoded",
               "Host": self.environment.host,
               "Connection": "Keep-Alive",
               "Accept-Encoding": "gzip",
               "User-Agent": "okhttp/3.10.0",
               "grant_type": "authorization_code",
               "ccsp-application-id": self.environment.appId,
               "Stamp": self.environment.stamp(),
            },
            data=form_data,
         )

         if response.status_code != 200:
            raise Exception(f"@AustraliaController.login: Could not manage to get token: {response.text}")

         if response is not None:
            responseBody = response.json()
            self.session.accessToken = f"Bearer {responseBody['access_token']}"
            self.session.refreshToken = responseBody["refresh_token"]
            self.session.tokenExpiresAt = math.floor(time.time() + responseBody["expires_in"])

         logger.debug("@AustraliaController.login: Session defined properly")

         return "Login success"
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaController.login")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      if self.session.accessToken is None:
         raise "Token not set"

      try:
         response = requests.get(
            f"{self.environment.baseUrl}/api/v1/spa/vehicles",
            headers={
               **self.defaultHeaders,
               "Stamp": self.environment.stamp(),
            },
         )
         response.raise_for_status()
         body = response.json()

         vehicles_desc = body["resMsg"]["vehicles"]

         def _map_vehicle(v: Dict[str, Any]) -> AustraliaVehicle:
            vehicleProfileReponse = requests.get(
               f"{self.environment.baseUrl}/api/v1/spa/vehicles/{v['vehicleId']}/profile",
               headers={
                  **self.defaultHeaders,
                  "Stamp": self.environment.stamp(),
               },
            )
            vehicleProfileReponse.raise_for_status()
            vehicleProfile = vehicleProfileReponse.json()["resMsg"]

            vehicleConfig = VehicleRegisterOptions(
               nickname=v["nickname"],
               name=v["vehicleName"],
               regDate=v["regDate"],
               brandIndicator="H",
               id=v["vehicleId"],
               vin=vehicleProfile["vinInfo"][0]["basic"]["vin"],
               generation=vehicleProfile["vinInfo"][0]["basic"]["modelYear"],
            )

            logger.debug(f"@AustraliaController.getVehicles: Added vehicle {vehicleConfig.id}")
            return AustraliaVehicle(vehicleConfig, self)

         self.vehicles = asyncMap(vehicles_desc, _map_vehicle)
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaController.getVehicles")

      return self.vehicles

   def checkControlToken(self) -> None:
      self.refreshAccessToken()
      if getattr(self.session, "controlTokenExpiresAt", None) is not None:
         if (not self.session.controlToken) or (time.time() > float(self.session.controlTokenExpiresAt)):
            self.enterPin()

   def getVehicleHttpService(self):
      self.checkControlToken()

      controller = self

      class _VehicleHttpService:
         def __init__(self):
            self.baseUrl = controller.environment.baseUrl

         def request(self, method: str, path: str, **kwargs):
            headers = kwargs.pop("headers", {}) or {}
            merged_headers = {
               **controller.defaultHeaders,
               "Authorization": controller.session.controlToken,
               "Stamp": controller.environment.stamp(),
               **headers,
            }
            url = path if path.startswith("http") else f"{self.baseUrl}{path}"
            return requests.request(method=method, url=url, headers=merged_headers, **kwargs)

         def get(self, path: str, **kwargs):
            return self.request("GET", path, **kwargs)

         def post(self, path: str, **kwargs):
            return self.request("POST", path, **kwargs)

         def put(self, path: str, **kwargs):
            return self.request("PUT", path, **kwargs)

         def delete(self, path: str, **kwargs):
            return self.request("DELETE", path, **kwargs)

      return _VehicleHttpService()

   def getApiHttpService(self):
      self.refreshAccessToken()

      controller = self

      class _ApiHttpService:
         def __init__(self):
            self.baseUrl = controller.environment.baseUrl

         def request(self, method: str, path: str, **kwargs):
            headers = kwargs.pop("headers", {}) or {}
            merged_headers = {
               **controller.defaultHeaders,
               "Stamp": controller.environment.stamp(),
               **headers,
            }
            url = path if path.startswith("http") else f"{self.baseUrl}{path}"
            return requests.request(method=method, url=url, headers=merged_headers, **kwargs)

         def get(self, path: str, **kwargs):
            return self.request("GET", path, **kwargs)

         def post(self, path: str, **kwargs):
            return self.request("POST", path, **kwargs)

         def put(self, path: str, **kwargs):
            return self.request("PUT", path, **kwargs)

         def delete(self, path: str, **kwargs):
            return self.request("DELETE", path, **kwargs)

      return _ApiHttpService()

   @property
   def defaultHeaders(self) -> Dict[str, Any]:
      offset_hours = (time.timezone / 3600.0) * -1.0
      try:
         # Match JS Date().getTimezoneOffset() (minutes behind UTC, positive in the Americas)
         import datetime as _dt

         now = _dt.datetime.now(_dt.timezone.utc).astimezone()
         offset_td = now.utcoffset() or _dt.timedelta(0)
         offset_hours = -(offset_td.total_seconds() / 60.0) / 60.0
      except Exception:
         pass

      return {
         "Authorization": self.session.accessToken,
         "offset": f"{offset_hours:.2f}",
         "ccsp-device-id": self.session.deviceId,
         "ccsp-application-id": self.environment.appId,
         "Content-Type": "application/json",
      }