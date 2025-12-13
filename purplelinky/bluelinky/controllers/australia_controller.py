from typing import List

from bluelinky.constants.australia import AustraliaBrandEnvironment, getBrandEnvironment
from bluelinky.controllers.controller import SessionController
from bluelinky.logger import logger
from bluelinky.vehicles.vehicle import Vehicle


class AustraliaController(SessionController):
   def __init__(self, userConfig):
      super().__init__(userConfig)
      self._environment: AustraliaBrandEnvironment = getBrandEnvironment({"brand": userConfig.brand})
      logger.debug("AU Controller created")

   @property
   def environment(self) -> AustraliaBrandEnvironment:
      return self._environment

   def refreshAccessToken(self) -> str:
      return "Token not expired, no need to refresh"

   def login(self) -> str:
      raise NotImplementedError("Australia controller authentication not ported yet")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      return []

