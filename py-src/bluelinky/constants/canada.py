from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, cast

from ..interfaces.common_interfaces import Brand


@dataclass(frozen=True)
class CanadianBrandEnvironment:
   brand: Brand
   host: str
   baseUrl: str
   origin: Literal['SPA']
   endpoints: Dict[str, str]


def getEndpoints(baseUrl: str) -> Dict[str, str]:
   return {
      'login': f'{baseUrl}/tods/api/lgn',
      'logout': f'{baseUrl}/tods/api/lgout',
      # Vehicle
      'vehicleList': f'{baseUrl}/tods/api/vhcllst',
      'vehicleInfo': f'{baseUrl}/tods/api/sltvhcl',
      'status': f'{baseUrl}/tods/api/lstvhclsts',
      'remoteStatus': f'{baseUrl}/tods/api/rltmvhclsts',
      # Car commands with preauth (PIN)
      'lock': f'{baseUrl}/tods/api/drlck',
      'unlock': f'{baseUrl}/tods/api/drulck',
      'start': f'{baseUrl}/tods/api/evc/rfon',
      'stop': f'{baseUrl}/tods/api/evc/rfoff',
      'startCharge': f'{baseUrl}/tods/api/evc/rcstrt',
      'stopCharge': f'{baseUrl}/tods/api/evc/rcstp',
      'setChargeTarget': f'{baseUrl}/tods/api/evc/setsoc',
      'locate': f'{baseUrl}/tods/api/fndmcr',
      'hornlight': f'{baseUrl}/tods/api/hornlight',
      # System
      'verifyAccountToken': f'{baseUrl}/tods/api/vrfyacctkn',
      'verifyPin': f'{baseUrl}/tods/api/vrfypin',
      'verifyToken': f'{baseUrl}/tods/api/vrfytnc',
   }


def getEnvironment(host: str) -> Dict[str, object]:
   baseUrl = f'https://{host}'
   return {
      'host': host,
      'baseUrl': baseUrl,
      'origin': 'SPA',
      'endpoints': getEndpoints(baseUrl),
   }


def getHyundaiEnvironment() -> CanadianBrandEnvironment:
   return CanadianBrandEnvironment(
      brand=cast(Brand, 'hyundai'),
      **getEnvironment('mybluelink.ca'),
   )


def getKiaEnvironment() -> CanadianBrandEnvironment:
   return CanadianBrandEnvironment(
      brand=cast(Brand, 'hyundai'),
      **getEnvironment('kiaconnect.ca'),
   )


def getBrandEnvironment(brand: Brand) -> CanadianBrandEnvironment:
   if brand == 'hyundai':
      return getHyundaiEnvironment()
   if brand == 'kia':
      return getKiaEnvironment()
   raise Exception(f'Constructor {brand} is not managed.')