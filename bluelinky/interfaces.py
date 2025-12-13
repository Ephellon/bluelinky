"""Shared dataclasses for configuration and vehicle metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, TypedDict, Union

from .constants import Region


class VehicleStartOptions(TypedDict, total=False):
    hvac: bool
    duration: int
    temperature: Union[int, float]
    defrost: bool
    heated_features: int
    unit: str
    seat_climate_settings: Dict[str, str]


class VehicleStatusOptions(TypedDict, total=False):
    refresh: bool
    parsed: bool
    use_cache: bool


@dataclass
class BlueLinkyConfig:
    username: str
    password: str
    region: Region
    brand: str = "hyundai"
    auto_login: bool = True
    pin: str = "1234"
    vin: str = ""
    vehicle_id: Optional[str] = None
    language: Optional[str] = None
    stamp_mode: Optional[str] = None
    stamps_file: Optional[str] = None


@dataclass
class Session:
    access_token: str = ""
    refresh_token: str = ""
    control_token: str = ""
    device_id: str = ""
    token_expires_at: int = 0
    control_token_expires_at: int = 0


@dataclass
class VehicleRegisterOptions:
    nickname: str
    name: str
    vin: str
    reg_date: str = ""
    reg_id: Optional[str] = None
    brand_indicator: Optional[str] = None
    generation: Optional[str] = None
    id: Optional[str] = None
    engine_type: Optional[str] = None


@dataclass
class VehicleLocation:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[Dict[str, Union[int, float]]] = field(default_factory=dict)


@dataclass
class VehicleOdometer:
    value: Union[int, float]
    unit: int


@dataclass
class VehicleStatus:
    state: Dict[str, Union[int, str, float]]


@dataclass
class FullVehicleStatus:
    raw: Dict[str, Union[int, str, float]]


@dataclass
class RawVehicleStatus:
    raw: Dict[str, Union[int, str, float]]
