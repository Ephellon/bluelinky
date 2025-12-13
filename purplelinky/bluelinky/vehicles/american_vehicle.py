from __future__ import annotations

import json
from typing import Any, Dict

import requests

from bluelinky.constants import DEFAULT_VEHICLE_STATUS_OPTIONS, REGIONS
from bluelinky.constants.seatheatvent import advClimateValidator
from bluelinky.controllers.american_controller import AmericanController
from bluelinky.interfaces.common import (
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
from bluelinky.logger import logger
from bluelinky.vehicles.vehicle import Vehicle


class AmericanVehicle(Vehicle):
   region = REGIONS.US

   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: AmericanController):
      super().__init__(vehicleConfig, controller)
      logger.debug(f"US Vehicle {self.vehicleConfig.regId} created")

   def getDefaultHeaders(self) -> Dict[str, str]:
      return {
         "access_token": self.controller.session.get("accessToken"),
         "client_id": self.controller.environment.clientId,
         "Host": self.controller.environment.host,
         "User-Agent": "okhttp/3.12.0",
         "registrationId": self.vehicleConfig.regId,
         "gen": self.vehicleConfig.generation,
         "username": self.userConfig.username or "",
         "vin": self.vehicleConfig.vin,
         "APPCLOUD-VIN": self.vehicleConfig.vin,
         "Language": "0",
         "to": "ISS",
         "encryptFlag": "false",
         "from": "SPA",
         "brandIndicator": self.vehicleConfig.brandIndicator,
         "bluelinkservicepin": self.userConfig.pin or "",
         "offset": "-5",
      }

   def fullStatus(self, input: VehicleStatusOptions | None = None) -> FullVehicleStatus | None:
      raise NotImplementedError("Full status is not implemented for the US region")

   def odometer(self) -> VehicleOdometer | None:
      response = self._request(
         "/ac/v2/enrollment/details/{username}".format(username=self.userConfig.username),
         method="GET",
         headers={**self.getDefaultHeaders()},
      )
      if response.status_code != 200:
         raise RuntimeError("Failed to get odometer reading!")
      data = response.json()
      found = None
      for item in data.get("enrolledVehicleDetails", []):
         if item.get("vehicleDetails", {}).get("vin") == self.vin():
            found = item
            break
      if not found:
         return None
      self._odometer = {"value": found.get("vehicleDetails", {}).get("odometer"), "unit": 0}
      return self._odometer

   def location(self) -> VehicleLocation | None:
      response = self._request(
         "/ac/v2/rcs/rfc/findMyCar",
         method="GET",
         headers={**self.getDefaultHeaders()},
      )
      if response.status_code != 200:
         raise RuntimeError("Failed to get location!")
      data = response.json()
      return {
         "latitude": data.get("coord", {}).get("lat"),
         "longitude": data.get("coord", {}).get("lon"),
         "altitude": data.get("coord", {}).get("alt"),
         "speed": data.get("speed"),
         "heading": data.get("head"),
      }

   def start(self, startConfig: VehicleStartOptions) -> str:
      logger.debug(f"try start: {json.dumps(startConfig)}")
      seatClimateOptions: SeatHeaterVentInfo | None = None
      gen2ev = False
      mergedConfig: VehicleStartOptions = {
         "hvac": False,
         "duration": 10,
         "temperature": 70,
         "defrost": False,
         "heatedFeatures": 0,
         "unit": "F",
         "seatClimateSettings": seatClimateOptions,
         **startConfig,
      }
      logger.debug(f"mergedConfig: {json.dumps(mergedConfig)}")
      validator = advClimateValidator(self.userConfig.brand, self.region.value if hasattr(self.region, "value") else self.region)
      logger.debug(f"advClimateOptionValidator: {json.dumps(validator)}")
      start_url = "ac/v2/rcs/rsc/start"
      if self.vehicleConfig.engineType == "EV":
         start_url = "ac/v2/evc/fatc/start"
         if self.vehicleConfig.generation == "2":
            gen2ev = True
            logger.debug("gen2 EV vehicle - seat and climate duration options not supported")
      if isinstance(mergedConfig.get("heatedFeatures"), bool):
         mergedConfig["heatedFeatures"] = 1 if mergedConfig["heatedFeatures"] else 0
         logger.warning("heatedFeatures was boolean; is actually enum; please update code to use enum values")
      elif isinstance(mergedConfig.get("heatedFeatures"), int):
         heat_val = mergedConfig.get("heatedFeatures", 0)
         mergedConfig["heatedFeatures"] = heat_val if heat_val in validator.get("validHeats", []) else 0
      else:
         mergedConfig["heatedFeatures"] = 0
      result: Dict[str, int] = {}
      settings = mergedConfig.get("seatClimateSettings") or {}
      if settings and not gen2ev:
         for seat, status in settings.items():
            target_seat = validator.get("validSeats", {}).get(seat)
            if target_seat and status in validator.get("validStatus", []):
               result[target_seat] = status  # type: ignore[assignment]
            else:
               logger.warning(f"invalid seat / seat climate option for {seat}")
      seatClimateOptions = result if result else None
      logger.debug(f"Processed seatClimateOptions: {json.dumps(seatClimateOptions)}")
      body: Dict[str, Any] = {
         "Ims": 0,
         "airCtrl": int(bool(mergedConfig.get("hvac"))),
         "airTemp": {"unit": 1, "value": f"{mergedConfig.get('temperature')}"},
         "defrost": mergedConfig.get("defrost"),
         "heating1": mergedConfig.get("heatedFeatures"),
         "username": self.userConfig.username,
         "vin": self.vehicleConfig.vin,
      }
      if not gen2ev:
         body["igniOnDuration"] = mergedConfig.get("duration")
         body["seatHeaterVentInfo"] = seatClimateOptions
      logger.debug(f"starting car with payload: {json.dumps(body)}")
      response = self._request(
         f"/{start_url}",
         method="POST",
         headers={**self.getDefaultHeaders(), "offset": "-4"},
         json_body=body,
      )
      if response.status_code == 200:
         logger.debug(f"Vehicle started successfully: {response.text}")
         return "Vehicle started!"
      logger.error(f"Failed to start vehicle: {response.text}")
      return "Failed to start vehicle"

   def stop(self) -> str:
      response = self._request(
         "/ac/v2/rcs/rsc/stop",
         method="POST",
         headers={**self.getDefaultHeaders(), "offset": "-4"},
      )
      if response.status_code == 200:
         return "Vehicle stopped"
      raise RuntimeError("Failed to stop vehicle!")

   def status(self, input: VehicleStatusOptions) -> VehicleStatus | RawVehicleStatus | None:
      status_config = {**DEFAULT_VEHICLE_STATUS_OPTIONS, **(input or {})}
      response = self._request(
         "/ac/v2/rcs/rvs/vehicleStatus",
         method="GET",
         headers={"REFRESH": str(status_config.get("refresh", False)), **self.getDefaultHeaders()},
      )
      if response.status_code != 200:
         return None
      payload = response.json()
      vehicle_status = payload.get("vehicleStatus", {})
      parsed_status: VehicleStatus = {
         "chassis": {
            "hoodOpen": vehicle_status.get("hoodOpen"),
            "trunkOpen": vehicle_status.get("trunkOpen"),
            "locked": vehicle_status.get("doorLock"),
            "openDoors": {
               "frontRight": bool(vehicle_status.get("doorOpen", {}).get("frontRight")),
               "frontLeft": bool(vehicle_status.get("doorOpen", {}).get("frontLeft")),
               "backLeft": bool(vehicle_status.get("doorOpen", {}).get("backLeft")),
               "backRight": bool(vehicle_status.get("doorOpen", {}).get("backRight")),
            },
            "tirePressureWarningLamp": {
               "rearLeft": bool(vehicle_status.get("tirePressureLamp", {}).get("tirePressureWarningLampRearLeft")),
               "frontLeft": bool(vehicle_status.get("tirePressureLamp", {}).get("tirePressureWarningLampFrontLeft")),
               "frontRight": bool(vehicle_status.get("tirePressureLamp", {}).get("tirePressureWarningLampFrontRight")),
               "rearRight": bool(vehicle_status.get("tirePressureLamp", {}).get("tirePressureWarningLampRearRight")),
               "all": bool(vehicle_status.get("tirePressureLamp", {}).get("tirePressureWarningLampAll")),
            },
         },
         "climate": {
            "active": vehicle_status.get("airCtrlOn"),
            "steeringwheelHeat": bool(vehicle_status.get("steerWheelHeat")),
            "sideMirrorHeat": False,
            "rearWindowHeat": bool(vehicle_status.get("sideBackWindowHeat")),
            "defrost": vehicle_status.get("defrost"),
            "temperatureSetpoint": vehicle_status.get("airTemp", {}).get("value"),
            "temperatureUnit": vehicle_status.get("airTemp", {}).get("unit"),
         },
         "engine": {
            "ignition": vehicle_status.get("engine"),
            "accessory": vehicle_status.get("acc"),
            "range": vehicle_status.get("evStatus", {})
            .get("drvDistance", [
               {"rangeByFuel": {"totalAvailableRange": {"value": None}}}
            ])[0]
            .get("rangeByFuel", {})
            .get("totalAvailableRange", {})
            .get("value")
            or vehicle_status.get("dte", {}).get("value"),
            "charging": vehicle_status.get("evStatus", {}).get("batteryCharge"),
            "batteryCharge12v": vehicle_status.get("battery", {}).get("batSoc"),
            "batteryChargeHV": vehicle_status.get("evStatus", {}).get("batteryStatus"),
         },
         "lastupdate": vehicle_status.get("dateTime"),
      }
      self._status = parsed_status if status_config.get("parsed") else vehicle_status
      return self._status

   def unlock(self) -> str:
      form = {"userName": self.userConfig.username or "", "vin": self.vehicleConfig.vin}
      response = self._request(
         "/ac/v2/rcs/rdo/on",
         method="POST",
         headers={**self.getDefaultHeaders()},
         data=form,
      )
      if response.status_code == 200:
         return "Unlock successful"
      return "Something went wrong!"

   def lock(self) -> str:
      form = {"userName": self.userConfig.username or "", "vin": self.vehicleConfig.vin}
      response = self._request(
         "/ac/v2/rcs/rdo/off",
         method="POST",
         headers={**self.getDefaultHeaders()},
         data=form,
      )
      if response.status_code == 200:
         return "Lock successful"
      return "Something went wrong!"

   def _request(self, service: str, method: str = "GET", headers: Dict[str, str] | None = None, data: Any = None, json_body: Any = None):
      self.controller.refreshAccessToken()
      req_headers = headers or {}
      req_headers["access_token"] = self.controller.session.get("accessToken", "")
      url = f"{self.controller.environment.baseUrl}{service if service.startswith('/') else '/' + service}"
      response = requests.request(method=method, url=url, headers=req_headers, data=data, json=json_body)
      logger.debug(response.text)
      return response

