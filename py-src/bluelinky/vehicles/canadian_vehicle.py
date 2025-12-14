from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from ..constants import (
   DEFAULT_VEHICLE_STATUS_OPTIONS,
   POSSIBLE_CHARGE_LIMIT_VALUES,
   REGIONS,
   ChargeTarget,
)
from ..interfaces.common_interfaces import (
   EVChargeModeTypes,
   FullVehicleStatus,
   RawVehicleStatus,
   VehicleFeatureEntry,
   VehicleInfo,
   VehicleLocation,
   VehicleOdometer,
   VehicleRegisterOptions,
   VehicleStartOptions,
   VehicleStatus,
   VehicleStatusOptions,
)
from ..logger import logger
from ..tools.common_tools import ManagedBluelinkyError
from ..util import celciusToTempCode, parseDate
from .vehicle import Vehicle
from ..controllers.canadian_controller import CanadianController


@dataclass
class CanadianInfo:
   vehicle: VehicleInfo
   features: Dict[str, Any]
   featuresModel: Dict[str, Any]
   status: RawVehicleStatus


class CanadianVehicle(Vehicle):
   region = REGIONS.CA

   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: CanadianController):
      super().__init__(vehicleConfig, controller)
      self.vehicleConfig = vehicleConfig
      self.controller = controller
      self.timeOffset = -(__import__("datetime").datetime.now().astimezone().utcoffset().total_seconds() / 3600)  # type: ignore[union-attr]
      self._info: Optional[CanadianInfo] = None
      logger.debug(f"CA Vehicle {self.vehicleConfig.id} created")

   def fullStatus(self) -> Optional[FullVehicleStatus]:
      raise NotImplementedError("Method not implemented.")

   def status(
      self,
      input: VehicleStatusOptions,
   ) -> Optional[Union[VehicleStatus, RawVehicleStatus]]:
      statusConfig = {
         **DEFAULT_VEHICLE_STATUS_OPTIONS,
         **(input or {}),
      }

      logger.debug("Begin status request, polling car %s", statusConfig.get("refresh"))
      try:
         vehicleStatus: Optional[RawVehicleStatus] = None

         if statusConfig.get("useInfo"):
            self.setInfo(bool(statusConfig.get("refresh")))
            if self._info:
               vehicleStatus = self._info.status
         else:
            endpoint = (
               self.controller.environment.endpoints.remoteStatus
               if statusConfig.get("refresh")
               else self.controller.environment.endpoints.status
            )
            response = self.request(endpoint, {})
            vehicleStatus = (response or {}).get("result", {}).get("status")

            if response and response.get("error"):
               raise Exception(response.get("error", {}).get("errorDesc"))

         logger.debug(vehicleStatus)
         parsedStatus: Optional[VehicleStatus] = None
         if vehicleStatus:
            parsedStatus = {
               "chassis": {
                  "hoodOpen": vehicleStatus.get("hoodOpen"),
                  "trunkOpen": vehicleStatus.get("trunkOpen"),
                  "locked": vehicleStatus.get("doorLock"),
                  "openDoors": {
                     "frontRight": bool((vehicleStatus.get("doorOpen") or {}).get("frontRight")),
                     "frontLeft": bool((vehicleStatus.get("doorOpen") or {}).get("frontLeft")),
                     "backLeft": bool((vehicleStatus.get("doorOpen") or {}).get("backLeft")),
                     "backRight": bool((vehicleStatus.get("doorOpen") or {}).get("backRight")),
                  },
                  "tirePressureWarningLamp": {
                     "rearLeft": bool(
                        (vehicleStatus.get("tirePressureLamp") or {}).get(
                           "tirePressureWarningLampRearLeft"
                        )
                     ),
                     "frontLeft": bool(
                        (vehicleStatus.get("tirePressureLamp") or {}).get(
                           "tirePressureWarningLampFrontLeft"
                        )
                     ),
                     "frontRight": bool(
                        (vehicleStatus.get("tirePressureLamp") or {}).get(
                           "tirePressureWarningLampFrontRight"
                        )
                     ),
                     "rearRight": bool(
                        (vehicleStatus.get("tirePressureLamp") or {}).get(
                           "tirePressureWarningLampRearRight"
                        )
                     ),
                     "all": bool(
                        (vehicleStatus.get("tirePressureLamp") or {}).get(
                           "tirePressureWarningLampAll"
                        )
                     ),
                  },
               },
               "climate": {
                  "active": vehicleStatus.get("airCtrlOn"),
                  "steeringwheelHeat": bool(vehicleStatus.get("steerWheelHeat")),
                  "sideMirrorHeat": False,
                  "rearWindowHeat": bool(vehicleStatus.get("sideBackWindowHeat")),
                  "defrost": vehicleStatus.get("defrost"),
                  "temperatureSetpoint": (vehicleStatus.get("airTemp") or {}).get("value"),
                  "temperatureUnit": (vehicleStatus.get("airTemp") or {}).get("unit"),
               },
               "engine": {
                  "ignition": vehicleStatus.get("engine"),
                  "accessory": vehicleStatus.get("acc"),
                  "range": (vehicleStatus.get("dte") or {}).get("value"),
                  "charging": ((vehicleStatus.get("evStatus") or {}).get("batteryCharge")),
                  "batteryCharge12v": ((vehicleStatus.get("battery") or {}).get("batSoc")),
                  "batteryChargeHV": ((vehicleStatus.get("evStatus") or {}).get("batteryStatus")),
               },
               "lastupdate": parseDate(vehicleStatus.get("lastStatusDate")),
            }

         self._status = parsedStatus if statusConfig.get("parsed") else vehicleStatus
         return self._status
      except Exception as err:
         message = getattr(err, "message", None)
         raise Exception(message if message is not None else str(err)) from err

   # ////////////////////////////////////////////////////////////////////////////
   # Car commands with preauth (PIN)
   # ////////////////////////////////////////////////////////////////////////////

   def lock(self) -> str:
      logger.debug("Begin lock request")
      try:
         preAuth = self.getPreAuth()
         self.request(self.controller.environment.endpoints.lock, {}, {"pAuth": preAuth})
         return "Lock successful"
      except Exception as err:
         message = getattr(err, "message", None)
         raise Exception(message if message is not None else str(err)) from err

   def unlock(self) -> str:
      logger.debug("Begin unlock request")
      try:
         preAuth = self.getPreAuth()
         self.request(self.controller.environment.endpoints.unlock, {}, {"pAuth": preAuth})
         return "Unlock successful"
      except Exception as err:
         message = getattr(err, "message", None)
         raise Exception(message if message is not None else str(err)) from err

   def start(self, startConfig: VehicleStartOptions) -> str:
      logger.debug("Begin startClimate request")
      try:
         hvac = (startConfig.get("hvac") if isinstance(startConfig, dict) else getattr(startConfig, "hvac", None))  # type: ignore[truthy-bool]
         defrost = (
            startConfig.get("defrost") if isinstance(startConfig, dict) else getattr(startConfig, "defrost", None)
         )
         heatedFeatures = (
            startConfig.get("heatedFeatures")
            if isinstance(startConfig, dict)
            else getattr(startConfig, "heatedFeatures", None)
         )
         temperature = (
            startConfig.get("temperature")
            if isinstance(startConfig, dict)
            else getattr(startConfig, "temperature", None)
         )

         body: Dict[str, Any] = {
            "hvacInfo": {
               "airCtrl": 1 if ((hvac or False) or (defrost or False)) else 0,
               "defrost": defrost or False,
               "heating1": 1 if heatedFeatures else 0,
            }
         }

         airTemp = temperature
         if airTemp is not None:
            body["hvacInfo"]["airTemp"] = {
               "value": celciusToTempCode(REGIONS.CA, airTemp),
               "unit": 0,
               "hvacTempType": 1,
            }
         elif (hvac or False) or (defrost or False):
            raise Exception("air temperature should be specified")

         preAuth = self.getPreAuth()
         response = self.request(
            self.controller.environment.endpoints.start,
            body,
            {"pAuth": preAuth},
         )

         logger.debug(response)

         if response and response.get("responseHeader") and response["responseHeader"].get("responseCode") == 0:
            return "Vehicle started!"

         return "Failed to start vehicle"
      except Exception as err:
         message = getattr(err, "message", None)
         raise Exception(message if message is not None else str(err)) from err

   def stop(self) -> str:
      logger.debug("Begin stop request")
      try:
         preAuth = self.getPreAuth()
         response = self.request(
            self.controller.environment.endpoints.stop,
            {"pAuth": preAuth},
         )
         return response
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def lights(self, withHorn: bool = False) -> str:
      logger.debug("Begin lights request with horn " + str(withHorn))
      try:
         preAuth = self.getPreAuth()
         response = self.request(
            self.controller.environment.endpoints.hornlight,
            {"horn": withHorn},
            {"pAuth": preAuth},
         )
         return response
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def stopCharge(self) -> None:
      logger.debug("Begin stopCharge")
      stopCharge = self.controller.environment.endpoints.stopCharge
      try:
         preAuth = self.getPreAuth()
         response = self.request(
            stopCharge,
            {"pin": self.controller.userConfig.pin, "pAuth": preAuth},
         )
         return response
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def startCharge(self) -> None:
      logger.debug("Begin startCharge")
      startCharge = self.controller.environment.endpoints.startCharge
      try:
         preAuth = self.getPreAuth()
         response = self.request(
            startCharge,
            {"pin": self.controller.userConfig.pin, "pAuth": preAuth},
         )
         return response
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def setChargeTargets(self, limits: Dict[str, ChargeTarget]) -> None:
      logger.debug("Begin setChargeTarget")
      if (limits.get("fast") not in POSSIBLE_CHARGE_LIMIT_VALUES) or (
         limits.get("slow") not in POSSIBLE_CHARGE_LIMIT_VALUES
      ):
         raise ManagedBluelinkyError(
            f"Charge target values are limited to {', '.join([str(x) for x in POSSIBLE_CHARGE_LIMIT_VALUES])}"
         )

      setChargeTarget = self.controller.environment.endpoints.setChargeTarget
      try:
         preAuth = self.getPreAuth()
         response = self.request(
            setChargeTarget,
            {
               "pin": self.controller.userConfig.pin,
               "pAuth": preAuth,
               "tsoc": [
                  {"plugType": EVChargeModeTypes.FAST, "level": limits.get("fast")},
                  {"plugType": EVChargeModeTypes.SLOW, "level": limits.get("slow")},
               ],
            },
         )
         return response
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def odometer(self) -> Optional[VehicleOdometer]:
      try:
         self.setInfo()
         if self._info:
            return {"unit": self._info.vehicle.odometer, "value": self._info.vehicle.odometerUnit}
         raise Exception("error: no info")
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def location(self) -> VehicleLocation:
      logger.debug("Begin locate request")
      try:
         preAuth = self.getPreAuth()
         response = self.request(
            self.controller.environment.endpoints.locate,
            {},
            {"pAuth": preAuth},
         )
         self._location = response.get("result")
         return self._location
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   # ////////////////////////////////////////////////////////////////////////////
   # Internal
   # ////////////////////////////////////////////////////////////////////////////

   def getPreAuth(self) -> str:
      logger.info("Begin pre-authentication")
      try:
         response = self.request(self.controller.environment.endpoints.verifyPin, {})
         return response["result"]["pAuth"]
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def request(self, endpoint: str, body: Any, headers: Any = None) -> Any:
      if headers is None:
         headers = {}
      logger.debug(f"[{endpoint}] {__import__('json').dumps(headers)} {__import__('json').dumps(body)}")

      # add logic for token refresh to ensure we don't use a stale token
      self.controller.refreshAccessToken()

      import requests

      options_headers: Dict[str, Any] = {
         "from": self.controller.environment.origin,
         "language": 1,
         "offset": self.timeOffset,
         "accessToken": self.controller.session.accessToken,
         "vehicleId": self.vehicleConfig.id,
         **headers,
      }

      payload: Dict[str, Any]
      if isinstance(body, dict):
         payload = {"pin": self.userConfig.pin, **body}
      else:
         payload = {"pin": self.userConfig.pin, "body": body}

      try:
         resp = requests.post(endpoint, json=payload, headers=options_headers)
         data = resp.json()

         if (
            isinstance(data, dict)
            and data.get("responseHeader")
            and data["responseHeader"].get("responseCode") != 0
         ):
            return data["responseHeader"].get("responseDesc")

         return data
      except Exception as err:
         raise Exception("error: " + str(err)) from err

   def setInfo(self, refresh: bool = False) -> None:
      if self._info is not None and not refresh:
         return
      try:
         preAuth = self.getPreAuth()
         response = self.request(
            self.controller.environment.endpoints.vehicleInfo,
            {},
            {"pAuth": preAuth},
         )
         self._info = response.get("result")
      except Exception as err:
         raise Exception("error: " + str(err)) from err