from __future__ import annotations

from abc import ABC, abstractmethod
from bluelinky.interfaces.common import Session, BlueLinkyConfig


class SessionController(ABC):
   def __init__(self, userConfig: BlueLinkyConfig):
      self.userConfig = userConfig
      self.session: Session = {
         "accessToken": "",
         "refreshToken": "",
         "controlToken": "",
         "deviceId": "",
         "tokenExpiresAt": 0,
      }

   @abstractmethod
   def login(self) -> str:
      raise NotImplementedError

   @abstractmethod
   def logout(self) -> str:
      raise NotImplementedError

   @abstractmethod
   def getVehicles(self):
      raise NotImplementedError

   @abstractmethod
   def refreshAccessToken(self) -> str:
      raise NotImplementedError

