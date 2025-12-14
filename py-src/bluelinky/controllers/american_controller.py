from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import List

import requests

from ..interfaces.common_interfaces import BlueLinkyConfig, VehicleRegisterOptions
from ..logger import logger
from ..tools.common_tools import manageBluelinkyError
from ..vehicles.vehicle import Vehicle
from ..vehicles.american_vehicle import AmericanVehicle
from .controller import SessionController
from ..constants.america import getBrandEnvironment, AmericaBrandEnvironment


@dataclass
class AmericanBlueLinkyConfig(BlueLinkyConfig):
   region: str = "US"


class AmericanController(SessionController[AmericanBlueLinkyConfig]):
   _environment: AmericaBrandEnvironment

   def __init__(self, userConfig: AmericanBlueLinkyConfig):
      super().__init__(userConfig)
      self._environment = getBrandEnvironment(userConfig.brand)
      logger.debug("US Controller created")

   @property
   def environment(self) -> AmericaBrandEnvironment:
      return self._environment

   vehicles: List[AmericanVehicle] = []

   def refreshAccessToken(self) -> str:
      shouldRefreshToken = int(time.time() - self.session.tokenExpiresAt) >= -10

      try:
         if self.session.refreshToken and shouldRefreshToken:
            logger.debug("refreshing token")
            response = requests.post(
               f"{self.environment.baseUrl}/v2/ac/oauth/token/refresh",
               json={
                  "refresh_token": self.session.refreshToken,
               },
               headers={
                  "User-Agent": "PostmanRuntime/7.26.10",
                  "client_secret": self.environment.clientSecret,
                  "client_id": self.environment.clientId,
               },
            )

            body = response.json()
            logger.debug(body)

            self.session.accessToken = body.get("access_token")
            self.session.refreshToken = body.get("refresh_token")
            self.session.tokenExpiresAt = int(time.time() + int(body.get("expires_in")))

            logger.debug("Token refreshed")
            return "Token refreshed"

         logger.debug("Token not expired, no need to refresh")
         return "Token not expired, no need to refresh"
      except Exception as err:
         raise manageBluelinkyError(err, "AmericanController.refreshAccessToken")

   # TODO: come up with a better return value?
   def login(self) -> str:
      logger.debug("Logging in to the API")

      last_body = None
      last_status = None

      for attempt in range(1, 4):
         try:
            response = requests.post(
               f"{self.environment.baseUrl}/v2/ac/oauth/token",
               json={
                  "username": self.userConfig.username,
                  "password": self.userConfig.password,
               },
               headers={
                  "User-Agent": "PostmanRuntime/7.26.10",
                  "client_secret": self.environment.clientSecret,
                  "client_id": self.environment.clientId,
               },
               timeout=30,
            )

            last_status = response.status_code
            try:
               body = response.json()
            except Exception:
               body = {"raw": response.text}
            last_body = body

            logger.debug(body)

            if response.status_code in (502, 503, 504):
               logger.debug(f"Token endpoint error {response.status_code}; retry {attempt}/3")
               time.sleep(1.5 * attempt)
               continue

            if response.status_code != 200:
               raise RuntimeError(f"Login failed ({response.status_code}): {body}")

            self.session.accessToken = body.get("access_token")
            self.session.refreshToken = body.get("refresh_token")
            self.session.tokenExpiresAt = int(time.time() + int(body.get("expires_in", 0)))

            if not self.session.accessToken:
               raise RuntimeError(f"Login response missing access_token: {body}")

            return "login good"

         except Exception as err:
            if attempt >= 3:
               raise manageBluelinkyError(err, "AmericanController.login")
            time.sleep(1.0 * attempt)

      raise RuntimeError(f"Login failed ({last_status}): {last_body}")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      try:
         response = requests.get(
            f"{self.environment.baseUrl}/ac/v2/enrollment/details/{self.userConfig.username}",
            headers={
               "access_token": self.session.accessToken,
               "client_id": self.environment.clientId,
               "Host": self.environment.host,
               "User-Agent": "okhttp/3.12.0",
               "payloadGenerated": "20200226171938",
               "includeNonConnectedVehicles": "Y",
            },
         )

         data = json.loads(response.text)

         if data.get("enrolledVehicleDetails") is None:
            self.vehicles = []
            return self.vehicles

         self.vehicles = []
         for vehicle in data["enrolledVehicleDetails"]:
            vehicleInfo = vehicle["vehicleDetails"]
            vehicleConfig = VehicleRegisterOptions(
               nickname=vehicleInfo.get("nickName"),
               name=vehicleInfo.get("nickName"),
               vin=vehicleInfo.get("vin"),
               regDate=vehicleInfo.get("enrollmentDate"),
               brandIndicator=vehicleInfo.get("brandIndicator"),
               regId=vehicleInfo.get("regid"),
               id=str(
                  vehicleInfo.get("vehicleId")
                  or vehicleInfo.get("regid")
                  or vehicleInfo.get("vin")
                  or ""
               ),
               generation=vehicleInfo.get("vehicleGeneration"),
            )

            if vehicleInfo.get("evStatus") == "N":
               vehicleConfig.engineType = "ICE"  # Internal Combustion Engine
            elif vehicleInfo.get("evStatus") == "E":
               vehicleConfig.engineType = "EV"  # Electric Vehicle

            self.vehicles.append(AmericanVehicle(vehicleConfig, self))

         return self.vehicles
      except Exception as err:
         raise manageBluelinkyError(err, "AmericanController.getVehicles")
