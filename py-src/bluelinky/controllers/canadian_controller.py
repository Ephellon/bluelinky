from __future__ import annotations

from ..constants import Region
from ..interfaces import BlueLinkyConfig
from .basic_controller import BasicController


class CanadianController(BasicController):
   def __init__(self, user_config: BlueLinkyConfig):
      super().__init__(user_config, Region.CA, vehicle_cls=self._vehicle_class())

   @staticmethod
   def _vehicle_class():
      from ..vehicles.canadian_vehicle import CanadianVehicle

      return CanadianVehicle
