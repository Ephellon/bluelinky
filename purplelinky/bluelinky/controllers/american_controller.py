import json
import time
from typing import List

import requests

from bluelinky.constants.america import AmericaBrandEnvironment, getBrandEnvironment
from bluelinky.interfaces.common import VehicleRegisterOptions
from bluelinky.interfaces.american import AmericanBlueLinkyConfig
from bluelinky.logger import logger
from bluelinky.tools.common import manageBluelinkyError
from bluelinky.controllers.controller import SessionController
from bluelinky.vehicles.american_vehicle import AmericanVehicle


class AmericanController(SessionController):
   def __init__(self, userConfig: AmericanBlueLinkyConfig):
      super().__init__(userConfig)
      self._environment: AmericaBrandEnvironment = getBrandEnvironment(userConfig.brand)
      self.vehicles: List[AmericanVehicle] = []
      logger.debug("US Controller created")

   @property
   def environment(self) -> AmericaBrandEnvironment:
      return self._environment

   def refreshAccessToken(self) -> str:
      should_refresh = int(time.time() - self.session.get("tokenExpiresAt", 0)) >= -10
      try:
         if self.session.get("refreshToken") and should_refresh:
            logger.debug("refreshing token")
            response = requests.post(
               f"{self.environment.baseUrl}/v2/ac/oauth/token/refresh",
               json={"refresh_token": self.session.get("refreshToken")},
               headers={
                  "User-Agent": "PostmanRuntime/7.26.10",
                  "client_secret": self.environment.clientSecret,
                  "client_id": self.environment.clientId,
               },
            )
            response.raise_for_status()
            data = response.json()
            self.session["accessToken"] = data.get("access_token", "")
            self.session["refreshToken"] = data.get("refresh_token", "")
            self.session["tokenExpiresAt"] = int(time.time() + int(data.get("expires_in", 0)))
            logger.debug("Token refreshed")
            return "Token refreshed"
         logger.debug("Token not expired, no need to refresh")
         return "Token not expired, no need to refresh"
      except Exception as err:
         raise manageBluelinkyError(err, "AmericanController.refreshAccessToken")

   def login(self) -> str:
      logger.debug("Logging in to the API")
      try:
         response = requests.post(
            f"{self.environment.baseUrl}/v2/ac/oauth/token",
            json={"username": self.userConfig.username, "password": self.userConfig.password},
            headers={
               "User-Agent": "PostmanRuntime/7.26.10",
               "client_id": self.environment.clientId,
               "client_secret": self.environment.clientSecret,
            },
         )
         logger.debug(response.text)
         if response.status_code != 200:
            return "login bad"
         data = response.json()
         self.session["accessToken"] = data.get("access_token", "")
         self.session["refreshToken"] = data.get("refresh_token", "")
         self.session["tokenExpiresAt"] = int(time.time() + int(data.get("expires_in", 0)))
         return "login good"
      except Exception as err:
         raise manageBluelinkyError(err, "AmericanController.login")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[AmericanVehicle]:
      try:
         response = requests.get(
            f"{self.environment.baseUrl}/ac/v2/enrollment/details/{self.userConfig.username}",
            headers={
               "access_token": self.session.get("accessToken", ""),
               "client_id": self.environment.clientId,
               "Host": self.environment.host,
               "User-Agent": "okhttp/3.12.0",
               "payloadGenerated": "20200226171938",
               "includeNonConnectedVehicles": "Y",
            },
         )
         response.raise_for_status()
         data = response.json()
         details = data.get("enrolledVehicleDetails") or []
         self.vehicles = []
         for vehicle in details:
            vehicle_info = vehicle.get("vehicleDetails", {})
            vehicle_config = VehicleRegisterOptions(
               nickname=vehicle_info.get("nickName", ""),
               name=vehicle_info.get("nickName", ""),
               vin=vehicle_info.get("vin", ""),
               regDate=vehicle_info.get("enrollmentDate", ""),
               brandIndicator=vehicle_info.get("brandIndicator", ""),
               regId=vehicle_info.get("regid", ""),
               generation=str(vehicle_info.get("vehicleGeneration", "")),
            )
            ev_status = vehicle_info.get("evStatus")
            if ev_status == "N":
               vehicle_config.engineType = "ICE"
            elif ev_status == "E":
               vehicle_config.engineType = "EV"
            self.vehicles.append(AmericanVehicle(vehicle_config, self))
         return self.vehicles
      except Exception as err:
         raise manageBluelinkyError(err, "AmericanController.getVehicles")

