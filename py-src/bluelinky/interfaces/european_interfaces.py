from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal


@dataclass
class EuropeanEndpoints:
   session: str
   login: str
   redirect_uri: str
   token: str


@dataclass
class EUPOIInformationCoord:
   lat: float
   alt: float
   lon: float
   type: Literal[0]


@dataclass
class EUPOIInformation:
   phone: str
   waypointID: int
   lang: Literal[1]
   src: Literal["HERE"]
   coord: EUPOIInformationCoord
   addr: str
   zip: str
   placeid: str
   name: str


class historyDrivingPeriod(Enum):
   DAY = 0
   MONTH = 1
   ALL = 2


class historyCumulatedTypes(Enum):
   TOTAL = 0
   AVERAGE = 1
   TODAY = 2


@dataclass
class EUDriveHistoryConsumption:
   total: float
   engine: float
   climate: float
   devices: float
   battery: float


@dataclass
class EUDriveHistory:
   period: historyCumulatedTypes
   consumption: EUDriveHistoryConsumption
   regen: float
   distance: float


@dataclass
class EUDatedDriveHistory:
   period: historyDrivingPeriod
   consumption: EUDriveHistoryConsumption
   regen: float
   distance: float
   rawDate: str
   date: datetime