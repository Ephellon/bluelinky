from typing import List

from bluelinky.constants.europe import DEFAULT_LANGUAGE, EuropeanBrandEnvironment, EU_LANGUAGES, getBrandEnvironment
from bluelinky.controllers.controller import SessionController
from bluelinky.logger import logger
from bluelinky.vehicles.vehicle import Vehicle


class EuropeanController(SessionController):
   def __init__(self, userConfig):
      super().__init__(userConfig)
      self.userConfig.language = getattr(userConfig, "language", DEFAULT_LANGUAGE)
      self._environment: EuropeanBrandEnvironment = getBrandEnvironment({"brand": userConfig.brand})
      logger.debug("EU Controller created")

   @property
   def environment(self) -> EuropeanBrandEnvironment:
      return self._environment

   def refreshAccessToken(self) -> str:
      return "Token not expired, no need to refresh"

   def login(self) -> str:
      raise NotImplementedError("European controller authentication not ported yet")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      return []

