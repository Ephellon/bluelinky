from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypeVar, Union, overload

from bluelinky.constants import (
   DEFAULT_VEHICLE_STATUS_OPTIONS,
   POSSIBLE_CHARGE_LIMIT_VALUES,
   REGIONS,
   ChargeTarget,
)
from bluelinky.interfaces.common_interfaces import (
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
   VehicleWindowsOptions,
)
from bluelinky.interfaces.european_interfaces import (
   EUDatedDriveHistory,
   EUDriveHistory,
   EUPOIInformation,
   historyDrivingPeriod,
)
from bluelinky.logger import logger
from bluelinky.tools.common_tools import ManagedBluelinkyError, manageBluelinkyError
from bluelinky.util import addMinutes, celciusToTempCode, parseDate, tempCodeToCelsius
from bluelinky.vehicles.vehicle import Vehicle

if TYPE_CHECKING:  # pragma: no cover - type checking only
   from ..controllers.australia_controller import AustraliaController

T = TypeVar("T", bound=Dict[str, Any])


@dataclass
class _ServerRates:
   max: int = -1
   current: int = -1
   reset: Optional[datetime] = None
   updatedAt: Optional[datetime] = None


def _to_month_date(month: Dict[str, int]) -> str:
   return f"{month['year']}{str(month['month']).zfill(2)}"


def _to_day_date(date: Dict[str, int]) -> str:
   if date.get("day"):
      return f"{_to_month_date(date)}{str(date['day']).zfill(2)}"
   return _to_month_date(date)


class AustraliaVehicle(Vehicle):
   region = REGIONS.AU

   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: AustraliaController):
      self.region = REGIONS.AU
      self.serverRates: _ServerRates = _ServerRates()
      super().__init__(vehicleConfig, controller)
      logger.debug(f"AU Vehicle {self.vehicleConfig.id} created")

   def start(self, config: VehicleStartOptions) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/engine",
               body={
                  "action": "start",
                  "hvacType": 0,
                  "options": {
                     "defrost": config.defrost,
                     "heating1": 1 if config.heatedFeatures else 0,
                  },
                  "tempCode": celciusToTempCode(REGIONS.AU, config.temperature),
                  "unit": config.unit,
               },
            )
         )
         logger.info(f"Climate started for vehicle {self.vehicleConfig.id}")
         return response.body
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.start")

   def stop(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/engine",
               body={
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
         return response.body
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.stop")

   def lock(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/door",
               body={
                  "action": "close",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )
         if response.statusCode == 200:
            logger.debug(f"Vehicle {self.vehicleConfig.id} locked")
            return "Lock successful"
         return "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.lock")

   def unlock(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/door",
               body={
                  "action": "open",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if response.statusCode == 200:
            logger.debug(f"Vehicle {self.vehicleConfig.id} unlocked")
            return "Unlock successful"

         return "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.unlock")

   def setWindows(self, config: VehicleWindowsOptions) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/windowcurtain",
               body=config,  # type: ignore[arg-type]
            )
         )
         logger.info(f"Climate started for vehicle {self.vehicleConfig.id}")
         return response.body
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.start")

   def fullStatus(self, input: VehicleStatusOptions) -> Optional[FullVehicleStatus]:
      statusConfig = {
         **DEFAULT_VEHICLE_STATUS_OPTIONS,
         **(input or {}),
      }

      http = self.controller.getVehicleHttpService()

      try:
         vehicleStatusResponse = self._update_rates(
            http.get(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status/latest"
               if statusConfig.get("refresh")
               else f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status"
            )
         )
         locationResponse = self._update_rates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location/park")
         )
         odometer = self.odometer()
         if not odometer:
            return None

         self._fullStatus = {
            "vehicleLocation": locationResponse.body.get("resMsg", {}).get("gpsDetail"),
            "odometer": odometer,
            "vehicleStatus": vehicleStatusResponse.body.get("resMsg"),
         }
         return self._fullStatus  # type: ignore[return-value]
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.fullStatus")

   def status(
      self, input: VehicleStatusOptions | None = None
   ) -> Optional[Union[VehicleStatus, RawVehicleStatus]]:
      if input is None:
         input = VehicleStatusOptions(refresh=True, parsed=True)

      statusConfig = {
         **DEFAULT_VEHICLE_STATUS_OPTIONS,
         **(input or {}),
      }

      http = self.controller.getVehicleHttpService()

      try:
         cacheString = "" if statusConfig.get("refresh") else "/latest"
         response = self._update_rates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status{cacheString}")
         )
         vehicleStatus = response.body.get("resMsg")

         parsedStatus: VehicleStatus = {
            "chassis": {
               "hoodOpen": (vehicleStatus or {}).get("hoodOpen") if vehicleStatus else None,
               "trunkOpen": (vehicleStatus or {}).get("trunkOpen") if vehicleStatus else None,
               "locked": (vehicleStatus or {}).get("doorLock") if vehicleStatus else None,
               "openDoors": {
                  "frontRight": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("frontRight")),
                  "frontLeft": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("frontLeft")),
                  "backLeft": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("backLeft")),
                  "backRight": bool(((vehicleStatus or {}).get("doorOpen") or {}).get("backRight")),
               },
               "tirePressureWarningLamp": {
                  "rearLeft": bool(
                     (((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureLampRL"))
                  ),
                  "frontLeft": bool(
                     (((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureLampFL"))
                  ),
                  "frontRight": bool(
                     (((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureLampFR"))
                  ),
                  "rearRight": bool(
                     (((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureLampRR"))
                  ),
                  "all": bool(
                     (((vehicleStatus or {}).get("tirePressureLamp") or {}).get("tirePressureWarningLampAll"))
                  ),
               },
            },
            "climate": {
               "active": (vehicleStatus or {}).get("airCtrlOn") if vehicleStatus else None,
               "steeringwheelHeat": bool((vehicleStatus or {}).get("steerWheelHeat") if vehicleStatus else None),
               "sideMirrorHeat": False,
               "rearWindowHeat": bool((vehicleStatus or {}).get("sideBackWindowHeat") if vehicleStatus else None),
               "defrost": (vehicleStatus or {}).get("defrost") if vehicleStatus else None,
               "temperatureSetpoint": tempCodeToCelsius(
                  REGIONS.AU, (((vehicleStatus or {}).get("airTemp") or {}).get("value"))
               ),
               "temperatureUnit": ((vehicleStatus or {}).get("airTemp") or {}).get("unit"),
            },
            "engine": {
               "ignition": (vehicleStatus or {}).get("engine") if vehicleStatus else None,
               "accessory": (vehicleStatus or {}).get("acc") if vehicleStatus else None,
               "rangeGas": (
                  ((((((vehicleStatus or {}).get("evStatus") or {}).get("drvDistance") or [None])[0] or {}).get("rangeByFuel") or {}).get("gasModeRange") or {}).get("value")
                  if vehicleStatus
                  else None
               )
               or ((vehicleStatus or {}).get("dte") or {}).get("value"),
               "range": (
                  ((((((vehicleStatus or {}).get("evStatus") or {}).get("drvDistance") or [None])[0] or {}).get("rangeByFuel") or {}).get("totalAvailableRange") or {}).get("value")
                  if vehicleStatus
                  else None
               ),
               "rangeEV": (
                  ((((((vehicleStatus or {}).get("evStatus") or {}).get("drvDistance") or [None])[0] or {}).get("rangeByFuel") or {}).get("evModeRange") or {}).get("value")
                  if vehicleStatus
                  else None
               ),
               "plugedTo": ((vehicleStatus or {}).get("evStatus") or {}).get("batteryPlugin")
               if ((vehicleStatus or {}).get("evStatus") or {}).get("batteryPlugin") is not None
               else EVPlugTypes.UNPLUGED,
               "charging": ((vehicleStatus or {}).get("evStatus") or {}).get("batteryCharge"),
               "estimatedCurrentChargeDuration": (
                  (((vehicleStatus or {}).get("evStatus") or {}).get("remainTime2") or {}).get("atc") or {}
               ).get("value"),
               "estimatedFastChargeDuration": (
                  (((vehicleStatus or {}).get("evStatus") or {}).get("remainTime2") or {}).get("etc1") or {}
               ).get("value"),
               "estimatedPortableChargeDuration": (
                  (((vehicleStatus or {}).get("evStatus") or {}).get("remainTime2") or {}).get("etc2") or {}
               ).get("value"),
               "estimatedStationChargeDuration": (
                  (((vehicleStatus or {}).get("evStatus") or {}).get("remainTime2") or {}).get("etc3") or {}
               ).get("value"),
               "batteryCharge12v": ((vehicleStatus or {}).get("battery") or {}).get("batSoc"),
               "batteryChargeHV": ((vehicleStatus or {}).get("evStatus") or {}).get("batteryStatus"),
            },
            "lastupdate": parseDate((vehicleStatus or {}).get("time")) if (vehicleStatus or {}).get("time") else None,
         }

         if not parsedStatus["engine"].get("range"):
            if parsedStatus["engine"].get("rangeEV") or parsedStatus["engine"].get("rangeGas"):
               parsedStatus["engine"]["range"] = (parsedStatus["engine"].get("rangeEV") or 0) + (
                  parsedStatus["engine"].get("rangeGas") or 0
               )

         self._status = parsedStatus if statusConfig.get("parsed") else vehicleStatus
         return self._status  # type: ignore[return-value]
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.status")

   def odometer(self) -> Optional[VehicleOdometer]:
      http = self.controller.getVehicleHttpService()
      try:
         now = datetime.now()
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/monthlyreport",
               body={
                  "setRptMonth": _to_month_date({"year": now.year, "month": now.month}),
               },
            )
         )
         self._odometer = {
            "unit": 0,
            "value": response.body.get("resMsg", {}).get("odometer"),
         }
         return self._odometer  # type: ignore[return-value]
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.odometer")

   def location(self) -> VehicleLocation:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location/park")
         )

         data = (response.body.get("resMsg") or {}).get("gpsDetail") if response.body else None
         coord = (data or {}).get("coord") or {}
         speed = (data or {}).get("speed") or {}

         self._location = {
            "latitude": coord.get("lat"),
            "longitude": coord.get("lon"),
            "altitude": coord.get("alt"),
            "speed": {
               "unit": speed.get("unit"),
               "value": speed.get("value"),
            },
            "heading": (data or {}).get("head"),
         }

         return self._location  # type: ignore[return-value]
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.location")

   def startCharge(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
               body={
                  "action": "start",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if response.statusCode == 200:
            logger.debug(f"Send start charge command to Vehicle {self.vehicleConfig.id}")
            return "Start charge successful"

         raise "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.startCharge")

   def stopCharge(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
               body={
                  "action": "stop",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if response.statusCode == 200:
            logger.debug(f"Send stop charge command to Vehicle {self.vehicleConfig.id}")
            return "Stop charge successful"

         raise "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.stopCharge")

   def monthlyReport(
      self,
      month: Dict[str, int] = None,
   ) -> Optional[DeepPartial[VehicleMonthlyReport]]:
      if month is None:
         now = datetime.now()
         month = {"year": now.year, "month": now.month}

      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/monthlyreport",
               body={
                  "setRptMonth": _to_month_date(month),
               },
            )
         )
         rawData = (response.body.get("resMsg") or {}).get("monthlyReport")
         if rawData:
            return {
               "start": ((rawData.get("ifo") or {}).get("mvrMonthStart")),
               "end": ((rawData.get("ifo") or {}).get("mvrMonthEnd")),
               "breakdown": rawData.get("breakdown"),
               "driving": (
                  {
                     "distance": (rawData.get("driving") or {}).get("runDistance"),
                     "startCount": (rawData.get("driving") or {}).get("engineStartCount"),
                     "durations": {
                        "idle": (rawData.get("driving") or {}).get("engineIdleTime"),
                        "drive": (rawData.get("driving") or {}).get("engineOnTime"),
                     },
                  }
                  if rawData.get("driving")
                  else None
               ),
               "vehicleStatus": (
                  {
                     "tpms": (
                        bool((rawData.get("vehicleStatus") or {}).get("tpmsSupport"))
                        if (rawData.get("vehicleStatus") or {}).get("tpmsSupport")
                        else None
                     ),
                     "tirePressure": {
                        "all": ((rawData.get("vehicleStatus") or {}).get("tirePressure") or {}).get(
                           "tirePressureLampAll"
                        )
                        == "1",
                     },
                  }
                  if rawData.get("vehicleStatus")
                  else None
               ),
            }
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.monthyReports")

   @overload
   def tripInfo(self, date: Dict[str, int]) -> Optional[List[DeepPartial[VehicleDayTrip]]]: ...

   @overload
   def tripInfo(self, date: Optional[Dict[str, int]] = None) -> Optional[DeepPartial[VehicleMonthTrip]]: ...

   def tripInfo(
      self,
      date: Optional[Dict[str, int]] = None,
   ) -> Optional[Union[List[DeepPartial[VehicleDayTrip]], DeepPartial[VehicleMonthTrip]]]:
      if date is None:
         now = datetime.now()
         date = {"year": now.year, "month": now.month}

      http = self.controller.getApiHttpService()
      try:
         perDay = bool(date.get("day"))
         response = self._update_rates(
            http.post(
               f"/api/v1/spa/vehicles/{self.vehicleConfig.id}/tripinfo",
               body={
                  "setTripLatest": 10,
                  "setTripMonth": None if perDay else _to_month_date(date),  # type: ignore[arg-type]
                  "setTripDay": _to_day_date(date) if perDay else None,  # type: ignore[arg-type]
                  "tripPeriodType": 1 if perDay else 0,
               },
            )
         )

         if not perDay:
            rawData = response.body.get("resMsg") or {}
            tripDayList = rawData.get("tripDayList")
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
            return {
               "days": days,
               "durations": {
                  "drive": rawData.get("tripDrvTime"),
                  "idle": rawData.get("tripIdleTime"),
               },
               "distance": rawData.get("tripDist"),
               "speed": {
                  "avg": rawData.get("tripAvgSpeed"),
                  "max": rawData.get("tripMaxSpeed"),
               },
            }
         else:
            rawData = (response.body.get("resMsg") or {}).get("dayTripList")
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
               return out
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.history")

   def driveHistory(
      self, period: historyDrivingPeriod = historyDrivingPeriod.DAY
   ) -> DeepPartial[Dict[str, Any]]:
      http = self.controller.getApiHttpService()
      try:
         response = http.post(
            f"/api/v1/spa/vehicles/{self.vehicleConfig.id}/drvhistory",
            body={
               "periodTarget": period,
            },
         )
         resMsg = response.body.get("resMsg") or {}
         drivingInfo = resMsg.get("drivingInfo") or []
         drivingInfoDetail = resMsg.get("drivingInfoDetail") or []
         return {
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
               if isinstance(line, dict)
            ],
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
               if isinstance(line, dict)
            ],
         }
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.history")

   def getChargeTargets(self) -> Optional[List[DeepPartial[VehicleTargetSOC]]]:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._update_rates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/charge/target")
         )
         rawData = (response.body.get("resMsg") or {}).get("targetSOClist")
         if rawData and isinstance(rawData, list):
            out: List[DeepPartial[VehicleTargetSOC]] = []
            for rawSOC in rawData:
               if not isinstance(rawSOC, dict):
                  continue
               out.append(
                  {
                     "distance": (
                        (((rawSOC.get("drvDistance") or {}).get("distanceType") or {}).get("distanceValue"))
                     ),
                     "targetLevel": rawSOC.get("targetSOClevel"),
                     "type": rawSOC.get("plugType"),
                  }
               )
            return out
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.getChargeTargets")

   def setChargeTargets(self, limits: Dict[str, ChargeTarget]) -> None:
      http = self.controller.getVehicleHttpService()
      if (limits.get("fast") not in POSSIBLE_CHARGE_LIMIT_VALUES) or (
         limits.get("slow") not in POSSIBLE_CHARGE_LIMIT_VALUES
      ):
         raise ManagedBluelinkyError(
            f"Charge target values are limited to {', '.join(str(v) for v in POSSIBLE_CHARGE_LIMIT_VALUES)}"
         )
      try:
         self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/charge/target",
               body={
                  "targetSOClist": [
                     {"plugType": EVChargeModeTypes.FAST, "targetSOClevel": limits.get("fast")},
                     {"plugType": EVChargeModeTypes.SLOW, "targetSOClevel": limits.get("slow")},
                  ]
               },
            )
         )
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.setChargeTargets")

   def setNavigation(self, poiInformations: List[EUPOIInformation]) -> None:
      http = self.controller.getVehicleHttpService()
      try:
         self._update_rates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location/routes",
               body={
                  "deviceID": self.controller.session.deviceId,
                  "poiInfoList": poiInformations,
               },
            )
         )
      except Exception as err:
         raise manageBluelinkyError(err, "AustraliaVehicle.setNavigation")

   def _update_rates(self, resp: Any) -> Any:
      headers = getattr(resp, "headers", None) or {}
      if headers.get("x-ratelimit-limit") is not None:
         try:
            self.serverRates.max = int(headers.get("x-ratelimit-limit"))
         except Exception:
            self.serverRates.max = -1
         try:
            self.serverRates.current = int(headers.get("x-ratelimit-remaining"))
         except Exception:
            self.serverRates.current = -1
         if headers.get("x-ratelimit-reset") is not None:
            try:
               self.serverRates.reset = datetime.fromtimestamp(int(f"{headers.get('x-ratelimit-reset')}000") / 1000.0)
            except Exception:
               self.serverRates.reset = None
         self.serverRates.updatedAt = datetime.now()
      return resp
