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
      self._locked = True
      self._engine_on = False
      self._status: Optional[VehicleStatus] = None
      self._full_status: Optional[FullVehicleStatus] = None
      self._location: Optional[VehicleLocation] = None
      self._odometer: Optional[VehicleOdometer] = None

   def status(self, input: VehicleStatusOptions) -> Optional[VehicleStatus | RawVehicleStatus]:
      if self._status is None or input.refresh:
         self._status = VehicleStatus(
            engine_on=self._engine_on,
            locked=self._locked,
            last_update=datetime.utcnow(),
            raw={},
         )
      return self._status

   def full_status(self, input: VehicleStatusOptions) -> Optional[FullVehicleStatus]:
      if self._full_status is None or input.refresh:
         self._full_status = FullVehicleStatus(payload={"vin": self.vin()})
      return self._full_status

   def unlock(self) -> str:
      self._locked = False
      return "unlocked"

   def lock(self) -> str:
      self._locked = True
      return "locked"

   def start(self, config: VehicleStartOptions) -> str:
      self._engine_on = True
      self._status = VehicleStatus(
         engine_on=True,
         locked=self._locked,
         last_update=datetime.utcnow(),
         raw={"config": config.__dict__},
      )
      return "started"

   def stop(self) -> str:
      self._engine_on = False
      if self._status:
         self._status.engine_on = False
      return "stopped"

   def location(self) -> Optional[VehicleLocation]:
      return self._location

   def odometer(self) -> Optional[VehicleOdometer]:
      return self._odometer

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
