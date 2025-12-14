from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict, TypeVar, Union

REGION = Literal["US", "CA", "EU", "CN", "AU"]


Brand = Literal["kia", "hyundai"]


# config
@dataclass
class BlueLinkyConfig:
   username: Optional[str]
   password: Optional[str]
   region: Optional[REGION]
   brand: Brand = "hyundai"
   autoLogin: Optional[bool] = None
   pin: Optional[str] = None
   vin: Optional[str] = None
   vehicleId: Optional[str] = None


@dataclass
class BluelinkVehicle:
   name: str
   vin: str
   type: str


@dataclass
class Session:
   accessToken: Optional[str] = None
   refreshToken: Optional[str] = None
   controlToken: Optional[str] = None
   deviceId: Optional[str] = None
   tokenExpiresAt: int = 0
   controlTokenExpiresAt: Optional[int] = None


class EVPlugTypes(Enum):
   UNPLUGED = 0
   FAST = 1
   PORTABLE = 2
   STATION = 3


class EVChargeModeTypes(Enum):
   FAST = 0
   SLOW = 1


# Status remapped
class _VehicleStatusEngine(TypedDict, total=False):
   ignition: bool
   batteryCharge: int
   charging: bool
   timeToFullCharge: Any
   range: int
   rangeGas: int
   rangeEV: int
   plugedTo: EVPlugTypes
   estimatedCurrentChargeDuration: int
   estimatedFastChargeDuration: int
   estimatedPortableChargeDuration: int
   estimatedStationChargeDuration: int
   batteryCharge12v: int
   batteryChargeHV: int
   accessory: bool


class _VehicleStatusClimate(TypedDict):
   active: bool
   steeringwheelHeat: bool
   sideMirrorHeat: bool
   rearWindowHeat: bool
   temperatureSetpoint: Union[int, str]
   temperatureUnit: int
   defrost: bool


class _VehicleStatusOpenDoors(TypedDict):
   frontRight: bool
   frontLeft: bool
   backLeft: bool
   backRight: bool


class _VehicleStatusTirePressureWarningLamp(TypedDict):
   rearLeft: bool
   frontLeft: bool
   frontRight: bool
   rearRight: bool
   all: bool


class _VehicleStatusChassis(TypedDict):
   hoodOpen: bool
   trunkOpen: bool
   locked: bool
   openDoors: _VehicleStatusOpenDoors
   tirePressureWarningLamp: _VehicleStatusTirePressureWarningLamp


@dataclass
class VehicleStatus:
   engine: Dict[str, Any]
   climate: Dict[str, Any]
   chassis: Dict[str, Any]
   lastupdate: Optional[datetime]


# TODO: fix/update
@dataclass
class FullVehicleStatus:
   vehicleLocation: Dict[str, Any]
   odometer: Dict[str, Any]
   vehicleStatus: Dict[str, Any]


# TODO: remove
# =======
# Rough mapping of the raw status that might no be the same for all regions
@dataclass
class RawVehicleStatus:
   lastStatusDate: str
   dateTime: str
   acc: bool
   trunkOpen: bool
   doorLock: bool
   defrostStatus: str
   transCond: bool
   doorLockStatus: str
   doorOpen: Dict[str, int]
   airCtrlOn: bool
   airTempUnit: str
   airTemp: Dict[str, Any]
   battery: Dict[str, Any]
   ign3: bool
   ignitionStatus: str
   lowFuelLight: bool
   sideBackWindowHeat: int
   dte: Dict[str, Any]
   engine: bool
   defrost: bool
   hoodOpen: bool
   airConditionStatus: str
   steerWheelHeat: int
   tirePressureLamp: Dict[str, int]
   trunkOpenStatus: str
   evStatus: Dict[str, Any]
   remoteIgnition: bool
   seatHeaterVentInfo: Any
   sleepModeCheck: bool
   lampWireStatus: Dict[str, Any]
   windowOpen: Any
   engineRuntime: Any


# Vehicle Info
@dataclass
class VehicleInfo:
   vehicleId: str
   nickName: str
   modelCode: str
   modelName: str
   modelYear: str
   fuelKindCode: str
   trim: str
   engine: str
   exteriorColor: str
   dtcCount: int
   subscriptionStatus: str
   subscriptionEndDate: str
   overviewMessage: str
   odometer: int
   odometerUnit: int
   defaultVehicle: bool
   enrollmentStatus: str
   genType: str
   transmissionType: str
   vin: str


@dataclass
class VehicleFeatureEntry:
   category: str
   features: List[Dict[str, Any]]


# Location
@dataclass
class VehicleLocation:
   latitude: float
   longitude: float
   altitude: float
   speed: Dict[str, Union[int, float]]
   heading: float


@dataclass
class VehicleOdometer:
   unit: int
   value: int


@dataclass
class VehicleStatusOptions:
   refresh: bool
   parsed: bool
   useInfo: Optional[bool] = None


# VEHICLE COMMANDS /////////////////////////////////////////////
@dataclass
class VehicleCommandResponse:
   responseCode: int  # 0 is success
   responseDesc: str


SeatHeaterVentInfo = Optional[Dict[str, int]]


@dataclass
class VehicleStartOptions:
   hvac: Union[bool, str]
   duration: int
   temperature: int
   defrost: Union[bool, str]
   heatedFeatures: Union[int, bool]
   unit: Optional[Literal["C", "F"]] = None
   seatClimateSettings: Optional[SeatHeaterVentInfo] = None


class VehicleWindowState(Enum):
   CLOSED = 0
   OPEN = 1
   VENTILATION = 2


@dataclass
class VehicleWindowsOptions:
   backLeft: VehicleWindowState
   backRight: VehicleWindowState
   frontLeft: VehicleWindowState
   frontRight: VehicleWindowState


@dataclass
class VehicleRegisterOptions:
   nickname: str
   name: str
   vin: str
   regDate: str
   brandIndicator: str
   regId: str
   id: str
   generation: str
   ccuCCS2ProtocolSupport: Optional[bool] = None
   engineType: Optional[Literal["ICE", "EV"]] = None  # ICE = Internal Combustion Engine, EV = Electric Vehicle, HEV = Hybrid Electric Vehicle, PHEV = Plug-in Hybrid Electric Vehicle


T = TypeVar("T")


class DeepPartial(Dict[str, Any]):
   pass


@dataclass
class VehicleMonthlyReport:
   start: str  # format YYYYMMDD, eg: 20210210
   end: str  # format YYYYMMDD, eg: 20210312
   driving: Dict[str, Any]
   breakdown: List[Dict[str, str]]
   vehicleStatus: Dict[str, Any]


@dataclass
class VehicleTargetSOC:
   type: EVChargeModeTypes
   distance: int
   targetLevel: int


@dataclass
class VehicleMonthTrip:
   days: List[Dict[str, Any]]
   durations: Dict[str, int]
   speed: Dict[str, int]
   distance: int


@dataclass
class VehicleDayTrip:
   dayRaw: str
   tripsCount: int
   distance: int
   durations: Dict[str, int]
   speed: Dict[str, int]
   trips: List[Dict[str, Any]]
