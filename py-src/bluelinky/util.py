from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from .constants import REGION


def dec2hexString(dec: int) -> str:
   return "0x" + format(dec, "x")[-4:].upper()


def floatRange(start, stop, step) -> List[float]:
   ranges: List[float] = []
   i = start
   while i <= stop:
      ranges.append(i)
      i += step
   return ranges


REGION_STEP_RANGES = {
   "EU": {
      "start": 14,
      "end": 30,
      "step": 0.5,
   },
   "CA": {
      "start": 16,
      "end": 32,
      "step": 0.5,
   },
   "CN": {
      "start": 14,
      "end": 30,
      "step": 0.5,
   },
   # TODO: verify the Australian temp code ranges
   "AU": {
      "start": 17,
      "end": 27,
      "step": 0.5,
   },
}


# Converts Kia's stupid temp codes to celsius
# From what I can tell it uses a hex index on a list of temperatures starting at 14c ending at 30c with an added H on the end,
# I'm thinking it has to do with Heat/Cool H/C but needs to be tested, while the car is off, it defaults to 01H
def celciusToTempCode(region: REGION, temperature: float) -> str:
   # create a range of floats
   region_key = region.name if hasattr(region, "name") else str(region)
   spec = REGION_STEP_RANGES[region_key]
   start, end, step = spec["start"], spec["end"], spec["step"]
   tempRange = floatRange(start, end, step)

   # get the index from the celcious degre
   tempCodeIndex = tempRange.index(temperature)

   # convert to hex
   hexCode = dec2hexString(tempCodeIndex)

   # get the second param and stick an H on the end?
   # this needs more testing I guess :P
   return (f"{hexCode.split('x')[1].upper()}H").rjust(3, "0")


def tempCodeToCelsius(region: REGION, code: str) -> float:
   # create a range
   region_key = region.name if hasattr(region, "name") else str(region)
   spec = REGION_STEP_RANGES[region_key]
   start, end, step = spec["start"], spec["end"], spec["step"]
   tempRange = floatRange(start, end, step)

   # get the index
   tempIndex = int(code, 16)

   # return the relevant celsius temp
   return tempRange[tempIndex]


def parseDate(str: str) -> datetime:
   year = int(str[0:4])
   month = int(str[4:6])
   if len(str) <= 6:
      return datetime(year, month, 1)
   day = int(str[6:8])
   if len(str) <= 8:
      return datetime(year, month, day)
   hour = int(str[8:10])
   minute = int(str[10:12])
   second = int(str[12:14])
   return datetime(year, month, day, hour, minute, second)


MILISECONDS_PER_SECOND = 1000
MILISECONDS_PER_MINUTE = MILISECONDS_PER_SECOND * 60


def addMinutes(date: datetime, minutes: int) -> datetime:
   return date + timedelta(minutes=minutes)