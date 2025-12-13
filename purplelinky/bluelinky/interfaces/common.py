from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict, Union, Literal


Brand = Literal["kia", "hyundai"]
REGION = Literal["US", "CA", "EU", "CN", "AU"]


class EVPlugTypes(Enum):
   UNPLUGED = 0
   FAST = 1
   PORTABLE = 2
   STATION = 3


class EVChargeModeTypes(Enum):
   FAST = 0
   SLOW = 1


class SeatHeaterVentInfo(TypedDict, total=False):
   leftFront: int
   rightFront: int
   leftRear: int
   rightRear: int


@dataclass
class BlueLinkyConfig:
   username: Optional[str]
   password: Optional[str]
   region: Optional[REGION]
   brand: Brand
   autoLogin: bool = True
   pin: Optional[str] = None
   vin: Optional[str] = None
   vehicleId: Optional[str] = None


class Session(TypedDict, total=False):
   accessToken: Optional[str]
   refreshToken: Optional[str]
   controlToken: Optional[str]
   deviceId: Optional[str]
   tokenExpiresAt: int
   controlTokenExpiresAt: Optional[int]


class VehicleStatus(TypedDict, total=False):
   engine: Dict[str, Any]
   climate: Dict[str, Any]
   chassis: Dict[str, Any]
   lastupdate: Optional[Any]


FullVehicleStatus = Dict[str, Any]
RawVehicleStatus = Dict[str, Any]
VehicleLocation = Dict[str, Any]
VehicleOdometer = Dict[str, Any]


class VehicleStartOptions(TypedDict, total=False):
   hvac: bool
   duration: int
   temperature: Union[int, float]
   defrost: bool
   unit: str
   heatedFeatures: Union[int, bool]
   seatClimateSettings: Optional[SeatHeaterVentInfo]


class VehicleStatusOptions(TypedDict, total=False):
   refresh: bool
   parsed: bool


@dataclass
class VehicleRegisterOptions:
   nickname: str
   name: str
   vin: str
   regDate: str
   brandIndicator: str
   regId: str
   generation: str
   engineType: Optional[str] = None

