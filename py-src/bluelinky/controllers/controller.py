from __future__ import annotations

from typing import Generic, List, TypeVar
from uuid import uuid4

from ..constants import Region
from ..interfaces import BlueLinkyConfig, Session


TConfig = TypeVar("TConfig", bound=BlueLinkyConfig)


class SessionController(Generic[TConfig]):
   region: Region

   def __init__(self, user_config: TConfig):
      self.user_config = user_config
      self.session = Session(
         access_token=None,
         refresh_token=None,
         control_token=None,
         device_id=str(uuid4()),
         token_expires_at=0,
      )

   def login(self) -> str:
      raise NotImplementedError

   def logout(self) -> str:
      raise NotImplementedError

   def get_vehicles(self) -> List[object]:
      raise NotImplementedError

   def refresh_access_token(self) -> str:
      raise NotImplementedError
