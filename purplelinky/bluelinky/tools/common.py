import json
import random
from typing import Any, Awaitable, Callable, Iterable, List

import requests

from bluelinky.logger import logger


class ManagedBluelinkyError(Exception):
   ErrorName = "ManagedBluelinkyError"

   def __init__(self, message: str, source: Exception | None = None):
      super().__init__(message)
      self.source = source
      self.name = ManagedBluelinkyError.ErrorName


def manageBluelinkyError(err: Exception, context: str | None = None) -> ManagedBluelinkyError:
   if isinstance(err, requests.HTTPError):
      response = err.response
      status = response.status_code if response else "unknown"
      reason = response.reason if response else ""
      try:
         body = response.json() if response else None
      except Exception:
         body = response.text if response else None
      message = f"{f'@{context}: ' if context else ''}[{status}] {reason} - {json.dumps(body)}"
      return ManagedBluelinkyError(message, err)
   if isinstance(err, Exception):
      message = f"{f'@{context}: ' if context else ''}{err}"
      return ManagedBluelinkyError(message, err)
   return ManagedBluelinkyError(str(err))


def asyncMap(array: Iterable[Any], callback: Callable[[Any, int, Iterable[Any]], Awaitable[Any]]) -> List[Any]:
   # Synchronous compatibility helper
   mapped: List[Any] = []
   for index, item in enumerate(array):
      result = callback(item, index, array)
      mapped.append(result)
   return mapped


def uuidV4() -> str:
   def repl(c: str) -> str:
      r = random.randint(0, 15)
      v = r if c == "x" else (r & 0x3) | 0x8
      return format(v, "x")

   pattern = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
   chars = [repl(c) if c in ("x", "y") else c for c in pattern]
   return "".join(chars)

