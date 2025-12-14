from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Literal


@dataclass
class ChineseEndpoints:
   session: str
   login: str
   redirect_uri: str
   token: str


@dataclass
class CNPOIInformationCoord:
   lat: float
   alt: float
   lon: float
   type: Literal[0]


@dataclass
class CNPOIInformation:
   phone: str
   waypointID: int
   lang: Literal[1]
   src: Literal["HERE"]
   coord: CNPOIInformationCoord
   addr: str
   zip: str
   placeid: str
   name: str


class historyDrivingPeriod(IntEnum):
   DAY = 0
   MONTH = 1
   ALL = 2


class historyCumulatedTypes(IntEnum):
   TOTAL = 0
   AVERAGE = 1
   TODAY = 2


@dataclass
class CNDriveHistoryConsumption:
   total: float
   engine: float
   climate: float
   devices: float
   battery: float


@dataclass
class CNDriveHistory:
   period: historyCumulatedTypes
   consumption: CNDriveHistoryConsumption
   regen: float
   distance: float


@dataclass
class CNDatedDriveHistory:
   period: historyDrivingPeriod
   consumption: CNDriveHistoryConsumption
   regen: float
   distance: float
   rawDate: str
   date: datetime