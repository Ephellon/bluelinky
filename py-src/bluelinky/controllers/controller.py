from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, List, TypeVar

from ..interfaces.common_interfaces import BlueLinkyConfig, Session
from ..vehicles.vehicle import Vehicle

T = TypeVar("T", bound=BlueLinkyConfig)


class SessionController(ABC, Generic[T]):
   @abstractmethod
   def login(self) -> str:
      raise NotImplementedError

   @abstractmethod
   def logout(self) -> str:
      raise NotImplementedError

   @abstractmethod
   def getVehicles(self) -> List[Vehicle]:
      raise NotImplementedError

   @abstractmethod
   def refreshAccessToken(self) -> str:
      raise NotImplementedError

   def __init__(self, userConfig: T):
      self.userConfig: T = userConfig
      self.session: Session = Session(
         accessToken="",
         refreshToken="",
         controlToken="",
         deviceId="",
         tokenExpiresAt=0,
      )