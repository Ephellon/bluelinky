from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .constants import Region


class Brand(str, Enum):
   KIA = "kia"
   HYUNDAI = "hyundai"


@dataclass
class Session:
   access_token: Optional[str] = None
   refresh_token: Optional[str] = None
   control_token: Optional[str] = None
   device_id: Optional[str] = None
   token_expires_at: int = 0
   control_token_expires_at: Optional[int] = None


@dataclass
class BlueLinkyConfig:
   username: Optional[str]
   password: Optional[str]
   region: Region
   brand: Brand = Brand.HYUNDAI
   auto_login: bool = True
   pin: Optional[str] = None
   vin: Optional[str] = None
   vehicle_id: Optional[str] = None

   def normalized(self) -> "BlueLinkyConfig":
      brand_value = self.brand.value if isinstance(self.brand, Brand) else str(self.brand)
      return BlueLinkyConfig(
         username=self.username,
         password=self.password,
         region=self.region,
         brand=Brand(brand_value),
         auto_login=self.auto_login,
         pin=self.pin,
         vin=self.vin,
         vehicle_id=self.vehicle_id,
      )


@dataclass
class VehicleRegisterOptions:
   id: str
   name: str
   nickname: str
   vin: str
   brand_indicator: str
   generation: str = ""


@dataclass
class VehicleStartOptions:
   hvac: bool = False
   duration: int = 10
   temperature: float = 70.0
   defrost: bool = False
   heated_features: int = 0
   unit: str = "F"
   seat_climate_settings: Optional[Dict[str, Any]] = None


@dataclass
class VehicleStatusOptions:
   refresh: bool = False
   parsed: bool = False


RawVehicleStatus = Dict[str, Any]


@dataclass
class VehicleStatus:
   engine_on: bool = False
   locked: bool = True
   battery_charge: Optional[float] = None
   last_update: Optional[datetime] = None
   raw: RawVehicleStatus = field(default_factory=dict)


@dataclass
class FullVehicleStatus:
   payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VehicleLocation:
   latitude: float
   longitude: float
   altitude: Optional[float] = None
   heading: Optional[float] = None
   speed: Optional[Dict[str, float]] = None


@dataclass
class VehicleOdometer:
   value: float
   unit: int


@dataclass
class SeatHeaterVentInfo:
   levels: List[int] = field(default_factory=list)
   enabled: bool = False
