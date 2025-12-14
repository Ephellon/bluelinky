from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic

from .constants import REGIONS, Region
from .controllers.american_controller import AmericanBlueLinkyConfig, AmericanController
from .controllers.australia_controller import AustraliaBlueLinkyConfig, AustraliaController
from .controllers.canadian_controller import CanadianBlueLinkyConfig, CanadianController
from .controllers.chinese_controller import ChineseBlueLinkConfig, ChineseController
from .controllers.controller import SessionController
from .controllers.european_controller import EuropeBlueLinkyConfig, EuropeanController
from .interfaces.common_interfaces import Session
from .logger import logger
from .vehicles.vehicle import Vehicle

T = TypeVar("T")
VEHICLE_TYPE = TypeVar("VEHICLE_TYPE", bound=Vehicle)


DEFAULT_CONFIG: Dict[str, Any] = {
   "username": "",
   "password": "",
   "region": REGIONS.US,
   "brand": "hyundai",
   "autoLogin": True,
   "pin": "1234",
   "vin": "",
   "vehicleId": None,
}


class EventEmitter:
   def __init__(self) -> None:
      self._listeners: Dict[Any, List[Callable[..., None]]] = {}

   def on(self, event: Any, listener: Callable[..., None]) -> "EventEmitter":
      self._listeners.setdefault(event, []).append(listener)
      return self

   def emit(self, event: Any, *args: Any, **kwargs: Any) -> None:
      for listener in list(self._listeners.get(event, [])):
         listener(*args, **kwargs)


class BlueLinky(Generic[T, VEHICLE_TYPE], EventEmitter):
   def __init__(self, config: T) -> None:
      super().__init__()

      merged: Dict[str, Any] = dict(DEFAULT_CONFIG)
      if isinstance(config, dict):
         merged.update(config)
      else:
         merged.update(getattr(config, "__dict__", {}))

      self.config: Any = merged
      self.controller: SessionController
      self.vehicles: List[VEHICLE_TYPE] = []

      region = self.config.get("region")

      if region == REGIONS.EU:
         self.controller = EuropeanController(self.config)  # type: ignore[arg-type]
      elif region == REGIONS.US:
         self.controller = AmericanController(self.config)  # type: ignore[arg-type]
      elif region == REGIONS.CA:
         self.controller = CanadianController(self.config)  # type: ignore[arg-type]
      elif region == REGIONS.CN:
         self.controller = ChineseController(self.config)  # type: ignore[arg-type]
      elif region == REGIONS.AU:
         self.controller = AustraliaController(self.config)  # type: ignore[arg-type]
      else:
         raise Exception("Your region is not supported yet.")

      if self.config.get("autoLogin") is None:
         self.config["autoLogin"] = True

      self.onInit()

   def on(self, event: Any, fnc: Callable[..., None]) -> "BlueLinky[T, VEHICLE_TYPE]":  # type: ignore[override]
      return super().on(event, fnc)  # type: ignore[return-value]

   def onInit(self) -> None:
      if self.config.get("autoLogin"):
         logger.debug("Bluelinky is logging in automatically, to disable use autoLogin: false")
         self.login()

   def login(self) -> str:
      try:
         response = self.controller.login()

         self.vehicles = self.getVehicles()
         logger.debug(f"Found {len(self.vehicles)} on the account")

         self.emit("ready", self.vehicles)
         return response
      except Exception as error:
         self.emit("error", error)
         return str(error)

   def getVehicles(self) -> List[VEHICLE_TYPE]:
      vehicles = self.controller.getVehicles()
      return vehicles if vehicles else []  # type: ignore[name-defined]

   def getVehicle(self, input: str) -> Optional[VEHICLE_TYPE]:
      try:
         foundCar: Optional[VEHICLE_TYPE] = next(
            (car for car in self.vehicles if car.vin().lower() == input.lower()),
            None,
         )

         if not foundCar and len(self.vehicles) > 0:
            raise Exception(f"Could not find vehicle with id: {input}")

         return foundCar
      except Exception as _err:
         raise Exception(f"Vehicle not found: {input}!")

   def refreshAccessToken(self) -> str:
      return self.controller.refreshAccessToken()

   def logout(self) -> str:
      return self.controller.logout()

   def getSession(self) -> Optional[Session]:
      return self.controller.session

   @property
   def cachedVehicles(self) -> List[VEHICLE_TYPE]:
      return self.vehicles or []


__all__ = ["BlueLinky"]
