from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, TypedDict

from ..interfaces.common_interfaces import Brand
from ..constants import REGION


class AdvClimateMap(TypedDict):
   validSeats: Dict[str, str]
   validStatus: List[int]
   validHeats: List[int]


payloadSeatNameMapUS: Dict[str, str] = {
   "driverSeat": "drvSeatHeatState",
   "passengerSeat": "astSeatHeatState",
   "rearLeftSeat": "rlSeatHeatState",
   "rearRightSeat": "rrSeatHeatState",
}

seatStatusMap: Dict[int, str] = {
   0: "Off",
   1: "On",
   2: "Off",
   3: "Low Cool",
   4: "Medium Cool",
   5: "High Cool",
   6: "Low Heat",
   7: "Medium Heat",
   8: "High Heat",
}

heatStatusMap: Dict[int, str] = {
   0: "Off",
   1: "Steering Wheel and Rear Window",
   2: "Rear Window",
   3: "Steering Wheel",
   # 4: "Steering Wheel and Rear Window",  # handled via region logic
}


def createValidatorMapping(region: REGION) -> AdvClimateMap:
   convry: List[int] = [int(key) for key in seatStatusMap.keys()]
   heatstates: List[int] = [int(key) for key in heatStatusMap.keys()]
   if region == "EU":
      heatstates.append(4)  # EU has 4 as a valid heat state not actually implemented in the code
   return {
      "validSeats": payloadSeatNameMapUS,
      "validStatus": convry,
      "validHeats": heatstates,
   }


def advClimateValidator(brand: Brand, region: REGION) -> AdvClimateMap:
   if region == "US" and brand == "hyundai":
      return createValidatorMapping(region)
   return {"validSeats": {}, "validStatus": [], "validHeats": []}