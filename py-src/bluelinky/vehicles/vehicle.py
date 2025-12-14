from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union

from ..constants import REGIONS
from ..controllers.controller import SessionController
from ..interfaces.common_interfaces import (
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
   @abstractmethod
   def status(self, input: VehicleStatusOptions) -> Optional[Union[VehicleStatus, RawVehicleStatus]]:
      raise NotImplementedError

   @abstractmethod
   def fullStatus(self, input: VehicleStatusOptions) -> Optional[FullVehicleStatus]:
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
   def location(self) -> Optional[VehicleLocation]:
      raise NotImplementedError

   @abstractmethod
   def odometer(self) -> Optional[VehicleOdometer]:
      raise NotImplementedError

   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: SessionController):
      self.vehicleConfig = vehicleConfig
      self.controller = controller

      self._fullStatus: Optional[FullVehicleStatus] = None
      self._status: Optional[Union[VehicleStatus, RawVehicleStatus]] = None
      self._location: Optional[VehicleLocation] = None
      self._odometer: Optional[VehicleOdometer] = None

      self.userConfig: BlueLinkyConfig = BlueLinkyConfig(
         username=None,
         password=None,
         region=REGIONS.EU,
         brand="hyundai",
         autoLogin=True,
         pin=None,
         vin=None,
         vehicleId=None,
      )

      self.userConfig = controller.userConfig

   def vin(self) -> str:
      return self.vehicleConfig.vin

   def name(self) -> str:
      return self.vehicleConfig.name

   def nickname(self) -> str:
      return self.vehicleConfig.nickname

   def id(self) -> str:
      return self.vehicleConfig.id

   def brandIndicator(self) -> str:
      return self.vehicleConfig.brandIndicator