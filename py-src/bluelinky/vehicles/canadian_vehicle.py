from __future__ import annotations

from ..constants import Region
from ..interfaces import VehicleRegisterOptions
from .vehicle import Vehicle


class CanadianVehicle(Vehicle):
   region = Region.CA

   def __init__(self, vehicle_config: VehicleRegisterOptions, controller: object):
      super().__init__(vehicle_config, controller)
