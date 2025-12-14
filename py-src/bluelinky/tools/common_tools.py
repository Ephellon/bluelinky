from __future__ import annotations

import json
import random
import math
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Protocol, TypeVar


class ManagedBluelinkyError(Exception):
   ErrorName = "ManagedBluelinkyError"

   def __init__(self, message: str, source: Optional[BaseException] = None):
      super().__init__(message)
      self.name = ManagedBluelinkyError.ErrorName
      self.source = source


class Stringifiable(Protocol):
   def __str__(self) -> str: ...


@dataclass
class _HTTPErrorLike(Exception):
   statusCode: int
   statusMessage: str
   method: str
   url: str
   body: Any = None


@dataclass
class _ParseErrorLike(Exception):
   method: str
   url: str
   response: Optional[Any] = None


def manageBluelinkyError(err: Any, context: Optional[str] = None) -> Any | Exception | ManagedBluelinkyError:
   # Mirrors TypeScript behavior for got.HTTPError / got.ParseError but without hard dependency on got.
   # Controllers may raise requests exceptions; those will fall through as generic Exceptions.
   prefix = f"@{context}: " if context else ""

   if hasattr(err, "statusCode") and hasattr(err, "statusMessage") and hasattr(err, "method") and hasattr(err, "url"):
      try:
         body = getattr(err, "body", None)
         return ManagedBluelinkyError(
            f"{prefix}[{getattr(err, 'statusCode')}] {getattr(err, 'statusMessage')} on [{getattr(err, 'method')}] {getattr(err, 'url')} - {json.dumps(body)}",
            err,
         )
      except Exception:
         return ManagedBluelinkyError(
            f"{prefix}HTTP error on [{getattr(err, 'method', None)}] {getattr(err, 'url', None)}",
            err,
         )

   if hasattr(err, "method") and hasattr(err, "url") and hasattr(err, "response"):
      try:
         response = getattr(err, "response", None)
         body = getattr(response, "body", None) if response is not None else None
         return ManagedBluelinkyError(
            f"{prefix} Parsing error on [{getattr(err, 'method')}] {getattr(err, 'url')} - {json.dumps(body)}",
            err,
         )
      except Exception:
         return ManagedBluelinkyError(
            f"{prefix}Parsing error on [{getattr(err, 'method', None)}] {getattr(err, 'url', None)}",
            err,
         )

   if isinstance(err, Exception):
      return err
   return err


T = TypeVar("T")
U = TypeVar("U")


def asyncMap(array: List[T], callback: Callable[[T, int, List[T]], U]) -> List[U]:
   mapped: List[U] = []
   for index in range(len(array)):
      mapped.append(callback(array[index], index, array))
   return mapped


def uuidV4() -> str:
   def repl(c: str) -> str:
      r = int(random.random() * 16) | 0
      v = r if c == "x" else (r & 0x3) | 0x8
      return format(v, "x")

   template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
   out_chars: List[str] = []
   for ch in template:
      if ch in ("x", "y"):
         out_chars.append(repl(ch))
      else:
         out_chars.append(ch)
   return "".join(out_chars)

def haversine_km(lat1, lon1, lat2, lon2):
   R = 6371.0
   dlat = math.radians(lat2 - lat1)
   dlon = math.radians(lon2 - lon1)
   a = (
      math.sin(dlat / 2) ** 2
      + math.cos(math.radians(lat1))
      * math.cos(math.radians(lat2))
      * math.sin(dlon / 2) ** 2
   )
   return 2 * R * math.asin(math.sqrt(a))
