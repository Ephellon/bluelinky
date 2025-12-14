import json
import os
import ssl
from typing import Any, Dict, List, Optional

import requests

from ..constants.canada import CanadianBrandEnvironment, getBrandEnvironment
from ..interfaces.common_interfaces import BlueLinkyConfig, VehicleRegisterOptions
from ..tools.common_tools import manageBluelinkyError
from ..vehicles.vehicle import Vehicle
from ..vehicles.canadian_vehicle import CanadianVehicle
from .controller import SessionController

from ..logger import logger


class CanadianBlueLinkyConfig(BlueLinkyConfig):
   region: str = "CA"


class CanadianController(SessionController[CanadianBlueLinkyConfig]):
   def __init__(self, userConfig: CanadianBlueLinkyConfig):
      super().__init__(userConfig)
      logger.debug("CA Controller created")
      self._environment: CanadianBrandEnvironment = getBrandEnvironment(userConfig.brand)
      self.vehicles: List[CanadianVehicle] = []
      self.timeOffset: float = -(self._get_timezone_offset_minutes() / 60)

   @property
   def environment(self) -> CanadianBrandEnvironment:
      return self._environment

   def refreshAccessToken(self) -> str:
      shouldRefreshToken = (int((self._now_ms() / 1000) - self.session.tokenExpiresAt) >= -10)

      logger.debug("shouldRefreshToken: " + str(shouldRefreshToken))

      if self.session.refreshToken and shouldRefreshToken:
         # TODO: someone should find the refresh token API url then we dont have to do this hack
         # the previously used CA_ENDPOINTS.verifyToken did not refresh it only provided if the token was valid
         self.login()
         logger.debug("Token refreshed")
         return "Token refreshed"

      logger.debug("Token not expired, no need to refresh")
      return "Token not expired, no need to refresh"

   def login(self) -> str:
      logger.info("Begin login request")
      try:
         response = self.request(
            self.environment.endpoints.login,
            {
               "loginId": self.userConfig.username,
               "password": self.userConfig.password,
            },
         )

         logger.debug(response.get("result") if isinstance(response, dict) else response)

         result = response["result"]
         self.session.accessToken = result["accessToken"]
         self.session.refreshToken = result.get("refreshToken")
         self.session.tokenExpiresAt = int((self._now_ms() / 1000) + result["expireIn"])

         return "login good"
      except Exception as err:
         return "error: " + str(err)

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      logger.info("Begin getVehicleList request")
      try:
         response = self.request(self.environment.endpoints.vehicleList, {})

         data = response.get("result", {}) if isinstance(response, dict) else {}
         if data.get("vehicles") is None:
            self.vehicles = []
            return self.vehicles

         for vehicle in data["vehicles"]:
            vehicleConfig = VehicleRegisterOptions(
               nickname=vehicle.get("nickName"),
               name=vehicle.get("nickName"),
               vin=vehicle.get("vin"),
               regDate=vehicle.get("enrollmentDate"),
               brandIndicator=vehicle.get("brandIndicator"),
               regId=vehicle.get("regid"),
               id=vehicle.get("vehicleId"),
               generation=vehicle.get("genType"),
            )
            self.vehicles.append(CanadianVehicle(vehicleConfig, self))

         return self.vehicles
      except Exception as err:
         logger.debug(err)
         return self.vehicles

   # ////////////////////////////////////////////////////////////////////////////
   # Internal
   # ////////////////////////////////////////////////////////////////////////////

   def request(self, endpoint, body: Any, headers: Any = None) -> Optional[Any]:
      if headers is None:
         headers = {}

      logger.debug(f"[{endpoint}] {json.dumps(headers, default=str)} {json.dumps(body, default=str)}")

      # Python port note:
      # The TypeScript implementation conditionally uses undici.fetch for Node >= 21 with TLS relaxations.
      # In Python we mirror the relaxed TLS behavior by using a requests session with verify=False when
      # NODE_TLS_REJECT_UNAUTHORIZED is effectively disabled.
      use_insecure_tls = True
      if use_insecure_tls:
         os.environ["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

      try:
         session = requests.Session()

         req_headers: Dict[str, Any] = {
            "from": self.environment.origin,
            "language": 0 if use_insecure_tls else 1,
            "offset": self.timeOffset,
            "accessToken": self.session.accessToken,
            "Origin": "https://kiaconnect.ca",
            "Referer": "https://kiaconnect.ca/login",
            "Content-Type": "application/json",
         }
         req_headers.update(headers or {})

         response = session.post(
            endpoint,
            data=json.dumps(body),
            headers=req_headers,
            verify=False if use_insecure_tls else True,
            timeout=60,
         )
         response.raise_for_status()
         data = response.json()

         # got branch in TS checks responseHeader.responseCode != 0 and throws responseDesc
         try:
            response_header = data.get("responseHeader") if isinstance(data, dict) else None
            if response_header and response_header.get("responseCode") != 0:
               raise Exception(response_header.get("responseDesc"))
         except Exception:
            raise

         return data
      except Exception as err:
         if use_insecure_tls:
            logger.error(err)
            return None
         raise manageBluelinkyError(err, "CanadianController")

   @staticmethod
   def _now_ms() -> int:
      import time

      return int(time.time() * 1000)

   @staticmethod
   def _get_timezone_offset_minutes() -> int:
      import datetime

      now = datetime.datetime.now().astimezone()
      offset = now.utcoffset()
      if offset is None:
         return 0
      return int(offset.total_seconds() / 60) * -1