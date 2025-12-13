from __future__ import annotations

from typing import List, Optional, Type
from uuid import uuid4

from ..constants import Region
from ..interfaces import BlueLinkyConfig, VehicleRegisterOptions
from ..logger import logger
from .controller import SessionController
from ..vehicles.vehicle import Vehicle
from ..vehicles.american_vehicle import AmericanVehicle
from ..vehicles.canadian_vehicle import CanadianVehicle
from ..vehicles.european_vehicle import EuropeanVehicle
from ..vehicles.chinese_vehicle import ChineseVehicle
from ..vehicles.australia_vehicle import AustraliaVehicle


class BasicController(SessionController[BlueLinkyConfig]):
   vehicle_cls: Type[Vehicle]

   def __init__(self, user_config: BlueLinkyConfig, region: Region, vehicle_cls: Type[Vehicle]):
      super().__init__(user_config)
      self.region = region
      self.vehicle_cls = vehicle_cls
      self._vehicles: Optional[List[Vehicle]] = None

   def login(self) -> str:
      self.session.access_token = f"{self.region.value.lower()}-{uuid4()}"
      self.session.refresh_token = f"refresh-{uuid4()}"
      logger.info("Logged into region %s for user %s", self.region.value, self.user_config.username)
      return self.session.access_token or ""

   def logout(self) -> str:
      logger.info("Logging out user %s", self.user_config.username)
      self.session = SessionController(self.user_config).session
      self._vehicles = None
      return "logged out"

   def refresh_access_token(self) -> str:
      self.session.access_token = f"{self.region.value.lower()}-{uuid4()}"
      logger.info("Refreshed access token for %s", self.user_config.username)
      return self.session.access_token or ""

   def get_vehicles(self) -> List[Vehicle]:
      if self._vehicles is not None:
         return self._vehicles
      register_options = self._build_vehicle_register()
      vehicle = self.vehicle_cls(register_options, self)
      self._vehicles = [vehicle]
      return self._vehicles

   def _build_vehicle_register(self) -> VehicleRegisterOptions:
      vin = self.user_config.vin or f"VIN-{self.region.value}-{uuid4().hex[:11].upper()}"
      vehicle_id = self.user_config.vehicle_id or vin[-8:]
      name = f"{self.user_config.brand.value.title()} {self.region.value}"
      return VehicleRegisterOptions(
         id=vehicle_id,
         name=name,
         nickname=name,
         vin=vin,
         brand_indicator=self.user_config.brand.value,
         generation="",
      )


def controller_for_region(region: Region, config: BlueLinkyConfig) -> BasicController:
   if region is Region.US:
      return BasicController(config, region, AmericanVehicle)
   if region is Region.CA:
      return BasicController(config, region, CanadianVehicle)
   if region is Region.EU:
      return BasicController(config, region, EuropeanVehicle)
   if region is Region.CN:
      return BasicController(config, region, ChineseVehicle)
   if region is Region.AU:
      return BasicController(config, region, AustraliaVehicle)
   raise ValueError(f"Unsupported region: {region}")
