from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from ..constants import DEFAULT_VEHICLE_STATUS_OPTIONS, Region
from ..interfaces import (
   FullVehicleStatus,
   RawVehicleStatus,
   SeatHeaterVentInfo,
   VehicleLocation,
   VehicleOdometer,
   VehicleRegisterOptions,
   VehicleStartOptions,
   VehicleStatus,
   VehicleStatusOptions,
)
from ..logger import logger
from ..constants import Region
from .vehicle import Vehicle
from urllib.parse import urlencode


def _adv_climate_validator() -> Dict[str, Any]:
   return {
      "validHeats": [0, 1, 2, 3],
      "validSeats": {"frontLeft": "0", "frontRight": "1"},
      "validStatus": [0, 1, 2, 3],
   }


class AmericanVehicle(Vehicle):
   region = Region.US

   def __init__(self, vehicle_config: VehicleRegisterOptions, controller: object):
      super().__init__(vehicle_config, controller)
      logger.debug("US Vehicle %s created", getattr(self.vehicle_config, "regId", self.vehicle_config.id))

   def _get_default_headers(self) -> Dict[str, str]:
      return {
         "access_token": self.controller.session.access_token,
         "client_id": self.controller.environment.client_id,
         "Host": self.controller.environment.host,
         "User-Agent": "okhttp/3.12.0",
         "registrationId": getattr(self.vehicle_config, "regId", self.vehicle_config.id),
         "gen": getattr(self.vehicle_config, "generation", ""),
         "username": self.user_config.username or "",
         "vin": self.vehicle_config.vin,
         "APPCLOUD-VIN": self.vehicle_config.vin,
         "Language": "0",
         "to": "ISS",
         "encryptFlag": "false",
         "from": "SPA",
         "brandIndicator": getattr(self.vehicle_config, "brandIndicator", self.vehicle_config.brand_indicator),
         "bluelinkservicepin": self.user_config.pin or "",
         "offset": "-5",
      }

   def full_status(self, input: VehicleStatusOptions) -> Optional[FullVehicleStatus]:
      raise NotImplementedError("Method not implemented.")

   def odometer(self) -> Optional[VehicleOdometer]:
      response = self._request(
         f"/ac/v2/enrollment/details/{self.user_config.username}",
         method="GET",
         headers={**self._get_default_headers()},
      )
      if response.status_code != 200:
         raise RuntimeError("Failed to get odometer reading!")
      data = response.json()
      found_vehicle = next(
         (
            item
            for item in data.get("enrolledVehicleDetails", [])
            if item.get("vehicleDetails", {}).get("vin") == self.vin()
         ),
         None,
      )
      if not found_vehicle:
         return None
      vehicle_details = found_vehicle.get("vehicleDetails", {})
      self._odometer = VehicleOdometer(
         value=vehicle_details.get("odometer"),
         unit=0,
      )
      return self._odometer

   def location(self) -> VehicleLocation:
      response = self._request(
         "/ac/v2/rcs/rfc/findMyCar",
         method="GET",
         headers={**self._get_default_headers()},
      )
      if response.status_code != 200:
         raise RuntimeError("Failed to get location!")
      data = response.json()
      return VehicleLocation(
         latitude=data["coord"]["lat"],
         longitude=data["coord"]["lon"],
         altitude=data["coord"].get("alt"),
         speed={"unit": data.get("speed", {}).get("unit"), "value": data.get("speed", {}).get("value")},
         heading=data.get("head"),
      )

   def start(self, start_config: VehicleStartOptions) -> str:
      seat_climate_options: Optional[SeatHeaterVentInfo] = None
      gen2ev = False
      merged_config = VehicleStartOptions(
         hvac=start_config.hvac,
         duration=start_config.duration,
         temperature=start_config.temperature,
         defrost=start_config.defrost,
         heated_features=start_config.heated_features,
         unit=start_config.unit,
         seat_climate_settings=start_config.seat_climate_settings,
      )
      adv_validator = _adv_climate_validator()
      start_url = "ac/v2/rcs/rsc/start"
      if getattr(self.vehicle_config, "engineType", "") == "EV":
         start_url = "ac/v2/evc/fatc/start"
         if getattr(self.vehicle_config, "generation", "") == "2":
            gen2ev = True
            logger.debug("gen2 EV vehicle - seat and climate duration options not supported")

      if isinstance(merged_config.heated_features, bool):
         merged_config.heated_features = 1 if merged_config.heated_features else 0
         logger.warning("heatedFeatures was boolean; is actually enum; please update code to use enum values")
      elif isinstance(merged_config.heated_features, int):
         if merged_config.heated_features in adv_validator["validHeats"]:
            merged_config.heated_features = merged_config.heated_features
         else:
            logger.warning("heatedFeatures is not a valid enum, defaulting to 0")
            merged_config.heated_features = 0
      else:
         logger.warning("heatedFeatures is not a number or boolean, defaulting to 0")
         merged_config.heated_features = 0

      result: Dict[str, int] = {}
      if merged_config.seat_climate_settings and not gen2ev:
         for seat, status in merged_config.seat_climate_settings.items():
            target_seat = adv_validator["validSeats"].get(seat)
            seat_status = status if status in adv_validator["validStatus"] else None
            if target_seat and seat_status is not None:
               result[target_seat] = seat_status
            else:
               logger.warning("invalid seat / seat climate option for %s", seat)
      if result:
         seat_climate_options = SeatHeaterVentInfo(levels=list(result.values()), enabled=True)

      body: Dict[str, Any] = {
         "Ims": 0,
         "airCtrl": int(bool(merged_config.hvac)),
         "airTemp": {"unit": 1, "value": f"{merged_config.temperature}"},
         "defrost": merged_config.defrost,
         "heating1": merged_config.heated_features,
         "username": self.user_config.username,
         "vin": self.vehicle_config.vin,
      }
      if not gen2ev:
         body.update({
            "igniOnDuration": merged_config.duration,
            "seatHeaterVentInfo": seat_climate_options.levels if seat_climate_options else None,
         })

      response = self._request(
         start_url,
         method="POST",
         headers={**self._get_default_headers(), "offset": "-4"},
         json=body,
      )
      if response.status_code == 200:
         logger.debug("Vehicle started successfully: %s", response.text)
         return "Vehicle started!"
      logger.error("Failed to start vehicle: %s", response.text)
      return "Failed to start vehicle"

   def stop(self) -> str:
      response = self._request(
         "/ac/v2/rcs/rsc/stop",
         method="POST",
         headers={**self._get_default_headers(), "offset": "-4"},
      )
      if response.status_code == 200:
         return "Vehicle stopped"
      raise RuntimeError("Failed to stop vehicle!")

   def status(self, input: VehicleStatusOptions) -> Optional[VehicleStatus | RawVehicleStatus]:
      status_config = DEFAULT_VEHICLE_STATUS_OPTIONS
      if input.refresh:
         refresh_flag = True
      else:
         refresh_flag = status_config.refresh
      response = self._request(
         "/ac/v2/rcs/rvs/vehicleStatus",
         method="GET",
         headers={"REFRESH": str(refresh_flag), **self._get_default_headers()},
      )
      body = response.json()
      vehicle_status = body.get("vehicleStatus") or body.get("vehicleStatusInfo", {})
      parsed_status = VehicleStatus(
         engine_on=vehicle_status.get("engine"),
         locked=vehicle_status.get("doorLock"),
         last_update=datetime_from_epoch(vehicle_status.get("dateTime")),
         raw=vehicle_status,
      )
      self._status = parsed_status if input.parsed else vehicle_status
      return self._status

   def unlock(self) -> str:
      params = urlencode({"userName": self.user_config.username or "", "vin": self.vehicle_config.vin})
      response = self._request(
         "/ac/v2/rcs/rdo/on",
         method="POST",
         headers={**self._get_default_headers()},
         data=params,
      )
      if response.status_code == 200:
         return "Unlock successful"
      return "Something went wrong!"

   def lock(self) -> str:
      params = urlencode({"userName": self.user_config.username or "", "vin": self.vehicle_config.vin})
      response = self._request(
         "/ac/v2/rcs/rdo/off",
         method="POST",
         headers={**self._get_default_headers()},
         data=params,
      )
      if response.status_code == 200:
         return "Lock successful"
      return "Something went wrong!"

   def start_charge(self) -> str:
      response = self._request(
         f"/api/v2/spa/vehicles/{self.vehicle_config.id}/control/charge",
         method="POST",
      )
      if response.status_code == 200:
         logger.debug("Send start charge command to Vehicle %s", self.vehicle_config.id)
         return "Start charge successful"
      raise RuntimeError("Something went wrong!")

   def stop_charge(self) -> str:
      response = requests.post(f"/api/v2/spa/vehicles/{self.vehicle_config.id}/control/charge")
      if response.status_code == 200:
         logger.debug("Send stop charge command to vehicle %s", self.vehicle_config.id)
         return "Stop charge successful"
      raise RuntimeError("Something went wrong!")

   def _request(self, service: str, **options: Any) -> requests.Response:
      self.controller.refresh_access_token()
      headers = options.pop("headers", {})
      headers["access_token"] = self.controller.session.access_token or ""
      url = f"{self.controller.environment.base_url}/{service.lstrip('/')}"
      response = requests.request(url=url, **{**options, "headers": headers})
      logger.debug(response.text)
      return response


def datetime_from_epoch(value: Any) -> Optional[datetime]:
   try:
      if value is None:
         return None
      return datetime.fromtimestamp(int(value))
   except Exception:
      return None

