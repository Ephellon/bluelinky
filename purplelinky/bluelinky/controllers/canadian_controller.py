from typing import List

from bluelinky.constants.canada import CanadianBrandEnvironment, getBrandEnvironment
from bluelinky.controllers.controller import SessionController
from bluelinky.interfaces.common import VehicleRegisterOptions
from bluelinky.logger import logger
from bluelinky.vehicles.vehicle import Vehicle


class CanadianController(SessionController):
   def __init__(self, userConfig):
      super().__init__(userConfig)
      self._environment: CanadianBrandEnvironment = getBrandEnvironment(userConfig.brand)
      logger.debug("CA Controller created")

   @property
   def environment(self) -> CanadianBrandEnvironment:
      return self._environment

   def login(self) -> str:
      raise NotImplementedError("Canadian controller authentication not ported yet")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      return []

   def refreshAccessToken(self) -> str:
      return "Token not expired, no need to refresh"

