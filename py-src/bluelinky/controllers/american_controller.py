from __future__ import annotations

from ..constants import Region
from ..interfaces import BlueLinkyConfig
from .basic_controller import BasicController


class AmericanController(BasicController):
   def __init__(self, user_config: BlueLinkyConfig):
      super().__init__(user_config, Region.US, vehicle_cls=self._vehicle_class())

   @staticmethod
   def _vehicle_class():
      from ..vehicles.american_vehicle import AmericanVehicle

      return AmericanVehicle
