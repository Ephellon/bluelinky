from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..interfaces import (
   BlueLinkyConfig,
   FullVehicleStatus,
   RawVehicleStatus,
   VehicleLocation,
   VehicleOdometer,
   VehicleRegisterOptions,
   VehicleStartOptions,
   VehicleStatus,
   VehicleStatusOptions,
)


class Vehicle:
   def __init__(self, vehicle_config: VehicleRegisterOptions, controller: object):
      self.vehicle_config = vehicle_config
      self.controller = controller
      self.user_config: BlueLinkyConfig = getattr(controller, "user_config")
      self._full_status: Optional[FullVehicleStatus | None] = None
      self._status: Optional[VehicleStatus | RawVehicleStatus | None] = None
      self._location: Optional[VehicleLocation | None] = None
      self._odometer: Optional[VehicleOdometer | None] = None

   def status(self, input: VehicleStatusOptions) -> Optional[VehicleStatus | RawVehicleStatus]:
      raise NotImplementedError

   def full_status(self, input: VehicleStatusOptions) -> Optional[FullVehicleStatus]:
      raise NotImplementedError

   def unlock(self) -> str:
      raise NotImplementedError

   def lock(self) -> str:
      raise NotImplementedError

   def start(self, config: VehicleStartOptions) -> str:
      raise NotImplementedError

   def stop(self) -> str:
      raise NotImplementedError

   def location(self) -> Optional[VehicleLocation]:
      raise NotImplementedError

   def odometer(self) -> Optional[VehicleOdometer]:
      raise NotImplementedError

   def vin(self) -> str:
      return self.vehicle_config.vin

   def name(self) -> str:
      return self.vehicle_config.name

   def nickname(self) -> str:
      return self.vehicle_config.nickname

   def id(self) -> str:
      return self.vehicle_config.id

   def brand_indicator(self) -> str:
      return self.vehicle_config.brand_indicator
