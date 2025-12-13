from enum import Enum
from typing import Callable, Dict


class StampMode(str, Enum):
   LOCAL = "local"
   REMOTE = "remote"


def getStampGenerator(config: Dict[str, object]) -> Callable[[], str]:
   def _generator() -> str:
      return ""

   return _generator

