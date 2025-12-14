```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Union, cast

from ..constants import (
   DEFAULT_VEHICLE_STATUS_OPTIONS,
   POSSIBLE_CHARGE_LIMIT_VALUES,
   REGIONS,
)
from ..interfaces.common_interfaces import (
   ChargeTarget,
   DeepPartial,
   EVChargeModeTypes,
   EVPlugTypes,
   FullVehicleStatus,
   RawVehicleStatus,
   VehicleDayTrip,
   VehicleLocation,
   VehicleMonthTrip,
   VehicleMonthlyReport,
   VehicleOdometer,
   VehicleRegisterOptions,
   VehicleStartOptions,
   VehicleStatus,
   VehicleStatusOptions,
   VehicleTargetSOC,
)
from ..interfaces.european_interfaces import (
   EUDatedDriveHistory,
   EUDriveHistory,
   EUPOIInformation,
   historyDrivingPeriod,
)
from ..logger import logger
from ..tools.common_tools import ManagedBluelinkyError, manageBluelinkyError
from ..util import addMinutes, celciusToTempCode, parseDate, tempCodeToCelsius
from .vehicle import Vehicle

T = TypeVar("T")


@dataclass
class _ServerRates:
   max: int = -1
   current: int = -1
   reset: Optional[datetime] = None
   updatedAt: Optional[datetime] = None


class EuropeanVehicle(Vehicle):
   region = REGIONS.EU

   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: Any):
      super().__init__(vehicleConfig, controller)
      self.vehicleConfig = vehicleConfig
      self.controller = controller
      self.serverRates: _ServerRates = _ServerRates()
      logger.debug(f"EU Vehicle {self.vehicleConfig.id} created")

   def start(self, config: VehicleStartOptions) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/temperature",
               json={
                  "action": "start",
                  "hvacType": 0,
                  "options": {
                     "defrost": config.defrost,
                     "heating1": 1 if config.heatedFeatures else 0,
                  },
                  "tempCode": celciusToTempCode(REGIONS.EU, config.temperature),
                  "unit": config.unit,
               },
            )
         )
         logger.info(f"Climate started for vehicle {self.vehicleConfig.id}")
         return cast(str, response.body)
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.start")

   def stop(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/temperature",
               json={
                  "action": "stop",
                  "hvacType": 0,
                  "options": {
                     "defrost": True,
                     "heating1": 1,
                  },
                  "tempCode": "10H",
                  "unit": "C",
               },
            )
         )
         logger.info(f"Climate stopped for vehicle {self.vehicleConfig.id}")
         return cast(str, response.body)
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.stop")

   def lock(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/door",
               json={
                  "action": "close",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )
         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Vehicle {self.vehicleConfig.id} locked")
            return "Lock successful"
         return "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.lock")

   def unlock(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/door",
               json={
                  "action": "open",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Vehicle {self.vehicleConfig.id} unlocked")
            return "Unlock successful"

         return "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.unlock")

   def fullStatus(self, input: VehicleStatusOptions) -> Optional[FullVehicleStatus]:
      statusConfig: Dict[str, Any] = {}
      statusConfig.update(DEFAULT_VEHICLE_STATUS_OPTIONS)
      statusConfig.update(input.__dict__ if hasattr(input, "__dict__") else cast(Dict[str, Any], input))

      http = self.controller.getVehicleHttpService()

      try:
         fullStatus: Any

         if getattr(self.vehicleConfig, "ccuCCS2ProtocolSupport", False):
            cachedResponse = self.updateRates(
               http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/ccs2/carstatus/latest")
            )
            fullStatus = cachedResponse.body["resMsg"]["state"]["Vehicle"]
         else:
            cachedResponse = self.updateRates(
               http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status/latest")
            )
            fullStatus = cachedResponse.body["resMsg"]["vehicleStatusInfo"]

            if statusConfig.get("refresh"):
               statusResponse = self.updateRates(
                  http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status")
               )
               fullStatus["vehicleStatus"] = statusResponse.body["resMsg"]

               locationResponse = self.updateRates(
                  http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location")
               )
               fullStatus["vehicleLocation"] = locationResponse.body["resMsg"]["gpsDetail"]

         self._fullStatus = fullStatus
         return self._fullStatus
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.fullStatus")

   def status(self, input: VehicleStatusOptions) -> Optional[Union[VehicleStatus, RawVehicleStatus]]:
      statusConfig: Dict[str, Any] = {}
      statusConfig.update(DEFAULT_VEHICLE_STATUS_OPTIONS)
      statusConfig.update(input.__dict__ if hasattr(input, "__dict__") else cast(Dict[str, Any], input))

      http = self.controller.getVehicleHttpService()

      try:
         vehicleStatus: Any
         parsedStatus: VehicleStatus

         if getattr(self.vehicleConfig, "ccuCCS2ProtocolSupport", False):
            vehicleStatus = self.fullStatus(input)

            locks = [
               bool(vehicleStatus.get("Cabin", {}).get("Door", {}).get("Row1", {}).get("Passenger", {}).get("Lock"))
               if isinstance(vehicleStatus, dict)
               else False,
               bool(vehicleStatus.get("Cabin", {}).get("Door", {}).get("Row1", {}).get("Driver", {}).get("Lock"))
               if isinstance(vehicleStatus, dict)
               else False,
               bool(vehicleStatus.get("Cabin", {}).get("Door", {}).get("Row2", {}).get("Left", {}).get("Lock"))
               if isinstance(vehicleStatus, dict)
               else False,
               bool(vehicleStatus.get("Cabin", {}).get("Door", {}).get("Row2", {}).get("Right", {}).get("Lock"))
               if isinstance(vehicleStatus, dict)
               else False,
            ]

            plugedTo: EVPlugTypes
            connector_state = (
               vehicleStatus.get("Green", {})
               .get("ChargingInformation", {})
               .get("ConnectorFastening", {})
               .get("State")
               if isinstance(vehicleStatus, dict)
               else None
            )
            if connector_state:
               plugedTo = EVPlugTypes.STATION
            else:
               plugedTo = EVPlugTypes.UNPLUGED

            body = vehicleStatus.get("Body", {}) if isinstance(vehicleStatus, dict) else {}
            cabin = vehicleStatus.get("Cabin", {}) if isinstance(vehicleStatus, dict) else {}
            chassis = vehicleStatus.get("Chassis", {}) if isinstance(vehicleStatus, dict) else {}
            electronics = vehicleStatus.get("Electronics", {}) if isinstance(vehicleStatus, dict) else {}
            drivetrain = vehicleStatus.get("Drivetrain", {}) if isinstance(vehicleStatus, dict) else {}
            green = vehicleStatus.get("Green", {}) if isinstance(vehicleStatus, dict) else {}

            parsedStatus = {
               "chassis": {
                  "hoodOpen": bool(body.get("Hood", {}).get("Open")),
                  "trunkOpen": bool(body.get("Trunk", {}).get("Open")),
                  "locked": all(v is False for v in locks),
                  "openDoors": {
                     "frontRight": bool(
                        cabin.get("Door", {})
                        .get("Row1", {})
                        .get("Passenger", {})
                        .get("Open")
                     ),
                     "frontLeft": bool(
                        cabin.get("Door", {})
                        .get("Row1", {})
                        .get("Driver", {})
                        .get("Open")
                     ),
                     "backLeft": bool(
                        cabin.get("Door", {})
                        .get("Row2", {})
                        .get("Left", {})
                        .get("Open")
                     ),
                     "backRight": bool(
                        cabin.get("Door", {})
                        .get("Row2", {})
                        .get("Right", {})
                        .get("Open")
                     ),
                  },
                  "tirePressureWarningLamp": {
                     "rearLeft": bool(
                        chassis.get("Axle", {})
                        .get("Row2", {})
                        .get("Left", {})
                        .get("Tire", {})
                        .get("PressureLow")
                     ),
                     "frontLeft": bool(
                        chassis.get("Axle", {})
                        .get("Row1", {})
                        .get("Left", {})
                        .get("Tire", {})
                        .get("PressureLow")
                     ),
                     "frontRight": bool(
                        chassis.get("Axle", {})
                        .get("Row1", {})
                        .get("Right", {})
                        .get("Tire", {})
                        .get("PressureLow")
                     ),
                     "rearRight": bool(
                        chassis.get("Axle", {})
                        .get("Row2", {})
                        .get("Right", {})
                        .get("Tire", {})
                        .get("PressureLow")
                     ),
                     "all": bool(chassis.get("Axle", {}).get("Tire", {}).get("PressureLow")),
                  },
               },
               "climate": {
                  "active": cabin.get("HVAC", {})
                  .get("Row1", {})
                  .get("Driver", {})
                  .get("Temperature", {})
                  .get("Value")
                  == "ON",
                  "steeringwheelHeat": bool(cabin.get("SteeringWheel", {}).get("Heat", {}).get("State")),
                  "sideMirrorHeat": False,
                  "rearWindowHeat": False,
                  "defrost": False,
                  "temperatureSetpoint": "",
                  "temperatureUnit": 0,
               },
               "engine": {
                  "ignition": bool(electronics.get("PowerSupply", {}).get("Ignition1"))
                  or bool(electronics.get("PowerSupply", {}).get("Ignition3")),
                  "accessory": bool(electronics.get("PowerSupply", {}).get("Accessory")),
                  "rangeGas": None,
                  "range": drivetrain.get("FuelSystem", {}).get("DTE", {}).get("Total"),
                  "rangeEV": None,
                  "plugedTo": plugedTo,
                  "charging": None,
                  "estimatedCurrentChargeDuration": green.get("ChargingInformation", {})
                  .get("Charging", {})
                  .get("RemainTime"),
                  "estimatedFastChargeDuration": green.get("ChargingInformation", {})
                  .get("EstimatedTime", {})
                  .get("Quick"),
                  "estimatedPortableChargeDuration": green.get("ChargingInformation", {})
                  .get("EstimatedTime", {})
                  .get("ICCB"),
                  "estimatedStationChargeDuration": green.get("ChargingInformation", {})
                  .get("EstimatedTime", {})
                  .get("Standard"),
                  "batteryCharge12v": electronics.get("Battery", {}).get("Level"),
                  "batteryChargeHV": green.get("BatteryManagement", {})
                  .get("BatteryRemain", {})
                  .get("Ratio"),
               },
               "lastupdate": parseDate(vehicleStatus.get("Date")) if isinstance(vehicleStatus, dict) and vehicleStatus.get("Date") else None,
            }
         else:
            cacheString = "" if statusConfig.get("refresh") else "/latest"
            response = self.updateRates(
               http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status{cacheString}")
            )

            vehicleStatus = (
               response.body["resMsg"]
               if statusConfig.get("refresh")
               else response.body["resMsg"]["vehicleStatusInfo"]["vehicleStatus"]
            )

            def _get(dct: Any, *path: str) -> Any:
               cur = dct
               for p in path:
                  if not isinstance(cur, dict):
                     return None
                  cur = cur.get(p)
               return cur

            parsedStatus = {
               "chassis": {
                  "hoodOpen": _get(vehicleStatus, "hoodOpen"),
                  "trunkOpen": _get(vehicleStatus, "trunkOpen"),
                  "locked": vehicleStatus.get("doorLock") if isinstance(vehicleStatus, dict) else None,
                  "openDoors": {
                     "frontRight": bool(_get(vehicleStatus, "doorOpen", "frontRight")),
                     "frontLeft": bool(_get(vehicleStatus, "doorOpen", "frontLeft")),
                     "backLeft": bool(_get(vehicleStatus, "doorOpen", "backLeft")),
                     "backRight": bool(_get(vehicleStatus, "doorOpen", "backRight")),
                  },
                  "tirePressureWarningLamp": {
                     "rearLeft": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampRL")),
                     "frontLeft": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampFL")),
                     "frontRight": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampFR")),
                     "rearRight": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampRR")),
                     "all": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureWarningLampAll")),
                  },
               },
               "climate": {
                  "active": _get(vehicleStatus, "airCtrlOn"),
                  "steeringwheelHeat": bool(_get(vehicleStatus, "steerWheelHeat")),
                  "sideMirrorHeat": False,
                  "rearWindowHeat": bool(_get(vehicleStatus, "sideBackWindowHeat")),
                  "defrost": _get(vehicleStatus, "defrost"),
                  "temperatureSetpoint": tempCodeToCelsius(REGIONS.EU, _get(vehicleStatus, "airTemp", "value")),
                  "temperatureUnit": _get(vehicleStatus, "airTemp", "unit"),
               },
               "engine": {
                  "ignition": _get(vehicleStatus, "engine"),
                  "accessory": _get(vehicleStatus, "acc"),
                  "rangeGas": (
                     _get(vehicleStatus, "evStatus", "drvDistance", 0, "rangeByFuel", "gasModeRange", "value")
                     if isinstance(_get(vehicleStatus, "evStatus", "drvDistance"), list)
                     else None
                  )
                  if (
                     isinstance(_get(vehicleStatus, "evStatus", "drvDistance"), list)
                     and _get(vehicleStatus, "evStatus", "drvDistance")
                  )
                  else (_get(vehicleStatus, "dte", "value")),
                  "range": (
                     _get(vehicleStatus, "evStatus", "drvDistance", 0, "rangeByFuel", "totalAvailableRange", "value")
                     if isinstance(_get(vehicleStatus, "evStatus", "drvDistance"), list)
                     else None
                  ),
                  "rangeEV": (
                     _get(vehicleStatus, "evStatus", "drvDistance", 0, "rangeByFuel", "evModeRange", "value")
                     if isinstance(_get(vehicleStatus, "evStatus", "drvDistance"), list)
                     else None
                  ),
                  "plugedTo": _get(vehicleStatus, "evStatus", "batteryPlugin") or EVPlugTypes.UNPLUGED,
                  "charging": _get(vehicleStatus, "evStatus", "batteryCharge"),
                  "estimatedCurrentChargeDuration": _get(vehicleStatus, "evStatus", "remainTime2", "atc", "value"),
                  "estimatedFastChargeDuration": _get(vehicleStatus, "evStatus", "remainTime2", "etc1", "value"),
                  "estimatedPortableChargeDuration": _get(vehicleStatus, "evStatus", "remainTime2", "etc2", "value"),
                  "estimatedStationChargeDuration": _get(vehicleStatus, "evStatus", "remainTime2", "etc3", "value"),
                  "batteryCharge12v": _get(vehicleStatus, "battery", "batSoc"),
                  "batteryChargeHV": _get(vehicleStatus, "evStatus", "batteryStatus"),
               },
               "lastupdate": parseDate(vehicleStatus.get("time")) if isinstance(vehicleStatus, dict) and vehicleStatus.get("time") else None,
            }

            if not parsedStatus["engine"].get("range"):
               if parsedStatus["engine"].get("rangeEV") or parsedStatus["engine"].get("rangeGas"):
                  parsedStatus["engine"]["range"] = (parsedStatus["engine"].get("rangeEV") or 0) + (
                     parsedStatus["engine"].get("rangeGas") or 0
                  )

         self._status = parsedStatus if statusConfig.get("parsed") else vehicleStatus
         return self._status
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.status")

   def odometer(self) -> Optional[VehicleOdometer]:
      http = self.controller.getVehicleHttpService()
      try:
         if getattr(self.vehicleConfig, "ccuCCS2ProtocolSupport", False):
            response = self.updateRates(
               http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/ccs2/carstatus/latest")
            )
            self._odometer = response.body["resMsg"]["state"]["Vehicle"]["Drivetrain"]["Odometer"]
            return self._odometer

         response = self.updateRates(http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status/latest"))
         self._odometer = cast(VehicleOdometer, response.body["resMsg"]["vehicleStatusInfo"]["odometer"])
         return self._odometer
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.odometer")

   def location(self) -> VehicleLocation:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location"))

         resMsg = response.body.get("resMsg") if isinstance(response.body, dict) else None
         data = (resMsg.get("gpsDetail") if isinstance(resMsg, dict) else None) or resMsg

         self._location = {
            "latitude": (data or {}).get("coord", {}).get("lat") if isinstance(data, dict) else None,
            "longitude": (data or {}).get("coord", {}).get("lon") if isinstance(data, dict) else None,
            "altitude": (data or {}).get("coord", {}).get("alt") if isinstance(data, dict) else None,
            "speed": {
               "unit": (data or {}).get("speed", {}).get("unit") if isinstance(data, dict) else None,
               "value": (data or {}).get("speed", {}).get("value") if isinstance(data, dict) else None,
            },
            "heading": (data or {}).get("head") if isinstance(data, dict) else None,
         }
         return cast(VehicleLocation, self._location)
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.location")

   def startCharge(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
               json={
                  "action": "start",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Send start charge command to Vehicle {self.vehicleConfig.id}")
            return "Start charge successful"

         raise Exception("Something went wrong!")
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.startCharge")

   def stopCharge(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
               json={
                  "action": "stop",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Send stop charge command to Vehicle {self.vehicleConfig.id}")
            return "Stop charge successful"

         raise Exception("Something went wrong!")
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.stopCharge")

   def monthlyReport(
      self,
      month: Dict[str, int] = None,
   ) -> Optional[DeepPartial[VehicleMonthlyReport]]:
      if month is None:
         now = datetime.now()
         month = {"year": now.year, "month": now.month}

      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/monthlyreport",
               json={
                  "setRptMonth": toMonthDate(month),
               },
            )
         )
         rawData = (
            response.body.get("resMsg", {}).get("monthlyReport")
            if isinstance(response.body, dict)
            else None
         )
         if rawData:
            return cast(
               DeepPartial[VehicleMonthlyReport],
               {
                  "start": rawData.get("ifo", {}).get("mvrMonthStart") if isinstance(rawData, dict) else None,
                  "end": rawData.get("ifo", {}).get("mvrMonthEnd") if isinstance(rawData, dict) else None,
                  "breakdown": rawData.get("breakdown") if isinstance(rawData, dict) else None,
                  "driving": (
                     {
                        "distance": rawData.get("driving", {}).get("runDistance"),
                        "startCount": rawData.get("driving", {}).get("engineStartCount"),
                        "durations": {
                           "idle": rawData.get("driving", {}).get("engineIdleTime"),
                           "drive": rawData.get("driving", {}).get("engineOnTime"),
                        },
                     }
                     if isinstance(rawData, dict) and rawData.get("driving")
                     else None
                  ),
                  "vehicleStatus": (
                     {
                        "tpms": (
                           bool(rawData.get("vehicleStatus", {}).get("tpmsSupport"))
                           if rawData.get("vehicleStatus", {}).get("tpmsSupport") is not None
                           else None
                        ),
                        "tirePressure": {
                           "all": rawData.get("vehicleStatus", {})
                           .get("tirePressure", {})
                           .get("tirePressureLampAll")
                           == "1",
                        },
                     }
                     if isinstance(rawData, dict) and rawData.get("vehicleStatus")
                     else None
                  ),
               },
            )
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.monthyReports")

   def tripInfo(
      self,
      date: Dict[str, int] = None,
   ) -> Optional[Union[List[DeepPartial[VehicleDayTrip]], DeepPartial[VehicleMonthTrip]]]:
      if date is None:
         now = datetime.now()
         date = {"year": now.year, "month": now.month}

      http = self.controller.getApiHttpService()
      try:
         perDay = bool(date.get("day"))
         response = self.updateRates(
            http.post(
               f"/api/v1/spa/vehicles/{self.vehicleConfig.id}/tripinfo",
               json={
                  "setTripLatest": 10,
                  "setTripMonth": toMonthDate(date) if not perDay else None,
                  "setTripDay": toDayDate(date) if perDay else None,
                  "tripPeriodType": 1 if perDay else 0,
               },
            )
         )

         if not perDay:
            rawData = response.body.get("resMsg") if isinstance(response.body, dict) else None
            tripDayList = rawData.get("tripDayList") if isinstance(rawData, dict) else None
            days = (
               [
                  {
                     "dayRaw": day.get("tripDayInMonth"),
                     "date": parseDate(day.get("tripDayInMonth")) if day.get("tripDayInMonth") else None,
                     "tripsCount": day.get("tripCntDay"),
                  }
                  for day in tripDayList
                  if isinstance(day, dict)
               ]
               if isinstance(tripDayList, list)
               else []
            )
            return cast(
               DeepPartial[VehicleMonthTrip],
               {
                  "days": days,
                  "durations": {
                     "drive": rawData.get("tripDrvTime") if isinstance(rawData, dict) else None,
                     "idle": rawData.get("tripIdleTime") if isinstance(rawData, dict) else None,
                  },
                  "distance": rawData.get("tripDist") if isinstance(rawData, dict) else None,
                  "speed": {
                     "avg": rawData.get("tripAvgSpeed") if isinstance(rawData, dict) else None,
                     "max": rawData.get("tripMaxSpeed") if isinstance(rawData, dict) else None,
                  },
               },
            )
         rawData = (
            response.body.get("resMsg", {}).get("dayTripList")
            if isinstance(response.body, dict)
            else None
         )
         if rawData and isinstance(rawData, list):
            out: List[DeepPartial[VehicleDayTrip]] = []
            for day in rawData:
               if not isinstance(day, dict):
                  continue
               tripList = day.get("tripList")
               trips = []
               if isinstance(tripList, list):
                  for trip in tripList:
                     if not isinstance(trip, dict):
                        continue
                     start = parseDate(f"{day.get('tripDay')}{trip.get('tripTime')}")
                     trips.append(
                        {
                           "timeRaw": trip.get("tripTime"),
                           "start": start,
                           "end": addMinutes(start, trip.get("tripDrvTime")),
                           "durations": {
                              "drive": trip.get("tripDrvTime"),
                              "idle": trip.get("tripIdleTime"),
                           },
                           "speed": {
                              "avg": trip.get("tripAvgSpeed"),
                              "max": trip.get("tripMaxSpeed"),
                           },
                           "distance": trip.get("tripDist"),
                        }
                     )
               out.append(
                  {
                     "dayRaw": day.get("tripDay"),
                     "tripsCount": day.get("dayTripCnt"),
                     "distance": day.get("tripDist"),
                     "durations": {
                        "drive": day.get("tripDrvTime"),
                        "idle": day.get("tripIdleTime"),
                     },
                     "speed": {
                        "avg": day.get("tripAvgSpeed"),
                        "max": day.get("tripMaxSpeed"),
                     },
                     "trips": trips,
                  }
               )
            return cast(List[DeepPartial[VehicleDayTrip]], out)
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.history")

   def driveHistory(
      self, period: historyDrivingPeriod = historyDrivingPeriod.DAY
   ) -> DeepPartial[Dict[str, Any]]:
      http = self.controller.getApiHttpService()
      try:
         response = http.post(
            f"/api/v1/spa/vehicles/{self.vehicleConfig.id}/drvhistory",
            json={
               "periodTarget": period,
            },
         )
         resMsg = response.body.get("resMsg") if isinstance(response.body, dict) else {}
         drivingInfo = resMsg.get("drivingInfo") if isinstance(resMsg, dict) else None
         drivingInfoDetail = resMsg.get("drivingInfoDetail") if isinstance(resMsg, dict) else None

         return cast(
            DeepPartial[Dict[str, Any]],
            {
               "cumulated": [
                  {
                     "period": line.get("drivingPeriod"),
                     "consumption": {
                        "total": line.get("totalPwrCsp"),
                        "engine": line.get("motorPwrCsp"),
                        "climate": line.get("climatePwrCsp"),
                        "devices": line.get("eDPwrCsp"),
                        "battery": line.get("batteryMgPwrCsp"),
                     },
                     "regen": line.get("regenPwr"),
                     "distance": line.get("calculativeOdo"),
                  }
                  for line in drivingInfo
                  if isinstance(drivingInfo, list) and isinstance(line, dict)
               ]
               if isinstance(drivingInfo, list)
               else None,
               "history": [
                  {
                     "period": line.get("drivingPeriod"),
                     "rawDate": line.get("drivingDate"),
                     "date": parseDate(line.get("drivingDate")) if line.get("drivingDate") else None,
                     "consumption": {
                        "total": line.get("totalPwrCsp"),
                        "engine": line.get("motorPwrCsp"),
                        "climate": line.get("climatePwrCsp"),
                        "devices": line.get("eDPwrCsp"),
                        "battery": line.get("batteryMgPwrCsp"),
                     },
                     "regen": line.get("regenPwr"),
                     "distance": line.get("calculativeOdo"),
                  }
                  for line in drivingInfoDetail
                  if isinstance(drivingInfoDetail, list) and isinstance(line, dict)
               ]
               if isinstance(drivingInfoDetail, list)
               else None,
            },
         )
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.history")

   def getChargeTargets(self) -> Optional[List[DeepPartial[VehicleTargetSOC]]]:
      http = self.controller.getVehicleHttpService()
      try:
         response = self.updateRates(http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/charge/target"))
         rawData = (
            response.body.get("resMsg", {}).get("targetSOClist")
            if isinstance(response.body, dict)
            else None
         )
         if rawData and isinstance(rawData, list):
            return cast(
               List[DeepPartial[VehicleTargetSOC]],
               [
                  {
                     "distance": soc.get("drvDistance", {}).get("distanceType", {}).get("distanceValue")
                     if isinstance(soc, dict)
                     else None,
                     "targetLevel": soc.get("targetSOClevel") if isinstance(soc, dict) else None,
                     "type": soc.get("plugType") if isinstance(soc, dict) else None,
                  }
                  for soc in rawData
               ],
            )
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.getChargeTargets")

   def setChargeTargets(self, limits: Dict[str, ChargeTarget]) -> None:
      http = self.controller.getVehicleHttpService()
      if (
         limits.get("fast") not in POSSIBLE_CHARGE_LIMIT_VALUES
         or limits.get("slow") not in POSSIBLE_CHARGE_LIMIT_VALUES
      ):
         raise ManagedBluelinkyError(
            f"Charge target values are limited to {', '.join([str(v) for v in POSSIBLE_CHARGE_LIMIT_VALUES])}"
         )
      try:
         self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/charge/target",
               json={
                  "targetSOClist": [
                     {"plugType": EVChargeModeTypes.FAST, "targetSOClevel": limits.get("fast")},
                     {"plugType": EVChargeModeTypes.SLOW, "targetSOClevel": limits.get("slow")},
                  ],
               },
            )
         )
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.setChargeTargets")

   def setNavigation(self, poiInformations: List[EUPOIInformation]) -> None:
      http = self.controller.getVehicleHttpService()
      try:
         self.updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location/routes",
               json={
                  "deviceID": self.controller.session.deviceId,
                  "poiInfoList": poiInformations,
               },
            )
         )
      except Exception as err:
         raise manageBluelinkyError(err, "EuropeVehicle.setNavigation")

   def updateRates(self, resp: Any) -> Any:
      headers = getattr(resp, "headers", None) or {}
      limit = None
      if isinstance(headers, dict):
         limit = headers.get("x-ratelimit-limit")
      if limit is not None:
         self.serverRates.max = int(limit)
         remaining = headers.get("x-ratelimit-remaining") if isinstance(headers, dict) else None
         self.serverRates.current = int(remaining) if remaining is not None else self.serverRates.current

         reset = headers.get("x-ratelimit-reset") if isinstance(headers, dict) else None
         if reset is not None:
            self.serverRates.reset = datetime.fromtimestamp(int(f"{reset}000") / 1000.0)
         self.serverRates.updatedAt = datetime.now()
      return resp


def toMonthDate(month: Dict[str, int]) -> str:
   return f"{month['year']}{str(month['month']).zfill(2)}"


def toDayDate(date: Dict[str, int]) -> str:
   if date.get("day"):
      return f"{toMonthDate(date)}{str(date['day']).zfill(2)}"
   return toMonthDate(date)
```