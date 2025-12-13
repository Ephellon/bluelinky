from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from bluelinky.controllers.controller import SessionController
from bluelinky.constants import REGIONS
from bluelinky.interfaces.common import (
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


class Vehicle(ABC):
   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: SessionController):
      self.vehicleConfig = vehicleConfig
      self.controller = controller
      self.userConfig: BlueLinkyConfig = controller.userConfig
      self._fullStatus: Optional[FullVehicleStatus] = None
      self._status: Optional[VehicleStatus | RawVehicleStatus] = None
      self._location: Optional[VehicleLocation] = None
      self._odometer: Optional[VehicleOdometer] = None

   @abstractmethod
   def status(self, input: VehicleStatusOptions) -> VehicleStatus | RawVehicleStatus | None:
      raise NotImplementedError

   @abstractmethod
   def fullStatus(self, input: VehicleStatusOptions) -> FullVehicleStatus | None:
      raise NotImplementedError

   @abstractmethod
   def unlock(self) -> str:
      raise NotImplementedError

   @abstractmethod
   def lock(self) -> str:
      raise NotImplementedError

   @abstractmethod
   def start(self, config: VehicleStartOptions) -> str:
      raise NotImplementedError

   @abstractmethod
   def stop(self) -> str:
      raise NotImplementedError

   @abstractmethod
   def location(self) -> VehicleLocation | None:
      raise NotImplementedError

   @abstractmethod
   def odometer(self) -> VehicleOdometer | None:
      raise NotImplementedError

   def vin(self) -> str:
      return self.vehicleConfig.vin

   def name(self) -> str:
      return self.vehicleConfig.name

   def nickname(self) -> str:
      return self.vehicleConfig.nickname

   def id(self) -> str:
      return self.vehicleConfig.regId

   def brandIndicator(self) -> str:
      return self.vehicleConfig.brandIndicator

