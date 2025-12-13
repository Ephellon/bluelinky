from datetime import datetime, timedelta
from typing import List

from bluelinky.constants import REGION


def dec2hexString(dec: int) -> str:
   return "0x" + format(dec, "x").upper().zfill(4)


def floatRange(start: float, stop: float, step: float) -> List[float]:
   ranges: List[float] = []
   value = start
   while value <= stop:
      ranges.append(round(value, 2))
      value += step
   return ranges


REGION_STEP_RANGES = {
   "EU": {"start": 14, "end": 30, "step": 0.5},
   "CA": {"start": 16, "end": 32, "step": 0.5},
   "CN": {"start": 14, "end": 30, "step": 0.5},
   "AU": {"start": 17, "end": 27, "step": 0.5},
}


def celciusToTempCode(region: REGION, temperature: float) -> str:
   start = REGION_STEP_RANGES[region]["start"]
   end = REGION_STEP_RANGES[region]["end"]
   step = REGION_STEP_RANGES[region]["step"]
   temp_range = floatRange(start, end, step)
   temp_code_index = temp_range.index(temperature)
   hex_code = dec2hexString(temp_code_index)
   return f"{hex_code.split('x')[1].upper()}H".zfill(3)


def tempCodeToCelsius(region: REGION, code: str) -> float:
   start = REGION_STEP_RANGES[region]["start"]
   end = REGION_STEP_RANGES[region]["end"]
   step = REGION_STEP_RANGES[region]["step"]
   temp_range = floatRange(start, end, step)
   temp_index = int(code, 16)
   return temp_range[temp_index]


def parseDate(string: str) -> datetime:
   year = int(string[0:4])
   month = int(string[4:6])
   if len(string) <= 6:
      return datetime(year, month, 1)
   day = int(string[6:8])
   if len(string) <= 8:
      return datetime(year, month, day)
   hour = int(string[8:10])
   minute = int(string[10:12])
   second = int(string[12:14])
   return datetime(year, month, day, hour, minute, second)


MILISECONDS_PER_SECOND = 1000
MILISECONDS_PER_MINUTE = MILISECONDS_PER_SECOND * 60


def addMinutes(date: datetime, minutes: int) -> datetime:
   return date + timedelta(minutes=minutes)

