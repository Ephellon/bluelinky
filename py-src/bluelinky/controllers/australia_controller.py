from __future__ import annotations

from ..constants import Region
from ..interfaces import BlueLinkyConfig
from .basic_controller import BasicController


class AustraliaController(BasicController):
   def __init__(self, user_config: BlueLinkyConfig):
      super().__init__(user_config, Region.AU, vehicle_cls=self._vehicle_class())

   @staticmethod
   def _vehicle_class():
      from ..vehicles.australia_vehicle import AustraliaVehicle

      return AustraliaVehicle
