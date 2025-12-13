from typing import Dict, List

from bluelinky.interfaces.common import Brand
from bluelinky.constants import REGION


advClimateMap = Dict[str, object]


payloadSeatNameMapUS = {
   "driverSeat": "drvSeatHeatState",
   "passengerSeat": "astSeatHeatState",
   "rearLeftSeat": "rlSeatHeatState",
   "rearRightSeat": "rrSeatHeatState",
}

seatStatusMap = {
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

heatStatusMap = {
   0: "Off",
   1: "Steering Wheel and Rear Window",
   2: "Rear Window",
   3: "Steering Wheel",
}


def createValidatorMapping(region: REGION) -> Dict[str, object]:
   convry: List[int] = [int(key) for key in seatStatusMap.keys()]
   heatstates: List[int] = [int(key) for key in heatStatusMap.keys()]
   if region == "EU":
      heatstates.append(4)
   return {
      "validSeats": payloadSeatNameMapUS,
      "validStatus": convry,
      "validHeats": heatstates,
   }


def advClimateValidator(brand: Brand, region: REGION) -> Dict[str, object]:
   if region == "US" and brand == "hyundai":
      return createValidatorMapping(region)
   return {"validSeats": {}, "validStatus": [], "validHeats": []}

