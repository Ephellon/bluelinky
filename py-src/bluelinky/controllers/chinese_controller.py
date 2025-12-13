from __future__ import annotations

from ..constants import Region
from ..interfaces import BlueLinkyConfig
from .basic_controller import BasicController


class ChineseController(BasicController):
   def __init__(self, user_config: BlueLinkyConfig):
      super().__init__(user_config, Region.CN, vehicle_cls=self._vehicle_class())

   @staticmethod
   def _vehicle_class():
      from ..vehicles.chinese_vehicle import ChineseVehicle

      return ChineseVehicle
