from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Optional, Union
from urllib.parse import urlencode

import requests

from ..constants import DEFAULT_VEHICLE_STATUS_OPTIONS, REGIONS
from ..constants.seatheatvent import advClimateValidator
from ..interfaces.common_interfaces import (
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
from ..interfaces.american_interfaces import RequestHeaders
from ..logger import logger
from .vehicle import Vehicle
from ..controllers.american_controller import AmericanController


class AmericanVehicle(Vehicle):
   region = REGIONS.US

   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: AmericanController):
      super().__init__(vehicleConfig, controller)
      self.vehicleConfig = vehicleConfig
      self.controller = controller
      logger.debug(f"US Vehicle {self.vehicleConfig.regId} created")

   def getDefaultHeaders(self) -> RequestHeaders:
      return {
         "access_token": self.controller.session.accessToken,
         "client_id": self.controller.environment.clientId,
         "Host": self.controller.environment.host,
         "User-Agent": "okhttp/3.12.0",
         "registrationId": self.vehicleConfig.regId,
         "gen": self.vehicleConfig.generation,
         "username": self.userConfig.username,
         "vin": self.vehicleConfig.vin,
         "APPCLOUD-VIN": self.vehicleConfig.vin,
         "Language": "0",
         "to": "ISS",
         "encryptFlag": "false",
         "from": "SPA",
         "brandIndicator": self.vehicleConfig.brandIndicator,
         "bluelinkservicepin": self.userConfig.pin,
         "offset": "-5",
      }

   def fullStatus(self) -> Optional[FullVehicleStatus]:
      raise Exception("Method not implemented.")

   def odometer(self) -> Optional[VehicleOdometer]:
      response = self._request(
         f"/ac/v2/enrollment/details/{self.userConfig.username}",
         {
            "method": "GET",
            "headers": {**self.getDefaultHeaders()},
         },
      )

      if response.status_code != 200:
         raise Exception("Failed to get odometer reading!")

      data = response.json()
      foundVehicle = None
      for item in data.get("enrolledVehicleDetails", []) or []:
         try:
            if item.get("vehicleDetails", {}).get("vin") == self.vin():
               foundVehicle = item
               break
         except Exception:
            continue

      if not foundVehicle:
         raise Exception("Failed to get odometer reading!")

      self._odometer = VehicleOdometer(
         value=foundVehicle.get("vehicleDetails", {}).get("odometer"),
         unit=0,
      )
      return self._odometer

   def location(self) -> VehicleLocation:
      response = self._request(
         "/ac/v2/rcs/rfc/findMyCar",
         {
            "method": "GET",
            "headers": {**self.getDefaultHeaders()},
         },
      )

      if response.status_code != 200:
         raise Exception("Failed to get location!")

      data = response.json()
      return VehicleLocation(
         latitude=data.get("coord", {}).get("lat"),
         longitude=data.get("coord", {}).get("lon"),
         altitude=data.get("coord", {}).get("alt"),
         speed={
            "unit": data.get("speed", {}).get("unit"),
            "value": data.get("speed", {}).get("value"),
         },
         heading=data.get("head"),
      )

   def start(self, startConfig: VehicleStartOptions) -> str:
      logger.debug("try start: ", json.dumps(asdict(startConfig) if hasattr(startConfig, "__dataclass_fields__") else startConfig))

      seatClimateOptions: Optional[SeatHeaterVentInfo] = None
      gen2ev = False

      defaults: Dict[str, Any] = {
         "hvac": False,
         "duration": 10,
         "temperature": 70,
         "defrost": False,
         "heatedFeatures": 0,
         "unit": "F",
         "seatClimateSettings": seatClimateOptions,
      }

      incoming = asdict(startConfig) if hasattr(startConfig, "__dataclass_fields__") else (startConfig or {})
      mergedConfig: Dict[str, Any] = {**defaults, **incoming}

      logger.debug(f"mergedConfig:  {json.dumps(mergedConfig)}")
      advClimateOptionValidator = advClimateValidator(self.userConfig.brand, self.region)
      logger.debug(f"advClimateOptionValidator: {json.dumps(advClimateOptionValidator)}")

      start_url = "ac/v2/rcs/rsc/start"
      if self.vehicleConfig.engineType == "EV":
         start_url = "ac/v2/evc/fatc/start"
         if str(self.vehicleConfig.generation) == "2":
            gen2ev = True
            logger.debug("gen2 EV vehicle - seat and climate duration options not supported")
      logger.debug(f"Using start URL: {start_url}")

      heatedFeatures = mergedConfig.get("heatedFeatures")
      if isinstance(heatedFeatures, bool):
         mergedConfig["heatedFeatures"] = 1 if heatedFeatures else 0
         logger.warn("heatedFeatures was boolean; is actually enum; please update code to use enum values")
      elif isinstance(heatedFeatures, (int, float)):
         try:
            valid_heats = advClimateOptionValidator.get("validHeats", [])
            if heatedFeatures in valid_heats:
               mergedConfig["heatedFeatures"] = valid_heats[int(heatedFeatures)]
            else:
               logger.warn("heatedFeatures is not a valid enum, defaulting to 0")
               mergedConfig["heatedFeatures"] = 0
         except Exception:
            logger.warn("heatedFeatures is not a valid enum, defaulting to 0")
            mergedConfig["heatedFeatures"] = 0
      else:
         logger.warn("heatedFeatures is not a number or boolean, defaulting to 0")
         mergedConfig["heatedFeatures"] = 0

      result: Dict[str, Any] = {}
      seat_settings = mergedConfig.get("seatClimateSettings")
      if seat_settings and not gen2ev:
         controlled_seats = list(seat_settings.keys())
         if len(controlled_seats) > 0:
            logger.debug(f"Seat climate settings found: {json.dumps(seat_settings)}")
            valid_seats = advClimateOptionValidator.get("validSeats", {}) or {}
            valid_status = advClimateOptionValidator.get("validStatus", []) or []
            for seat in controlled_seats:
               targetSeat = valid_seats.get(seat) if valid_seats.get(seat) else None
               seatStatus = seat_settings.get(seat) if seat_settings.get(seat) in valid_status else None
               if targetSeat and seatStatus:
                  result[targetSeat] = seatStatus
               else:
                  logger.warn(f"invalid seat / seat climate option for {seat}")
         else:
            logger.warn("invalid seatClimateSettings provided, defaulting to null")
      else:
         logger.debug("no seatClimateSettings found / gen 2 ev")

      seatClimateOptions = result if len(result.keys()) > 0 else None
      logger.debug(f"Processed seatClimateOptions: {json.dumps(seatClimateOptions)}")

      body: Dict[str, Any] = {
         "Ims": 0,
         "airCtrl": int(bool(mergedConfig.get("hvac"))),
         "airTemp": {
            "unit": 1,
            "value": f"{mergedConfig.get('temperature')}",
         },
         "defrost": mergedConfig.get("defrost"),
         "heating1": mergedConfig.get("heatedFeatures"),
         "username": self.userConfig.username,
         "vin": self.vehicleConfig.vin,
      }

      if not gen2ev:
         body.update(
            {
               "igniOnDuration": mergedConfig.get("duration"),
               "seatHeaterVentInfo": seatClimateOptions,
            }
         )

      logger.debug(f"starting car with payload: {json.dumps(body)}")

      response = self._request(
         start_url,
         {
            "method": "POST",
            "headers": {**self.getDefaultHeaders(), "offset": "-4"},
            "body": body,
            "json": True,
         },
      )

      if response.status_code == 200:
         logger.debug(f"Vehicle started successfully: {response.text}")
         return "Vehicle started!"

      logger.error(f"Failed to start vehicle: {response.text}")
      return "Failed to start vehicle"

   def stop(self) -> str:
      response = self._request(
         "/ac/v2/rcs/rsc/stop",
         {
            "method": "POST",
            "headers": {**self.getDefaultHeaders(), "offset": "-4"},
         },
      )

      if response.status_code == 200:
         return "Vehicle stopped"

      raise Exception("Failed to stop vehicle!")

   def status(self, input: VehicleStatusOptions) -> Union[VehicleStatus, RawVehicleStatus, None]:
      base = asdict(DEFAULT_VEHICLE_STATUS_OPTIONS) if hasattr(DEFAULT_VEHICLE_STATUS_OPTIONS, "__dataclass_fields__") else dict(DEFAULT_VEHICLE_STATUS_OPTIONS)
      incoming = asdict(input) if hasattr(input, "__dataclass_fields__") else (input or {})
      statusConfig: Dict[str, Any] = {**base, **incoming}

      response = self._request(
         "/ac/v2/rcs/rvs/vehicleStatus",
         {
            "method": "GET",
            "headers": {
               "REFRESH": str(statusConfig.get("refresh")),
               **self.getDefaultHeaders(),
            },
         },
      )

      payload = response.json()
      vehicleStatus = payload.get("vehicleStatus")

      parsedStatus: VehicleStatus = VehicleStatus(
         chassis={
            "hoodOpen": (vehicleStatus or {}).get("hoodOpen") if vehicleStatus else None,
            "trunkOpen": (vehicleStatus or {}).get("trunkOpen") if vehicleStatus else None,
            "locked": (vehicleStatus or {}).get("doorLock") if vehicleStatus else None,
            "openDoors": {
               "frontRight": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("frontRight")) if vehicleStatus else False,
               "frontLeft": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("frontLeft")) if vehicleStatus else False,
               "backLeft": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("backLeft")) if vehicleStatus else False,
               "backRight": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("backRight")) if vehicleStatus else False,
            },
            "tirePressureWarningLamp": {
               "rearLeft": bool((((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureWarningLampRearLeft"))) if vehicleStatus else False,
               "frontLeft": bool((((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureWarningLampFrontLeft"))) if vehicleStatus else False,
               "frontRight": bool((((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureWarningLampFrontRight"))) if vehicleStatus else False,
               "rearRight": bool((((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureWarningLampRearRight"))) if vehicleStatus else False,
               "all": bool((((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureWarningLampAll"))) if vehicleStatus else False,
            },
         },
         climate={
            "active": (vehicleStatus or {}).get("airCtrlOn") if vehicleStatus else None,
            "steeringwheelHeat": bool((vehicleStatus or {}).get("steerWheelHeat")) if vehicleStatus else False,
            "sideMirrorHeat": False,
            "rearWindowHeat": bool((vehicleStatus or {}).get("sideBackWindowHeat")) if vehicleStatus else False,
            "defrost": (vehicleStatus or {}).get("defrost") if vehicleStatus else None,
            "temperatureSetpoint": (((vehicleStatus or {}).get("airTemp") or {}).get("value")) if vehicleStatus else None,
            "temperatureUnit": (((vehicleStatus or {}).get("airTemp") or {}).get("unit")) if vehicleStatus else None,
         },
         engine={
            "ignition": (vehicleStatus or {}).get("engine") if vehicleStatus else None,
            "accessory": (vehicleStatus or {}).get("acc") if vehicleStatus else None,
            "range": (
               (((((vehicleStatus or {}).get("evStatus") or {}).get("drvDistance") or [{}])[0].get("rangeByFuel") or {}).get("totalAvailableRange") or {}).get("value")
               if vehicleStatus
               else None
            )
            or (((vehicleStatus or {}).get("dte") or {}).get("value") if vehicleStatus else None),
            "charging": (((vehicleStatus or {}).get("evStatus") or {}).get("batteryCharge")) if vehicleStatus else None,
            "batteryCharge12v": (((vehicleStatus or {}).get("battery") or {}).get("batSoc")) if vehicleStatus else None,
            "batteryChargeHV": (((vehicleStatus or {}).get("evStatus") or {}).get("batteryStatus")) if vehicleStatus else None,
         },
         lastupdate=self._parse_ts_date((vehicleStatus or {}).get("dateTime") if vehicleStatus else None),
      )

      self._status = parsedStatus if statusConfig.get("parsed") else vehicleStatus
      return self._status

   def unlock(self) -> str:
      formData = {
         "userName": self.userConfig.username or "",
         "vin": self.vehicleConfig.vin,
      }

      response = self._request(
         "/ac/v2/rcs/rdo/on",
         {
            "method": "POST",
            "headers": {**self.getDefaultHeaders()},
            "body": urlencode(formData),
         },
      )

      if response.status_code == 200:
         return "Unlock successful"

      return "Something went wrong!"

   def lock(self) -> str:
      formData = {
         "userName": self.userConfig.username or "",
         "vin": self.vehicleConfig.vin,
      }

      response = self._request(
         "/ac/v2/rcs/rdo/off",
         {
            "method": "POST",
            "headers": {**self.getDefaultHeaders()},
            "body": urlencode(formData),
         },
      )

      if response.status_code == 200:
         return "Lock successful"

      return "Something went wrong!"

   def startCharge(self) -> str:
      response = self._request(
         f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
         {
            "method": "POST",
         },
      )

      if response.status_code == 200:
         logger.debug(f"Send start charge command to Vehicle {self.vehicleConfig.id}")
         return "Start charge successful"

      raise Exception("Something went wrong!")

   def stopCharge(self) -> str:
      response = requests.request(
         "POST",
         f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
      )

      if response.status_code == 200:
         logger.debug(f"Send stop charge command to vehicle {self.vehicleConfig.id}")
         return "Stop charge successful"

      raise Exception("Something went wrong!")

   def _request(self, service: str, options: Dict[str, Any]) -> requests.Response:
      self.controller.refreshAccessToken()

      headers = options.get("headers") or {}
      headers["access_token"] = self.controller.session.accessToken
      options["headers"] = headers

      method = (options.get("method") or "GET").upper()
      url = f"{self.controller.environment.baseUrl}/{service.lstrip('/')}"

      json_body = options.get("json", False)
      body = options.get("body", None)

      req_kwargs: Dict[str, Any] = {
         "headers": headers,
      }

      if method in ("POST", "PUT", "PATCH", "DELETE"):
         if json_body:
            req_kwargs["json"] = body
         else:
            if body is not None:
               req_kwargs["data"] = body
      else:
         if json_body and body is not None:
            req_kwargs["json"] = body
         elif body is not None:
            req_kwargs["data"] = body

      response = requests.request(method, url, **req_kwargs)

      if response is not None and getattr(response, "text", None):
         logger.debug(response.text)

      return response

   @staticmethod
   def _parse_ts_date(value: Any):
      if not value:
         return None
      try:
         from datetime import datetime, timezone

         if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
         if isinstance(value, str):
            v = value.strip()
            if v.isdigit():
               return datetime.fromtimestamp(float(v) / 1000.0, tz=timezone.utc)
            try:
               return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
               return datetime.fromtimestamp(float(v) / 1000.0, tz=timezone.utc)
      except Exception:
         return None
      return None