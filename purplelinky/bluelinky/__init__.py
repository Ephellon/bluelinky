from __future__ import annotations

from typing import Callable, Dict, List, Optional

from bluelinky.constants import REGIONS
from bluelinky.controllers.american_controller import AmericanController
from bluelinky.controllers.australia_controller import AustraliaController
from bluelinky.controllers.canadian_controller import CanadianController
from bluelinky.controllers.chinese_controller import ChineseController
from bluelinky.controllers.european_controller import EuropeanController
from bluelinky.controllers.controller import SessionController
from bluelinky.interfaces.common import BlueLinkyConfig, VehicleRegisterOptions
from bluelinky.logger import logger
from bluelinky.vehicles.american_vehicle import AmericanVehicle
from bluelinky.vehicles.australia_vehicle import AustraliaVehicle
from bluelinky.vehicles.canadian_vehicle import CanadianVehicle
from bluelinky.vehicles.chinese_vehicle import ChineseVehicle
from bluelinky.vehicles.european_vehicle import EuropeanVehicle
from bluelinky.vehicles.vehicle import Vehicle


class EventEmitter:
   def __init__(self):
      self._listeners: Dict[str, List[Callable]] = {}

   def on(self, event: str, fnc: Callable) -> "EventEmitter":
      self._listeners.setdefault(event, []).append(fnc)
      return self

   def emit(self, event: str, *args, **kwargs):
      for listener in self._listeners.get(event, []):
         listener(*args, **kwargs)


DEFAULT_CONFIG: Dict[str, object] = {
   "username": "",
   "password": "",
   "region": REGIONS.US,
   "brand": "hyundai",
   "autoLogin": True,
   "pin": "1234",
   "vin": "",
   "vehicleId": None,
}


class BlueLinky:
   def __init__(self, config: BlueLinkyConfig):
      self.config: BlueLinkyConfig = BlueLinkyConfig(**{**DEFAULT_CONFIG, **config.__dict__})
      self.emitter = EventEmitter()
      self.vehicles: List[Vehicle] = []
      self.controller: SessionController
      if self.config.region == REGIONS.EU:
         self.controller = EuropeanController(self.config)
      elif self.config.region == REGIONS.US:
         self.controller = AmericanController(self.config)
      elif self.config.region == REGIONS.CA:
         self.controller = CanadianController(self.config)
      elif self.config.region == REGIONS.CN:
         self.controller = ChineseController(self.config)
      elif self.config.region == REGIONS.AU:
         self.controller = AustraliaController(self.config)
      else:
         raise ValueError("Your region is not supported yet.")
      if self.config.autoLogin:
         logger.debug("Bluelinky is logging in automatically, to disable use autoLogin: false")
         self.login()

   def on(self, event: str, fnc: Callable) -> "BlueLinky":
      self.emitter.on(event, fnc)
      return self

   def login(self) -> str:
      try:
         response = self.controller.login()
         self.vehicles = self.getVehicles()
         logger.debug(f"Found {len(self.vehicles)} on the account")
         self.emitter.emit("ready", self.vehicles)
         return response
      except Exception as error:
         self.emitter.emit("error", error)
         return str(error)

   def getVehicles(self) -> List[Vehicle]:
      vehicles = self.controller.getVehicles()
      return vehicles or []

   def getVehicle(self, input: str) -> Optional[Vehicle]:
      found = next((car for car in self.vehicles if car.vin().lower() == input.lower()), None)
      if not found and self.vehicles:
         raise ValueError(f"Vehicle not found: {input}!")
      return found

   def refreshAccessToken(self) -> str:
      return self.controller.refreshAccessToken()

   def logout(self) -> str:
      return self.controller.logout()

   def getSession(self):
      return self.controller.session

   @property
   def cachedVehicles(self) -> List[Vehicle]:
      return self.vehicles or []

