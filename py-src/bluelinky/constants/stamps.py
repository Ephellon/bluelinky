from __future__ import annotations

import base64
import json
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional

import requests

from ..interfaces.common_interfaces import Brand
from ..constants import REGIONS
from .australia_cfb import hyundaiCFB as australiaHyundaiCFB, kiaCFB as australiaKiaCFB
from .europe_cfb import hyundaiCFB as europeHyundaiCFB, kiaCFB as europeKiaCFB


class StampMode(str, Enum):
   LOCAL = "LOCAL"
   DISTANT = "DISTANT"


@dataclass
class StampCollection:
   stamps: list[str]
   generated: str
   frequency: int


cachedStamps: Dict[str, StampCollection] = {}


def _getAndCacheStampsFromFile(
   file: str,
   stampHost: str,
   stampsFile: Optional[str] = None,
) -> StampCollection:
   stampsFileResolved = stampsFile or f"{stampHost}{file}.v2.json"

   if stampsFileResolved.startswith("file://"):
      _, path = stampsFileResolved.split("file://", 1)
      with open(path, "rb") as f:
         content = f.read()
      data = json.loads(content.decode("utf-8"))
      return StampCollection(
         stamps=list(data["stamps"]),
         generated=str(data["generated"]),
         frequency=int(data["frequency"]),
      )

   response = requests.get(stampsFileResolved)
   response.raise_for_status()
   body = response.json()

   collection = StampCollection(
      stamps=list(body["stamps"]),
      generated=str(body["generated"]),
      frequency=int(body["frequency"]),
   )
   cachedStamps[file] = collection
   return collection


def getStampFromFile(
   stampFileKey: str,
   stampHost: str,
   stampsFile: Optional[str] = None,
) -> Callable[[], str]:
   def _generator() -> str:
      collection = cachedStamps.get(stampFileKey)
      if collection is None:
         collection = _getAndCacheStampsFromFile(stampFileKey, stampHost, stampsFile)

      stamps = collection.stamps
      generated = collection.generated
      frequency = collection.frequency

      # Parse ISO timestamp to epoch milliseconds (UTC when possible)
      generatedDateMs: float
      gen = generated
      if gen.endswith("Z"):
         gen = gen[:-1] + "+00:00"
      try:
         from datetime import datetime

         generatedDateMs = datetime.fromisoformat(gen).timestamp() * 1000.0
      except Exception:
         # Fallback: treat as 0 so we will quickly advance and refresh cache if needed
         generatedDateMs = 0.0

      millisecondsSinceStampsGeneration = (time.time() * 1000.0) - generatedDateMs
      position = int(math.floor(millisecondsSinceStampsGeneration / frequency))
      if (position / (len(stamps) - 1)) >= 0.9:
         cachedStamps.pop(stampFileKey, None)
      return stamps[min(position, len(stamps) - 1)]

   return _generator


def _xorBuffers(a: bytes, b: bytes) -> bytes:
   if len(a) != len(b):
      raise ValueError(f"XOR Buffers are not the same size {len(a)} vs {len(b)}")
   return bytes([a[i] ^ b[i] for i in range(len(a))])


def _getCFB(brand: Brand, region: REGIONS) -> bytes:
   if region == REGIONS.AU:
      return australiaKiaCFB if brand == "kia" else australiaHyundaiCFB
   if region == REGIONS.EU:
      return europeKiaCFB if brand == "kia" else europeHyundaiCFB
   raise ValueError("Local stamp generation is only supported in Australia and Europe")


def getStampFromCFB(appId: str, brand: Brand, region: REGIONS) -> Callable[[], str]:
   cfb = _getCFB(brand, region)

   def _generator() -> str:
      rawData = f"{appId}:{int(time.time() * 1000)}".encode("utf-8")
      xored = _xorBuffers(cfb, rawData)
      return base64.b64encode(xored).decode("utf-8")

   return _generator


def getStampGenerator(
   *,
   appId: str,
   brand: Brand,
   mode: StampMode,
   region: REGIONS,
   stampHost: str,
   stampsFile: Optional[str] = None,
) -> Callable[[], str]:
   if mode == StampMode.LOCAL:
      return getStampFromCFB(appId, brand, region)
   # StampMode.DISTANT or default
   return getStampFromFile(f"{brand}-{appId}", stampHost, stampsFile)