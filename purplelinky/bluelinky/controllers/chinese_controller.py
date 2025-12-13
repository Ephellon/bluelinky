from typing import List

from bluelinky.constants.china import ChineseBrandEnvironment, getBrandEnvironment
from bluelinky.controllers.controller import SessionController
from bluelinky.logger import logger
from bluelinky.vehicles.vehicle import Vehicle


class ChineseController(SessionController):
   def __init__(self, userConfig):
      super().__init__(userConfig)
      self._environment: ChineseBrandEnvironment = getBrandEnvironment({"brand": userConfig.brand})
      logger.debug("CN Controller created")

   @property
   def environment(self) -> ChineseBrandEnvironment:
      return self._environment

   def refreshAccessToken(self) -> str:
      return "Token not expired, no need to refresh"

   def login(self) -> str:
      raise NotImplementedError("Chinese controller authentication not ported yet")

   def logout(self) -> str:
      return "OK"

   def getVehicles(self) -> List[Vehicle]:
      return []

