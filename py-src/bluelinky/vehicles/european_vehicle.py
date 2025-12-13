from __future__ import annotations

from ..constants import Region
from ..interfaces import VehicleRegisterOptions
from .vehicle import Vehicle


class EuropeanVehicle(Vehicle):
   region = Region.EU

   def __init__(self, vehicle_config: VehicleRegisterOptions, controller: object):
      super().__init__(vehicle_config, controller)
