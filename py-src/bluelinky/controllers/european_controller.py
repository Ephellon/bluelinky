from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict, Union

import requests

from ..constants.europe import DEFAULT_LANGUAGE, EU_LANGUAGES, getBrandEnvironment
from ..interfaces.common_interfaces import BlueLinkyConfig, Session, VehicleRegisterOptions
from ..logger import logger
from ..tools.common_tools import asyncMap, manageBluelinkyError, uuidV4
from ..vehicles.vehicle import Vehicle
from ..vehicles.european_vehicle import EuropeanVehicle
from .authStrategies.auth_strategy import AuthStrategy, Code
from .authStrategies.european_brandAuth_strategy import EuropeanBrandAuthStrategy
from .authStrategies.european_legacyAuth_strategy import EuropeanLegacyAuthStrategy
from .controller import SessionController


EuropeBlueLinkyConfig = BlueLinkyConfig


class EuropeanVehicleDescription(TypedDict):
   nickname: str
   vehicleName: str
   regDate: str
   vehicleId: str
   ccuCCS2ProtocolSupport: int


class EuropeanController(SessionController[EuropeBlueLinkyConfig]):
   def __init__(self, userConfig: EuropeBlueLinkyConfig):
      super().__init__(userConfig)
      self.userConfig.language = getattr(userConfig, "language", None) or DEFAULT_LANGUAGE
      if self.userConfig.language not in EU_LANGUAGES:
         raise Exception(
            f"The language code {self.userConfig.language} is not managed. Only {', '.join(EU_LANGUAGES)} are."
         )

      # Ensure deviceId exists early (TypeScript sets twice: here and in session default)
      self.session.deviceId = uuidV4()

      self._environment = getBrandEnvironment(userConfig)
      self.authStrategies: Dict[str, AuthStrategy] = {
         "main": EuropeanBrandAuthStrategy(self._environment, self.userConfig.language),
         "fallback": EuropeanLegacyAuthStrategy(self._environment, self.userConfig.language),
      }
      logger.debug("EU Controller created")

   @property
   def environment(self):
      return self._environment

   session: Session = Session(
      accessToken=None,
      refreshToken=None,
      controlToken=None,
      deviceId=uuidV4(),
      tokenExpiresAt=0,
      controlTokenExpiresAt=0,
   )

   vehicles: List[EuropeanVehicle] = []

   def refreshAccessToken(self) -> str:
      shouldRefreshToken = math.floor(time.time() - (self.session.tokenExpiresAt or 0)) >= -10

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
         raise manageBluelinkyError(err, "EuropeController.refreshAccessToken")

      logger.debug("Token refreshed")
      return "Token refreshed"

   def enterPin(self) -> str:
      if self.session.accessToken == "":
         raise Exception("Token not set")

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
         raise manageBluelinkyError(err, "EuropeController.pin")

   def login(self) -> str:
      try:
         if not getattr(self.userConfig, "password", None) or not getattr(self.userConfig, "username", None):
            raise Exception("@EuropeController.login: username and password must be defined.")

         authResult: Optional[Dict[str, Any]] = None

         try:
            logger.debug(f"@EuropeController.login: Trying to sign in with {self.authStrategies['main'].name}")
            authResult = self.authStrategies["main"].login(
               {
                  "password": self.userConfig.password,
                  "username": self.userConfig.username,
               }
            )
         except Exception as e:
            try:
               err_str = str(e)
            except Exception:
               err_str = repr(e)
            logger.error(
               f"@EuropeController.login: sign in with {self.authStrategies['main'].name} failed with error {err_str}"
            )
            logger.debug(f"@EuropeController.login: Trying to sign in with {self.authStrategies['fallback'].name}")
            authResult = self.authStrategies["fallback"].login(
               {
                  "password": self.userConfig.password,
                  "username": self.userConfig.username,
               }
            )

         logger.debug("@EuropeController.login: Authenticated properly with user and password")

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
               "pushType": "APNS",
               "uuid": self.session.deviceId,
            },
         )
         notificationReponse.raise_for_status()

         if notificationReponse is not None:
            notif_body = notificationReponse.json()
            self.session.deviceId = notif_body["resMsg"]["deviceId"]
         logger.debug("@EuropeController.login: Device registered")

         tokenUrl = (
            "https://idpconnect-eu.kia.com/auth/api/v2/user/oauth2/token"
            if self.environment.brand == "kia"
            else "https://idpconnect-eu.hyundai.com/auth/api/v2/user/oauth2/token"
         )

         tokenFormData = {
            "grant_type": "authorization_code",
            "code": authResult["code"] if authResult else None,
            "redirect_uri": f"{self.environment.baseUrl}/api/v1/user/oauth2/redirect",
            "client_id": self.environment.clientId,
            "client_secret": "secret",
         }

         # Cookie jar equivalent: requests' Session with cookies; authStrategies return should be compatible.
         sess = requests.Session()
         cookies = authResult.get("cookies") if authResult else None
         if cookies is not None:
            # Best-effort cookie transfer. If cookies is a requests.cookies.RequestsCookieJar, update works.
            # If it's a dict-like, update will also work.
            try:
               sess.cookies.update(cookies)
            except Exception:
               # If it's a tough-cookie jar-like object, we can't port it faithfully without a shim.
               # This will surface as auth failure, matching call-site behavior.
               pass

         response = sess.post(
            tokenUrl,
            headers={
               "Content-Type": "application/x-www-form-urlencoded",
               "User-Agent": "okhttp/3.10.0",
            },
            data=tokenFormData,
         )

         if response.status_code != 200:
            raise Exception(f"@EuropeController.login: Could not manage to get token: {response.text}")

         if response is not None:
            responseBody = response.json()
            self.session.accessToken = f"Bearer {responseBody['access_token']}"
            self.session.refreshToken = responseBody["refresh_token"]
            self.session.tokenExpiresAt = math.floor(time.time() + responseBody["expires_in"])

         logger.debug("@EuropeController.login: Session defined properly")
         return "Login success"
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeController.login")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      if self.session.accessToken is None:
         raise Exception("Token not set")

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

         def map_vehicle(v: EuropeanVehicleDescription) -> EuropeanVehicle:
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
               ccuCCS2ProtocolSupport=bool(v.get("ccuCCS2ProtocolSupport")),
            )

            logger.debug(f"@EuropeController.getVehicles: Added vehicle {vehicleConfig.id}")
            return EuropeanVehicle(vehicleConfig, self)

         self.vehicles = asyncMap(body["resMsg"]["vehicles"], map_vehicle)
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeController.getVehicles")

      return self.vehicles

   def checkControlToken(self) -> None:
      self.refreshAccessToken()
      if self.session is not None and self.session.controlTokenExpiresAt is not None:
         if (not self.session.controlToken) or (time.time() > self.session.controlTokenExpiresAt):
            self.enterPin()

   def getVehicleHttpService(self):
      # Returns a lightweight callable HTTP service equivalent to got.extend(...)
      self.checkControlToken()

      base_url = self.environment.baseUrl
      headers = {
         **self.defaultHeaders,
         "Authorization": self.session.controlToken,
         "Stamp": self.environment.stamp(),
      }

      class _Service:
         def request(self_inner, method: str, path: str, **kwargs):
            url = path if path.startswith("http") else f"{base_url}{path}"
            h = dict(headers)
            if "headers" in kwargs and kwargs["headers"]:
               h.update(kwargs["headers"])
            kwargs["headers"] = h
            return requests.request(method=method, url=url, **kwargs)

      return _Service()

   def getApiHttpService(self):
      self.refreshAccessToken()

      base_url = self.environment.baseUrl
      headers = {
         **self.defaultHeaders,
         "Stamp": self.environment.stamp(),
      }

      class _Service:
         def request(self_inner, method: str, path: str, **kwargs):
            url = path if path.startswith("http") else f"{base_url}{path}"
            h = dict(headers)
            if "headers" in kwargs and kwargs["headers"]:
               h.update(kwargs["headers"])
            kwargs["headers"] = h
            return requests.request(method=method, url=url, **kwargs)

      return _Service()

   @property
   def defaultHeaders(self) -> Dict[str, Any]:
      offset_hours = -time.timezone / 3600.0
      # Match JS: (new Date().getTimezoneOffset() / 60).toFixed(2)
      # getTimezoneOffset is minutes behind UTC (positive in west). Python's time.timezone is seconds west of UTC.
      # So JS offsetHours = -(time.timezone/3600). We'll format to two decimals like toFixed(2).
      js_like_offset = f"{(-offset_hours):.2f}"

      return {
         "Authorization": self.session.accessToken,
         "offset": js_like_offset,
         "ccsp-device-id": self.session.deviceId,
         "ccsp-application-id": self.environment.appId,
         "Content-Type": "application/json",
      }