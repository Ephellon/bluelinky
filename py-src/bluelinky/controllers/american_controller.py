from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import List

import requests

from ..interfaces import BlueLinkyConfig, Session, VehicleRegisterOptions
from ..logger import logger
from .controller import SessionController


@dataclass(frozen=True)
class AmericaBrandEnvironment:
   brand: str
   host: str
   base_url: str
   client_id: str
   client_secret: str


def _get_brand_environment(brand: str) -> AmericaBrandEnvironment:
   if brand == "hyundai":
      host = "api.telematics.hyundaiusa.com"
      base_url = f"https://{host}"
      return AmericaBrandEnvironment(
         brand="hyundai",
         host=host,
         base_url=base_url,
         client_id="m66129Bb-em93-SPAHYN-bZ91-am4540zp19920",
         client_secret="v558o935-6nne-423i-baa8",
      )
   if brand == "kia":
      host = "api.owners.kia.com"
      base_url = f"https://{host}/apigw/v1/"
      return AmericaBrandEnvironment(
         brand="kia",
         host=host,
         base_url=base_url,
         client_id="MWAMOBILE",
         client_secret="98er-w34rf-ibf3-3f6h",
      )
   raise ValueError(f"Constructor {brand} is not managed.")


def _manage_bluelinky_error(err: Exception, ctx: str) -> RuntimeError:
   return RuntimeError(f"{ctx}: {err}")


class AmericanController(SessionController[BlueLinkyConfig]):
   def __init__(self, user_config: BlueLinkyConfig):
      super().__init__(user_config)
      self._environment = _get_brand_environment(user_config.brand.value)
      logger.debug("US Controller created")
      self._vehicles: List["AmericanVehicle"] = []

   @property
   def environment(self) -> AmericaBrandEnvironment:
      return self._environment

   def refresh_access_token(self) -> str:
      should_refresh_token = int(time.time() - self.session.token_expires_at) >= -10
      try:
         if self.session.refresh_token and should_refresh_token:
            logger.debug("refreshing token")
            response = requests.post(
               f"{self.environment.base_url}/v2/ac/oauth/token/refresh",
               json={"refresh_token": self.session.refresh_token},
               headers={
                  "User-Agent": "PostmanRuntime/7.26.10",
                  "client_secret": self.environment.client_secret,
                  "client_id": self.environment.client_id,
               },
            )
            response.raise_for_status()
            body = response.json()
            logger.debug(body)
            self.session.access_token = body.get("access_token")
            self.session.refresh_token = body.get("refresh_token")
            self.session.token_expires_at = int(time.time() + int(body.get("expires_in", 0)))
            logger.debug("Token refreshed")
            return "Token refreshed"
         logger.debug("Token not expired, no need to refresh")
         return "Token not expired, no need to refresh"
      except Exception as err:
         raise _manage_bluelinky_error(err, "AmericanController.refreshAccessToken")

   def login(self) -> str:
      logger.debug("Logging in to the API")
      try:
         response = requests.post(
            f"{self.environment.base_url}/v2/ac/oauth/token",
            json={
               "username": self.user_config.username,
               "password": self.user_config.password,
            },
            headers={
               "User-Agent": "PostmanRuntime/7.26.10",
               "client_id": self.environment.client_id,
               "client_secret": self.environment.client_secret,
            },
         )
         if response.status_code != 200:
            return "login bad"
         body = response.json()
         logger.debug(body)
         self.session.access_token = body.get("access_token")
         self.session.refresh_token = body.get("refresh_token")
         self.session.token_expires_at = int(time.time() + int(body.get("expires_in", 0)))
         return "login good"
      except Exception as err:
         raise _manage_bluelinky_error(err, "AmericanController.login")

   def logout(self) -> str:
      return "OK"

   def get_vehicles(self) -> List["Vehicle"]:
      from ..vehicles.american_vehicle import AmericanVehicle

      try:
         response = requests.get(
            f"{self.environment.base_url}/ac/v2/enrollment/details/{self.user_config.username}",
            headers={
               "access_token": self.session.access_token or "",
               "client_id": self.environment.client_id,
               "Host": self.environment.host,
               "User-Agent": "okhttp/3.12.0",
               "payloadGenerated": "20200226171938",
               "includeNonConnectedVehicles": "Y",
            },
         )
         response.raise_for_status()
         data = response.json()
         if data.get("enrolledVehicleDetails") is None:
            self._vehicles = []
            return self._vehicles
         vehicles = []
         for vehicle in data.get("enrolledVehicleDetails", []):
            vehicle_info = vehicle.get("vehicleDetails", {})
            vehicle_config = VehicleRegisterOptions(
               nickname=vehicle_info.get("nickName", ""),
               name=vehicle_info.get("nickName", ""),
               vin=vehicle_info.get("vin", ""),
               brand_indicator=vehicle_info.get("brandIndicator", ""),
               id=vehicle_info.get("regid", ""),
               generation=str(vehicle_info.get("vehicleGeneration", "")),
            )
            setattr(vehicle_config, "regDate", vehicle_info.get("enrollmentDate"))
            ev_status = vehicle_info.get("evStatus")
            if ev_status == "N":
               setattr(vehicle_config, "engineType", "ICE")
            elif ev_status == "E":
               setattr(vehicle_config, "engineType", "EV")
            vehicles.append(AmericanVehicle(vehicle_config, self))
         self._vehicles = vehicles
         return self._vehicles
      except Exception as err:
         raise _manage_bluelinky_error(err, "AmericanController.getVehicles")


Vehicle = object

