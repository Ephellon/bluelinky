from __future__ import annotations

from typing import List, Optional

from .constants import Region
from .controllers import controller_for_region
from .interfaces import BlueLinkyConfig, Session
from .logger import logger
from .vehicles import Vehicle


class BlueLinky:
   def __init__(self, config: BlueLinkyConfig):
      normalized = config.normalized()
      self.config = normalized
      self.controller = controller_for_region(normalized.region, normalized)
      self._vehicles: List[Vehicle] = []
      if normalized.auto_login:
         logger.debug("Automatic login enabled; attempting login")
         self.login()

   def login(self) -> str:
      response = self.controller.login()
      self._vehicles = self.get_vehicles()
      logger.debug("Found %s vehicle(s)", len(self._vehicles))
      return response

   def get_vehicles(self) -> List[Vehicle]:
      vehicles = self.controller.get_vehicles()
      return list(vehicles) if vehicles else []

   def get_vehicle(self, input: str) -> Optional[Vehicle]:
      for vehicle in self._vehicles:
         if vehicle.vin().lower() == input.lower():
            return vehicle
      return None

   def refresh_access_token(self) -> str:
      return self.controller.refresh_access_token()

   def logout(self) -> str:
      return self.controller.logout()

   def get_session(self) -> Session:
      return self.controller.session

   @property
   def cached_vehicles(self) -> List[Vehicle]:
      return self._vehicles


__all__ = ["BlueLinky"]
