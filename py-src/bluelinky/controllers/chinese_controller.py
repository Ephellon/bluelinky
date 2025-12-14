from __future__ import annotations

from typing import List

from ..constants.china import ChineseBrandEnvironment, getBrandEnvironment
from ..interfaces.common_interfaces import BlueLinkyConfig
from ..logger import logger
from ..vehicles.vehicle import Vehicle
from ..vehicles.chinese_vehicle import ChineseVehicle
from .controller import SessionController


class ChineseBlueLinkConfig(BlueLinkyConfig):
   region: str = "CN"


class ChineseController(SessionController[ChineseBlueLinkConfig]):
   def __init__(self, userConfig: ChineseBlueLinkConfig):
      super().__init__(userConfig)
      self._environment: ChineseBrandEnvironment = getBrandEnvironment({"brand": userConfig.brand})
      self.vehicles: List[ChineseVehicle] = []
      logger.debug("CN Controller created")

   @property
   def environment(self) -> ChineseBrandEnvironment:
      return self._environment

   def login(self) -> str:
      raise NotImplementedError("ChineseController.login is not implemented yet")

   def logout(self) -> str:
      raise NotImplementedError("ChineseController.logout is not implemented yet")

   def getVehicles(self) -> List[Vehicle]:
      # TODO: implement vehicle discovery for Chinese region
      return self.vehicles

   def refreshAccessToken(self) -> str:
      raise NotImplementedError("ChineseController.refreshAccessToken is not implemented yet")
